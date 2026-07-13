"""Light platform for Enki lights, fan kits, switches and multi-endpoint nodes."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.components.light.const import DEFAULT_MAX_KELVIN, DEFAULT_MIN_KELVIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity
from .lib.conversion import enki_to_hs, hs_to_enki, select_light_color_modes
from .platforms.light.behavior import EnkiLightBehaviorMixin


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    entities: list[LightEntity] = []
    for device in coordinator.data or []:
        entities.extend(_build_light_entities(coordinator, device))
    async_add_entities(entities)


def _build_light_entities(
    coordinator: EnkiCoordinator,
    device: EnkiDevice,
) -> list[LightEntity]:
    profile = device.profile
    if not profile.is_light_controllable:
        return []

    if profile.is_fan:
        light_endpoints = profile.fan_light_endpoints
        if len(light_endpoints) > 1:
            return [
                EnkiFanLightEntity(
                    coordinator,
                    device,
                    endpoint_id=endpoint_id,
                    suffix=f"light_{chr(ord('a') + index)}",
                )
                for index, endpoint_id in enumerate(light_endpoints)
            ]
        return [EnkiFanLightEntity(coordinator, device)]

    endpoint_ids = profile.power_switch_endpoints
    if endpoint_ids:
        return [
            EnkiLightEntity(
                coordinator,
                device,
                suffix=f"light_{chr(ord('a') + index)}",
                endpoint_id=endpoint_id,
            )
            for index, endpoint_id in enumerate(endpoint_ids)
        ]

    return [EnkiLightEntity(coordinator, device, suffix="light")]


class EnkiFanLightEntity(EnkiLightBehaviorMixin, EnkiEntity, LightEntity):
    """Light kit on an ESDK ceiling fan (api-enki-lighting-prod)."""

    _attr_translation_key = "fan_light"
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = 2748
    _attr_max_color_temp_kelvin = 6500
    _brightness_max = 100
    _color_temp_values: list[int] = []

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        *,
        endpoint_id: int | None = None,
        suffix: str = "light",
    ) -> None:
        super().__init__(coordinator, device)
        self._endpoint_id = endpoint_id
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{suffix}"
        possible = device.profile.possible_values
        self._brightness_max = self._parse_brightness_max(possible)
        self._color_temp_values = self._parse_color_temp_values(possible)

    @property
    def is_on(self) -> bool:
        return self._device.reported.light_power == "ON"

    @property
    def brightness(self) -> int | None:
        raw = self._device.reported.brightness
        return round(raw * 255 / self._brightness_max) if raw is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        raw = self._device.reported.color_temperature
        return int(raw.strip("TK")) if raw else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        if (
            self._endpoint_id is not None
            and self._uses_endpoint_power(self._endpoint_id)
            and self._simple_light_turn_on(kwargs)
        ):
            await self._switch_endpoint_power(self._endpoint_id, "ON")
            return

        fallback_endpoint = self._bare_power_fallback_endpoint(kwargs)
        if fallback_endpoint is not None:
            await self.coordinator.api.async_switch_electrical_power(
                self._device.home_id,
                self._device.node_id,
                "ON",
                endpoint=fallback_endpoint,
            )
            self._cache_global_light_on(self.coordinator)
            self._update_light_endpoint_cache("ON", fallback_endpoint)
            return

        await self._mixed_endpoint_workaround()
        changes = self._build_turn_on_changes(kwargs, restore_last_brightness=True)
        if changes.get("power") == "OFF":
            await self.async_turn_off(**kwargs)
            return
        await self.coordinator.api.async_change_light_state(
            self._device.home_id,
            self._device.node_id,
            changes,
        )
        self._cache_global_light_on(self.coordinator)
        self._update_light_endpoint_cache("ON", self._endpoint_id)
        if "brightness" in changes:
            self.coordinator.update_cached_value(self.node_id, "brightness", changes["brightness"])
        if "colorTemperature" in changes:
            self.coordinator.update_cached_value(
                self.node_id,
                "colorTemperature",
                changes["colorTemperature"],
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._endpoint_id is not None and self._uses_endpoint_power(self._endpoint_id):
            await self._switch_endpoint_power(self._endpoint_id, "OFF")
            return

        await self.coordinator.api.async_change_light_state(
            self._device.home_id,
            self._device.node_id,
            {"power": "OFF"},
        )
        self._cache_global_light_off(self.coordinator)
        self._update_light_endpoint_cache("OFF", self._endpoint_id)


class EnkiLightEntity(EnkiLightBehaviorMixin, EnkiEntity, LightEntity):
    """Standard Enki light or dimmer node."""

    _attr_translation_key = "light"
    _brightness_max = 100
    _color_temp_values: list[int] = []

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        *,
        suffix: str,
        endpoint_id: int | None = None,
        translation_key: str = "light",
    ) -> None:
        super().__init__(coordinator, device)
        self._endpoint_id = endpoint_id
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{suffix}"

        profile = device.profile
        caps = profile.capabilities
        possible = profile.possible_values
        self._supports_light_state = profile.supports_light_state
        modes: set[ColorMode] = set()

        if "change_color_temperature" in caps:
            modes.add(ColorMode.COLOR_TEMP)
            self._color_temp_values = self._parse_color_temp_values(possible)
            if self._color_temp_values:
                self._attr_min_color_temp_kelvin = min(self._color_temp_values)
                self._attr_max_color_temp_kelvin = max(self._color_temp_values)
            else:
                self._attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN
                self._attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN

        if "change_hue" in caps and "change_saturation" in caps:
            modes.add(ColorMode.HS)

        if "change_brightness" in caps:
            modes.add(ColorMode.BRIGHTNESS)
            self._brightness_max = self._parse_brightness_max(possible)

        if not modes and profile.supports_electrical_power:
            modes.add(ColorMode.ONOFF)

        supported = {
            ColorMode(value)
            for value in select_light_color_modes(
                has_hs=ColorMode.HS in modes,
                has_color_temp=ColorMode.COLOR_TEMP in modes,
                has_brightness=ColorMode.BRIGHTNESS in modes,
            )
        }
        self._attr_supported_color_modes = supported or {ColorMode.ONOFF}
        if len(self._attr_supported_color_modes) == 1:
            self._attr_color_mode = next(iter(self._attr_supported_color_modes))

    @property
    def is_on(self) -> bool:
        reported = self._device.reported
        if self._endpoint_id is not None:
            power = reported.endpoint_power(self._endpoint_id)
            return power == "ON" if power is not None else False

        if self._supports_light_state:
            if reported.global_power is not None:
                return reported.global_power == "ON"
            return False

        return reported.electrical_power == "ON"

    @property
    def brightness(self) -> int | None:
        raw = self._device.reported.brightness
        if raw is None:
            return None
        return round(raw * 255 / self._brightness_max)

    @property
    def color_temp_kelvin(self) -> int | None:
        raw = self._device.reported.color_temperature
        return int(raw.strip("TK")) if raw else None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        if (
            self._attr_supported_color_modes is None
            or ColorMode.HS not in self._attr_supported_color_modes
        ):
            return None
        reported = self._device.reported
        return enki_to_hs(reported.hue, reported.saturation)

    @property
    def color_mode(self) -> ColorMode | None:
        if self._attr_color_mode is not None:
            return self._attr_color_mode
        reported = self._device.reported
        mode = reported.color_mode
        if mode == "hs":
            return ColorMode.HS
        if mode == "ct":
            return ColorMode.COLOR_TEMP
        if reported.color_temperature:
            return ColorMode.COLOR_TEMP
        if ColorMode.HS in (self._attr_supported_color_modes or set()):
            return ColorMode.HS
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        home_id = self._device.home_id
        node_id = self._device.node_id

        if not self._supports_light_state:
            await self.coordinator.api.async_switch_electrical_power(
                home_id,
                node_id,
                "ON",
                endpoint=self._endpoint_id,
            )
            self._cache_electrical_power("ON")
            return

        if (
            self._endpoint_id is not None
            and self._uses_endpoint_power(self._endpoint_id)
            and self._simple_light_turn_on(kwargs)
            and ATTR_HS_COLOR not in kwargs
        ):
            await self._switch_endpoint_power(self._endpoint_id, "ON")
            return

        if ATTR_HS_COLOR in kwargs:
            hue, saturation = hs_to_enki(*kwargs[ATTR_HS_COLOR])
            await self.coordinator.api.async_change_light_color(home_id, node_id, hue, saturation)
            self.coordinator.update_cached_value(node_id, "hue", hue)
            self.coordinator.update_cached_value(node_id, "saturation", saturation)
            self.coordinator.update_cached_value(node_id, "colorMode", "hs")
            self.coordinator.update_cached_value(node_id, "colorTemperature", None)
            self.coordinator.update_cached_value(node_id, "power", "ON")
            self._update_light_endpoint_cache("ON", self._endpoint_id)
            return

        await self._mixed_endpoint_workaround()
        changes = self._build_turn_on_changes(kwargs)
        if changes.get("power") == "OFF":
            await self.async_turn_off(**kwargs)
            return
        await self.coordinator.api.async_change_light_state(home_id, node_id, changes)
        self.coordinator.update_cached_value(node_id, "power", "ON")
        if "brightness" in changes:
            self.coordinator.update_cached_value(node_id, "brightness", changes["brightness"])
        if "colorTemperature" in changes:
            self.coordinator.update_cached_value(
                node_id,
                "colorTemperature",
                changes["colorTemperature"],
            )
            self.coordinator.update_cached_value(node_id, "colorMode", "ct")
        self._update_light_endpoint_cache("ON", self._endpoint_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        home_id = self._device.home_id
        node_id = self._device.node_id

        if not self._supports_light_state:
            await self.coordinator.api.async_switch_electrical_power(
                home_id,
                node_id,
                "OFF",
                endpoint=self._endpoint_id,
            )
            self._cache_electrical_power("OFF")
            return

        if self._endpoint_id is not None and self._uses_endpoint_power(self._endpoint_id):
            await self._switch_endpoint_power(self._endpoint_id, "OFF")
            return

        await self.coordinator.api.async_change_light_state(
            home_id,
            node_id,
            {"power": "OFF"},
        )
        self.coordinator.update_cached_value(node_id, "power", "OFF")
        self._update_light_endpoint_cache("OFF", self._endpoint_id)

    def _cache_electrical_power(self, power: str) -> None:
        node_id = self._device.node_id
        if self._endpoint_id is not None:
            self.coordinator.update_endpoint_power(node_id, self._endpoint_id, power)
            return
        self.coordinator.update_cached_value(node_id, "electrical_power", power)
        self.coordinator.update_cached_value(node_id, "power", power)
