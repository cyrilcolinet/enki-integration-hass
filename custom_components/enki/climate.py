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
from .domain.airco import (
    FAN_SPEEDS,
    OPERATING_MODES,
    STATE_KEY_BY_FIELD,
    SWING_HORIZONTAL,
    SWING_VERTICAL,
)
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.heating import (
    thermostat_running_to_hvac_action,
    thermostat_temperature_range,
)

# The app's own enums, confirmed against a unit reporting COOL / AUTO (#286).
_HVAC_BY_MODE = {
    "AUTO": HVACMode.AUTO,
    "COOL": HVACMode.COOL,
    "DRY": HVACMode.DRY,
    "FAN": HVACMode.FAN_ONLY,
    "HEAT": HVACMode.HEAT,
}
_MODE_BY_HVAC = {hvac: mode for mode, hvac in _HVAC_BY_MODE.items()}


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
    async_add_entities(
        EnkiAirConditionerClimate(coordinator, device)
        for device in coordinator.data or []
        if device.profile.supports_airconditioner_state
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
            await self.async_set_temperature(**{ATTR_TEMPERATURE: self._off_temperature})
            return
        if hvac_mode != HVACMode.HEAT:
            return
        target = self.target_temperature
        if target is not None and target > self._off_temperature:
            return
        step = self._attr_target_temperature_step or 1.0
        default_target = min(float(self._attr_max_temp), self._off_temperature + step)
        await self.async_set_temperature(**{ATTR_TEMPERATURE: default_target})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        with self.coordinator.optimistic(self.node_id):
            self.coordinator.update_cached_value(
                self.node_id,
                "thermostat_target_temperature",
                float(temperature),
            )
            await self.coordinator.api.async_set_thermostat_target_temperature(
                self._device.home_id,
                self._device.node_id,
                float(temperature),
            )


class EnkiAirConditionerClimate(EnkiEntity, ClimateEntity):
    """Equation air conditioner: mode, setpoint and fan speed (#286).

    Every write carries the whole state, so each command is built from what the
    last poll read. Changing the temperature alone would otherwise blank the
    mode, the fan speed and the comfort toggles.
    """

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.OFF, *(_HVAC_BY_MODE[mode] for mode in OPERATING_MODES)]
    _attr_fan_modes = [speed.lower() for speed in FAN_SPEEDS]
    # The louvres are two independent settings, and they do not have the same
    # number of steps: horizontal goes to 5, vertical to 4 (#286).
    _attr_swing_modes = [step.lower() for step in SWING_VERTICAL]
    _attr_swing_horizontal_modes = [step.lower() for step in SWING_HORIZONTAL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.SWING_HORIZONTAL_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_translation_key = "air_conditioner"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-air-conditioner"

    @property
    def _state(self) -> dict[str, Any]:
        return self._device.last_reported_value

    @property
    def current_temperature(self) -> float | None:
        return self._device.reported.airco_current_temperature

    @property
    def target_temperature(self) -> float | None:
        return self._device.reported.airco_target_temperature

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self._device.reported.airco_power == "OFF":
            return HVACMode.OFF
        mode = self._device.reported.airco_operating_mode
        return _HVAC_BY_MODE.get(mode or "")

    @property
    def fan_mode(self) -> str | None:
        return self._option(self._device.reported.airco_fan_speed, self._attr_fan_modes)

    @property
    def swing_mode(self) -> str | None:
        return self._option(self._state.get("airco_swing_vertical"), self._attr_swing_modes)

    @property
    def swing_horizontal_mode(self) -> str | None:
        return self._option(
            self._state.get("airco_swing_horizontal"), self._attr_swing_horizontal_modes
        )

    @staticmethod
    def _option(value: Any, allowed: list[str]) -> str | None:
        """Home Assistant logs an error for every value outside the declared list."""
        if not isinstance(value, str):
            return None
        lowered = value.lower()
        return lowered if lowered in allowed else None

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self._async_write(airco_swing_vertical=swing_mode.upper())

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        await self._async_write(airco_swing_horizontal=swing_horizontal_mode.upper())

    async def _async_write(self, **changes: Any) -> None:
        # The write carries the whole state, so it is built from what was read
        # before the cache is patched.
        state = dict(self._state)
        with self.coordinator.optimistic(self.node_id), self.coordinator.batch_updates():
            for field, value in changes.items():
                # Swing changes come keyed by state key already, the rest by API field.
                key = STATE_KEY_BY_FIELD.get(field, field)
                self.coordinator.update_cached_value(self.node_id, key, value)
            await self.coordinator.api.async_set_airconditioner_state(
                self._device.home_id,
                self._device.node_id,
                state,
                **changes,
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self._async_write(targetTemperature=float(temperature))

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._async_write(fanSpeed=fan_mode.upper())

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._async_write(power="OFF")
            return
        mode = _MODE_BY_HVAC.get(hvac_mode)
        if mode is None:
            return
        # Leaving a mode on a unit that is off should also turn it back on.
        await self._async_write(power="ON", operatingMode=mode)
