"""The Fronius Smart Meter Emulator integration.

Emulates a Fronius system (Solar API over HTTP + Smart Meter IP over Modbus
TCP, both announced via mDNS) so a Fronius Wattpilot can do PV-surplus
charging against a Home Assistant entity instead of real Fronius hardware.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_state_change_event

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
)
from .mdns_announcer import FroniusMDNSAnnouncer, RawMDNSAnnouncer
from .modbus_server import FroniusSmartMeterModbusServer
from .solar_api_server import FroniusSolarApiServer

_LOGGER = logging.getLogger(__name__)


@dataclass
class FroniusMeterEmulatorData:
    """Runtime data stored on the config entry."""

    http_server: FroniusSolarApiServer
    mdns: FroniusMDNSAnnouncer | None
    raw_mdns: RawMDNSAnnouncer | None
    modbus_server: FroniusSmartMeterModbusServer | None


FroniusMeterEmulatorConfigEntry = ConfigEntry[FroniusMeterEmulatorData]


def _make_serial(entry_id: str) -> str:
    return hashlib.md5(entry_id.encode()).hexdigest()[:8].upper()


def _state_to_watts(state: State | None) -> float:
    """Convert a source entity's state to a power value in watts."""
    if state is None or state.state in ("unknown", "unavailable"):
        return 0.0
    try:
        value = float(state.state)
    except ValueError:
        return 0.0
    if state.attributes.get("unit_of_measurement") == "kW":
        value *= 1000
    return value


async def async_setup_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> bool:
    """Set up Fronius Smart Meter Emulator from a config entry."""
    config = {**entry.data, **entry.options}

    source_entity = config[CONF_SOURCE_ENTITY]
    invert_sign = config.get(CONF_INVERT_SIGN, DEFAULT_INVERT_SIGN)
    system_name = config.get(CONF_SYSTEM_NAME) or DEFAULT_SYSTEM_NAME
    http_port = int(config.get(CONF_HTTP_PORT, DEFAULT_HTTP_PORT))
    modbus_enabled = bool(config.get(CONF_MODBUS_ENABLED, DEFAULT_MODBUS_ENABLED))
    modbus_port = int(config.get(CONF_MODBUS_PORT, DEFAULT_MODBUS_PORT))
    modbus_unit_id = int(config.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID))
    serial = _make_serial(entry.entry_id)

    def _current_power() -> float:
        watts = _state_to_watts(hass.states.get(source_entity))
        return -watts if invert_sign else watts

    # ── HTTP Solar API server ────────────────────────────────────────────
    http_server = FroniusSolarApiServer(http_port, serial, system_name)
    http_server.update_power(_current_power())
    try:
        await http_server.async_start()
    except OSError as err:
        raise ConfigEntryNotReady(str(err)) from err

    # ── mDNS announcers ───────────────────────────────────────────────────
    mdns = FroniusMDNSAnnouncer(name=system_name, port=http_port, system_name=system_name)
    try:
        await mdns.async_start(hass)
    except Exception as err:  # noqa: BLE001 - non-fatal, HTTP server still works
        _LOGGER.warning("mDNS announcement failed (non-fatal): %s", err)
        mdns = None

    raw_mdns = RawMDNSAnnouncer(
        name=system_name, port=http_port, serial=serial, system_name=system_name
    )
    try:
        await raw_mdns.async_start()
    except Exception as err:  # noqa: BLE001 - non-fatal
        _LOGGER.warning("Raw mDNS announcement failed (non-fatal): %s", err)
        raw_mdns = None

    # ── Modbus TCP Smart Meter IP server (optional) ──────────────────────
    modbus_server: FroniusSmartMeterModbusServer | None = None
    if modbus_enabled:
        modbus_server = FroniusSmartMeterModbusServer(modbus_port, serial, modbus_unit_id)
        modbus_server.update_power(_current_power())
        try:
            await modbus_server.async_start()
        except OSError as err:
            _LOGGER.error(
                "Failed to start Modbus server on port %d: %s. "
                "PV-surplus pairing may not work without it.",
                modbus_port, err,
            )
            modbus_server = None

    @callback
    def _handle_state_change(event: Event[EventStateChangedData]) -> None:
        power = _current_power()
        http_server.update_power(power)
        if modbus_server is not None:
            modbus_server.update_power(power)

    entry.async_on_unload(
        async_track_state_change_event(hass, [source_entity], _handle_state_change)
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    entry.runtime_data = FroniusMeterEmulatorData(
        http_server=http_server, mdns=mdns, raw_mdns=raw_mdns, modbus_server=modbus_server
    )
    return True


async def _async_reload_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> bool:
    """Unload a config entry."""
    data = entry.runtime_data
    await data.http_server.async_stop()
    if data.mdns is not None:
        await data.mdns.async_stop()
    if data.raw_mdns is not None:
        await data.raw_mdns.async_stop()
    if data.modbus_server is not None:
        await data.modbus_server.async_stop()
    return True
