"""HTTP server emulating a Fronius Datamanager's local Solar API.

Real Fronius devices (wallboxes, Ohmpilot, ...) that pull PV data from a
Datamanager on the local network do so via plain HTTP GET requests against the
"Solar API" (see https://www.fronius.com -> Solar API documentation). This
module serves the two endpoints most consumers use:

- /solar_api/GetAPIVersion.cgi
- /solar_api/v1/GetPowerFlowRealtimeData.fcgi

This is a best-effort reimplementation based on the public JSON schema, not
official Fronius software - if a device needs additional endpoints, extend
`_build_app` accordingly.
"""
from __future__ import annotations

import logging
from datetime import datetime

from aiohttp import web

from .const import API_VERSION_PATH, POWER_FLOW_PATH

_LOGGER = logging.getLogger(__name__)


class FroniusSolarApiServer:
    """Owns the aiohttp server and the current PV power value it reports."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._pv_watts: float = 0.0
        self._runner: web.AppRunner | None = None

    def update_pv_power(self, watts: float) -> None:
        """Update the PV power value served to clients."""
        self._pv_watts = watts

    def _build_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get(API_VERSION_PATH, self._handle_api_version)
        app.router.add_get(POWER_FLOW_PATH, self._handle_power_flow)
        return app

    async def _handle_api_version(self, request: web.Request) -> web.Response:
        return web.json_response({"APIVersion": 1, "BaseURL": "/solar_api/v1/"})

    async def _handle_power_flow(self, request: web.Request) -> web.Response:
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        return web.json_response(
            {
                "Head": {
                    "RequestArguments": {},
                    "Status": {"Code": 0, "Reason": "", "UserMessage": ""},
                    "Timestamp": timestamp,
                },
                "Body": {
                    "Data": {
                        "Site": {
                            "Mode": "meter",
                            "P_Grid": None,
                            "P_Load": None,
                            "P_Akku": None,
                            "P_PV": self._pv_watts,
                            "rel_Autonomy": None,
                            "rel_SelfConsumption": None,
                            "E_Day": None,
                            "E_Year": None,
                            "E_Total": None,
                            "Meter_Location": "grid",
                        },
                        "Inverters": {
                            "1": {"DT": 1, "P": self._pv_watts, "SOC": None}
                        },
                    }
                },
            }
        )

    async def async_start(self) -> None:
        """Start the HTTP server."""
        app = self._build_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        try:
            await site.start()
        except OSError as err:
            await runner.cleanup()
            raise OSError(
                f"Could not bind Solar API server to {self._host}:{self._port} "
                f"({err})"
            ) from err
        self._runner = runner
        _LOGGER.info(
            "Fronius Solar API emulator listening on %s:%s", self._host, self._port
        )

    async def async_stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
