"""Anonymized Enki device profiles for telemetry and diagnostics."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import quote

from ..const import TELEMETRY_GITHUB_REPO
from ..lib.fan_endpoints import endpoint_id_from_entry
from ..lib.telemetry_labels import (
    format_telemetry_issue_title,
    resolve_display_value,
    resolve_manufacturer_label,
    resolve_model_label,
    telemetry_github_labels,
)
from .capabilities import device_is_supported
from .models import EnkiDevice, EnkiDiscoveryRecord


def integration_supports_device(device: EnkiDevice) -> bool:
    """Return True when at least one HA platform can represent this node."""
    return device_is_supported(device)


_SENSITIVE_STATE_KEYS = frozenset(
    {
        "homeId",
        "home_id",
        "nodeId",
        "node_id",
        "deviceId",
        "device_id",
        "deviceName",
        "device_name",
        "title",
        "email",
        "username",
    }
)

# Integration state keys safe to export in telemetry (no account/home/node ids).
_POLL_STATE_EXPORT_KEYS = frozenset(
    {
        "fan_speed",
        "airflow_mode",
        "airflow_rotation",
        "airflow_rotation_supported",
        "light_power",
        "power",
        "electrical_power",
        "electrical_consumption",
        "electrical_consumption_unit",
        "brightness",
        "colorTemperature",
        "hue",
        "saturation",
        "colorMode",
        "power_production",
        "shutter_position",
        "shutter_opening",
        "roller_shutter_state",
        "roller_shutter_mode",
        "current_temperature",
        "current_humidity",
        "illuminance_level",
        "battery_health",
        "motion_detection",
        "motion_detector_state",
        "vibration_detection",
        "contact_sensor_state",
        "dry_contact_state",
        "vibration_detection_activation",
        "contact_detection_activation",
        "vibration_sensibility_level",
        "siren_global_state",
        "water_sensor_state",
        "pilot_wire_state",
        "thermostat_target_temperature",
        "thermostat_running_state",
        "window_open_detection",
        "window_open_detection_mode",
        "occupancy",
        "occupancy_mode",
        "presence_detection",
        "camera_last_event_type",
        "camera_last_event_at",
        "camera_last_motion_at",
        "camera_sd_removed",
        "channel1_electrical_power",
        "channel2_electrical_power",
        "firmware_version",
        "firmware_latest_version",
        "firmware_update_available",
        "firmware_update_status",
        "node_connected",
        "version",
        "electrical_endpoints",
    }
)


def _sanitize_endpoint(endpoint: dict[str, Any]) -> dict[str, Any] | None:
    endpoint_id = endpoint.get("id")
    if endpoint_id is None:
        return None
    last_reported = endpoint.get("lastReportedValue")
    if isinstance(last_reported, str):
        return {"id": endpoint_id, "power": last_reported}
    if isinstance(last_reported, dict):
        allowed = {"power", "brightness", "colorTemperature", "hue", "saturation"}
        filtered = {
            key: value
            for key, value in last_reported.items()
            if key in allowed and isinstance(value, (str, int, float))
        }
        if filtered:
            return {"id": endpoint_id, **filtered}
    return {"id": endpoint_id}


def sanitize_poll_state(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Return anonymized last-poll values for diagnostics and GitHub prefill."""
    if not isinstance(raw, dict):
        return {}
    sanitized: dict[str, Any] = {}
    for key in _POLL_STATE_EXPORT_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "electrical_endpoints" and isinstance(value, list):
            endpoints = [_sanitize_endpoint(item) for item in value if isinstance(item, dict)]
            endpoints = [item for item in endpoints if item]
            if endpoints:
                sanitized[key] = endpoints
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
    return sanitized


def _sanitize_possible_values(values: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, dict):
            entry = {k: v for k, v in value.items() if k in {"values", "type", "min", "max"}}
            if entry:
                sanitized[key] = entry
        elif isinstance(value, list):
            sanitized[key] = value
    return sanitized


