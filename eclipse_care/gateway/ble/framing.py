"""Eclipse Care — BLE Protocol Framing.

Ported from WHOOP open-source reference (whoop_protocol/framing.py).
Handles: SOF detection, length parsing, CRC8/CRC32 validation, multi-fragment reassembly.

Reference: wearable/FINDINGS.md §3 — verified on-device.
Frame format:  [0xAA][len u16 LE][crc8(len)][type u8][seq u8][cmd u8][payload...][crc32 LE]
"""

import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum


# CRC-8 polynomial 0x07 (verified against WHOOP device, FINDINGS.md §3)
_CRC8_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c << 1) ^ 0x07 if _c & 0x80 else _c << 1
    _CRC8_TABLE.append(_c & 0xFF)


def crc8(data: bytes) -> int:
    """CRC-8 with poly 0x07 over the given bytes."""
    c = 0
    for b in data:
        c = _CRC8_TABLE[c ^ b]
    return c


def crc32_whoop(data: bytes) -> int:
    """Standard zlib CRC-32 (poly 0xEDB88320), matching WHOOP frames."""
    return zlib.crc32(data) & 0xFFFFFFFF


SOF = 0xAA
HEADER_SIZE = 4  # SOF(1) + length(2) + crc8(1)
TRAILER_SIZE = 4  # CRC32(4)


class PacketType(IntEnum):
    """BLE packet types from whoop_protocol.json — verified."""
    COMMAND = 35
    COMMAND_RESPONSE = 36
    REALTIME_DATA = 40
    REALTIME_RAW_DATA = 43
    HISTORICAL_DATA = 47
    EVENT = 48
    METADATA = 49
    CONSOLE_LOGS = 50
    REALTIME_IMU = 51


class EventNumber(IntEnum):
    """Device events — from whoop_protocol.json, verified on-device."""
    BATTERY_LEVEL = 3
    CHARGING_ON = 7
    CHARGING_OFF = 8
    WRIST_ON = 9
    WRIST_OFF = 10
    BLE_CONNECTION_UP = 11
    BLE_CONNECTION_DOWN = 12
    DOUBLE_TAP = 14
    BOOT = 15
    TEMPERATURE_LEVEL = 17
    BATTERY_PACK_CONNECTED = 21
    BATTERY_PACK_REMOVED = 22
    BLE_BONDED = 23
    EXTENDED_BATTERY_INFORMATION = 63


class CommandNumber(IntEnum):
    """Device commands — from whoop_protocol.json, verified on-device."""
    LINK_VALID = 1
    TOGGLE_REALTIME_HR = 3
    REPORT_VERSION_INFO = 7
    SET_CLOCK = 10
    GET_CLOCK = 11
    SEND_HISTORICAL_DATA = 22
    HISTORICAL_DATA_RESULT = 23
    GET_BATTERY_LEVEL = 26
    GET_DATA_RANGE = 34
    GET_HELLO_HARVARD = 35
    START_RAW_DATA = 81
    STOP_RAW_DATA = 82
    GET_EXTENDED_BATTERY_INFO = 98
    TOGGLE_IMU_MODE = 106
    ENABLE_OPTICAL_DATA = 107


@dataclass
class Frame:
    """A decoded BLE frame."""
    packet_type: int
    seq: int
    cmd: int
    payload: bytes
    raw: bytes  # full raw frame including header + trailer

    @property
    def type_name(self) -> str:
        try:
            return PacketType(self.packet_type).name
        except ValueError:
            return f"UNKNOWN({self.packet_type})"

    @property
    def data_len(self) -> int:
        """Length of the data portion (type+seq+cmd+payload), excluding CRC."""
        return len(self.payload) + 3  # +3 for type, seq, cmd bytes


class FrameAssembler:
    """Reassembles BLE notification fragments into complete frames.
    
    BLE notifications are limited to ~244 bytes (ATT MTU). Large packets
    (raw IMU/optical ~1920 bytes) arrive as multiple fragments. Only the 
    first fragment starts with SOF (0xAA). We buffer and reassemble.
    
    Reference: FINDINGS.md §3 — "BLE reassembly is mandatory"
    """

    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        """Feed raw BLE notification bytes; return any complete frames."""
        self._buffer.extend(data)
        frames = []
        while True:
            frame = self._try_extract()
            if frame is None:
                break
            frames.append(frame)
        return frames

    def _try_extract(self) -> Frame | None:
        """Try to extract one complete frame from the buffer."""
        # Find SOF
        try:
            sof_idx = self._buffer.index(SOF)
        except ValueError:
            self._buffer.clear()
            return None

        # Discard bytes before SOF
        if sof_idx > 0:
            del self._buffer[:sof_idx]

        # Need at least header
        if len(self._buffer) < HEADER_SIZE:
            return None

        # Parse length
        payload_len = struct.unpack_from("<H", self._buffer, 1)[0]
        header_crc = self._buffer[3]

        # Validate header CRC (CRC8 over the 2 length bytes)
        if crc8(self._buffer[1:3]) != header_crc:
            # Bad header — skip this SOF and try next
            del self._buffer[0]
            return None

        # Total frame size
        total_len = HEADER_SIZE + payload_len + TRAILER_SIZE
        if len(self._buffer) < total_len:
            return None  # Need more fragments

        # Extract frame bytes
        frame_bytes = bytes(self._buffer[:total_len])
        del self._buffer[:total_len]

        # Parse data portion (between header and CRC32 trailer)
        data = frame_bytes[HEADER_SIZE: HEADER_SIZE + payload_len]
        if len(data) < 3:
            return None

        # Validate CRC32 over data portion
        expected_crc = struct.unpack_from("<I", frame_bytes, HEADER_SIZE + payload_len)[0]
        actual_crc = crc32_whoop(data)
        if actual_crc != expected_crc:
            return None  # CRC mismatch — corrupted frame

        packet_type = data[0]
        seq = data[1]
        cmd = data[2] if len(data) > 2 else 0
        payload = data[3:] if len(data) > 3 else b""

        return Frame(
            packet_type=packet_type,
            seq=seq,
            cmd=cmd,
            payload=payload,
            raw=frame_bytes,
        )

    def reset(self):
        """Clear the buffer (e.g. on disconnect)."""
        self._buffer.clear()


def build_command(cmd: int, payload: bytes = b"") -> bytes:
    """Build a complete command frame to send to the wearable.
    
    Frame: [0xAA][len LE u16][crc8(len)][type=35][seq=0][cmd][payload][crc32 LE]
    """
    data = bytes([PacketType.COMMAND, 0, cmd]) + payload
    data_len = len(data)
    length_bytes = struct.pack("<H", data_len)
    header = bytes([SOF]) + length_bytes + bytes([crc8(length_bytes)])
    trailer = struct.pack("<I", crc32_whoop(data))
    return header + data + trailer
