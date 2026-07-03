"""Enki cloud API client (Leroy Merlin / Adeo)."""

from __future__ import annotations

from typing import Any

import aiohttp

from ..const import DEVICE_TYPE_LIGHTS, LOGGER
from ..domain.capabilities import EnkiCapabilityProfile
from ..domain.models import EnkiDevice, EnkiDiscoveryRecord
from ..domain.profile import build_discovery_record, integration_supports_device
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
from .transport import EnkiHttpClient

_SENSOR_CAPABILITY_READS: tuple[tuple[str, str, str], ...] = (
    ("temperature_humidity", "check_current_temperature", "current_temperature"),
    ("temperature_humidity", "check_current_humidity", "current_humidity"),
    ("battery_health", "check_battery_health", "battery_health"),
    ("presence_detector", "check_motion_detection", "motion_detection"),
    ("presence_detector", "check_motion_detector_state", "motion_detector_state"),
    ("contact_sensor", "check_contact_sensor_state", "contact_sensor_state"),
    ("contact_sensor", "check_vibration_detection", "vibration_detection"),
    (
        "contact_sensor",
        "check_vibration_detection_activation",
        "vibration_detection_activation",
    ),
    (
        "contact_sensor",
        "check_contact_detection_activation",
        "contact_detection_activation",
    ),
    (
        "contact_sensor",
        "check_vibration_sensibility_level",
        "vibration_sensibility_level",
    ),
    ("siren", "check_siren_global_state", "siren_global_state"),
    ("water_sensor", "check_water_sensor_state", "water_sensor_state"),
)

