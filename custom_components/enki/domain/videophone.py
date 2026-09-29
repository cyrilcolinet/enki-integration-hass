"""State of a Lexman video doorbell, from its event list (#233).

``check-videophone-events`` answers ``{"items": [{"eventType", "eventDate",
"media"}]}``, newest first. ``eventType`` is one of ``ACCEPTED_CALL``,
``REJECTED_CALL``, ``MISSED_CALL``, ``CAPTURED_MEDIA``, ``GATE_OPENED`` or
``STRIKE_OPENED``; calls and captures carry a ``media.url`` snapshot, the
openings do not. The doorbell's own settings decide whether a capture is an image
or a video clip; a clip comes with a ``thumbnail``, which is the still to show
(#233). ``check-videophone-state`` answers ``{"connected", "connectors"}``.
"""

from __future__ import annotations

from typing import Any

ACCEPTED_CALL = "ACCEPTED_CALL"
REJECTED_CALL = "REJECTED_CALL"
MISSED_CALL = "MISSED_CALL"
CAPTURED_MEDIA = "CAPTURED_MEDIA"
GATE_OPENED = "GATE_OPENED"
STRIKE_OPENED = "STRIKE_OPENED"

# What the doorbell can report: the HA event entity offers exactly these.
VIDEOPHONE_EVENT_TYPES = (
    ACCEPTED_CALL,
    REJECTED_CALL,
    MISSED_CALL,
    CAPTURED_MEDIA,
    GATE_OPENED,
    STRIKE_OPENED,
)
CALL_TYPES = frozenset({ACCEPTED_CALL, REJECTED_CALL, MISSED_CALL})


def _event_date(item: dict[str, Any]) -> str:
    value = item.get("eventDate")
    return value if isinstance(value, str) else ""


def _url(media: dict[str, Any], field: str) -> str | None:
    value = media.get(field)
    return value if isinstance(value, str) and value else None


def _media(item: dict[str, Any]) -> dict[str, Any] | None:
    media = item.get("media")
    return media if isinstance(media, dict) and _url(media, "url") else None


def _still_url(media: dict[str, Any]) -> str | None:
    """What to show as a picture: the capture itself, or a clip's thumbnail."""
    if media.get("type") == "video":
        return _url(media, "thumbnail")
    return _url(media, "url")


def parse_videophone_events(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce the event list to the flat state keys the entities read."""
    events = sorted(
        (item for item in items if isinstance(item, dict)),
        key=_event_date,
        reverse=True,
    )
    if not events:
        return {}

    state: dict[str, Any] = {
        "videophone_last_event_type": events[0].get("eventType"),
        "videophone_last_event_at": _event_date(events[0]) or None,
    }

    call = next((e for e in events if e.get("eventType") in CALL_TYPES), None)
    if call is not None:
        state["videophone_last_call_type"] = call.get("eventType")
        state["videophone_last_call_at"] = _event_date(call) or None

    media = next((found for e in events if (found := _media(e))), None)
    if media is not None:
        state["videophone_last_media_type"] = media.get("type")
        state["videophone_last_media_url"] = _url(media, "url")
        still = _still_url(media)
        if still is not None:
            state["videophone_last_image_url"] = still

    return state


def parse_videophone_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten check-videophone-state into the state keys the entities read."""
    if not isinstance(payload, dict):
        return {}
    state: dict[str, Any] = {}
    if isinstance(payload.get("connected"), bool):
        state["videophone_connected"] = payload["connected"]
    if isinstance(payload.get("connectors"), str):
        state["videophone_connectors"] = payload["connectors"]
    return state
