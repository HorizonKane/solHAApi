"""Constants for the Fronius Smart Meter Emulator integration."""

DOMAIN = "fronius_meter_emulator"

CONF_SOURCE_ENTITY = "source_entity"
CONF_LISTEN_HOST = "listen_host"
CONF_LISTEN_PORT = "listen_port"

DEFAULT_LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 8080

API_VERSION_PATH = "/solar_api/GetAPIVersion.cgi"
POWER_FLOW_PATH = "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
