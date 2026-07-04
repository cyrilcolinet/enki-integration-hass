"""Opt-in device profile notifications (pre-filled GitHub issue link)."""

from __future__ import annotations

from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

STORAGE_VERSION = 1


class EnkiTelemetryReporter:
    """Notify once per new anonymized device profile (manual GitHub issue)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
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
        coordinator = self._entry.runtime_data

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
            )

            # Re-notify when API read errors appear on a profile seen earlier.
            if fingerprint in reported and not (needs_telemetry and api_errors):
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

    def _notify_new_profile(self, export_dict: dict[str, Any], fingerprint: str) -> None:
        device_type = export_dict.get("device_type", "unknown")
        model = export_dict.get("model") or "unknown"
        issue_url = build_github_new_issue_url(export_dict, fingerprint)
        supported = export_dict.get("supported_by_integration")
        title, message = _profile_notification_copy(
            self._hass,
            device_type=str(device_type),
            model=str(model),
            issue_url=issue_url,
            supported=bool(supported),
        )

        persistent_notification.async_create(
            self._hass,
            message=message,
            title=title,
            notification_id=f"{DOMAIN}_profile_{fingerprint[:16]}",
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
    return str(version) if version is not None else "unknown"


def _profile_notification_copy(
    hass: HomeAssistant,
    *,
    device_type: str,
    model: str,
    issue_url: str,
    supported: bool,
) -> tuple[str, str]:
    language = getattr(hass.config, "language", None) or "en"
    if language.startswith("fr"):
        if supported:
            return (
                "Enki — nouveau profil d'appareil",
                (
                    f"Profil détecté : **{device_type}** ({model}).\n\n"
                    "Données anonymisées — rien n'est envoyé sans votre action.\n\n"
                    f"[Ouvrir une issue GitHub pré-remplie]({issue_url})"
                ),
            )
        return (
            "Enki — appareil non supporté",
            (
                f"Type **{device_type}** ({model}) n'est pas encore géré par l'intégration.\n\n"
                f"[Proposer le support sur GitHub]({issue_url})"
            ),
        )

    if supported:
        return (
            "Enki — new device profile",
            (
                f"Profile detected: **{device_type}** ({model}).\n\n"
                "Anonymized data only — nothing is sent without your action.\n\n"
                f"[Open a pre-filled GitHub issue]({issue_url})"
            ),
        )
    return (
        "Enki — unsupported device",
        (
            f"Type **{device_type}** ({model}) is not supported by the integration yet.\n\n"
            f"[Request support on GitHub]({issue_url})"
        ),
    )
