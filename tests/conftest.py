"""Shared pytest fixtures."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))


def _patch_aiohttp_client_response_for_aioresponses() -> None:
    """aioresponses 0.7.8 omits stream_writer required by aiohttp 3.14+."""
    import aiohttp.client_reqrep

    original_init = aiohttp.client_reqrep.ClientResponse.__init__
    if "stream_writer" not in inspect.signature(original_init).parameters:
        return

    def patched_init(self, *args, **kwargs):
        if "stream_writer" not in kwargs:
            kwargs["stream_writer"] = Mock(output_size=0)
        original_init(self, *args, **kwargs)

    aiohttp.client_reqrep.ClientResponse.__init__ = patched_init  # type: ignore[method-assign]


_patch_aiohttp_client_response_for_aioresponses()

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
    "homeassistant.components.sensor",
]

for module_name in _HA_STUBS:
    sys.modules.setdefault(module_name, MagicMock())
