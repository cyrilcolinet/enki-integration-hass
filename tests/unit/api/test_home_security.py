"""Enki home alarm over the wire: discovery, state reads, arming."""

from __future__ import annotations

import re

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.const import ENKI_BASE_URL, ENKI_OIDC_URL

_SECURITY = f"{re.escape(ENKI_BASE_URL)}/api-enki-home-security-prod/v1"


def _mock_login(mocked: aioresponses) -> None:
    mocked.post(
        ENKI_OIDC_URL,
        status=200,
        payload={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
    )


def _mock_dashboard(mocked: aioresponses, items: list[dict]) -> None:
    mocked.get(
        re.compile(rf"{re.escape(ENKI_BASE_URL)}/api-enki-home-prod/v1/homes"),
        status=200,
        payload={"items": [{"id": "home-1"}]},
    )
    mocked.get(
        re.compile(rf"{re.escape(ENKI_BASE_URL)}/api-enki-mobile-bff-prod/v1/dashboard/.*"),
        status=200,
        payload={"sections": [{"items": items}]},
    )


_SECURITY_TILE = {"template": "SECURITY", "metadata": {"securityId": "sec-1"}, "state": "ACTIVE"}


@pytest.mark.asyncio
async def test_security_tile_is_found_and_its_state_read() -> None:
    with aioresponses() as mocked:
        _mock_login(mocked)
        _mock_dashboard(mocked, [_SECURITY_TILE])
        mocked.get(
            re.compile(rf"{_SECURITY}/security\?homeId=home-1"),
            status=200,
            payload={
                "homeId": "home-1",
                "threatLevel": "DEFAULT",
                "currentMode": "PARTIAL",
                "alarmDelay": 30,
                "notificationsEnabled": True,
            },
        )
        mocked.get(
            re.compile(rf"{_SECURITY}/modes\?homeId=home-1"),
            status=200,
            payload={"items": [{"type": "FULL"}, {"type": "PARTIAL"}]},
        )

        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        await api.async_get_devices()
        await api.async_refresh_security()
        await api.async_close()

    (system,) = api.security_systems
    assert system.security_id == "sec-1"
    assert system.current_mode == "PARTIAL"
    assert system.arming_modes == frozenset({"FULL", "PARTIAL"})


@pytest.mark.asyncio
async def test_no_security_tile_means_no_alarm_request() -> None:
    with aioresponses() as mocked:
        _mock_login(mocked)
        _mock_dashboard(mocked, [])
        # No security route registered: any call to it would raise.

        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        await api.async_get_devices()
        await api.async_refresh_security()
        await api.async_close()

    assert api.security_systems == ()


@pytest.mark.asyncio
async def test_arming_patches_the_current_mode() -> None:
    with aioresponses() as mocked:
        _mock_login(mocked)
        url = (
            f"{ENKI_BASE_URL}/api-enki-home-security-prod/v1"
            "/security/sec-1/homes/home-1/currentMode"
        )
        mocked.patch(url, status=200)

        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        await api.async_set_security_mode("home-1", "sec-1", "FULL")
        await api.async_close()

        (call,) = [c for key, calls in mocked.requests.items() if key[0] == "PATCH" for c in calls]
        assert call.kwargs["json"] == {"currentMode": "FULL"}
