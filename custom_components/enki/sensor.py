"""Sensor platform for Enki devices (solar, temperature, humidity, battery)."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.battery import battery_health_to_percent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        entity
        for device in coordinator.data or []
        for entity in _build_sensor_entities(coordinator, device)
    )


def _build_sensor_entities(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[SensorEntity]:
    profile = device.profile
    entities: list[SensorEntity] = []

    if _has_power_production_sensor(device):
        entities.append(EnkiPowerProductionSensor(coordinator, device))
    if profile.supports_current_temperature and not profile.is_climate:
        entities.append(EnkiTemperatureSensor(coordinator, device))
    if profile.supports_current_humidity:
        entities.append(EnkiHumiditySensor(coordinator, device))
    if profile.supports_battery_health:
        entities.append(EnkiBatterySensor(coordinator, device))

    return entities


def _has_power_production_sensor(device: EnkiDevice) -> bool:
    profile = device.profile
    if device.power_production is None:
        return False
    return profile.is_inverter or profile.supports_power_production


class EnkiPowerProductionSensor(EnkiEntity, SensorEntity):
    """Live solar production from the Enki BFF dashboard."""

    _attr_translation_key = "power_production"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-power-production"

    @property
    def native_value(self) -> float | None:
        value = self._device.power_production
        if value is None:
            value = self._device.reported.power_production
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class EnkiTemperatureSensor(EnkiEntity, SensorEntity):
    _attr_translation_key = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-temperature"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.current_temperature


class EnkiHumiditySensor(EnkiEntity, SensorEntity):
    _attr_translation_key = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-humidity"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.current_humidity


class EnkiBatterySensor(EnkiEntity, SensorEntity):
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-battery"

    @property
    def native_value(self) -> float | None:
        return battery_health_to_percent(self._device.reported.battery_health)
