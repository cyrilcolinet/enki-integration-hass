"""Opt-in device profile notifications (pre-filled GitHub issue link)."""

from __future__ import annotations

from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import CONF_TELEMETRY, DOMAIN, LOGGER
from .device_profile import (
    build_github_new_issue_url,
    profile_fingerprint,
    profile_to_export_dict,
)
from .models import EnkiDiscoveryRecord

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
        integration_version = await self._integration_version()
        ha_version = self._hass.config.version

        new_count = 0
        for record in records:
            export_dict = profile_to_export_dict(
                record,
                integration_version=integration_version,
                ha_version=ha_version,
            )
            fingerprint = profile_fingerprint(export_dict)
            if fingerprint in reported:
                continue

            reported.add(fingerprint)
            new_count += 1
            await self._notify_new_profile(export_dict, fingerprint)

        if new_count == 0:
            return

        await self._save_reported(reported)
        LOGGER.info(
            "Notified about %s new Enki device profile(s) (opt-in telemetry)",
            new_count,
        )

    async def _notify_new_profile(self, export_dict: dict[str, Any], fingerprint: str) -> None:
        device_type = export_dict.get("device_type", "unknown")
        model = export_dict.get("model") or "inconnu"
        issue_url = build_github_new_issue_url(export_dict, fingerprint)
        supported = export_dict.get("supported_by_integration")

        if supported:
            title = "Enki — nouveau profil d'appareil"
            message = (
                f"Profil détecté : **{device_type}** ({model}).\n\n"
                "Données anonymisées — rien n'est envoyé sans votre action.\n\n"
                f"[Ouvrir une issue GitHub pré-remplie]({issue_url})"
            )
        else:
            title = "Enki — appareil non supporté"
            message = (
                f"Type **{device_type}** ({model}) n'est pas encore géré par l'intégration.\n\n"
                f"[Proposer le support sur GitHub]({issue_url})"
            )

        await persistent_notification.async_create(
            self._hass,
            message=message,
            title=title,
            notification_id=f"{DOMAIN}_profile_{fingerprint[:16]}",
        )

    async def _load_reported(self) -> set[str]:
        if self._reported is not None:
            return self._reported
        data = await self._store.async_load() or {}
        fingerprints = data.get("fingerprints", [])
        self._reported = {str(item) for item in fingerprints}
        return self._reported

    async def _save_reported(self, reported: set[str]) -> None:
        self._reported = reported
        await self._store.async_save({"fingerprints": sorted(reported)})

    async def _integration_version(self) -> str:
        from . import __version__

        return __version__
