"""Update platform exposing Enki device firmware in Settings → Updates."""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice
from .entity import EnkiEntity

_OTA_CAPABILITY = "ota_inventory"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    async_add_entities(
        EnkiFirmwareUpdate(coordinator, device)
        for device in coordinator.data or []
        if _OTA_CAPABILITY in set(device.capabilities)
    )


class EnkiFirmwareUpdate(EnkiEntity, UpdateEntity):
    """Firmware state from the Enki OTA endpoints (read-only — install via Enki app)."""

    _attr_has_entity_name = True
    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-firmware-update"

    @property
    def installed_version(self) -> str | None:
        return self._device.reported.firmware_version

    @property
    def latest_version(self) -> str | None:
        reported = self._device.reported
        latest = reported.firmware_latest_version
        if latest:
            return latest
        # Enki sometimes reports "an update exists" without a version string;
        # a value distinct from installed keeps HA showing the update as available.
        if reported.firmware_update_available:
            return "unknown"
        return reported.firmware_version
