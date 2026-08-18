"""Constants for the Fronius Smart Meter Emulator integration."""

DOMAIN = "fronius_meter_emulator"

CONF_LISTEN_HOST = "listen_host"
CONF_LISTEN_PORT = "listen_port"
CONF_UNIT_ID = "unit_id"
CONF_SERIAL_NUMBER = "serial_number"
CONF_POWER_SOURCE = "power_source"
CONF_INVERT_SIGN = "invert_sign"

DEFAULT_SCAN_INTERVAL = 5
DEFAULT_LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 1502
DEFAULT_UNIT_ID = 1
DEFAULT_SERIAL_NUMBER = "HA00000001"
DEFAULT_INVERT_SIGN = True

POWER_SOURCE_PV = "P_PV"
POWER_SOURCE_GRID = "P_Grid"
POWER_SOURCES = [POWER_SOURCE_PV, POWER_SOURCE_GRID]

SOLAR_API_PATH = "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"

MANUFACTURER = "Fronius"
METER_MODEL_NAME = "Smart Meter 63A-3"

SIGNAL_METER_UPDATE = f"{DOMAIN}_meter_update"
