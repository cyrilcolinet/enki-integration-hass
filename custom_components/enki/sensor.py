"""Sensor platform for Enki devices (solar, temperature, humidity, battery)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.battery import battery_health_to_percent
from .lib.heating import water_heater_mode_option, water_heater_mode_options


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
    if _has_energy_production_sensor(device):
        entities.append(EnkiEnergyProductionSensor(coordinator, device))
    if profile.supports_current_temperature and not profile.is_climate:
        entities.append(EnkiTemperatureSensor(coordinator, device))
    if profile.supports_current_humidity:
        entities.append(EnkiHumiditySensor(coordinator, device))
    if profile.supports_battery_health:
        entities.append(EnkiBatterySensor(coordinator, device))
    if profile.supports_illuminance_level:
        entities.append(EnkiIlluminanceSensor(coordinator, device))
    if profile.supports_electrical_consumption:
        # Some plugs declare the capability but the instant route answers nothing
        # for them, leaving a sensor that reads unknown for ever. The energy one
        # works on the same devices, so the reading is not lost (#268). A device
        # that starts answering later needs a reload.
        if "electrical_consumption" in device.last_reported_value:
            entities.append(EnkiElectricalConsumptionSensor(coordinator, device))
        entities.append(EnkiEnergySensor(coordinator, device))
    if profile.supports_water_heater_mode and not profile.supports_water_heater_mode_change:
        entities.append(EnkiWaterHeaterModeSensor(coordinator, device))
    if profile.is_camera:
        entities.append(EnkiCameraLastMotionSensor(coordinator, device))
        if profile.supports_camera_sound_events:
            entities.append(EnkiCameraLastSoundSensor(coordinator, device))
        entities.append(EnkiCameraLastEventSensor(coordinator, device))
    if profile.supports_camera_settings:
        entities.extend(
            [
                EnkiCameraPercentSensor(
                    coordinator,
                    device,
                    "camera_battery_level",
                    "battery",
                    SensorDeviceClass.BATTERY,
                ),
                EnkiCameraPercentSensor(
                    coordinator, device, "camera_wifi_strength", "camera_wifi_strength"
                ),
                EnkiCameraEnumSensor(
                    coordinator,
                    device,
                    "camera_battery_charging",
                    "camera_battery_charging",
                    ("not_charging", "charging", "charging_full"),
                ),
                EnkiCameraEnumSensor(
                    coordinator,
                    device,
                    "camera_sd_state",
                    "camera_sd_card",
                    (
                        "no_card_inserted",
                        "normal_use",
                        "abnormal_card_read_write",
                        "formatting",
                        "file_system_not_supported",
                        "card_being_recognized",
                        "not_formatted",
                        "other_errors",
                    ),
                ),
            ]
        )

    return entities


def _has_power_production_sensor(device: EnkiDevice) -> bool:
    profile = device.profile
    return profile.is_inverter and profile.supports_power_production


def _has_energy_production_sensor(device: EnkiDevice) -> bool:
    profile = device.profile
    return profile.is_inverter and profile.supports_energy_production


class EnkiPowerProductionSensor(EnkiEntity, SensorEntity):
    """Live solar production (W) from BFF dashboard or Envertech API."""

    _attr_translation_key = "power_production"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-power-production"

    @property
    def native_value(self) -> float | None:
        value = self._device.reported.power_production
        if value is None:
            value = self._device.power_production
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class EnkiEnergyProductionSensor(EnkiEntity, SensorEntity):
    """Cumulative solar energy (kWh) from api-enki-lexman-envertech-prod."""

    _attr_translation_key = "energy_production"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-energy-production"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.energy_production


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
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-battery"

    @property
    def native_value(self) -> float | None:
        return battery_health_to_percent(self._device.reported.battery_health)


class EnkiIlluminanceSensor(EnkiEntity, SensorEntity):
    _attr_translation_key = "illuminance"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-illuminance"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.illuminance_level


class EnkiCameraLastMotionSensor(EnkiEntity, SensorEntity):
    """Timestamp of the camera's most recent motion event."""

    _attr_translation_key = "camera_last_motion"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-camera-last-motion"

    @property
    def native_value(self) -> datetime | None:
        raw = self._device.reported.camera_last_motion_at
        return dt_util.parse_datetime(raw) if raw else None


