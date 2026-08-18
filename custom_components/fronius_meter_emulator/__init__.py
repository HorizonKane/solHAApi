"""The Fronius Smart Meter Emulator integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_LISTEN_HOST, CONF_LISTEN_PORT, CONF_SOURCE_ENTITY, DEFAULT_LISTEN_HOST, DEFAULT_LISTEN_PORT
from .solar_api_server import FroniusSolarApiServer

_LOGGER = logging.getLogger(__name__)


@dataclass
class FroniusMeterEmulatorData:
    """Runtime data stored on the config entry."""

    server: FroniusSolarApiServer


FroniusMeterEmulatorConfigEntry = ConfigEntry[FroniusMeterEmulatorData]


def _state_to_watts(state: State | None) -> float:
    """Convert a source entity's state to a power value in watts."""
    if state is None or state.state in ("unknown", "unavailable"):
        return 0.0
    try:
        value = float(state.state)
    except ValueError:
        return 0.0
    unit = state.attributes.get("unit_of_measurement", "W")
    if unit == "kW":
        value *= 1000
    return value


async def async_setup_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> bool:
    """Set up Fronius Smart Meter Emulator from a config entry."""
    source_entity = entry.data[CONF_SOURCE_ENTITY]
    listen_host = entry.options.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST)
    listen_port = entry.options.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT)

    server = FroniusSolarApiServer(listen_host, listen_port)
    server.update_pv_power(_state_to_watts(hass.states.get(source_entity)))

    try:
        await server.async_start()
    except OSError as err:
        raise ConfigEntryNotReady(str(err)) from err

    @callback
    def _handle_state_change(event: Event[EventStateChangedData]) -> None:
        server.update_pv_power(_state_to_watts(event.data["new_state"]))

    entry.async_on_unload(
        async_track_state_change_event(hass, [source_entity], _handle_state_change)
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    entry.runtime_data = FroniusMeterEmulatorData(server=server)
    return True


async def _async_reload_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> None:
    """Reload the config entry when options change (e.g. listen host/port)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.server.async_stop()
    return True
