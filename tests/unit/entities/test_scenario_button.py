"""Unit tests for EnkiScenarioButton entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.button import EnkiScenarioButton
from enki.domain.models import EnkiScenario


def _scenario(**kwargs) -> EnkiScenario:
    defaults = {
        "home_id": "home-1",
        "scenario_id": "scenario-1",
        "label": "Good night",
        "enabled": True,
        "status": "IDLE",
    }
    defaults.update(kwargs)
    return EnkiScenario(**defaults)


def _coordinator(*, scenarios: list[EnkiScenario], last_update_success: bool = True) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = last_update_success
    coordinator.api.scenarios = scenarios
    coordinator.api.async_activate_scenario = AsyncMock()
    return coordinator


def test_scenario_button_available_when_enabled() -> None:
    scenario = _scenario()
    entity = EnkiScenarioButton(_coordinator(scenarios=[scenario]), "home-1", "scenario-1")

    assert entity.available is True


def test_scenario_button_unavailable_when_disabled() -> None:
    scenario = _scenario(enabled=False)
    entity = EnkiScenarioButton(_coordinator(scenarios=[scenario]), "home-1", "scenario-1")

    assert entity.available is False


def test_scenario_button_unavailable_when_missing_from_poll() -> None:
    entity = EnkiScenarioButton(_coordinator(scenarios=[]), "home-1", "scenario-1")

    assert entity.available is False


def test_scenario_button_unavailable_when_coordinator_failed() -> None:
    scenario = _scenario()
    entity = EnkiScenarioButton(
        _coordinator(scenarios=[scenario], last_update_success=False),
        "home-1",
        "scenario-1",
    )

    assert entity.available is False


def test_refresh_from_scenario_updates_label() -> None:
    entity = EnkiScenarioButton(_coordinator(scenarios=[_scenario()]), "home-1", "scenario-1")
    entity._attr_name = "Old label"

    entity.refresh_from_scenario(_scenario(label="Away mode"))

    assert entity._attr_name == "Away mode"


def test_coordinator_update_applies_latest_label() -> None:
    coordinator = _coordinator(scenarios=[_scenario(label="Morning")])
    entity = EnkiScenarioButton(coordinator, "home-1", "scenario-1")
    entity._attr_name = "Stale"

    entity._handle_coordinator_update()

    assert entity._attr_name == "Morning"


@pytest.mark.asyncio
async def test_scenario_button_press_activates_cloud_scenario() -> None:
    coordinator = _coordinator(scenarios=[_scenario()])
    entity = EnkiScenarioButton(coordinator, "home-1", "scenario-1")

    await entity.async_press()

    coordinator.api.async_activate_scenario.assert_awaited_once_with("home-1", "scenario-1")
