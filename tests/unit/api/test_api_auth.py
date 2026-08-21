"""Unit tests for Enki API authentication."""

from __future__ import annotations

import time

import aiohttp
import pytest
from aioresponses import aioresponses
from enki.api import EnkiAPI
from enki.const import ENKI_OIDC_URL
from enki.exceptions import EnkiAuthError, EnkiConnectionError


@pytest.mark.asyncio
async def test_connect_success() -> None:
    with aioresponses() as mocked:
        mocked.post(
            ENKI_OIDC_URL,
            status=200,
            payload={
                "access_token": "token-abc",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )
        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        assert api._auth.access_token == "token-abc"
        await api.async_close()


@pytest.mark.asyncio
async def test_connect_invalid_credentials() -> None:
    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=401, payload={"error": "invalid_grant"})
        api = EnkiAPI("user@example.com", "wrong")
        with pytest.raises(EnkiAuthError):
            await api.async_connect()
        await api.async_close()


@pytest.mark.asyncio
async def test_connect_upstream_error() -> None:
    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=503, payload={"error": "unavailable"})
        api = EnkiAPI("user@example.com", "secret")
        with pytest.raises(EnkiConnectionError):
            await api.async_connect()
        await api.async_close()


@pytest.mark.asyncio
async def test_connect_network_failure() -> None:
    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, exception=aiohttp.ClientConnectionError("offline"))
        api = EnkiAPI("user@example.com", "secret")
        with pytest.raises(EnkiConnectionError, match="Cannot reach Enki auth"):
            await api.async_connect()
        await api.async_close()


@pytest.mark.asyncio
async def test_connect_stores_refresh_token() -> None:
    with aioresponses() as mocked:
        mocked.post(
            ENKI_OIDC_URL,
            status=200,
            payload={
                "access_token": "token-abc",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "refresh-xyz",
            },
        )
        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        assert api._auth._refresh_token == "refresh-xyz"
        await api.async_close()


@pytest.mark.asyncio
async def test_ensure_token_uses_refresh_before_password() -> None:
    with aioresponses() as mocked:
        mocked.post(
            ENKI_OIDC_URL,
            status=200,
            payload={
                "access_token": "refreshed-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "new-refresh",
            },
        )
        api = EnkiAPI("user@example.com", "secret")
        api._auth._access_token = "expired"
        api._auth._refresh_token = "old-refresh"
        api._auth._token_expires_at = time.time() - 10

        await api._ensure_token()

        assert api._auth.access_token == "refreshed-token"
        assert api._auth._refresh_token == "new-refresh"
        await api.async_close()


@pytest.mark.asyncio
async def test_ensure_token_falls_back_to_password_when_refresh_fails() -> None:
    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=401, payload={"error": "invalid_grant"})
        mocked.post(
            ENKI_OIDC_URL,
            status=200,
            payload={
                "access_token": "password-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "fresh-refresh",
            },
        )
        api = EnkiAPI("user@example.com", "secret")
        api._auth._access_token = "expired"
        api._auth._refresh_token = "bad-refresh"
        api._auth._token_expires_at = time.time() - 10

        await api._ensure_token()

        assert api._auth.access_token == "password-token"
        await api.async_close()
