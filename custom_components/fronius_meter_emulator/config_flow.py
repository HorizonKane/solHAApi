"""Config flow for the Fronius Smart Meter Emulator integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_SOURCE_ENTITY,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DOMAIN,
)


class FroniusMeterEmulatorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fronius Smart Meter Emulator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            state = self.hass.states.get(user_input[CONF_SOURCE_ENTITY])
            if state is None:
                errors["base"] = "entity_not_found"
            else:
                await self.async_set_unique_id(user_input[CONF_SOURCE_ENTITY])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Fronius Solar API Emulator", data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_LISTEN_PORT, default=DEFAULT_LISTEN_PORT
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FroniusMeterEmulatorOptionsFlow()


class FroniusMeterEmulatorOptionsFlow(OptionsFlow):
    """Handle options for Fronius Smart Meter Emulator."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LISTEN_HOST,
                    default=options.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST),
                ): str,
                vol.Optional(
                    CONF_LISTEN_PORT,
                    default=options.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
