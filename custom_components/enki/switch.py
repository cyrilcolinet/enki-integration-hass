"""Switch platform for Enki outlets, sirens, and detector activation toggles."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity

_SWITCH_SPECS: tuple[dict[str, str], ...] = (
    {
        "switch_capability": "activate_vibration_detection",
        "check_capability": "check_vibration_detection_activation",
        "state_key": "vibration_detection_activation",
        "suffix": "vibration_detection",
        "translation_key": "vibration_detection",
        "service": "contact_sensor",
        "entity_category": EntityCategory.CONFIG,
    },
    {
        "switch_capability": "activate_contact_detection",
        "check_capability": "check_contact_detection_activation",
        "state_key": "contact_detection_activation",
        "suffix": "contact_detection",
        "translation_key": "contact_detection",
        "service": "contact_sensor",
        "entity_category": EntityCategory.CONFIG,
    },
    {
        "switch_capability": "switch_siren_status",
        "check_capability": "check_siren_global_state",
        "state_key": "siren_global_state",
        "suffix": "siren",
        "translation_key": "siren",
        "service": "siren",
    },
    {
        "switch_capability": "change_window_open_detection_mode",
        "check_capability": "check_window_open_detection_mode",
        "state_key": "window_open_detection_mode",
        "suffix": "window_open_detection_mode",
        "translation_key": "window_open_detection_mode",
        "service": "thermostat",
        "on_value": "ENABLED",
        "off_value": "DISABLED",
        "entity_category": EntityCategory.CONFIG,
    },
    {
        "switch_capability": "change_occupancy_mode",
        "check_capability": "check_occupancy_mode",
        "state_key": "occupancy_mode",
        "suffix": "occupancy_mode",
        "translation_key": "occupancy_mode",
        "service": "presence_detector",
        "on_value": "ENABLED",
        "off_value": "DISABLED",
        "entity_category": EntityCategory.CONFIG,
    },
    {
        "switch_capability": "change_child_lock",
        "check_capability": "check_child_lock",
        "state_key": "child_lock",
        "suffix": "child_lock",
        "translation_key": "child_lock",
        "service": "thermostat",
        "on_value": "LOCK",
        "off_value": "UNLOCK",
        "entity_category": EntityCategory.CONFIG,
    },
    {
        "switch_capability": "change_preheating_status",
        "check_capability": "check_preheating_status",
        "state_key": "preheating_status",
        "suffix": "preheating",
        "translation_key": "preheating",
        "service": "thermostat",
        "on_value": "ENABLED",
        "off_value": "DISABLED",
        "entity_category": EntityCategory.CONFIG,
    },
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        entity
        for device in coordinator.data or []
        for entity in _build_switch_entities(coordinator, device)
    )


def _build_switch_entities(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[SwitchEntity]:
    entities: list[SwitchEntity] = []
    entities.extend(_build_outlet_switches(coordinator, device))
    entities.extend(_build_channel_switches(coordinator, device))
    entities.extend(_build_boiler_switches(coordinator, device))
    entities.extend(_build_config_switches(coordinator, device))
    return entities


def _build_channel_switches(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[EnkiChannelSwitch]:
    return [
        EnkiChannelSwitch(coordinator, device, channel=channel)
        for channel in device.profile.channel_power_indices
    ]


def _build_boiler_switches(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[EnkiBoilerSwitch]:
    if not device.profile.is_boiler_switch:
        return []
    return [EnkiBoilerSwitch(coordinator, device)]


def _build_outlet_switches(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[EnkiOutletSwitch]:
    profile = device.profile
    if not profile.is_outlet:
        return []

    endpoint_ids = profile.power_switch_endpoints
    if endpoint_ids:
        return [
            EnkiOutletSwitch(
                coordinator,
                device,
                endpoint_id=endpoint_id,
                suffix=f"outlet_{chr(ord('a') + index)}",
            )
            for index, endpoint_id in enumerate(endpoint_ids)
        ]
    return [EnkiOutletSwitch(coordinator, device, endpoint_id=None, suffix="outlet")]


def _build_config_switches(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[EnkiConfigSwitch]:
    profile = device.profile
    if not profile.is_config_switch:
        return []

    capabilities = profile.capabilities
    entities: list[EnkiConfigSwitch] = []
    for spec in _SWITCH_SPECS:
        switch_cap = spec["switch_capability"]
        if switch_cap not in capabilities:
            continue
        entities.append(
            EnkiConfigSwitch(
                coordinator,
                device,
                switch_capability=switch_cap,
                check_capability=spec["check_capability"],
                state_key=spec["state_key"],
                suffix=spec["suffix"],
                translation_key=spec["translation_key"],
                service=spec["service"],
                on_value=spec.get("on_value", "ON"),
                off_value=spec.get("off_value", "OFF"),
                entity_category=spec.get("entity_category"),
            )
        )
    return entities


class EnkiOutletSwitch(EnkiEntity, SwitchEntity):
    """Power outlet or relay controlled via api-enki-power-prod."""

    _attr_has_entity_name = True
    _attr_translation_key = "outlet"
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        *,
        endpoint_id: int | None,
        suffix: str,
    ) -> None:
        super().__init__(coordinator, device)
        self._endpoint_id = endpoint_id
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{suffix}"

    @property
    def is_on(self) -> bool | None:
        reported = self._device.reported
        if self._endpoint_id is not None:
            power = reported.endpoint_power(self._endpoint_id)
            if power is None:
                return None
            return power == "ON"
        if reported.global_power is not None:
            return reported.global_power == "ON"
        if reported.electrical_power is not None:
            return reported.electrical_power == "ON"
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_power("ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_power("OFF")

    async def _set_power(self, power: str) -> None:
        node_id = self._device.node_id
        await self.coordinator.api.async_switch_electrical_power(
            self._device.home_id,
            node_id,
            power,
            endpoint=self._endpoint_id,
        )
        if self._endpoint_id is not None:
            self.coordinator.update_endpoint_power(node_id, self._endpoint_id, power)
            return
        self.coordinator.update_cached_value(node_id, "electrical_power", power)
        self.coordinator.update_cached_value(node_id, "power", power)


class EnkiChannelSwitch(EnkiEntity, SwitchEntity):
    """One relay of a multi-channel in-wall module (api-enki-power-prod)."""

    _attr_has_entity_name = True
    _attr_translation_key = "channel"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        *,
        channel: int,
    ) -> None:
        super().__init__(coordinator, device)
        self._channel = channel
        self._state_key = f"channel{channel}_electrical_power"
        self._switch_capability = f"switch_channel{channel}_electrical_power"
        self._attr_translation_placeholders = {"channel": str(channel)}
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-channel{channel}"

    @property
    def is_on(self) -> bool | None:
        value = self._device.last_reported_value.get(self._state_key)
        if isinstance(value, str):
            normalized = value.upper()
            if normalized == "ON":
                return True
            if normalized == "OFF":
                return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_power("ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_power("OFF")

    async def _set_power(self, value: str) -> None:
        await self.coordinator.api.async_set_capability_value(
            self._device.home_id,
            self._device.node_id,
            "power",
            self._switch_capability,
            value,
        )
        self.coordinator.update_cached_value(self.node_id, self._state_key, value)


class EnkiBoilerSwitch(EnkiOutletSwitch):
    """On/off relay wired to a water heater (Enki `boiler` module).

    Same power API as an outlet (switch_electrical_power on the whole node), but
    surfaced as a plain switch rather than an OUTLET so it reads as a water-heater
    control. See EnkiCapabilityProfile.is_boiler_switch.
    """

    _attr_translation_key = "boiler"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
    ) -> None:
        super().__init__(coordinator, device, endpoint_id=None, suffix="boiler")


class EnkiConfigSwitch(EnkiEntity, SwitchEntity):
    """Siren or detector activation switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        *,
        switch_capability: str,
        check_capability: str,
        state_key: str,
        suffix: str,
        translation_key: str,
        service: str,
        on_value: str = "ON",
        off_value: str = "OFF",
        entity_category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator, device)
        self._switch_capability = switch_capability
        self._check_capability = check_capability
        self._state_key = state_key
        self._service = service
        self._on_value = on_value
        self._off_value = off_value
        self._attr_translation_key = translation_key
        self._attr_entity_category = entity_category
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{suffix}"

    @property
    def is_on(self) -> bool | None:
        value = self._device.last_reported_value.get(self._state_key)
        if isinstance(value, str):
            normalized = value.upper()
            if normalized == self._on_value.upper():
                return True
            if normalized == self._off_value.upper():
                return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_value(self._on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_value(self._off_value)

    async def _set_value(self, value: str) -> None:
        await self.coordinator.api.async_set_capability_value(
            self._device.home_id,
            self._device.node_id,
            self._service,
            self._switch_capability,
            value,
        )
        self.coordinator.update_cached_value(self.node_id, self._state_key, value)
