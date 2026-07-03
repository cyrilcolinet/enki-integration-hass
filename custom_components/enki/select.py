"""Select platform for Enki fil pilote (pilot wire) controllers."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.heating import pilot_wire_api_value, pilot_wire_option_slug, pilot_wire_options


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiPilotWireSelect(coordinator, device)
        for device in coordinator.data or []
        if device.profile.is_pilot_wire
    )


class EnkiPilotWireSelect(EnkiEntity, SelectEntity):
    """Fil pilote mode selector (Confort, Éco, Hors gel, Off, …)."""

    _attr_has_entity_name = True
    _attr_translation_key = "pilot_wire"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-pilot-wire"
        self._attr_options = pilot_wire_options(device.profile.possible_values)

    @property
    def current_option(self) -> str | None:
        value = self._device.reported.pilot_wire_state
        if not isinstance(value, str):
            return None
        slug = pilot_wire_option_slug(value)
        if slug in self._attr_options:
            return slug
        return None

    async def async_select_option(self, option: str) -> None:
        api_value = pilot_wire_api_value(option)
        await self.coordinator.api.async_set_pilot_wire_mode(
            self._device.home_id,
            self._device.node_id,
            api_value,
        )
        self.coordinator.update_cached_value(self.node_id, "pilot_wire_state", api_value)
