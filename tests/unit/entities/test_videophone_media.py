"""Browsing the video doorbell's past captures from Media (#267)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.domain.videophone import parse_videophone_captures
from enki.media_source import EnkiMediaSource
from homeassistant.components.media_player import BrowseError
from homeassistant.components.media_source import MediaSourceItem, Unresolvable

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

VIDEOPHONE_CAPABILITIES = ["check_videophone_state", "check_videophone_media_events"]

# A clip: the picture to show is the thumbnail, the URL to play is the video.
CLIP_EVENT = {
    "eventType": "CAPTURED_MEDIA",
    "media": {
        "type": "video",
        "url": "https://cdn/clip.mp4",
        "thumbnail": "https://cdn/clip-thumb.jpg",
    },
    "eventDate": "2026-09-26T08:12:04.500+02:00",
}


def _doorbell() -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-vp",
        device_name="Interphone",
        device_type="videophones",
        is_enabled=True,
        state="ACTIVE",
        capabilities=VIDEOPHONE_CAPABILITIES,
    )


def _source(events: list[dict] | None = None) -> tuple[EnkiMediaSource, AsyncMock]:
    device = _doorbell()
    get_events = AsyncMock(return_value={"items": events if events is not None else REAL_EVENTS})
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.runtime_data.data = [device]
    entry.runtime_data.api.get_videophone_events = get_events
    hass = MagicMock()
    hass.config_entries.async_loaded_entries = lambda domain: [entry]
    return EnkiMediaSource(hass), get_events


def test_captures_keep_only_events_that_carry_media() -> None:
    captures = parse_videophone_captures([*REAL_EVENTS, CLIP_EVENT])

    # The two openings carry no media and must not show up as dead entries.
    assert [c["event_type"] for c in captures] == [
        "CAPTURED_MEDIA",
        "MISSED_CALL",
        "ACCEPTED_CALL",
    ]
    assert captures[0]["stamp"] == "202609260812045000200"
    assert captures[0]["url"] == "https://cdn/clip.mp4"
    assert captures[0]["still_url"] == "https://cdn/clip-thumb.jpg"


def test_captures_of_an_empty_history() -> None:
    assert parse_videophone_captures([]) == []


@pytest.mark.asyncio
async def test_root_lists_the_doorbells() -> None:
    source, get_events = _source()

    root = await source.async_browse_media(MediaSourceItem(identifier=""))

    assert [child.title for child in root.children] == ["Interphone"]
    assert root.children[0].identifier == "entry-1/node-vp"
    # Listing devices must not call the cloud — only opening one does.
    get_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_doorbell_lists_its_captures_newest_first() -> None:
    source, _ = _source([*REAL_EVENTS, CLIP_EVENT])

    listing = await source.async_browse_media(MediaSourceItem(identifier="entry-1/node-vp"))

    assert [child.title for child in listing.children] == [
        "Captured media — 26/09 08:12",
        "Missed call — 25/09 17:57",
        "Accepted call — 25/09 17:56",
    ]
    clip, picture = listing.children[0], listing.children[1]
    assert (clip.media_class, clip.media_content_type) == ("video", "video/mp4")
    assert clip.thumbnail == "https://cdn/clip-thumb.jpg"
    assert (picture.media_class, picture.media_content_type) == ("image", "image/jpeg")


@pytest.mark.asyncio
async def test_resolving_a_capture_plays_the_media_not_the_thumbnail() -> None:
    source, _ = _source([CLIP_EVENT])
    stamp = parse_videophone_captures([CLIP_EVENT])[0]["stamp"]

    item = MediaSourceItem(identifier=f"entry-1/node-vp/{stamp}")
    played = await source.async_resolve_media(item)

    assert (played.url, played.mime_type) == ("https://cdn/clip.mp4", "video/mp4")


@pytest.mark.asyncio
async def test_an_expired_capture_is_unresolvable() -> None:
    source, _ = _source()

    with pytest.raises(Unresolvable):
        item = MediaSourceItem(identifier="entry-1/node-vp/19990101000000")
        await source.async_resolve_media(item)


@pytest.mark.asyncio
async def test_an_unknown_doorbell_fails_the_browse_not_the_resolve() -> None:
    """Browsing is only caught as BrowseError; Unresolvable would surface as a crash."""
    source, _ = _source()

    with pytest.raises(BrowseError):
        await source.async_browse_media(MediaSourceItem(identifier="entry-1/node-gone"))

    with pytest.raises(Unresolvable):
        await source.async_resolve_media(MediaSourceItem(identifier="entry-1/node-gone/1"))