def build_discovery_record(
    *,
    device_type: str,
    bff_device_type: str,
    capabilities: list[str],
    possible_values: dict[str, Any],
    manufacturer: str | None,
    model: str | None,
    firmware_version: str | None,
    supported_by_integration: bool,
    referentiel_device_id: str | None = None,
    main_change_capability_id: str | None = None,
    main_change_capability_endpoints: list[int | dict[str, Any]] | None = None,
    referentiel_i18n: str | None = None,
) -> EnkiDiscoveryRecord:
    endpoint_ids = {
        endpoint_id
        for entry in main_change_capability_endpoints or []
        if (endpoint_id := endpoint_id_from_entry(entry)) is not None
    }
    return EnkiDiscoveryRecord(
        device_type=device_type,
        bff_device_type=bff_device_type,
        capabilities=list(capabilities),
        possible_values=_sanitize_possible_values(possible_values),
        manufacturer=manufacturer,
        model=model,
        firmware_version=firmware_version,
        supported_by_integration=supported_by_integration,
        referentiel_device_id=referentiel_device_id,
        main_change_capability_id=main_change_capability_id,
        main_change_capability_endpoints=sorted(endpoint_ids),
        referentiel_i18n=referentiel_i18n or None,
    )


def profile_to_export_dict(
    record: EnkiDiscoveryRecord,
    *,
    integration_version: str,
    ha_version: str,
) -> dict[str, Any]:
    return {
        "device_type": record.device_type,
        "bff_device_type": record.bff_device_type,
        "manufacturer": record.manufacturer,
        "model": record.model,
        "firmware_version": record.firmware_version,
        "referentiel_device_id": record.referentiel_device_id,
        "main_change_capability_id": record.main_change_capability_id,
        "main_change_capability_endpoints": list(record.main_change_capability_endpoints),
        "referentiel_i18n": record.referentiel_i18n,
        "supported_by_integration": record.supported_by_integration,
        "capabilities": sorted(record.capabilities or []),
        "possible_values": record.possible_values,
        "integration_version": integration_version,
        "ha_version": ha_version,
    }


