"""Unit tests for scenario, shutter-preset, and impulse-relay buttons."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.button import (
    EnkiImpulseRelayButton,
    EnkiScenarioButton,
    EnkiShutterPresetButton,
)
from enki.domain.models import EnkiDevice, EnkiScenario


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "Gate",
        "device_type": "access_and_motorizations",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _coordinator(scenarios: list[EnkiScenario] | None = None) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.api.scenarios = scenarios or []
    coordinator.api.async_activate_scenario = AsyncMock()
    coordinator.api.async_execute_shutter_preset = AsyncMock()
    coordinator.api.async_power_on_with_timer = AsyncMock()
    return coordinator


# --- scenario button --------------------------------------------------------


def test_scenario_available_when_enabled() -> None:
    scenario = EnkiScenario(home_id="home-1", scenario_id="s1", label="Movie", enabled=True)
    button = EnkiScenarioButton(_coordinator([scenario]), "home-1", "s1")
    assert button.available is True


def test_scenario_unavailable_when_missing_or_disabled() -> None:
    disabled = EnkiScenario(home_id="home-1", scenario_id="s1", label="Movie", enabled=False)
    assert EnkiScenarioButton(_coordinator([disabled]), "home-1", "s1").available is False
    assert EnkiScenarioButton(_coordinator([]), "home-1", "s1").available is False


@pytest.mark.asyncio
async def test_scenario_press_activates() -> None:
    coordinator = _coordinator()
    await EnkiScenarioButton(coordinator, "home-1", "s1").async_press()
    coordinator.api.async_activate_scenario.assert_awaited_once_with("home-1", "s1")


def test_scenario_device_info_groups_under_virtual_device() -> None:
    info = EnkiScenarioButton(_coordinator(), "home-1", "s1").device_info
    assert info["identifiers"] == {("enki", "home-1", "scenarios")}


# --- shutter preset + impulse relay ----------------------------------------


@pytest.mark.asyncio
async def test_shutter_preset_press_executes_preset() -> None:
    device = _device()
    coordinator = _coordinator()
    await EnkiShutterPresetButton(coordinator, device, "MORNING").async_press()
    coordinator.api.async_execute_shutter_preset.assert_awaited_once_with(
        "home-1", "node-1", "MORNING"
    )


@pytest.mark.asyncio
async def test_impulse_relay_press_triggers_timer() -> None:
    device = _device()
    coordinator = _coordinator()
    await EnkiImpulseRelayButton(coordinator, device).async_press()
    coordinator.api.async_power_on_with_timer.assert_awaited_once_with("home-1", "node-1")
