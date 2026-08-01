"""Transport-level GET decoding, incl. empty / non-JSON bodies (StephaneBranly/ha-enki#23)."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses
from enki.api.transport import EnkiHttpClient
from enki.const import ENKI_BASE_URL


class _FakeAuth:
    """Minimal auth stand-in: token always valid, no network."""

    async def ensure_valid(self, session: aiohttp.ClientSession) -> None:
        return None

    def auth_headers(self, extra: dict[str, str]) -> dict[str, str]:
        return {**extra, "Authorization": "Bearer test-token"}

    def invalidate(self) -> None:
        return None


async def _get_json(*, status: int, body: str):
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.get(f"{ENKI_BASE_URL}/probe", status=status, body=body)
            client = EnkiHttpClient(_FakeAuth(), session)
            return await client.get_json("lighting", "/probe")


@pytest.mark.asyncio
async def test_get_json_returns_empty_dict_for_empty_body() -> None:
    assert await _get_json(status=200, body="") == {}


@pytest.mark.asyncio
async def test_get_json_returns_empty_dict_for_non_json_body() -> None:
    assert await _get_json(status=200, body="Accepted") == {}


@pytest.mark.asyncio
async def test_get_json_parses_a_normal_json_body() -> None:
    assert await _get_json(status=200, body='{"lastReportedValue": "ON"}') == {
        "lastReportedValue": "ON"
    }
