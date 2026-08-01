"""Dry-contact / electric-strike state as a binary sensor (issue #121)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.binary_sensor import _build_binary_sensor_entities
from enki.domain.models import EnkiDevice
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

_CAPABILITY = "check_dry_contact_for_electric_strike_state"


def _module(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "dev",
        "node_id": "node-module",
        "device_name": "Module Eclairage",
        "device_type": "modules",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["power_on_with_timer", "check_electrical_power", _CAPABILITY],
        "last_reported_value": {"dry_contact_state": "OPENED"},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_profile_flags_dry_contact_binary_sensor() -> None:
    profile = _module().profile
    assert profile.supports_dry_contact_state is True
    assert profile.is_binary_sensor is True


def test_capability_read_routes_dry_contact_via_power_service() -> None:
    read = next((r for r in CAPABILITY_READS if r.capability == _CAPABILITY), None)
    assert read is not None
    assert read.transport_id == "power"
    assert read.state_key == "dry_contact_state"


def test_builds_dry_contact_binary_sensor() -> None:
    entities = _build_binary_sensor_entities(MagicMock(), _module())
    sensor = next(e for e in entities if e._state_key == "dry_contact_state")
    assert sensor._attr_device_class == BinarySensorDeviceClass.OPENING
    assert sensor._attr_translation_key == "dry_contact"


def test_dry_contact_is_on_maps_open_closed() -> None:
    sensor = next(
        e
        for e in _build_binary_sensor_entities(MagicMock(), _module())
        if e._state_key == "dry_contact_state"
    )
    assert sensor.is_on is True  # OPENED

    closed = next(
        e
        for e in _build_binary_sensor_entities(
            MagicMock(), _module(last_reported_value={"dry_contact_state": "CLOSED"})
        )
        if e._state_key == "dry_contact_state"
    )
    assert closed.is_on is False
