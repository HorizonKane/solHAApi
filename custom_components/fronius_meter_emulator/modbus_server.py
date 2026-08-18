"""Async Modbus TCP server emulating a Fronius Smart Meter."""
from __future__ import annotations

import logging

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import ModbusTcpServer

from .sunspec import BASE_ADDRESS, build_initial_registers, encode_meter_values

_LOGGER = logging.getLogger(__name__)

NOMINAL_PHASE_VOLTAGE = 230.0
NOMINAL_LL_VOLTAGE = 400.0
NOMINAL_FREQUENCY = 50.0


class FroniusSmartMeterServer:
    """Owns the Modbus TCP server and the live meter register values."""

    def __init__(
        self,
        host: str,
        port: int,
        serial_number: str,
    ) -> None:
        self._host = host
        self._port = port
        initial_values = build_initial_registers(serial_number)
        # pymodbus applies a +1 offset between the wire address a client requests and
        # the ModbusSequentialDataBlock's own addressing, so the block base must be
        # BASE_ADDRESS + 1 for a request for BASE_ADDRESS to return values[0].
        block = ModbusSequentialDataBlock(BASE_ADDRESS + 1, initial_values)
        slave_context = ModbusSlaveContext(hr=block, ir=block)
        self._context = ModbusServerContext(slaves=slave_context, single=True)
        self._server: ModbusTcpServer | None = None
        self.write_static_defaults()

    def write_static_defaults(self) -> None:
        """Fill in plausible constant values (voltage, frequency, power factor)."""
        self._write(
            {
                "avg_phase_voltage": NOMINAL_PHASE_VOLTAGE,
                "phase_a_voltage": NOMINAL_PHASE_VOLTAGE,
                "phase_b_voltage": NOMINAL_PHASE_VOLTAGE,
                "phase_c_voltage": NOMINAL_PHASE_VOLTAGE,
                "avg_ll_voltage": NOMINAL_LL_VOLTAGE,
                "phase_ab_voltage": NOMINAL_LL_VOLTAGE,
                "phase_bc_voltage": NOMINAL_LL_VOLTAGE,
                "phase_ca_voltage": NOMINAL_LL_VOLTAGE,
                "frequency": NOMINAL_FREQUENCY,
                "power_factor": 1.0,
                "phase_a_pf": 1.0,
                "phase_b_pf": 1.0,
                "phase_c_pf": 1.0,
            }
        )

    def update_power(self, net_watts: float) -> None:
        """Push a new net AC power reading, split evenly across the three phases.

        Sign convention (SunSpec/Modbus meter): positive = importing from the grid,
        negative = exporting to the grid.
        """
        phase_watts = net_watts / 3
        phase_current = phase_watts / NOMINAL_PHASE_VOLTAGE
        net_current = net_watts / NOMINAL_PHASE_VOLTAGE

        self._write(
            {
                "total_real_power": net_watts,
                "phase_a_watts": phase_watts,
                "phase_b_watts": phase_watts,
                "phase_c_watts": phase_watts,
                "apparent_power": abs(net_watts),
                "phase_a_va": abs(phase_watts),
                "phase_b_va": abs(phase_watts),
                "phase_c_va": abs(phase_watts),
                "net_ac_current": net_current,
                "phase_a_current": phase_current,
                "phase_b_current": phase_current,
                "phase_c_current": phase_current,
            }
        )

    def _write(self, readings: dict[str, float]) -> None:
        for address, regs in encode_meter_values(readings).items():
            self._context[0].setValues(3, address, regs)

    async def async_start(self) -> None:
        """Start the Modbus TCP server (listening in the background)."""
        server = ModbusTcpServer(self._context, address=(self._host, self._port))
        await server.serve_forever(background=True)
        if server.transport is None:
            # pymodbus swallows OSError (bind failures) internally and just logs a
            # warning, so we have to detect a failed bind ourselves.
            raise OSError(
                f"Could not bind Modbus TCP server to {self._host}:{self._port} "
                "(port already in use or insufficient permissions)"
            )
        self._server = server
        _LOGGER.info(
            "Fronius smart meter emulator listening on %s:%s", self._host, self._port
        )

    async def async_stop(self) -> None:
        """Stop the Modbus TCP server."""
        if self._server is not None:
            await self._server.shutdown()
            self._server = None
