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


@pytest.mark.asyncio
async def test_gateway_403_stops_further_reads_on_that_service() -> None:
    """A gateway-level 403 raises once, then that service is skipped (#190).

    `api-enki-consumption-prod` and `api-enki-ota-prod` started refusing the key
    shipped with the app for every account. Those reads run on each polling
    cycle, so retrying only floods the log.
    """
    body = '{"message":"You cannot consume this service"}'
    url = f"{ENKI_BASE_URL}/api-enki-consumption-prod/v1/consumption/n1/check-instant-consumption"
    path = "/api-enki-consumption-prod/v1/consumption/n1/check-instant-consumption"

    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.get(url, status=403, body=body)
            client = EnkiHttpClient(_FakeAuth(), session)

            with pytest.raises(EnkiConnectionError) as first:
                await client.get_json("consumption", path)
            assert first.value.status == 403

            # No second HTTP call is registered on the mock: a further read would
            # raise ConnectionError from aioresponses if it hit the network.
            assert await client.get_json("consumption", path) == {}
            assert "consumption" in client.forbidden_services

            # Other services are untouched by one service's refusal.
            assert "ota" not in client.forbidden_services


@pytest.mark.asyncio
async def test_unrelated_403_still_raises_every_time() -> None:
    """A 403 without the gateway's wording is not a service-wide refusal."""
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.get(f"{ENKI_BASE_URL}/probe", status=403, body='{"message":"Forbidden node"}')
            mocked.get(f"{ENKI_BASE_URL}/probe", status=403, body='{"message":"Forbidden node"}')
            client = EnkiHttpClient(_FakeAuth(), session)

            for _ in range(2):
                with pytest.raises(EnkiConnectionError):
                    await client.get_json("lighting", "/probe")
            assert not client.forbidden_services
