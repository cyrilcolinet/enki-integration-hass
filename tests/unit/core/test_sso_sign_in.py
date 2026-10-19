"""Signing in with Google or Apple, which have no Enki password (#325).

The app opens Keycloak's authorize endpoint with ``kc_idp_hint``, Keycloak brokers
the provider and comes back to ``enki://oauth/callback`` with a code, and that
code is exchanged on the same token endpoint the password grant uses. Everything
here is checked against those exact parameters, read out of APK 2.26.3.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from aioresponses import aioresponses
from enki.api.auth import (
    EnkiAuthSession,
    account_from_claims,
    claims_from_token,
    exchange_sso_code,
    sso_authorize_url,
    sso_code_from_callback,
)
from enki.config_flow import EnkiConfigFlow
from enki.const import ENKI_OIDC_URL
from enki.exceptions import EnkiAuthError

CALLBACK = "enki://oauth/callback"


def _token(claims: dict) -> str:
    """An access token shaped like Keycloak's, with no signature worth checking."""
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{body}.signature"


TOKENS = {
    "access_token": _token({"email": "someone@gmail.com", "preferred_username": "someone"}),
    "refresh_token": "refresh-1",
    "token_type": "Bearer",
    "expires_in": 300,
}


# --- the authorize link -----------------------------------------------------


def test_the_link_carries_what_the_app_sends() -> None:
    query = parse_qs(urlparse(sso_authorize_url("google")).query)

    assert query["client_id"] == ["enki-front"]
    assert query["kc_idp_hint"] == ["google"]
    assert query["redirect_uri"] == [CALLBACK]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["profile email"]


def test_apple_is_the_same_link_with_its_own_hint() -> None:
    assert parse_qs(urlparse(sso_authorize_url("apple")).query)["kc_idp_hint"] == ["apple"]


# --- what comes back --------------------------------------------------------


def test_the_code_is_read_out_of_the_pasted_address() -> None:
    """No browser opens enki://, so what the user has is the address bar."""
    pasted = f"{CALLBACK}?state=abc&session_state=def&code=the-code"

    assert sso_code_from_callback(pasted) == "the-code"


def test_a_code_pasted_on_its_own_is_taken_as_is() -> None:
    assert sso_code_from_callback("  the-code  ") == "the-code"


def test_a_refusal_from_the_provider_is_not_a_code() -> None:
    """Keycloak reports it on the same redirect, and sending it on would hide it."""
    with pytest.raises(EnkiAuthError, match="access_denied"):
        sso_code_from_callback(f"{CALLBACK}?error=access_denied&error_description=no")


def test_an_address_without_a_code_says_so() -> None:
    with pytest.raises(EnkiAuthError, match="no code"):
        sso_code_from_callback(f"{CALLBACK}?state=abc")


def test_nothing_pasted_is_an_error_not_an_empty_code() -> None:
    with pytest.raises(EnkiAuthError):
        sso_code_from_callback("   ")


# --- the account the entry is named after -----------------------------------


def test_the_account_comes_out_of_the_token() -> None:
    claims = claims_from_token(TOKENS["access_token"])

    assert claims["email"] == "someone@gmail.com"
    assert account_from_claims(claims) == "someone@gmail.com"


def test_a_token_without_an_email_falls_back_to_the_username() -> None:
    assert account_from_claims({"preferred_username": "someone"}) == "someone"
    assert account_from_claims({}) is None


def test_an_unreadable_token_is_refused_rather_than_guessed() -> None:
    with pytest.raises(EnkiAuthError):
        claims_from_token("not-a-token")


# --- the exchange -----------------------------------------------------------


@pytest.mark.asyncio
async def test_the_exchange_sends_the_app_s_own_parameters() -> None:
    import aiohttp

    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=200, payload=TOKENS)
        async with aiohttp.ClientSession() as session:
            payload = await exchange_sso_code(session, "the-code", "google")

        assert payload["refresh_token"] == "refresh-1"
        (request,) = next(iter(mocked.requests.values()))
        sent = request.kwargs["data"]
        assert sent == {
            "grant_type": "authorization_code",
            "code": "the-code",
            "provider_type": "GOOGLE",
            "redirect_uri": CALLBACK,
            "client_id": "enki-front",
        }


