"""Unit tests for Enki integration device scope."""

from __future__ import annotations

from enki.lib.enki_scope import device_in_enki_scope, manufacturer_in_enki_ecosystem


def test_third_party_zigbee_out_of_scope() -> None:
    assert device_in_enki_scope(manufacturer="Sonoff", device_type="sensors") is False
    assert device_in_enki_scope(manufacturer="Tuya", device_type="sensors") is False
    assert device_in_enki_scope(manufacturer="Aqara", device_type="sensors") is False
    assert device_in_enki_scope(manufacturer=None, device_type="sensors") is False


def test_enki_ecosystem_in_scope() -> None:
    assert manufacturer_in_enki_ecosystem("Lexman") is True
    assert manufacturer_in_enki_ecosystem("Equation") is True
    assert manufacturer_in_enki_ecosystem("Noirot") is True
    assert manufacturer_in_enki_ecosystem("Envertech-Lexman") is True
    assert device_in_enki_scope(manufacturer="Lexman", device_type="sensors") is True


def test_native_enki_device_types_without_manufacturer() -> None:
    assert device_in_enki_scope(manufacturer=None, device_type="ceiling_fans") is True
    assert device_in_enki_scope(manufacturer=None, device_type="inverters") is True
    assert device_in_enki_scope(manufacturer=None, device_type="access_and_motorizations") is True
