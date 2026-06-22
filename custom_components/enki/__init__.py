"""Enki integration for Home Assistant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .exceptions import EnkiAuthError, EnkiConnectionError

if TYPE_CHECKING:
    from .coordinator import EnkiCoordinator

__version__ = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))[
    "version"
]

PLATFORMS: list[Platform] = [Platform.FAN, Platform.LIGHT]

type EnkiConfigEntry = ConfigEntry[EnkiCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EnkiConfigEntry) -> bool:
    from .coordinator import EnkiCoordinator

    coordinator = EnkiCoordinator(hass, entry)

    try:
        await coordinator.api.async_connect()
    except EnkiAuthError as err:
        raise ConfigEntryNotReady(f"Invalid Enki credentials: {err}") from err
    except EnkiConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot reach Enki cloud: {err}") from err

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: EnkiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EnkiConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.api.async_close()
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: EnkiConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removing orphaned devices from the UI."""
    return True
