"""Smoke-import every HA platform module so ImportError cannot hide them."""

from __future__ import annotations

import importlib

import pytest

PLATFORM_MODULES = (
    "diagnostics",
    "fan",
    "light",
    "climate",
    "cover",
    "switch",
    "sensor",
    "binary_sensor",
    "number",
    "select",
    "button",
    "update",
    "camera",
    "device_trigger",
    "config_flow",
    "migration",
)


@pytest.mark.parametrize("module_name", PLATFORM_MODULES)
def test_platform_module_imports(module_name: str) -> None:
    # Given / When
    module = importlib.import_module(f"enki.{module_name}")

    # Then
    assert module is not None
