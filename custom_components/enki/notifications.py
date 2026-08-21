"""Repairs issues for Enki operational problems.

Uses Home Assistant's issue registry (Settings → Repairs) rather than
hardcoded bilingual persistent notifications: the copy lives in the translation
files (``strings.json`` / ``translations``) under ``issues`` and HA renders it in
the user's language. Authentication failures are handled by the reauth flow
(``ConfigEntryAuthFailed``), not here.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .exceptions import EnkiConnectionError

_DOCUMENTATION_URL = "https://github.com/cyrilcolinet/enki-integration-hass"


def notify_for_connection_error(notifier: EnkiNotifier, err: EnkiConnectionError) -> None:
    """Map an API transport error to the appropriate repair issue."""
    if err.status == 403:
        notifier.notify_gateway_rejected(service=err.service)
    else:
        notifier.notify_connection_failed()


class EnkiNotifier:
    """Create or clear Enki repair issues for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry

    def notify_gateway_rejected(self, *, service: str | None = None) -> None:
        """HTTP 403 — a gateway API key is likely outdated after an app update."""
        self._delete("connection")
        self._create(
            "gateway",
            translation_key="gateway_key_rejected",
            placeholders={"service": service or "?"},
            learn_more_url=f"{_DOCUMENTATION_URL}/blob/main/docs/DEVELOPMENT.md",
        )

    def notify_connection_failed(self) -> None:
        """Network error or unexpected upstream failure."""
        self._delete("gateway")
        self._create("connection", translation_key="cloud_unreachable")

    def notify_service_unavailable(self) -> None:
        """Enki cloud temporarily unavailable (5xx)."""
        self.notify_connection_failed()

    def notify_maintenance_mode(self) -> None:
        """Enki cloud reports active maintenance."""
        self._create(
            "maintenance",
            translation_key="maintenance",
            learn_more_url="https://support.enki-home.com/",
        )

    def dismiss_maintenance_mode(self) -> None:
        """Clear the maintenance issue when Enki reports normal operations."""
        self._delete("maintenance")

    def sync_maintenance_mode(self, settings: dict[str, Any] | None) -> None:
        """Show or hide the maintenance issue from a mobile-config payload."""
        if settings is None:
            return
        if settings.get("maintenance") is True:
            self.notify_maintenance_mode()
        else:
            self.dismiss_maintenance_mode()

    def dismiss_operational_errors(self) -> None:
        """Clear gateway / connection issues after a successful poll."""
        self._delete("gateway")
        self._delete("connection")

    def dismiss_all(self) -> None:
        """Clear every operational issue for this entry (e.g. on unload)."""
        self.dismiss_operational_errors()
        self._delete("maintenance")

    def _issue_id(self, suffix: str) -> str:
        return f"{suffix}_{self._entry.entry_id}"

    def _create(
        self,
        suffix: str,
        *,
        translation_key: str,
        placeholders: dict[str, str] | None = None,
        learn_more_url: str | None = None,
    ) -> None:
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            self._issue_id(suffix),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders=placeholders,
            learn_more_url=learn_more_url,
        )

    def _delete(self, suffix: str) -> None:
        ir.async_delete_issue(self._hass, DOMAIN, self._issue_id(suffix))