def profile_fingerprint(export_dict: dict[str, Any]) -> str:
    """Stable hash for deduplication (excludes integration/HA version)."""
    stable = {
        "device_type": export_dict.get("device_type"),
        "bff_device_type": export_dict.get("bff_device_type"),
        "manufacturer": export_dict.get("manufacturer"),
        "model": export_dict.get("model"),
        "firmware_version": export_dict.get("firmware_version"),
        "supported_by_integration": export_dict.get("supported_by_integration"),
        "capabilities": export_dict.get("capabilities"),
        "possible_values": export_dict.get("possible_values"),
    }
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_github_issue_body(export_dict: dict[str, Any], fingerprint: str) -> str:
    supported = "yes" if export_dict.get("supported_by_integration") else "no"
    capabilities = export_dict.get("capabilities") or []
    possible_values = export_dict.get("possible_values") or {}

    cap_lines = "\n".join(f"- `{capability}`" for capability in capabilities) or "- _(none)_"

    firmware = resolve_display_value(
        export_dict.get("firmware_version"),
        fallback="not reported",
    )
    integration_version = resolve_display_value(export_dict.get("integration_version"))
    ha_version = resolve_display_value(
        export_dict.get("ha_version"),
        fallback="not available",
    )

    body = (
        "## Enki device profile (opt-in share)\n\n"
        "Anonymized data — no account or home identifiers. "
        "Issue opened manually from Home Assistant.\n\n"
        f"- **Referentiel type:** `{resolve_display_value(export_dict.get('device_type'))}`\n"
        f"- **BFF type:** `{resolve_display_value(export_dict.get('bff_device_type'))}`\n"
        f"- **Manufacturer:** {resolve_manufacturer_label(export_dict)}\n"
        f"- **Model:** {resolve_model_label(export_dict)}\n"
        f"- **Firmware:** {firmware}\n"
        f"- **Supported by integration:** {supported}\n"
        f"- **Integration version:** `{integration_version}`\n"
        f"- **Home Assistant:** `{ha_version}`\n"
        f"- **Fingerprint:** `{fingerprint[:16]}`\n"
    )

    if referentiel_device_id := export_dict.get("referentiel_device_id"):
        body += f"- **Referentiel device ID:** `{referentiel_device_id}`\n"

    if main_change := export_dict.get("main_change_capability_id"):
        body += f"- **Main change capability:** `{main_change}`\n"

    if endpoints := export_dict.get("main_change_capability_endpoints"):
        endpoint_line = ", ".join(f"`{endpoint}`" for endpoint in endpoints)
        body += f"- **Main change endpoints:** {endpoint_line}\n"

    if i18n := export_dict.get("referentiel_i18n"):
        body += f"- **Referentiel i18n key:** `{i18n}`\n"

    if platforms := export_dict.get("ha_platforms"):
        platform_line = ", ".join(f"`{platform}`" for platform in platforms)
        body += f"- **HA platforms:** {platform_line}\n"

    if reason := export_dict.get("telemetry_reason"):
        reason_text = _TELEMETRY_REASON_LABELS.get(reason, reason)
        body += f"- **Why this report:** {reason_text}\n"

    suggested_labels = telemetry_github_labels(export_dict)
    if suggested_labels:
        label_list = ", ".join(f"`{label}`" for label in suggested_labels)
        body += f"- **Suggested labels:** {label_list}\n"

    body += (
        "\n### Capabilities\n"
        f"{cap_lines}\n\n"
        "### Possible values\n"
        f"```json\n{json.dumps(possible_values, indent=2, sort_keys=True)}\n```\n"
    )

    if uncovered := export_dict.get("uncovered_capabilities"):
        uncovered_lines = "\n".join(f"- `{capability}`" for capability in uncovered)
        body += f"\n### Uncovered capabilities\n{uncovered_lines}\n"

    if poll_state := export_dict.get("last_poll_state"):
        body += (
            "\n### Last poll state (anonymized)\n"
            f"```json\n{json.dumps(poll_state, indent=2, sort_keys=True)}\n```\n"
        )

    if api_errors := export_dict.get("api_read_errors"):
        error_lines = "\n".join(
            f"- `{endpoint}` → {status}" for endpoint, status in api_errors.items()
        )
        body += (
            "\n### API read errors (last poll)\n"
            f"{error_lines}\n\n"
            "_No node or home identifiers — attach HA diagnostics if more context is needed._\n"
        )

    return body


_TELEMETRY_REASON_LABELS = {
    "api_read_errors": "Cloud API returned errors while reading state",
    "unsupported_device": "Device type not supported by the integration yet",
    "uncovered_capabilities": "Referentiel lists capabilities not implemented yet",
}


def format_github_issue_title(export_dict: dict[str, Any]) -> str:
    return format_telemetry_issue_title(export_dict)


_GITHUB_ISSUE_URL_MAX_LENGTH = 7500


def build_github_new_issue_url(export_dict: dict[str, Any], fingerprint: str) -> str:
    """Build a GitHub new-issue URL with title and body query parameters."""
    title = format_github_issue_title(export_dict)
    labels = ",".join(telemetry_github_labels(export_dict))
    base = f"https://github.com/{TELEMETRY_GITHUB_REPO}/issues/new"

    payload = dict(export_dict)
    body = format_github_issue_body(payload, fingerprint)
    while True:
        url = f"{base}?title={quote(title)}&body={quote(body)}&labels={quote(labels)}"
        if len(url) <= _GITHUB_ISSUE_URL_MAX_LENGTH:
            return url
        if payload.get("possible_values"):
            payload = {**payload, "possible_values": {"_truncated": "see HA diagnostics export"}}
            body = format_github_issue_body(payload, fingerprint)
            continue
        body = body[:4000] + "\n\n_(body truncated — use HA diagnostics export)_\n"
        return f"{base}?title={quote(title)}&body={quote(body)}&labels={quote(labels)}"
