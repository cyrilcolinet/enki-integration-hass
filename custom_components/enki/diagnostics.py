"""Diagnostics support for the Enki integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import __version__
from .const import CONF_TELEMETRY, CONF_USERNAME
from .device_profile import profile_to_export_dict

TO_REDACT = {CONF_USERNAME, "username", "password", "home_id", "node_id", "device_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    ha_version = hass.config.version
    devices = coordinator.data or []

    profiles = [
        profile_to_export_dict(
            record,
            integration_version=__version__,
            ha_version=ha_version,
        )
        for record in coordinator.api.discovery_records
    ]

    payload: dict[str, Any] = {
        "integration_version": __version__,
        "telemetry_enabled": entry.options.get(CONF_TELEMETRY, False),
        "device_count": len(devices),
        "discovery_profiles": profiles,
    }
    return async_redact_data(payload, TO_REDACT)
