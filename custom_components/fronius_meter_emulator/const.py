"""Constants for the Fronius Smart Meter Emulator integration."""

DOMAIN = "fronius_meter_emulator"

CONF_SOURCE_ENTITY = "source_entity"
CONF_INVERT_SIGN = "invert_sign"
CONF_SYSTEM_NAME = "system_name"
CONF_HTTP_PORT = "http_port"
CONF_MODBUS_ENABLED = "modbus_enabled"
CONF_MODBUS_PORT = "modbus_port"
CONF_MODBUS_UNIT_ID = "modbus_unit_id"

DEFAULT_SYSTEM_NAME = "fronius-virtual"
DEFAULT_HTTP_PORT = 80
DEFAULT_MODBUS_ENABLED = True
DEFAULT_MODBUS_PORT = 502
DEFAULT_MODBUS_UNIT_ID = 240
DEFAULT_INVERT_SIGN = True

# Fronius Solar API v1 paths
API_BASE = "/solar_api/v1"
API_VERSION = "/solar_api/GetAPIVersion.cgi"
API_ACTIVE_DEVICE_INFO = f"{API_BASE}/GetActiveDeviceInfo.cgi"
API_POWER_FLOW = f"{API_BASE}/GetPowerFlowRealtimeData.fcgi"
API_INVERTER_INFO = f"{API_BASE}/GetInverterInfo.fcgi"
API_INVERTER_REALTIME = f"{API_BASE}/GetInverterRealtimeData.fcgi"
API_METER_REALTIME = f"{API_BASE}/GetMeterRealtimeData.fcgi"
API_STORAGE_REALTIME = f"{API_BASE}/GetStorageRealtimeData.fcgi"
API_LOGGER_INFO = f"{API_BASE}/GetLoggerInfo.fcgi"

FRONIUS_DEVICE_TYPE = 1  # DT=1 = hybrid inverter (GEN24), what the Wattpilot expects
