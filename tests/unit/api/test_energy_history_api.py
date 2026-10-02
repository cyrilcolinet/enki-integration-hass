"""Energy history over the wire: the period read and its hourly throttle (#270)."""

from __future__ import annotations

import re

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI
from enki.const import ENKI_BASE_URL, ENKI_OIDC_URL

_CONSUMPTION = f"{ENKI_BASE_URL}/api-enki-consumption-prod/v1/consumption"
_NODE_ROUTE = re.compile(rf"{re.escape(_CONSUMPTION)}/nodes/node-1")

SEPTEMBER = {
    "firstMeasurementDate": "2026-09-19T00:00:00.000Z",
    "periodConsumption": {"value": 3.805, "unit": "kWh"},
    "periodChart": {"series": [{"data": [None, 2.0, 1.805, None], "unit": "kWh"}]},
}


def _login(mocked: aioresponses) -> None:
    mocked.post(
        ENKI_OIDC_URL,
        status=200,
        payload={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
    )


async def _connected() -> tuple[EnkiAPI, object]:
    api = EnkiAPI("user@example.com", "secret")
    await api.async_connect()
    return api, await api._get_http()


@pytest.mark.asyncio
async def test_the_month_is_read_once_then_served_from_cache() -> None:
    with aioresponses() as mocked:
        _login(mocked)
        # Registered once: a second network read would raise.
        mocked.get(_NODE_ROUTE, status=200, payload=SEPTEMBER)
        api, http = await _connected()

        first = await api._async_energy_history(http, "home-1", "node-1")
        second = await api._async_energy_history(http, "home-1", "node-1")
        await api.async_close()

    assert first == second
    assert first["energy_period_total"] == 3.805
    assert first["energy_period_buckets"] == 2


@pytest.mark.asyncio
async def test_the_request_asks_for_the_month_enclosing_now() -> None:
    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(_NODE_ROUTE, status=200, payload=SEPTEMBER)
        api, http = await _connected()

        await api._async_energy_history(http, "home-1", "node-1")
        await api.async_close()

    url = next(url for url in mocked.requests if "nodes/node-1" in str(url[1]))[1]
    assert url.query["timePeriod"] == "MONTHLY"
    assert url.query["startDate"].endswith("Z")


@pytest.mark.asyncio
async def test_a_refused_read_still_holds_the_throttle() -> None:
    """A service that says no once must not be asked again on every poll."""
    with aioresponses() as mocked:
        _login(mocked)
        # One failure is registered; a second network read would raise.
        mocked.get(_NODE_ROUTE, status=500, body="boom")
        api, http = await _connected()

        first = await api._async_energy_history(http, "home-1", "node-1")
        second = await api._async_energy_history(http, "home-1", "node-1")
        await api.async_close()

    assert first == second == {}
