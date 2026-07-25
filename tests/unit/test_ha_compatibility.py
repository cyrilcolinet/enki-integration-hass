"""Guard `homeassistant.const` imports against the minimum HA version we support."""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT = REPO_ROOT / "custom_components" / "enki"
HACS_MANIFEST = REPO_ROOT / "hacs.json"

# Removed from homeassistant.const — use UnitOf* StrEnum members instead.
BANNED_CONST_SYMBOLS = frozenset(
    {
        "ENERGY_KILO_WATT_HOUR",
        "ENERGY_WATT_HOUR",
        "ENERGY_MEGAJOULE",
        "POWER_WATT",
        "POWER_KILO_WATT",
        "TEMP_CELSIUS",
        "TEMP_FAHRENHEIT",
        "TEMP_KELVIN",
    }
)

# Symbols added to homeassistant.const in a given release. Importing one on an older
# core raises ImportError, which HA swallows: the whole platform silently disappears.
CONST_SYMBOL_ADDED_IN = {
    "UnitOfRatio": (2026, 7, 0),
}


def _min_supported_ha_version() -> tuple[int, ...]:
    manifest = json.loads(HACS_MANIFEST.read_text(encoding="utf-8"))
    return tuple(int(part) for part in manifest["homeassistant"].split("."))


def _const_imports_from_ast(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "homeassistant.const":
            continue
        for alias in node.names:
            names.add(alias.name)
    return names


def test_no_removed_home_assistant_const_symbols() -> None:
    # Given / When
    violations: list[str] = []
    for path in sorted(COMPONENT.rglob("*.py")):
        banned = _const_imports_from_ast(path) & BANNED_CONST_SYMBOLS
        if banned:
            violations.append(f"{path.relative_to(REPO_ROOT)}: {sorted(banned)}")

    # Then
    assert not violations, "Removed HA const imports found:\n" + "\n".join(violations)


def test_no_const_symbol_newer_than_minimum_supported_core() -> None:
    # Given
    minimum = _min_supported_ha_version()

    # When
    violations: list[str] = []
    for path in sorted(COMPONENT.rglob("*.py")):
        for symbol in sorted(_const_imports_from_ast(path)):
            added_in = CONST_SYMBOL_ADDED_IN.get(symbol)
            if added_in and added_in > minimum:
                rel = path.relative_to(REPO_ROOT)
                added = ".".join(str(part) for part in added_in)
                violations.append(f"{rel}: {symbol} requires HA {added}")

    # Then
    declared = ".".join(str(part) for part in minimum)
    assert not violations, (
        f"hacs.json declares HA {declared} as minimum, but these imports need a newer core:\n"
        + "\n".join(violations)
    )


def test_sensor_uses_modern_unit_enums() -> None:
    # Given / When
    imports = _const_imports_from_ast(COMPONENT / "sensor.py")

    # Then
    assert "UnitOfEnergy" in imports
    assert "UnitOfPower" in imports
    assert "UnitOfTemperature" in imports
    assert not imports & BANNED_CONST_SYMBOLS
