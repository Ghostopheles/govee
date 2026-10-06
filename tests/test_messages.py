import json

import pytest

from govee.messages import (
    GoveeMessageType,
    GoveeMessages,
    GOVEE_INCOMING_MESSAGES,
)


def decode(b: bytes) -> dict:
    return json.loads(b.decode())


def test_status_in_incoming_messages():
    assert GoveeMessageType.Status in GOVEE_INCOMING_MESSAGES


def test_power_state_message_no_shared_state():
    on_msg = decode(GoveeMessages.power_state_message(True))
    off_msg = decode(GoveeMessages.power_state_message(False))
    assert on_msg["msg"]["data"]["value"] is True
    assert off_msg["msg"]["data"]["value"] is False


def test_power_state_message_roundtrip():
    msg = decode(GoveeMessages.power_state_message(True))
    assert msg["msg"]["cmd"] == GoveeMessageType.Turn
    assert "value" in msg["msg"]["data"]


def test_brightness_message_roundtrip():
    msg = decode(GoveeMessages.brightness_message(75))
    assert msg["msg"]["cmd"] == GoveeMessageType.Brightness
    assert msg["msg"]["data"]["value"] == 75


def test_brightness_message_no_shared_state():
    msg_a = decode(GoveeMessages.brightness_message(10))
    msg_b = decode(GoveeMessages.brightness_message(90))
    assert msg_a["msg"]["data"]["value"] == 10
    assert msg_b["msg"]["data"]["value"] == 90


def test_status_query_message_roundtrip():
    msg = decode(GoveeMessages.status_query_message())
    assert msg["msg"]["cmd"] == GoveeMessageType.Status


def test_scan_message_roundtrip():
    msg = decode(GoveeMessages.scan_message())
    assert msg["msg"]["cmd"] == GoveeMessageType.Scan
    assert msg["msg"]["data"]["account_topic"] == "reserve"


def test_color_message_roundtrip():
    from govee.shared import GoveeColor

    msg = decode(GoveeMessages.color_message(GoveeColor.red(), 4000))
    assert msg["msg"]["cmd"] == GoveeMessageType.Color
    assert msg["msg"]["data"]["color"] == {"r": 255, "g": 0, "b": 0}
    assert msg["msg"]["data"]["colorTemInKelvin"] == 4000


def test_color_message_no_shared_state():
    from govee.shared import GoveeColor

    msg_a = decode(GoveeMessages.color_message(GoveeColor.red(), 3000))
    msg_b = decode(GoveeMessages.color_message(GoveeColor.blue(), 6000))
    assert msg_a["msg"]["data"]["color"]["r"] == 255
    assert msg_b["msg"]["data"]["color"]["b"] == 255
    assert msg_a["msg"]["data"]["colorTemInKelvin"] == 3000
    assert msg_b["msg"]["data"]["colorTemInKelvin"] == 6000
