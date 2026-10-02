"""Browse a video doorbell's past calls and captures from Media (#267).

``check-videophone-events`` returns the whole history in one call, so the list is
fetched on demand rather than kept in the coordinator: a browse is a user action,
and the freshest list is the one worth showing. Media is also the only place in
Home Assistant built for browsing recordings — an attribute holding a history
would end up in the recorder on every poll.
"""

from __future__ import annotations

import mimetypes
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)

from .const import DOMAIN
from .domain.videophone import parse_videophone_captures

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import EnkiConfigEntry
    from .domain.models import EnkiDevice

# What the doorbell says it recorded, when the URL carries no usable extension.
MIME_BY_MEDIA_TYPE = {"image": "image/jpeg", "video": "video/mp4"}


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Entry point for the media_source component."""
    return EnkiMediaSource(hass)


def _title(capture: dict[str, Any]) -> str:
    """ "Missed call — 25/09 17:57", from the event type and its date."""
    label = str(capture.get("event_type") or "capture").replace("_", " ").capitalize()
    happened_at = capture.get("happened_at")
    try:
        when = datetime.fromisoformat(happened_at).strftime("%d/%m %H:%M")
    except (TypeError, ValueError):
        return label
    return f"{label} — {when}"


def _mime_type(capture: dict[str, Any]) -> str:
    url = capture.get("url") or ""
    guessed, _ = mimetypes.guess_type(urlparse(url).path)
    return guessed or MIME_BY_MEDIA_TYPE.get(capture.get("media_type"), "image/jpeg")


class EnkiMediaSource(MediaSource):
    """Lists each Enki video doorbell and the captures it still holds."""

    name = "Enki"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        if not item.identifier:
            return self._browse_root()
        entry_id, _, node_id = item.identifier.partition("/")
        if not node_id:
            raise BrowseError(f"Not a doorbell: {item.identifier}")
        return await self._browse_doorbell(entry_id, node_id)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        entry_id, _, rest = item.identifier.partition("/")
        node_id, _, stamp = rest.partition("/")
        if not stamp:
            raise Unresolvable(f"Not a capture: {item.identifier}")
        try:
            captures = await self._async_captures(entry_id, node_id)
        except BrowseError as err:
            # Only the browse path gets BrowseError translated; resolve needs its own.
            raise Unresolvable(str(err)) from err
        capture = next((c for c in captures if c["stamp"] == stamp), None)
        if capture is None:
            # The API decides how long it keeps a capture: old links drop out.
            raise Unresolvable(f"The doorbell no longer holds this capture: {stamp}")
        return PlayMedia(capture["url"], _mime_type(capture))

    def _doorbells(self) -> list[tuple[EnkiConfigEntry, EnkiDevice]]:
        found = []
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            for device in entry.runtime_data.data or []:
                if device.profile.is_videophone:
                    found.append((entry, device))
        return found

    def _device(self, entry_id: str, node_id: str) -> tuple[EnkiConfigEntry, EnkiDevice]:
        for entry, device in self._doorbells():
            if entry.entry_id == entry_id and device.node_id == node_id:
                return entry, device
        raise BrowseError(f"Unknown doorbell: {entry_id}/{node_id}")

    async def _async_captures(self, entry_id: str, node_id: str) -> list[dict[str, Any]]:
        entry, device = self._device(entry_id, node_id)
        payload = await entry.runtime_data.api.get_videophone_events(device.home_id, node_id)
        items = payload.get("items") if isinstance(payload, dict) else None
        return parse_videophone_captures(items if isinstance(items, list) else [])

    def _browse_root(self) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=self.name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry.entry_id}/{device.node_id}",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type="",
                    title=device.device_name,
                    can_play=False,
                    can_expand=True,
                )
                for entry, device in self._doorbells()
            ],
        )

    async def _browse_doorbell(self, entry_id: str, node_id: str) -> BrowseMediaSource:
        _, device = self._device(entry_id, node_id)
        captures = await self._async_captures(entry_id, node_id)
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}/{node_id}",
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=device.device_name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.IMAGE,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}/{node_id}/{capture['stamp']}",
                    media_class=(
                        MediaClass.VIDEO if capture["media_type"] == "video" else MediaClass.IMAGE
                    ),
                    media_content_type=_mime_type(capture),
                    title=_title(capture),
                    can_play=True,
                    can_expand=False,
                    thumbnail=capture["still_url"],
                )
                for capture in captures
            ],
        )
