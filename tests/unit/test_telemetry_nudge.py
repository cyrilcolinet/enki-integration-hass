"""Unit tests for the one-time telemetry nudge for legacy installs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.const import CONF_TELEMETRY, CONF_TELEMETRY_ONBOARDING
from enki.telemetry.nudge import (
    EnkiTelemetryNudge,
    parse_version,
    version_is_before,
)


def test_version_is_before() -> None:
    assert version_is_before("1.0.5", "1.0.6") is True
    assert version_is_before("1.0.6", "1.0.6") is False
    assert version_is_before("1.1.0", "1.0.6") is False


def test_parse_version_with_suffix() -> None:
    assert parse_version("1.0.6-beta") == (1, 0, 6)


@pytest.mark.asyncio
async def test_nudge_skipped_when_telemetry_enabled() -> None:
    hass = MagicMock()
    hass.config.language = "fr"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: True}

    nudge = EnkiTelemetryNudge(hass, entry)
    nudge._store.async_load = AsyncMock(return_value={})  # type: ignore[method-assign]
    nudge._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with (
        patch(
            "enki.telemetry.nudge.ir.async_create_issue",
            new_callable=MagicMock,
        ) as notify,
        patch(
            "enki.telemetry.nudge.ir.async_delete_issue",
            new_callable=MagicMock,
        ),
    ):
        await nudge.async_handle_setup()
        notify.assert_not_called()


@pytest.mark.asyncio
async def test_nudge_skipped_after_onboarding_step() -> None:
    hass = MagicMock()
    hass.config.language = "en"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: False, CONF_TELEMETRY_ONBOARDING: True}

    nudge = EnkiTelemetryNudge(hass, entry)
    nudge._store.async_load = AsyncMock(return_value={})  # type: ignore[method-assign]
    nudge._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.nudge.ir.async_create_issue",
        new_callable=MagicMock,
    ) as notify:
        await nudge.async_handle_setup()
        notify.assert_not_called()
        nudge._store.async_save.assert_awaited()


@pytest.mark.asyncio
async def test_nudge_shown_once_for_legacy_install() -> None:
    hass = MagicMock()
    hass.config.language = "fr"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: False}

    nudge = EnkiTelemetryNudge(hass, entry)
    nudge._store.async_load = AsyncMock(return_value={})  # type: ignore[method-assign]
    nudge._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.nudge.ir.async_create_issue",
        new_callable=MagicMock,
    ) as notify:
        await nudge.async_handle_setup()
        notify.assert_called_once()
        assert notify.call_args.args[2] == "telemetry_nudge_entry1"
        assert notify.call_args.kwargs["translation_key"] == "telemetry_nudge"

        nudge._store.async_load = AsyncMock(  # type: ignore[method-assign]
            return_value={"telemetry_nudge_dismissed": True, "first_seen_version": "legacy"}
        )
        await nudge.async_handle_setup()
        notify.assert_called_once()


@pytest.mark.asyncio
async def test_nudge_dismissed_when_telemetry_turned_on() -> None:
    hass = MagicMock()
    hass.config.language = "en"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: True}

    nudge = EnkiTelemetryNudge(hass, entry)
    nudge._store.async_load = AsyncMock(return_value={})  # type: ignore[method-assign]
    nudge._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.nudge.ir.async_delete_issue",
        new_callable=MagicMock,
    ) as dismiss:
        await nudge.async_handle_setup()
        dismiss.assert_called_once()
        assert dismiss.call_args.args[2] == "telemetry_nudge_entry1"
