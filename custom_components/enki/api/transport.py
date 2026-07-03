"""Thin HTTP transport for Enki micro-service APIs."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from ..const import ENKI_BASE_URL, ENKI_USER_AGENT, LOGGER, REFERENTIEL_VERSION
from ..exceptions import EnkiApiNotFoundError, EnkiConnectionError
from ..lib.capability_path import capability_to_path_segment
from ..lib.conversion import is_command_success_status
from .auth import EnkiAuthSession
from .gateway_keys import GatewayKeyStore
from .gateway_registry import OPTIONAL_KEY_TRANSPORT_IDS, WIRED_PATH_PREFIXES


class EnkiHttpClient:
    """Authenticated requests against Enki cloud micro-services.

    Each Enki domain (lighting, airflow, power, …) uses a separate API key
    and sometimes a ``homeId`` header — this class centralises that wiring.
    """

    _ROLLING_PATH_PREFIX = WIRED_PATH_PREFIXES["motorization"]

    def __init__(
        self,
        auth: EnkiAuthSession,
        session: aiohttp.ClientSession,
        *,
        key_store: GatewayKeyStore | None = None,
    ) -> None:
        self._auth = auth
        self._session = session
        self._key_store = key_store or GatewayKeyStore()

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def key_store(self) -> GatewayKeyStore:
        return self._key_store

    async def ensure_token(self) -> None:
        await self._auth.ensure_valid(self._session)

    def _service_api_key(self, service: str) -> str | None:
        api_key = self._key_store.get_transport_key(service)
        if api_key:
            return api_key
        if service in OPTIONAL_KEY_TRANSPORT_IDS:
            return None
        return api_key

    def _headers(self, service: str, home_id: str | None = None) -> dict[str, str]:
        extra: dict[str, str] = {
            "User-Agent": ENKI_USER_AGENT,
            "Accept": "application/json",
            "X-Correlation-Id": f"iOS_{uuid.uuid4().hex.upper()}",
        }
        api_key = self._service_api_key(service)
        if api_key:
            extra["X-Gateway-APIKey"] = api_key
        if home_id is not None:
            extra["homeId"] = home_id
        return self._auth.auth_headers(extra)

    async def _reauthenticate(self) -> None:
        self._auth.invalidate()
        await self._auth.connect(self._session)

    async def _with_auth_retry(
        self,
        request: Callable[[], Awaitable[aiohttp.ClientResponse]],
    ) -> aiohttp.ClientResponse:
        """Run one HTTP call; on 401 invalidate the session and retry once."""
        await self.ensure_token()
        response = await request()
        if response.status != 401:
            return response
        LOGGER.warning("Enki API returned 401, re-authenticating and retrying once")
        await response.release()
        await self._reauthenticate()
        return await request()

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
        url = f"{ENKI_BASE_URL}{path}"

        async def _get() -> aiohttp.ClientResponse:
            return await self._session.get(
                url,
                headers=self._headers(service, home_id),
                params=params,
            )

        response = await self._with_auth_retry(_get)
        async with response:
            if response.status == 404 and not_found_ok:
                return {}
            if response.status == 404:
                raise EnkiApiNotFoundError(f"GET {path} not found", status=404)
            if response.status != 200:
                raise EnkiConnectionError(
                    f"GET {path} failed: HTTP {response.status}",
                    status=response.status,
                    service=service,
                )
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
        url = f"{ENKI_BASE_URL}{path}"

        async def _post() -> aiohttp.ClientResponse:
            return await self._session.post(
                url,
                headers=self._headers(service, home_id),
                params=params,
                json=json,
            )

        response = await self._with_auth_retry(_post)
        async with response:
            if response.status == 404 and not_found_ok:
                raise EnkiApiNotFoundError(f"POST {path} not found", status=404)
            if not is_command_success_status(response.status):
                raise EnkiConnectionError(
                    f"POST {path} failed: HTTP {response.status}",
                    status=response.status,
                    service=service,
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
        if not self._service_api_key("motorization"):
            raise EnkiConnectionError(
                "Motorization API key is not configured (beta shutters). "
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md.",
                service="motorization",
            )
        return await self.get_json(
            "motorization",
            f"{self._ROLLING_PATH_PREFIX}/{node_id}/{action}",
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
        if not self._service_api_key("motorization"):
            raise EnkiConnectionError(
                "Motorization API key is not configured (beta shutters). "
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md.",
                service="motorization",
            )
        await self.post_command(
            "motorization",
            f"{self._ROLLING_PATH_PREFIX}/{node_id}/{action}",
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
        prefix = WIRED_PATH_PREFIXES[service]
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
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md.",
                service=service,
            )
        prefix = WIRED_PATH_PREFIXES[service]
        action = capability_to_path_segment(capability)
        await self.post_command(
            service,
            f"{prefix}/{node_id}/{action}",
            home_id=home_id,
            json={"value": value},
        )

    async def get_instant_consumption(self, home_id: str, node_id: str) -> dict[str, Any]:
        """Instant electrical consumption (Edisio / api-enki-consumption-prod)."""
        if not self._service_api_key("consumption"):
            return {}
        prefix = WIRED_PATH_PREFIXES["consumption"]
        return await self.get_json(
            "consumption",
            f"{prefix}/{node_id}/check-instant-consumption",
            params={"homeId": home_id},
            not_found_ok=True,
        )

    async def list_scenarios(self, home_id: str) -> list[dict[str, Any]]:
        """List Enki scenarios for one home (homeId query param, APK rnl.h)."""
        if not self._service_api_key("scenario"):
            return []
        prefix = WIRED_PATH_PREFIXES["scenario"]
        data = await self.get_json(
            "scenario",
            prefix,
            params={"homeId": home_id},
            not_found_ok=True,
        )
        items = data.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []

    async def activate_scenario(self, home_id: str, scenario_id: str) -> None:
        """Run one Enki scenario (homeId header, APK rnl.a)."""
        if not self._service_api_key("scenario"):
            raise EnkiConnectionError(
                "Scenario API key is not configured. "
                "Capture X-Gateway-APIKey from the Enki app — see docs/API.md.",
                service="scenario",
            )
        prefix = WIRED_PATH_PREFIXES["scenario"]
        await self.post_command(
            "scenario",
            f"{prefix}/{scenario_id}/activate",
            home_id=home_id,
        )
