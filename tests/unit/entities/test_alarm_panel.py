"""Enki home alarm as an alarm_control_panel entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.alarm_control_panel import EnkiAlarmPanel
from enki.domain.security import EnkiSecuritySystem
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.exceptions import HomeAssistantError


def _system(**overrides) -> EnkiSecuritySystem:
    values = {
        "home_id": "home-1",
        "security_id": "sec-1",
        "current_mode": "DISABLED",
        "threat_level": "DEFAULT",
        "last_threat_date": None,
        "alarm_delay": 30,
        "notifications_enabled": True,
        "configured_modes": frozenset({"FULL", "PARTIAL", "PRESENCE"}),
    }
    values.update(overrides)
    return EnkiSecuritySystem(**values)


def _panel(system: EnkiSecuritySystem | None) -> tuple[EnkiAlarmPanel, MagicMock]:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.api.security_systems = (system,) if system else ()
    coordinator.api.async_set_security_mode = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    panel = EnkiAlarmPanel(coordinator, "home-1", "sec-1")
    panel.async_write_ha_state = MagicMock()
    return panel, coordinator


@pytest.mark.parametrize(
    ("mode", "state"),
    [
        ("DISABLED", AlarmControlPanelState.DISARMED),
        ("INACTIVE", AlarmControlPanelState.DISARMED),
        ("FULL", AlarmControlPanelState.ARMED_AWAY),
        ("PARTIAL", AlarmControlPanelState.ARMED_HOME),
        ("PRESENCE", AlarmControlPanelState.ARMED_NIGHT),
    ],
)
def test_enki_modes_map_to_ha_states(mode: str, state: AlarmControlPanelState) -> None:
    panel, _ = _panel(_system(current_mode=mode))
    assert panel.alarm_state == state


def test_unknown_mode_reports_no_state() -> None:
    panel, _ = _panel(_system(current_mode="SOMETHING_NEW"))
    assert panel.alarm_state is None


def test_intrusion_overrides_the_mode() -> None:
    panel, _ = _panel(_system(current_mode="FULL", threat_level="INTRUSION"))
    assert panel.alarm_state == AlarmControlPanelState.TRIGGERED


def test_only_configured_modes_are_offered() -> None:
    panel, _ = _panel(_system(configured_modes=frozenset({"FULL"})))
    assert panel.supported_features == AlarmControlPanelEntityFeature.ARM_AWAY


def test_unavailable_without_a_system() -> None:
    panel, _ = _panel(None)
    assert panel.available is False
    assert panel.alarm_state is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "mode"),
    [
        ("async_alarm_arm_away", "FULL"),
        ("async_alarm_arm_home", "PARTIAL"),
        ("async_alarm_arm_night", "PRESENCE"),
        ("async_alarm_disarm", "DISABLED"),
    ],
)
async def test_commands_send_the_enki_mode(action: str, mode: str) -> None:
    panel, coordinator = _panel(_system(current_mode="PARTIAL"))
    await getattr(panel, action)()
    coordinator.api.async_set_security_mode.assert_awaited_once_with("home-1", "sec-1", mode)
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_arming_an_unconfigured_mode_is_refused() -> None:
    panel, coordinator = _panel(_system(configured_modes=frozenset({"FULL"})))
    with pytest.raises(HomeAssistantError):
        await panel.async_alarm_arm_night()
    coordinator.api.async_set_security_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_shows_arming_until_the_cloud_catches_up() -> None:
    system = _system(current_mode="DISABLED")
    panel, coordinator = _panel(system)

    await panel.async_alarm_arm_away()
    assert panel.alarm_state == AlarmControlPanelState.ARMING

    coordinator.api.security_systems = (_system(current_mode="FULL"),)
    assert panel.alarm_state == AlarmControlPanelState.ARMED_AWAY


@pytest.mark.asyncio
async def test_shows_disarming_while_waiting() -> None:
    panel, _ = _panel(_system(current_mode="FULL"))
    await panel.async_alarm_disarm()
    assert panel.alarm_state == AlarmControlPanelState.DISARMING


def test_attributes_carry_the_raw_enki_values() -> None:
    panel, _ = _panel(_system(current_mode="FULL", threat_level="DETERRENCE"))
    assert panel.extra_state_attributes == {
        "enki_mode": "FULL",
        "threat_level": "DETERRENCE",
        "alarm_delay": 30,
    }
