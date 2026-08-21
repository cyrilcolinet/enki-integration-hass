"""Regression tests for Lexman water leak detector API routing (APK 2.25.1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.api.gateway_registry import WIRED_PATH_PREFIXES
from enki.domain.models import EnkiDevice
from enki.domain.profile import build_discovery_record
from enki.lib.capability_path import capability_to_path_segment

REPO_ROOT = Path(__file__).resolve().parents[3]
LEXMAN_LEAK_PROFILE = REPO_ROOT / "tests" / "fixtures" / "devices" / "651eada55b3a798ef6b6bc5c.json"
ENKI_BASE = "https://enki.api.devportal.adeo.cloud"


def test_water_leak_read_uses_leak_detector_prod() -> None:
    prefix = WIRED_PATH_PREFIXES["water_sensor"]
    segment = capability_to_path_segment("check_water_sensor_state")
    assert prefix == "/api-enki-water-leak-detector-prod/v1/detectors"
    assert segment == "check-water-sensor-state"


def _device_from_profile(path: Path, *, node_id: str) -> EnkiDevice:
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = build_discovery_record(
        device_type="sensors",
        bff_device_type="sensors",
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
async def test_poll_lexman_leak_hits_water_and_battery_urls() -> None:
    device = _device_from_profile(LEXMAN_LEAK_PROFILE, node_id="node-leak")
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    water_prefix = WIRED_PATH_PREFIXES["water_sensor"]
    battery_prefix = WIRED_PATH_PREFIXES["battery_health"]

    with aioresponses() as mocked:
        mocked.get(
            re.compile(rf"{re.escape(ENKI_BASE)}{re.escape(water_prefix)}/node-leak/.*"),
            payload={"lastReportedValue": "NO_WATER_DETECTED"},
            repeat=True,
        )
        mocked.get(
            re.compile(rf"{re.escape(ENKI_BASE)}{re.escape(battery_prefix)}/node-leak/.*"),
            payload={"lastReportedValue": "GOOD"},
            repeat=True,
        )

        http = await api._get_http()
        state: dict = {}
        await api._append_capability_states(
            http,
            "home-1",
            "node-leak",
            device.profile,
            state,
        )

    assert state.get("water_sensor_state") == "NO_WATER_DETECTED"
    assert state.get("battery_health") == "GOOD"
    await api.async_close()


def test_water_sensor_gateway_key_present() -> None:
    import enki.gateway_keys_data as keys_module

    assert keys_module.ENKI_WATER_SENSOR_API_KEY
