"""Enki home alarm (api-enki-home-security-prod).

The alarm is not a physical node: the dashboard shows it as a tile with
``template == "SECURITY"`` whose metadata carries a ``securityId`` instead of a
device id — which is why node discovery never saw it. State and arming go
through the home-security service:

- ``GET security?homeId=`` → current mode, threat level, delay, notifications
- ``GET modes?homeId=`` → the modes configured for the home, by ``type``
- ``PATCH security/{securityId}/homes/{homeId}/currentMode`` ``{"currentMode": …}``

Mode and threat values are the app's own enums (APK 2.26.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SECURITY_TILE_TEMPLATE = "SECURITY"

MODE_DISABLED = "DISABLED"
MODE_FULL = "FULL"
MODE_PARTIAL = "PARTIAL"
MODE_PRESENCE = "PRESENCE"
# Listed by the app but never offered as a choice (no label): not a user mode.
MODE_INACTIVE = "INACTIVE"

# A mode is only selectable once configured in the app — the app refuses to save
# one without at least a detector and a siren — so GET modes decides what to offer.
ARMING_MODES = frozenset({MODE_FULL, MODE_PARTIAL, MODE_PRESENCE})

# Threat levels that mean the alarm went off. DETERRENCE (pre-alarm warning),
# AUTO_PROTECTION and ALERT stay out until a real trace shows what they mean in
# practice: a false "triggered" hurts as much as a missed one. The raw level is
# exposed as an attribute either way.
TRIGGERED_THREAT_LEVELS = frozenset({"INTRUSION", "INTRUSION_CONFIRMED", "DANGER"})


@dataclass(frozen=True, slots=True)
class EnkiSecuritySystem:
    """One home's alarm: its current mode and what it can be armed to."""

    home_id: str
    security_id: str
    current_mode: str | None
    threat_level: str | None
    last_threat_date: str | None
    alarm_delay: int | None
    notifications_enabled: bool | None
    configured_modes: frozenset[str]

    @property
    def is_triggered(self) -> bool:
        return (self.threat_level or "").upper() in TRIGGERED_THREAT_LEVELS

    @property
    def arming_modes(self) -> frozenset[str]:
        """Arming modes the user configured in the app, and only those."""
        return self.configured_modes & ARMING_MODES


def security_id_from_tile(item: dict[str, Any]) -> str | None:
    """The alarm id carried by a dashboard SECURITY tile, else None."""
    if not isinstance(item, dict) or item.get("template") != SECURITY_TILE_TEMPLATE:
        return None
    metadata = item.get("metadata")
    security_id = metadata.get("securityId") if isinstance(metadata, dict) else None
    return security_id if isinstance(security_id, str) and security_id else None


def parse_configured_modes(payload: dict[str, Any]) -> frozenset[str]:
    """Mode types from GET modes (``{"items": [{"type": …}, …]}``)."""
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return frozenset()
    return frozenset(
        item["type"].upper()
        for item in items
        if isinstance(item, dict) and isinstance(item.get("type"), str)
    )


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def parse_security_state(
    payload: dict[str, Any],
    *,
    home_id: str,
    security_id: str,
    configured_modes: frozenset[str],
) -> EnkiSecuritySystem | None:
    """Build the alarm snapshot from GET security, or None if nothing came back."""
    if not isinstance(payload, dict) or not payload:
        return None
    mode = _as_str(payload.get("currentMode"))
    notifications = payload.get("notificationsEnabled")
    return EnkiSecuritySystem(
        home_id=home_id,
        security_id=security_id,
        current_mode=mode.upper() if mode else None,
        threat_level=_as_str(payload.get("threatLevel")),
        last_threat_date=_as_str(payload.get("lastThreatDate")),
        alarm_delay=_as_int(payload.get("alarmDelay")),
        notifications_enabled=notifications if isinstance(notifications, bool) else None,
        configured_modes=configured_modes,
    )
