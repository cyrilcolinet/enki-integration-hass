"""Unit tests for the Enki user / telemetry / options / reconfigure flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.config_flow import CannotConnect, EnkiConfigFlow, EnkiOptionsFlow, InvalidAuth


def _flow() -> EnkiConfigFlow:
    flow = EnkiConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()  # noqa: SLF001
    return flow


# --- user step --------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_step_shows_form_without_input() -> None:
    flow = _flow()
    await flow.async_step_user()
    assert flow.async_show_form.call_args.kwargs["step_id"] == "user"


@pytest.mark.asyncio
async def test_user_step_valid_advances_to_telemetry() -> None:
    flow = _flow()
    creds = {"username": "a@b.c", "password": "secret"}
    with patch("enki.config_flow._validate_credentials", new=AsyncMock()):
        await flow.async_step_user(creds)
    # credentials stashed, telemetry form shown next
    assert flow.context["credentials"] == creds
    assert flow.async_show_form.call_args.kwargs["step_id"] == "telemetry"


@pytest.mark.asyncio
async def test_user_step_invalid_auth_shows_error() -> None:
    flow = _flow()
    with patch("enki.config_flow._validate_credentials", new=AsyncMock(side_effect=InvalidAuth)):
        await flow.async_step_user({"username": "a@b.c", "password": "bad"})
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_user_step_cannot_connect_shows_error() -> None:
    flow = _flow()
    with patch("enki.config_flow._validate_credentials", new=AsyncMock(side_effect=CannotConnect)):
        await flow.async_step_user({"username": "a@b.c", "password": "x"})
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_user_step_unexpected_error_shows_unknown() -> None:
    flow = _flow()
    with patch(
        "enki.config_flow._validate_credentials", new=AsyncMock(side_effect=RuntimeError("boom"))
    ):
        await flow.async_step_user({"username": "a@b.c", "password": "x"})
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "unknown"}


# --- telemetry step (entry creation) ---------------------------------------


@pytest.mark.asyncio
async def test_telemetry_step_creates_entry() -> None:
    flow = _flow()
    flow.context["credentials"] = {"username": "A@B.c", "password": "secret"}
    await flow.async_step_telemetry({"telemetry": True})
    flow.async_set_unique_id.assert_awaited_once_with("a@b.c")
    flow._abort_if_unique_id_configured.assert_called_once()  # noqa: SLF001
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data["username"] == "A@B.c"
    options = flow.async_create_entry.call_args.kwargs["options"]
    assert options["telemetry"] is True


@pytest.mark.asyncio
async def test_telemetry_step_without_credentials_restarts_user() -> None:
    flow = _flow()
    await flow.async_step_telemetry({"telemetry": True})
    # no credentials in context → falls back to the user form
    assert flow.async_show_form.call_args.kwargs["step_id"] == "user"


# --- reconfigure ------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconfigure_success_updates_entry() -> None:
    flow = _flow()
    entry = MagicMock()
    entry.data = {"username": "a@b.c", "password": "old"}
    entry.unique_id = "a@b.c"
    flow._get_reconfigure_entry = MagicMock(return_value=entry)  # noqa: SLF001
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    with patch("enki.config_flow._validate_credentials", new=AsyncMock()):
        await flow.async_step_reconfigure({"username": "a@b.c", "password": "new"})
    data = flow.async_update_reload_and_abort.call_args.kwargs["data"]
    assert data["password"] == "new"


@pytest.mark.asyncio
async def test_reconfigure_invalid_auth_shows_error() -> None:
    flow = _flow()
    entry = MagicMock()
    entry.data = {"username": "a@b.c", "password": "old"}
    flow._get_reconfigure_entry = MagicMock(return_value=entry)  # noqa: SLF001
    with patch("enki.config_flow._validate_credentials", new=AsyncMock(side_effect=InvalidAuth)):
        await flow.async_step_reconfigure({"username": "a@b.c", "password": "bad"})
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "invalid_auth"}


# --- options flow -----------------------------------------------------------


@pytest.mark.asyncio
async def test_options_flow_saves_interval_and_telemetry() -> None:
    entry = MagicMock()
    entry.options = {"scan_interval": 30, "telemetry": False}
    options = EnkiOptionsFlow(entry)
    options.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    await options.async_step_init({"scan_interval": 60, "telemetry": True})
    saved = options.async_create_entry.call_args.kwargs["data"]
    assert saved["scan_interval"] == 60
    assert saved["telemetry"] is True


@pytest.mark.asyncio
async def test_options_flow_shows_form_without_input() -> None:
    entry = MagicMock()
    entry.options = {}
    options = EnkiOptionsFlow(entry)
    options.async_show_form = MagicMock(return_value={"type": "form"})
    await options.async_step_init()
    assert options.async_show_form.call_args.kwargs["step_id"] == "init"
