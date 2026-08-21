"""Unit tests for the Enki reauthentication flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.config_flow import CannotConnect, EnkiConfigFlow, InvalidAuth


def _flow(entry_data: dict | None = None) -> EnkiConfigFlow:
    flow = EnkiConfigFlow()
    flow.hass = MagicMock()
    entry = MagicMock()
    entry.data = entry_data or {"username": "user@example.com", "password": "old-secret"}
    flow._get_reauth_entry = MagicMock(return_value=entry)  # noqa: SLF001
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    return flow


@pytest.mark.asyncio
async def test_reauth_shows_form_first() -> None:
    flow = _flow()
    await flow.async_step_reauth({"username": "user@example.com"})
    assert flow.async_show_form.call_args.kwargs["step_id"] == "reauth_confirm"
    # The account being reauthenticated is shown to the user.
    placeholders = flow.async_show_form.call_args.kwargs["description_placeholders"]
    assert placeholders["username"] == "user@example.com"


@pytest.mark.asyncio
async def test_reauth_success_updates_entry_with_new_password() -> None:
    flow = _flow()
    with patch("enki.config_flow._validate_credentials", new=AsyncMock()):
        await flow.async_step_reauth_confirm({"password": "new-secret"})

    flow.async_update_reload_and_abort.assert_called_once()
    data = flow.async_update_reload_and_abort.call_args.kwargs["data"]
    # Username preserved, password refreshed.
    assert data["username"] == "user@example.com"
    assert data["password"] == "new-secret"


@pytest.mark.asyncio
async def test_reauth_invalid_password_reprompts() -> None:
    flow = _flow()
    with patch("enki.config_flow._validate_credentials", new=AsyncMock(side_effect=InvalidAuth)):
        await flow.async_step_reauth_confirm({"password": "wrong"})

    flow.async_update_reload_and_abort.assert_not_called()
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_reauth_connection_error_reprompts() -> None:
    flow = _flow()
    with patch("enki.config_flow._validate_credentials", new=AsyncMock(side_effect=CannotConnect)):
        await flow.async_step_reauth_confirm({"password": "whatever"})

    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "cannot_connect"}
