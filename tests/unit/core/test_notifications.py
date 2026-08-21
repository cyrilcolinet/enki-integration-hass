"""Unit tests for Enki operational repair issues."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from enki.exceptions import EnkiConnectionError
from enki.notifications import EnkiNotifier, notify_for_connection_error


@pytest.fixture
def notifier() -> tuple[MagicMock, EnkiNotifier]:
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test-entry"
    return hass, EnkiNotifier(hass, entry)


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_gateway_rejected_creates_issue(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    hass, n = notifier
    n.notify_gateway_rejected(service="api-enki-lighting-prod")
    assert mock_create.call_args.args[1:] == ("enki", "gateway_test-entry")
    assert mock_create.call_args.kwargs["translation_key"] == "gateway_key_rejected"
    assert (
        mock_create.call_args.kwargs["translation_placeholders"]["service"]
        == "api-enki-lighting-prod"
    )
    # A gateway error supersedes a lingering connection issue.
    mock_delete.assert_called_once_with(hass, "enki", "connection_test-entry")


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_connection_failed_creates_issue(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    n.notify_connection_failed()
    assert mock_create.call_args.args[1:] == ("enki", "connection_test-entry")
    assert mock_create.call_args.kwargs["translation_key"] == "cloud_unreachable"


@patch("enki.notifications.ir.async_delete_issue")
def test_dismiss_operational_errors(
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    hass, n = notifier
    n.dismiss_operational_errors()
    assert mock_delete.call_count == 2
    mock_delete.assert_any_call(hass, "enki", "gateway_test-entry")
    mock_delete.assert_any_call(hass, "enki", "connection_test-entry")


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_connection_error_maps_403_to_gateway(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    notify_for_connection_error(n, EnkiConnectionError("forbidden", status=403))
    assert mock_create.call_args.kwargs["translation_key"] == "gateway_key_rejected"


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_connection_error_maps_other_to_cloud_unreachable(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    notify_for_connection_error(n, EnkiConnectionError("boom", status=500))
    assert mock_create.call_args.kwargs["translation_key"] == "cloud_unreachable"


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_sync_maintenance_shows_issue(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    n.sync_maintenance_mode({"maintenance": True})
    assert mock_create.call_args.kwargs["translation_key"] == "maintenance"
    mock_delete.assert_not_called()


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_sync_maintenance_clears_issue(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    hass, n = notifier
    n.sync_maintenance_mode({"maintenance": False})
    mock_create.assert_not_called()
    mock_delete.assert_called_once_with(hass, "enki", "maintenance_test-entry")


@patch("enki.notifications.ir.async_delete_issue")
@patch("enki.notifications.ir.async_create_issue")
def test_sync_maintenance_skips_when_unavailable(
    mock_create: MagicMock,
    mock_delete: MagicMock,
    notifier: tuple[MagicMock, EnkiNotifier],
) -> None:
    _, n = notifier
    n.sync_maintenance_mode(None)
    mock_create.assert_not_called()
    mock_delete.assert_not_called()
