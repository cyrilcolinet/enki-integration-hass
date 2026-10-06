"""Reading an Equation air conditioner's state (#286)."""

from __future__ import annotations

from enki.domain.airco import AIRCO_STATE_KEYS, parse_airconditioner_state
from enki.domain.models import EnkiDevice
from enki.domain.profile import sanitize_poll_state

# check-airconditioner-state as the app's own DTO describes it: lastReportedValue
# is an object, mirroring the body of change-airconditioner-state field for field.
AIRCO_STATE = {
    "nodeId": "node-ac",
    "homeId": "home-1",
    "lastReportedDate": "2026-10-04T18:12:00.000Z",
    "lastReportedValue": {
        "targetTemperature": 21.0,
        "currentTemperature": 26.0,
        "operatingMode": "COOLING",
        "power": "ON",
        "fanSpeed": "AUTO",
        "swingOrientation": {"horizontal": "NIV_2", "vertical": "AUTO"},
        "selfCleanMode": "OFF",
        "frostProtectionMode": "OFF",
        "healthMode": "OFF",
        "quietMode": "OFF",
        "sleepMode": "OFF",
    },
}


def _aircon(**reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-ac",
        device_name="Clim",
        device_type="air_conditioners",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["check_airconditioner_state", "switch_electrical_power"],
        last_reported_value=reported,
    )


def test_the_nested_state_is_flattened() -> None:
    state = parse_airconditioner_state(AIRCO_STATE)

    assert state["airco_operating_mode"] == "COOLING"
    assert state["airco_target_temperature"] == 21.0
    assert state["airco_fan_speed"] == "AUTO"
    assert state["airco_swing_horizontal"] == "NIV_2"
    assert state["airco_swing_vertical"] == "AUTO"
    assert set(state) == set(AIRCO_STATE_KEYS)


def test_a_response_without_the_nested_object_yields_nothing() -> None:
    assert parse_airconditioner_state({"lastReportedValue": None}) == {}
    assert parse_airconditioner_state({}) == {}
    assert parse_airconditioner_state({"lastReportedValue": "ON"}) == {}


def test_unexpected_fields_are_ignored_and_missing_ones_skipped() -> None:
    state = parse_airconditioner_state(
        {"lastReportedValue": {"operatingMode": "HEATING", "unknownThing": {"a": 1}}}
    )

    assert state == {"airco_operating_mode": "HEATING"}


def test_the_flattened_state_reaches_diagnostics() -> None:
    """The reason for reading this today: a reporter's own values, not a guess."""
    exported = sanitize_poll_state(parse_airconditioner_state(AIRCO_STATE))

    assert exported["airco_operating_mode"] == "COOLING"
    assert exported["airco_fan_speed"] == "AUTO"


def test_only_a_unit_advertising_the_capability_is_read() -> None:
    assert _aircon().profile.supports_airconditioner_state is True

    plain = EnkiDevice(
        home_id="home-1",
        device_id="dev-2",
        node_id="node-plug",
        device_name="Prise",
        device_type="outlets",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["switch_electrical_power"],
    )
    assert plain.profile.supports_airconditioner_state is False
