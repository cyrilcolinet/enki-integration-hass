"""Unit tests for fan blade rotation mapping."""

from __future__ import annotations

from enki.const import DIRECTION_FORWARD, DIRECTION_REVERSE
from enki.lib.conversion import direction_to_enki_rotation, enki_rotation_to_direction


def test_enki_rotation_to_direction_clockwise() -> None:
    assert enki_rotation_to_direction("CLOCKWISE") == DIRECTION_FORWARD
    assert enki_rotation_to_direction("COUNTERCLOCKWISE") == DIRECTION_REVERSE
    assert enki_rotation_to_direction("FORWARD") == DIRECTION_FORWARD
    assert enki_rotation_to_direction("REVERSE") == DIRECTION_REVERSE


def test_enki_rotation_to_direction_legacy_aliases() -> None:
    assert enki_rotation_to_direction("SUMMER") == DIRECTION_FORWARD
    assert enki_rotation_to_direction("WINTER") == DIRECTION_REVERSE


def test_enki_rotation_to_direction_from_state_dict() -> None:
    assert enki_rotation_to_direction({"rotation": "COUNTERCLOCKWISE"}) == DIRECTION_REVERSE


def test_direction_to_enki_rotation_round_trip() -> None:
    assert direction_to_enki_rotation(DIRECTION_FORWARD) == "CLOCKWISE"
    assert direction_to_enki_rotation(DIRECTION_REVERSE) == "COUNTERCLOCKWISE"
    assert enki_rotation_to_direction(direction_to_enki_rotation(DIRECTION_FORWARD)) == (
        DIRECTION_FORWARD
    )
