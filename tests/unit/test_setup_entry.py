"""Setup must close the API session whenever the config entry fails to start."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import enki
import pytest
from enki.exceptions import EnkiAuthError, EnkiConnectionError
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady


def _make_coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.api.async_connect = AsyncMock()
    coordinator.api.async_close = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    return coordinator


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    return hass


@contextmanager
def _patched_dependencies(coordinator: MagicMock):
    with (
        patch("enki.coordinator.EnkiCoordinator", return_value=coordinator),
        patch("enki.EnkiNotifier"),
        patch("enki.notify_for_connection_error"),
        patch("enki.telemetry.async_handle_telemetry_nudge", new=AsyncMock()),
    ):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (EnkiAuthError("bad credentials"), ConfigEntryAuthFailed),
        (EnkiConnectionError("cloud down"), ConfigEntryNotReady),
    ],
)
async def test_whenConnectFails_thenApiSessionIsClosed(
    error: Exception,
    expected: type[Exception],
) -> None:
    # Given
    coordinator = _make_coordinator()
    coordinator.api.async_connect.side_effect = error

    # When: an auth error triggers reauth, a connection error a retry
    with _patched_dependencies(coordinator), pytest.raises(expected):
        await enki.async_setup_entry(_make_hass(), MagicMock())

    # Then
    coordinator.api.async_close.assert_awaited_once()


@pytest.mark.asyncio
async def test_whenFirstRefreshFails_thenApiSessionIsClosed() -> None:
    # Given
    coordinator = _make_coordinator()
    coordinator.async_config_entry_first_refresh.side_effect = ConfigEntryNotReady("no data")

    # When
    with _patched_dependencies(coordinator), pytest.raises(ConfigEntryNotReady):
        await enki.async_setup_entry(_make_hass(), MagicMock())

    # Then
    coordinator.api.async_close.assert_awaited_once()


@pytest.mark.asyncio
async def test_whenSetupSucceeds_thenSessionStaysOpenAndPlatformsLoad() -> None:
    # Given
    coordinator = _make_coordinator()
    hass = _make_hass()

    # When
    with _patched_dependencies(coordinator):
        result = await enki.async_setup_entry(hass, MagicMock())

    # Then
    assert result is True
    coordinator.api.async_close.assert_not_awaited()
    hass.config_entries.async_forward_entry_setups.assert_awaited_once()