@pytest.mark.asyncio
async def test_a_code_keycloak_refuses_reads_as_expired() -> None:
    """A code lives about a minute and works once, so 400 is the common case."""
    import aiohttp

    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=400, payload={"error": "invalid_grant"})
        async with aiohttp.ClientSession() as session:
            with pytest.raises(EnkiAuthError, match="already used"):
                await exchange_sso_code(session, "stale", "google")


# --- a session with no password ---------------------------------------------


@pytest.mark.asyncio
async def test_a_federated_session_starts_from_its_refresh_token() -> None:
    import aiohttp

    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=200, payload={**TOKENS, "refresh_token": "refresh-2"})
        auth = EnkiAuthSession("someone@gmail.com", None, refresh_token="refresh-1")
        async with aiohttp.ClientSession() as session:
            await auth.connect(session)

        (request,) = next(iter(mocked.requests.values()))
        assert request.kwargs["data"]["grant_type"] == "refresh_token"
        assert auth.refresh_token == "refresh-2", "Keycloak rotates it on every use"


@pytest.mark.asyncio
async def test_a_dead_refresh_token_raises_instead_of_trying_a_password() -> None:
    """There is no password to fall back on, and pretending otherwise hides the ask."""
    import aiohttp

    with aioresponses() as mocked:
        mocked.post(ENKI_OIDC_URL, status=401, payload={"error": "invalid_grant"})
        auth = EnkiAuthSession("someone@gmail.com", None, refresh_token="dead")
        async with aiohttp.ClientSession() as session:
            with pytest.raises(EnkiAuthError):
                await auth.ensure_valid(session)

        assert len(next(iter(mocked.requests.values()))) == 1, "one attempt, not two"


@pytest.mark.asyncio
async def test_a_session_with_neither_credential_says_so() -> None:
    import aiohttp

    auth = EnkiAuthSession("someone@gmail.com")
    async with aiohttp.ClientSession() as session:
        with pytest.raises(EnkiAuthError, match="no refresh token"):
            await auth.connect(session)


# --- the flow ---------------------------------------------------------------


