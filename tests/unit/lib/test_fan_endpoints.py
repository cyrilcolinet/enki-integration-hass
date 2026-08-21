"""Unit tests for fan endpoint resolution."""

from __future__ import annotations

from enki.lib.fan_endpoints import (
    infer_fan_motor_endpoints,
    motor_endpoints_from_metadata,
)


def test_motor_endpoints_from_metadata_type_fan() -> None:
    entries = (
        {"id": 1, "type": "LIGHTING"},
        {"id": 2, "type": "FAN"},
        {"id": 3, "type": "LIGHTING"},
    )
    assert motor_endpoints_from_metadata(entries) == frozenset({2})


def test_infer_fan_motor_endpoints_radix_by_name() -> None:
    motors = infer_fan_motor_endpoints(
        power_endpoints=[1, 2, 3],
        endpoint_entries=(1, 2, 3),
        supports_light_state=True,
        supports_fan_speed=True,
        device_name="Ventilateur Radix",
        referentiel_i18n="",
        referentiel_model="",
    )
    assert motors == frozenset({2})


def test_infer_fan_motor_endpoints_siroco_default() -> None:
    motors = infer_fan_motor_endpoints(
        power_endpoints=[1, 2, 3],
        endpoint_entries=(1, 2, 3),
        supports_light_state=True,
        supports_fan_speed=True,
        device_name="Inspire Siroco+",
        referentiel_i18n="",
        referentiel_model="",
    )
    assert motors == frozenset({1})
