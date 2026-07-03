"""Unit tests for Enki operational notifications."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from enki.exceptions import EnkiConnectionError
from enki.notifications import EnkiNotifier, notify_for_connection_error


@pytest.fixture
def notifier() -> tuple[MagicMock, EnkiNotifier]:
    hass = MagicMock()
    hass.config.language = "en"
    entry = MagicMock()
    entry.entry_id = "test-entry"
    return hass, EnkiNotifier(hass, entry)


@patch("enki.notifications.persistent_notification.async_create")
def test_notify_auth_failed(
    mock_create: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    hass, n = notifier
    n.notify_auth_failed()
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["notification_id"] == "enki_auth_test-entry"
    assert "sign-in failed" in mock_create.call_args.kwargs["title"].lower()
    assert "/config/integrations/configure/test-entry" in mock_create.call_args.kwargs["message"]


@patch("enki.notifications.persistent_notification.async_dismiss")
@patch("enki.notifications.persistent_notification.async_create")
def test_notify_gateway_rejected(
    mock_create: MagicMock,
    mock_dismiss: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    n.notify_gateway_rejected()
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["notification_id"] == "enki_gateway_test-entry"
    assert "403" in mock_create.call_args.kwargs["message"]
    mock_dismiss.assert_called_once_with(n._hass, "enki_connection_test-entry")


@patch("enki.notifications.persistent_notification.async_dismiss")
@patch("enki.notifications.persistent_notification.async_create")
def test_notify_connection_failed(
    mock_create: MagicMock,
    mock_dismiss: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    n.notify_connection_failed()
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["notification_id"] == "enki_connection_test-entry"
    assert mock_dismiss.call_count == 2


@patch("enki.notifications.persistent_notification.async_dismiss")
def test_dismiss_operational_errors(
    mock_dismiss: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    hass, n = notifier
    n.dismiss_operational_errors()
    assert mock_dismiss.call_count == 3
    mock_dismiss.assert_any_call(hass, "enki_auth_test-entry")
    mock_dismiss.assert_any_call(hass, "enki_gateway_test-entry")
    mock_dismiss.assert_any_call(hass, "enki_connection_test-entry")


@patch("enki.notifications.persistent_notification.async_create")
def test_notify_for_connection_error_maps_403(
    mock_create: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    notify_for_connection_error(n, EnkiConnectionError("forbidden", status=403))
    assert mock_create.call_args.kwargs["notification_id"] == "enki_gateway_test-entry"


@patch("enki.notifications.persistent_notification.async_create")
def test_french_auth_copy(mock_create: MagicMock) -> None:
    hass = MagicMock()
    hass.config.language = "fr-FR"
    entry = MagicMock()
    entry.entry_id = "abc"
    EnkiNotifier(hass, entry).notify_auth_failed()
    assert "connexion refusée" in mock_create.call_args.kwargs["title"].lower()
