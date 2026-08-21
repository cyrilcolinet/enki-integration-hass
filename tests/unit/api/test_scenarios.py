"""Unit tests for Enki scenarios."""

from __future__ import annotations

import re

import pytest
from aioresponses import aioresponses
from enki.api.client import EnkiAPI, _parse_scenario
from enki.const import ENKI_BASE_URL, ENKI_OIDC_URL
from enki.domain.models import EnkiScenario


def test_parse_scenario() -> None:
    scenario = _parse_scenario(
        {"id": "abc123", "label": "Good night", "enabled": False, "status": "IDLE"},
        "home-1",
    )
    assert scenario == EnkiScenario(
        home_id="home-1",
        scenario_id="abc123",
        label="Good night",
        enabled=False,
        status="IDLE",
    )


def test_parse_scenario_requires_id() -> None:
    assert _parse_scenario({"label": "Missing id"}, "home-1") is None


@pytest.mark.asyncio
async def test_refresh_and_activate_scenario() -> None:
    with aioresponses() as mocked:
        mocked.post(
            ENKI_OIDC_URL,
            status=200,
            payload={"access_token": "token", "token_type": "Bearer", "expires_in": 3600},
        )
        homes_url = re.compile(rf"{re.escape(ENKI_BASE_URL)}/api-enki-home-prod/v1/homes")
        mocked.get(homes_url, status=200, payload={"items": [{"id": "home-1"}]})
        list_url = re.compile(
            rf"{re.escape(ENKI_BASE_URL)}/api-enki-scenario-prod/v1/scenarios\?homeId=home-1"
        )
        mocked.get(
            list_url,
            status=200,
            payload={
                "items": [
                    {"id": "scenario-1", "label": "Away", "enabled": True, "status": "IDLE"},
                ],
            },
        )
        activate_url = re.compile(
            rf"{re.escape(ENKI_BASE_URL)}/api-enki-scenario-prod/v1/scenarios/scenario-1/activate"
        )
        mocked.post(activate_url, status=202)

        api = EnkiAPI("user@example.com", "secret")
        await api.async_connect()
        await api.async_refresh_scenarios()
        assert len(api.scenarios) == 1
        assert api.scenarios[0].label == "Away"
        await api.async_activate_scenario("home-1", "scenario-1")
        await api.async_close()
