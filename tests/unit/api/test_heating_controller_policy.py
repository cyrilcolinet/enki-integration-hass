"""Water heater mode writes through heating-controller policies (#285)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.api.gateway_registry import WIRED_PATH_PREFIXES

ENKI_BASE = "https://enki.api.devportal.adeo.cloud"


def test_heating_controller_is_wired_at_the_version_root() -> None:
    """The app calls nodes/… and override-commands/… directly under /v1."""
    assert WIRED_PATH_PREFIXES["heating_controller"] == "/api-enki-heating-controller-prod/v1"


@pytest.mark.asyncio
async def test_setting_the_mode_posts_the_policy_the_app_sends() -> None:
    api = EnkiAPI("user@example.com", "secret")
    api._auth.connect = AsyncMock()
    api._auth.ensure_valid = AsyncMock()
    api._auth.auth_headers = MagicMock(side_effect=lambda extra: extra)

    url = f"{ENKI_BASE}/api-enki-heating-controller-prod/v1/nodes/node-wh/policies"

    with aioresponses() as mocked:
        mocked.post(url, status=204)
        await api.async_set_water_heater_mode("home-1", "node-wh", "CLEAN")

    [(_, sent)] = [(key, calls) for key, calls in mocked.requests.items() if str(key[1]) == url]
    assert sent[0].kwargs["json"] == {"capabilityId": "change_water_heater_mode", "value": "CLEAN"}
    assert sent[0].kwargs["headers"]["homeId"] == "home-1"
    await api.async_close()
