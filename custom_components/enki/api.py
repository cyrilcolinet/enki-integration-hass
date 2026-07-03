"""Enki cloud API client (Leroy Merlin / Adeo)."""

from __future__ import annotations

import time
from typing import Any

import aiohttp

from .capabilities import (
    is_fan_device,
    is_inverter_device,
    parse_bff_power,
    supports_airflow_mode,
    supports_electrical_power,
    supports_fan_speed,
    supports_light_state,
)
from .const import (
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
    LOGGER,
    REFERENTIEL_VERSION,
)
from .device_profile import build_discovery_record, integration_supports_device
from .exceptions import EnkiApiNotFoundError, EnkiAuthError, EnkiConnectionError
from .helpers import (
    direction_to_enki_rotation,
    enki_rotation_to_direction,
    is_command_success_status,
    merge_light_state_payload,
    normalize_power_state,
)
from .models import EnkiDevice, EnkiDiscoveryRecord


class EnkiAPI:
    """Async client for the unofficial Enki REST API."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_type = "Bearer"
        self._token_expires_at = 0.0
        self._session: aiohttp.ClientSession | None = None
        self._discovery_records: list[EnkiDiscoveryRecord] = []

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
        if self._refresh_token:
            try:
                await self._refresh_access_token()
                return
            except EnkiAuthError:
                LOGGER.debug("Refresh token rejected, falling back to password grant")
        await self.async_connect()

    async def _refresh_access_token(self) -> None:
        """Renew the access token without sending the account password again."""
        if not self._refresh_token:
            raise EnkiAuthError("No refresh token available")
        session = await self._get_session()
        try:
            async with session.post(
                ENKI_OIDC_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": "enki-front",
                },
            ) as response:
                if response.status != 200:
                    raise EnkiAuthError(f"Token refresh failed: HTTP {response.status}")
                payload = await response.json()
        except aiohttp.ClientError as err:
            raise EnkiConnectionError(f"Cannot reach Enki auth: {err}") from err

        self._access_token = payload["access_token"]
        self._token_type = payload.get("token_type", "Bearer")
        self._token_expires_at = time.time() + payload["expires_in"]
        if refreshed := payload.get("refresh_token"):
            self._refresh_token = refreshed
        LOGGER.debug("Enki token refreshed, expires in %ss", payload["expires_in"])

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
        self._refresh_token = payload.get("refresh_token")
        self._token_type = payload.get("token_type", "Bearer")
        self._token_expires_at = time.time() + payload["expires_in"]
        LOGGER.debug("Enki session established, expires in %ss", payload["expires_in"])

    async def async_get_devices(self) -> list[EnkiDevice]:
        """Discover all nodes across every home on the account."""
        await self._ensure_token()
        homes = await self._get_homes()
        devices: list[EnkiDevice] = []
        self._discovery_records = []
        for home_id in homes:
            home_devices, records = await self._get_devices_for_home(home_id)
            devices.extend(home_devices)
            self._discovery_records.extend(records)
        return devices

    @property
    def discovery_records(self) -> list[EnkiDiscoveryRecord]:
        return list(self._discovery_records)

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

    async def _get_devices_for_home(
        self,
        home_id: str,
    ) -> tuple[list[EnkiDevice], list[EnkiDiscoveryRecord]]:
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
        records: list[EnkiDiscoveryRecord] = []
        for section in dashboard.get("sections", []):
            for item in section.get("items", []):
                metadata = item.get("metadata", {})
                if "nodeId" not in metadata:
                    continue

                node_id = metadata["nodeId"]
                device_id = metadata["deviceId"]
                bff_type = metadata.get("deviceType", "")
                main_change_capability = metadata.get("mainChangeCapability") or {}
                main_change_endpoints = [
                    endpoint.get("id")
                    for endpoint in main_change_capability.get("endpoints", [])
                    if endpoint.get("id") is not None
                ]

                node_info = await self._get_node(home_id, node_id)
                device_info = await self._get_device_info_safe(device_id)
                device_type = device_info.get("type") or bff_type
                capabilities = device_info.get("capabilities", [])
                possible_values = device_info.get("possibleValues", {})
                power_production = parse_bff_power(item.get("description"))

                probe_device = EnkiDevice(
                    home_id=home_id,
                    device_id=device_id,
                    node_id=node_id,
                    device_name=item["title"]["label"],
                    device_type=device_type,
                    is_enabled=item["isEnabled"],
                    state=item["state"],
                    capabilities=capabilities,
                    possible_values=possible_values,
                    bff_device_type=bff_type,
                    main_change_capability_id=metadata.get("mainChangeCapabilityId"),
                    main_change_capability_endpoints=main_change_endpoints,
                    power_production=power_production,
                )
                supported = integration_supports_device(probe_device)

                manufacturer = (
                    node_info.get("manufacturerId")
                    or device_info.get("manufacturerId")
                    or device_info.get("manufacturer")
                )
                model = node_info.get("modelNumber") or device_info.get("modelNumber")
                firmware = node_info.get("version") or device_info.get("version")

                records.append(
                    build_discovery_record(
                        device_type=device_type,
                        bff_device_type=bff_type,
                        capabilities=capabilities,
                        possible_values=possible_values,
                        manufacturer=str(manufacturer) if manufacturer else None,
                        model=str(model) if model else None,
                        firmware_version=str(firmware) if firmware else None,
                        supported_by_integration=supported,
                    )
                )

                last_reported: dict[str, Any] = {}
                if item["isEnabled"]:
                    last_reported = await self._refresh_device_state(
                        home_id,
                        node_id,
                        probe_device,
                        node_info,
                    )

                if not supported:
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
                        capabilities=capabilities,
                        possible_values=possible_values,
                        last_reported_value={**node_info, **last_reported},
                        bff_device_type=bff_type,
                        main_change_capability_id=metadata.get("mainChangeCapabilityId"),
                        main_change_capability_endpoints=main_change_endpoints,
                        power_production=power_production,
                    )
                )
        return devices, records

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

    async def _refresh_device_state(
        self,
        home_id: str,
        node_id: str,
        device: EnkiDevice,
        node_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Load live state based on referentiel capabilities (not only device type)."""
        caps = {cap for cap in device.capabilities if isinstance(cap, str)}
        possible = device.possible_values if isinstance(device.possible_values, dict) else {}

        if is_fan_device(device):
            return await self._get_fan_full_state(home_id, node_id)

        state: dict[str, Any] = {}

        if supports_light_state(caps, possible) or device.device_type == DEVICE_TYPE_LIGHTS:
            try:
                light_state = await self._get_light_state_payload(home_id, node_id)
                state.update(light_state)
                if light_state.get("power"):
                    state["light_power"] = light_state["power"]
            except EnkiConnectionError as err:
                LOGGER.debug("Light state skipped for node %s: %s", node_id, err)

        if supports_electrical_power(caps, possible):
            try:
                power_details = await self._get_electrical_power_details(home_id, node_id)
                state["electrical_power"] = power_details.get("lastReportedValue")
                state["electrical_endpoints"] = power_details.get("endpoints", [])
                if not state.get("power") and isinstance(state["electrical_power"], str):
                    state["power"] = state["electrical_power"]
            except EnkiConnectionError as err:
                LOGGER.debug("Electrical power skipped for node %s: %s", node_id, err)

        if supports_fan_speed(caps, possible):
            try:
                state["fan_speed"] = await self._get_fan_speed(home_id, node_id)
            except EnkiConnectionError as err:
                LOGGER.debug("Fan speed skipped for node %s: %s", node_id, err)

        if supports_airflow_mode(caps, possible):
            try:
                state["airflow_mode"] = await self._get_airflow_mode(home_id, node_id)
            except EnkiConnectionError as err:
                LOGGER.debug("Airflow mode skipped for node %s: %s", node_id, err)

        if is_inverter_device(device):
            state["power_production"] = device.power_production

        return state

    async def _get_electrical_power_details(
        self,
        home_id: str,
        node_id: str,
    ) -> dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-power-prod/v1/power/{node_id}/check-electrical-power",
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_POWER_API_KEY,
                    "homeId": home_id,
                }
            ),
        ) as response:
            if response.status == 404:
                return {}
            if response.status != 200:
                raise EnkiConnectionError(f"check-electrical-power failed: HTTP {response.status}")
            return await response.json()

    async def async_switch_electrical_power(
        self,
        home_id: str,
        node_id: str,
        value: str,
    ) -> None:
        """Switch global electrical power (sockets, outlets without lighting API)."""
        await self._ensure_token()
        session = await self._get_session()
        async with session.post(
            (f"{ENKI_BASE_URL}/api-enki-power-prod/v1/power/{node_id}/switch-electrical-power"),
            headers=self._auth_headers(
                {
                    "X-Gateway-APIKey": ENKI_POWER_API_KEY,
                    "homeId": home_id,
                }
            ),
            json={"value": value},
        ) as response:
            if not is_command_success_status(response.status):
                raise EnkiConnectionError(f"switch-electrical-power failed: HTTP {response.status}")

    async def _get_fan_full_state(self, home_id: str, node_id: str) -> dict[str, Any]:
        speed = await self._get_fan_speed(home_id, node_id)
        mode = await self._get_airflow_mode(home_id, node_id)
        rotation, rotation_supported = await self._get_fan_rotation(home_id, node_id)
        light_state = await self._get_light_state(home_id, node_id)
        last_reported = light_state.get("lastReportedValue", {})
        # ESDK fan kit on/off is reported by api-enki-lighting-prod (`power`), not power-prod.
        light_power = last_reported.get("power", "OFF")
        state: dict[str, Any] = {
            "fan_speed": speed,
            "airflow_mode": mode,
            "airflow_rotation": rotation,
            "airflow_rotation_supported": rotation_supported,
            "light_power": light_power,
            "brightness": last_reported.get("brightness"),
            "colorTemperature": last_reported.get("colorTemperature"),
            "power": last_reported.get("power"),
        }
        try:
            power_details = await self._get_electrical_power_details(home_id, node_id)
            state["electrical_power"] = power_details.get("lastReportedValue")
            state["electrical_endpoints"] = power_details.get("endpoints", [])
        except EnkiConnectionError as err:
            LOGGER.debug("Electrical power skipped for fan node %s: %s", node_id, err)
        return state

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

    def _airflow_headers(self, home_id: str) -> dict[str, str]:
        return self._auth_headers(
            {
                "X-Gateway-APIKey": ENKI_AIRFLOW_API_KEY,
                "homeId": home_id,
            }
        )

    async def _airflow_get(
        self,
        home_id: str,
        node_id: str,
        action: str,
    ) -> dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{ENKI_BASE_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/{action}",
            headers=self._airflow_headers(home_id),
        ) as response:
            if response.status == 404:
                raise EnkiApiNotFoundError(f"{action} not found", status=404)
            if response.status != 200:
                raise EnkiConnectionError(
                    f"{action} failed: HTTP {response.status}",
                    status=response.status,
                )
            return await response.json()

    async def _airflow_post(
        self,
        home_id: str,
        node_id: str,
        action: str,
        value: Any,
    ) -> None:
        session = await self._get_session()
        async with session.post(
            f"{ENKI_BASE_URL}/api-enki-airflow-prod/v1/airflow/{node_id}/{action}",
            headers=self._airflow_headers(home_id),
            json={"value": value},
        ) as response:
            if response.status == 404:
                raise EnkiApiNotFoundError(f"{action} not found", status=404)
            if response.status != 202 and response.status != 204:
                raise EnkiConnectionError(
                    f"{action} failed: HTTP {response.status}",
                    status=response.status,
                )

    async def _get_fan_speed(self, home_id: str, node_id: str) -> int:
        data = await self._airflow_get(home_id, node_id, "check-fan-speed")
        return data["lastReportedValue"]

    async def _get_airflow_mode(self, home_id: str, node_id: str) -> str:
        data = await self._airflow_get(home_id, node_id, "check-airflow-mode")
        return data["lastReportedValue"]

    async def _try_airflow_get(
        self,
        home_id: str,
        node_id: str,
        action: str,
    ) -> dict[str, Any] | None:
        """Best-effort airflow read; never fails discovery (404/500 on optional probes)."""
        try:
            return await self._airflow_get(home_id, node_id, action)
        except (EnkiApiNotFoundError, EnkiConnectionError) as err:
            LOGGER.debug(
                "Optional airflow %s for node %s skipped: %s",
                action,
                node_id,
                err,
            )
            return None

    async def _get_fan_rotation(
        self,
        home_id: str,
        node_id: str,
    ) -> tuple[str | None, bool]:
        """Return (HA direction, supported) via check-fan-rotation-direction."""
        data = await self._try_airflow_get(home_id, node_id, "check-fan-rotation-direction")
        if data is None:
            return None, False
        direction = enki_rotation_to_direction(data.get("lastReportedValue"))
        return direction, True

    async def async_set_fan_rotation(
        self,
        home_id: str,
        node_id: str,
        direction: str,
    ) -> None:
        """Set blade rotation via change-fan-rotation-direction."""
        await self._ensure_token()
        enki_value = direction_to_enki_rotation(direction)
        await self._airflow_post(home_id, node_id, "change-fan-rotation-direction", enki_value)

    async def async_set_airflow_mode(self, home_id: str, node_id: str, mode: str) -> None:
        """Set ventilation mode (MANUAL / BREEZE)."""
        await self._ensure_token()
        await self._airflow_post(home_id, node_id, "change-airflow-mode", mode)

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
            if response.status != 202 and response.status != 204:
                raise EnkiConnectionError(f"change-fan-speed failed: HTTP {response.status}")

    async def async_set_light_power(self, home_id: str, node_id: str, on: bool) -> None:
        """Turn the ESDK fan light kit on or off (lighting API)."""
        await self.async_change_light_state(
            home_id,
            node_id,
            {"power": "ON" if on else "OFF"},
        )

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
            if not is_command_success_status(response.status):
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
        changes: dict[str, Any],
    ) -> None:
        """Apply one or more lighting fields in a single change-light-state call."""
        await self._ensure_token()
        current = await self._get_light_state(home_id, node_id)
        payload = merge_light_state_payload(
            current.get("lastReportedValue", {}),
            changes,
        )
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
            if not is_command_success_status(response.status):
                raise EnkiConnectionError(f"change-light-state failed: HTTP {response.status}")

    async def async_change_light_state_field(
        self,
        home_id: str,
        node_id: str,
        parameter: str,
        value: Any,
    ) -> None:
        """Backward-compatible wrapper for single-field lighting updates."""
        await self.async_change_light_state(home_id, node_id, {parameter: value})
