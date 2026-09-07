"""DIO outlets: in scope, and assumed-state because the RF is one-way (#203)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.domain.models import EnkiDevice
from enki.lib.enki_scope import device_in_enki_scope
from enki.switch import _build_switch_entities


def _dio_outlet(**overrides) -> EnkiDevice:
    # Shape reported by scripts/discover_devices.py on a DIO 2300 W nano outlet.
    defaults = {
        "home_id": "home",
        "device_id": "dev-dio",
        "node_id": "node-dio",
        "device_name": "Prise salon",
        "device_type": "outlets",
        "bff_device_type": "outlets",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "cancel_electrical_power_switch_in",
            "next_electrical_power_switch_in",
            "switch_electrical_power",
            "switch_electrical_power_in",
        ],
        "possible_values": {"switch_electrical_power": {"values": ["ON", "OFF"]}},
        "referentiel_i18n": "tr_device_dio_outlet_2300Watt_nano_label",
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_dio_is_in_enki_scope() -> None:
    # DIO is an Enki hub partner (433 MHz RF), not third-party Zigbee.
    assert device_in_enki_scope(manufacturer="Dio", device_type="outlets") is True


def test_unrelated_brand_still_out_of_scope() -> None:
    assert device_in_enki_scope(manufacturer="Tuya", device_type="outlets") is False


def test_dio_outlet_builds_a_switch() -> None:
    entities = _build_switch_entities(MagicMock(), _dio_outlet())
    assert len(entities) == 1


def test_dio_outlet_is_assumed_state() -> None:
    # No check_electrical_power: the cloud never learns the real state, so the
    # entity must not claim to know it.
    switch = _build_switch_entities(MagicMock(), _dio_outlet())[0]
    assert switch._attr_assumed_state is True
    assert switch.is_on is None


def test_readable_outlet_is_not_assumed_state() -> None:
    device = _dio_outlet(
        capabilities=["switch_electrical_power", "check_electrical_power"],
        last_reported_value={"electrical_power": "ON"},
    )
    switch = _build_switch_entities(MagicMock(), device)[0]
    assert switch._attr_assumed_state is False
    assert switch.is_on is True
