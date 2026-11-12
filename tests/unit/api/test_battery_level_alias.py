"""Remotes report their battery under the other of the two capability names (#377).

A four-button Lexman remote declares `check_battery_level`, never
`check_battery_health`. There is no `check-battery-level` route: the app labels
that capability `common_battery_health` and routes its node event through
BatteryHealthChangeEventHandler, so `check-battery-health` is the only battery
read, and the device was left with no entity at all.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.capability_routing import CAPABILITY_READS
from enki.api.client import EnkiAPI
from enki.domain.capabilities import EnkiCapabilityProfile

REMOTE = [
    "check_battery_level",
    "check_first_button_from_left_state",
    "check_fourth_button_from_left_state",
    "check_lighting_remote_state",
    "check_second_button_from_left_state",
    "check_third_button_from_left_state",
]


def _profile(capabilities: list[str]) -> EnkiCapabilityProfile:
    return EnkiCapabilityProfile(
        device_type="remote_controls_and_switches",
        capabilities=tuple(capabilities),
        possible_values={},
    )


def test_the_battery_read_is_marked_for_devices_declaring_only_the_level_name() -> None:
    read = next(r for r in CAPABILITY_READS if r.capability == "check_battery_health")

    assert read.also_when is not None
    assert read.also_when(_profile(REMOTE)), "the reporter's remote"
    assert not read.also_when(_profile(["check_current_temperature"])), "a plain sensor"


def test_a_battery_only_remote_is_a_supported_device() -> None:
    profile = _profile(REMOTE)

    assert profile.supports_battery_health is True
    assert profile.is_supported is True


@pytest.mark.asyncio
async def test_the_battery_is_read_although_the_referentiel_names_it_differently() -> None:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock()
    http.capability_get = AsyncMock(return_value={"lastReportedValue": "GOOD"})
    state: dict = {}

    await api._append_capability_states(http, "home", "node", _profile(REMOTE), state)

    assert state["battery_health"] == "GOOD"
    asked = {call.args[3] for call in http.capability_get.await_args_list}
    assert "check_battery_health" in asked
    assert "check_battery_level" not in asked, "no such route"
    await api.async_close()
