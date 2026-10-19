"""State of a Lexman video doorbell, from its event list (#233).

``check-videophone-events`` answers ``{"items": [{"eventType", "eventDate",
"media"}]}``, newest first. ``eventType`` is one of ``ACCEPTED_CALL``,
``REJECTED_CALL``, ``MISSED_CALL``, ``CAPTURED_MEDIA``, ``GATE_OPENED`` or
``STRIKE_OPENED``; calls and captures carry a ``media.url`` snapshot, the
openings do not. The doorbell's own settings decide whether a capture is an image
or a video clip; a clip comes with a ``thumbnail``, which is the still to show
(#233). ``check-videophone-state`` answers ``{"connected", "connectors"}``.

The live view runs over the two SDP routes rather than a signaling socket, so
the pieces an offer and an answer are made of are parsed here too (#259).
"""

from __future__ import annotations

import re
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


def _newest_first(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The event list as the API means it to be read, defensively re-sorted."""
    return sorted(
        (item for item in items if isinstance(item, dict)),
        key=_event_date,
        reverse=True,
    )


def parse_videophone_events(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce the event list to the flat state keys the entities read."""
    events = _newest_first(items)
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


def parse_videophone_captures(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Past events that carry a picture or a clip, newest first (#267).

    ``stamp`` identifies a capture in a media source identifier: the event list
    has no id of its own, and ``eventDate`` is unique to the millisecond, so its
    digits make a stable URL-safe key. Openings are dropped, they carry no media
    and would show up in Media as entries that cannot be opened.
    """
    captures: list[dict[str, Any]] = []
    for item in _newest_first(items):
        media = _media(item)
        if media is None:
            continue
        captures.append(
            {
                "stamp": "".join(c for c in _event_date(item) if c.isdigit()),
                "event_type": item.get("eventType"),
                "happened_at": _event_date(item) or None,
                "media_type": media.get("type"),
                "url": _url(media, "url"),
                "still_url": _still_url(media),
            }
        )
    return captures


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


def unescape_sdp(sdp: str) -> str:
    """Real line breaks from the escaped ones the doorbell sends (#259).

    The answer comes back with its newlines written out rather than sent, so it
    reads as one line and no peer would take it. The app substitutes them before
    ``setRemoteDescription`` (APK ``s0e``), through a plain string replace of
    ``\\r\\n``; this accepts the single-escaped form as well. An answer that
    already carries real line breaks has nothing to match and comes back as is.
    """
    return re.sub(r"(?:\\+r)?\\+n", "\r\n", sdp)


def _normalized_sdp(sdp: str) -> str:
    """One comparable form, whatever escaping and line endings it arrived with."""
    return unescape_sdp(sdp).replace("\r\n", "\n").strip()


def offer_candidates(sdp: str) -> list[dict[str, Any]]:
    """The candidates an offer already carries, for the POST body (#259).

    Home Assistant's frontend appends the candidates it has gathered by the time
    it sends the offer to the SDP itself, and trickles the rest afterwards. The
    doorbell takes them in a list beside the SDP, keyed by their m-section, so
    the embedded ones are read back out.
    """
    found: list[dict[str, Any]] = []
    index = -1
    mid: str | None = None
    for line in unescape_sdp(sdp).splitlines():
        if line.startswith("m="):
            index += 1
            mid = None
        elif line.startswith("a=mid:"):
            mid = line[6:].strip() or None
        elif line.startswith("a=candidate:"):
            found.append(
                {"candidate": line[2:].strip(), "sdpMid": mid, "sdpMLineIndex": max(index, 0)}
            )
    return found


def parse_sdp_answer(
    payload: dict[str, Any], *, offered: str
) -> tuple[str, list[dict[str, Any]]] | None:
    """The doorbell's answer, or None while the mailbox holds nothing of ours (#259).

    ``check-sdp-candidates-info`` is one slot per node: a poll can read back the
    very offer that was just deposited there. An offer is not an answer, it
    carries ``a=setup:actpass``, where an answer commits to a role, and it is
    the string we sent, so either tell is enough to keep polling.
    """
    if not isinstance(payload, dict):
        return None
    sdp = payload.get("sdp")
    if not isinstance(sdp, str) or not sdp.strip():
        return None
    sdp = unescape_sdp(sdp)
    if _normalized_sdp(sdp) == _normalized_sdp(offered) or "a=setup:actpass" in sdp:
        return None
    items = payload.get("candidates")
    candidates = [
        {
            "candidate": item["candidate"],
            "sdpMid": item.get("sdpMid"),
            "sdpMLineIndex": item.get("sdpMLineIndex"),
        }
        for item in (items if isinstance(items, list) else [])
        if isinstance(item, dict) and isinstance(item.get("candidate"), str)
    ]
    return sdp, candidates
