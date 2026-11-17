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


def test_essentielb_is_in_the_enki_ecosystem() -> None:
    # Boulanger brand on the same platform, reported in #237.
    assert manufacturer_in_enki_ecosystem("EssentielB") is True
    assert manufacturer_in_enki_ecosystem("Essentiel B") is True
    assert device_in_enki_scope(manufacturer="EssentielB", device_type="lights") is True


def test_trio2sys_is_in_the_enki_ecosystem() -> None:
    # Temperature / humidity sensors on the Enki sensor service, reported in #364.
    assert manufacturer_in_enki_ecosystem("Trio2sys") is True
    assert device_in_enki_scope(manufacturer="Trio2sys", device_type="sensors") is True


def test_nous_is_in_the_enki_ecosystem() -> None:
    # Switchable outlets and modules on the standard power service, reported in #371.
    assert manufacturer_in_enki_ecosystem("Nous") is True
    assert device_in_enki_scope(manufacturer="Nous", device_type="outlets") is True
    assert device_in_enki_scope(manufacturer="Nous", device_type="modules") is True


def test_netsecur_is_in_the_enki_ecosystem() -> None:
    # Smoke detectors on the Enki smoke-detector service, reported in #371.
    assert manufacturer_in_enki_ecosystem("Netsecur") is True
    assert device_in_enki_scope(manufacturer="Netsecur", device_type="sensors") is True
