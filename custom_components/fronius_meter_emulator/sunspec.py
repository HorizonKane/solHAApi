"""SunSpec register map helpers for emulating a Fronius Smart Meter (Modbus Map Model 213, float).

The register layout below mirrors what real Fronius devices (Datamanager, Ohmpilot,
wallboxes) expect when reading an external "Smart Meter via Modbus TCP" and matches a
proven third-party emulator (see README for details). All addresses are the raw
Modbus wire/PDU addresses (i.e. what a client passes as the "starting address" of a
read-holding-registers request) - Fronius devices address these directly as 4xxxx
numbers rather than translating them to a 0-based holding-register offset.
"""
from __future__ import annotations

import struct

# First and last wire address of the whole SunSpec block we serve.
BASE_ADDRESS = 40000
END_ADDRESS = 40196  # last register of the End-of-map model (id 0xFFFF, length 0)
BLOCK_LENGTH = END_ADDRESS - BASE_ADDRESS + 1

# Offsets (relative to BASE_ADDRESS) of the dynamic meter readings. Each value is an
# IEEE-754 float32 stored big-endian across two consecutive registers (high word
# first), per SunSpec "float" model convention.
METER_DATA_ADDRESS = 40071

METER_REGISTERS = [
    "net_ac_current",
    "phase_a_current",
    "phase_b_current",
    "phase_c_current",
    "avg_phase_voltage",
    "phase_a_voltage",
    "phase_b_voltage",
    "phase_c_voltage",
    "avg_ll_voltage",
    "phase_ab_voltage",
    "phase_bc_voltage",
    "phase_ca_voltage",
    "frequency",
    "total_real_power",
    "phase_a_watts",
    "phase_b_watts",
    "phase_c_watts",
    "apparent_power",
    "phase_a_va",
    "phase_b_va",
    "phase_c_va",
    "reactive_power",
    "phase_a_var",
    "phase_b_var",
    "phase_c_var",
    "power_factor",
    "phase_a_pf",
    "phase_b_pf",
    "phase_c_pf",
]

# address of each named register, 2 words each, in order starting at METER_DATA_ADDRESS
METER_REGISTER_ADDRESS = {
    name: METER_DATA_ADDRESS + i * 2 for i, name in enumerate(METER_REGISTERS)
}


def float_to_regs(value: float) -> tuple[int, int]:
    """Encode a float as (high_word, low_word) big-endian 16-bit registers."""
    raw = struct.pack(">f", float(value))
    high, low = struct.unpack(">HH", raw)
    return high, low


def string_to_regs(value: str, length_words: int) -> list[int]:
    """Encode an ASCII string into `length_words` registers (2 chars/register, null padded)."""
    data = value.encode("ascii", errors="replace")[: length_words * 2]
    data = data.ljust(length_words * 2, b"\x00")
    regs = []
    for i in range(0, len(data), 2):
        regs.append((data[i] << 8) | data[i + 1])
    return regs


def build_initial_registers(serial_number: str) -> list[int]:
    """Build the full static register block (BASE_ADDRESS..END_ADDRESS)."""
    values = [0] * BLOCK_LENGTH

    def set_regs(address: int, regs: list[int]) -> None:
        offset = address - BASE_ADDRESS
        values[offset : offset + len(regs)] = regs

    # "SunS" marker
    set_regs(40000, [0x5375, 0x6E53])

    # Common block (model 1), length 65
    set_regs(40002, [1, 65])
    set_regs(40004, string_to_regs("Fronius", 16))  # Manufacturer
    set_regs(40020, string_to_regs("Smart Meter 63A-3", 16))  # Model
    set_regs(40036, string_to_regs("", 8))  # Options
    set_regs(40044, string_to_regs("1", 8))  # Version
    set_regs(40052, string_to_regs(serial_number, 16))  # Serial number
    set_regs(40068, [1])  # Modbus device address

    # Meter block header (model 213, three-phase float), length 124
    set_regs(40069, [213, 124])

    # End model
    set_regs(40195, [0xFFFF, 0])

    return values


def encode_meter_values(readings: dict[str, float]) -> dict[int, list[int]]:
    """Encode a dict of {register_name: float value} into {address: [hi, lo]}."""
    result: dict[int, list[int]] = {}
    for name, value in readings.items():
        address = METER_REGISTER_ADDRESS[name]
        high, low = float_to_regs(value)
        result[address] = [high, low]
    return result
