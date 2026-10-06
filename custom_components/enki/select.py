"""Select platform for Enki pilot wire controllers, shutters, cameras and water heaters."""

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
from .entity import EnkiCameraSettingEntity, EnkiEntity
from .lib.heating import (
    pilot_wire_api_value,
    pilot_wire_option_slug,
    pilot_wire_options,
    water_heater_mode_api_value,
    water_heater_mode_option,
    water_heater_mode_options,
)
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
        EnkiWaterHeaterModeSelect(coordinator, device)
        for device in coordinator.data or []
        if device.profile.supports_water_heater_mode_change
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
        with self.coordinator.optimistic(self.node_id):
            self.coordinator.update_cached_value(self.node_id, "pilot_wire_state", api_value)
            await self.coordinator.api.async_set_pilot_wire_mode(
                self._device.home_id,
                self._device.node_id,
                api_value,
            )


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
        with self.coordinator.optimistic(self.node_id):
            self.coordinator.update_cached_value(self.node_id, "roller_shutter_mode", api_value)
            await self.coordinator.api.async_set_roller_shutter_mode(
                self._device.home_id,
                self._device.node_id,
                api_value,
            )


# The heater reported a new mode 1.5 to 4 minutes after the app wrote it (AD-HEWH3-1,
# #285). The default hold would let the stale mode come back before the new one lands.
_WATER_HEATER_MODE_HOLD_SECONDS = 300.0


class EnkiWaterHeaterModeSelect(EnkiEntity, SelectEntity):
    """Equation water heater mode (manual, boost, self-clean, …).

    A mode carries its own setpoint: entering one rewrites the target temperature,
    and MANUAL comes back with whatever setpoint it last held (#285).
    """

    _attr_has_entity_name = True
    _attr_translation_key = "water_heater_mode"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-water-heater-mode-select"
        self._attr_options = water_heater_mode_options(device.profile.possible_values)

    @property
    def current_option(self) -> str | None:
        return water_heater_mode_option(self._device.reported.water_heater_mode, self._attr_options)

    async def async_select_option(self, option: str) -> None:
        api_value = water_heater_mode_api_value(option)
        with self.coordinator.optimistic(self.node_id):
            self.coordinator.update_cached_value(
                self.node_id,
                "water_heater_mode",
                api_value,
                hold_seconds=_WATER_HEATER_MODE_HOLD_SECONDS,
            )
            await self.coordinator.api.async_set_water_heater_mode(
                self._device.home_id,
                self._device.node_id,
                api_value,
            )


class EnkiCameraSettingSelect(EnkiCameraSettingEntity, SelectEntity):
    """One multi-choice setting of a meari camera (night vision, recording, …)."""

    def __init__(
        self, coordinator: EnkiCoordinator, device: EnkiDevice, spec: CameraSelectSpec
    ) -> None:
        super().__init__(coordinator, device, spec)
        # Options are the API values lowercased, so states can be translated.
        self._attr_options = [
            value.lower() for value in select_values(spec, device.profile.possible_values)
        ]

    @property
    def current_option(self) -> str | None:
        value = self._value
        if isinstance(value, str) and value.lower() in self._attr_options:
            return value.lower()
        return None

    async def async_select_option(self, option: str) -> None:
        await self._write(option.upper())
