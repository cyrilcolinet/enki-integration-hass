"""Unit tests for Enki light supported-color-mode selection and HS conversion."""

from __future__ import annotations

from enki.lib.conversion import enki_to_hs, hs_to_enki, select_light_color_modes


def test_color_temp_wins_over_brightness() -> None:
    assert select_light_color_modes(
        has_hs=False, has_color_temp=True, has_brightness=True
    ) == {"color_temp"}


def test_color_temp_only() -> None:
    assert select_light_color_modes(
        has_hs=False, has_color_temp=True, has_brightness=False
    ) == {"color_temp"}


def test_brightness_only() -> None:
    assert select_light_color_modes(
        has_hs=False, has_color_temp=False, has_brightness=True
    ) == {"brightness"}


def test_onoff_fallback() -> None:
    assert select_light_color_modes(
        has_hs=False, has_color_temp=False, has_brightness=False
    ) == {"onoff"}


def test_hs_and_color_temp_combine() -> None:
    assert select_light_color_modes(
        has_hs=True, has_color_temp=True, has_brightness=True
    ) == {"hs", "color_temp"}


def test_hs_only_drops_brightness() -> None:
    assert select_light_color_modes(
        has_hs=True, has_color_temp=False, has_brightness=True
    ) == {"hs"}


def test_hs_to_enki_normalizes() -> None:
    assert hs_to_enki(0, 0) == (0.0, 0.0)
    assert hs_to_enki(360, 100) == (1.0, 1.0)
    assert hs_to_enki(180, 50) == (0.5, 0.5)


def test_enki_to_hs_denormalizes() -> None:
    assert enki_to_hs(0.0, 0.0) == (0.0, 0.0)
    assert enki_to_hs(1.0, 1.0) == (360.0, 100.0)
    assert enki_to_hs(0.5, 0.5) == (180.0, 50.0)


def test_enki_to_hs_missing_returns_none() -> None:
    assert enki_to_hs(None, 0.5) is None
    assert enki_to_hs(0.5, None) is None


def test_hs_roundtrip() -> None:
    hue, sat = hs_to_enki(210, 80)
    result = enki_to_hs(hue, sat)
    assert result is not None
    assert abs(result[0] - 210) <= 4
    assert abs(result[1] - 80) <= 1
