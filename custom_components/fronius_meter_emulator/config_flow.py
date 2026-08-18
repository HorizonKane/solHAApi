"""Config flow for the Fronius Smart Meter Emulator integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_INVERT_SIGN,
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_POWER_SOURCE,
    CONF_SERIAL_NUMBER,
    DEFAULT_INVERT_SIGN,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SERIAL_NUMBER,
    DOMAIN,
    POWER_SOURCE_PV,
    POWER_SOURCES,
    SOLAR_API_PATH,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_host(hass, host: str) -> None:
    """Raise ValueError if the Fronius Solar API is not reachable at host."""
    session = async_get_clientsession(hass)
    async with asyncio.timeout(10):
        async with session.get(f"http://{host}{SOLAR_API_PATH}") as response:
            response.raise_for_status()
            await response.json(content_type=None)


class FroniusMeterEmulatorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fronius Smart Meter Emulator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate_host(self.hass, user_input[CONF_HOST])
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Fronius Meter Emulator ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(
                    CONF_SERIAL_NUMBER, default=DEFAULT_SERIAL_NUMBER
                ): str,
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
                    "scan_interval",
                    default=options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Optional(
                    CONF_LISTEN_HOST,
                    default=options.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST),
                ): str,
                vol.Optional(
                    CONF_LISTEN_PORT,
                    default=options.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Optional(
                    CONF_POWER_SOURCE,
                    default=options.get(CONF_POWER_SOURCE, POWER_SOURCE_PV),
                ): SelectSelector(
                    SelectSelectorConfig(options=POWER_SOURCES, translation_key="power_source")
                ),
                vol.Optional(
                    CONF_INVERT_SIGN,
                    default=options.get(CONF_INVERT_SIGN, DEFAULT_INVERT_SIGN),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
