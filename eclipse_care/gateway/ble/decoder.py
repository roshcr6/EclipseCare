"""Eclipse Care — BLE Packet Decoder.

Decodes raw BLE frames into structured sensor readings for elderly monitoring.
Ported from WHOOP reference (interpreter.py) — adapted for elderly care.

We decode:
  - Heart Rate + R-R intervals (realtime + historical)
  - Battery status (SOC %, voltage, charging)
  - Device events (wrist on/off, charging, bonding)
  - Accelerometer (X/Y/Z) — used for fall detection
  - Gyroscope (X/Y/Z) — used for fall detection
  - Historical biometrics (HR, SpO2 raw, skin temp raw, respiration raw, gravity)
  
We do NOT decode (athlete-only, irrelevant to elderly care):
  - Recovery score
  - Strain score  
  - Sleep stage scoring (athlete-style)
  - Workout detection
  - Calorie estimation
"""

import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .framing import Frame, PacketType, EventNumber, CommandNumber


class ReadingType(str, Enum):
    """Types of sensor readings we produce."""
    HEART_RATE = "heart_rate"
    RR_INTERVAL = "rr_interval"
    BATTERY = "battery"
    EVENT = "event"
    ACCELEROMETER = "accel"
    GYROSCOPE = "gyro"
    SPO2_RAW = "spo2_raw"
    SKIN_TEMP_RAW = "skin_temp_raw"
    RESPIRATION_RAW = "resp_raw"
    GRAVITY = "gravity"
    SKIN_CONTACT = "skin_contact"
    DEVICE_INFO = "device_info"
    RSSI = "rssi"


@dataclass
class SensorReading:
    """A single decoded sensor reading from the wearable."""
    device_id: str
    reading_type: ReadingType
    timestamp: float           # Unix timestamp (seconds)
    value: Any                 # Type depends on reading_type
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "type": self.reading_type.value,
            "ts": self.timestamp,
            "value": self.value,
            "meta": self.metadata,
        }


