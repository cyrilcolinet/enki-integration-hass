"""Data update coordinator for Enki."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EnkiAPI
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .domain.models import EnkiDevice
from .exceptions import EnkiAuthError, EnkiConnectionError
from .notifications import EnkiNotifier, notify_for_connection_error
from .telemetry import EnkiTelemetryReporter


class EnkiCoordinator(DataUpdateCoordinator[list[EnkiDevice]]):
    """Poll Enki cloud and expose device snapshots to platforms."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self.api = EnkiAPI(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        self._notifier = EnkiNotifier(hass, config_entry)
        self._telemetry = EnkiTelemetryReporter(hass, config_entry)
        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> list[EnkiDevice]:
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
            return devices

    def get_device_by_node(self, node_id: str) -> EnkiDevice | None:
        if not self.data:
            return None
        return next((device for device in self.data if device.node_id == node_id), None)

    def update_cached_value(self, node_id: str, key: str, value: Any) -> None:
        """Optimistically patch cached state after a successful command."""
        device = self.get_device_by_node(node_id)
        if device is None or self.data is None:
            return
        device.last_reported_value[key] = value
        self.async_set_updated_data(self.data)

    def update_cached_nested(self, node_id: str, parent_key: str, key: str, value: Any) -> None:
        """Optimistically patch a nested value in cached device state."""
        device = self.get_device_by_node(node_id)
        if device is None or self.data is None:
            return
        parent = device.last_reported_value.setdefault(parent_key, {})
        if isinstance(parent, dict):
            parent[key] = value
        self.async_set_updated_data(self.data)

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
        self.async_set_updated_data(self.data)
