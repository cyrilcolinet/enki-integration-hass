"""Switch platform for Enki sirens and detector activation toggles."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    },
    {
        "switch_capability": "activate_contact_detection",
        "check_capability": "check_contact_detection_activation",
        "state_key": "contact_detection_activation",
        "suffix": "contact_detection",
        "translation_key": "contact_detection",
        "service": "contact_sensor",
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
        "service": "heating",
        "on_value": "ENABLED",
        "off_value": "DISABLED",
    },
    {
        "switch_capability": "change_occupancy_mode",
        "check_capability": "check_occupancy_mode",
        "state_key": "occupancy_mode",
        "suffix": "occupancy_mode",
        "translation_key": "occupancy_mode",
        "service": "heating",
        "on_value": "ENABLED",
        "off_value": "DISABLED",
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
            )
        )
    return entities


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
    ) -> None:
        super().__init__(coordinator, device)
        self._switch_capability = switch_capability
        self._check_capability = check_capability
        self._state_key = state_key
        self._service = service
        self._on_value = on_value
        self._off_value = off_value
        self._attr_translation_key = translation_key
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
