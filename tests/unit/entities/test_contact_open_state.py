"""Contact sensors report OPEN, not OPENED (issue #198)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.binary_sensor import _build_binary_sensor_entities
from enki.domain.models import EnkiDevice

_CAPABILITY = "check_contact_sensor_state"


def _sensor(value: str | None):
    device = EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node-contact",
        device_name="Porte cuisine",
        device_type="sensors",
        is_enabled=True,
        state="ACTIVE",
        capabilities=[_CAPABILITY, "check_vibration_detection"],
        last_reported_value={"contact_sensor_state": value} if value else {},
    )
    return next(
        e
        for e in _build_binary_sensor_entities(MagicMock(), device)
        if e._state_key == "contact_sensor_state"
    )


def test_open_is_on() -> None:
    # The gateway's own enum for check_contact_sensor_state is OPEN / CLOSED;
    # mapping only OPENED left every opening as "unknown" in Home Assistant.
    assert _sensor("OPEN").is_on is True


def test_opened_still_maps_for_safety() -> None:
    assert _sensor("OPENED").is_on is True


def test_closed_is_off() -> None:
    assert _sensor("CLOSED").is_on is False


def test_unknown_enum_stays_none_and_logs_once() -> None:
    from unittest.mock import patch

    import enki.binary_sensor as module

    module._UNMAPPED_SEEN.clear()
    with patch.object(module, "LOGGER") as logger:
        assert _sensor("AJAR").is_on is None
        assert _sensor("AJAR").is_on is None
    assert logger.debug.call_count == 1
