"""Unit tests for opt-in device profile notifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.const import CONF_TELEMETRY
from enki.device_profile import build_discovery_record
from enki.telemetry import EnkiTelemetryReporter


def _record():
    return build_discovery_record(
        device_type="equation_radiator",
        bff_device_type="radiators",
        capabilities=["check_temperature"],
        possible_values={},
        manufacturer="equation",
        model="neo",
        firmware_version=None,
        supported_by_integration=False,
    )


@pytest.mark.asyncio
async def test_telemetry_skipped_when_disabled() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: False}

    reporter = EnkiTelemetryReporter(hass, entry)
    with patch(
        "enki.telemetry.persistent_notification.async_create",
        new_callable=AsyncMock,
    ) as notify:
        await reporter.async_report([_record()])
        notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_telemetry_notifies_new_profile() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: True}

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    version_patch = patch(
        "enki.telemetry.EnkiTelemetryReporter._integration_version",
        AsyncMock(return_value="1.0.7"),
    )
    with (
        patch(
            "enki.telemetry.persistent_notification.async_create",
            new_callable=AsyncMock,
        ) as notify,
        version_patch,
    ):
        await reporter.async_report([_record()])
        notify.assert_awaited_once()
        message = notify.await_args.kwargs["message"]
        assert "github.com" in message
        assert "equation_radiator" in message


@pytest.mark.asyncio
async def test_telemetry_dedupes_fingerprint() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: True}

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    version_patch = patch(
        "enki.telemetry.EnkiTelemetryReporter._integration_version",
        AsyncMock(return_value="1.0.7"),
    )
    with (
        patch(
            "enki.telemetry.persistent_notification.async_create",
            new_callable=AsyncMock,
        ) as notify,
        version_patch,
    ):
        await reporter.async_report([_record()])
        await reporter.async_report([_record()])
        notify.assert_awaited_once()
