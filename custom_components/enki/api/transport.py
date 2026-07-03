"""Thin HTTP transport for Enki micro-service APIs."""

from __future__ import annotations

from typing import Any

import aiohttp

from ..const import (
    ENKI_ACCESS_MOTORIZATION_API_KEY,
    ENKI_AIRFLOW_API_KEY,
    ENKI_BASE_URL,
    ENKI_BATTERY_HEALTH_API_KEY,
    ENKI_BFF_API_KEY,
    ENKI_CONTACT_SENSOR_API_KEY,
    ENKI_HEATING_API_KEY,
    ENKI_HOME_API_KEY,
    ENKI_LIGHTS_API_KEY,
    ENKI_NODE_API_KEY,
    ENKI_POWER_API_KEY,
    ENKI_PRESENCE_DETECTOR_API_KEY,
    ENKI_REFERENTIEL_API_KEY,
    ENKI_SIREN_API_KEY,
    ENKI_TEMPERATURE_HUMIDITY_API_KEY,
    ENKI_WATER_SENSOR_API_KEY,
    LOGGER,
    REFERENTIEL_VERSION,
)
from ..exceptions import EnkiApiNotFoundError, EnkiConnectionError
from ..lib.capability_path import capability_to_path_segment
from ..lib.conversion import is_command_success_status
from .auth import EnkiAuthSession