def _flow() -> EnkiConfigFlow:
    flow = EnkiConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_show_menu = MagicMock(return_value={"type": "menu"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()  # noqa: SLF001
    return flow


@pytest.mark.asyncio
async def test_the_link_reaches_the_form_the_user_reads() -> None:
    flow = _flow()
    flow.context["auth_provider"] = "google"

    await flow.async_step_sso_code()

    placeholders = flow.async_show_form.call_args.kwargs["description_placeholders"]
    assert "kc_idp_hint=google" in placeholders["authorize_url"]


@pytest.mark.asyncio
async def test_a_successful_sign_in_stores_the_token_and_the_provider() -> None:
    flow = _flow()
    flow.context["auth_provider"] = "google"
    signed_in = {
        "username": "someone@gmail.com",
        "refresh_token": "refresh-1",
        "auth_provider": "google",
    }

    with patch("enki.config_flow._sign_in_with_provider", new=AsyncMock(return_value=signed_in)):
        await flow.async_step_sso_code({"sso_code": f"{CALLBACK}?code=x"})

    assert flow.context["credentials"] == signed_in
    # On to the same telemetry question a password sign-in answers.
    assert flow.async_show_form.call_args.kwargs["step_id"] == "telemetry"


@pytest.mark.asyncio
async def test_an_entry_from_a_provider_carries_no_password() -> None:
    flow = _flow()
    flow.context["credentials"] = {
        "username": "someone@gmail.com",
        "refresh_token": "refresh-1",
        "auth_provider": "google",
    }

    await flow.async_step_telemetry({"telemetry": False})

    data = flow.async_create_entry.call_args.kwargs["data"]
    assert "password" not in data
    assert data["refresh_token"] == "refresh-1"
    flow.async_set_unique_id.assert_awaited_once_with("someone@gmail.com")


@pytest.mark.asyncio
async def test_reauth_sends_a_federated_account_back_to_its_provider() -> None:
    flow = _flow()
    entry = MagicMock()
    entry.data = {"username": "someone@gmail.com", "auth_provider": "google"}
    entry.unique_id = "someone@gmail.com"
    flow.context["source"] = "reauth"
    flow._get_reauth_entry = MagicMock(return_value=entry)  # noqa: SLF001

    await flow.async_step_reauth_confirm()

    # Not the password form: there is no password to re-enter.
    assert flow.async_show_form.call_args.kwargs["step_id"] == "reauth_sso"


@pytest.mark.asyncio
async def test_signing_in_as_someone_else_is_refused() -> None:
    """It would repoint the entry at another home and keep every entity id."""
    flow = _flow()
    entry = MagicMock()
    entry.data = {"username": "someone@gmail.com", "auth_provider": "google"}
    entry.unique_id = "someone@gmail.com"
    flow.context["source"] = "reauth"
    flow._get_reauth_entry = MagicMock(return_value=entry)  # noqa: SLF001
    other = {
        "username": "someone.else@gmail.com",
        "refresh_token": "refresh-9",
        "auth_provider": "google",
    }

    with patch("enki.config_flow._sign_in_with_provider", new=AsyncMock(return_value=other)):
        await flow.async_step_reauth_sso({"sso_code": "x"})

    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "wrong_account"}
    flow.async_update_reload_and_abort.assert_not_called()


# --- keeping the stored token current ---------------------------------------


def _coordinator(entry_data: dict) -> tuple:
    from enki.coordinator import EnkiCoordinator

    hass = MagicMock()
    entry = MagicMock()
    entry.data = entry_data
    entry.options = {}
    coordinator = EnkiCoordinator(hass, entry)
    coordinator.hass = hass
    coordinator.api = MagicMock()
    return coordinator, hass, entry


def test_a_rotated_token_is_written_back_to_the_entry() -> None:
    """Keycloak hands back a new one on every use; lose it and a restart has nothing."""
    coordinator, hass, entry = _coordinator(
        {"username": "someone@gmail.com", "refresh_token": "refresh-1", "auth_provider": "google"}
    )
    coordinator.api.refresh_token = "refresh-2"

    coordinator._persist_rotated_refresh_token()  # noqa: SLF001

    data = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert data["refresh_token"] == "refresh-2"
    assert data["auth_provider"] == "google"


def test_an_unchanged_token_is_not_written_every_poll() -> None:
    coordinator, hass, _ = _coordinator(
        {"username": "someone@gmail.com", "refresh_token": "refresh-1", "auth_provider": "google"}
    )
    coordinator.api.refresh_token = "refresh-1"

    coordinator._persist_rotated_refresh_token()  # noqa: SLF001

    hass.config_entries.async_update_entry.assert_not_called()


def test_a_password_account_keeps_its_password_as_the_credential() -> None:
    """A token stored beside a password would outlive a password change."""
    coordinator, hass, _ = _coordinator({"username": "a@b.c", "password": "secret"})
    coordinator.api.refresh_token = "refresh-2"

    coordinator._persist_rotated_refresh_token()  # noqa: SLF001

    hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_reconfigure_on_a_federated_entry_signs_in_again() -> None:
    """There is no password to change, so the only operation is the sign-in."""
    flow = _flow()
    entry = MagicMock()
    entry.data = {"username": "someone@gmail.com", "auth_provider": "google"}
    entry.unique_id = "someone@gmail.com"
    flow.context["source"] = "reconfigure"
    flow._get_reconfigure_entry = MagicMock(return_value=entry)  # noqa: SLF001

    await flow.async_step_reconfigure()

    assert flow.async_show_form.call_args.kwargs["step_id"] == "reauth_sso"


@pytest.mark.asyncio
async def test_a_rotated_token_does_not_reload_the_integration() -> None:
    """Every entry write reaches the listener; reloading on a poll would loop (#325)."""
    from enki import _async_update_listener

    hass = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    coordinator, _, entry = _coordinator(
        {"username": "someone@gmail.com", "refresh_token": "refresh-1", "auth_provider": "google"}
    )
    entry.runtime_data = coordinator

    await _async_update_listener(hass, entry)

    hass.config_entries.async_reload.assert_not_called()


@pytest.mark.asyncio
async def test_an_options_change_still_reloads() -> None:
    from enki import _async_update_listener

    hass = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    coordinator, _, entry = _coordinator({"username": "a@b.c", "password": "secret"})
    entry.runtime_data = coordinator
    entry.options = {"scan_interval": 60}

    await _async_update_listener(hass, entry)

    hass.config_entries.async_reload.assert_awaited_once()
