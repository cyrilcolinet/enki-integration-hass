"""Number platform for Enki contact sensor and thermostat configuration."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.heating import offset_temperature_range


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    for device in coordinator.data or []:
        if device.profile.supports_vibration_sensibility:
            entities.append(EnkiVibrationSensibilityNumber(coordinator, device))
        if device.profile.supports_offset_temperature:
            entities.append(EnkiOffsetTemperatureNumber(coordinator, device))
    async_add_entities(entities)


class EnkiVibrationSensibilityNumber(EnkiEntity, NumberEntity):
    """Vibration sensitivity level on Lexman contact sensors."""

    _attr_has_entity_name = True
    _attr_translation_key = "vibration_sensibility"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 5
    _attr_native_step = 1

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-vibration-sensibility"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.vibration_sensibility_level

    async def async_set_native_value(self, value: float) -> None:
        level = str(int(value))
        await self.coordinator.api.async_set_capability_value(
            self._device.home_id,
            self._device.node_id,
            "contact_sensor",
            "change_vibration_sensibility_level",
            level,
        )
        self.coordinator.update_cached_value(
            self.node_id,
            "vibration_sensibility_level",
            level,
        )


class EnkiOffsetTemperatureNumber(EnkiEntity, NumberEntity):
    """Temperature calibration offset on Enki thermostats."""

    _attr_has_entity_name = True
    _attr_translation_key = "offset_temperature"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        minimum, maximum, step = offset_temperature_range(device.profile.possible_values)
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-offset-temperature"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.offset_temperature

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.async_set_capability_value(
            self._device.home_id,
            self._device.node_id,
            "thermostat",
            "change_offset_temperature",
            value,
        )
        self.coordinator.update_cached_value(
            self.node_id,
            "offset_temperature",
            value,
        )
