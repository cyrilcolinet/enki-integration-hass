"""Tests for command-override thermostat setpoint writes (issue #48)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.api.gateway_registry import WIRED_PATH_PREFIXES
from enki.exceptions import EnkiConnectionError
from enki.lib.command_override import override_end_time_iso

ENKI_BASE = "https://enki.api.devportal.adeo.cloud"


def test_override_end_time_iso_is_utc_z() -> None:
    end = override_end_time_iso(hours=1)
    assert end.endswith("Z")
    assert "T" in end


def test_command_override_gateway_wired() -> None:
    assert WIRED_PATH_PREFIXES["command_override"] == ("/api-enki-command-override-prod/v1")


def test_command_override_api_key_from_apk() -> None:
    import enki.gateway_keys_data as keys_module

    assert keys_module.ENKI_COMMAND_OVERRIDE_API_KEY == ("1E4MjXFFSuKKULDytsNnGC3bKX4RV3Wc")


@pytest.mark.asyncio
async def test_set_thermostat_target_temperature_posts_override_command() -> None:
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    prefix = WIRED_PATH_PREFIXES["command_override"]
    url = f"{ENKI_BASE}{prefix}/override-commands"
    fixed_end = "2026-07-05T12:00:00Z"

    with aioresponses() as mocked:
        mocked.post(url, status=202, payload={"status": "SUCCESS"})
        http = await api._get_http()
        await http.create_thermostat_setpoint_override(
            "home-1",
            "node-noirot",
            19.5,
            end_time=fixed_end,
        )

    assert mocked.requests
    assert any(str(key[1]) == url for key in mocked.requests)
    await api.async_close()


@pytest.mark.asyncio
async def test_client_setpoint_uses_command_override() -> None:
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    prefix = WIRED_PATH_PREFIXES["command_override"]
    url = f"{ENKI_BASE}{prefix}/override-commands"

    with aioresponses() as mocked:
        mocked.post(url, status=202, payload={"status": "SUCCESS"})
        await api.async_set_thermostat_target_temperature("home-1", "node-noirot", 20.0)

    assert url in {str(req[1]) for req in mocked.requests}
    await api.async_close()


@pytest.mark.asyncio
async def test_client_setpoint_falls_back_to_thermostat_post_on_404() -> None:
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    override_prefix = WIRED_PATH_PREFIXES["command_override"]
    thermostat_prefix = WIRED_PATH_PREFIXES["thermostat"]
    override_url = f"{ENKI_BASE}{override_prefix}/override-commands"
    fallback_url = (
        f"{ENKI_BASE}{thermostat_prefix}/node-noirot/change-thermostat-target-temperature"
    )

    with aioresponses() as mocked:
        mocked.post(override_url, status=404)
        mocked.post(fallback_url, status=202, payload={"status": "SUCCESS"})
        await api.async_set_thermostat_target_temperature("home-1", "node-noirot", 18.0)

    assert override_url in {str(req[1]) for req in mocked.requests}
    assert fallback_url in {str(req[1]) for req in mocked.requests}
    await api.async_close()


@pytest.mark.asyncio
async def test_create_override_raises_without_api_key(monkeypatch) -> None:
    import enki.gateway_keys_data as keys_module

    monkeypatch.setattr(keys_module, "ENKI_COMMAND_OVERRIDE_API_KEY", "")

    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    http = await api._get_http()
    with pytest.raises(EnkiConnectionError, match="Command-override API key"):
        await http.create_thermostat_setpoint_override("home-1", "node-1", 21.0)

    await api.async_close()
