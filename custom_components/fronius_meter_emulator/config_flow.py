"""Config flow for the Fronius Smart Meter Emulator integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    CONF_HTTP_PORT,
    CONF_INVERT_SIGN,
    CONF_MODBUS_ENABLED,
    CONF_MODBUS_PORT,
    CONF_MODBUS_UNIT_ID,
    CONF_SOURCE_ENTITY,
    CONF_SYSTEM_NAME,
    DEFAULT_HTTP_PORT,
    DEFAULT_INVERT_SIGN,
    DEFAULT_MODBUS_ENABLED,
    DEFAULT_MODBUS_PORT,
    DEFAULT_MODBUS_UNIT_ID,
    DEFAULT_SYSTEM_NAME,
    DOMAIN,
)


def _shared_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_INVERT_SIGN, default=defaults.get(CONF_INVERT_SIGN, DEFAULT_INVERT_SIGN)
            ): BooleanSelector(),
            vol.Optional(
                CONF_SYSTEM_NAME, default=defaults.get(CONF_SYSTEM_NAME, DEFAULT_SYSTEM_NAME)
            ): str,
            vol.Optional(
                CONF_HTTP_PORT, default=defaults.get(CONF_HTTP_PORT, DEFAULT_HTTP_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(
                CONF_MODBUS_ENABLED,
                default=defaults.get(CONF_MODBUS_ENABLED, DEFAULT_MODBUS_ENABLED),
            ): BooleanSelector(),
            vol.Optional(
                CONF_MODBUS_PORT, default=defaults.get(CONF_MODBUS_PORT, DEFAULT_MODBUS_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(
                CONF_MODBUS_UNIT_ID,
                default=defaults.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        }
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
                    title="Fronius Smart Meter Emulator", data=user_input
                )

        schema = vol.Schema(
            {vol.Required(CONF_SOURCE_ENTITY): EntitySelector(EntitySelectorConfig(domain="sensor"))}
        ).extend(_shared_schema({}).schema)
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

        schema = _shared_schema(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=schema)