class EnkiCameraLastSoundSensor(EnkiEntity, SensorEntity):
    """Timestamp of the camera's most recent sound detection."""

    _attr_translation_key = "camera_last_sound"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-camera-last-sound"

    @property
    def native_value(self) -> datetime | None:
        raw = self._device.reported.camera_last_sound_at
        return dt_util.parse_datetime(raw) if raw else None


class EnkiCameraLastEventSensor(EnkiEntity, SensorEntity):
    """Type of the camera's most recent event (movement / SD state)."""

    _attr_translation_key = "camera_last_event"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-camera-last-event"

    @property
    def native_value(self) -> str | None:
        return self._device.reported.camera_last_event_type


class EnkiElectricalConsumptionSensor(EnkiEntity, SensorEntity):
    """Instant power draw from api-enki-consumption-prod (Edisio, …)."""

    _attr_translation_key = "electrical_consumption"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-electrical-consumption"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        unit = self._device.reported.electrical_consumption_unit
        if unit in {"kWh", "KWH"}:
            return SensorDeviceClass.ENERGY
        return SensorDeviceClass.POWER

    @property
    def state_class(self) -> SensorStateClass | None:
        if self.device_class == SensorDeviceClass.ENERGY:
            return SensorStateClass.TOTAL_INCREASING
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str:
        unit = self._device.reported.electrical_consumption_unit
        if unit in {"kWh", "KWH"}:
            return UnitOfEnergy.KILO_WATT_HOUR
        return UnitOfPower.WATT

    @property
    def native_value(self) -> float | None:
        return self._device.reported.electrical_consumption

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Enki's own timestamp for this reading (`lastReportedDate`).

        It is not when we last asked: on the units measured so far it only moves
        when the value itself changes, so an hour-old date on an idle device
        means nothing has changed in an hour, not that the reading is stale
        (#279). The name follows Enki's field rather than that reading, since
        nothing says every device behaves the same way.
        """
        return {"last_reported_at": self._device.reported.electrical_consumption_at}


class EnkiWaterHeaterModeSensor(EnkiEntity, SensorEntity):
    """Operating mode of an Equation water heater, as read (#285).

    The control is the `select`, which writes through heating-controller. This
    stays for a heater that declares the read but not the write.
    """

    _attr_translation_key = "water_heater_mode"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-water-heater-mode"
        self._attr_options = water_heater_mode_options(device.profile.possible_values)

    @property
    def native_value(self) -> str | None:
        return water_heater_mode_option(self._device.reported.water_heater_mode, self._attr_options)


class EnkiEnergySensor(EnkiEntity, SensorEntity):
    """Energy consumed so far this month (api-enki-consumption-prod, #270).

    The service bills by period, not as a running meter, so this resets when the
    month turns — on the API's UTC boundary, which is an hour or two off local
    midnight. `TOTAL_INCREASING` is what makes that harmless: Home Assistant
    reads the drop as a meter reset and keeps the long-term total it has built.
    """

    _attr_translation_key = "energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-energy"

    @property
    def native_value(self) -> float | None:
        return self._device.reported.energy_period_total

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        reported = self._device.reported
        return {
            "first_measurement_at": reported.energy_first_measurement_at,
            "last_measurement_at": reported.energy_last_measurement_at,
        }


class EnkiCameraPercentSensor(EnkiEntity, SensorEntity):
    """A percentage reported by a meari camera (battery, Wi-Fi signal)."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        state_key: str,
        translation_key: str,
        device_class: SensorDeviceClass | None = None,
    ) -> None:
        super().__init__(coordinator, device)
        self._state_key = state_key
        self._attr_translation_key = translation_key
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{state_key}"

    @property
    def native_value(self) -> int | None:
        value = self._device.last_reported_value.get(self._state_key)
        return value if isinstance(value, int) else None


class EnkiCameraEnumSensor(EnkiEntity, SensorEntity):
    """A reported camera state with a fixed set of values (charging, SD card)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        state_key: str,
        translation_key: str,
        options: tuple[str, ...],
    ) -> None:
        super().__init__(coordinator, device)
        self._state_key = state_key
        self._attr_translation_key = translation_key
        self._attr_options = list(options)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{translation_key}"

    @property
    def native_value(self) -> str | None:
        value = self._device.last_reported_value.get(self._state_key)
        # An unknown value would be rejected by the enum device class.
        if isinstance(value, str) and value.lower() in self._attr_options:
            return value.lower()
        return None