_HEATING_CAPABILITY_READS: tuple[tuple[str, str], ...] = (
    ("check_pilot_wire_state", "pilot_wire_state"),
    ("check_thermostat_target_temperature", "thermostat_target_temperature"),
    ("check_thermostat_running_state", "thermostat_running_state"),
    ("check_current_temperature", "current_temperature"),
    ("check_window_open_detection", "window_open_detection"),
    ("check_window_open_detection_mode", "window_open_detection_mode"),
    ("check_occupancy", "occupancy"),
    ("check_occupancy_mode", "occupancy_mode"),
)


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
        self._discovery_records: list[EnkiDiscoveryRecord] = []

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
            self._http = EnkiHttpClient(self._auth, self._session)
        assert self._http is not None
        return self._http

    async def async_connect(self) -> None:
        """Authenticate with Keycloak (resource-owner password grant)."""
        http = await self._get_http()
        await self._auth.connect(http.session)

    async def async_get_devices(self) -> list[EnkiDevice]:
        """Discover all nodes across every home on the account."""
        http = await self._get_http()
        homes = await http.get_homes()
        devices: list[EnkiDevice] = []
        self._discovery_records = []
        for home_id in homes:
            home_devices, records = await self._discover_home(http, home_id)
            devices.extend(home_devices)
            self._discovery_records.extend(records)
        return devices

    @property
    def discovery_records(self) -> list[EnkiDiscoveryRecord]:
        return list(self._discovery_records)

    async def _discover_home(
        self,
        http: EnkiHttpClient,
        home_id: str,
    ) -> tuple[list[EnkiDevice], list[EnkiDiscoveryRecord]]:
        dashboard = await http.get_dashboard(home_id)
        devices: list[EnkiDevice] = []
        records: list[EnkiDiscoveryRecord] = []

        for section in dashboard.get("sections", []):
            for item in section.get("items", []):
                device, record = await self._discover_dashboard_item(http, home_id, item)
                if record is not None:
                    records.append(record)
                if device is not None:
                    devices.append(device)
        return devices, records

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
        device_info = await http.get_referentiel_device(device_id)
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

        last_reported: dict[str, Any] = {}
        if item.get("isEnabled", True):
            last_reported = await self._refresh_device_state(http, skeleton, node_info)

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

        if profile.supports_electrical_power:
            try:
                power_details = await http.get_electrical_power(home_id, node_id)
                state["electrical_power"] = power_details.get("lastReportedValue")
                state["electrical_endpoints"] = power_details.get("endpoints", [])
                if not state.get("power") and isinstance(state["electrical_power"], str):
                    state["power"] = state["electrical_power"]
            except EnkiConnectionError as err:
                LOGGER.debug("Electrical power skipped for node %s: %s", node_id, err)

        if profile.supports_fan_speed:
            try:
                data = await http.airflow_get(home_id, node_id, "check-fan-speed")
                state["fan_speed"] = data["lastReportedValue"]
            except EnkiConnectionError as err:
                LOGGER.debug("Fan speed skipped for node %s: %s", node_id, err)

        if profile.supports_airflow_mode:
            try:
                data = await http.airflow_get(home_id, node_id, "check-airflow-mode")
                state["airflow_mode"] = data["lastReportedValue"]
            except EnkiConnectionError as err:
                LOGGER.debug("Airflow mode skipped for node %s: %s", node_id, err)

        if profile.is_inverter:
            state["power_production"] = device.power_production

        await self._append_sensor_capability_states(http, home_id, node_id, profile, state)
        await self._append_heating_capability_states(http, home_id, node_id, profile, state)
        return state

    async def _append_heating_capability_states(
        self,
        http: EnkiHttpClient,
        home_id: str,
        node_id: str,
        profile: EnkiCapabilityProfile,
        state: dict[str, Any],
    ) -> None:
        """Best-effort reads for heating micro-service (pilot wire, thermostats)."""
        caps = profile.capabilities
        for capability, state_key in _HEATING_CAPABILITY_READS:
            if capability not in caps:
                continue
            if capability == "check_current_temperature" and not profile.supports_thermostat:
                continue
            try:
                data = await http.capability_get("heating", home_id, node_id, capability)
                if data and "lastReportedValue" in data:
                    state[state_key] = data["lastReportedValue"]
            except EnkiConnectionError as err:
                LOGGER.debug(
                    "Heating capability %s skipped for node %s: %s",
                    capability,
                    node_id,
                    err,
                )

    async def _append_sensor_capability_states(
        self,
        http: EnkiHttpClient,
        home_id: str,
        node_id: str,
        profile: EnkiCapabilityProfile,
        state: dict[str, Any],
    ) -> None:
        """Best-effort reads for sensor / detector micro-services."""
        caps = profile.capabilities
        for service, capability, state_key in _SENSOR_CAPABILITY_READS:
            if capability not in caps:
                continue
            if capability == "check_current_temperature" and profile.supports_thermostat:
                continue
            try:
                data = await http.capability_get(service, home_id, node_id, capability)
                if data and "lastReportedValue" in data:
                    state[state_key] = data["lastReportedValue"]
            except EnkiConnectionError as err:
                LOGGER.debug(
                    "Capability %s skipped for node %s: %s",
                    capability,
                    node_id,
                    err,
                )

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

        try:
            mode_data = await http.airflow_get(home_id, node_id, "check-airflow-mode")
            if "lastReportedValue" in mode_data:
                state["airflow_mode"] = mode_data["lastReportedValue"]
        except EnkiConnectionError as err:
            LOGGER.debug("Airflow mode skipped for node %s: %s", node_id, err)

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

        try:
            power_details = await http.get_electrical_power(home_id, node_id)
            state["electrical_power"] = power_details.get("lastReportedValue")
            state["electrical_endpoints"] = power_details.get("endpoints", [])
        except EnkiConnectionError as err:
            LOGGER.debug("Electrical power skipped for fan node %s: %s", node_id, err)
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
        """Read roller shutter position/opening from access-and-motorizations API."""
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

        await self._append_sensor_capability_states(
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
        """Set fil pilote mode (COMFORT, ECO, OFF, …)."""
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
