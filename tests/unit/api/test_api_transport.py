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
async def test_get_json_treats_202_and_204_as_no_value() -> None:
    # Evology multisensor battery/contact reads answer 202 Accepted (value not
    # ready); this must be "no value", not a read error (#153).
    assert await _get_json(status=202, body="") == {}
    assert await _get_json(status=204, body="") == {}


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


@pytest.mark.asyncio
async def test_post_command_debug_logs_accepted_route() -> None:
    from unittest.mock import patch

    url = f"{ENKI_BASE_URL}/api-enki-power-prod/v1/power/n1/switch-electrical-power"
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked, patch("enki.api.transport.LOGGER") as logger:
            mocked.post(f"{url}?endpoints=2", status=202, body="")
            client = EnkiHttpClient(_FakeAuth(), session)
            await client.post_command(
                "power",
                "/api-enki-power-prod/v1/power/n1/switch-electrical-power",
                home_id="h1",
                params={"endpoints": 2},
                json={"value": "OFF"},
            )

    logger.debug.assert_called_once()
    fmt = logger.debug.call_args.args[0]
    args = logger.debug.call_args.args[1:]
    assert "command accepted" in fmt.lower()
    # route, params (endpoint selector) and payload are all in the log record
    assert "/switch-electrical-power" in args[0]
    assert args[1] == {"endpoints": 2}
    assert args[2] == {"value": "OFF"}
