"""A valve that spells its child lock in one word still gets the switch (#343).

The Sedea thermostatic valve declares `change_childlock` / `check_childlock`
with the same LOCK / UNLOCK values as every other valve, so it was reported as
a capability gap and got no switch. Both spellings now count, and both paths
are asked: the route follows the capability name, so the one-word read goes to
`check-childlock` and the dashed one stays 404-tolerant.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.capability_routing import CAPABILITY_READS
from enki.api.client import EnkiAPI
from enki.domain.capabilities import EnkiCapabilityProfile
from enki.domain.telemetry_coverage import capability_is_covered

VALVE = [
    "change_childlock",
    "change_offset_temperature",
    "change_thermostat_target_temperature",
    "check_battery_health",
    "check_childlock",
    "check_current_temperature",
    "check_thermostat_target_temperature",
]


def _profile(capabilities: list[str]) -> EnkiCapabilityProfile:
    schema = {"check_childlock": {"values": ["LOCK", "UNLOCK"]}}
    return EnkiCapabilityProfile(
        device_type="heaters_and_pilot_wires",
        capabilities=tuple(capabilities),
        possible_values={k: v for k, v in schema.items() if k in capabilities},
    )


def test_the_one_word_spelling_is_a_child_lock() -> None:
    profile = _profile(VALVE)

    assert profile.supports_child_lock is True
    assert profile.is_config_switch is True


def test_neither_spelling_is_reported_as_a_gap() -> None:
    profile = _profile(VALVE)

    for capability in ("change_childlock", "check_childlock"):
        assert capability_is_covered(capability, profile), capability


def test_the_dashed_read_is_tried_for_a_valve_that_names_it_differently() -> None:
    read = next(r for r in CAPABILITY_READS if r.capability == "check_child_lock")

    assert read.also_when is not None
    assert read.also_when(_profile(VALVE)), "the reporter's valve"
    assert not read.also_when(_profile(["check_current_temperature"])), "a plain thermostat"


@pytest.mark.asyncio
async def test_both_spellings_are_asked_and_feed_the_same_state_key() -> None:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock()
    http.capability_get = AsyncMock(return_value={"lastReportedValue": "LOCK"})
    state: dict = {}

    await api._append_capability_states(http, "home", "node", _profile(VALVE), state)

    assert state["child_lock"] == "LOCK"
    asked = {call.args[3] for call in http.capability_get.await_args_list}
    assert {"check_childlock", "check_child_lock"} <= asked
    await api.async_close()
