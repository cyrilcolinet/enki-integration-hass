"""Branch coverage for the solar production value parser."""

from __future__ import annotations

from enki.lib.production import parse_production_value


def test_numeric_values_pass_through_as_float() -> None:
    assert parse_production_value(0) == 0.0
    assert parse_production_value(250) == 250.0
    assert parse_production_value(12.5) == 12.5


def test_string_with_unit_uses_bff_parser() -> None:
    assert parse_production_value("109 W") == 109.0
    assert parse_production_value("42.3 kWh") == 42.3


def test_plain_numeric_string() -> None:
    assert parse_production_value("88") == 88.0


def test_non_numeric_string_returns_none() -> None:
    # parse_bff_power fails and the float() fallback raises ValueError.
    assert parse_production_value("not-a-number") is None


def test_dict_value_key() -> None:
    assert parse_production_value({"value": "109 W"}) == 109.0


def test_dict_last_reported_value_key() -> None:
    assert parse_production_value({"lastReportedValue": 305}) == 305.0


def test_dict_amount_key() -> None:
    assert parse_production_value({"amount": 7.5}) == 7.5


def test_dict_nested_value() -> None:
    assert parse_production_value({"value": {"amount": "12 W"}}) == 12.0


def test_dict_first_matching_key_wins_over_later() -> None:
    assert parse_production_value({"value": 1, "amount": 999}) == 1.0


def test_dict_with_unparseable_value_returns_none() -> None:
    assert parse_production_value({"value": "??"}) is None


def test_dict_without_known_keys_returns_none() -> None:
    assert parse_production_value({"foo": 1}) is None


def test_none_and_other_types_return_none() -> None:
    assert parse_production_value(None) is None
    assert parse_production_value([1, 2, 3]) is None
