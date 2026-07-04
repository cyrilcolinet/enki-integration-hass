"""Enki cloud API client (Leroy Merlin / Adeo)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from ..const import DEVICE_TYPE_LIGHTS, LOGGER
from ..domain.capabilities import EnkiCapabilityProfile
from ..domain.models import EnkiDevice, EnkiDiscoveryRecord, EnkiScenario
from ..domain.profile import (
    build_discovery_record,
    integration_supports_device,
    profile_fingerprint,
    profile_to_export_dict,
    sanitize_poll_state,
)
from ..exceptions import EnkiApiNotFoundError, EnkiConnectionError
from ..lib.bff import parse_bff_power
from ..lib.conversion import (
    direction_to_enki_rotation,
    enki_rotation_to_direction,
    merge_light_state_payload,
    normalize_power_state,
)
from ..lib.enki_scope import device_in_enki_scope
from ..lib.shutter import normalize_shutter_position
from .auth import EnkiAuthSession
from .capability_routing import CAPABILITY_READS, CapabilityRead
from .gateway_keys import GatewayKeyStore, fetch_mobile_config
from .transport import EnkiHttpClient

_DISCOVERY_CONCURRENCY = 8


class EnkiAPI:
    """Async facade over Enki REST micro-services.

    Composes :class:`EnkiAuthSession` (OAuth) and :class:`EnkiHttpClient`
    (per-domain HTTP). Platform modules call the public ``async_*`` methods;
    discovery and state refresh stay internal.
    """

    def __init__(self, username: str, password: str) -> None:
        self._auth = EnkiAuthSession(username, password)
        self._session: aiohttp.ClientSession | None = None
        self._http: EnkiHttpClient | None = None
        self._key_store = GatewayKeyStore()
        self._discovery_records: list[EnkiDiscoveryRecord] = []
        self._referentiel_cache: dict[str, dict[str, Any]] = {}
        self._scenarios: tuple[EnkiScenario, ...] = ()
        self._node_fingerprints: dict[str, str] = {}
        self._profile_read_errors: dict[str, dict[str, str]] = {}
        self._profile_poll_state: dict[str, dict[str, Any]] = {}

    async def async_close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._http = None

    async def _ensure_token(self) -> None:
        """Ensure a valid OAuth token (refresh, then password grant)."""
        http = await self._get_http()
        await http.ensure_token()

    async def _get_http(self) -> EnkiHttpClient:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
            self._http = EnkiHttpClient(
                self._auth,
                self._session,
                key_store=self._key_store,
            )
        assert self._http is not None
        return self._http

    async def async_connect(self) -> None:
        """Authenticate with Keycloak (resource-owner password grant)."""
        http = await self._get_http()
        await self._auth.connect(http.session)

    async def async_fetch_mobile_settings(self) -> dict[str, Any]:
        """Fetch Enki app settings (maintenance flags, min app version, …)."""
        http = await self._get_http()
        try:
            payload = await fetch_mobile_config(http)
        except EnkiConnectionError as err:
            LOGGER.debug("Mobile-config settings skipped: %s", err)
            return {}
        return payload if isinstance(payload, dict) else {}

    async def async_get_devices(self) -> list[EnkiDevice]:
        """Discover all nodes across every home on the account."""
        http = await self._get_http()
        homes = await http.get_homes()
        devices: list[EnkiDevice] = []
        self._discovery_records = []
        self._node_fingerprints.clear()
        self._profile_read_errors.clear()
        self._profile_poll_state.clear()
        for home_id in homes:
            home_devices, records = await self._discover_home(http, home_id)
            devices.extend(home_devices)
            self._discovery_records.extend(records)
        return devices

    @property
    def discovery_records(self) -> list[EnkiDiscoveryRecord]:
        return list(self._discovery_records)

    def read_errors_for_fingerprint(self, fingerprint: str) -> dict[str, str]:
        """Anonymized API read failures from the last poll (no node or home ids)."""
        return dict(self._profile_read_errors.get(fingerprint, {}))

    def poll_state_for_fingerprint(self, fingerprint: str) -> dict[str, Any]:
        """Anonymized state values merged from the last poll (no node or home ids)."""
        return dict(self._profile_poll_state.get(fingerprint, {}))

    def _register_node_profile(self, node_id: str, record: EnkiDiscoveryRecord) -> None:
        export = profile_to_export_dict(record, integration_version="", ha_version="")
        self._node_fingerprints[node_id] = profile_fingerprint(export)

    def _register_poll_state(self, node_id: str, state: dict[str, Any]) -> None:
        fingerprint = self._node_fingerprints.get(node_id)
        if not fingerprint:
            return
        sanitized = sanitize_poll_state(state)
        if sanitized:
            self._profile_poll_state[fingerprint] = sanitized

    def _note_read_error(
        self,
        node_id: str,
        *,
        service: str,
        capability: str,
        err: Exception,
    ) -> None:
        fingerprint = self._node_fingerprints.get(node_id)
        if not fingerprint:
            return
        status = getattr(err, "status", None)
        label = f"HTTP {status}" if status else err.__class__.__name__
        key = f"{service}/{capability}"
        self._profile_read_errors.setdefault(fingerprint, {})[key] = label

    @property
    def scenarios(self) -> tuple[EnkiScenario, ...]:
        return self._scenarios

    async def async_refresh_scenarios(self) -> None:
        """Load scenario list for every home on the account (best-effort, atomic)."""
        http = await self._get_http()
        try:
            home_ids = await http.get_homes()
        except EnkiConnectionError as err:
            LOGGER.debug("Scenario list skipped — cannot list homes: %s", err)
            return

        if not home_ids:
            self._scenarios = ()
            return

        scenarios: list[EnkiScenario] = []
        failed = False

        async def load_home(home_id: str) -> None:
            nonlocal failed
            try:
                items = await http.list_scenarios(home_id)
            except Exception as err:  # noqa: BLE001 — one home must not break the poll
                LOGGER.debug("Scenario list skipped for home %s: %s", home_id, err)
                failed = True
                return
            for item in items:
                parsed = _parse_scenario(item, home_id)
                if parsed is not None:
                    scenarios.append(parsed)

        await asyncio.gather(*(load_home(home_id) for home_id in sorted(home_ids)))

        if failed:
            return

        self._scenarios = tuple(scenarios)

    async def _discover_home(
        self,
        http: EnkiHttpClient,
        home_id: str,
    ) -> tuple[list[EnkiDevice], list[EnkiDiscoveryRecord]]:
        dashboard = await http.get_dashboard(home_id)
        items = [
            item for section in dashboard.get("sections", []) for item in section.get("items", [])
        ]
        semaphore = asyncio.Semaphore(_DISCOVERY_CONCURRENCY)

        async def discover_item(
            item: dict[str, Any],
        ) -> tuple[EnkiDevice | None, EnkiDiscoveryRecord | None]:
            async with semaphore:
                return await self._discover_dashboard_item(http, home_id, item)

        results = await asyncio.gather(*(discover_item(item) for item in items))

        devices: list[EnkiDevice] = []
        records: list[EnkiDiscoveryRecord] = []
        for device, record in results:
            if record is not None:
                records.append(record)
            if device is not None:
                devices.append(device)
        return devices, records

    async def _get_referentiel_device(
        self,
        http: EnkiHttpClient,
        device_id: str,
    ) -> dict[str, Any]:
        if device_id not in self._referentiel_cache:
            self._referentiel_cache[device_id] = await http.get_referentiel_device(device_id)
        return self._referentiel_cache[device_id]

    async def _discover_dashboard_item(
        self,
        http: EnkiHttpClient,
        home_id: str,
        item: dict[str, Any],
    ) -> tuple[EnkiDevice | None, EnkiDiscoveryRecord | None]:
        metadata = item.get("metadata", {})
        if "nodeId" not in metadata:
            return None, None

        node_id = metadata["nodeId"]
        device_id = metadata["deviceId"]
        bff_type = metadata.get("deviceType", "")
        main_change_capability = metadata.get("mainChangeCapability") or {}
        main_change_endpoints = [
            endpoint.get("id")
            for endpoint in main_change_capability.get("endpoints", [])
            if endpoint.get("id") is not None
        ]

        node_info = await http.get_node(home_id, node_id)
        device_info = await self._get_referentiel_device(http, device_id)
        device_type = device_info.get("type") or bff_type
        capabilities = device_info.get("capabilities", [])
        possible_values = device_info.get("possibleValues", {})
        power_production = parse_bff_power(item.get("description"))

        title = item.get("title") or {}
        device_name = title.get("label") or node_id

        skeleton = EnkiDevice(
            home_id=home_id,
            device_id=device_id,
            node_id=node_id,
            device_name=device_name,
            device_type=device_type,
            is_enabled=item.get("isEnabled", True),
            state=item.get("state", "ACTIVE"),
            capabilities=capabilities,
            possible_values=possible_values,
            bff_device_type=bff_type,
            main_change_capability_id=metadata.get("mainChangeCapabilityId"),
            main_change_capability_endpoints=main_change_endpoints,
            power_production=power_production,
        )
        manufacturer = (
            node_info.get("manufacturerId")
            or device_info.get("manufacturerId")
            or device_info.get("manufacturer")
        )
        manufacturer_str = str(manufacturer) if manufacturer else None

        if not device_in_enki_scope(manufacturer=manufacturer_str, device_type=device_type):
            LOGGER.debug(
                "Skipping non-Enki device %s (manufacturer=%s, type=%s) — "
                "third-party Zigbee belongs in Zigbee2MQTT or ZHA",
                device_name,
                manufacturer_str or "unknown",
                device_type,
            )
            supported = False
        else:
            supported = integration_supports_device(skeleton)
        model = node_info.get("modelNumber") or device_info.get("modelNumber")
        firmware = node_info.get("version") or device_info.get("version")

        record = build_discovery_record(
            device_type=device_type,
            bff_device_type=bff_type,
            capabilities=capabilities,
            possible_values=possible_values,
            manufacturer=manufacturer_str,
            model=str(model) if model else None,
            firmware_version=str(firmware) if firmware else None,
            supported_by_integration=supported,
        )
        self._register_node_profile(node_id, record)

        last_reported: dict[str, Any] = {}
        if item.get("isEnabled", True):
            last_reported = await self._refresh_device_state(http, skeleton, node_info)

        self._register_poll_state(node_id, {**node_info, **last_reported})

        if not supported:
            LOGGER.debug(
                "Skipping unsupported Enki device type %s (%s)",
                device_type,
                item.get("title", {}).get("label"),
            )
            return None, record

        return (
            EnkiDevice(
                home_id=home_id,
                device_id=device_id,
                node_id=node_id,
                device_name=device_name,
                device_type=device_type,
                is_enabled=item.get("isEnabled", True),
                state=item.get("state", "ACTIVE"),
                capabilities=capabilities,
                possible_values=possible_values,
                last_reported_value={**node_info, **last_reported},
                bff_device_type=bff_type,
                main_change_capability_id=metadata.get("mainChangeCapabilityId"),
                main_change_capability_endpoints=main_change_endpoints,
                power_production=power_production,
            ),
            record,
        )

    async def _refresh_device_state(
        self,
        http: EnkiHttpClient,
        device: EnkiDevice,
        node_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Load live state based on referentiel capabilities (not only device type)."""
        profile = device.profile
        home_id = device.home_id
        node_id = device.node_id

        if profile.is_fan:
            return await self._read_fan_state(http, home_id, node_id)

        if profile.is_cover:
            return await self._read_shutter_state(http, device)

        state: dict[str, Any] = {}

        if profile.supports_light_state or device.device_type == DEVICE_TYPE_LIGHTS:
            try:
                light_state = await self._read_light_payload(http, home_id, node_id)
                state.update(light_state)
                if light_state.get("power"):
                    state["light_power"] = light_state["power"]
            except EnkiConnectionError as err:
                LOGGER.debug("Light state skipped for node %s: %s", node_id, err)
                self._note_read_error(
                    node_id,
                    service="lighting",
                    capability="check-light-state",
                    err=err,
                )

        if profile.supports_electrical_power:
            try:
                power_details = await http.get_electrical_power(home_id, node_id)
                state["electrical_power"] = power_details.get("lastReportedValue")
                state["electrical_endpoints"] = power_details.get("endpoints", [])
                if not state.get("power") and isinstance(state["electrical_power"], str):
                    state["power"] = state["electrical_power"]
            except EnkiConnectionError as err:
                LOGGER.debug("Electrical power skipped for node %s: %s", node_id, err)
                self._note_read_error(
                    node_id,
                    service="power",
                    capability="check-electrical-power",
                    err=err,
                )

        if profile.supports_electrical_consumption:
            try:
                consumption = await http.get_instant_consumption(home_id, node_id)
                if consumption:
                    state["electrical_consumption"] = consumption.get("lastReportedValue")
                    unit = consumption.get("unit")
                    if isinstance(unit, str):
                        state["electrical_consumption_unit"] = unit
            except EnkiConnectionError as err:
                LOGGER.debug("Electrical consumption skipped for node %s: %s", node_id, err)
                self._note_read_error(
                    node_id,
                    service="consumption",
                    capability="check-instant-consumption",
                    err=err,
                )

        if profile.supports_fan_speed:
            try:
                data = await http.airflow_get(home_id, node_id, "check-fan-speed")
                state["fan_speed"] = data["lastReportedValue"]
            except EnkiConnectionError as err:
                LOGGER.debug("Fan speed skipped for node %s: %s", node_id, err)
                self._note_read_error(
                    node_id,
                    service="airflow",
                    capability="check-fan-speed",
                    err=err,
                )

        if profile.supports_airflow_mode:
            try:
                data = await http.airflow_get(home_id, node_id, "check-airflow-mode")
                state["airflow_mode"] = data["lastReportedValue"]
            except EnkiConnectionError as err:
                LOGGER.debug("Airflow mode skipped for node %s: %s", node_id, err)
                self._note_read_error(
                    node_id,
                    service="airflow",
                    capability="check-airflow-mode",
                    err=err,
                )

        if profile.is_inverter:
            state["power_production"] = device.power_production

        await self._append_capability_states(http, home_id, node_id, profile, state)
        return state

    async def _append_capability_states(
        self,
        http: EnkiHttpClient,
        home_id: str,
        node_id: str,
        profile: EnkiCapabilityProfile,
        state: dict[str, Any],
    ) -> None:
        """Best-effort parallel reads for sensor / heating micro-services."""
        caps = profile.capabilities

        async def read_one(read: CapabilityRead) -> tuple[str, Any] | None:
            if read.capability not in caps:
                return None
            if read.skip is not None and read.skip(profile):
                return None
            try:
                data = await http.capability_get(
                    read.transport_id,
                    home_id,
                    node_id,
                    read.capability,
                )
            except EnkiConnectionError as err:
                LOGGER.debug(
                    "Capability %s skipped for node %s: %s",
                    read.capability,
                    node_id,
                    err,
                )
                self._note_read_error(
                    node_id,
                    service=read.transport_id,
                    capability=read.capability,
                    err=err,
                )
                return None
            if data and "lastReportedValue" in data:
                return read.state_key, data["lastReportedValue"]
            return None

        results = await asyncio.gather(*(read_one(read) for read in CAPABILITY_READS))
        for result in results:
            if result is not None:
                state[result[0]] = result[1]

    async def _read_fan_state(
        self,
        http: EnkiHttpClient,
        home_id: str,
        node_id: str,
    ) -> dict[str, Any]:
        state: dict[str, Any] = {}

        try:
            speed_data = await http.airflow_get(home_id, node_id, "check-fan-speed")
            if "lastReportedValue" in speed_data:
                state["fan_speed"] = speed_data["lastReportedValue"]
        except EnkiConnectionError as err:
            LOGGER.debug("Fan speed skipped for node %s: %s", node_id, err)
            self._note_read_error(
                node_id,
                service="airflow",
                capability="check-fan-speed",
                err=err,
            )

        try:
            mode_data = await http.airflow_get(home_id, node_id, "check-airflow-mode")
            if "lastReportedValue" in mode_data:
                state["airflow_mode"] = mode_data["lastReportedValue"]
        except EnkiConnectionError as err:
            LOGGER.debug("Airflow mode skipped for node %s: %s", node_id, err)
            self._note_read_error(
                node_id,
                service="airflow",
                capability="check-airflow-mode",
                err=err,
            )

        rotation, rotation_supported = await self._read_fan_rotation(http, home_id, node_id)
        state["airflow_rotation"] = rotation
        state["airflow_rotation_supported"] = rotation_supported

        try:
            light_state = await http.get_light_state(home_id, node_id)
            last_reported = light_state.get("lastReportedValue", {})
            if isinstance(last_reported, dict):
                state["light_power"] = last_reported.get("power", "OFF")
                state["brightness"] = last_reported.get("brightness")
                state["colorTemperature"] = last_reported.get("colorTemperature")
                state["power"] = last_reported.get("power")
        except EnkiConnectionError as err:
            LOGGER.debug("Fan light state skipped for node %s: %s", node_id, err)
            self._note_read_error(
                node_id,
                service="lighting",
                capability="check-light-state",
                err=err,
            )

        try:
            power_details = await http.get_electrical_power(home_id, node_id)
            state["electrical_power"] = power_details.get("lastReportedValue")
            state["electrical_endpoints"] = power_details.get("endpoints", [])
        except EnkiConnectionError as err:
            LOGGER.debug("Electrical power skipped for fan node %s: %s", node_id, err)
            self._note_read_error(
                node_id,
                service="power",
                capability="check-electrical-power",
                err=err,
            )
        return state

    async def _read_fan_rotation(
        self,
        http: EnkiHttpClient,
        home_id: str,
        node_id: str,
    ) -> tuple[str | None, bool]:
        """Best-effort rotation read; optional probes must not fail discovery."""
        try:
            data = await http.airflow_get(home_id, node_id, "check-fan-rotation-direction")
        except (EnkiApiNotFoundError, EnkiConnectionError) as err:
            LOGGER.debug(
                "Optional airflow check-fan-rotation-direction for node %s skipped: %s",
                node_id,
                err,
            )
            return None, False
        direction = enki_rotation_to_direction(data.get("lastReportedValue"))
        return direction, True

    async def _read_light_payload(
        self,
        http: EnkiHttpClient,
        home_id: str,
        node_id: str,
    ) -> dict[str, Any]:
        state = await http.get_light_state(home_id, node_id)
        return state.get("lastReportedValue", {})

    async def _read_shutter_state(
        self,
        http: EnkiHttpClient,
        device: EnkiDevice,
    ) -> dict[str, Any]:
        """Read roller shutter position/opening from api-enki-rolling-prod."""
        home_id = device.home_id
        node_id = device.node_id
        profile = device.profile
        state: dict[str, Any] = {}

        if profile.supports_shutter_position:
            try:
                position_data = await http.motorization_get(
                    home_id,
                    node_id,
                    "check-shutter-position",
                )
                if position_data:
                    normalized = normalize_shutter_position(position_data.get("lastReportedValue"))
                    if normalized is not None:
                        state["shutter_position"] = normalized
            except EnkiConnectionError as err:
                LOGGER.debug("Shutter position skipped for node %s: %s", node_id, err)

        if profile.supports_shutter_opening:
            try:
                opening_data = await http.motorization_get(
                    home_id,
                    node_id,
                    "check-shutter-opening",
                )
                if opening_data:
                    opening = opening_data.get("lastReportedValue")
                    if isinstance(opening, str):
                        state["shutter_opening"] = opening.upper()
            except EnkiConnectionError as err:
                LOGGER.debug("Shutter opening skipped for node %s: %s", node_id, err)

        await self._append_capability_states(
            http,
            home_id,
            node_id,
            profile,
            state,
        )
        return state

    # --- public command API --------------------------------------------------

    async def async_switch_electrical_power(
        self,
        home_id: str,
        node_id: str,
        value: str,
        *,
        endpoint: int | None = None,
    ) -> None:
        """Switch electrical power globally or for one BFF endpoint."""
        http = await self._get_http()
        await http.switch_electrical_power(home_id, node_id, value, endpoint=endpoint)

    async def async_set_fan_rotation(
        self,
        home_id: str,
        node_id: str,
        direction: str,
    ) -> None:
        """Set blade rotation via change-fan-rotation-direction."""
        http = await self._get_http()
        enki_value = direction_to_enki_rotation(direction)
        await http.airflow_post(home_id, node_id, "change-fan-rotation-direction", enki_value)

    async def async_set_airflow_mode(self, home_id: str, node_id: str, mode: str) -> None:
        """Set ventilation mode (MANUAL / BREEZE)."""
        http = await self._get_http()
        await http.airflow_post(home_id, node_id, "change-airflow-mode", mode)

    async def async_set_fan_speed(self, home_id: str, node_id: str, speed: int) -> None:
        """Set fan speed (0 = off, 1–6 = levels)."""
        http = await self._get_http()
        await http.airflow_post(home_id, node_id, "change-fan-speed", speed)

    async def async_set_shutter_position(
        self,
        home_id: str,
        node_id: str,
        position: int,
    ) -> None:
        """Set roller shutter position (0 = closed, 100 = open)."""
        http = await self._get_http()
        await http.motorization_post(
            home_id,
            node_id,
            "change-shutter-position",
            max(0, min(100, position)),
        )

    async def async_set_capability_value(
        self,
        home_id: str,
        node_id: str,
        service: str,
        capability: str,
        value: Any,
    ) -> None:
        """POST a change/switch/activate capability on a sensor or heating micro-service."""
        http = await self._get_http()
        await http.capability_post(service, home_id, node_id, capability, value)

    async def async_set_pilot_wire_mode(
        self,
        home_id: str,
        node_id: str,
        mode: str,
    ) -> None:
        """Set pilot wire mode (COMFORT, ECO, OFF, …)."""
        await self.async_set_capability_value(
            home_id,
            node_id,
            "heating",
            "switch_pilot_wire_mode",
            mode,
        )

    async def async_set_thermostat_target_temperature(
        self,
        home_id: str,
        node_id: str,
        temperature: float,
    ) -> None:
        """Set radiator / thermostat target temperature (°C)."""
        await self.async_set_capability_value(
            home_id,
            node_id,
            "heating",
            "change_thermostat_target_temperature",
            temperature,
        )

    async def async_set_light_power(self, home_id: str, node_id: str, on: bool) -> None:
        """Turn the ESDK fan light kit on or off (lighting API)."""
        await self.async_change_light_state(
            home_id,
            node_id,
            {"power": "ON" if on else "OFF"},
        )

    async def async_change_light_state(
        self,
        home_id: str,
        node_id: str,
        changes: dict[str, Any],
    ) -> None:
        """Apply one or more lighting fields in a single change-light-state call."""
        http = await self._get_http()
        current = await http.get_light_state(home_id, node_id)
        payload = merge_light_state_payload(
            current.get("lastReportedValue", {}),
            changes,
        )
        await http.change_light_state(home_id, node_id, payload)

    async def async_change_light_color(
        self,
        home_id: str,
        node_id: str,
        hue: float,
        saturation: float,
    ) -> None:
        """Set an HS colour and switch the bulb into colour mode."""
        http = await self._get_http()
        current = await http.get_light_state(home_id, node_id)
        payload = merge_light_state_payload(
            current.get("lastReportedValue", {}),
            {"colorMode": "hs", "hue": hue, "saturation": saturation},
        )
        payload.pop("colorTemperature", None)
        await http.change_light_state(home_id, node_id, payload)

    async def async_change_light_state_field(
        self,
        home_id: str,
        node_id: str,
        parameter: str,
        value: Any,
    ) -> None:
        """Backward-compatible wrapper for single-field lighting updates."""
        await self.async_change_light_state(home_id, node_id, {parameter: value})

    async def _get_power_state(self, home_id: str, node_id: str, endpoint: int) -> str:
        """Read one endpoint power state (used by integration tests)."""
        http = await self._get_http()
        data = await http.get_electrical_power(home_id, node_id)
        return normalize_power_state(data.get("lastReportedValue"), endpoint)

    async def async_activate_scenario(self, home_id: str, scenario_id: str) -> None:
        """Trigger an Enki cloud scenario."""
        http = await self._get_http()
        await http.activate_scenario(home_id, scenario_id)


def _parse_scenario(item: dict[str, Any], home_id: str) -> EnkiScenario | None:
    scenario_id = item.get("id")
    if not isinstance(scenario_id, str) or not scenario_id:
        return None
    label = item.get("label")
    enabled = item.get("enabled")
    status = item.get("status")
    return EnkiScenario(
        home_id=home_id,
        scenario_id=scenario_id,
        label=str(label) if isinstance(label, str) and label else scenario_id,
        enabled=bool(enabled) if isinstance(enabled, bool) else True,
        status=str(status) if isinstance(status, str) else "",
    )
