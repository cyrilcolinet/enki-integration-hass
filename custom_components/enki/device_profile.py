"""Anonymized Enki device profiles for telemetry and diagnostics."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import quote

from .const import (
    DEVICE_TYPE_FANS,
    DEVICE_TYPE_LIGHTS,
    TELEMETRY_GITHUB_REPO,
    TELEMETRY_ISSUE_LABELS,
)
from .models import EnkiDiscoveryRecord

SUPPORTED_DEVICE_TYPES = {DEVICE_TYPE_FANS, DEVICE_TYPE_LIGHTS}

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
        "capabilities": sorted(record.capabilities),
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
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_github_issue_body(export_dict: dict[str, Any], fingerprint: str) -> str:
    supported = "oui" if export_dict.get("supported_by_integration") else "non"
    capabilities = export_dict.get("capabilities") or []
    possible_values = export_dict.get("possible_values") or {}

    cap_lines = "\n".join(f"- `{capability}`" for capability in capabilities) or "- _(aucune)_"

    return (
        "## Profil appareil Enki (partage opt-in)\n\n"
        "Données anonymisées — sans identifiant de compte ou de domicile. "
        "Issue ouverte manuellement depuis Home Assistant.\n\n"
        f"- **Type référentiel** : `{export_dict.get('device_type', 'unknown')}`\n"
        f"- **Type BFF** : `{export_dict.get('bff_device_type', '')}`\n"
        f"- **Fabricant** : {export_dict.get('manufacturer') or 'inconnu'}\n"
        f"- **Modèle** : {export_dict.get('model') or 'inconnu'}\n"
        f"- **Firmware** : {export_dict.get('firmware_version') or 'inconnu'}\n"
        f"- **Supporté par l'intégration** : {supported}\n"
        f"- **Version intégration** : `{export_dict.get('integration_version', '')}`\n"
        f"- **Home Assistant** : `{export_dict.get('ha_version', '')}`\n"
        f"- **Empreinte** : `{fingerprint[:16]}`\n\n"
        "### Capabilities\n"
        f"{cap_lines}\n\n"
        "### Possible values\n"
        f"```json\n{json.dumps(possible_values, indent=2, sort_keys=True)}\n```\n"
    )


def format_github_issue_title(export_dict: dict[str, Any]) -> str:
    device_type = export_dict.get("device_type", "unknown")
    model = export_dict.get("model") or "unknown"
    if export_dict.get("supported_by_integration"):
        return f"[telemetry] Profil {device_type} — {model}"
    return f"[telemetry] Appareil non supporté — {device_type} ({model})"


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
