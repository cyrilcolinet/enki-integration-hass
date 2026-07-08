"""Human-readable labels for telemetry exports and GitHub issue prefills."""

from __future__ import annotations

from typing import Any

_MISSING = "—"

_REASON_GITHUB_LABELS: dict[str, str] = {
    "api_read_errors": "api error",
    "uncovered_capabilities": "capability gap",
    "unsupported_device": "unsupported",
}

_DEVICE_FAMILY_GITHUB_LABELS: dict[str, str] = {
    "access_and_motorizations": "motorization",
    "ceiling_fans": "climate",
    "heaters_and_pilot_wires": "climate",
    "inverters": "energy",
    "lights": "lighting",
    "modules": "control",
    "remote_controls_and_switches": "control",
    "sensors": "sensor",
}

_TELEMETRY_BASE_LABEL = "device telemetry"

# Labels synced by scripts/sync_github_labels.sh (base + reason + coarse device family).
TELEMETRY_GITHUB_LABEL_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("device telemetry", "6f42c1", "Opt-in anonymized device profile from Home Assistant"),
    ("unsupported", "d73a4a", "Device type not supported yet (telemetry)"),
    ("capability gap", "fbca04", "Supported device with missing capabilities (telemetry)"),
    ("api error", "b60205", "Cloud API read failures on supported device (telemetry)"),
    ("motorization", "1d76db", "Shutters, covers, and motorizations (telemetry)"),
    ("climate", "b60205", "Heating, pilot wire, ceiling fans (telemetry)"),
    ("lighting", "fef2c0", "Lights and dimmers (telemetry)"),
    ("sensor", "c5def5", "Environment and security sensors (telemetry)"),
    ("control", "0e8a16", "Remotes, switches, outlets, and relays (telemetry)"),
    ("energy", "006b75", "Solar inverters and production (telemetry)"),
)

# Removed from prefill; delete from repo via scripts/sync_github_labels.sh.
TELEMETRY_GITHUB_ORPHAN_LABELS: tuple[str, ...] = (
    "device-telemetry",
    "capability-gap",
    "api-error",
    "telemetry-unsupported",
    "telemetry-capability-gap",
    "telemetry-api-error",
    "telemetry-motorization",
    "telemetry-climate",
    "telemetry-lighting",
    "telemetry-sensor",
    "telemetry-control",
    "telemetry-energy",
    "device-cover",
    "device-remote",
    "device-fan",
    "device-heating",
    "device-light",
    "device-sensor",
    "device-module",
    "device-inverter",
    "brand-lexman",
    "brand-inspire",
    "brand-equation",
    "brand-noirot",
    "brand-eglo",
    "brand-edisio",
    "brand-evology",
    "brand-nodon",
    "brand-sedea",
    "brand-envertech",
    "brand-acova",
)

_DEVICE_TYPE_LABELS: dict[str, str] = {
    "access_and_motorizations": "motorization",
    "ceiling_fans": "ceiling fan",
    "heaters_and_pilot_wires": "heating",
    "inverters": "inverter",
    "lights": "light",
    "modules": "module",
    "remote_controls_and_switches": "remote control",
    "sensors": "sensor",
}

_REASON_TITLE: dict[str, str] = {
    "api_read_errors": "API read errors",
    "uncovered_capabilities": "capability gap",
    "unsupported_device": "unsupported",
}


def humanize_device_type(device_type: str | None) -> str:
    if not device_type:
        return "device"
    normalized = device_type.strip().lower()
    if normalized in _DEVICE_TYPE_LABELS:
        return _DEVICE_TYPE_LABELS[normalized]
    return normalized.replace("_", " ")


def resolve_manufacturer_label(export: dict[str, Any]) -> str:
    manufacturer = export.get("manufacturer")
    if isinstance(manufacturer, str) and manufacturer.strip():
        return manufacturer.strip().title()
    return "Enki"


def resolve_model_label(export: dict[str, Any]) -> str:
    model = export.get("model")
    if (
        isinstance(model, str)
        and model.strip()
        and model.strip().lower()
        not in {
            "unknown",
            "none",
            "n/a",
        }
    ):
        return model.strip()

    referentiel_device_id = export.get("referentiel_device_id")
    if isinstance(referentiel_device_id, str) and referentiel_device_id.strip():
        return f"ref {referentiel_device_id.strip()[:12]}"

    capability_count = len(export.get("capabilities") or [])
    if capability_count:
        return f"{capability_count} capabilities"

    return humanize_device_type(str(export.get("device_type") or "device"))


def resolve_display_value(value: object, *, fallback: str = _MISSING) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"unknown", "none", "n/a"}:
            return fallback
        return stripped
    return str(value)


def telemetry_issue_reason(export: dict[str, Any]) -> str:
    reason_key = export.get("telemetry_reason")
    if isinstance(reason_key, str) and reason_key in _REASON_TITLE:
        return _REASON_TITLE[reason_key]
    if export.get("supported_by_integration"):
        return _REASON_TITLE["uncovered_capabilities"]
    return _REASON_TITLE["unsupported_device"]


def format_telemetry_issue_title(export: dict[str, Any]) -> str:
    manufacturer = resolve_manufacturer_label(export)
    device_kind = humanize_device_type(str(export.get("device_type") or ""))
    detail = resolve_model_label(export)
    reason = telemetry_issue_reason(export)

    if detail == device_kind:
        headline = f"{manufacturer} {device_kind}"
    else:
        headline = f"{manufacturer} {device_kind} · {detail}"

    return f"[telemetry] {headline} — {reason}"


def format_telemetry_notification_summary(export: dict[str, Any]) -> str:
    manufacturer = resolve_manufacturer_label(export)
    device_kind = humanize_device_type(str(export.get("device_type") or ""))
    detail = resolve_model_label(export)
    if detail == device_kind:
        return f"{manufacturer} {device_kind}"
    return f"{manufacturer} {device_kind} · {detail}"


def _device_family_github_label(device_type: object) -> str | None:
    if not isinstance(device_type, str):
        return None
    normalized = device_type.strip().lower()
    return _DEVICE_FAMILY_GITHUB_LABELS.get(normalized)


def telemetry_github_labels(export: dict[str, Any]) -> tuple[str, ...]:
    """GitHub labels to pre-fill on a telemetry issue (labels must exist on the repo)."""
    reason_key = export.get("telemetry_reason")
    if isinstance(reason_key, str) and reason_key in _REASON_GITHUB_LABELS:
        reason_label = _REASON_GITHUB_LABELS[reason_key]
    elif export.get("supported_by_integration"):
        reason_label = _REASON_GITHUB_LABELS["uncovered_capabilities"]
    else:
        reason_label = _REASON_GITHUB_LABELS["unsupported_device"]

    labels: list[str] = [_TELEMETRY_BASE_LABEL, reason_label]
    family_label = _device_family_github_label(export.get("device_type"))
    if family_label is not None:
        labels.append(family_label)
    return tuple(labels)
