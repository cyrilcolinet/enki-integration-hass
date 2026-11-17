"""Netsecur smoke detector as a binary sensor (#371)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.binary_sensor import _build_binary_sensor_entities
from enki.domain.models import EnkiDevice
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

_CAPABILITY = "check_smoke_alarm_status"


def _detector(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "dev",
        "node_id": "node-smoke",
        "device_name": "Smoke detector",
        "device_type": "sensors",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "check_current_temperature",
            "check_current_humidity",
            "check_battery_health",
            _CAPABILITY,
            "check_smoke_detector_state",
        ],
        "last_reported_value": {"smoke_alarm_status": "INACTIVE"},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_profile_flags_smoke_binary_sensor() -> None:
    profile = _detector().profile
    assert profile.supports_smoke_alarm is True
    assert profile.is_binary_sensor is True


def test_capability_read_routes_smoke_via_smoke_service() -> None:
    read = next((r for r in CAPABILITY_READS if r.capability == _CAPABILITY), None)
    assert read is not None
    assert read.transport_id == "smoke_detector"
    assert read.state_key == "smoke_alarm_status"


def test_builds_smoke_binary_sensor() -> None:
    sensor = next(
        e
        for e in _build_binary_sensor_entities(MagicMock(), _detector())
        if e._state_key == "smoke_alarm_status"
    )
    assert sensor._attr_device_class == BinarySensorDeviceClass.SMOKE
    assert sensor._attr_translation_key == "smoke"


def _smoke_sensor(device: EnkiDevice):
    return next(
        e
        for e in _build_binary_sensor_entities(MagicMock(), device)
        if e._state_key == "smoke_alarm_status"
    )


def test_smoke_is_on_maps_active_inactive() -> None:
    assert _smoke_sensor(_detector()).is_on is False  # INACTIVE
    active = _detector(last_reported_value={"smoke_alarm_status": "ACTIVE"})
    assert _smoke_sensor(active).is_on is True


def test_smoke_fails_to_unknown_never_clear() -> None:
    # A smoke sensor must report unknown, not "no smoke", when it has no reading
    # or an unrecognised value.
    missing = _detector(last_reported_value={})
    assert _smoke_sensor(missing).is_on is None
    unmapped = _detector(last_reported_value={"smoke_alarm_status": "WHATEVER"})
    assert _smoke_sensor(unmapped).is_on is None
