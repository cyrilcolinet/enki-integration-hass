"""Alarm control panel for the Enki home alarm (api-enki-home-security-prod).

Enki modes map onto Home Assistant's fixed arm states:

- ``DISABLED`` → disarmed
- ``FULL`` ("Total" in the app) → armed away
- ``PARTIAL`` ("Partial") → armed home
- ``PRESENCE`` ("Presence") → armed night

Only the modes the user configured in the app are offered. No code is asked:
the Enki app arms without one, and a code enforced here would only be ours —
restrict access with Home Assistant permissions or an automation instead.
"""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.security import (
    MODE_DISABLED,
    MODE_FULL,
    MODE_INACTIVE,
    MODE_PARTIAL,
    MODE_PRESENCE,
    EnkiSecuritySystem,
)

_MODE_TO_STATE: dict[str, AlarmControlPanelState] = {
    MODE_DISABLED: AlarmControlPanelState.DISARMED,
    MODE_INACTIVE: AlarmControlPanelState.DISARMED,
    MODE_FULL: AlarmControlPanelState.ARMED_AWAY,
    MODE_PARTIAL: AlarmControlPanelState.ARMED_HOME,
    MODE_PRESENCE: AlarmControlPanelState.ARMED_NIGHT,
}

_FEATURE_FOR_MODE: dict[str, AlarmControlPanelEntityFeature] = {
    MODE_FULL: AlarmControlPanelEntityFeature.ARM_AWAY,
    MODE_PARTIAL: AlarmControlPanelEntityFeature.ARM_HOME,
    MODE_PRESENCE: AlarmControlPanelEntityFeature.ARM_NIGHT,
}

# How long an arm/disarm shows as arming/disarming before the cloud state is
# trusted again. The service is eventually consistent (#111), and the alarm has
# an exit delay of its own.
_PENDING_HOLD_SECONDS = 60.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiAlarmPanel(coordinator, system.home_id, system.security_id)
        for system in coordinator.api.security_systems
    )


class EnkiAlarmPanel(CoordinatorEntity[EnkiCoordinator], AlarmControlPanelEntity):
    """One home's Enki alarm."""

    _attr_has_entity_name = True
    _attr_translation_key = "security"
    _attr_code_arm_required = False

    def __init__(self, coordinator: EnkiCoordinator, home_id: str, security_id: str) -> None:
        super().__init__(coordinator)
        self._home_id = home_id
        self._security_id = security_id
        self._attr_unique_id = f"{DOMAIN}-{home_id}-security"
        # (target mode, monotonic expiry) while a command waits for the cloud.
        self._pending: tuple[str, float] | None = None

    def _system(self) -> EnkiSecuritySystem | None:
        for system in self.coordinator.api.security_systems:
            if system.home_id == self._home_id:
                return system
        return None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._home_id}-security")},
            name="Enki alarm",
            manufacturer="Leroy Merlin",
            model="Security",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._system() is not None

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        system = self._system()
        features = AlarmControlPanelEntityFeature(0)
        if system is None:
            return features
        for mode in system.arming_modes:
            features |= _FEATURE_FOR_MODE[mode]
        return features

    def _active_pending(self, system: EnkiSecuritySystem) -> str | None:
        """The mode still being waited for, or None once the cloud caught up."""
        if self._pending is None:
            return None
        target, expires_at = self._pending
        if time.monotonic() >= expires_at or system.current_mode == target:
            return None
        return target

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        system = self._system()
        if system is None:
            return None
        if system.is_triggered:
            return AlarmControlPanelState.TRIGGERED
        target = self._active_pending(system)
        if target is not None:
            if target == MODE_DISABLED:
                return AlarmControlPanelState.DISARMING
            return AlarmControlPanelState.ARMING
        return _MODE_TO_STATE.get(system.current_mode or "")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        system = self._system()
        if system is None:
            return {}
        attributes = {
            "enki_mode": system.current_mode,
            "threat_level": system.threat_level,
            "last_threat_date": system.last_threat_date,
            "alarm_delay": system.alarm_delay,
        }
        return {key: value for key, value in attributes.items() if value is not None}

    @callback
    def _handle_coordinator_update(self) -> None:
        system = self._system()
        if system is not None and self._active_pending(system) is None:
            self._pending = None
        super()._handle_coordinator_update()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._set_mode(MODE_DISABLED)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._set_mode(MODE_FULL)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._set_mode(MODE_PARTIAL)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        await self._set_mode(MODE_PRESENCE)

    async def _set_mode(self, mode: str) -> None:
        system = self._system()
        if system is None:
            raise HomeAssistantError("The Enki alarm is not available")
        if mode != MODE_DISABLED and mode not in system.arming_modes:
            # The app refuses a mode with no detector and siren; so does the API.
            raise HomeAssistantError(f"The Enki alarm has no {mode} mode configured in the app")
        await self.coordinator.api.async_set_security_mode(self._home_id, self._security_id, mode)
        self._pending = (mode, time.monotonic() + _PENDING_HOLD_SECONDS)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
