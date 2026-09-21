"""Base entity for Enki platforms."""

from __future__ import annotations

from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.camera_settings import CameraSettingSpec
from .domain.models import EnkiDevice


class EnkiEntity(CoordinatorEntity[EnkiCoordinator]):
    """Shared behaviour for Enki entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator)
        self._device = device

    @property
    def device(self) -> EnkiDevice:
        return self._device

    @property
    def node_id(self) -> str:
        return self._device.node_id

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        if self.coordinator.get_device_by_node(self.node_id) is None:
            return False
        return self._device.is_active

    @callback
    def _handle_coordinator_update(self) -> None:
        updated = self.coordinator.get_device_by_node(self.node_id)
        if updated is not None:
            self._device = updated
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Group entities by physical node (node_id + serial for HA registry)."""
        metadata = self._device.last_reported_value
        firmware = metadata.get("firmware_version") or metadata.get("version")
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.node_id)},
            name=self._device.device_name,
            manufacturer=str(metadata.get("manufacturerId", "Enki")),
            model=str(metadata.get("modelNumber", self._device.device_id))
            .replace("_", " ")
            .title(),
            model_id=self._device.device_id,
            sw_version=str(firmware) if firmware else None,
            serial_number=metadata.get("eui64") or self._device.node_id,
        )


class EnkiCameraSettingEntity(EnkiEntity):
    """One setting of a meari camera: read from its status, written back as-is."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: EnkiCoordinator, device: EnkiDevice, spec: CameraSettingSpec
    ) -> None:
        super().__init__(coordinator, device)
        self._spec = spec
        self._attr_translation_key = spec.translation_key
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-{spec.translation_key}"

    @property
    def _value(self) -> Any:
        return self._device.last_reported_value.get(self._spec.state_key)

    async def _write(self, value: Any) -> None:
        await self.coordinator.api.async_set_camera_setting(
            self._device.home_id, self._device.node_id, self._spec.capability, value
        )
        self.coordinator.update_cached_value(self.node_id, self._spec.state_key, value)
