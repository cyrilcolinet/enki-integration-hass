"""Opt-in device profile notifications (pre-filled GitHub issue link)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from ..const import CONF_TELEMETRY, DOMAIN, LOGGER
from ..domain.models import EnkiDiscoveryRecord
from ..domain.profile import (
    build_github_new_issue_url,
    profile_fingerprint,
    profile_to_export_dict,
)
from ..domain.telemetry_coverage import discovery_record_needs_telemetry
from ..domain.telemetry_enrichment import enrich_telemetry_export
from ..lib.telemetry_labels import format_telemetry_notification_summary

if TYPE_CHECKING:
    from ..coordinator import EnkiCoordinator

STORAGE_VERSION = 1


class EnkiTelemetryReporter:
    """Notify once per new anonymized device profile (manual GitHub issue)."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: EnkiCoordinator,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.telemetry.{entry.entry_id}",
        )
        self._reported: set[str] | None = None

    async def async_report(self, records: list[EnkiDiscoveryRecord]) -> None:
        if not self._entry.options.get(CONF_TELEMETRY, False):
            return
        if not records:
            return

        reported = await self._load_reported()
        integration_version = _integration_version()
        ha_version = _ha_version(self._hass)
        coordinator = self._coordinator

        new_count = 0
        for record in records:
            try:
                export_dict = profile_to_export_dict(
                    record,
                    integration_version=integration_version,
                    ha_version=ha_version,
                )
                fingerprint = profile_fingerprint(export_dict)
                api_errors = coordinator.api.read_errors_for_fingerprint(fingerprint)
                poll_state = coordinator.api.poll_state_for_fingerprint(fingerprint)
                export_dict = enrich_telemetry_export(
                    export_dict,
                    record,
                    api_read_errors=api_errors or None,
                    last_poll_state=poll_state or None,
                )
            except (TypeError, ValueError) as err:
                LOGGER.warning(
                    "Skipping telemetry for profile %s: %s",
                    getattr(record, "device_type", "unknown"),
                    err,
                )
                continue

            needs_telemetry = discovery_record_needs_telemetry(
                record,
                api_read_errors=api_errors,
                poll_state=poll_state,
            )

            if fingerprint in reported:
                if not needs_telemetry:
                    self._dismiss_profile_notification(fingerprint)
                continue

            if fingerprint not in reported:
                reported.add(fingerprint)
                await self._save_reported(reported)

            if not needs_telemetry:
                continue

            new_count += 1
            self._notify_new_profile(export_dict, fingerprint)

        if new_count == 0:
            return

        LOGGER.info(
            "Notified about %s new Enki device profile(s) (opt-in telemetry)",
            new_count,
        )

    def _dismiss_profile_notification(self, fingerprint: str) -> None:
        ir.async_delete_issue(
            self._hass,
            DOMAIN,
            f"profile_{fingerprint[:16]}",
        )

    def _notify_new_profile(self, export_dict: dict[str, Any], fingerprint: str) -> None:
        summary = format_telemetry_notification_summary(export_dict)
        issue_url = build_github_new_issue_url(export_dict, fingerprint)
        supported = bool(export_dict.get("supported_by_integration"))
        translation_key = "new_device_profile" if supported else "unsupported_device"

        ir.async_create_issue(
            self._hass,
            DOMAIN,
            f"profile_{fingerprint[:16]}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders={"summary": summary},
            learn_more_url=issue_url,
        )

    async def _load_reported(self) -> set[str]:
        if self._reported is not None:
            return self._reported
        data = await self._store.async_load() or {}
        fingerprints = data.get("fingerprints") or []
        if not isinstance(fingerprints, list):
            fingerprints = []
        self._reported = {str(item) for item in fingerprints if item}
        return self._reported

    async def _save_reported(self, reported: set[str]) -> None:
        self._reported = reported
        await self._store.async_save({"fingerprints": sorted(reported)})


def _integration_version() -> str:
    from .. import __version__

    return __version__


def _ha_version(hass: HomeAssistant) -> str:
    version = getattr(hass.config, "version", None)
    if version:
        return str(version)
    try:
        from homeassistant.const import __version__

        return str(__version__)
    except ImportError:
        return "not available"
