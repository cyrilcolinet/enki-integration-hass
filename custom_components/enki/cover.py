"""Cover platform for Enki roller shutters (beta)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.shutter import (
    roller_shutter_state_is_closing,
    roller_shutter_state_is_opening,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiCoverEntity(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_cover
    )


class EnkiCoverEntity(EnkiEntity, CoverEntity):
    """Roller shutter via api-enki-rolling-prod (beta)."""

    _attr_translation_key = "roller_shutter"
    _attr_device_class = CoverDeviceClass.SHUTTER

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-cover"
        self._supports_position = device.profile.supports_shutter_position
        self._supports_stop = device.profile.supports_shutter_stop

    @property
    def supported_features(self) -> CoverEntityFeature:
        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if self._supports_position:
            features |= CoverEntityFeature.SET_POSITION
        if self._supports_stop:
            features |= CoverEntityFeature.STOP
        return features

    @property
    def current_cover_position(self) -> int | None:
        if not self._supports_position:
            return None
        return self._device.reported.shutter_position

    @property
    def is_closed(self) -> bool | None:
        reported = self._device.reported
        if reported.shutter_opening is not None:
            return reported.shutter_opening == "CLOSED"
        position = reported.shutter_position
        if position is not None:
            return position <= 0
        return None

    @property
    def is_opening(self) -> bool | None:
        return roller_shutter_state_is_opening(self._device.reported.roller_shutter_state)

    @property
    def is_closing(self) -> bool | None:
        return roller_shutter_state_is_closing(self._device.reported.roller_shutter_state)

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._set_position(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._set_position(0)

    async def async_set_cover_position(self, position: int, **kwargs: Any) -> None:
        await self._set_position(position)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        home_id = self._device.home_id
        node_id = self._device.node_id
        await self.coordinator.api.async_stop_shutter(home_id, node_id)
        self.coordinator.update_cached_value(node_id, "roller_shutter_state", "STOPPED")

    async def _set_position(self, position: int) -> None:
        clamped = max(0, min(100, position))
        home_id = self._device.home_id
        node_id = self._device.node_id
        await self.coordinator.api.async_set_shutter_position(home_id, node_id, clamped)
        self.coordinator.update_cached_value(node_id, "shutter_position", clamped)
        if clamped <= 0:
            self.coordinator.update_cached_value(node_id, "shutter_opening", "CLOSED")
        elif clamped >= 100:
            self.coordinator.update_cached_value(node_id, "shutter_opening", "OPEN")
