"""Config flow for the Enki integration.

Two ways to sign in. Email and password is the Keycloak password grant, which an
account federated to Google or Apple does not have: for those the user goes
through the provider in their own browser and brings back the authorization code
Keycloak hands to the app's deep link, which no browser can open (#325). The
refresh token that comes out of it is what the entry stores.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EnkiAPI
from .api.auth import (
    account_from_claims,
    claims_from_token,
    exchange_sso_code,
    sso_authorize_url,
    sso_code_from_callback,
)
from .const import (
    CONF_AUTH_PROVIDER,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TELEMETRY,
    CONF_TELEMETRY_ONBOARDING,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SSO_PROVIDERS,
)
from .exceptions import EnkiAuthError, EnkiConnectionError

CONF_SSO_CODE = "sso_code"


async def _validate_credentials(hass: HomeAssistant, data: dict[str, Any]) -> None:
    api = EnkiAPI(
        data[CONF_USERNAME],
        data.get(CONF_PASSWORD),
        refresh_token=data.get(CONF_REFRESH_TOKEN),
    )
    try:
        await api.async_connect()
        await api.async_get_devices()
    except EnkiAuthError as err:
        raise InvalidAuth from err
    except EnkiConnectionError as err:
        raise CannotConnect from err
    finally:
        await api.async_close()


async def _sign_in_with_provider(
    hass: HomeAssistant,
    pasted: str,
    provider: str,
) -> dict[str, Any]:
    """Trade what the user pasted back for the credentials an entry stores (#325).

    The refresh token is then exercised like a password would be, so a sign-in
    that Keycloak accepts but the gateway refuses fails here rather than at the
    first poll.
    """
    try:
        payload = await exchange_sso_code(
            async_get_clientsession(hass), sso_code_from_callback(pasted), provider
        )
    except EnkiAuthError as err:
        raise InvalidAuth from err
    except EnkiConnectionError as err:
        raise CannotConnect from err

    account = account_from_claims(claims_from_token(payload["access_token"]))
    if not account:
        raise InvalidAuth("The token names no account")
    credentials = {
        CONF_USERNAME: account,
        CONF_REFRESH_TOKEN: payload["refresh_token"],
        CONF_AUTH_PROVIDER: provider,
    }
    await _validate_credentials(hass, credentials)
    return credentials


class EnkiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Enki config and reconfigure flows."""

    VERSION = 2

    @staticmethod
    async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
        """Migrate legacy CyrilP/hass-enki-component config entries."""
        from .migration import async_migrate_entry as migrate_entry

        return await migrate_entry(hass, config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Ask which way in, since the two take different credentials."""
        return self.async_show_menu(step_id="user", menu_options=["password", "sso"])

    async def async_step_password(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_credentials(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                LOGGER.exception("Unexpected error during Enki config flow")
                errors["base"] = "unknown"
            else:
                self.context["credentials"] = user_input
                return await self.async_step_telemetry()

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_sso(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Pick the provider, then hand over the link to sign in with."""
        if user_input is not None:
            self.context[CONF_AUTH_PROVIDER] = user_input[CONF_AUTH_PROVIDER]
            return await self.async_step_sso_code()

        return self.async_show_form(
            step_id="sso",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_PROVIDER, default="google"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=sorted(SSO_PROVIDERS),
                            translation_key=CONF_AUTH_PROVIDER,
                        )
                    ),
                }
            ),
        )

    async def async_step_sso_code(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Take the authorization code back and trade it for tokens."""
        provider = self.context.get(CONF_AUTH_PROVIDER, "google")
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                credentials = await _sign_in_with_provider(
                    self.hass, user_input[CONF_SSO_CODE], provider
                )
            except InvalidAuth:
                errors["base"] = "invalid_code"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during Enki SSO sign-in")
                errors["base"] = "unknown"
            else:
                self.context["credentials"] = credentials
                return await self.async_step_telemetry()

        return self.async_show_form(
            step_id="sso_code",
            data_schema=vol.Schema({vol.Required(CONF_SSO_CODE): str}),
            description_placeholders={"authorize_url": sso_authorize_url(provider)},
            errors=errors,
        )

    async def async_step_telemetry(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Explain opt-in telemetry and let the user choose before finishing setup."""
        credentials = self.context.get("credentials")
        if not credentials:
            return await self.async_step_user()

        if user_input is not None:
            await self.async_set_unique_id(credentials[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Enki – {credentials[CONF_USERNAME]}",
                data=credentials,
                options={
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_TELEMETRY: user_input[CONF_TELEMETRY],
                    CONF_TELEMETRY_ONBOARDING: True,
                },
            )

        return self.async_show_form(
            step_id="telemetry",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TELEMETRY, default=False): selector.BooleanSelector(),
                }
            ),
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if CONF_AUTH_PROVIDER in entry.data:
            # Nothing to change: no password, and the account is whoever the
            # provider says it is. Signing in again is the only operation.
            return await self.async_step_reauth_sso()

        if user_input is not None:
            try:
                await _validate_credentials(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                LOGGER.exception("Unexpected error during Enki reconfigure")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=entry.unique_id,
                    data={**entry.data, **user_input},
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Start reauth when stored credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if CONF_AUTH_PROVIDER in entry.data:
            return await self.async_step_reauth_sso()

        if user_input is not None:
            credentials = {
                CONF_USERNAME: entry.data[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                await _validate_credentials(self.hass, credentials)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                LOGGER.exception("Unexpected error during Enki reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, **credentials},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    def _signed_in_entry(self) -> ConfigEntry:
        """The entry being signed in again, whichever flow asked for it."""
        if self.context.get("source") == SOURCE_REAUTH:
            return self._get_reauth_entry()
        return self._get_reconfigure_entry()

    async def async_step_reauth_sso(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Send a federated account back through its provider (#325).

        Its refresh token is the only credential it has, so when that stops
        working there is nothing to re-enter — only the sign-in to redo.
        """
        entry = self._signed_in_entry()
        provider = entry.data[CONF_AUTH_PROVIDER]
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                credentials = await _sign_in_with_provider(
                    self.hass, user_input[CONF_SSO_CODE], provider
                )
            except InvalidAuth:
                errors["base"] = "invalid_code"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during Enki SSO reauth")
                errors["base"] = "unknown"
            else:
                # Signing in as somebody else would quietly repoint the entry at
                # another home, keeping every entity id of the first one.
                if credentials[CONF_USERNAME].lower() != (entry.unique_id or "").lower():
                    errors["base"] = "wrong_account"
                else:
                    return self.async_update_reload_and_abort(
                        entry, data={**entry.data, **credentials}
                    )

        return self.async_show_form(
            step_id="reauth_sso",
            data_schema=vol.Schema({vol.Required(CONF_SSO_CODE): str}),
            description_placeholders={
                CONF_USERNAME: entry.data[CONF_USERNAME],
                "authorize_url": sso_authorize_url(provider),
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EnkiOptionsFlow:
        return EnkiOptionsFlow(config_entry)


class EnkiOptionsFlow(OptionsFlow):
    """Options flow for polling interval and telemetry."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            options = {
                **dict(self._config_entry.options),
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                CONF_TELEMETRY: user_input[CONF_TELEMETRY],
            }
            return self.async_create_entry(title="", data=options)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
        current_telemetry = self._config_entry.options.get(CONF_TELEMETRY, False)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=5,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                    vol.Required(
                        CONF_TELEMETRY,
                        default=current_telemetry,
                    ): selector.BooleanSelector(),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Cannot reach Enki cloud."""


class InvalidAuth(HomeAssistantError):
    """Invalid Enki credentials."""
