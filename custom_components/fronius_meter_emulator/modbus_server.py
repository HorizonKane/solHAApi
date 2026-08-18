"""Fronius Smart Meter IP emulation via SunSpec Modbus TCP.

A raw asyncio TCP server implementing just enough of Modbus TCP (MBAP framing
+ Read Holding/Input Registers) to serve a SunSpec model 213 (three-phase
float) register block, so it needs no extra Modbus library and can't clash
with pymodbus versions pinned by other integrations (e.g. HA core's own
"modbus" integration).

Register layout ported from, and credit to,
https://github.com/l2smith2/fronius-virtual-inverter (MIT licensed), which
reverse-engineered a real Fronius Smart Meter IP's register map; cross-checked
against Fronius's own published "Smart Meter Register Map with Float AC-Meter
Model" document.

Sign convention: W positive = importing from the grid, negative = exporting
(this is the Fronius/SunSpec convention, matching P_Grid in the Solar API).
"""
from __future__ import annotations

import asyncio
import logging
import struct

_LOGGER = logging.getLogger(__name__)

SUNSPEC_SID = 0x53756E53  # 'SunS'
SUNSPEC_END = 0xFFFF

FC_READ_HOLDING = 0x03
FC_READ_INPUT = 0x04


class FroniusSmartMeterModbusServer:
    """Async Modbus TCP server emulating a Fronius Smart Meter IP."""

    def __init__(self, port: int, serial: str, unit_id: int = 240) -> None:
        self._port = port
        self._serial = serial
        self._unit_id = unit_id
        self._power_watts: float = 0.0
        self._server: asyncio.AbstractServer | None = None

    def update_power(self, watts: float) -> None:
        """Update the (signed) grid power value served to clients."""
        self._power_watts = watts

    async def async_start(self) -> None:
        """Start the Modbus TCP server."""
        try:
            self._server = await asyncio.start_server(
                self._handle_client, "0.0.0.0", self._port
            )
        except OSError as err:
            raise OSError(
                f"Could not bind Modbus TCP server to 0.0.0.0:{self._port} ({err})"
            ) from err
        _LOGGER.info(
            "Fronius Smart Meter IP Modbus server started on port %d (unit_id=%d)",
            self._port, self._unit_id,
        )

    async def async_stop(self) -> None:
        """Stop the Modbus TCP server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        _LOGGER.debug("Modbus client connected: %s", peer)
        try:
            while True:
                try:
                    header = await reader.readexactly(6)
                except (asyncio.IncompleteReadError, ConnectionResetError):
                    break

                transaction_id = (header[0] << 8) | header[1]
                length = (header[4] << 8) | header[5]

                try:
                    pdu = await reader.readexactly(length)
                except (asyncio.IncompleteReadError, ConnectionResetError):
                    break

                unit_id = pdu[0]
                func_code = pdu[1]

                if unit_id != self._unit_id:
                    continue

                if func_code in (FC_READ_HOLDING, FC_READ_INPUT) and len(pdu) >= 6:
                    start_addr = (pdu[2] << 8) | pdu[3]
                    count = (pdu[4] << 8) | pdu[5]
                    response_data = self._read_registers(start_addr, count)
                    byte_count = len(response_data)
                    resp_pdu = bytes([unit_id, func_code, byte_count]) + response_data
                    writer.write(self._mbap(transaction_id, resp_pdu))
                else:
                    exc_pdu = bytes([unit_id, func_code | 0x80, 0x01])
                    writer.write(self._mbap(transaction_id, exc_pdu))
                await writer.drain()
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.debug("Modbus client loop error: %s", err)
        finally:
            writer.close()
            _LOGGER.debug("Modbus client disconnected: %s", peer)

    def _mbap(self, transaction_id: int, pdu: bytes) -> bytes:
        return struct.pack(">HHH", transaction_id, 0, len(pdu)) + pdu

    def _read_registers(self, start_addr: int, count: int) -> bytes:
        registers = self._build_register_map()
        result = bytearray()
        for addr in range(start_addr, start_addr + count):
            result += registers.get(addr, b"\x00\x00")
        return bytes(result)

    def _build_register_map(self) -> dict[int, bytes]:
        """Build the complete SunSpec register map as {wire_address: 2_bytes}."""
        power = self._power_watts
        regs: dict[int, bytes] = {}

        def set_float(addr: int, value: float) -> None:
            raw = struct.pack(">f", float(value))
            regs[addr] = raw[0:2]
            regs[addr + 1] = raw[2:4]

        def set_uint16(addr: int, value: int) -> None:
            regs[addr] = struct.pack(">H", value & 0xFFFF)

        def set_uint32(addr: int, value: int) -> None:
            raw = struct.pack(">I", value & 0xFFFFFFFF)
            regs[addr] = raw[0:2]
            regs[addr + 1] = raw[2:4]

        def set_string(addr: int, text: str, num_regs: int) -> None:
            encoded = text.encode("ascii", errors="replace")
            padded = encoded[: num_regs * 2].ljust(num_regs * 2, b"\x00")
            for i in range(num_regs):
                regs[addr + i] = padded[i * 2 : i * 2 + 2]

        # ── Common block (register 40001 = wire address 40000) ──────────────
        set_uint32(40000, SUNSPEC_SID)
        set_uint16(40002, 1)   # ID = 1 (Common model)
        set_uint16(40003, 65)  # L = 65 registers
        set_string(40004, "Fronius", 16)
        set_string(40020, "Smart Meter IP", 16)
        set_string(40036, "1.0", 8)
        set_string(40044, "1.0.0", 8)
        set_string(40052, self._serial, 16)
        set_uint16(40068, self._unit_id)

        # ── Meter model 213 (three-phase, float) ─────────────────────────────
        set_uint16(40069, 213)
        set_uint16(40070, 124)

        per_phase_i = power / 3 / 230.0 if power != 0 else 0.0
        set_float(40071, per_phase_i * 3)
        set_float(40073, per_phase_i)
        set_float(40075, per_phase_i)
        set_float(40077, per_phase_i)

        set_float(40079, 230.0)
        set_float(40081, 230.0)
        set_float(40083, 230.0)
        set_float(40085, 230.0)
        set_float(40087, 400.0)
        set_float(40089, 400.0)
        set_float(40091, 400.0)
        set_float(40093, 400.0)

        set_float(40095, 50.0)  # Hz

        set_float(40097, power)       # W — the key register
        set_float(40099, power / 3)
        set_float(40101, power / 3)
        set_float(40103, power / 3)

        set_float(40105, abs(power))
        set_float(40107, abs(power) / 3)
        set_float(40109, abs(power) / 3)
        set_float(40111, abs(power) / 3)

        set_float(40113, 0.0)
        set_float(40115, 0.0)
        set_float(40117, 0.0)
        set_float(40119, 0.0)

        set_float(40121, 1.0)
        set_float(40123, 1.0)
        set_float(40125, 1.0)
        set_float(40127, 1.0)

        for addr in range(40129, 40161, 2):
            set_float(addr, 0.0)  # energy accumulators (Wh/VAh), not tracked
        for addr in range(40161, 40193, 2):
            set_float(addr, 0.0)  # VAr quadrant registers

        set_uint32(40193, 0)  # events

        set_uint16(40195, SUNSPEC_END)
        set_uint16(40196, 0)

        return regs
