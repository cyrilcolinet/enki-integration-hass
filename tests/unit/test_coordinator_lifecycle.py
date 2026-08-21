"""Coverage for the Enki coordinator: polling, error routing, optimistic cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.coordinator import (
    EnkiCoordinator,
    _override_apply,
    _override_current,
)
from enki.domain.models import EnkiDevice
from enki.exceptions import EnkiAuthError, EnkiConnectionError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed


def _device(node_id: str = "node", **last_reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id=node_id,
        device_name="Device",
        device_type="ceiling_fans",
        is_enabled=True,
        state="ACTIVE",
        last_reported_value=dict(last_reported),
    )


def _make_coordinator() -> EnkiCoordinator:
    """A fully constructed coordinator (exercises __init__) with stubbed collaborators."""
    hass = MagicMock()
    entry = MagicMock()
    entry.data = {"username": "user@example.com", "password": "secret"}
    entry.options = {}
    coordinator = EnkiCoordinator(hass, entry)
    coordinator.hass = hass
    coordinator.api = MagicMock()
    coordinator.api.discovery_records = []
    coordinator.api.async_get_devices = AsyncMock(return_value=[])
    coordinator.api.async_refresh_scenarios = AsyncMock()
    coordinator.api.async_fetch_mobile_settings = AsyncMock(return_value={})
    coordinator._notifier = MagicMock()
    coordinator._telemetry = MagicMock()
    coordinator._telemetry.async_report = AsyncMock()
    return coordinator


def test_init_wires_api_and_state() -> None:
    coordinator = _make_coordinator()
    assert coordinator.api is not None
    assert coordinator._overrides == {}
    assert coordinator._fan_light_restore == {}


@pytest.mark.asyncio
async def test_update_data_success_returns_devices() -> None:
    coordinator = _make_coordinator()
    device = _device()
    coordinator.data = [device]
    coordinator.api.async_get_devices = AsyncMock(return_value=[device])

    result = await coordinator._async_update_data()

    assert result == [device]
    coordinator._notifier.dismiss_operational_errors.assert_called_once()
    coordinator._telemetry.async_report.assert_awaited_once()
    coordinator.api.async_refresh_scenarios.assert_awaited_once()
    coordinator._notifier.sync_maintenance_mode.assert_called_once()


@pytest.mark.asyncio
async def test_update_data_auth_error_raises_config_entry_auth_failed() -> None:
    coordinator = _make_coordinator()
    coordinator.api.async_get_devices = AsyncMock(side_effect=EnkiAuthError("bad creds"))

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_connection_error_raises_update_failed_and_notifies() -> None:
    coordinator = _make_coordinator()
    coordinator.api.async_get_devices = AsyncMock(side_effect=EnkiConnectionError("down"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_swallows_telemetry_and_scenario_errors() -> None:
    coordinator = _make_coordinator()
    device = _device()
    coordinator.data = [device]
    coordinator.api.async_get_devices = AsyncMock(return_value=[device])
    coordinator._telemetry.async_report = AsyncMock(side_effect=RuntimeError("telemetry boom"))
    coordinator.api.async_refresh_scenarios = AsyncMock(side_effect=RuntimeError("scenarios boom"))

    # Neither optional side task may break the poll.
    result = await coordinator._async_update_data()
    assert result == [device]


@pytest.mark.asyncio
async def test_maintenance_check_swallows_errors() -> None:
    coordinator = _make_coordinator()
    coordinator.api.async_fetch_mobile_settings = AsyncMock(side_effect=RuntimeError("nope"))

    await coordinator._async_sync_maintenance_notification()

    coordinator._notifier.sync_maintenance_mode.assert_not_called()


def test_get_device_by_node_without_data_returns_none() -> None:
    coordinator = _make_coordinator()
    coordinator.data = None
    assert coordinator.get_device_by_node("node") is None


def test_get_device_by_node_finds_and_misses() -> None:
    coordinator = _make_coordinator()
    device = _device()
    coordinator.data = [device]
    assert coordinator.get_device_by_node("node") is device
    assert coordinator.get_device_by_node("other") is None


def test_request_reconcile_schedules_refresh() -> None:
    coordinator = _make_coordinator()
    coordinator.async_request_refresh = MagicMock(return_value="coro")
    coordinator.request_reconcile()
    coordinator.hass.async_create_task.assert_called_once_with("coro")


def test_update_cached_value_noop_when_device_missing() -> None:
    coordinator = _make_coordinator()
    coordinator.data = [_device()]
    coordinator.async_set_updated_data = MagicMock()

    coordinator.update_cached_value("unknown-node", "power", "ON")

    assert coordinator._overrides == {}
    coordinator.async_set_updated_data.assert_not_called()


def test_update_cached_nested_writes_and_records_override() -> None:
    coordinator = _make_coordinator()
    device = _device()
    coordinator.data = [device]
    coordinator.async_set_updated_data = MagicMock()

    coordinator.update_cached_nested("node", "settings", "mode", "AUTO")

    assert device.last_reported_value["settings"] == {"mode": "AUTO"}
    assert ("nested", "settings", "mode") in coordinator._overrides["node"]
    coordinator.async_set_updated_data.assert_called_once()


def test_update_cached_nested_noop_when_device_missing() -> None:
    coordinator = _make_coordinator()
    coordinator.data = [_device()]
    coordinator.update_cached_nested("missing", "settings", "mode", "AUTO")
    assert coordinator._overrides == {}


def test_update_endpoint_power_patches_endpoint_and_records() -> None:
    coordinator = _make_coordinator()
    device = _device(electrical_endpoints=[{"id": 2, "lastReportedValue": "OFF"}])
    coordinator.data = [device]
    coordinator.async_set_updated_data = MagicMock()

    coordinator.update_endpoint_power("node", 2, "ON")

    assert device.last_reported_value["electrical_endpoints"][0]["lastReportedValue"] == "ON"
    assert ("endpoint", 2) in coordinator._overrides["node"]


def test_update_endpoint_power_noop_when_device_missing() -> None:
    coordinator = _make_coordinator()
    coordinator.data = [_device()]
    coordinator.update_endpoint_power("missing", 1, "ON")
    assert coordinator._overrides == {}


def test_remember_and_pop_fan_light_state() -> None:
    coordinator = _make_coordinator()
    coordinator.remember_fan_light_state("node", {1: "ON", 3: "OFF"})
    assert coordinator.pop_fan_light_state("node") == {1: "ON", 3: "OFF"}
    # Popped once, gone afterwards.
    assert coordinator.pop_fan_light_state("node") is None


def test_apply_overrides_drops_node_absent_from_poll() -> None:
    coordinator = _make_coordinator()
    coordinator.data = [_device(light_power="OFF")]
    coordinator.async_set_updated_data = MagicMock()
    coordinator.update_cached_value("node", "light_power", "ON")

    # The device disappears from the fresh poll -> its overrides are dropped.
    result = coordinator._apply_optimistic_overrides([])

    assert result == []
    assert coordinator._overrides == {}


def test_apply_overrides_reapplies_nested_value() -> None:
    coordinator = _make_coordinator()
    device = _device()
    coordinator.data = [device]
    coordinator.async_set_updated_data = MagicMock()
    coordinator.update_cached_nested("node", "settings", "mode", "AUTO")

    fresh = _device(settings={"mode": "ECO"})
    coordinator._apply_optimistic_overrides([fresh])

    assert fresh.last_reported_value["settings"]["mode"] == "AUTO"


# --- module-level override read/apply helpers --------------------------------


def test_override_current_top() -> None:
    device = _device(power="ON")
    assert _override_current(device, ("top", "power")) == "ON"


def test_override_current_nested() -> None:
    device = _device(settings={"mode": "ECO"})
    assert _override_current(device, ("nested", "settings", "mode")) == "ECO"
    # Missing / non-dict parent yields None.
    assert _override_current(_device(), ("nested", "settings", "mode")) is None


def test_override_current_endpoint_dict_and_string() -> None:
    dict_form = _device(electrical_endpoints=[{"id": 3, "lastReportedValue": {"power": "ON"}}])
    assert _override_current(dict_form, ("endpoint", 3)) == "ON"

    string_form = _device(electrical_endpoints=[{"id": 3, "lastReportedValue": "OFF"}])
    assert _override_current(string_form, ("endpoint", 3)) == "OFF"


def test_override_current_endpoint_missing_returns_none() -> None:
    device = _device(electrical_endpoints=[{"id": 1, "lastReportedValue": "ON"}])
    assert _override_current(device, ("endpoint", 9)) is None


def test_override_current_unknown_kind_returns_none() -> None:
    assert _override_current(_device(), ("bogus", "x")) is None


def test_override_apply_top_and_nested() -> None:
    device = _device()
    _override_apply(device, ("top", "power"), "ON")
    assert device.last_reported_value["power"] == "ON"

    _override_apply(device, ("nested", "settings", "mode"), "AUTO")
    assert device.last_reported_value["settings"]["mode"] == "AUTO"


def test_override_apply_endpoint_dict_updates_power_key() -> None:
    device = _device(electrical_endpoints=[{"id": 3, "lastReportedValue": {"power": "OFF"}}])
    _override_apply(device, ("endpoint", 3), "ON")
    assert device.last_reported_value["electrical_endpoints"][0]["lastReportedValue"]["power"] == (
        "ON"
    )


def test_override_apply_endpoint_string_replaces_value() -> None:
    device = _device(electrical_endpoints=[{"id": 3, "lastReportedValue": "OFF"}])
    _override_apply(device, ("endpoint", 3), "ON")
    assert device.last_reported_value["electrical_endpoints"][0]["lastReportedValue"] == "ON"
