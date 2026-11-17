"""Regression tests for Netsecur smoke detector API routing (#371)."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.api.gateway_registry import WIRED_PATH_PREFIXES
from enki.domain.models import EnkiDevice
from enki.lib.capability_path import capability_to_path_segment

ENKI_BASE = "https://enki.api.devportal.adeo.cloud"

# Only the smoke read: the device's other reads (temperature, humidity, battery)
# hit their own services and are covered by their own routing tests.
NETSECUR_CAPABILITIES = ["check_smoke_alarm_status"]


def test_smoke_read_uses_smoke_detector_prod() -> None:
    prefix = WIRED_PATH_PREFIXES["smoke_detector"]
    segment = capability_to_path_segment("check_smoke_alarm_status")
    assert prefix == "/api-enki-smoke-detector-prod/v1/sensors"
    assert segment == "check-smoke-alarm-status"


def _netsecur_device() -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-smoke",
        node_id="node-smoke",
        device_name="Smoke detector",
        device_type="sensors",
        is_enabled=True,
        state="ACTIVE",
        capabilities=NETSECUR_CAPABILITIES,
        possible_values={"check_smoke_alarm_status": {"values": ["ACTIVE", "INACTIVE"]}},
    )


@pytest.mark.asyncio
async def test_poll_netsecur_smoke_hits_smoke_url() -> None:
    device = _netsecur_device()
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    smoke_prefix = WIRED_PATH_PREFIXES["smoke_detector"]

    with aioresponses() as mocked:
        mocked.get(
            re.compile(rf"{re.escape(ENKI_BASE)}{re.escape(smoke_prefix)}/node-smoke/.*"),
            payload={"lastReportedValue": "ACTIVE"},
            repeat=True,
        )

        http = await api._get_http()
        state: dict = {}
        await api._append_capability_states(http, "home-1", "node-smoke", device.profile, state)

    assert state.get("smoke_alarm_status") == "ACTIVE"
    await api.async_close()


def test_smoke_gateway_key_present() -> None:
    import enki.gateway_keys_data as keys_module

    assert keys_module.ENKI_SMOKE_DETECTOR_API_KEY
