"""Anonymized Enki device profiles for telemetry and diagnostics."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import quote

from ..const import TELEMETRY_GITHUB_REPO, TELEMETRY_ISSUE_LABELS
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
        "current_temperature",
        "current_humidity",
        "illuminance_level",
        "battery_health",
        "motion_detection",
        "motion_detector_state",
        "vibration_detection",
        "contact_sensor_state",
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
) -> EnkiDiscoveryRecord:
    return EnkiDiscoveryRecord(
        device_type=device_type,
        bff_device_type=bff_device_type,
        capabilities=list(capabilities),
        possible_values=_sanitize_possible_values(possible_values),
        manufacturer=manufacturer,
        model=model,
        firmware_version=firmware_version,
        supported_by_integration=supported_by_integration,
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

    body = (
        "## Enki device profile (opt-in share)\n\n"
        "Anonymized data — no account or home identifiers. "
        "Issue opened manually from Home Assistant.\n\n"
        f"- **Referentiel type:** `{export_dict.get('device_type', 'unknown')}`\n"
        f"- **BFF type:** `{export_dict.get('bff_device_type', '')}`\n"
        f"- **Manufacturer:** {export_dict.get('manufacturer') or 'unknown'}\n"
        f"- **Model:** {export_dict.get('model') or 'unknown'}\n"
        f"- **Firmware:** {export_dict.get('firmware_version') or 'unknown'}\n"
        f"- **Supported by integration:** {supported}\n"
        f"- **Integration version:** `{export_dict.get('integration_version', '')}`\n"
        f"- **Home Assistant:** `{export_dict.get('ha_version', '')}`\n"
        f"- **Fingerprint:** `{fingerprint[:16]}`\n"
    )

    if platforms := export_dict.get("ha_platforms"):
        platform_line = ", ".join(f"`{platform}`" for platform in platforms)
        body += f"- **HA platforms:** {platform_line}\n"

    if reason := export_dict.get("telemetry_reason"):
        reason_text = _TELEMETRY_REASON_LABELS.get(reason, reason)
        body += f"- **Why this report:** {reason_text}\n"

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
    device_type = export_dict.get("device_type", "unknown")
    model = export_dict.get("model") or "unknown"
    if export_dict.get("supported_by_integration"):
        return f"[telemetry] Profile {device_type} — {model}"
    return f"[telemetry] Unsupported device — {device_type} ({model})"


_GITHUB_ISSUE_URL_MAX_LENGTH = 7500


def build_github_new_issue_url(export_dict: dict[str, Any], fingerprint: str) -> str:
    """Build a GitHub new-issue URL with title and body query parameters."""
    title = format_github_issue_title(export_dict)
    labels = ",".join(TELEMETRY_ISSUE_LABELS)
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
