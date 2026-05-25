"""Enki cloud API client (Leroy Merlin / Adeo)."""

from __future__ import annotations

import time
from typing import Any

import aiohttp

from .const import (
    DEVICE_TYPE_FANS,
    DEVICE_TYPE_LIGHTS,
    ENKI_AIRFLOW_API_KEY,
    ENKI_BASE_URL,
    ENKI_BFF_API_KEY,
    ENKI_HOME_API_KEY,
    ENKI_LIGHTS_API_KEY,
    ENKI_NODE_API_KEY,
    ENKI_OIDC_URL,
    ENKI_POWER_API_KEY,
    ENKI_REFERENTIEL_API_KEY,
    LIGHT_ENDPOINT,
    LOGGER,
    REFERENTIEL_VERSION,
)
from .exceptions import EnkiAuthError, EnkiConnectionError
from .helpers import normalize_power_state
from .models import EnkiDevice


class EnkiAPI:
    """Async client for the unofficial Enki REST API."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_type = "Bearer"
        self._token_expires_at = 0.0
        self._session: aiohttp.ClientSession | None = None

    async def async_close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _ensure_token(self) -> None:
        if self._access_token and time.time() < self._token_expires_at - 30:
            return
        await self.async_connect()

    def _auth_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Authorization": f"{self._token_type} {self._access_token}"}
        if extra:
            headers.update(extra)
        return headers

    async def async_connect(self) -> None:
        """Authenticate with Keycloak (resource-owner password grant)."""
        session = await self._get_session()
        try:
            async with session.post(
                ENKI_OIDC_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "password",
                    "client_id": "enki-front",
                    "username": self._username,
                    "password": self._password,
                },
            ) as response:
                if response.status == 401:
                    raise EnkiAuthError("Invalid username or password")
                if response.status != 200:
                    raise EnkiConnectionError(f"Authentication failed: HTTP {response.status}")
                payload = await response.json()
        except aiohttp.ClientError as err:
            raise EnkiConnectionError(f"Cannot reach Enki auth: {err}") from err

        self._access_token = payload["access_token"]
        self._token_type = payload.get("token_type", "Bearer")
        self._token_expires_at = time.time() + payload["expires_in"]
        LOGGER.debug("Enki session established, expires in %ss", payload["expires_in"])

    async def async_get_devices(self) -> list[EnkiDevice]:
        """Discover all nodes across every home on the account."""
        await self._ensure_token()
        homes = await self._get_homes()
        devices: list[EnkiDevice] = []
        for home_id in homes:
            devices.extend(await self._get_devices_for_home(home_id))
        return devices

    async def _get_homes(self) -> list[str]:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-home-prod/v1/homes",
            headers=self._auth_headers({"X-Gateway-APIKey": ENKI_HOME_API_KEY}),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"get_homes failed: HTTP {response.status}")
            data = await response.json()
            return [home["id"] for home in data["items"]]

    async def _get_devices_for_home(self, home_id: str) -> list[EnkiDevice]:
        session = await self._get_session()
        async with session.get(
            (
                f"{ENKI_BASE_URL}/api-enki-mobile-bff-prod/v1/dashboard/homes/"
                f"{home_id}?hasGroups=true"
            ),
            headers=self._auth_headers({"X-Gateway-APIKey": ENKI_BFF_API_KEY}),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"dashboard failed: HTTP {response.status}")
            dashboard = await response.json()

        devices: list[EnkiDevice] = []
        for section in dashboard.get("sections", []):
            for item in section.get("items", []):
                metadata = item.get("metadata", {})
                if "nodeId" not in metadata:
                    continue

                node_id = metadata["nodeId"]
                device_id = metadata["deviceId"]
                bff_type = metadata.get("deviceType", "")

                node_info = await self._get_node(home_id, node_id)
                device_info = await self._get_device_info_safe(device_id)
                device_type = device_info.get("type") or bff_type

                last_reported: dict[str, Any] = {}
                if item["isEnabled"]:
                    if device_type == DEVICE_TYPE_FANS:
                        last_reported = await self._get_fan_full_state(home_id, node_id)
                    elif device_type == DEVICE_TYPE_LIGHTS:
                        last_reported = await self._get_light_state_payload(home_id, node_id)

                if device_type not in {DEVICE_TYPE_FANS, DEVICE_TYPE_LIGHTS}:
                    LOGGER.debug(
                        "Skipping unsupported Enki device type %s (%s)",
                        device_type,
                        item.get("title", {}).get("label"),
                    )
                    continue

                devices.append(
                    EnkiDevice(
                        home_id=home_id,
                        device_id=device_id,
                        node_id=node_id,
                        device_name=item["title"]["label"],
                        device_type=device_type,
                        is_enabled=item["isEnabled"],
                        state=item["state"],
                        capabilities=device_info.get("capabilities", []),
                        possible_values=device_info.get("possibleValues", {}),
                        last_reported_value={**node_info, **last_reported},
                    )
                )
        return devices

    async def _get_node(self, home_id: str, node_id: str) -> dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-node-agg-prod/v1/nodes/{node_id}",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_NODE_API_KEY,
                    "homeId": home_id,
                }
            ),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"get_node failed: HTTP {response.status}")
            return await response.json()

    async def _get_device_info_safe(self, device_id: str) -> dict[str, Any]:
        """Referentiel metadata; ESDK fan nodes may return 404."""
        session = await self._get_session()
        async with session.get(
            (
                f"{ENKI_BASE_URL}/api-enki-referentiel-agg-prod/v1/devices/"
                f"{device_id}?version={REFERENTIEL_VERSION}"
            ),
            headers=self._auth_headers({"X-Gateway-APIKey": ENKI_REFERENTIEL_API_KEY}),
        ) as response:
            if response.status == 404:
                return {}
            if response.status != 200:
                raise EnkiConnectionError(f"get_device_info failed: HTTP {response.status}")
            return await response.json()

    async def _get_fan_full_state(self, home_id: str, node_id: str) -> dict[str, Any]:
        speed = await self._get_fan_speed(home_id, node_id)
        mode = await self._get_airflow_mode(home_id, node_id)
        light_state = await self._get_light_state(home_id, node_id)
        last_reported = light_state.get("lastReportedValue", {})
        light_power = last_reported.get("power", "OFF")
        try:
            light_power = await self._get_power_state(home_id, node_id, LIGHT_ENDPOINT)
        except EnkiConnectionError as err:
            LOGGER.warning(
                "Power state for fan %s unavailable, using lighting API fallback: %s",
                node_id,
                err,
            )
        return {
            "fan_speed": speed,
            "airflow_mode": mode,
            "light_power": light_power,
            "brightness": last_reported.get("brightness"),
            "colorTemperature": last_reported.get("colorTemperature"),
            "power": last_reported.get("power"),
        }

    async def _get_power_state(self, home_id: str, node_id: str, endpoint: int) -> str:
        session = await self._get_session()
        async with session.get(
            (
                f"{ENKI_BASE_URL}/api-enki-power-prod/v1/power/{node_id}/"
                f"check-electrical-power?endpoints={endpoint}"
            ),
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_POWER_API_KEY,
                    "homeId": home_id,
                }
            ),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"check-electrical-power failed: HTTP {response.status}")
            data = await response.json()
            return normalize_power_state(data.get("lastReportedValue"), endpoint)

    async def _get_fan_speed(self, home_id: str, node_id: str) -> int:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/check-fan-speed",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_AIRFLOW_API_KEY,
                    "homeId": home_id,
                }
            ),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"check-fan-speed failed: HTTP {response.status}")
            data = await response.json()
            return data["lastReportedValue"]

    async def _get_airflow_mode(self, home_id: str, node_id: str) -> str:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/check-airflow-mode",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_AIRFLOW_API_KEY,
                    "homeId": home_id,
                }
            ),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"check-airflow-mode failed: HTTP {response.status}")
            data = await response.json()
            return data["lastReportedValue"]

    async def async_set_fan_speed(self, home_id: str, node_id: str, speed: int) -> None:
        """Set fan speed (0 = off, 1–6 = levels)."""
        await self._ensure_token()
        session = await self._get_session()
        async with session.post(
            f"{ENKI_BASE_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/change-fan-speed",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_AIRFLOW_API_KEY,
                    "homeId": home_id,
                }
            ),
            json={"value": speed},
        ) as response:
            if response.status != 202:
                raise EnkiConnectionError(f"change-fan-speed failed: HTTP {response.status}")

    async def async_set_light_power(self, home_id: str, node_id: str, on: bool) -> None:
        await self._ensure_token()
        await self._switch_power(home_id, node_id, LIGHT_ENDPOINT, "ON" if on else "OFF")

    async def _switch_power(
        self,
        home_id: str,
        node_id: str,
        endpoint: int,
        value: str,
    ) -> None:
        session = await self._get_session()
        async with session.post(
            (
                f"{ENKI_BASE_URL}/api-enki-power-prod/v1/power/{node_id}/"
                f"switch-electrical-power?endpoints={endpoint}"
            ),
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_POWER_API_KEY,
                    "homeId": home_id,
                }
            ),
            json={"value": value},
        ) as response:
            if response.status != 202:
                raise EnkiConnectionError(f"switch-electrical-power failed: HTTP {response.status}")

    async def _get_light_state(self, home_id: str, node_id: str) -> dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-lighting-prod/v1/lighting/{node_id}/check-light-state",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_LIGHTS_API_KEY,
                    "homeId": home_id,
                }
            ),
        ) as response:
            if response.status != 200:
                raise EnkiConnectionError(f"check-light-state failed: HTTP {response.status}")
            return await response.json()

    async def _get_light_state_payload(self, home_id: str, node_id: str) -> dict[str, Any]:
        state = await self._get_light_state(home_id, node_id)
        return state.get("lastReportedValue", {})

    async def async_change_light_state(
        self,
        home_id: str,
        node_id: str,
        parameter: str,
        value: Any,
        *,
        fan_light_kit: bool = False,
    ) -> None:
        await self._ensure_token()
        current = await self._get_light_state(home_id, node_id)
        payload = dict(current.get("lastReportedValue", {}))
        if fan_light_kit:
            # ESDK fan: relay on/off uses api-enki-power-prod; lighting API keeps power ON.
            payload["power"] = "ON"
        payload[parameter] = value
        session = await self._get_session()
        async with session.post(
            f"{ENKI_BASE_URL}/api-enki-lighting-prod/v1/lighting/{node_id}/change-light-state",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_LIGHTS_API_KEY,
                    "homeId": home_id,
                }
            ),
            json=payload,
        ) as response:
            if response.status != 202:
                raise EnkiConnectionError(f"change-light-state failed: HTTP {response.status}")
