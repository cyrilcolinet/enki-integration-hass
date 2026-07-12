"""Shared lighting behaviour for Enki light entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN

from ...coordinator import EnkiCoordinator
from ...entity import EnkiEntity


class EnkiLightBehaviorMixin:
    """Mixin for entities driving api-enki-lighting-prod.

    Subclasses must inherit :class:`EnkiEntity` so ``coordinator``, ``_device``,
    and ``node_id`` are available.
    """

    _brightness_max: int
    _color_temp_values: list[int]

    def _closest_color_temp(self, target: int) -> str:
        best = min(self._color_temp_values, key=lambda value: abs(value - target))
        return f"T{best}K"

    def _light_endpoint_ids(self: EnkiEntity) -> list[int]:
        profile = self._device.profile
        if profile.is_fan:
            return profile.fan_light_endpoints
        return profile.power_switch_endpoints

    def _uses_endpoint_power(self: EnkiEntity, endpoint_id: int | None) -> bool:
        """True when simple on/off should use per-endpoint power API."""
        if endpoint_id is None:
            return False
        profile = self._device.profile
        if profile.is_fan:
            return False
        if endpoint_id in profile.fan_motor_endpoints:
            return False
        return len(profile.power_switch_endpoints) > 1

    def _simple_light_turn_on(self, kwargs: dict[str, Any]) -> bool:
        return ATTR_BRIGHTNESS not in kwargs and ATTR_COLOR_TEMP_KELVIN not in kwargs

    def _bare_power_fallback_endpoint(self: EnkiEntity, kwargs: dict[str, Any]) -> int | None:
        """Endpoint for a bare on/off via switch_electrical_power, or None.

        Only applies when change_light_state has no real possibleValues
        schema (see EnkiCapabilityProfile.light_state_has_schema) and the
        call carries no brightness/color_temp_kelvin. Honors this entity's
        own endpoint_id first, so a multi-gang fan light (e.g. Siroco+,
        endpoints 2/3) always targets its own circuit rather than falling
        back to the profile's first declared power-switch endpoint.
        """
        if not self._simple_light_turn_on(kwargs):
            return None
        if self._device.profile.light_state_has_schema:
            return None
        if self._endpoint_id is not None:
            return self._endpoint_id
        return self._device.profile.bare_power_fallback_endpoint

    async def _switch_endpoint_power(self: EnkiEntity, endpoint_id: int, power: str) -> None:
        await self.coordinator.api.async_switch_electrical_power(
            self._device.home_id,
            self._device.node_id,
            power,
            endpoint=endpoint_id,
        )
        self.coordinator.update_endpoint_power(self._device.node_id, endpoint_id, power)

    def _light_endpoints_have_mixed_power(self: EnkiEntity) -> bool:
        return self._device.reported.light_endpoints_have_mixed_power(self._light_endpoint_ids())

    async def _mixed_endpoint_workaround(self: EnkiEntity) -> None:
        """Force OFF before ON when multi-light endpoints disagree (Siroco+)."""
        if self._light_endpoints_have_mixed_power():
            await self.coordinator.api.async_change_light_state(
                self._device.home_id,
                self._device.node_id,
                {"power": "OFF"},
            )

    def _build_turn_on_changes(
        self: EnkiEntity,
        kwargs: dict[str, Any],
        *,
        restore_last_brightness: bool = False,
    ) -> dict[str, Any]:
        """Build a single change-light-state payload from HA service kwargs."""
        changes: dict[str, Any] = {"power": "ON"}
        if ATTR_BRIGHTNESS in kwargs:
            ha_brightness = int(kwargs[ATTR_BRIGHTNESS])
            if ha_brightness <= 0:
                return {"power": "OFF"}
            enki_brightness = round(ha_brightness * self._brightness_max / 255, 2)
            min_brightness = self._parse_brightness_min(self._device.profile.possible_values)
            if enki_brightness < min_brightness:
                return {"power": "OFF"}
            changes["brightness"] = enki_brightness
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            if self._color_temp_values:
                changes["colorTemperature"] = self._closest_color_temp(
                    kwargs[ATTR_COLOR_TEMP_KELVIN]
                )
            else:
                changes["colorTemperature"] = f"T{kwargs[ATTR_COLOR_TEMP_KELVIN]}K"
            changes["colorMode"] = "ct"
        elif restore_last_brightness and ATTR_BRIGHTNESS not in kwargs:
            last_brightness = self._device.reported.brightness
            if last_brightness is not None and last_brightness > 0:
                changes["brightness"] = last_brightness
        return changes

    def _cache_global_light_on(self: EnkiEntity, coordinator: EnkiCoordinator) -> None:
        coordinator.update_cached_value(self.node_id, "light_power", "ON")
        coordinator.update_cached_value(self.node_id, "power", "ON")

    def _cache_global_light_off(self: EnkiEntity, coordinator: EnkiCoordinator) -> None:
        coordinator.update_cached_value(self.node_id, "light_power", "OFF")
        coordinator.update_cached_value(self.node_id, "power", "OFF")

    def _update_light_endpoint_cache(
        self: EnkiEntity,
        power: str,
        endpoint_id: int | None = None,
    ) -> None:
        if endpoint_id is not None:
            self.coordinator.update_endpoint_power(self._device.node_id, endpoint_id, power)
            return
        for gang_id in self._light_endpoint_ids():
            self.coordinator.update_endpoint_power(self._device.node_id, gang_id, power)

    @staticmethod
    def _parse_color_temp_values(possible_values: dict[str, Any]) -> list[int]:
        values = possible_values.get("change_color_temperature", {}).get("values", [])
        if not values:
            return []
        return [int(value.strip("TK")) for value in values]

    @staticmethod
    def _parse_brightness_max(possible_values: dict[str, Any], default: int = 100) -> int:
        brightness_range = possible_values.get("change_brightness", {}).get("range", {})
        return int(brightness_range.get("max", default))

    @staticmethod
    def _parse_brightness_min(possible_values: dict[str, Any], *, default: float = 1.0) -> float:
        brightness_range = possible_values.get("change_brightness", {}).get("range", {})
        raw_min = brightness_range.get("min")
        if isinstance(raw_min, (int, float)):
            return float(raw_min)
        return default
