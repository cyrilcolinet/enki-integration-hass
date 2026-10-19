"""OAuth session management for the Enki Keycloak realm.

Two ways in, both against the same realm and the same public client:

- **email and password**, Keycloak's resource-owner password grant, which is what
  the app sends for an account that has a password;
- **Google or Apple**, Keycloak's own identity brokering (#325). The app opens
  ``…/openid-connect/auth`` with ``kc_idp_hint``, Keycloak bounces through the
  provider and comes back to the app's deep link with a code, which is exchanged
  on the token endpoint with a ``provider_type``.

An account federated to Google or Apple has **no password in this realm**, so the
password grant can only ever fail for it. Its refresh token is the credential
instead, which also means there is nothing to fall back on when that token dies:
the user has to go through the provider again, and Home Assistant asks them to.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from ..const import (
    ENKI_OIDC_AUTH_URL,
    ENKI_OIDC_CLIENT_ID,
    ENKI_OIDC_URL,
    ENKI_SSO_REDIRECT_URI,
    LOGGER,
    SSO_PROVIDERS,
)
from ..exceptions import EnkiAuthError, EnkiConnectionError


def sso_authorize_url(provider: str) -> str:
    """Where to send the user to sign in with Google or Apple (#325)."""
    return f"{ENKI_OIDC_AUTH_URL}?" + urlencode(
        {
            "client_id": ENKI_OIDC_CLIENT_ID,
            "kc_idp_hint": provider,
            "redirect_uri": ENKI_SSO_REDIRECT_URI,
            "response_type": "code",
            "scope": "profile email",
        }
    )


def sso_code_from_callback(pasted: str) -> str:
    """The code out of whatever the user pasted back.

    The redirect lands on the app's own deep link, which a desktop browser cannot
    open, so what the user has in front of them is the address bar. They may
    paste the whole thing, or just the code. Keycloak reports a refusal on that
    same redirect, as ``error=``, and that is worth saying rather than sending an
    empty code to the token endpoint.
    """
    pasted = pasted.strip()
    if not pasted:
        raise EnkiAuthError("No code in what was pasted")
    query = parse_qs(urlparse(pasted).query) if "?" in pasted else {}
    if error := query.get("error"):
        raise EnkiAuthError(f"The provider refused the sign-in: {error[0]}")
    if code := query.get("code"):
        return code[0]
    if query:
        raise EnkiAuthError("That address carries no code")
    # Not a URL: assume the code itself, pasted on its own.
    return pasted


def claims_from_token(access_token: str) -> dict[str, Any]:
    """The claims an access token carries, read without verifying it.

    Only used to label the entry with the account it belongs to. The token's
    signature is Keycloak's business, it is the gateway that checks it, and
    nothing here trusts these claims for access.
    """
    try:
        payload = access_token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except (IndexError, ValueError) as err:
        raise EnkiAuthError("Unreadable access token") from err
    return claims if isinstance(claims, dict) else {}


def account_from_claims(claims: dict[str, Any]) -> str | None:
    """The email a federated account is known by, for the entry's title and id."""
    for field in ("email", "preferred_username", "upn"):
        value = claims.get(field)
        if isinstance(value, str) and value:
            return value
    return None


class EnkiAuthSession:
    """Maintains access and refresh tokens for Enki cloud APIs.

    Tokens are renewed via refresh_token when possible, falling back to the
    resource-owner password grant only when refresh fails (#44).
    """

    _TOKEN_SKEW_SECONDS = 30

    def __init__(
        self,
        username: str,
        password: str | None = None,
        *,
        refresh_token: str | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = refresh_token
        self._token_type = "Bearer"
        self._token_expires_at = 0.0

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """The current refresh token, which Keycloak may replace on every use.

        For an account without a password this is the only credential there is,
        so whoever stored it has to notice when it changes.
        """
        return self._refresh_token

    @property
    def token_type(self) -> str:
        return self._token_type

    def is_valid(self) -> bool:
        return (
            bool(self._access_token)
            and time.time() < self._token_expires_at - self._TOKEN_SKEW_SECONDS
        )

    def auth_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build Authorization header; call ``ensure_valid`` first."""
        headers = {"Authorization": f"{self._token_type} {self._access_token}"}
        if extra:
            headers.update(extra)
        return headers

    async def ensure_valid(self, session: aiohttp.ClientSession) -> None:
        """Refresh or re-authenticate when the access token is near expiry."""
        if self.is_valid():
            return
        if self._refresh_token:
            try:
                await self.refresh(session)
                return
            except EnkiAuthError:
                if self._password is None:
                    # Federated account: there is no second way in, and Home
                    # Assistant's reauthentication is the only honest answer.
                    raise
                LOGGER.debug("Refresh token rejected, falling back to password grant")
        await self.connect(session)

    async def connect(self, session: aiohttp.ClientSession) -> None:
        """Authenticate with Keycloak: the password grant, or the stored token."""
        if self._password is None:
            if not self._refresh_token:
                raise EnkiAuthError("No password and no refresh token to sign in with")
            await self.refresh(session)
            return
        payload = await self._token_request(
            session,
            {
                "grant_type": "password",
                "client_id": "enki-front",
                "username": self._username,
                "password": self._password,
            },
        )
        if payload is None:
            raise EnkiAuthError("Invalid username or password")
        self._apply_token_payload(payload)
        LOGGER.debug("Enki session established, expires in %ss", payload["expires_in"])

    async def refresh(self, session: aiohttp.ClientSession) -> None:
        """Renew the access token without sending the account password again."""
        if not self._refresh_token:
            raise EnkiAuthError("No refresh token available")
        payload = await self._token_request(
            session,
            {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": "enki-front",
            },
        )
        if payload is None:
            raise EnkiAuthError("Token refresh rejected")
        self._apply_token_payload(payload)
        LOGGER.debug("Enki token refreshed, expires in %ss", payload["expires_in"])

    def invalidate(self) -> None:
        """Drop cached tokens so the next request re-authenticates."""
        self._access_token = None
        self._token_expires_at = 0.0

    def _apply_token_payload(self, payload: dict[str, Any]) -> None:
        self._access_token = payload["access_token"]
        self._token_type = payload.get("token_type", "Bearer")
        self._token_expires_at = time.time() + payload["expires_in"]
        if refreshed := payload.get("refresh_token"):
            self._refresh_token = refreshed

    async def _token_request(
        self,
        session: aiohttp.ClientSession,
        data: dict[str, str],
    ) -> dict[str, Any] | None:
        return await request_token(session, data)


async def request_token(
    session: aiohttp.ClientSession,
    data: dict[str, str],
) -> dict[str, Any] | None:
    """POST the token endpoint; None when the realm refused the grant.

    Keycloak answers 401 for a password it does not accept and 400 for a code it
    will not take: expired, already used, or issued for another redirect. Both
    are refusals rather than faults, so both read as "no token"; the body goes to
    the debug log, which is the only place the distinction is visible.
    """
    try:
        async with session.post(
            ENKI_OIDC_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        ) as response:
            if response.status in (400, 401):
                LOGGER.debug(
                    "Enki auth refused the %s grant: HTTP %s %s",
                    data.get("grant_type"),
                    response.status,
                    await response.text(),
                )
                return None
            if response.status != 200:
                raise EnkiConnectionError(f"Authentication failed: HTTP {response.status}")
            return await response.json()
    except aiohttp.ClientError as err:
        raise EnkiConnectionError(f"Cannot reach Enki auth: {err}") from err


async def exchange_sso_code(
    session: aiohttp.ClientSession,
    code: str,
    provider: str,
) -> dict[str, Any]:
    """Trade a Keycloak authorization code for tokens (#325).

    The code is single-use and short-lived (a minute, on a default realm), so a
    refusal here is nearly always one that was pasted too late or twice.
    """
    payload = await request_token(
        session,
        {
            "grant_type": "authorization_code",
            "code": code,
            "provider_type": SSO_PROVIDERS[provider],
            "redirect_uri": ENKI_SSO_REDIRECT_URI,
            "client_id": ENKI_OIDC_CLIENT_ID,
        },
    )
    if payload is None:
        raise EnkiAuthError("The sign-in code was refused: expired, or already used")
    # Claim *names* only: which claims a federated token carries, against a
    # password account's, is the first thing to check if the gateway refuses it.
    LOGGER.debug("Enki SSO token claims: %s", sorted(claims_from_token(payload["access_token"])))
    return payload
