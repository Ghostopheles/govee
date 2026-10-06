import pytest

from govee.device import GoveeDevice
from govee.messages import GoveeMessageType


def make_device(**kwargs) -> GoveeDevice:
    defaults = dict(
        ip="1.2.3.4",
        device="H6001",
        sku="H6001",
        bleVersionHard="1.0",
        bleVersionSoft="1.0",
        wifiVersionHard="1.0",
        wifiVersionSoft="1.0",
    )
    defaults.update(kwargs)
    return GoveeDevice(**defaults)


def test_color_instances_are_independent():
    a = make_device(ip="1.1.1.1")
    b = make_device(ip="2.2.2.2")
    a.color["r"] = 99
    assert "r" not in b.color


def test_default_power_state_is_false_bool():
    d = make_device()
    assert d.powerState is False
    assert isinstance(d.powerState, bool)


def test_default_color_is_empty_dict():
    d = make_device()
    assert d.color == {}
    assert isinstance(d.color, dict)


def test_default_brightness():
    d = make_device()
    assert d.brightness == 100


def test_on_status_received_updates_fields():
    d = make_device()
    d.on_status_received(
        {"onOff": 1, "brightness": 50, "color": {"r": 10, "g": 20, "b": 30}}
    )
    assert d.powerState is True
    assert d.brightness == 50
    assert d.color == {"r": 10, "g": 20, "b": 30}


def test_on_status_received_off():
    d = make_device()
    d.powerState = True
    d.on_status_received({"onOff": 0})
    assert d.powerState is False


def test_on_status_received_partial_does_not_overwrite():
    d = make_device()
    d.brightness = 77
    d.color = {"r": 1, "g": 2, "b": 3}
    d.on_status_received({"onOff": 1})
    assert d.brightness == 77
    assert d.color == {"r": 1, "g": 2, "b": 3}


def test_on_message_received_status_updates_state_then_callback():
    d = make_device()
    order = []

    def cb(device, data):
        order.append(("callback", device.powerState))

    d.add_callback(GoveeMessageType.Status, cb)
    d.on_message_received(
        GoveeMessageType.Status, {"onOff": 1, "brightness": 80}
    )

    assert d.powerState is True
    assert order == [("callback", True)]


def test_remove_callback():
    d = make_device()
    called = []
    cb = lambda dev, data: called.append(1)
    d.add_callback(GoveeMessageType.Status, cb)
    d.remove_callback(GoveeMessageType.Status, cb)
    d.on_message_received(GoveeMessageType.Status, {"onOff": 1})
    assert called == []
