"""Derive camera state from the Lexman event list (api-enki-lexman-camera-prod).

The events endpoint returns ``{"items": [{"type", "createdAt", "image", "id"}]}``
newest-first, where ``type`` is one of ``CAMERA_MOVEMENT`` / ``SD_WORKING`` /
``SD_REMOVED`` and movement events carry an ``image`` snapshot URL.
"""

from __future__ import annotations

from typing import Any

MOVEMENT = "CAMERA_MOVEMENT"
SD_REMOVED = "SD_REMOVED"
SD_WORKING = "SD_WORKING"
_SD_TYPES = {SD_WORKING, SD_REMOVED}


def _created_at(item: dict[str, Any]) -> str:
    value = item.get("createdAt")
    return value if isinstance(value, str) else ""


def parse_camera_events(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce the raw event list to the flat state keys the entities read."""
    events = sorted(
        (item for item in items if isinstance(item, dict)),
        key=_created_at,
        reverse=True,
    )
    if not events:
        return {}

    state: dict[str, Any] = {
        "camera_last_event_type": events[0].get("type"),
        "camera_last_event_at": _created_at(events[0]) or None,
    }

    motion = next((e for e in events if e.get("type") == MOVEMENT), None)
    if motion is not None:
        state["camera_last_motion_at"] = _created_at(motion) or None

    image = next((e.get("image") for e in events if e.get("image")), None)
    if isinstance(image, str) and image:
        state["camera_last_image_url"] = image

    sd_event = next((e for e in events if e.get("type") in _SD_TYPES), None)
    if sd_event is not None:
        state["camera_sd_removed"] = sd_event.get("type") == SD_REMOVED

    return state
