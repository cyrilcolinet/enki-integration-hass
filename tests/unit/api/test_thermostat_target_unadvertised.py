"""A radiator that can be written to but not read, per the referentiel (#335).

The reporter's Equation radiators advertise `change_thermostat_target_temperature`
and no `check_` counterpart, so the setpoint was never read, the climate entity
had no target temperature, and Home Assistant hid the +/- controls. Switching the
radiator off and back on was the only way to get them, which left the Enki
schedule. The route answers anyway, measured on 3 of his 4 units.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.capability_routing import CAPABILITY_READS
from enki.api.client import EnkiAPI
from enki.domain.capabilities import EnkiCapabilityProfile

WRITE_ONLY = [
    "change_thermostat_target_temperature",
    "check_current_temperature",
    "check_electrical_consumption",
]


def _profile(capabilities: list[str]) -> EnkiCapabilityProfile:
    return EnkiCapabilityProfile(
        device_type="heaters_and_pilot_wires",
        capabilities=tuple(capabilities),
        possible_values={},
    )


def test_the_setpoint_read_is_marked_for_devices_that_only_advertise_the_write() -> None:
    read = next(
        r for r in CAPABILITY_READS if r.capability == "check_thermostat_target_temperature"
    )

    assert read.also_when is not None
    assert read.also_when(_profile(WRITE_ONLY)), "the reporter's radiators"
    assert not read.also_when(_profile(["check_current_temperature"])), "a plain sensor"


@pytest.mark.asyncio
async def test_the_setpoint_is_read_although_the_referentiel_omits_it() -> None:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock()
    http.capability_get = AsyncMock(return_value={"lastReportedValue": 16.5})
    state: dict = {}

    await api._append_capability_states(http, "home", "node", _profile(WRITE_ONLY), state)

    assert state["thermostat_target_temperature"] == 16.5
    asked = {call.args[3] for call in http.capability_get.await_args_list}
    assert "check_thermostat_target_temperature" in asked
    await api.async_close()


@pytest.mark.asyncio
async def test_a_device_with_no_thermostat_capability_is_not_asked() -> None:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock()
    http.capability_get = AsyncMock(return_value={})
    await api._append_capability_states(
        http, "home", "node", _profile(["check_current_temperature"]), {}
    )

    asked = {call.args[3] for call in http.capability_get.await_args_list}
    assert "check_thermostat_target_temperature" not in asked
    await api.async_close()
