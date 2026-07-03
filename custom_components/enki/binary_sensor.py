"""Binary sensor platform for Enki motion, contact, and vibration detectors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity

_ENUM_TO_BOOL = {
    "MOTION_DETECTED": True,
    "NO_MOTION_DETECTED": False,
    "VIBRATION_DETECTED": True,
    "NO_VIBRATION_DETECTED": False,
    "OPENED": True,
    "CLOSED": False,
    "WATER_DETECTED": True,
    "NO_WATER_DETECTED": False,
    "WET": True,
    "DRY": False,
    "LEAK": True,
    "NO_LEAK": False,
    "WINDOW_OPEN": True,
    "NO_WINDOW_OPEN": False,
    "OCCUPIED": True,
    "UNOCCUPIED": False,
}

_BINARY_SENSOR_SPECS: tuple[dict[str, str | BinarySensorDeviceClass], ...] = (
    {
        "capability": "check_motion_detection",
        "state_key": "motion_detection",
        "suffix": "motion",
        "translation_key": "motion",
        "device_class": BinarySensorDeviceClass.MOTION,
    },
    {
        "capability": "check_motion_detector_state",
        "state_key": "motion_detector_state",
        "suffix": "motion_state",
        "translation_key": "motion",
        "device_class": BinarySensorDeviceClass.MOTION,
    },
    {
        "capability": "check_vibration_detection",
        "state_key": "vibration_detection",
        "suffix": "vibration",
        "translation_key": "vibration",
        "device_class": BinarySensorDeviceClass.VIBRATION,
    },
    {
        "capability": "check_contact_sensor_state",
        "state_key": "contact_sensor_state",
        "suffix": "contact",
        "translation_key": "contact",
        "device_class": BinarySensorDeviceClass.OPENING,
    },
    {
        "capability": "check_water_sensor_state",
        "state_key": "water_sensor_state",
        "suffix": "water_leak",
        "translation_key": "water_leak",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    {
        "capability": "check_window_open_detection",
        "state_key": "window_open_detection",
        "suffix": "window",
        "translation_key": "window",
        "device_class": BinarySensorDeviceClass.WINDOW,
    },
    {
        "capability": "check_occupancy",
        "state_key": "occupancy",
        "suffix": "occupancy",
        "translation_key": "occupancy",
        "device_class": BinarySensorDeviceClass.OCCUPANCY,
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
        for entity in _build_binary_sensor_entities(coordinator, device)
    )


def _build_binary_sensor_entities(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[EnkiBinarySensor]:
    profile = device.profile
    if not profile.is_binary_sensor:
        return []

    capabilities = profile.capabilities
    entities: list[EnkiBinarySensor] = []
    for spec in _BINARY_SENSOR_SPECS:
        capability = str(spec["capability"])
        if capability not in capabilities:
            continue
        entities.append(
            EnkiBinarySensor(
                coordinator,
                device,
                state_key=str(spec["state_key"]),
                suffix=str(spec["suffix"]),
                translation_key=str(spec["translation_key"]),
                device_class=spec["device_class"],
            )
        )
    return entities


class EnkiBinarySensor(EnkiEntity, BinarySensorEntity):
    """Motion, opening, or vibration state from Enki sensor APIs."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        *,
        state_key: str,
        suffix: str,
        translation_key: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        super().__init__(coordinator, device)
        self._state_key = state_key
        self._attr_translation_key = translation_key
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{suffix}"

    @property
    def is_on(self) -> bool | None:
        raw = self._device.last_reported_value.get(self._state_key)
        if raw is None and self._state_key == "motion_detection":
            raw = self._device.reported.motion_detection
        elif raw is None and self._state_key == "motion_detector_state":
            raw = self._device.last_reported_value.get("motion_detector_state")
        elif raw is None and self._state_key == "vibration_detection":
            raw = self._device.reported.vibration_detection
        elif raw is None and self._state_key == "contact_sensor_state":
            raw = self._device.reported.contact_sensor_state
        elif raw is None and self._state_key == "water_sensor_state":
            raw = self._device.reported.water_sensor_state
        elif raw is None and self._state_key == "window_open_detection":
            raw = self._device.reported.window_open_detection
        elif raw is None and self._state_key == "occupancy":
            raw = self._device.reported.occupancy

        if isinstance(raw, str):
            mapped = _ENUM_TO_BOOL.get(raw.upper())
            if mapped is not None:
                return mapped
        if isinstance(raw, bool):
            return raw
        return None
