"""Climate platform for Enki radiators and thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.heating import (
    thermostat_running_to_hvac_action,
    thermostat_temperature_range,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiThermostatClimate(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_climate
    )


class EnkiThermostatClimate(EnkiEntity, ClimateEntity):
    """Radiator thermostat with target temperature and heating action."""

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_translation_key = "thermostat"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-thermostat"
        minimum, maximum, step = thermostat_temperature_range(device.profile.possible_values)
        self._attr_min_temp = minimum
        self._attr_max_temp = maximum
        self._attr_target_temperature_step = step
        self._off_temperature = minimum

    @property
    def current_temperature(self) -> float | None:
        return self._device.reported.current_temperature

    @property
    def target_temperature(self) -> float | None:
        return self._device.reported.thermostat_target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        target = self.target_temperature
        if target is not None and target <= self._off_temperature:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        action = thermostat_running_to_hvac_action(self._device.reported.thermostat_running_state)
        if action == "heating":
            return HVACAction.HEATING
        if action == "idle":
            return HVACAction.IDLE
        if action == "cooling":
            return HVACAction.COOLING
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.async_set_temperature(self._off_temperature)
        elif hvac_mode == HVACMode.HEAT and self.target_temperature is None:
            default_target = min(self._attr_max_temp, self._off_temperature + 1)
            await self.async_set_temperature(default_target)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.api.async_set_thermostat_target_temperature(
            self._device.home_id,
            self._device.node_id,
            float(temperature),
        )
        self.coordinator.update_cached_value(
            self.node_id,
            "thermostat_target_temperature",
            float(temperature),
        )
