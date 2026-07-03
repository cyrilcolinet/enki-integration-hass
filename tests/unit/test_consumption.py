"""Unit tests for Edisio electrical consumption."""

from __future__ import annotations

from enki.domain.capabilities import device_is_supported
from enki.domain.models import EnkiDevice
from enki.domain.state import EnkiDeviceState


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "63a053851a423d4a245a877c",
        "node_id": "node-edisio",
        "device_name": "Edisio plug",
        "device_type": "power",
        "is_enabled": True,
        "state": "ACTIVE",
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def test_edisio_consumption_capability() -> None:
    device = _device(
        capabilities=[
            "switch_electrical_power",
            "check_electrical_power",
            "check_electrical_consumption",
        ],
    )
    profile = device.profile
    assert profile.supports_electrical_consumption is True
    assert profile.supports_electrical_power is True
    assert device_is_supported(device) is True


def test_electrical_consumption_state() -> None:
    state = EnkiDeviceState(
        {"electrical_consumption": 42.5, "electrical_consumption_unit": "W"},
    )
    assert state.electrical_consumption == 42.5
    assert state.electrical_consumption_unit == "W"
