"""Lexman camera: event parsing + entities (#135)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.binary_sensor import _build_binary_sensor_entities
from enki.domain.camera_events import parse_camera_events
from enki.domain.models import EnkiDevice
from enki.sensor import (
    EnkiCameraLastEventSensor,
    EnkiCameraLastMotionSensor,
    _build_sensor_entities,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

_ITEMS = [
    {
        "type": "CAMERA_MOVEMENT",
        "id": "a",
        "image": "https://cdn/1.jpg",
        "createdAt": "2026-08-09T05:56:53.000Z",
    },
    {
        "type": "CAMERA_MOVEMENT",
        "id": "b",
        "image": "https://cdn/2.jpg",
        "createdAt": "2026-08-09T05:50:15.000Z",
    },
    {"type": "SD_WORKING", "id": "c", "image": None, "createdAt": "2026-08-07T21:09:22.139Z"},
]


def _camera(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "IPC176KF",
        "node_id": "node-cam",
        "device_name": "Camera",
        "device_type": "cameras",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "check_camera_events",
            "check_camera_last_event",
            "remove_camera_events",
        ],
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_parse_picks_latest_event_motion_image_and_sd() -> None:
    state = parse_camera_events(_ITEMS)
    assert state["camera_last_event_type"] == "CAMERA_MOVEMENT"
    assert state["camera_last_event_at"] == "2026-08-09T05:56:53.000Z"
    assert state["camera_last_motion_at"] == "2026-08-09T05:56:53.000Z"
    assert state["camera_last_image_url"] == "https://cdn/1.jpg"
    assert state["camera_sd_removed"] is False


def test_parse_sorts_unordered_and_flags_sd_removed() -> None:
    items = [
        {"type": "SD_REMOVED", "createdAt": "2026-08-10T10:00:00Z", "image": None},
        {"type": "CAMERA_MOVEMENT", "createdAt": "2026-08-10T09:00:00Z", "image": "https://cdn/x"},
    ]
    state = parse_camera_events(items)
    assert state["camera_last_event_type"] == "SD_REMOVED"
    assert state["camera_sd_removed"] is True
    assert state["camera_last_motion_at"] == "2026-08-10T09:00:00Z"


def test_parse_empty_returns_empty() -> None:
    assert parse_camera_events([]) == {}


def test_profile_is_camera() -> None:
    assert _camera().profile.is_camera is True


def test_camera_events_read_routes_via_camera_service() -> None:
    read = next((r for r in CAPABILITY_READS if r.capability == "check_camera_events"), None)
    # events are read through a dedicated path, not the generic CapabilityRead table
    assert read is None


def test_builds_camera_sensors() -> None:
    entities = _build_sensor_entities(MagicMock(), _camera())
    kinds = {type(e) for e in entities}
    assert EnkiCameraLastMotionSensor in kinds
    assert EnkiCameraLastEventSensor in kinds


def test_last_motion_sensor_parses_timestamp() -> None:
    device = _camera(last_reported_value={"camera_last_motion_at": "2026-08-09T05:56:53+00:00"})
    sensor = EnkiCameraLastMotionSensor(MagicMock(), device)
    assert sensor.native_value is not None
    assert sensor.native_value.year == 2026


def test_builds_sd_card_binary_sensor() -> None:
    device = _camera(last_reported_value={"camera_sd_removed": True})
    sd = next(
        e
        for e in _build_binary_sensor_entities(MagicMock(), device)
        if e._state_key == "camera_sd_removed"
    )
    assert sd._attr_device_class == BinarySensorDeviceClass.PROBLEM
    assert sd.is_on is True

    ok = _camera(last_reported_value={"camera_sd_removed": False})
    sd_ok = next(
        e
        for e in _build_binary_sensor_entities(MagicMock(), ok)
        if e._state_key == "camera_sd_removed"
    )
    assert sd_ok.is_on is False
