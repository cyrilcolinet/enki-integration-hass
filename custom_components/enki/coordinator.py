"""Data update coordinator for Enki."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EnkiAPI
from .const import DOMAIN, LOGGER
from .domain.models import EnkiDevice
from .exceptions import EnkiAuthError, EnkiConnectionError
from .migration import resolve_scan_interval
from .notifications import EnkiNotifier, notify_for_connection_error
from .telemetry import EnkiTelemetryReporter

# How long an optimistic value stays authoritative against the cloud. The Enki
# cloud can take ~30 s to reflect a command, so a poll inside that window still
# returns the pre-command state; holding a bit past that keeps HA from reverting
# an optimistic change before the cloud catches up (issue #111).
_OPTIMISTIC_HOLD_SECONDS = 45.0


def _override_current(device: EnkiDevice, path: tuple) -> Any:
    """Read the value a stored override targets from live device state."""
    reported = device.last_reported_value
    kind = path[0]
    if kind == "top":
        return reported.get(path[1])
    if kind == "nested":
        parent = reported.get(path[1])
        return parent.get(path[2]) if isinstance(parent, dict) else None
    if kind == "endpoint":
        for endpoint in reported.get("electrical_endpoints") or []:
            if isinstance(endpoint, dict) and endpoint.get("id") == path[1]:
                value = endpoint.get("lastReportedValue")
                return value.get("power") if isinstance(value, dict) else value
    return None


def _override_apply(device: EnkiDevice, path: tuple, value: Any) -> None:
    """Re-apply a held optimistic value onto freshly polled device state."""
    reported = device.last_reported_value
    kind = path[0]
    if kind == "top":
        reported[path[1]] = value
    elif kind == "nested":
        parent = reported.setdefault(path[1], {})
        if isinstance(parent, dict):
            parent[path[2]] = value
    elif kind == "endpoint":
        for endpoint in reported.get("electrical_endpoints") or []:
            if isinstance(endpoint, dict) and endpoint.get("id") == path[1]:
                current = endpoint.get("lastReportedValue")
                if isinstance(current, dict):
                    current["power"] = value
                else:
                    endpoint["lastReportedValue"] = value
                break


class EnkiCoordinator(DataUpdateCoordinator[list[EnkiDevice]]):
    """Poll Enki cloud and expose device snapshots to platforms."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._suspend_notify = False
        # node_id -> {path: (optimistic value, monotonic expiry)}. Holds optimistic
        # writes authoritative until the cloud reflects them or they expire (#111).
        self._overrides: dict[str, dict[tuple, tuple[Any, float]]] = {}
        self.api = EnkiAPI(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        self._notifier = EnkiNotifier(hass, config_entry)
        self._telemetry = EnkiTelemetryReporter(hass, config_entry, self)
        scan_interval = resolve_scan_interval(config_entry)
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> list[EnkiDevice]:
        await self._async_sync_maintenance_notification()
        try:
            devices = await self.api.async_get_devices()
        except EnkiAuthError as err:
            self._notifier.notify_auth_failed()
            raise UpdateFailed(f"Authentication error: {err}") from err
        except EnkiConnectionError as err:
            notify_for_connection_error(self._notifier, err)
            raise UpdateFailed(f"Cannot reach Enki cloud: {err}") from err
        else:
            self._notifier.dismiss_operational_errors()
            try:
                await self._telemetry.async_report(self.api.discovery_records)
            except Exception as err:  # noqa: BLE001 — telemetry must never break polling
                LOGGER.warning(
                    "Enki telemetry skipped after discovery error: %s",
                    err,
                    exc_info=LOGGER.isEnabledFor(logging.DEBUG),
                )
            try:
                await self.api.async_refresh_scenarios()
            except Exception as err:  # noqa: BLE001 — scenarios must never break device poll
                LOGGER.debug(
                    "Scenario refresh skipped: %s",
                    err,
                    exc_info=LOGGER.isEnabledFor(logging.DEBUG),
                )
            return self._apply_optimistic_overrides(devices)

    async def _async_sync_maintenance_notification(self) -> None:
        """Re-check Enki maintenance flag each poll; dismiss when it clears."""
        try:
            settings = await self.api.async_fetch_mobile_settings()
        except Exception as err:  # noqa: BLE001 — must not break polling
            LOGGER.debug(
                "Maintenance status check skipped: %s",
                err,
                exc_info=LOGGER.isEnabledFor(logging.DEBUG),
            )
            return
        self._notifier.sync_maintenance_mode(settings)

    def get_device_by_node(self, node_id: str) -> EnkiDevice | None:
        if not self.data:
            return None
        return next((device for device in self.data if device.node_id == node_id), None)

    def request_reconcile(self) -> None:
        """Schedule a debounced re-poll to reconcile firmware-driven side effects.

        Optimistic caching reflects the commanded change instantly, but some
        devices apply coupled changes in firmware that HA cannot predict — e.g.
        the Inspire Cadix forces the ambient ring OFF and the main light ON when
        the fan starts, and restores the ring when it stops (issue #106). This
        pulls the real state shortly after a command instead of waiting for the
        next scheduled poll. HA debounces async_request_refresh, so a burst of
        commands coalesces into a single poll.
        """
        self.hass.async_create_task(self.async_request_refresh())

    def _notify(self) -> None:
        """Push cached state to entities unless a batch is coalescing writes."""
        if self._suspend_notify or self.data is None:
            return
        self.async_set_updated_data(self.data)

    @contextmanager
    def batch_updates(self) -> Iterator[None]:
        """Coalesce optimistic cache writes into a single state refresh.

        Each update_* helper normally notifies HA immediately, so one service
        call can emit several refreshes and re-render every entity on a node
        repeatedly (observed as UI flicker on multi-entity nodes like the
        Inspire Cadix). Within this block intermediate notifications are
        suppressed and a single refresh is emitted on exit.
        """
        previous = self._suspend_notify
        self._suspend_notify = True
        try:
            yield
        finally:
            self._suspend_notify = previous
            if not previous:
                self._notify()

    def _record_override(self, node_id: str, path: tuple, value: Any) -> None:
        self._overrides.setdefault(node_id, {})[path] = (
            value,
            time.monotonic() + _OPTIMISTIC_HOLD_SECONDS,
        )

    def update_cached_value(self, node_id: str, key: str, value: Any) -> None:
        """Optimistically patch cached state after a successful command."""
        device = self.get_device_by_node(node_id)
        if device is None or self.data is None:
            return
        device.last_reported_value[key] = value
        self._record_override(node_id, ("top", key), value)
        self._notify()

    def update_cached_nested(self, node_id: str, parent_key: str, key: str, value: Any) -> None:
        """Optimistically patch a nested value in cached device state."""
        device = self.get_device_by_node(node_id)
        if device is None or self.data is None:
            return
        parent = device.last_reported_value.setdefault(parent_key, {})
        if isinstance(parent, dict):
            parent[key] = value
        self._record_override(node_id, ("nested", parent_key, key), value)
        self._notify()

    def update_endpoint_power(self, node_id: str, endpoint_id: int, power: str) -> None:
        """Optimistically update power for one electricalEndpoints entry."""
        device = self.get_device_by_node(node_id)
        if device is None or self.data is None:
            return
        endpoints = device.last_reported_value.get("electrical_endpoints")
        if isinstance(endpoints, list):
            for endpoint in endpoints:
                if isinstance(endpoint, dict) and endpoint.get("id") == endpoint_id:
                    endpoint["lastReportedValue"] = power
                    break
        self._record_override(node_id, ("endpoint", endpoint_id), power)
        self._notify()

    def _apply_optimistic_overrides(self, devices: list[EnkiDevice]) -> list[EnkiDevice]:
        """Re-apply still-pending optimistic writes over freshly polled state.

        The Enki cloud is eventually consistent: a poll within the propagation
        window returns the pre-command value and would revert an optimistic
        change (issue #111). For each held override, drop it once the cloud
        agrees (or it expires) and otherwise re-apply it so the poll can't
        stomp it.
        """
        now = time.monotonic()
        for node_id in list(self._overrides):
            paths = self._overrides[node_id]
            device = next((item for item in devices if item.node_id == node_id), None)
            if device is None:
                del self._overrides[node_id]
                continue
            for path in list(paths):
                value, expires_at = paths[path]
                if now >= expires_at or _override_current(device, path) == value:
                    del paths[path]
                    continue
                _override_apply(device, path, value)
            if not paths:
                del self._overrides[node_id]
        return devices
