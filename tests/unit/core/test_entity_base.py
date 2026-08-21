"""Unit tests for the shared EnkiEntity base."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.domain.models import EnkiDevice
from enki.entity import EnkiEntity


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "Living room",
        "device_type": "sensors",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _coordinator(device: EnkiDevice | None, *, success: bool = True) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = success
    coordinator.get_device_by_node = lambda node_id: device
    return coordinator


def test_node_id_and_device_accessors() -> None:
    device = _device()
    entity = EnkiEntity(_coordinator(device), device)
    assert entity.node_id == "node-1"
    assert entity.device is device


def test_available_true_when_active_and_polling() -> None:
    device = _device()
    assert EnkiEntity(_coordinator(device), device).available is True


def test_unavailable_when_poll_failed() -> None:
    device = _device()
    assert EnkiEntity(_coordinator(device, success=False), device).available is False


def test_unavailable_when_device_gone() -> None:
    device = _device()
    assert EnkiEntity(_coordinator(None), device).available is False


def test_unavailable_when_deactivated() -> None:
    device = _device(state="DEACTIVATED")
    assert EnkiEntity(_coordinator(device), device).available is False


def test_handle_coordinator_update_refreshes_device() -> None:
    old = _device()
    fresh = _device(device_name="Renamed")
    entity = EnkiEntity(_coordinator(fresh), old)
    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()  # noqa: SLF001
    assert entity.device is fresh
    entity.async_write_ha_state.assert_called_once()


def test_device_info_carries_identity_and_firmware() -> None:
    device = _device(
        last_reported_value={
            "firmware_version": "1.2.3",
            "manufacturerId": "Lexman",
            "modelNumber": "smart_plug",
        }
    )
    info = EnkiEntity(_coordinator(device), device).device_info
    assert info["identifiers"] == {("enki", "node-1")}
    assert info["name"] == "Living room"
    assert info["manufacturer"] == "Lexman"
    assert info["model"] == "Smart Plug"
    assert info["sw_version"] == "1.2.3"
