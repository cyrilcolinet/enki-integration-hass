"""Unit tests for opt-in device profile notifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.const import CONF_TELEMETRY
from enki.domain.profile import build_discovery_record
from enki.telemetry.reporter import EnkiTelemetryReporter


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


def _entry_with_coordinator(*, telemetry: bool) -> MagicMock:
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_TELEMETRY: telemetry}
    entry.runtime_data = MagicMock()
    entry.runtime_data.api.read_errors_for_fingerprint.return_value = {}
    entry.runtime_data.api.poll_state_for_fingerprint.return_value = {}
    return entry


@pytest.mark.asyncio
async def test_telemetry_skipped_when_disabled() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = _entry_with_coordinator(telemetry=False)

    reporter = EnkiTelemetryReporter(hass, entry)
    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([_record()])
        notify.assert_not_called()


@pytest.mark.asyncio
async def test_telemetry_notifies_new_profile() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = _entry_with_coordinator(telemetry=True)

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([_record()])
        notify.assert_called_once()
        reporter._store.async_save.assert_awaited()
        message = notify.call_args.kwargs["message"]
        assert "github.com" in message
        assert "equation_radiator" in message


@pytest.mark.asyncio
async def test_telemetry_dedupes_fingerprint() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = _entry_with_coordinator(telemetry=True)

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([_record()])
        await reporter.async_report([_record()])
        notify.assert_called_once()


@pytest.mark.asyncio
async def test_telemetry_skips_fully_supported_profile() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = _entry_with_coordinator(telemetry=True)

    record = build_discovery_record(
        device_type="ceiling_fans",
        bff_device_type="ceiling_fans",
        capabilities=[
            "change_fan_speed",
            "check_fan_speed",
            "change_light_state",
            "check_light_state",
            "switch_electrical_power",
            "check_electrical_power",
        ],
        possible_values={},
        manufacturer="Inspire",
        model="AD_TCFL_1",
        firmware_version="2.21.0",
        supported_by_integration=True,
    )

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([record])
        notify.assert_not_called()
        reporter._store.async_save.assert_awaited()


@pytest.mark.asyncio
async def test_telemetry_skips_out_of_scope_sonoff() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = _entry_with_coordinator(telemetry=True)

    record = build_discovery_record(
        device_type="sensors",
        bff_device_type="sensors",
        capabilities=["check_current_temperature"],
        possible_values={},
        manufacturer="Sonoff",
        model="SNZB-02D",
        firmware_version=None,
        supported_by_integration=False,
    )

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([record])
        notify.assert_not_called()


@pytest.mark.asyncio
async def test_telemetry_notifies_when_api_errors_appear_after_fingerprint_stored() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    entry = _entry_with_coordinator(telemetry=True)

    record = build_discovery_record(
        device_type="heaters_and_pilot_wires",
        bff_device_type="heaters_and_pilot_wires",
        capabilities=[
            "change_thermostat_target_temperature",
            "check_thermostat_target_temperature",
        ],
        possible_values={},
        manufacturer="Noirot",
        model="radiator",
        firmware_version="2.15.0",
        supported_by_integration=True,
    )

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": ["already-known-fp"]})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    from enki.domain.profile import profile_fingerprint, profile_to_export_dict

    export = profile_to_export_dict(record, integration_version="1.6.6", ha_version="2025.1")
    fingerprint = profile_fingerprint(export)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": [fingerprint]})  # type: ignore[method-assign]

    entry.runtime_data.api.read_errors_for_fingerprint.return_value = {
        "heating/check_thermostat_target_temperature": "HTTP 500",
    }

    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([record])
        notify.assert_called_once()


@pytest.mark.asyncio
async def test_telemetry_tolerates_corrupt_storage() -> None:
    hass = MagicMock()
    hass.config.version = "2024.12.0"
    hass.config.language = "en"
    entry = _entry_with_coordinator(telemetry=True)

    reporter = EnkiTelemetryReporter(hass, entry)
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": None})  # type: ignore[method-assign]
    reporter._store.async_save = AsyncMock()  # type: ignore[method-assign]

    with patch(
        "enki.telemetry.reporter.persistent_notification.async_create",
        new_callable=MagicMock,
    ) as notify:
        await reporter.async_report([_record()])
        notify.assert_called_once()
