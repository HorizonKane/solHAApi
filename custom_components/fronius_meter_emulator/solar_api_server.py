"""HTTP server emulating a Fronius Datamanager's local Solar API.

Implements the broader set of Solar API v1 endpoints a Fronius Wattpilot may
probe during pairing/commissioning (not just GetPowerFlowRealtimeData.fcgi),
plus a catch-all for anything else under /solar_api/ so an unrecognized
request doesn't 404 and abort discovery.

Endpoint set and response shapes ported from, and credit to,
https://github.com/l2smith2/fronius-virtual-inverter (MIT licensed), tested
by its author against real Wattpilot firmware.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp import web

from .const import (
    API_ACTIVE_DEVICE_INFO,
    API_INVERTER_INFO,
    API_INVERTER_REALTIME,
    API_LOGGER_INFO,
    API_METER_REALTIME,
    API_POWER_FLOW,
    API_STORAGE_REALTIME,
    API_VERSION,
    FRONIUS_DEVICE_TYPE,
)

_LOGGER = logging.getLogger(__name__)


@web.middleware
async def _error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as err:
        _LOGGER.error("HTTP handler error for %s: %s", request.path, err)
        return web.Response(status=500)


def _make_head(request_arguments: dict | None = None) -> dict:
    return {
        "RequestArguments": request_arguments if request_arguments is not None else {},
        "Status": {"Code": 0, "Reason": "", "UserMessage": ""},
        "Timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }


class FroniusSolarApiServer:
    """Emulates a Fronius Datamanager's local Solar API over HTTP."""

    def __init__(self, port: int, serial: str, system_name: str) -> None:
        self._port = port
        self._serial = serial
        self._system_name = system_name
        self._power_watts: float = 0.0
        self._app = web.Application(middlewares=[_error_middleware])
        self._runner: web.AppRunner | None = None
        self._setup_routes()

    def update_power(self, watts: float) -> None:
        """Update the (signed) grid power value served to clients."""
        self._power_watts = watts

    def _setup_routes(self) -> None:
        self._app.router.add_get(API_VERSION, self._handle_api_version)
        self._app.router.add_get(API_ACTIVE_DEVICE_INFO, self._handle_active_device_info)
        self._app.router.add_get(API_POWER_FLOW, self._handle_power_flow)
        self._app.router.add_get(API_INVERTER_INFO, self._handle_inverter_info)
        self._app.router.add_get(API_INVERTER_REALTIME, self._handle_inverter_realtime)
        self._app.router.add_get(API_METER_REALTIME, self._handle_meter_realtime)
        self._app.router.add_get(
            "/solar_api/v1/GetMeterRealtimeData.cgi", self._handle_meter_realtime
        )
        self._app.router.add_get(API_STORAGE_REALTIME, self._handle_storage_realtime)
        self._app.router.add_get(API_LOGGER_INFO, self._handle_logger_info)
        self._app.router.add_get("/solar_api/{tail:.*}", self._handle_unknown)

    def _json_response(self, data: Any) -> web.Response:
        return web.Response(content_type="application/json", text=json.dumps(data))

    async def _handle_api_version(self, request: web.Request) -> web.Response:
        return self._json_response(
            {"APIVersion": 1, "BaseURL": "/solar_api/v1/", "CompatibilityRange": "1.8-1"}
        )

    async def _handle_active_device_info(self, request: web.Request) -> web.Response:
        device_class = request.rel_url.query.get("DeviceClass", "")
        data = {"0": {"DT": -1, "Serial": self._serial}} if device_class == "Meter" else {}
        return self._json_response({"Body": {"Data": data}, "Head": _make_head()})

    async def _handle_power_flow(self, request: web.Request) -> web.Response:
        power = self._power_watts
        p_pv = max(power * -1, 0.0)  # best-effort: surplus only, no separate PV reading

        payload = {
            "Body": {
                "Data": {
                    "Inverters": {
                        "1": {"DT": FRONIUS_DEVICE_TYPE, "P": round(p_pv, 1), "E_Day": 0.0}
                    },
                    "Site": {
                        "Meter_Location": "grid",
                        "Mode": "meter",
                        "P_Grid": round(power, 1),
                        "P_PV": round(p_pv, 1),
                        "P_Load": None,
                        "P_Akku": None,
                        "E_Day": 0.0,
                        "E_Year": 0.0,
                        "E_Total": 0.0,
                    },
                    "Version": "12",
                }
            },
            "Head": _make_head(),
        }
        return self._json_response(payload)

    async def _handle_inverter_info(self, request: web.Request) -> web.Response:
        payload = {
            "Body": {
                "Data": {
                    "1": {
                        "CustomName": self._system_name,
                        "DT": FRONIUS_DEVICE_TYPE,
                        "ErrorCode": 0,
                        "PVPower": 5000,
                        "Show": 1,
                        "StatusCode": 7,
                        "UniqueID": self._serial,
                    }
                }
            },
            "Head": _make_head(),
        }
        return self._json_response(payload)

    async def _handle_inverter_realtime(self, request: web.Request) -> web.Response:
        p_pv = max(self._power_watts * -1, 0.0)
        payload = {
            "Body": {
                "Data": {
                    "PAC": {"Value": round(p_pv, 1), "Unit": "W"},
                    "SAC": {"Value": round(p_pv, 1), "Unit": "VA"},
                    "DAY_ENERGY": {"Value": 0.0, "Unit": "Wh"},
                    "YEAR_ENERGY": {"Value": 0.0, "Unit": "Wh"},
                    "TOTAL_ENERGY": {"Value": 0.0, "Unit": "Wh"},
                }
            },
            "Head": _make_head(),
        }
        return self._json_response(payload)

    async def _handle_meter_realtime(self, request: web.Request) -> web.Response:
        power = self._power_watts
        current = power / 230.0

        meter_data: dict[str, Any] = {
            "Details": {
                "Manufacturer": "Fronius",
                "Model": "Smart Meter IP",
                "Serial": self._serial,
            },
            "Enable": 1,
            "TimeStamp": int(datetime.now(timezone.utc).timestamp()),
            "Meter_Location_Current": 0,
            "Visible": 1,
            "Frequency_Phase_Average": 50.0,
            "PowerReal_P_Sum": round(power, 1),
            "PowerReactive_Q_Sum": 0.0,
            "PowerApparent_S_Sum": round(abs(power), 1),
            "PowerFactor_Sum": 1.0 if power >= 0 else -1.0,
            "Current_AC_Sum": round(current, 2),
            "EnergyReal_WAC_Minus_Absolute": 0.0,
            "EnergyReal_WAC_Plus_Absolute": 0.0,
            "Current_AC_Phase_1": round(current, 2),
            "PowerReal_P_Phase_1": round(power, 1),
            "PowerReactive_Q_Phase_1": 0.0,
            "PowerApparent_S_Phase_1": round(abs(power), 1),
            "PowerFactor_Phase_1": 1.0 if power >= 0 else -1.0,
        }

        scope = request.rel_url.query.get("Scope", "System")
        device_id = request.rel_url.query.get("DeviceId", "0")
        request_args = {"DeviceClass": "Meter", "DeviceId": int(device_id), "Scope": scope}
        body_data = meter_data if scope == "Device" else {"0": meter_data}

        return self._json_response(
            {"Body": {"Data": body_data}, "Head": _make_head(request_arguments=request_args)}
        )

    async def _handle_storage_realtime(self, request: web.Request) -> web.Response:
        return self._json_response({"Body": {"Data": {}}, "Head": _make_head()})

    async def _handle_logger_info(self, request: web.Request) -> web.Response:
        payload = {
            "Body": {
                "LoggerInfo": {
                    "UniqueID": f"240.{self._system_name}",
                    "ProductID": "fronius-datamanager-card",
                    "PlatformID": "wilma",
                    "HWVersion": "1.4E",
                    "SWVersion": "3.4.0-102",
                    "DefaultLanguage": "de",
                    "Systemname": self._system_name,
                }
            },
            "Head": _make_head(),
        }
        return self._json_response(payload)

    async def _handle_unknown(self, request: web.Request) -> web.Response:
        _LOGGER.debug("Unknown Solar API request: %s", request.path)
        return self._json_response({"Body": {"Data": {}}, "Head": _make_head()})

    async def async_start(self) -> None:
        """Start the HTTP server."""
        runner = web.AppRunner(self._app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self._port)
        try:
            await site.start()
        except OSError as err:
            await runner.cleanup()
            raise OSError(
                f"Could not bind Solar API server to 0.0.0.0:{self._port} ({err})"
            ) from err
        self._runner = runner
        _LOGGER.info("Fronius Solar API emulator listening on port %s", self._port)

    async def async_stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
