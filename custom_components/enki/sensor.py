"""Sensor platform for Enki devices (solar production, …)."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .capabilities import capabilities_set as device_capabilities_set
from .capabilities import is_inverter_device, supports_power_production
from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .entity import EnkiEntity
from .models import EnkiDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiPowerProductionSensor(coordinator, device)
        for device in coordinator.data or []
        if _has_power_production_sensor(device)
    )


def _has_power_production_sensor(device: EnkiDevice) -> bool:
    if device.power_production is None:
        return False
    if is_inverter_device(device):
        return True
    return supports_power_production(device_capabilities_set(device.capabilities))


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
            value = self._device.last_reported_value.get("power_production")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
