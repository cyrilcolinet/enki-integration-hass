"""Unit tests for fan speed percentage mapping."""

from __future__ import annotations

from enki.const import FAN_SPEED_MAX, ORDERED_FAN_SPEEDS
from enki.lib.conversion import (
    fan_speed_to_percentage,
    percentage_to_fan_speed,
    percentage_to_speed,
    speed_to_percentage,
)


def test_speed_to_percentage_levels() -> None:
    assert speed_to_percentage(0) == 0
    assert speed_to_percentage(1) == 17
    assert speed_to_percentage(3) == 50
    assert speed_to_percentage(6) == 100


def test_percentage_round_trip() -> None:
    for speed in range(1, 7):
        percentage = speed_to_percentage(speed)
        restored = percentage_to_speed(percentage)
        assert restored == speed


def test_percentage_zero_is_off() -> None:
    assert percentage_to_speed(0) == 0


def test_ordered_fan_speeds_matches_enki_levels() -> None:
    assert list(range(1, FAN_SPEED_MAX + 1)) == ORDERED_FAN_SPEEDS
    for speed in ORDERED_FAN_SPEEDS:
        assert speed_to_percentage(speed) == round(speed * 100 / FAN_SPEED_MAX)


def test_percentage_to_fan_speed_low_values_turn_off() -> None:
    assert percentage_to_fan_speed(0, 6) == 0
    assert percentage_to_fan_speed(8, 6) == 0
    assert percentage_to_fan_speed(17, 6) == 1


def test_fan_speed_to_percentage_linear() -> None:
    assert fan_speed_to_percentage(0, 6) == 0
    assert fan_speed_to_percentage(3, 6) == 50
    assert fan_speed_to_percentage(6, 6) == 100
