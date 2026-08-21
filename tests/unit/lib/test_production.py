"""Unit tests for solar production parsers."""

from __future__ import annotations

from enki.lib.production import parse_production_value


def test_parse_production_value_numeric() -> None:
    assert parse_production_value(250) == 250.0
    assert parse_production_value(12.5) == 12.5


def test_parse_production_value_string_with_unit() -> None:
    assert parse_production_value("109 W") == 109.0
    assert parse_production_value("42.3 kWh") == 42.3
