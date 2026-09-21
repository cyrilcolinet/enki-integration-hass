"""Meari camera settings over the wire: status read, throttling, writes."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.const import ENKI_BASE_URL, ENKI_OIDC_URL

_MEARI = f"{ENKI_BASE_URL}/api-enki-lexman-camera-meari-prod/v1/camera"


def _login(mocked: aioresponses) -> None:
    mocked.post(
        ENKI_OIDC_URL,
        status=200,
        payload={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
    )


@pytest.mark.asyncio
async def test_status_is_read_once_then_served_from_cache() -> None:
    with aioresponses() as mocked:
        _login(mocked)
        # Registered once: a second network read would raise.
        mocked.get(
            re.compile(rf"{re.escape(_MEARI)}/node-1/check-camera-status"),
            status=200,
            payload={"nightVisionMode": "SMART", "batteryLevel": "80"},
        )
        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        http = await api._get_http()

        first = await api._read_camera_settings(http, "home-1", "node-1")
        second = await api._read_camera_settings(http, "home-1", "node-1")
        await api.async_close()

    assert first == second == {"camera_night_vision_mode": "SMART", "camera_battery_level": 80}


@pytest.mark.asyncio
async def test_a_setting_write_accepts_200_and_invalidates_the_cache() -> None:
    with aioresponses() as mocked:
        _login(mocked)
        # The meari routes answer 200 with the new setting in the body.
        mocked.post(
            f"{_MEARI}/node-1/change-night-vision-mode",
            status=200,
            payload={"value": "FULL_COLOR"},
        )
        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        api._camera_settings_cache["node-1"] = (0.0, {"camera_night_vision_mode": "SMART"})

        await api.async_set_camera_setting(
            "home-1", "node-1", "change_night_vision_mode", "FULL_COLOR"
        )
        await api.async_close()

        (call,) = [
            c
            for key, calls in mocked.requests.items()
            if key[0] == "POST" and "change-night" in str(key[1])
            for c in calls
        ]
        assert call.kwargs["json"] == {"value": "FULL_COLOR"}
    assert "node-1" not in api._camera_settings_cache


@pytest.mark.asyncio
async def test_status_failure_keeps_the_last_known_settings() -> None:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock()
    from enki.exceptions import EnkiConnectionError

    http.get_camera_status = AsyncMock(side_effect=EnkiConnectionError("asleep", status=500))
    api._camera_settings_cache["node-1"] = (-1e9, {"camera_night_vision_mode": "SMART"})

    assert await api._read_camera_settings(http, "home-1", "node-1") == {
        "camera_night_vision_mode": "SMART"
    }


@pytest.mark.asyncio
async def test_live_view_wakes_the_camera_then_starts_with_fresh_credentials() -> None:
    with aioresponses() as mocked:
        _login(mocked)
        mocked.post(f"{_MEARI}/node-1/wake-up", status=500)  # best-effort: tolerated
        mocked.get(
            re.compile(rf"{re.escape(_MEARI)}/node-1/check-camera-connect-wss"),
            status=200,
            payload={"wssUrl": "wss://signal", "callee": "cam", "deviceCode": "dev"},
        )
        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        session = MagicMock()
        session.start = AsyncMock()

        await api.async_start_camera_live("home-1", "node-1", session, "OFFER")
        await api.async_close()

    _, info, offer = session.start.await_args.args
    assert info["wssUrl"] == "wss://signal"
    assert offer == "OFFER"


@pytest.mark.asyncio
async def test_live_view_without_access_is_refused() -> None:
    from enki.api.meari_signaling import MeariSignalingError

    with aioresponses() as mocked:
        _login(mocked)
        mocked.post(f"{_MEARI}/node-1/wake-up", status=200)
        mocked.get(re.compile(rf"{re.escape(_MEARI)}/node-1/check-camera-connect-wss"), status=404)
        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        session = MagicMock()
        session.start = AsyncMock()

        with pytest.raises(MeariSignalingError):
            await api.async_start_camera_live("home-1", "node-1", session, "OFFER")
        await api.async_close()

    session.start.assert_not_awaited()
