"""strings.json is the source of truth for every translated string.

Two entity keys once lived only in translations/*.json: the entities were named
for users, but the source file the Home Assistant tooling reads had no trace of
them. Nothing failed loudly — which is why this is checked here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_PACKAGE = Path(__file__).resolve().parents[3] / "custom_components" / "enki"
_TRANSLATIONS = sorted((_PACKAGE / "translations").glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _keys(node: object, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return set()
    found: set[str] = set()
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        found.add(path)
        found |= _keys(value, path)
    return found


def _translation_keys_used_in_code() -> set[str]:
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(_PACKAGE.rglob("*.py")))
    return set(re.findall(r'translation_key\s*=\s*"([a-z0-9_]+)"', source)) | set(
        re.findall(r'"translation_key":\s*"([a-z0-9_]+)"', source)
    )


def test_translation_files_exist() -> None:
    assert _TRANSLATIONS, "no translations shipped"


@pytest.mark.parametrize("path", _TRANSLATIONS, ids=lambda path: path.name)
def test_translation_matches_strings(path: Path) -> None:
    strings = _keys(_load(_PACKAGE / "strings.json"))
    translated = _keys(_load(path))
    assert translated - strings == set(), f"{path.name} declares keys absent from strings.json"
    assert strings - translated == set(), f"{path.name} is missing keys from strings.json"


def test_every_entity_translation_key_is_declared() -> None:
    strings = _load(_PACKAGE / "strings.json")
    declared = {key for platform in strings.get("entity", {}).values() for key in platform}
    declared |= set(strings.get("issues", {}))
    # Dynamic keys, built from a tuple rather than a literal assignment.
    declared |= {"fan_light_main", "fan_light_ambient", "fan_light_numbered"}
    assert _translation_keys_used_in_code() - declared == set()
