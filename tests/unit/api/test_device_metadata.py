"""Unit tests for device metadata reads (firmware, OTA, connectivity)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.device_metadata import (
    merge_connectivity,
    merge_ota_check,
    merge_ota_version,
    refresh_device_metadata,
)
from enki.domain.models import EnkiDevice


def _device(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "AD_TCFL_1",
        "node_id": "node-1",
        "device_name": "Ventilateur",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "check_current_firmware_version",
            "ota_inventory",
            "change_fan_speed",
        ],
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_merge_ota_version_sets_firmware_and_update_flag() -> None:
    state: dict = {}
    merge_ota_version(
        state,
        {
            "nodeId": "node-1",
            "currentVersion": "2.21.0",
            "latestVersion": "2.22.0",
        },
    )
    assert state["firmware_version"] == "2.21.0"
    assert state["version"] == "2.21.0"
    assert state["firmware_latest_version"] == "2.22.0"
    assert state["firmware_update_available"] is True


def test_merge_ota_version_up_to_date() -> None:
    state: dict = {}
    merge_ota_version(
        state,
        {
            "currentVersion": "2.21.0",
            "latestVersion": "2.21.0",
        },
    )
    assert state["firmware_update_available"] is False


def test_merge_ota_check_needed() -> None:
    state: dict = {}
    merge_ota_check(state, {"status": "OTA_NEEDED"})
    assert state["firmware_update_status"] == "OTA_NEEDED"
    assert state["firmware_update_available"] is True


def test_merge_ota_check_up_to_date() -> None:
    state: dict = {}
    merge_ota_check(state, {"status": "FIRMWARE_ALREADY_UP_TO_DATE"})
    assert state["firmware_update_available"] is False


def test_merge_connectivity() -> None:
    state: dict = {}
    merge_connectivity(state, {"connected": True})
    assert state["node_connected"] is True


@pytest.mark.asyncio
async def test_refresh_device_metadata_fan_calls_ota_and_esdk() -> None:
    http = MagicMock()
    http.get_ota_version = AsyncMock(
        return_value={"currentVersion": "1.0.0", "latestVersion": "1.0.0"},
    )
    http.get_ota_check = AsyncMock(return_value={"status": "FIRMWARE_ALREADY_UP_TO_DATE"})
    http.get_esdk_connectivity = AsyncMock(return_value={"connected": True})

    state: dict = {}
    await refresh_device_metadata(http, _device(), state)

    http.get_ota_version.assert_awaited_once_with("home-1", "node-1")
    http.get_ota_check.assert_awaited_once_with("home-1", "node-1")
    http.get_esdk_connectivity.assert_awaited_once_with("home-1", "node-1")
    assert state["firmware_version"] == "1.0.0"
    assert state["node_connected"] is True


@pytest.mark.asyncio
async def test_refresh_device_metadata_swallows_unexpected_errors() -> None:
    http = MagicMock()
    http.get_ota_version = AsyncMock(side_effect=RuntimeError("boom"))
    http.get_ota_check = AsyncMock(return_value={"status": "FIRMWARE_ALREADY_UP_TO_DATE"})
    http.get_esdk_connectivity = AsyncMock(return_value={"connected": True})

    state: dict = {}
    await refresh_device_metadata(http, _device(), state)

    assert "firmware_version" not in state
    assert state.get("firmware_update_available") is False
    assert state.get("node_connected") is True


@pytest.mark.asyncio
async def test_refresh_device_metadata_skips_without_capabilities() -> None:
    http = MagicMock()
    http.get_ota_version = AsyncMock()
    http.get_ota_check = AsyncMock()
    http.get_esdk_connectivity = AsyncMock()

    device = _device(
        device_type="lights",
        capabilities=["change_light_state"],
    )
    await refresh_device_metadata(http, device, {})

    http.get_ota_version.assert_not_called()
    http.get_ota_check.assert_not_called()
    http.get_esdk_connectivity.assert_not_called()
