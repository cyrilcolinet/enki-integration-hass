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
    "homeassistant.components.climate",
    "homeassistant.components.climate.const",
    "homeassistant.components.switch",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.camera",
    "homeassistant.components.number",
    "homeassistant.components.select",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.util",
]

for module_name in _HA_STUBS:
    sys.modules.setdefault(module_name, MagicMock())

# Real package so submodule imports like homeassistant.components.climate work.
_components = sys.modules["homeassistant.components"]
_components.__path__ = []  # type: ignore[attr-defined]
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
_ha_const.__version__ = "test"
_ha_const.ATTR_TEMPERATURE = "temperature"
_ha_const.LIGHT_LUX = "lx"
_ha_const.PERCENTAGE = "%"
_ha_const.UnitOfEnergy = MagicMock()
_ha_const.UnitOfPower = MagicMock()
_ha_const.UnitOfTemperature = MagicMock()
_ha_const.UnitOfTemperature.CELSIUS = "°C"
_ha_const.UnitOfPower.WATT = "W"
_ha_const.UnitOfEnergy.KILO_WATT_HOUR = "kWh"


class _HaEntity:
    """Minimal HA Entity stand-in for unit tests."""

    _attr_assumed_state = False

    def async_write_ha_state(self) -> None:
        return None

    @property
    def assumed_state(self) -> bool:
        return self._attr_assumed_state


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


class _DataUpdateCoordinator:
    """Minimal DataUpdateCoordinator stand-in so EnkiCoordinator is a real class."""

    def __init__(self, *args, **kwargs) -> None:
        self.data = None

    def __class_getitem__(cls, _item):
        return cls

    def async_set_updated_data(self, data) -> None:
        self.data = data


class _UpdateFailed(Exception):
    """Minimal UpdateFailed stand-in — must stay raisable."""


_update_coordinator = sys.modules["homeassistant.helpers.update_coordinator"]
_update_coordinator.CoordinatorEntity = _CoordinatorEntity
_update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
_update_coordinator.UpdateFailed = _UpdateFailed

_fan = sys.modules["homeassistant.components.fan"]
_fan.FanEntity = _FanEntity
_fan.FanEntityFeature = _FanEntityFeature
_fan.DIRECTION_FORWARD = "forward"
_fan.DIRECTION_REVERSE = "reverse"

_core = sys.modules["homeassistant.core"]
_core.callback = lambda fn: fn


class _HomeAssistantError(Exception):
    """Minimal HomeAssistantError stand-in — must stay raisable."""


class _ConfigEntryNotReady(_HomeAssistantError):
    """Minimal ConfigEntryNotReady stand-in — must stay raisable."""


_ha_exceptions = sys.modules["homeassistant.exceptions"]
_ha_exceptions.HomeAssistantError = _HomeAssistantError
_ha_exceptions.ConfigEntryNotReady = _ConfigEntryNotReady

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

_light = sys.modules["homeassistant.components.light"]
_light.LightEntity = _HaEntity
_light.ColorMode = MagicMock()
_light.ATTR_HS_COLOR = "hs_color"
_light.ATTR_BRIGHTNESS = "brightness"
_light.ATTR_COLOR_TEMP_KELVIN = "color_temp_kelvin"

_light_const = sys.modules["homeassistant.components.light.const"]
_light_const.DEFAULT_MAX_KELVIN = 6500
_light_const.DEFAULT_MIN_KELVIN = 2000

_sensor = sys.modules["homeassistant.components.sensor"]
_sensor.SensorEntity = _HaEntity
_sensor.SensorDeviceClass = MagicMock()
_sensor.SensorStateClass = MagicMock()

_climate = sys.modules["homeassistant.components.climate"]
_climate.ClimateEntity = _HaEntity

_climate_const = sys.modules["homeassistant.components.climate.const"]
_climate_const.ClimateEntityFeature = MagicMock()
_climate_const.HVACAction = MagicMock()
_climate_const.HVACMode = MagicMock()

_switch = sys.modules["homeassistant.components.switch"]
_switch.SwitchEntity = _HaEntity
_switch.SwitchDeviceClass = MagicMock()

_binary_sensor = sys.modules["homeassistant.components.binary_sensor"]
_binary_sensor.BinarySensorEntity = _HaEntity
_binary_sensor.BinarySensorDeviceClass = MagicMock()

_camera = sys.modules["homeassistant.components.camera"]
_camera.Camera = _HaEntity

# Give homeassistant.util.dt a real-ish parse_datetime so timestamp sensors work.
import datetime as _datetime  # noqa: E402


def _parse_datetime(value: object) -> _datetime.datetime | None:
    try:
        return _datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


_util = sys.modules["homeassistant.util"]
_util.dt = MagicMock()
_util.dt.parse_datetime = _parse_datetime

_number = sys.modules["homeassistant.components.number"]
_number.NumberEntity = _HaEntity

_select = sys.modules["homeassistant.components.select"]
_select.SelectEntity = _HaEntity
