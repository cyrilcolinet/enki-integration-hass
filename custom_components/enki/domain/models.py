"""Domain models for Enki devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .capabilities import EnkiCapabilityProfile
    from .state import EnkiDeviceState


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
    bff_device_type: str = ""
    main_change_capability_id: str | None = None
    main_change_capability_endpoints: list[int | dict[str, Any]] = field(default_factory=list)
    power_production: float | None = None

    @property
    def is_active(self) -> bool:
        """Return True when the node is enabled and not deactivated."""
        return self.is_enabled and self.state != "DEACTIVATED"

    @property
    def profile(self) -> EnkiCapabilityProfile:
        """Capability snapshot used for platform selection and API probing."""
        from .capabilities import EnkiCapabilityProfile

        return EnkiCapabilityProfile.from_device(self)

    @property
    def reported(self) -> EnkiDeviceState:
        """Typed accessor for live API fields cached on the coordinator."""
        from .state import EnkiDeviceState

        return EnkiDeviceState(self.last_reported_value)


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


@dataclass(frozen=True, slots=True)
class EnkiScenario:
    """Enki cloud scenario (home-level automation)."""

    home_id: str
    scenario_id: str
    label: str
    enabled: bool = True
    status: str = ""
