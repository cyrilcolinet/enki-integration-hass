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
from .domain.camera_settings import CAMERA_NUMBERS, CameraSettingSpec, number_range
from .domain.models import EnkiDevice
from .domain.state import as_float
from .entity import EnkiCameraSettingEntity, EnkiEntity
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
        if device.profile.supports_camera_settings:
            for spec in CAMERA_NUMBERS:
                bounds = number_range(spec, device.profile.possible_values)
                # No range in the referentiel: no entity rather than guessed bounds.
                if spec.capability in device.profile.capabilities and bounds is not None:
                    entities.append(EnkiCameraSensitivityNumber(coordinator, device, spec, bounds))
    async_add_entities(entities)


class EnkiCapabilityNumber(EnkiEntity, NumberEntity):
    """A numeric configuration value written through one capability.

    Subclasses give the service, the capability and the state key; everything
    else is the same write.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _service: str
    _capability: str
    _state_key: str

    @property
    def native_value(self) -> float | None:
        # A capability can report, and an optimistic write can store, a string:
        # the vibration level goes over the wire as one.
        return as_float(self._device.last_reported_value.get(self._state_key))

    def _api_value(self, value: float) -> object:
        """What the capability expects on the wire."""
        return value

    async def async_set_native_value(self, value: float) -> None:
        api_value = self._api_value(value)
        with self.coordinator.optimistic(self.node_id):
            self.coordinator.update_cached_value(self.node_id, self._state_key, api_value)
            await self.coordinator.api.async_set_capability_value(
                self._device.home_id,
                self._device.node_id,
                self._service,
                self._capability,
                api_value,
            )


class EnkiVibrationSensibilityNumber(EnkiCapabilityNumber):
    """Vibration sensitivity level on Lexman contact sensors."""

    _attr_translation_key = "vibration_sensibility"
    _attr_native_min_value = 1
    _attr_native_max_value = 5
    _attr_native_step = 1
    _service = "contact_sensor"
    _capability = "change_vibration_sensibility_level"
    _state_key = "vibration_sensibility_level"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-vibration-sensibility"

    def _api_value(self, value: float) -> object:
        """The sensor takes its level as a string."""
        return str(int(value))


class EnkiOffsetTemperatureNumber(EnkiCapabilityNumber):
    """Temperature calibration offset on Enki thermostats."""

    _attr_translation_key = "offset_temperature"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _service = "thermostat"
    _capability = "change_offset_temperature"
    _state_key = "offset_temperature"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        minimum, maximum, step = offset_temperature_range(device.profile.possible_values)
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-offset-temperature"


class EnkiCameraSensitivityNumber(EnkiCameraSettingEntity, NumberEntity):
    """A detection sensitivity of a meari camera, bounded by its referentiel."""

    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        spec: CameraSettingSpec,
        bounds: tuple[float, float, float],
    ) -> None:
        super().__init__(coordinator, device, spec)
        (
            self._attr_native_min_value,
            self._attr_native_max_value,
            self._attr_native_step,
        ) = bounds

    @property
    def native_value(self) -> float | None:
        value = self._value
        return float(value) if isinstance(value, int) and not isinstance(value, bool) else None

    async def async_set_native_value(self, value: float) -> None:
        await self._write(int(value))
