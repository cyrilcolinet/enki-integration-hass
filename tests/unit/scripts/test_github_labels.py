"""Unit tests for GitHub label definitions."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "custom_components"))

from github_labels import github_label_definitions  # noqa: E402


def test_github_label_names_are_unique() -> None:
    names = [name for name, _color, _description in github_label_definitions()]
    assert len(names) == len(set(names))
