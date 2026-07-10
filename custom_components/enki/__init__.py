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
from .notifications import EnkiNotifier, notify_for_connection_error

if TYPE_CHECKING:
    from .coordinator import EnkiCoordinator

__version__ = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))[
    "version"
]

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.FAN,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type EnkiConfigEntry = ConfigEntry[EnkiCoordinator]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entries (required on this module for HA 2026.x+)."""
    from .migration import async_migrate_entry as migrate_entry

    return await migrate_entry(hass, config_entry)


async def async_setup_entry(hass: HomeAssistant, entry: EnkiConfigEntry) -> bool:
    from .coordinator import EnkiCoordinator

    coordinator = EnkiCoordinator(hass, entry)
    notifier = EnkiNotifier(hass, entry)

    try:
        await coordinator.api.async_connect()
    except EnkiAuthError as err:
        notifier.notify_auth_failed()
        raise ConfigEntryNotReady(f"Invalid Enki credentials: {err}") from err
    except EnkiConnectionError as err:
        notify_for_connection_error(notifier, err)
        raise ConfigEntryNotReady(f"Cannot reach Enki cloud: {err}") from err

    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()

    from .telemetry import async_handle_telemetry_nudge

    await async_handle_telemetry_nudge(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: EnkiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EnkiConfigEntry) -> bool:
    EnkiNotifier(hass, entry).dismiss_all()
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
