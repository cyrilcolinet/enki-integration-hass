"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))

_HA_STUBS = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.storage",
    "homeassistant.components",
    "homeassistant.components.fan",
    "homeassistant.components.light",
    "homeassistant.components.light.const",
    "homeassistant.components.diagnostics",
    "homeassistant.components.persistent_notification",
]

for module_name in _HA_STUBS:
    sys.modules.setdefault(module_name, MagicMock())
