"""Persistent notifications for Enki operational issues."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .exceptions import EnkiConnectionError

_DOCUMENTATION_URL = "https://github.com/cyrilcolinet/enki-integration-hass"
_ISSUE_TRACKER = f"{_DOCUMENTATION_URL}/issues"


def notify_for_connection_error(notifier: EnkiNotifier, err: EnkiConnectionError) -> None:
    """Map an API transport error to the appropriate persistent notification."""
    status = err.status
    if status == 403:
        notifier.notify_gateway_rejected()
    elif status == 401:
        notifier.notify_auth_failed(gateway_hint=True)
    elif status in {502, 503, 504}:
        notifier.notify_service_unavailable()
    else:
        notifier.notify_connection_failed()


class EnkiNotifier:
    """Show or dismiss Enki persistent notifications for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry

    def notify_auth_failed(self, *, gateway_hint: bool = False) -> None:
        """Credentials rejected by Enki / Keycloak."""
        self._dismiss(self._id("connection"))
        self._dismiss(self._id("gateway"))
        title, message = _auth_copy(self._hass, self._entry.entry_id, gateway_hint=gateway_hint)
        self._create(self._id("auth"), title, message)

    def notify_gateway_rejected(self) -> None:
        """HTTP 403 — gateway API key likely outdated."""
        self._dismiss(self._id("connection"))
        title, message = _gateway_copy(self._hass)
        self._create(self._id("gateway"), title, message)

    def notify_connection_failed(self) -> None:
        """Network error or unexpected upstream failure."""
        self._dismiss(self._id("auth"))
        self._dismiss(self._id("gateway"))
        title, message = _connection_copy(self._hass)
        self._create(self._id("connection"), title, message)

    def notify_service_unavailable(self) -> None:
        """Enki cloud temporarily unavailable (5xx)."""
        self.notify_connection_failed()

    def dismiss_operational_errors(self) -> None:
        """Clear auth / gateway / connection notifications after a successful poll."""
        for suffix in ("auth", "gateway", "connection"):
            self._dismiss(self._id(suffix))

    def dismiss_all(self) -> None:
        """Clear every operational notification for this entry (e.g. on unload)."""
        self.dismiss_operational_errors()

    def _id(self, suffix: str) -> str:
        return f"{DOMAIN}_{suffix}_{self._entry.entry_id}"

    def _create(self, notification_id: str, title: str, message: str) -> None:
        persistent_notification.async_create(
            self._hass,
            message=message,
            title=title,
            notification_id=notification_id,
        )

    def _dismiss(self, notification_id: str) -> None:
        persistent_notification.async_dismiss(self._hass, notification_id)


def _configure_url(entry_id: str) -> str:
    return f"/config/integrations/configure/{entry_id}"


def _auth_copy(
    hass: HomeAssistant,
    entry_id: str,
    *,
    gateway_hint: bool,
) -> tuple[str, str]:
    configure_url = _configure_url(entry_id)
    if hass.config.language.startswith("fr"):
        title = "Enki — connexion refusée"
        if gateway_hint:
            body = (
                "L'API Enki a rejeté la requête (HTTP 401). "
                "Vérifiez votre **email et mot de passe** Enki, ou mettez à jour les clés "
                "gateway si l'app mobile a changé de version.\n\n"
                f"[Reconfigurer Enki]({configure_url}) · "
                f"[Documentation]({_DOCUMENTATION_URL})"
            )
        else:
            body = (
                "Identifiants Enki invalides ou session expirée. "
                "Utilisez le même **email et mot de passe** que l'application mobile "
                "Leroy Merlin Enki.\n\n"
                f"[Reconfigurer Enki]({configure_url})"
            )
        return title, body

    title = "Enki — sign-in failed"
    if gateway_hint:
        body = (
            "The Enki API rejected the request (HTTP 401). Check your **email and password**, "
            "or update gateway API keys if the mobile app was recently upgraded.\n\n"
            f"[Reconfigure Enki]({configure_url}) · "
            f"[Documentation]({_DOCUMENTATION_URL})"
        )
    else:
        body = (
            "Invalid Enki credentials or expired session. Use the same **email and password** "
            "as the Leroy Merlin Enki mobile app.\n\n"
            f"[Reconfigure Enki]({configure_url})"
        )
    return title, body


def _gateway_copy(hass: HomeAssistant) -> tuple[str, str]:
    if hass.config.language.startswith("fr"):
        return (
            "Enki — clé API gateway refusée",
            (
                "L'API Enki a répondu **HTTP 403** : une clé gateway (micro-service) "
                "est probablement obsolète. Cela arrive quand l'application Enki est "
                "mise à jour.\n\n"
                "Mettez à jour les clés via `scripts/extract_gateway_keys.py` ou consultez "
                f"[la documentation]({_DOCUMENTATION_URL}).\n\n"
                f"[Signaler un problème]({_ISSUE_TRACKER})"
            ),
        )
    return (
        "Enki — gateway API key rejected",
        (
            "The Enki API returned **HTTP 403**: a gateway (micro-service) API key is likely "
            "outdated. This often happens after an Enki app update.\n\n"
            "Refresh keys with `scripts/extract_gateway_keys.py` or see "
            f"[the documentation]({_DOCUMENTATION_URL}).\n\n"
            f"[Report an issue]({_ISSUE_TRACKER})"
        ),
    )


def _connection_copy(hass: HomeAssistant) -> tuple[str, str]:
    if hass.config.language.startswith("fr"):
        return (
            "Enki — cloud inaccessible",
            (
                "Impossible de joindre le cloud Enki (réseau, timeout ou erreur serveur). "
                "Les entités ne seront pas mises à jour tant que la connexion "
                "n'est pas rétablie.\n\n"
                "Vérifiez votre connexion Internet et les logs Home Assistant (`enki`)."
            ),
        )
    return (
        "Enki — cloud unreachable",
        (
            "Cannot reach the Enki cloud (network, timeout, or server error). "
            "Entities will not update until connectivity is restored.\n\n"
            "Check your Internet connection and Home Assistant logs (`enki`)."
        ),
    )
