import asyncio
import json
from unittest.mock import MagicMock

import pytest

from govee.govee import GoveeConnectionListener
from govee.messages import GoveeMessageType


def make_discovery_bytes(ip="192.168.1.100"):
    return json.dumps(
        {
            "msg": {
                "cmd": "scan",
                "data": {
                    "ip": ip,
                    "device": "H6001",
                    "sku": "H6001",
                    "bleVersionHard": "1.0",
                    "bleVersionSoft": "1.0",
                    "wifiVersionHard": "1.0",
                    "wifiVersionSoft": "1.0",
                },
            }
        }
    ).encode()


def make_status_bytes(on_off=1, brightness=80):
    return json.dumps(
        {
            "msg": {
                "cmd": "devStatus",
                "data": {
                    "onOff": on_off,
                    "brightness": brightness,
                    "color": {"r": 255, "g": 0, "b": 0},
                },
            }
        }
    ).encode()


def make_listener() -> GoveeConnectionListener:
    listener = GoveeConnectionListener()
    listener.loop = asyncio.get_running_loop()
    listener.discovery_complete = asyncio.Event()
    listener.transport = MagicMock()
    return listener


async def test_discovery_reply_adds_device():
    listener = make_listener()
    ip = "192.168.1.100"

    async def fake_endpoint(*args, **kwargs):
        return MagicMock(), MagicMock()

    listener.loop.create_datagram_endpoint = fake_endpoint  # type: ignore[method-assign]

    listener.datagram_received(make_discovery_bytes(ip), (ip, 4002))
    await asyncio.sleep(0)  # let the create_task coroutine run

    assert ip in listener.devices


async def test_status_reply_updates_device_and_fires_callback():
    listener = make_listener()
    ip = "192.168.1.101"

    async def fake_endpoint(*args, **kwargs):
        return MagicMock(), MagicMock()

    listener.loop.create_datagram_endpoint = fake_endpoint  # type: ignore[method-assign]

    listener.datagram_received(make_discovery_bytes(ip), (ip, 4002))
    await asyncio.sleep(0)

    device = listener.devices[ip]
    received = []
    device.add_callback(
        GoveeMessageType.Status, lambda d, data: received.append(d.powerState)
    )

    listener.datagram_received(
        make_status_bytes(on_off=1, brightness=50), (ip, 4002)
    )

    assert device.powerState is True
    assert device.brightness == 50
    assert received == [True]


async def test_status_reply_unknown_ip_no_exception():
    listener = make_listener()
    listener.datagram_received(make_status_bytes(), ("9.9.9.9", 4002))


async def test_discovery_complete_event_fires_after_grace(monkeypatch):
    import govee.govee as govee_module

    monkeypatch.setattr(govee_module, "DISCOVERY_GRACE", 0.01)

    listener = make_listener()
    listener.discover()

    await asyncio.wait_for(listener.discovery_complete.wait(), timeout=1.0)
    assert listener.discovery_complete.is_set()
