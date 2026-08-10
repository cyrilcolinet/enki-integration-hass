"""Transport-level GET decoding, incl. empty / non-JSON bodies (StephaneBranly/ha-enki#23)."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses
from enki.api.transport import EnkiHttpClient
from enki.const import ENKI_BASE_URL
from enki.exceptions import EnkiConnectionError


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


@pytest.mark.asyncio
async def test_get_json_error_includes_response_body_reason() -> None:
    with pytest.raises(EnkiConnectionError) as exc:
        await _get_json(status=400, body='{"message": "invalid nodeId"}')
    assert exc.value.status == 400
    assert "HTTP 400" in str(exc.value)
    assert "invalid nodeId" in str(exc.value)


@pytest.mark.asyncio
async def test_get_json_error_without_body_keeps_status_only() -> None:
    with pytest.raises(EnkiConnectionError) as exc:
        await _get_json(status=500, body="")
    assert str(exc.value).endswith("HTTP 500")


@pytest.mark.asyncio
async def test_get_json_error_attaches_anonymized_report() -> None:
    with pytest.raises(EnkiConnectionError) as exc:
        await _get_json(status=400, body='{"message": "invalid nodeId"}')
    report = exc.value.report
    assert report is not None
    assert report["method"] == "GET"
    assert report["status"] == 400
    assert report["request_headers"]["Authorization"] == "***"
    assert report["response_body"] == {"message": "invalid nodeId"}
