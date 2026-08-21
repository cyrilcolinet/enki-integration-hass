"""Entity-category assignments: config knobs vs diagnostics vs primary controls."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.binary_sensor import EnkiBinarySensor
from enki.domain.models import EnkiDevice
from enki.number import EnkiOffsetTemperatureNumber, EnkiVibrationSensibilityNumber
from enki.select import EnkiRollerShutterModeSelect
from enki.sensor import (
    EnkiBatterySensor,
    EnkiCameraLastEventSensor,
    EnkiCameraLastMotionSensor,
    EnkiIlluminanceSensor,
    EnkiTemperatureSensor,
)
from enki.switch import _SWITCH_SPECS
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory

CONFIG = EntityCategory.CONFIG
DIAGNOSTIC = EntityCategory.DIAGNOSTIC


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "Device",
        "device_type": "sensors",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _coordinator(device: EnkiDevice) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = [device]
    coordinator.get_device_by_node = lambda node_id: device
    return coordinator


def _category(entity) -> EntityCategory | None:
    return getattr(entity, "_attr_entity_category", None)


def test_config_switch_specs_are_config_except_siren() -> None:
    for spec in _SWITCH_SPECS:
        if spec["suffix"] == "siren":
            assert "entity_category" not in spec
        else:
            assert spec["entity_category"] == CONFIG


def test_number_entities_are_config() -> None:
    device = _device(possible_values={})
    assert _category(EnkiVibrationSensibilityNumber(_coordinator(device), device)) == CONFIG
    assert _category(EnkiOffsetTemperatureNumber(_coordinator(device), device)) == CONFIG


def test_roller_shutter_mode_select_is_config() -> None:
    device = _device()
    assert _category(EnkiRollerShutterModeSelect(_coordinator(device), device)) == CONFIG


def test_battery_and_camera_sensors_are_diagnostic() -> None:
    device = _device()
    for cls in (EnkiBatterySensor, EnkiCameraLastMotionSensor, EnkiCameraLastEventSensor):
        assert _category(cls(_coordinator(device), device)) == DIAGNOSTIC


def test_primary_sensors_have_no_category() -> None:
    device = _device()
    for cls in (EnkiTemperatureSensor, EnkiIlluminanceSensor):
        assert _category(cls(_coordinator(device), device)) is None


def test_firmware_binary_sensor_is_diagnostic() -> None:
    device = _device()
    firmware = EnkiBinarySensor(
        _coordinator(device),
        device,
        state_key="firmware_update_available",
        suffix="firmware_update",
        translation_key="firmware_update",
        device_class=BinarySensorDeviceClass.UPDATE,
        entity_category=DIAGNOSTIC,
    )
    assert _category(firmware) == DIAGNOSTIC


def test_primary_binary_sensor_has_no_category() -> None:
    device = _device()
    motion = EnkiBinarySensor(
        _coordinator(device),
        device,
        state_key="motion_detection",
        suffix="motion",
        translation_key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
    )
    assert _category(motion) is None
