"""Domain models for Enki devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EnkiDevice:
    """A physical node discovered in an Enki home."""

    home_id: str
    device_id: str
    node_id: str
    device_name: str
    device_type: str
    is_enabled: bool
    state: str
    capabilities: list[str] = field(default_factory=list)
    possible_values: dict[str, Any] = field(default_factory=dict)
    last_reported_value: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Return True when the node is enabled and not deactivated."""
        return self.is_enabled and self.state != "DEACTIVATED"


@dataclass(slots=True)
class EnkiDiscoveryRecord:
    """Anonymized discovery snapshot for telemetry (no PII)."""

    device_type: str
    bff_device_type: str
    capabilities: list[str]
    possible_values: dict[str, Any]
    manufacturer: str | None
    model: str | None
    firmware_version: str | None
    supported_by_integration: bool
