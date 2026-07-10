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

_voluptuous = MagicMock()
_voluptuous.Schema = MagicMock(side_effect=lambda schema: schema)
_voluptuous.Required = MagicMock(side_effect=lambda key, **kwargs: key)
sys.modules.setdefault("voluptuous", _voluptuous)

_HA_STUBS = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_registry",
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
    "homeassistant.components.cover",
    "homeassistant.components.button",
    "homeassistant.util",
]

for module_name in _HA_STUBS:
    sys.modules.setdefault(module_name, MagicMock())

_config_entries = sys.modules["homeassistant.config_entries"]


class _ConfigFlow:
    """Minimal ConfigFlow stand-in so EnkiConfigFlow is a real class in tests."""

    VERSION = 1
    domain: str | None = None

    def __init_subclass__(cls, domain: str | None = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if domain is not None:
            cls.domain = domain

    @staticmethod
    async def async_migrate_entry(hass, config_entry):
        return True


class _OptionsFlow:
    """Minimal OptionsFlow stand-in for config_flow imports."""


_config_entries.ConfigFlow = _ConfigFlow
_config_entries.OptionsFlow = _OptionsFlow
_config_entries.ConfigFlowResult = dict

_ha_const = sys.modules["homeassistant.const"]
_ha_const.CONF_USERNAME = "username"
_ha_const.CONF_PASSWORD = "password"
_ha_const.CONF_SCAN_INTERVAL = "scan_interval"


class _HaEntity:
    """Minimal HA Entity stand-in for unit tests."""

    def async_write_ha_state(self) -> None:
        return None


class _CoordinatorEntity(_HaEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    def __class_getitem__(cls, _item):
        return cls


class _FanEntity(_HaEntity):
    pass


class _FanEntityFeature:
    SET_SPEED = 1
    TURN_ON = 2
    TURN_OFF = 4
    DIRECTION = 8
    PRESET_MODE = 16


_update_coordinator = sys.modules["homeassistant.helpers.update_coordinator"]
_update_coordinator.CoordinatorEntity = _CoordinatorEntity

_fan = sys.modules["homeassistant.components.fan"]
_fan.FanEntity = _FanEntity
_fan.FanEntityFeature = _FanEntityFeature
_fan.DIRECTION_FORWARD = "forward"
_fan.DIRECTION_REVERSE = "reverse"

_core = sys.modules["homeassistant.core"]
_core.callback = lambda fn: fn

_device_registry = sys.modules["homeassistant.helpers.device_registry"]
_device_registry.DeviceInfo = dict


def _ordered_list_item_to_percentage(speeds: list[int], speed: int) -> int:
    if not speeds:
        return 0
    try:
        index = speeds.index(speed)
    except ValueError:
        return 0
    return round((index + 1) * 100 / len(speeds))


def _percentage_to_ordered_list_item(speeds: list[int], percentage: int) -> int:
    if not speeds or percentage <= 0:
        return 0
    index = max(0, min(len(speeds) - 1, round(percentage * len(speeds) / 100) - 1))
    return speeds[index]


_percentage = MagicMock()
_percentage.ordered_list_item_to_percentage = _ordered_list_item_to_percentage
_percentage.percentage_to_ordered_list_item = _percentage_to_ordered_list_item
sys.modules["homeassistant.util.percentage"] = _percentage

_cover = sys.modules["homeassistant.components.cover"]


class _CoverEntityFeature:
    OPEN = 1
    CLOSE = 2
    SET_POSITION = 4
    STOP = 8


class _CoverDeviceClass:
    SHUTTER = "shutter"


_cover.CoverEntity = _HaEntity
_cover.CoverEntityFeature = _CoverEntityFeature
_cover.CoverDeviceClass = _CoverDeviceClass

_button = sys.modules["homeassistant.components.button"]
_button.ButtonEntity = _HaEntity
