"""Camera platform: last-event snapshot for Lexman cameras.

Live video is not wired yet: earlier Lexman cameras stream over TUTK Kalay P2P
(native SDK, out of reach here), while the meari generation uses WebRTC over the
meari signaling WebSocket (see docs/API.md). Meanwhile the event list carries a
snapshot URL for each motion event — surfaced as a still image so Home Assistant
shows the latest detection.
"""

from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiEventSnapshotCamera(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_camera
    )


class EnkiEventSnapshotCamera(EnkiEntity, Camera):
    """Still image of the camera's most recent motion event."""

    _attr_translation_key = "event_snapshot"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        EnkiEntity.__init__(self, coordinator, device)
        Camera.__init__(self)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-event-snapshot"
        self._cache: tuple[str, bytes] | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        url = self._device.reported.camera_last_image_url
        if not url:
            return None
        if self._cache is not None and self._cache[0] == url:
            return self._cache[1]
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    LOGGER.debug("Camera snapshot HTTP %s for %s", response.status, self.node_id)
                    return self._cache[1] if self._cache else None
                data = await response.read()
        except Exception as err:  # noqa: BLE001 - a broken snapshot must not crash HA
            LOGGER.debug("Camera snapshot fetch failed for %s: %s", self.node_id, err)
            return self._cache[1] if self._cache else None
        self._cache = (url, data)
        return data
