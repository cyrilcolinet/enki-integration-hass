"""Lexman video doorbell: calls, snapshot and connection (#233)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.camera import EnkiVideophoneCamera, _camera_class
from enki.domain.models import EnkiDevice
from enki.domain.videophone import parse_videophone_events, parse_videophone_state
from enki.event import EnkiVideophoneEvent

# check-videophone-events as the reporter's doorbell returned it, newest first.
REAL_EVENTS = [
    {
        "eventType": "MISSED_CALL",
        "media": {"type": "image", "url": "https://cdn/missed.jpg", "thumbnail": None},
        "eventDate": "2026-09-25T17:57:28.347+02:00",
    },
    {"eventType": "GATE_OPENED", "media": None, "eventDate": "2026-09-25T17:57:23.182+02:00"},
    {"eventType": "STRIKE_OPENED", "media": None, "eventDate": "2026-09-25T17:57:17.815+02:00"},
    {
        "eventType": "ACCEPTED_CALL",
        "media": {"type": "image", "url": "https://cdn/accepted.jpg", "thumbnail": None},
        "eventDate": "2026-09-25T17:56:25.092+02:00",
    },
]

VIDEOPHONE_CAPABILITIES = [
    "change_portal_state",
    "change_videophone_config",
    "check_portal_state",
    "check_videophone_call",
    "check_videophone_connector",
    "check_videophone_media_events",
    "check_videophone_state",
]


def _doorbell(**reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-vp",
        device_name="Interphone",
        device_type="videophones",
        is_enabled=True,
        state="ACTIVE",
        capabilities=VIDEOPHONE_CAPABILITIES,
        last_reported_value=reported,
    )


def _coordinator(device: EnkiDevice) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    return coordinator


def test_events_give_the_last_call_and_its_snapshot() -> None:
    state = parse_videophone_events(REAL_EVENTS)
    assert state["videophone_last_event_type"] == "MISSED_CALL"
    assert state["videophone_last_event_at"] == "2026-09-25T17:57:28.347+02:00"
    # Openings carry no media, so the picture comes from the call itself.
    assert state["videophone_last_image_url"] == "https://cdn/missed.jpg"
    assert state["videophone_last_call_type"] == "MISSED_CALL"
    assert parse_videophone_events([]) == {}


def test_an_opening_does_not_hide_the_previous_call() -> None:
    openings_last = [REAL_EVENTS[1], REAL_EVENTS[3]]
    state = parse_videophone_events(openings_last)
    assert state["videophone_last_event_type"] == "GATE_OPENED"
    assert state["videophone_last_call_type"] == "ACCEPTED_CALL"
    assert state["videophone_last_image_url"] == "https://cdn/accepted.jpg"


# The doorbell's settings can capture a clip instead of a picture (#233).
VIDEO_CAPTURE = [
    {
        "eventType": "CAPTURED_MEDIA",
        "media": {"type": "video", "url": "https://cdn/clip.mp4", "thumbnail": "https://cdn/t.jpg"},
        "eventDate": "2026-09-29T13:34:54.000+02:00",
    }
]


def test_a_video_capture_shows_its_thumbnail_and_keeps_the_clip() -> None:
    state = parse_videophone_events(VIDEO_CAPTURE)
    # The camera would choke on an MP4, so the picture is the thumbnail.
    assert state["videophone_last_image_url"] == "https://cdn/t.jpg"
    assert state["videophone_last_media_url"] == "https://cdn/clip.mp4"
    assert state["videophone_last_media_type"] == "video"


def test_an_image_capture_is_its_own_picture() -> None:
    state = parse_videophone_events(REAL_EVENTS)
    assert state["videophone_last_image_url"] == "https://cdn/missed.jpg"
    assert state["videophone_last_media_url"] == "https://cdn/missed.jpg"
    assert state["videophone_last_media_type"] == "image"


def test_a_clip_without_thumbnail_leaves_the_camera_empty() -> None:
    no_thumb = [{**VIDEO_CAPTURE[0], "media": {"type": "video", "url": "https://cdn/clip.mp4"}}]
    state = parse_videophone_events(no_thumb)
    assert "videophone_last_image_url" not in state
    assert state["videophone_last_media_url"] == "https://cdn/clip.mp4"


def test_state_read_gives_connection_and_connectors() -> None:
    assert parse_videophone_state({"connected": True, "connectors": "none"}) == {
        "videophone_connected": True,
        "videophone_connectors": "none",
    }
    assert parse_videophone_state({"connected": "yes"}) == {}


def test_the_doorbell_gets_its_own_snapshot_camera() -> None:
    device = _doorbell(videophone_last_image_url="https://cdn/missed.jpg")
    assert _camera_class(device) is EnkiVideophoneCamera
    camera = EnkiVideophoneCamera(_coordinator(device), device)
    assert camera._image_url_field == "videophone_last_image_url"


def test_a_new_call_fires_the_event_but_history_does_not() -> None:
    device = _doorbell(
        videophone_last_event_type="ACCEPTED_CALL",
        videophone_last_event_at="2026-09-25T17:56:25.092+02:00",
    )
    entity = EnkiVideophoneEvent(_coordinator(device), device)
    entity.async_write_ha_state = MagicMock()
    entity._trigger_event = MagicMock()

    # First refresh: same event as at startup, nothing happened since.
    entity._handle_coordinator_update()
    entity._trigger_event.assert_not_called()

    ringing = _doorbell(
        videophone_last_event_type="MISSED_CALL",
        videophone_last_event_at="2026-09-25T17:57:28.347+02:00",
        videophone_last_image_url="https://cdn/missed.jpg",
    )
    entity.coordinator.get_device_by_node = lambda node_id: ringing
    entity._handle_coordinator_update()
    event_type, attributes = entity._trigger_event.call_args.args
    assert event_type == "missed_call"
    assert attributes["image_url"] == "https://cdn/missed.jpg"
