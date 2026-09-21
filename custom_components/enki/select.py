"""Select platform for Enki pilot wire controllers."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.camera_settings import CAMERA_SELECTS, CameraSelectSpec, select_values
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.heating import pilot_wire_api_value, pilot_wire_option_slug, pilot_wire_options
from .lib.shutter import (
    roller_shutter_mode_api_value,
    roller_shutter_mode_option_slug,
    roller_shutter_mode_options,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiPilotWireSelect(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_pilot_wire
    )
    async_add_entities(
        EnkiRollerShutterModeSelect(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_roller_shutter_mode
    )
    async_add_entities(
        EnkiCameraSettingSelect(coordinator, device, spec)
        for device in coordinator.data or []
        if device.profile.supports_camera_settings
        for spec in CAMERA_SELECTS
        if spec.capability in device.profile.capabilities
        and select_values(spec, device.profile.possible_values)
    )


class EnkiPilotWireSelect(EnkiEntity, SelectEntity):
    """Pilot wire mode selector (Comfort, Eco, Frost, Off, …)."""

    _attr_has_entity_name = True
    _attr_translation_key = "pilot_wire"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-pilot-wire"
        self._attr_options = pilot_wire_options(device.profile.possible_values)

    @property
    def current_option(self) -> str | None:
        value = self._device.reported.pilot_wire_state
        if not isinstance(value, str):
            return None
        slug = pilot_wire_option_slug(value)
        if slug in self._attr_options:
            return slug
        return None

    async def async_select_option(self, option: str) -> None:
        api_value = pilot_wire_api_value(option)
        await self.coordinator.api.async_set_pilot_wire_mode(
            self._device.home_id,
            self._device.node_id,
            api_value,
        )
        self.coordinator.update_cached_value(self.node_id, "pilot_wire_state", api_value)


class EnkiRollerShutterModeSelect(EnkiEntity, SelectEntity):
    """Roller shutter wiring direction (normal / inverted)."""

    _attr_has_entity_name = True
    _attr_translation_key = "roller_shutter_mode"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-roller-shutter-mode"
        self._attr_options = roller_shutter_mode_options(device.profile.possible_values)

    @property
    def current_option(self) -> str | None:
        value = self._device.reported.roller_shutter_mode
        if not isinstance(value, str):
            return None
        slug = roller_shutter_mode_option_slug(value)
        if slug in self._attr_options:
            return slug
        return None

    async def async_select_option(self, option: str) -> None:
        api_value = roller_shutter_mode_api_value(option)
        await self.coordinator.api.async_set_roller_shutter_mode(
            self._device.home_id,
            self._device.node_id,
            api_value,
        )
        self.coordinator.update_cached_value(self.node_id, "roller_shutter_mode", api_value)


class EnkiCameraSettingSelect(EnkiEntity, SelectEntity):
    """One multi-choice setting of a meari camera (night vision, recording, …)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: EnkiCoordinator, device: EnkiDevice, spec: CameraSelectSpec
    ) -> None:
        super().__init__(coordinator, device)
        self._spec = spec
        self._attr_translation_key = spec.translation_key
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{spec.translation_key}"
        # Options are the API values lowercased, so states can be translated.
        self._attr_options = [
            value.lower() for value in select_values(spec, device.profile.possible_values)
        ]

    @property
    def current_option(self) -> str | None:
        value = self._device.last_reported_value.get(self._spec.state_key)
        if isinstance(value, str) and value.lower() in self._attr_options:
            return value.lower()
        return None

    async def async_select_option(self, option: str) -> None:
        value = option.upper()
        await self.coordinator.api.async_set_camera_setting(
            self._device.home_id, self._device.node_id, self._spec.capability, value
        )
        self.coordinator.update_cached_value(self.node_id, self._spec.state_key, value)
