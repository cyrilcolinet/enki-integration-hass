"""Event platform for the Lexman video doorbell (#233).

The doorbell has no push channel we can subscribe to: its calls and openings are
read from the event list on each poll, so the entity fires when a newer event
appears — a ring shows up within a polling cycle, not instantly.
"""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .domain.videophone import VIDEOPHONE_EVENT_TYPES
from .entity import EnkiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiVideophoneEvent(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_videophone
    )


class EnkiVideophoneEvent(EnkiEntity, EventEntity):
    """Rings, answered and missed calls, gate and door openings."""

    _attr_translation_key = "videophone"
    _attr_event_types = [event.lower() for event in VIDEOPHONE_EVENT_TYPES]

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-videophone-event"
        # The event read on startup is history, not something that just happened.
        self._last_seen_at = device.reported.videophone_last_event_at

    @callback
    def _handle_coordinator_update(self) -> None:
        updated = self.coordinator.get_device_by_node(self.node_id)
        if updated is not None:
            self._device = updated
        reported = self._device.reported
        happened_at = reported.videophone_last_event_at
        event_type = (reported.videophone_last_event_type or "").lower()
        if happened_at and happened_at != self._last_seen_at:
            self._last_seen_at = happened_at
            if event_type in self._attr_event_types:
                self._trigger_event(
                    event_type,
                    {
                        "happened_at": happened_at,
                        "image_url": reported.videophone_last_image_url,
                        # A capture can be a clip: the picture above is then its
                        # thumbnail, and the clip itself is here.
                        "media_type": reported.videophone_last_media_type,
                        "media_url": reported.videophone_last_media_url,
                    },
                )
        self.async_write_ha_state()
