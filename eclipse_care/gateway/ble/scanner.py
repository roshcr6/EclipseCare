"""Eclipse Care — BLE Scanner and Connection Manager.

Handles scanning for wearable devices, connecting, performing the 'bond' trick,
and subscribing to notifications.
"""

import asyncio
import struct
from collections.abc import Callable
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .framing import FrameAssembler, build_command, CommandNumber
from .decoder import PacketDecoder, SensorReading
from ..config import GatewayConfig

import structlog

logger = structlog.get_logger("ble.scanner")

class BLEScanner:
    """Manages BLE scanning, connection, and data routing for a single wearable."""
    
    # GATT characteristics (from WHOOP reference)
    CMD_WRITE_CHAR = "61080002-8d6d-82b8-614a-1c8cb0f8dcc6"
    CMD_NOTIFY_CHAR = "61080003-8d6d-82b8-614a-1c8cb0f8dcc6"
    EVENT_NOTIFY_CHAR = "61080004-8d6d-82b8-614a-1c8cb0f8dcc6"
    DATA_NOTIFY_CHAR = "61080005-8d6d-82b8-614a-1c8cb0f8dcc6"

    def __init__(self, config: GatewayConfig, target_mac: str | None = None):
        self.config = config
        self.target_mac = target_mac
        self.client: BleakClient | None = None
        
        # Callbacks
        self.on_reading: Callable[[SensorReading], None] | None = None
        self.on_disconnect: Callable[[], None] | None = None
        
        self.assembler = FrameAssembler()
        self.decoder: PacketDecoder | None = None
        self.is_connected = False
        
        self._disconnect_event = asyncio.Event()

    async def scan_and_connect(self) -> bool:
        """Scan for the device and attempt connection."""
        logger.info("Scanning for wearable", prefixes=self.config.ble_device_prefixes, target=self.target_mac)
        
        device_to_connect: BLEDevice | None = None
        
        def detection_callback(device: BLEDevice, adv: AdvertisementData):
            nonlocal device_to_connect
            if self.target_mac and device.address.upper() == self.target_mac.upper():
                device_to_connect = device
            elif not self.target_mac and device.name:
                for prefix in self.config.ble_device_prefixes:
                    if device.name.startswith(prefix):
                        device_to_connect = device
                        break

        scanner = BleakScanner(detection_callback)
        await scanner.start()
        await asyncio.sleep(self.config.ble_scan_window_sec)
        await scanner.stop()

        if not device_to_connect:
            logger.warning("No matching device found")
            return False

        logger.info("Found device", name=device_to_connect.name, address=device_to_connect.address)
        self.decoder = PacketDecoder(device_id=device_to_connect.address)
        
        return await self._connect(device_to_connect)

    async def _connect(self, device: BLEDevice) -> bool:
        self.client = BleakClient(
            device, 
            disconnected_callback=self._handle_disconnect
        )
        
        try:
            await self.client.connect()
            self.is_connected = True
            logger.info("Connected", address=device.address)
            
            # Subscriptions
            await self.client.start_notify(self.CMD_NOTIFY_CHAR, self._handle_notification)
            await self.client.start_notify(self.EVENT_NOTIFY_CHAR, self._handle_notification)
            await self.client.start_notify(self.DATA_NOTIFY_CHAR, self._handle_notification)
            
            # The Bonding Trick (FINDINGS.md §1)
            # CoreBluetooth / bleak requires a confirmed write to trigger bonding
            logger.info("Triggering bond...")
            bond_cmd = build_command(CommandNumber.GET_BATTERY_LEVEL)
            await self.client.write_gatt_char(self.CMD_WRITE_CHAR, bond_cmd, response=True)
            
            # Initial setup: Get clock, start raw data for IMU (falls)
            await asyncio.sleep(0.5)
            await self.client.write_gatt_char(
                self.CMD_WRITE_CHAR, build_command(CommandNumber.GET_CLOCK), response=True
            )
            
            # Start Raw Data (for accelerometer/fall detection)
            await asyncio.sleep(0.5)
            await self.client.write_gatt_char(
                self.CMD_WRITE_CHAR, build_command(CommandNumber.START_RAW_DATA), response=True
            )
            
            # Toggle Realtime HR
            await asyncio.sleep(0.5)
            await self.client.write_gatt_char(
                self.CMD_WRITE_CHAR, 
                build_command(CommandNumber.TOGGLE_REALTIME_HR, bytes([1])), 
                response=True
            )

            # Start RSSI Polling for Geofencing
            asyncio.create_task(self._poll_rssi())

            return True

        except Exception as e:
            logger.error("Connection failed", error=str(e))
            self.is_connected = False
            return False

    async def _poll_rssi(self):
        """Continuously poll RSSI to enable Geofencing tracking."""
        import time
        from .decoder import ReadingType, SensorReading
        while self.is_connected and self.client:
            try:
                # bleak exposes get_rssi on connected clients (or we can read it from scanner if unsupported on some platforms, but get_rssi is standard on bleak Mac/Win/Linux if implemented)
                rssi = await self.client.get_rssi()
                if self.on_reading:
                    self.on_reading(SensorReading(
                        device_id=self.client.address,
                        timestamp=time.time(),
                        reading_type=ReadingType.RSSI,
                        value=rssi
                    ))
            except Exception as e:
                pass
            await asyncio.sleep(2.0)

    def _handle_notification(self, sender: int, data: bytearray):
        """Handle incoming BLE notification data."""
        frames = self.assembler.feed(data)
        if not frames:
            return
            
        for frame in frames:
            if self.decoder:
                readings = self.decoder.decode(frame)
                for reading in readings:
                    if self.on_reading:
                        self.on_reading(reading)

    def _handle_disconnect(self, client: BleakClient):
        logger.info("Disconnected")
        self.is_connected = False
        self.assembler.reset()
        if self.on_disconnect:
            self.on_disconnect()
        self._disconnect_event.set()

    async def wait_until_disconnected(self):
        """Block until the device disconnects."""
        await self._disconnect_event.wait()

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
