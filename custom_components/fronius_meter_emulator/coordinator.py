"""Data update coordinator polling the Fronius Solar API."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SOLAR_API_PATH

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class FroniusSolarApiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls GetPowerFlowRealtimeData.fcgi on the Fronius inverter/Datamanager."""

    def __init__(self, hass: HomeAssistant, host: str, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._host = host
        self._url = f"http://{host}{SOLAR_API_PATH}"

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with session.get(self._url) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except Exception as err:  # noqa: BLE001 - surfaced as UpdateFailed
            raise UpdateFailed(
                f"Error fetching Fronius Solar API data from {self._url}: {err}"
            ) from err

        try:
            site = payload["Body"]["Data"]["Site"]
        except (KeyError, TypeError) as err:
            raise UpdateFailed(
                f"Unexpected Fronius Solar API response: {payload}"
            ) from err

        def as_float(key: str) -> float:
            value = site.get(key)
            return float(value) if value is not None else 0.0

        return {
            "P_PV": as_float("P_PV"),
            "P_Grid": as_float("P_Grid"),
            "P_Load": as_float("P_Load"),
            "P_Akku": as_float("P_Akku"),
        }
