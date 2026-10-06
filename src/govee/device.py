import json
import asyncio
import logging

from typing import Optional, Callable

from govee.shared import GoveeColor
from govee.messages import GoveeMessages, GoveeMessageType

logger = logging.getLogger("govee")

DEFAULT_COLOR_TEMP = 0

type GoveeMessageCallback = Callable[[GoveeDevice, dict]]


class GoveeDevice(asyncio.DatagramProtocol):
    loop: asyncio.AbstractEventLoop
    ip: Optional[str]
    device: Optional[str]
    sku: Optional[str]
    bleVersionHard: Optional[str]
    bleVersionSoft: Optional[str]
    wifiVersionHard: Optional[str]
    wifiVersionSoft: Optional[str]
    callbacks: dict[GoveeMessageType, list[GoveeMessageCallback]]
    powerState: bool
    brightness: int
    color: dict[str, int]
    retry_count: int
    transport: Optional[asyncio.DatagramTransport]

    def __init__(
        self,
        ip,
        device,
        sku,
        bleVersionHard,
        bleVersionSoft,
        wifiVersionHard,
        wifiVersionSoft,
    ):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.ip = ip
        self.device = device
        self.sku = sku
        self.bleVersionHard = bleVersionHard
        self.bleVersionSoft = bleVersionSoft
        self.wifiVersionHard = wifiVersionHard
        self.wifiVersionSoft = wifiVersionSoft

        self.transport = None
        self.task = None
        self.retry_count = 1
        self.powerState = False
        self.brightness = 100
        self.color = {}
        self.colorTemInKelvin: int = 0

        self.callbacks = {GoveeMessageType.Status: []}

    def __repr__(self):
        s = ""
        for key, value in self.__dict__.items():
            try:
                if key in {"loop", "task", "transport", "coro"}:
                    continue
                entry = f", {key}='{value}'"
                s += entry
            except:  # noqa: E722
                continue

        return f"{self.__class__}({s})"

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)

    def add_callback(
        self, message_type: GoveeMessageType, callback: GoveeMessageCallback
    ):
        self.callbacks[message_type].append(callback)

    def remove_callback(
        self, message_type: GoveeMessageType, callback: GoveeMessageCallback
    ):
        try:
            self.callbacks[message_type].remove(callback)
        except ValueError:
            pass

    def on_message_received(self, message_type: GoveeMessageType, data: dict):
        if message_type == GoveeMessageType.Status:
            self.on_status_received(data)
        callbacks = self.callbacks.get(message_type)
        if callbacks:
            for callback in callbacks:
                callback(self, data)

    def on_status_received(self, data: dict):
        if "onOff" in data:
            self.powerState = data["onOff"] == 1
        if "brightness" in data:
            self.brightness = data["brightness"]
        if "color" in data:
            self.color = data["color"]
        if "colorTemInKelvin" in data:
            self.colorTemInKelvin = data["colorTemInKelvin"]

    async def try_send(self, message, num_tries: Optional[int] = None):
        """coroutine used to send messages that don't need a response"""
        if isinstance(message, dict):
            message = json.dumps(message).encode("utf-8")

        if num_tries is None:
            num_tries = self.retry_count

        sent_msg_count = 0
        sleep_interval = 0.05
        while sent_msg_count < num_tries:
            if self.transport:
                self.transport.sendto(message)
            sent_msg_count += 1
            await asyncio.sleep(sleep_interval)

    def send(self, message, num_tries: Optional[int] = None):
        loop = self.loop or asyncio.get_event_loop()
        loop.create_task(self.try_send(message, num_tries))
        return True

    def toggle_power_state(self):
        logger.info(f"Toggling power state on '{self.ip}'")
        self.set_power_state(not self.powerState)

    def set_power_state(self, power_state: bool):
        logger.info(f"Setting power state on '{self.ip}' to {power_state}")
        message = GoveeMessages.power_state_message(power_state)
        self.send(message)
        self.powerState = power_state

    def set_brightness(self, brightness: int):
        logger.info(f"Setting brightness on '{self.ip}' to {brightness}")
        message = GoveeMessages.brightness_message(brightness)
        self.send(message)

    def set_color_and_temperature(
        self,
        rgb_color: Optional[GoveeColor] = None,
        temperature: Optional[int] = DEFAULT_COLOR_TEMP,
    ):
        logger.info(
            f"Setting color to (r={rgb_color.r}, g={rgb_color.g}, b={rgb_color.b}, temp={temperature}K) on '{self.ip}'"
        )
        message = GoveeMessages.color_message(rgb_color, temperature)
        self.send(message)

    def get_status(self):
        logger.info(f"Requesting device status for '{self.ip}'")
        message = GoveeMessages.status_query_message()
        self.send(message)

    # LIFECYCLE

    def connection_made(self, transport: asyncio.DatagramTransport):
        logger.debug(f"Connection established for device {self.device}")
        self.loop = asyncio.get_running_loop()
        self.transport = transport

    def connection_lost(self, exc):
        if exc:
            logger.error(f"ERROR: {exc}")
        self.cleanup()

    def cleanup(self):
        if self.transport:
            self.transport.close()
            self.transport = None
        if self.task:
            self.task.cancel()
            self.task = None