class PacketDecoder:
    """Decodes BLE frames into SensorReading objects.
    
    Reference: FINDINGS.md §5 (decoded data streams), whoop_protocol.json
    
    Clock correlation: The WHOOP device uses its own epoch (~31.5M ticks).
    Historical data (type 47) carries real Unix timestamps.
    Realtime data (type 40) uses device epoch — we correlate at connect time.
    """

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._clock_offset: float | None = None  # wall_time - device_time

    def set_clock_correlation(self, device_time: int, wall_time: float):
        """Set the mapping from device epoch to wall clock.
        Called after GET_CLOCK response is received.
        """
        self._clock_offset = wall_time - device_time

    def _device_to_unix(self, device_ts: int) -> float:
        """Convert device epoch timestamp to Unix timestamp."""
        if self._clock_offset is not None:
            return device_ts + self._clock_offset
        return time.time()  # fallback: use current time

    def decode(self, frame: Frame) -> list[SensorReading]:
        """Decode a frame into zero or more sensor readings."""
        ptype = frame.packet_type

        if ptype == PacketType.REALTIME_DATA:
            return self._decode_realtime(frame)
        elif ptype == PacketType.REALTIME_RAW_DATA:
            return self._decode_raw(frame)
        elif ptype == PacketType.HISTORICAL_DATA:
            return self._decode_historical(frame)
        elif ptype == PacketType.EVENT:
            return self._decode_event(frame)
        elif ptype == PacketType.COMMAND_RESPONSE:
            return self._decode_command_response(frame)
        else:
            return []

    def _decode_realtime(self, frame: Frame) -> list[SensorReading]:
        """Decode realtime HR data (type 40, 24-byte packet).
        
        Reference: FINDINGS.md §5
        Layout: [4:8]=device_epoch, [8:10]=subsec, [14]=heartRate, [15]=rr_count, [16:24]=R-R intervals
        NOTE: offsets are relative to frame.payload (after type/seq/cmd stripped by framing)
        """
        readings = []
        data = frame.payload  # payload starts after cmd byte
        if len(data) < 18:
            return readings

        # Offsets relative to payload (frame.payload = data after [type][seq][cmd])
        # In the raw frame: type@0, seq@1, cmd@2, then data[0] = frame byte 3
        # FINDINGS: data[0:4]=record_hdr, [4:8]=device_epoch, [8:10]=subsec
        # But our frame strips type/seq, keeps cmd+payload. cmd=data[0], real payload starts at data[0]
        # Let's use the schema offsets relative to the full data portion:
        # Full data = [type(1)][seq(1)][cmd(1)][payload...]
        # Schema offsets are from data[0] = type byte
        # In our Frame: cmd is already extracted, payload is after cmd
        # So schema_offset 6 = our_offset 3 (type=0,seq=1,cmd=2 are stripped, so off-3)
        
        # Reconstruct full data for offset compatibility
        full_data = bytes([frame.packet_type, frame.seq, frame.cmd]) + frame.payload
        
        if len(full_data) < 16:
            return readings

        device_ts = struct.unpack_from("<I", full_data, 6)[0]
        ts = self._device_to_unix(device_ts)

        heart_rate = full_data[12]
        if heart_rate > 0 and heart_rate < 250:
            readings.append(SensorReading(
                device_id=self.device_id,
                reading_type=ReadingType.HEART_RATE,
                timestamp=ts,
                value=heart_rate,
                metadata={"source": "realtime"},
            ))

        rr_count = full_data[13] if len(full_data) > 13 else 0
        for i in range(min(rr_count, 4)):
            off = 14 + i * 2
            if off + 2 <= len(full_data):
                rr_ms = struct.unpack_from("<H", full_data, off)[0]
                if 200 < rr_ms < 2000:  # physiological range
                    readings.append(SensorReading(
                        device_id=self.device_id,
                        reading_type=ReadingType.RR_INTERVAL,
                        timestamp=ts + (i * 0.001),  # sub-ms offset
                        value=rr_ms,
                    ))

        return readings

    def _decode_raw(self, frame: Frame) -> list[SensorReading]:
        """Decode raw IMU data (type 43, 1917-byte = IMU variant).
        
        Reference: FINDINGS.md §6, whoop_protocol.json variants.1917
        VERIFIED layout: 100 samples/axis, signed int16 LE
          accelX @ frame_offset 89,  accelY @ 289, accelZ @ 489
          gyroX  @ frame_offset 692, gyroY  @ 892, gyroZ  @ 1092
        Scale: accel 1/4096 g/LSB, gyro 2000/32768 deg/s/LSB
        """
        readings = []
        full_data = bytes([frame.packet_type, frame.seq, frame.cmd]) + frame.payload
        data_len = len(full_data)

        if data_len < 100:
            return readings

        # Timestamp
        device_ts = struct.unpack_from("<I", full_data, 7)[0]
        ts = self._device_to_unix(device_ts)

        # HR from raw packet header
        if data_len > 21:
            hr = full_data[21]
            if 0 < hr < 250:
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.HEART_RATE,
                    timestamp=ts,
                    value=hr,
                    metadata={"source": "raw"},
                ))

        # IMU variant (1917 bytes) — frame offsets from FINDINGS.md
        # Our full_data starts at frame byte 4 (after SOF+len+crc8)
        # Protocol schema uses "frame offset" = absolute from SOF
        # full_data offset = frame_offset - 4 (HEADER_SIZE)
        # But looking at the schema: the offsets in variants.1917 are listed as
        # "frame offset" e.g. accelX @ 89. Since our full_data = [type,seq,cmd,payload]
        # and in the actual frame: [SOF,len_lo,len_hi,crc8, type,seq,cmd,payload,crc32]
        # full_data offset = frame_offset - HEADER_SIZE = frame_offset - 4
        # So accelX data starts at full_data[89-4] = full_data[85]
        
        # Actually, re-reading the schema more carefully:
        # whoop_protocol.json: axes: [["accelX", 89, "accel"], ...] — these are FRAME offsets
        # Frame = [SOF(1)][len(2)][crc8(1)][data(payload_len)][crc32(4)]
        # data = [type(1)][seq(1)][payload...]
        # So data[0] = type, which is at frame offset 4
        # Therefore: data_offset = frame_offset - 4
        # accelX starts at data_offset = 89 - 4 = 85
        
        accel_scale = 1.0 / 4096.0  # LSB to g (verified: FINDINGS.md)
        gyro_scale = 2000.0 / 32768.0  # LSB to deg/s (verified: FINDINGS.md)
        
        num_samples = 100
        
        if data_len >= 1917 - 4:  # 1917 is full frame data len
            # Extract IMU samples for fall detection
            # We extract the LATEST sample (last of 100) for real-time monitoring
            # and compute aggregate stats for the full packet
            
            accel_offsets = {"x": 85, "y": 285, "z": 485}
            gyro_offsets = {"x": 688, "y": 888, "z": 1088}
            
            accel_samples = {"x": [], "y": [], "z": []}
            gyro_samples = {"x": [], "y": [], "z": []}
            
            for axis in ("x", "y", "z"):
                a_off = accel_offsets[axis]
                g_off = gyro_offsets[axis]
                for s in range(num_samples):
                    idx_a = a_off + s * 2
                    idx_g = g_off + s * 2
                    if idx_a + 2 <= data_len:
                        raw_a = struct.unpack_from("<h", full_data, idx_a)[0]
                        accel_samples[axis].append(raw_a * accel_scale)
                    if idx_g + 2 <= data_len:
                        raw_g = struct.unpack_from("<h", full_data, idx_g)[0]
                        gyro_samples[axis].append(raw_g * gyro_scale)
            
            if accel_samples["x"]:
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.ACCELEROMETER,
                    timestamp=ts,
                    value={
                        "x": accel_samples["x"],
                        "y": accel_samples["y"],
                        "z": accel_samples["z"],
                    },
                    metadata={"samples": len(accel_samples["x"]), "unit": "g"},
                ))
            
            if gyro_samples["x"]:
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.GYROSCOPE,
                    timestamp=ts,
                    value={
                        "x": gyro_samples["x"],
                        "y": gyro_samples["y"],
                        "z": gyro_samples["z"],
                    },
                    metadata={"samples": len(gyro_samples["x"]), "unit": "deg/s"},
                ))

        return readings

    def _decode_historical(self, frame: Frame) -> list[SensorReading]:
        """Decode historical biometric data (type 47, V24 variant).
        
        Reference: whoop_protocol.json HISTORICAL_DATA.versions.24
        These carry REAL Unix timestamps and the full sensor suite.
        Frame offsets from the schema (FRAME-absolute, meaning from SOF byte).
        """
        readings = []
        # Reconstruct the full frame data for offset compatibility
        full_data = bytes([frame.packet_type, frame.seq, frame.cmd]) + frame.payload

        version = frame.seq  # seq byte = version for type-47
        
        if version not in (24, 12, 5, 7, 9):
            return readings

        # All versions have unix timestamp at frame offset 11 = data offset 7
        if len(full_data) < 12:
            return readings

        unix_ts = struct.unpack_from("<I", full_data, 7)[0]
        ts = float(unix_ts)

        # HR at frame offset 21 = data offset 17
        if len(full_data) > 17:
            hr = full_data[17]
            if 0 < hr < 250:
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.HEART_RATE,
                    timestamp=ts,
                    value=hr,
                    metadata={"source": "historical", "version": version},
                ))

        # RR intervals (frame offset 23 = data offset 19)
        if len(full_data) > 18:
            rr_count = full_data[18]
            for i in range(min(rr_count, 4)):
                off = 19 + i * 2
                if off + 2 <= len(full_data):
                    rr_ms = struct.unpack_from("<H", full_data, off)[0]
                    if 200 < rr_ms < 2000:
                        readings.append(SensorReading(
                            device_id=self.device_id,
                            reading_type=ReadingType.RR_INTERVAL,
                            timestamp=ts + (i * 0.001),
                            value=rr_ms,
                        ))

        # V24/V12 have extended biometrics
        if version in (24, 12) and len(full_data) > 78:
            # SpO2 raw ADC — frame offset 68,70 = data offset 64,66
            spo2_red = struct.unpack_from("<H", full_data, 64)[0]
            spo2_ir = struct.unpack_from("<H", full_data, 66)[0]
            if spo2_red > 0 or spo2_ir > 0:
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.SPO2_RAW,
                    timestamp=ts,
                    value={"red": spo2_red, "ir": spo2_ir},
                ))

            # Skin temperature raw ADC — frame offset 72 = data offset 68
            temp_raw = struct.unpack_from("<H", full_data, 68)[0]
            if temp_raw > 0:
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.SKIN_TEMP_RAW,
                    timestamp=ts,
                    value=temp_raw,
                ))

            # Respiration rate raw — frame offset 80 = data offset 76
            if len(full_data) > 77:
                resp_raw = struct.unpack_from("<H", full_data, 76)[0]
                if resp_raw > 0:
                    readings.append(SensorReading(
                        device_id=self.device_id,
                        reading_type=ReadingType.RESPIRATION_RAW,
                        timestamp=ts,
                        value=resp_raw,
                    ))

            # Gravity vector — frame offsets 40-52 = data offsets 36-48
            if len(full_data) > 48:
                gx = struct.unpack_from("<f", full_data, 36)[0]
                gy = struct.unpack_from("<f", full_data, 40)[0]
                gz = struct.unpack_from("<f", full_data, 44)[0]
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.GRAVITY,
                    timestamp=ts,
                    value={"x": gx, "y": gy, "z": gz},
                    metadata={"unit": "g"},
                ))

            # Skin contact — frame offset 55 = data offset 51
            if len(full_data) > 51:
                skin_contact = full_data[51]
                readings.append(SensorReading(
                    device_id=self.device_id,
                    reading_type=ReadingType.SKIN_CONTACT,
                    timestamp=ts,
                    value=skin_contact != 0,
                ))

        return readings

    def _decode_event(self, frame: Frame) -> list[SensorReading]:
        """Decode device events (type 48).
        
        Reference: whoop_protocol.json EVENT, FINDINGS.md §5
        """
        readings = []
        full_data = bytes([frame.packet_type, frame.seq, frame.cmd]) + frame.payload

        if len(full_data) < 8:
            return readings

        event_num = full_data[6] if len(full_data) > 6 else 0
        event_ts = struct.unpack_from("<I", full_data, 8)[0] if len(full_data) > 11 else 0

        try:
            event_name = EventNumber(event_num).name
        except ValueError:
            event_name = f"UNKNOWN_{event_num}"

        ts = self._device_to_unix(event_ts) if event_ts > 0 else time.time()

        event_data: dict[str, Any] = {"event": event_name, "event_num": event_num}

        # Battery event: SOC at payload offset 1 (uint16/10), mV at offset 5
        if event_num == EventNumber.BATTERY_LEVEL and len(frame.payload) >= 7:
            soc_raw = struct.unpack_from("<H", frame.payload, 1)[0]
            mv = struct.unpack_from("<H", frame.payload, 5)[0]
            event_data["soc_pct"] = soc_raw / 10.0
            event_data["voltage_mv"] = mv
            
            readings.append(SensorReading(
                device_id=self.device_id,
                reading_type=ReadingType.BATTERY,
                timestamp=ts,
                value=soc_raw / 10.0,
                metadata={"voltage_mv": mv, "source": "event"},
            ))

        # Wrist on/off — critical for elderly (device removed alert)
        if event_num in (EventNumber.WRIST_ON, EventNumber.WRIST_OFF):
            readings.append(SensorReading(
                device_id=self.device_id,
                reading_type=ReadingType.SKIN_CONTACT,
                timestamp=ts,
                value=event_num == EventNumber.WRIST_ON,
            ))

        readings.append(SensorReading(
            device_id=self.device_id,
            reading_type=ReadingType.EVENT,
            timestamp=ts,
            value=event_data,
        ))

        return readings

    def _decode_command_response(self, frame: Frame) -> list[SensorReading]:
        """Decode command responses (type 36).
        
        We care about:
          - GET_BATTERY_LEVEL (26): uint16/10 = SOC %
          - GET_HELLO_HARVARD (35): serial, charging flag, isWorn
          - GET_CLOCK (11): device clock for correlation
          - GET_EXTENDED_BATTERY_INFO (98): voltage in mV
        """
        readings = []
        full_data = bytes([frame.packet_type, frame.seq, frame.cmd]) + frame.payload

        if len(full_data) < 7:
            return readings

        resp_cmd = full_data[6]
        payload = frame.payload

        # Verify response status: payload[0]=0x0a, payload[1]=status (01=ok)
        if len(payload) < 2:
            return readings

        # GET_BATTERY_LEVEL response: SOC = uint16 LE / 10
        if resp_cmd == CommandNumber.GET_BATTERY_LEVEL and len(payload) >= 5:
            soc_raw = struct.unpack_from("<H", payload, 3)[0]
            readings.append(SensorReading(
                device_id=self.device_id,
                reading_type=ReadingType.BATTERY,
                timestamp=time.time(),
                value=soc_raw / 10.0,
                metadata={"source": "command_response"},
            ))

        # GET_CLOCK response: device epoch for clock correlation
        if resp_cmd == CommandNumber.GET_CLOCK and len(payload) >= 7:
            device_time = struct.unpack_from("<I", payload, 3)[0]
            self.set_clock_correlation(device_time, time.time())

        # GET_HELLO_HARVARD: charging flag at byte 7, isWorn at byte 116
        if resp_cmd == CommandNumber.GET_HELLO_HARVARD and len(payload) >= 8:
            charging = payload[7] != 0
            is_worn = payload[116] != 0 if len(payload) > 116 else None
            readings.append(SensorReading(
                device_id=self.device_id,
                reading_type=ReadingType.DEVICE_INFO,
                timestamp=time.time(),
                value={"charging": charging, "is_worn": is_worn},
            ))

        # GET_EXTENDED_BATTERY_INFO: voltage at payload[7:9]
        if resp_cmd == CommandNumber.GET_EXTENDED_BATTERY_INFO and len(payload) >= 9:
            voltage_mv = struct.unpack_from("<H", payload, 7)[0]
            readings.append(SensorReading(
                device_id=self.device_id,
                reading_type=ReadingType.BATTERY,
                timestamp=time.time(),
                value=None,
                metadata={"voltage_mv": voltage_mv, "source": "extended_battery"},
            ))

        return readings
