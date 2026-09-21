"""Enki home alarm: tile detection and state parsing (APK 2.26.3 shapes)."""

from __future__ import annotations

from enki.domain.security import (
    EnkiSecuritySystem,
    parse_configured_modes,
    parse_security_state,
    security_id_from_tile,
)


def test_security_tile_yields_its_id() -> None:
    tile = {"template": "SECURITY", "metadata": {"securityId": "sec-1"}, "state": "ACTIVE"}
    assert security_id_from_tile(tile) == "sec-1"


def test_device_tiles_are_not_security_tiles() -> None:
    device = {"template": "DEVICE", "metadata": {"deviceId": "d", "nodeId": "n"}}
    assert security_id_from_tile(device) is None
    assert security_id_from_tile({"template": "SECURITY", "metadata": {}}) is None
    assert security_id_from_tile("not a dict") is None  # type: ignore[arg-type]


def test_configured_modes_come_from_the_modes_list() -> None:
    payload = {"items": [{"type": "FULL"}, {"type": "partial"}, {"id": "no-type"}]}
    assert parse_configured_modes(payload) == frozenset({"FULL", "PARTIAL"})
    assert parse_configured_modes({}) == frozenset()


def _state(**overrides) -> dict:
    payload = {
        "homeId": "home-1",
        "threatLevel": "DEFAULT",
        "lastThreatDate": None,
        "currentMode": "FULL",
        "alarmDelay": 30,
        "notificationsEnabled": True,
    }
    payload.update(overrides)
    return payload


def _parse(payload: dict, modes=frozenset({"FULL", "PARTIAL"})) -> EnkiSecuritySystem | None:
    return parse_security_state(
        payload, home_id="home-1", security_id="sec-1", configured_modes=modes
    )


def test_state_is_parsed() -> None:
    system = _parse(_state())
    assert system is not None
    assert system.current_mode == "FULL"
    assert system.alarm_delay == 30
    assert system.notifications_enabled is True
    assert system.is_triggered is False


def test_empty_payload_means_no_alarm() -> None:
    assert _parse({}) is None


def test_intrusion_is_triggered_but_deterrence_is_not() -> None:
    assert _parse(_state(threatLevel="INTRUSION")).is_triggered is True
    assert _parse(_state(threatLevel="INTRUSION_CONFIRMED")).is_triggered is True
    assert _parse(_state(threatLevel="DANGER")).is_triggered is True
    # Pre-alarm warning: not a trigger until a real trace says otherwise.
    assert _parse(_state(threatLevel="DETERRENCE")).is_triggered is False


def test_arming_modes_exclude_disabled_and_unknown_types() -> None:
    system = _parse(_state(), modes=frozenset({"FULL", "DISABLED", "INACTIVE", "WHATEVER"}))
    assert system.arming_modes == frozenset({"FULL"})
