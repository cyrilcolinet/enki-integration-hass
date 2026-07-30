"""Optimistic-write guard: a stale cloud poll must not revert optimistic state.

The Enki cloud is eventually consistent (~30 s), so a poll inside that window
returns the pre-command value. The coordinator holds optimistic writes
authoritative until the cloud agrees or they expire (issue #111).
"""

from __future__ import annotations

import time

from enki.coordinator import EnkiCoordinator
from enki.domain.models import EnkiDevice


def _device(**last_reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home",
        device_id="dev",
        node_id="node",
        device_name="Cadix",
        device_type="ceiling_fans",
        is_enabled=True,
        state="ACTIVE",
        last_reported_value=dict(last_reported),
    )


def _coordinator(device: EnkiDevice) -> EnkiCoordinator:
    coordinator = object.__new__(EnkiCoordinator)
    coordinator._suspend_notify = False
    coordinator._overrides = {}
    coordinator.data = [device]
    coordinator.async_set_updated_data = lambda data: None
    return coordinator


def test_stale_poll_does_not_revert_optimistic_value() -> None:
    coordinator = _coordinator(_device(light_power="OFF"))
    coordinator.update_cached_value("node", "light_power", "ON")

    # Cloud hasn't propagated yet: a fresh poll still reports OFF.
    fresh = _device(light_power="OFF")
    result = coordinator._apply_optimistic_overrides([fresh])

    assert result[0].last_reported_value["light_power"] == "ON"


def test_override_released_once_cloud_agrees() -> None:
    coordinator = _coordinator(_device(light_power="OFF"))
    coordinator.update_cached_value("node", "light_power", "ON")

    # Cloud catches up → the override is dropped.
    coordinator._apply_optimistic_overrides([_device(light_power="ON")])
    assert coordinator._overrides == {}

    # A later genuine change (e.g. physical off) is now respected, not held.
    later = _device(light_power="OFF")
    coordinator._apply_optimistic_overrides([later])
    assert later.last_reported_value["light_power"] == "OFF"


def test_expired_override_lets_the_cloud_win() -> None:
    coordinator = _coordinator(_device(light_power="OFF"))
    coordinator.update_cached_value("node", "light_power", "ON")
    # Force expiry so a genuinely-failed command can't stick forever.
    coordinator._overrides["node"][("top", "light_power")] = ("ON", time.monotonic() - 1)

    fresh = _device(light_power="OFF")
    coordinator._apply_optimistic_overrides([fresh])

    assert fresh.last_reported_value["light_power"] == "OFF"
    assert coordinator._overrides == {}


def test_endpoint_power_override_held_against_stale_poll() -> None:
    coordinator = _coordinator(
        _device(electrical_endpoints=[{"id": 3, "lastReportedValue": "ON"}])
    )
    coordinator.update_endpoint_power("node", 3, "OFF")

    fresh = _device(electrical_endpoints=[{"id": 3, "lastReportedValue": "ON"}])
    coordinator._apply_optimistic_overrides([fresh])

    assert fresh.last_reported_value["electrical_endpoints"][0]["lastReportedValue"] == "OFF"
