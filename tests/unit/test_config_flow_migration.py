"""Config-flow migration tests for legacy CyrilP config entries (v1→v2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from enki import async_migrate_entry as init_async_migrate_entry
from enki.config_flow import EnkiConfigFlow
from enki.const import CONF_SCAN_INTERVAL
from enki.migration import async_migrate_entry, is_legacy_config_entry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME


@dataclass
class FakeConfigEntry:
    """Minimal config entry stand-in with mutable fields like HA storage."""

    entry_id: str
    version: int
    data: dict
    options: dict
    unique_id: str | None
    title: str = "Enki – user@example.com"
    updates: list[dict] = field(default_factory=list)


def _apply_config_entry_update(
    entry: FakeConfigEntry,
    *,
    data: dict | None = None,
    options: dict | None = None,
    unique_id: str | None = None,
    version: int | None = None,
) -> None:
    payload: dict = {}
    if data is not None:
        entry.data = data
        payload["data"] = data
    if options is not None:
        entry.options = options
        payload["options"] = options
    if unique_id is not None:
        entry.unique_id = unique_id
        payload["unique_id"] = unique_id
    if version is not None:
        entry.version = version
        payload["version"] = version
    entry.updates.append(payload)


def _fake_hass() -> MagicMock:
    hass = MagicMock()

    def async_update_entry(entry: FakeConfigEntry, **kwargs) -> None:
        _apply_config_entry_update(entry, **kwargs)

    hass.config_entries.async_update_entry = async_update_entry
    return hass


def _legacy_v1_entry() -> FakeConfigEntry:
    return FakeConfigEntry(
        entry_id="legacy-entry-1",
        version=1,
        title="Enki - cyrilcolinet.pro@gmail.com",
        data={
            CONF_USERNAME: "cyrilcolinet.pro@gmail.com",
            CONF_PASSWORD: "secret",
            CONF_SCAN_INTERVAL: 45,
        },
        options={},
        unique_id="Enki - cyrilcolinet.pro@gmail.com",
    )


@pytest.mark.asyncio
async def test_legacy_v1_entry_migrates_fields_and_version() -> None:
    # Given
    hass = _fake_hass()
    entry = _legacy_v1_entry()
    registry = MagicMock()

    # When
    with (
        patch("enki.migration.er.async_get", return_value=registry),
        patch("enki.migration.er.async_entries_for_config_entry", return_value=[]),
    ):
        result = await async_migrate_entry(hass, entry)

    # Then
    assert result is True
    assert entry.version == 2
    assert CONF_SCAN_INTERVAL not in entry.data
    assert entry.options[CONF_SCAN_INTERVAL] == 45
    assert entry.unique_id == "cyrilcolinet.pro@gmail.com"
    assert entry.data[CONF_USERNAME] == "cyrilcolinet.pro@gmail.com"
    assert len(entry.updates) == 2
    assert entry.updates[0]["options"][CONF_SCAN_INTERVAL] == 45
    assert entry.updates[1]["version"] == 2


@pytest.mark.asyncio
async def test_legacy_v1_entry_keeps_existing_scan_interval_option() -> None:
    # Given
    hass = _fake_hass()
    entry = FakeConfigEntry(
        entry_id="legacy-entry-2",
        version=1,
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_SCAN_INTERVAL: 60,
        },
        options={CONF_SCAN_INTERVAL: 30},
        unique_id="user@example.com",
    )

    # When
    with (
        patch("enki.migration.er.async_get", return_value=MagicMock()),
        patch("enki.migration.er.async_entries_for_config_entry", return_value=[]),
    ):
        await async_migrate_entry(hass, entry)

    # Then
    assert entry.options[CONF_SCAN_INTERVAL] == 30
    assert CONF_SCAN_INTERVAL not in entry.data


@pytest.mark.asyncio
async def test_legacy_v1_entry_renames_solar_entity_unique_id() -> None:
    # Given
    hass = _fake_hass()
    entry = _legacy_v1_entry()
    solar_entity = SimpleNamespace(
        entity_id="sensor.enki_solar_power",
        unique_id="enki-node1-power_production",
    )
    registry = MagicMock()

    # When
    with (
        patch("enki.migration.er.async_get", return_value=registry),
        patch(
            "enki.migration.er.async_entries_for_config_entry",
            return_value=[solar_entity],
        ),
    ):
        await async_migrate_entry(hass, entry)

    # Then
    registry.async_update_entity.assert_called_once_with(
        "sensor.enki_solar_power",
        new_unique_id="enki-node1-power-production",
    )


@pytest.mark.asyncio
async def test_config_flow_async_migrate_entry_runs_full_migration() -> None:
    # Given
    hass = _fake_hass()
    entry = _legacy_v1_entry()

    # When
    with (
        patch("enki.migration.er.async_get", return_value=MagicMock()),
        patch("enki.migration.er.async_entries_for_config_entry", return_value=[]),
    ):
        result = await EnkiConfigFlow.async_migrate_entry(hass, entry)

    # Then
    assert result is True
    assert entry.version == 2
    assert entry.unique_id == "cyrilcolinet.pro@gmail.com"


@pytest.mark.asyncio
async def test_init_async_migrate_entry_runs_full_migration() -> None:
    # Given
    hass = _fake_hass()
    entry = _legacy_v1_entry()

    # When
    with (
        patch("enki.migration.er.async_get", return_value=MagicMock()),
        patch("enki.migration.er.async_entries_for_config_entry", return_value=[]),
    ):
        result = await init_async_migrate_entry(hass, entry)

    # Then
    assert result is True
    assert entry.version == 2
    assert CONF_SCAN_INTERVAL in entry.options


def test_is_legacy_config_entry_detects_cyrilp_shape() -> None:
    entry = _legacy_v1_entry()
    assert is_legacy_config_entry(entry) is True

    entry.version = 2
    entry.data.pop(CONF_SCAN_INTERVAL)
    entry.unique_id = "cyrilcolinet.pro@gmail.com"
    assert is_legacy_config_entry(entry) is False
