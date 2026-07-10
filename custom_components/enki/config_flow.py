"""Config flow for the Enki integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import EnkiAPI
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TELEMETRY,
    CONF_TELEMETRY_ONBOARDING,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .exceptions import EnkiAuthError, EnkiConnectionError


async def _validate_credentials(hass: HomeAssistant, data: dict[str, Any]) -> None:
    api = EnkiAPI(data[CONF_USERNAME], data[CONF_PASSWORD])
    try:
        await api.async_connect()
        await api.async_get_devices()
    except EnkiAuthError as err:
        raise InvalidAuth from err
    except EnkiConnectionError as err:
        raise CannotConnect from err
    finally:
        await api.async_close()


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
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
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
