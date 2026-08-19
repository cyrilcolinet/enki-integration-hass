"""Evology Philio 4-in-1 multisensor: brightness + presence support (#153)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.binary_sensor import _build_binary_sensor_entities
from enki.domain.models import EnkiDevice
from enki.sensor import _build_sensor_entities
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass


def _multisensor(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "dev",
        "node_id": "node-multisensor",
        "device_name": "Evology multisensor",
        "device_type": "sensors",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "check_battery_health",
            "check_brightness_level",
            "check_contact_sensor_state",
            "check_current_temperature",
            "check_multisensor_state",
            "check_presence_detection",
        ],
        "possible_values": {
            "check_presence_detection": {
                "values": ["PRESENCE_DETECTED", "NO_PRESENCE", "DISABLED"]
            },
        },
        "last_reported_value": {"presence_detection": "PRESENCE_DETECTED"},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_profile_flags_brightness_and_presence() -> None:
    profile = _multisensor().profile
    assert profile.supports_illuminance_level is True  # via check_brightness_level
    assert profile.supports_presence_detection is True
    assert profile.is_binary_sensor is True
    assert profile.is_environment_sensor is True


def test_brightness_routes_to_illuminance_state_key() -> None:
    read = next((r for r in CAPABILITY_READS if r.capability == "check_brightness_level"), None)
    assert read is not None
    assert read.transport_id == "luminosity_sensor"
    assert read.state_key == "illuminance_level"


def test_presence_routes_via_presence_detector() -> None:
    read = next((r for r in CAPABILITY_READS if r.capability == "check_presence_detection"), None)
    assert read is not None
    assert read.transport_id == "presence_detector"
    assert read.state_key == "presence_detection"


def test_builds_illuminance_sensor_from_brightness() -> None:
    entities = _build_sensor_entities(MagicMock(), _multisensor())
    illuminance = next(e for e in entities if e._attr_device_class == SensorDeviceClass.ILLUMINANCE)
    assert illuminance is not None


def test_builds_presence_binary_sensor_and_maps_state() -> None:
    entities = _build_binary_sensor_entities(MagicMock(), _multisensor())
    presence = next(e for e in entities if e._state_key == "presence_detection")
    assert presence._attr_device_class == BinarySensorDeviceClass.OCCUPANCY
    assert presence.is_on is True  # PRESENCE_DETECTED

    absent = next(
        e
        for e in _build_binary_sensor_entities(
            MagicMock(), _multisensor(last_reported_value={"presence_detection": "NO_PRESENCE"})
        )
        if e._state_key == "presence_detection"
    )
    assert absent.is_on is False

    disabled = next(
        e
        for e in _build_binary_sensor_entities(
            MagicMock(), _multisensor(last_reported_value={"presence_detection": "DISABLED"})
        )
        if e._state_key == "presence_detection"
    )
    assert disabled.is_on is None  # DISABLED is unknown, not a boolean
