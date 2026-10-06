import json
import socket
import asyncio
import logging

from govee.device import GoveeDevice
from govee.messages import GoveeMessages, GOVEE_INCOMING_MESSAGES
from govee.shared import (
    LISTEN_ADDR,
    LISTEN_PORT,
    BROADCAST_ADDR,
    BROADCAST_PORT,
    COMMAND_PORT,
)

logger = logging.getLogger("govee")

SCAN_MESSAGE = GoveeMessages.scan_message()

DISCOVERY_INTERVAL = 180
DISCOVERY_STEP = 5
DISCOVERY_GRACE = 2.0


class GoveeConnectionListener(asyncio.DatagramProtocol):
    loop: asyncio.AbstractEventLoop
    discovery_countdown: int
    discovery_complete: asyncio.Event
    devices: dict[str, GoveeDevice]

    transport = None

    def __init__(self):
        self.discovery_countdown = 0
        self.devices = {}
        self._discovery_grace_scheduled = False

    def start(self):
        self.loop = asyncio.get_running_loop()
        self.discovery_complete = asyncio.Event()
        coro = self.loop.create_datagram_endpoint(
            lambda: self, local_addr=(LISTEN_ADDR, LISTEN_PORT)
        )

        self.task = self.loop.create_task(coro)
        return self.task

    async def wait_for_devices(
        self, timeout: float | None = None
    ) -> dict[str, GoveeDevice]:
        await asyncio.wait_for(self.discovery_complete.wait(), timeout)
        return self.devices

    def discover(self):
        logger.info("Discovering...")
        if self.transport:
            if self.discovery_countdown <= 0:
                self.discovery_countdown = DISCOVERY_INTERVAL
                self.transport.sendto(
                    SCAN_MESSAGE, (BROADCAST_ADDR, BROADCAST_PORT)
                )
                if not self._discovery_grace_scheduled:
                    self._discovery_grace_scheduled = True
                    self.loop.call_later(
                        DISCOVERY_GRACE, self.discovery_complete.set
                    )
            else:
                self.discovery_countdown -= DISCOVERY_STEP
            self.loop.call_later(DISCOVERY_STEP, self.discover)

    def connection_lost(self, exc):
        logger.info("Connection closed.")
        if exc:
            self.error_received(exc)

    def connection_made(self, transport):
        logger.info("Connection made!")
        self.transport = transport

        sock: socket.socket = self.transport.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.loop.call_soon(self.discover)

    def datagram_received(self, data: bytes, addr):
        if not data:
            logger.warning("Response, but no data")
            return

        ip = addr[0]

        message = json.loads(data.decode("utf-8"))["msg"]
        message_type = message["cmd"]
        message_data = message["data"]
        if (
            message_type in GOVEE_INCOMING_MESSAGES
        ):  # reply from one of our requests, presumably
            device = self.devices.get(ip)
            if device is None:
                return
            device.on_message_received(message_type, message_data)
            return

        if "onOff" in message_data and "brightness" in message_data:
            logger.warning("Received mangled status response")
            return

        # probably the initial discovery response
        if ip not in self.devices:
            device = GoveeDevice.from_json(message_data)
            coro = self.loop.create_datagram_endpoint(
                lambda: device,
                family=socket.AF_INET,
                proto=socket.IPPROTO_UDP,
                remote_addr=(device.ip, COMMAND_PORT),
            )

            device.task = self.loop.create_task(coro)
            self.devices[ip] = device

    def error_received(self, exc):
        logger.error(f"ERROR: {exc}")

    def cleanup(self):
        if self.transport:
            self.transport.close()
            self.transport = None
        if self.task:
            self.task.cancel()
            self.task = None
        self.devices = {}
