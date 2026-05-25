"""Base entity for Enki platforms."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .models import EnkiDevice


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
        return self.coordinator.last_update_success and self._device.is_active

    @callback
    def _handle_coordinator_update(self) -> None:
        updated = self.coordinator.get_device_by_node(self.node_id)
        if updated is not None:
            self._device = updated
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        metadata = self._device.last_reported_value
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.node_id)},
            name=self._device.device_name,
            manufacturer=str(metadata.get("manufacturerId", "Enki")),
            model=str(metadata.get("modelNumber", self._device.device_id))
            .replace("_", " ")
            .title(),
            sw_version=metadata.get("version"),
        )
