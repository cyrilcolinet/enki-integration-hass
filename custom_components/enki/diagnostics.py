"""Diagnostics support for the Enki integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import __version__
from .const import CONF_TELEMETRY
from .domain.profile import profile_fingerprint, profile_to_export_dict
from .domain.telemetry_enrichment import enrich_telemetry_export

TO_REDACT = {CONF_USERNAME, "username", "password", "home_id", "node_id", "device_id"}


def _ha_version() -> str:
    """Resolve HA version without ``hass.config.version`` (does not exist)."""
    import homeassistant.const as ha_const

    return str(getattr(ha_const, "__version__", "unknown"))


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    del hass  # Required by HA platform signature.
    coordinator = entry.runtime_data
    devices = coordinator.data or []
    ha_version = _ha_version()

    profiles = []
    for record in coordinator.api.discovery_records:
        export = profile_to_export_dict(
            record,
            integration_version=__version__,
            ha_version=ha_version,
        )
        fingerprint = profile_fingerprint(export)
        profiles.append(
            enrich_telemetry_export(
                export,
                record,
                api_read_errors=coordinator.api.read_errors_for_fingerprint(fingerprint) or None,
                last_poll_state=coordinator.api.poll_state_for_fingerprint(fingerprint) or None,
            )
        )

    payload: dict[str, Any] = {
        "integration_version": __version__,
        "telemetry_enabled": entry.options.get(CONF_TELEMETRY, False),
        "device_count": len(devices),
        "discovery_profiles": profiles,
    }
    return async_redact_data(payload, TO_REDACT)
