"""Referentiel-driven device metadata reads (firmware, OTA, connectivity)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..const import LOGGER
from ..exceptions import EnkiConnectionError
from .transport import EnkiHttpClient

if TYPE_CHECKING:
    from ..domain.models import EnkiDevice

FIRMWARE_VERSION_CAPABILITY = "check_current_firmware_version"
OTA_INVENTORY_CAPABILITY = "ota_inventory"

_OTA_UPDATE_NEEDED = "OTA_NEEDED"


def merge_ota_version(state: dict[str, Any], payload: dict[str, Any]) -> None:
    """Apply OTA version response (currentVersion / latestVersion)."""
    current = payload.get("currentVersion")
    latest = payload.get("latestVersion")
    if isinstance(current, str) and current:
        state["firmware_version"] = current
        state["version"] = current
    if isinstance(latest, str) and latest:
        state["firmware_latest_version"] = latest
    if isinstance(current, str) and isinstance(latest, str) and current and latest:
        state["firmware_update_available"] = current != latest


def merge_ota_check(state: dict[str, Any], payload: dict[str, Any]) -> None:
    """Apply OTA check response (status enum)."""
    status = payload.get("status")
    if not isinstance(status, str) or not status:
        return
    state["firmware_update_status"] = status
    if status == _OTA_UPDATE_NEEDED:
        state["firmware_update_available"] = True
    elif status == "FIRMWARE_ALREADY_UP_TO_DATE":
        state["firmware_update_available"] = False


def merge_connectivity(state: dict[str, Any], payload: dict[str, Any]) -> None:
    """Apply ESDK / gateway connectivity DTO (connected flag)."""
    connected = payload.get("connected")
    if isinstance(connected, bool):
        state["node_connected"] = connected


def _should_read_firmware_version(capabilities: set[str]) -> bool:
    return FIRMWARE_VERSION_CAPABILITY in capabilities


def _should_read_ota_check(capabilities: set[str]) -> bool:
    return OTA_INVENTORY_CAPABILITY in capabilities


def _should_read_esdk_connectivity(device: EnkiDevice) -> bool:
    return device.profile.is_fan


async def refresh_device_metadata(
    http: EnkiHttpClient,
    device: EnkiDevice,
    state: dict[str, Any],
    *,
    note_error: Any | None = None,
) -> None:
    """Best-effort metadata reads driven by referentiel capabilities and device type.

    Failures are swallowed: missing fields are simply omitted from *state* so
    discovery and entity polling never break.
    """
    try:
        await _refresh_device_metadata_impl(http, device, state, note_error=note_error)
    except Exception as err:  # noqa: BLE001 - metadata must never break discovery
        LOGGER.debug(
            "Device metadata skipped for node %s: %s",
            device.node_id,
            err,
            exc_info=LOGGER.isEnabledFor(logging.DEBUG),
        )


async def _refresh_device_metadata_impl(
    http: EnkiHttpClient,
    device: EnkiDevice,
    state: dict[str, Any],
    *,
    note_error: Any | None = None,
) -> None:
    home_id = device.home_id
    node_id = device.node_id
    caps = set(device.capabilities)

    async def read_firmware_version() -> None:
        if not _should_read_firmware_version(caps):
            return
        try:
            payload = await http.get_ota_version(home_id, node_id)
        except Exception as err:  # noqa: BLE001
            LOGGER.debug("Firmware version skipped for node %s: %s", node_id, err)
            if note_error is not None and isinstance(err, EnkiConnectionError):
                note_error(node_id, service="ota", capability=FIRMWARE_VERSION_CAPABILITY, err=err)
            return
        if payload:
            merge_ota_version(state, payload)

    async def read_ota_check() -> None:
        if not _should_read_ota_check(caps):
            return
        try:
            payload = await http.get_ota_check(home_id, node_id)
        except Exception as err:  # noqa: BLE001
            LOGGER.debug("OTA check skipped for node %s: %s", node_id, err)
            if note_error is not None and isinstance(err, EnkiConnectionError):
                note_error(node_id, service="ota", capability=OTA_INVENTORY_CAPABILITY, err=err)
            return
        if payload:
            merge_ota_check(state, payload)

    async def read_esdk_connectivity() -> None:
        if not _should_read_esdk_connectivity(device):
            return
        try:
            payload = await http.get_esdk_connectivity(home_id, node_id)
        except Exception as err:  # noqa: BLE001
            LOGGER.debug("ESDK connectivity skipped for node %s: %s", node_id, err)
            if note_error is not None and isinstance(err, EnkiConnectionError):
                note_error(node_id, service="esdk", capability="node_connected", err=err)
            return
        if payload:
            merge_connectivity(state, payload)

    results = await asyncio.gather(
        read_firmware_version(),
        read_ota_check(),
        read_esdk_connectivity(),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, Exception):
            LOGGER.debug(
                "Device metadata task failed for node %s: %s",
                node_id,
                result,
            )
