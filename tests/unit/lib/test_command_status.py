"""Unit tests for command HTTP status handling."""

from __future__ import annotations

from enki.lib.conversion import is_command_success_status


def test_is_command_success_status() -> None:
    assert is_command_success_status(202) is True
    assert is_command_success_status(204) is True
    assert is_command_success_status(200) is False
    assert is_command_success_status(500) is False
