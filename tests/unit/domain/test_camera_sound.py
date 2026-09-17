"""Sound detection on Lexman cameras that report it (#212)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.domain.camera_events import parse_camera_events
from enki.domain.models import EnkiDevice
from enki.sensor import EnkiCameraLastSoundSensor, _build_sensor_entities


def _camera(values: list[str]) -> EnkiDevice:
    # Shape reported by the IPC167KF telemetry issue.
    return EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node-cam",
        device_name="Caméra salon",
        device_type="cameras",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["check_camera_events", "check_camera_last_event"],
        possible_values={"check_camera_last_event": {"values": values}},
        last_reported_value={"camera_last_sound_at": "2026-09-16T22:10:00.000Z"},
    )


def test_parser_keeps_the_latest_sound_event() -> None:
    state = parse_camera_events(
        [
            {"type": "CAMERA_MOVEMENT", "createdAt": "2026-09-16T22:18:39.000Z"},
            {"type": "SOUND_DETECTED", "createdAt": "2026-09-16T22:10:00.000Z"},
            {"type": "SOUND_DETECTED", "createdAt": "2026-09-16T21:00:00.000Z"},
        ]
    )
    assert state["camera_last_sound_at"] == "2026-09-16T22:10:00.000Z"
    # Sound never counts as motion.
    assert state["camera_last_motion_at"] == "2026-09-16T22:18:39.000Z"


def test_no_sound_key_without_sound_events() -> None:
    state = parse_camera_events([{"type": "CAMERA_MOVEMENT", "createdAt": "2026-09-16T22:18:39Z"}])
    assert "camera_last_sound_at" not in state


def test_sound_sensor_created_when_the_camera_reports_sound() -> None:
    device = _camera(["CAMERA_MOVEMENT", "SD_REMOVED", "SD_WORKING", "SOUND_DETECTED"])
    sensors = [
        e
        for e in _build_sensor_entities(MagicMock(), device)
        if isinstance(e, EnkiCameraLastSoundSensor)
    ]
    assert len(sensors) == 1
    assert sensors[0].native_value is not None


def test_no_sound_sensor_on_a_camera_without_microphone() -> None:
    device = _camera(["CAMERA_MOVEMENT", "SD_REMOVED", "SD_WORKING"])
    assert not any(
        isinstance(e, EnkiCameraLastSoundSensor)
        for e in _build_sensor_entities(MagicMock(), device)
    )
