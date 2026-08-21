"""Device automation triggers for Enki binary sensors.

Exposes native "motion detected", "leak detected", "window opened", … triggers
in the Home Assistant automation editor, so users don't have to hand-write state
triggers. Each trigger is translated to a state trigger on the matching Enki
binary-sensor entity.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

# device_class -> {trigger_type: (from_state, to_state)}
_TRIGGERS_BY_CLASS: dict[BinarySensorDeviceClass, dict[str, tuple[str, str]]] = {
    BinarySensorDeviceClass.MOTION: {
        "motion_detected": (STATE_OFF, STATE_ON),
        "motion_stopped": (STATE_ON, STATE_OFF),
    },
    BinarySensorDeviceClass.OCCUPANCY: {
        "presence_detected": (STATE_OFF, STATE_ON),
        "presence_cleared": (STATE_ON, STATE_OFF),
    },
    BinarySensorDeviceClass.MOISTURE: {
        "leak_detected": (STATE_OFF, STATE_ON),
        "leak_cleared": (STATE_ON, STATE_OFF),
    },
    BinarySensorDeviceClass.WINDOW: {
        "window_opened": (STATE_OFF, STATE_ON),
        "window_closed": (STATE_ON, STATE_OFF),
    },
    BinarySensorDeviceClass.OPENING: {
        "opened": (STATE_OFF, STATE_ON),
        "closed": (STATE_ON, STATE_OFF),
    },
    BinarySensorDeviceClass.VIBRATION: {
        "vibration_detected": (STATE_OFF, STATE_ON),
    },
}

# Flattened trigger_type -> (from_state, to_state); trigger types are unique.
_TRIGGER_STATES: dict[str, tuple[str, str]] = {
    trigger_type: states
    for mapping in _TRIGGERS_BY_CLASS.values()
    for trigger_type, states in mapping.items()
}
TRIGGER_TYPES = frozenset(_TRIGGER_STATES)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id_or_uuid,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, str]]:
    """List the device triggers available for one Enki device."""
    registry = er.async_get(hass)
    triggers: list[dict[str, str]] = []
    for entry in er.async_entries_for_device(registry, device_id, include_disabled_entities=False):
        if entry.domain != BINARY_SENSOR_DOMAIN or entry.platform != DOMAIN:
            continue
        device_class = entry.device_class or entry.original_device_class
        for trigger_type in _TRIGGERS_BY_CLASS.get(device_class, {}):
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DOMAIN: DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_ENTITY_ID: entry.id,
                    CONF_TYPE: trigger_type,
                }
            )
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a device trigger by delegating to the core state trigger."""
    from_state, to_state = _TRIGGER_STATES[config[CONF_TYPE]]
    state_config = {
        CONF_PLATFORM: "state",
        CONF_ENTITY_ID: config[CONF_ENTITY_ID],
        state_trigger.CONF_FROM: from_state,
        state_trigger.CONF_TO: to_state,
    }
    state_config = await state_trigger.async_validate_trigger_config(hass, state_config)
    return await state_trigger.async_attach_trigger(
        hass, state_config, action, trigger_info, platform_type="device"
    )
