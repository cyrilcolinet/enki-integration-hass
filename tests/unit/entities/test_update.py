"""Unit tests for the firmware update entity."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.domain.models import EnkiDevice
from enki.update import EnkiFirmwareUpdate


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "Device",
        "device_type": "sensors",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["ota_inventory"],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _entity(reported: dict) -> EnkiFirmwareUpdate:
    device = _device(last_reported_value=reported)
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = [device]
    coordinator.get_device_by_node = lambda node_id: device
    return EnkiFirmwareUpdate(coordinator, device)


def test_installed_and_latest_from_versions() -> None:
    e = _entity({"firmware_version": "1.2.0", "firmware_latest_version": "1.3.0"})
    assert e.installed_version == "1.2.0"
    assert e.latest_version == "1.3.0"
    assert e._attr_unique_id == "enki-node-1-firmware-update"  # noqa: SLF001


def test_up_to_date_when_no_latest_and_no_flag() -> None:
    e = _entity({"firmware_version": "1.2.0", "firmware_update_available": False})
    assert e.latest_version == "1.2.0"  # equal to installed → up to date


def test_available_without_version_signals_update() -> None:
    e = _entity({"firmware_version": "1.2.0", "firmware_update_available": True})
    # No latest string, but an update exists: latest must differ from installed.
    assert e.latest_version == "unknown"
    assert e.latest_version != e.installed_version
