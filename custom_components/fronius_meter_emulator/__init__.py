"""The Fronius Smart Meter Emulator integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

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
)
from .coordinator import FroniusSolarApiCoordinator
from .modbus_server import FroniusSmartMeterServer

PLATFORMS = [Platform.SENSOR]


@dataclass
class FroniusMeterEmulatorData:
    """Runtime data stored on the config entry."""

    coordinator: FroniusSolarApiCoordinator
    meter_server: FroniusSmartMeterServer


FroniusMeterEmulatorConfigEntry = ConfigEntry[FroniusMeterEmulatorData]


async def async_setup_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> bool:
    """Set up Fronius Smart Meter Emulator from a config entry."""
    options = entry.options
    host = entry.data[CONF_HOST]
    scan_interval = options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    listen_host = options.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST)
    listen_port = options.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT)
    serial_number = entry.data.get(CONF_SERIAL_NUMBER, DEFAULT_SERIAL_NUMBER)
    power_source = options.get(CONF_POWER_SOURCE, POWER_SOURCE_PV)
    invert_sign = options.get(CONF_INVERT_SIGN, DEFAULT_INVERT_SIGN)

    coordinator = FroniusSolarApiCoordinator(hass, host, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    meter_server = FroniusSmartMeterServer(listen_host, listen_port, serial_number)
    try:
        await meter_server.async_start()
    except OSError as err:
        raise ConfigEntryNotReady(str(err)) from err

    def _push_reading() -> None:
        value = coordinator.data.get(power_source, 0.0)
        if invert_sign:
            value = -value
        meter_server.update_power(value)

    _push_reading()
    remove_listener = coordinator.async_add_listener(_push_reading)

    entry.runtime_data = FroniusMeterEmulatorData(
        coordinator=coordinator, meter_server=meter_server
    )
    entry.async_on_unload(remove_listener)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> None:
    """Reload the config entry when options change (e.g. port, scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: FroniusMeterEmulatorConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.meter_server.async_stop()
    return unload_ok
