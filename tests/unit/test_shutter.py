"""Unit tests for shutter position helpers."""

from __future__ import annotations

from enki.domain.capabilities import is_cover_device
from enki.domain.models import EnkiDevice
from enki.domain.state import EnkiDeviceState
from enki.lib.shutter import (
    normalize_shutter_position,
    roller_shutter_mode_options,
    roller_shutter_state_is_closing,
    roller_shutter_state_is_opening,
    shutter_opening_is_closed,
    shutter_preset_options,
)

_COVER_DEVICE_KWARGS = {
    "home_id": "h",
    "device_id": "d",
    "node_id": "n",
    "device_name": "VR Salon",
    "device_type": "access_and_motorizations",
    "is_enabled": True,
    "state": "ACTIVE",
    "capabilities": ["change_shutter_position", "check_shutter_position"],
}


def test_normalize_shutter_position() -> None:
    assert normalize_shutter_position(0) == 0
    assert normalize_shutter_position(50.4) == 50
    assert normalize_shutter_position(100) == 100
    assert normalize_shutter_position("bad") is None


def test_shutter_opening_is_closed() -> None:
    assert shutter_opening_is_closed("CLOSED") is True
    assert shutter_opening_is_closed("open") is False


def test_is_cover_device_from_capabilities() -> None:
    device = EnkiDevice(**_COVER_DEVICE_KWARGS)
    assert is_cover_device(device) is True


def test_device_state_shutter_fields() -> None:
    state = EnkiDeviceState(
        {
            "shutter_position": 42,
            "shutter_opening": "OPEN",
            "roller_shutter_state": "OPENING",
            "roller_shutter_mode": "NORMAL",
        }
    )
    assert state.shutter_position == 42
    assert state.shutter_opening == "OPEN"
    assert state.roller_shutter_state == "OPENING"
    assert state.roller_shutter_mode == "NORMAL"


def test_roller_shutter_state_motion_flags() -> None:
    assert roller_shutter_state_is_opening("OPENING") is True
    assert roller_shutter_state_is_closing("CLOSING") is True
    assert roller_shutter_state_is_opening("CLOSED") is False
    assert roller_shutter_state_is_closing("OPEN") is False


def test_roller_shutter_mode_options_from_referentiel() -> None:
    options = roller_shutter_mode_options(
        {"change_roller_shutter_mode": {"values": ["NORMAL", "INVERTED"]}}
    )
    assert options == ["normal", "inverted"]


def test_shutter_preset_options_empty_without_metadata() -> None:
    assert shutter_preset_options({}) == []