class EnkiHttpClient:
    """Authenticated requests against Enki cloud micro-services.

    Each Enki domain (lighting, airflow, power, …) uses a separate API key
    and sometimes a ``homeId`` header — this class centralises that wiring.
    """

    _API_KEYS = {
        "home": ENKI_HOME_API_KEY,
        "bff": ENKI_BFF_API_KEY,
        "node": ENKI_NODE_API_KEY,
        "referentiel": ENKI_REFERENTIEL_API_KEY,
        "lighting": ENKI_LIGHTS_API_KEY,
        "airflow": ENKI_AIRFLOW_API_KEY,
        "power": ENKI_POWER_API_KEY,
        "motorization": ENKI_ACCESS_MOTORIZATION_API_KEY,
        "temperature_humidity": ENKI_TEMPERATURE_HUMIDITY_API_KEY,
        "battery_health": ENKI_BATTERY_HEALTH_API_KEY,
        "presence_detector": ENKI_PRESENCE_DETECTOR_API_KEY,
        "contact_sensor": ENKI_CONTACT_SENSOR_API_KEY,
        "siren": ENKI_SIREN_API_KEY,
        "heating": ENKI_HEATING_API_KEY,
        "water_sensor": ENKI_WATER_SENSOR_API_KEY,
    }

    _SERVICE_PATH_PREFIX = {
        "temperature_humidity": "/api-enki-temperature-humidity-sensor-prod/v1/sensors",
        "battery_health": "/api-enki-battery-health-prod/v1/sensors",
        "presence_detector": "/api-enki-presence-detector-prod/v1/sensors",
        "contact_sensor": "/api-enki-contact-sensor-prod/v1/sensors",
        "siren": "/api-enki-siren-prod/v1/siren",
        "heating": "/api-enki-heating-prod/v1/heating",
        "water_sensor": "/api-enki-water-sensor-prod/v1/sensors",
    }

    _OPTIONAL_API_KEY_SERVICES = frozenset({"heating", "water_sensor"})

    def __init__(self, auth: EnkiAuthSession, session: aiohttp.ClientSession) -> None:
        self._auth = auth
        self._session = session

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    async def ensure_token(self) -> None:
        await self._auth.ensure_valid(self._session)

    def _service_api_key(self, service: str) -> str | None:
        api_key = self._API_KEYS.get(service, "")
        if api_key:
            return api_key
        if service in self._OPTIONAL_API_KEY_SERVICES:
            return None
        return api_key

    def _headers(self, service: str, home_id: str | None = None) -> dict[str, str]:
        extra: dict[str, str] = {}
        api_key = self._service_api_key(service)
        if api_key:
            extra["X-Gateway-APIKey"] = api_key
        if home_id is not None:
            extra["homeId"] = home_id
        return self._auth.auth_headers(extra)

    async def get_json(
        self,
        service: str,
        path: str,
        *,
        home_id: str | None = None,
        params: dict[str, Any] | None = None,
        not_found_ok: bool = False,
    ) -> dict[str, Any]:
        """GET returning parsed JSON; raises on unexpected status."""
        await self.ensure_token()
        url = f"{ENKI_BASE_URL}{path}"
        async with self._session.get(
            url,
            headers=self._headers(service, home_id),
            params=params,
        ) as response:
            if response.status == 404 and not_found_ok:
                return {}
            if response.status == 404:
                raise EnkiApiNotFoundError(f"GET {path} not found", status=404)
            if response.status != 200:
                raise EnkiConnectionError(f"GET {path} failed: HTTP {response.status}")
            payload = await response.json()
            return payload if isinstance(payload, dict) else {}

    async def post_command(
        self,
        service: str,
        path: str,
        *,
        home_id: str | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        not_found_ok: bool = False,
    ) -> None:
        """POST a command endpoint; accepts HTTP 202/204 as success."""
        await self.ensure_token()
        url = f"{ENKI_BASE_URL}{path}"
        async with self._session.post(
            url,
            headers=self._headers(service, home_id),
            params=params,
            json=json,
        ) as response:
            if response.status == 404 and not_found_ok:
                raise EnkiApiNotFoundError(f"POST {path} not found", status=404)
            if not is_command_success_status(response.status):
                raise EnkiConnectionError(
                    f"POST {path} failed: HTTP {response.status}",
                    status=response.status,
                )

    async def get_homes(self) -> list[str]:
        data = await self.get_json("home", "/api-enki-home-prod/v1/homes")
        return [home["id"] for home in data.get("items", [])]

    async def get_dashboard(self, home_id: str) -> dict[str, Any]:
        return await self.get_json(
            "bff",
            f"/api-enki-mobile-bff-prod/v1/dashboard/homes/{home_id}?hasGroups=true",
        )

    async def get_node(self, home_id: str, node_id: str) -> dict[str, Any]:
        return await self.get_json(
            "node",
            f"/api-enki-node-agg-prod/v1/nodes/{node_id}",
            home_id=home_id,
        )

    async def get_referentiel_device(self, device_id: str) -> dict[str, Any]:
        """Referentiel metadata; ESDK fan nodes may return 404."""
        return await self.get_json(
            "referentiel",
            (
                f"/api-enki-referentiel-agg-prod/v1/devices/{device_id}"
                f"?version={REFERENTIEL_VERSION}"
            ),
            not_found_ok=True,
        )

    # --- domain-specific shortcuts -------------------------------------------

    async def get_light_state(self, home_id: str, node_id: str) -> dict[str, Any]:
        return await self.get_json(
            "lighting",
            f"/api-enki-lighting-prod/v1/lighting/{node_id}/check-light-state",
            home_id=home_id,
        )

    async def change_light_state(
        self,
        home_id: str,
        node_id: str,
        payload: dict[str, Any],
    ) -> None:
        await self.post_command(
            "lighting",
            f"/api-enki-lighting-prod/v1/lighting/{node_id}/change-light-state",
            home_id=home_id,
            json=payload,
        )

    async def get_electrical_power(self, home_id: str, node_id: str) -> dict[str, Any]:
        return await self.get_json(
            "power",
            f"/api-enki-power-prod/v1/power/{node_id}/check-electrical-power",
            home_id=home_id,
            not_found_ok=True,
        )

    async def switch_electrical_power(
        self,
        home_id: str,
        node_id: str,
        value: str,
        *,
        endpoint: int | None = None,
    ) -> None:
        params = {"endpoints": endpoint} if endpoint is not None else None
        await self.post_command(
            "power",
            f"/api-enki-power-prod/v1/power/{node_id}/switch-electrical-power",
            home_id=home_id,
            params=params,
            json={"value": value},
        )

    async def airflow_get(
        self,
        home_id: str,
        node_id: str,
        action: str,
    ) -> dict[str, Any]:
        return await self.get_json(
            "airflow",
            f"/api-enki-airflow-prod/v1/airflow/{node_id}/{action}",
            home_id=home_id,
        )

    async def airflow_post(
        self,
        home_id: str,
        node_id: str,
        action: str,
        value: Any,
    ) -> None:
        await self.post_command(
            "airflow",
            f"/api-enki-airflow-prod/v1/airflow/{node_id}/{action}",
            home_id=home_id,
            json={"value": value},
        )

    async def motorization_get(
        self,
        home_id: str,
        node_id: str,
        action: str,
    ) -> dict[str, Any]:
        if not ENKI_ACCESS_MOTORIZATION_API_KEY:
            raise EnkiConnectionError(
                "Motorization API key is not configured (beta shutters). "
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md."
            )
        return await self.get_json(
            "motorization",
            f"/api-enki-access-and-motorizations-prod/v1/access-and-motorizations/{node_id}/{action}",
            home_id=home_id,
            not_found_ok=True,
        )

    async def motorization_post(
        self,
        home_id: str,
        node_id: str,
        action: str,
        value: Any,
    ) -> None:
        if not ENKI_ACCESS_MOTORIZATION_API_KEY:
            raise EnkiConnectionError(
                "Motorization API key is not configured (beta shutters). "
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md."
            )
        await self.post_command(
            "motorization",
            f"/api-enki-access-and-motorizations-prod/v1/access-and-motorizations/{node_id}/{action}",
            home_id=home_id,
            json={"value": value},
        )

    async def capability_get(
        self,
        service: str,
        home_id: str,
        node_id: str,
        capability: str,
    ) -> dict[str, Any]:
        """GET a check_* capability on a sensor or heating micro-service."""
        if not self._service_api_key(service):
            LOGGER.debug(
                "Skipping %s read for node %s — API key not configured (see docs/API.md)",
                capability,
                node_id,
            )
            return {}
        prefix = self._SERVICE_PATH_PREFIX[service]
        action = capability_to_path_segment(capability)
        return await self.get_json(
            service,
            f"{prefix}/{node_id}/{action}",
            home_id=home_id,
            not_found_ok=True,
        )

    async def capability_post(
        self,
        service: str,
        home_id: str,
        node_id: str,
        capability: str,
        value: Any,
    ) -> None:
        """POST a change_*/switch_*/activate_* capability."""
        if not self._service_api_key(service):
            raise EnkiConnectionError(
                f"Heating/water API key is not configured for {capability}. "
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md."
            )
        prefix = self._SERVICE_PATH_PREFIX[service]
        action = capability_to_path_segment(capability)
        await self.post_command(
            service,
            f"{prefix}/{node_id}/{action}",
            home_id=home_id,
            json={"value": value},
        )
