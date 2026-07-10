"""Config entry migration from legacy CyrilP/hass-enki-component setups."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_SCAN_INTERVAL

LEGACY_TITLE_PREFIX = "Enki - "
LEGACY_POWER_SENSOR_SUFFIX = "-power_production"
CURRENT_POWER_SENSOR_SUFFIX = "-power-production"


def is_legacy_config_entry(config_entry: ConfigEntry) -> bool:
    """True when the entry still uses the legacy CyrilP config shape."""
    unique_id = config_entry.unique_id or ""
    return CONF_SCAN_INTERVAL in config_entry.data or unique_id.startswith(LEGACY_TITLE_PREFIX)


def migrate_config_entry_fields(
    *,
    data: dict[str, Any],
    options: dict[str, Any],
    unique_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """Move legacy fields to the current config-entry schema."""
    migrated_data = dict(data)
    migrated_options = dict(options)
    migrated_unique_id = unique_id

    if CONF_SCAN_INTERVAL in migrated_data:
        migrated_options.setdefault(CONF_SCAN_INTERVAL, migrated_data.pop(CONF_SCAN_INTERVAL))

    username = migrated_data.get(CONF_USERNAME)
    if username and (
        migrated_unique_id is None or str(migrated_unique_id).startswith(LEGACY_TITLE_PREFIX)
    ):
        migrated_unique_id = str(username).lower()

    return migrated_data, migrated_options, migrated_unique_id


def migrate_power_sensor_unique_id(unique_id: str) -> str | None:
    """Map legacy solar sensor IDs to the current hyphenated suffix."""
    if not unique_id.endswith(LEGACY_POWER_SENSOR_SUFFIX):
        return None
    return unique_id[: -len(LEGACY_POWER_SENSOR_SUFFIX)] + CURRENT_POWER_SENSOR_SUFFIX


def migrate_legacy_entity_unique_ids(
    registry: er.EntityRegistry,
    entry_id: str,
) -> None:
    """Rename legacy entity unique IDs for this config entry."""
    for entity in er.async_entries_for_config_entry(registry, entry_id):
        if entity.unique_id is None:
            continue
        new_unique_id = migrate_power_sensor_unique_id(entity.unique_id)
        if new_unique_id is not None:
            registry.async_update_entity(
                entity.entity_id,
                new_unique_id=new_unique_id,
            )


async def async_migrate_legacy_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Apply legacy config and entity registry migrations."""
    data, options, unique_id = migrate_config_entry_fields(
        data=config_entry.data,
        options=config_entry.options,
        unique_id=config_entry.unique_id,
    )
    migrate_legacy_entity_unique_ids(er.async_get(hass), config_entry.entry_id)

    if (
        data == config_entry.data
        and options == config_entry.options
        and unique_id == config_entry.unique_id
    ):
        return

    hass.config_entries.async_update_entry(
        config_entry,
        data=data,
        options=options,
        unique_id=unique_id,
    )


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate a config entry to the current schema.

    Home Assistant 2026.x resolves this on the integration module (__init__.py),
    not on the config flow class.
    """
    if config_entry.version >= 2:
        return True

    await async_migrate_legacy_entry(hass, config_entry)
    hass.config_entries.async_update_entry(config_entry, version=2)
    return True


def resolve_scan_interval(config_entry: ConfigEntry) -> int:
    """Read polling interval from options, with legacy data fallback."""
    from .const import DEFAULT_SCAN_INTERVAL

    interval = config_entry.options.get(CONF_SCAN_INTERVAL)
    if interval is None:
        interval = config_entry.data.get(CONF_SCAN_INTERVAL)
    if isinstance(interval, (int, float)) and interval > 0:
        return int(interval)
    return DEFAULT_SCAN_INTERVAL
