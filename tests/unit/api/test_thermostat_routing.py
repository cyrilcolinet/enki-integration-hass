"""Regression tests for thermostat / presence API routing (APK 2.25.1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses
from enki.api.capability_routing import CAPABILITY_READS
from enki.api.client import EnkiAPI
from enki.api.gateway_registry import WIRED_PATH_PREFIXES
from enki.domain.models import EnkiDevice
from enki.domain.profile import build_discovery_record
from enki.lib.capability_path import capability_to_path_segment

REPO_ROOT = Path(__file__).resolve().parents[3]
NOIROT_PROFILE = REPO_ROOT / "tests" / "fixtures" / "devices" / "67a4b12bae1eca4709a45680.json"
ENKI_BASE = "https://enki.api.devportal.adeo.cloud"


def _capability_route(transport_id: str, capability: str) -> str | None:
    for read in CAPABILITY_READS:
        if read.transport_id == transport_id and read.capability == capability:
            prefix = WIRED_PATH_PREFIXES[transport_id]
            return f"{prefix}/{{nodeId}}/{capability_to_path_segment(capability)}"
    return None


def test_noirot_thermostat_reads_use_thermostat_prod() -> None:
    assert _capability_route("thermostat", "check_thermostat_target_temperature") == (
        "/api-enki-thermostat-prod/v1/heating/{nodeId}/check-thermostat-target-temperature"
    )
    assert _capability_route("thermostat", "check_window_open_detection") == (
        "/api-enki-thermostat-prod/v1/heating/{nodeId}/check-window-open-detection"
    )


def test_noirot_occupancy_reads_use_presence_detector() -> None:
    assert _capability_route("presence_detector", "check_occupancy") == (
        "/api-enki-presence-detector-prod/v1/sensors/{nodeId}/check-occupancy"
    )
    assert _capability_route("presence_detector", "check_occupancy_mode") == (
        "/api-enki-presence-detector-prod/v1/sensors/{nodeId}/check-occupancy-mode"
    )


def test_current_temperature_always_uses_temperature_humidity() -> None:
    assert _capability_route("temperature_humidity", "check_current_temperature") == (
        "/api-enki-temperature-humidity-sensor-prod/v1/sensors/{nodeId}/check-current-temperature"
    )
    assert _capability_route("thermostat", "check_current_temperature") is None


def test_pilot_wire_reads_use_thermostat_prod() -> None:
    assert _capability_route("thermostat", "check_pilot_wire_state") == (
        "/api-enki-thermostat-prod/v1/heating/{nodeId}/check-pilot-wire-state"
    )


def _device_from_profile(path: Path, *, node_id: str) -> EnkiDevice:
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = build_discovery_record(
        device_type="heaters_and_pilot_wires",
        bff_device_type="heaters_and_pilot_wires",
        capabilities=payload["capabilities"],
        possible_values=payload.get("possibleValues") or payload.get("possible_values") or {},
        manufacturer=payload.get("manufacturer"),
        model=payload.get("name"),
        firmware_version=None,
        supported_by_integration=True,
    )
    return EnkiDevice(
        home_id="home-1",
        device_id=payload["deviceId"],
        node_id=node_id,
        device_name=payload.get("name") or "Test device",
        device_type=record.device_type,
        is_enabled=True,
        state="ACTIVE",
        capabilities=record.capabilities,
        possible_values=record.possible_values,
    )


@pytest.mark.asyncio
async def test_poll_noirot_hits_thermostat_and_presence_urls() -> None:
    device = _device_from_profile(NOIROT_PROFILE, node_id="node-noirot")
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    thermostat_prefix = WIRED_PATH_PREFIXES["thermostat"]
    presence_prefix = WIRED_PATH_PREFIXES["presence_detector"]
    temp_prefix = WIRED_PATH_PREFIXES["temperature_humidity"]

    with aioresponses() as mocked:
        mocked.get(
            re.compile(rf"{re.escape(ENKI_BASE)}{re.escape(thermostat_prefix)}/node-noirot/.*"),
            payload={"lastReportedValue": 21.0},
            repeat=True,
        )
        mocked.get(
            re.compile(rf"{re.escape(ENKI_BASE)}{re.escape(presence_prefix)}/node-noirot/.*"),
            payload={"lastReportedValue": "UNOCCUPIED"},
            repeat=True,
        )
        mocked.get(
            re.compile(rf"{re.escape(ENKI_BASE)}{re.escape(temp_prefix)}/node-noirot/.*"),
            payload={"lastReportedValue": 21.0},
            repeat=True,
        )

        http = await api._get_http()
        state: dict = {}
        await api._append_capability_states(
            http,
            "home-1",
            "node-noirot",
            device.profile,
            state,
        )

    assert state.get("thermostat_target_temperature") == 21.0
    assert state.get("occupancy") == "UNOCCUPIED"
    assert state.get("current_temperature") == 21.0
    await api.async_close()


@pytest.mark.asyncio
async def test_set_pilot_wire_posts_to_thermostat_prod() -> None:
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    prefix = WIRED_PATH_PREFIXES["thermostat"]
    url = f"{ENKI_BASE}{prefix}/node-pilot/switch-pilot-wire-mode"

    with aioresponses() as mocked:
        mocked.post(url, status=202, payload={"status": "SUCCESS"})
        await api.async_set_pilot_wire_mode("home-1", "node-pilot", "ECO")

    assert mocked.requests
    await api.async_close()


def test_thermostat_gateway_key_present() -> None:
    import enki.gateway_keys_data as keys_module

    assert keys_module.ENKI_THERMOSTAT_API_KEY == "2t3Qtt6jSI98PQc89kIlvDo7maleKL8l"
