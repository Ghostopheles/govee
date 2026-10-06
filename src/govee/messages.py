import json

from enum import StrEnum
from typing import Optional

from govee.shared import GoveeColor


class GoveeMessageType(StrEnum):
    Scan = "scan"
    Turn = "turn"
    Status = "devStatus"
    Brightness = "brightness"
    Color = "colorwc"


class GoveeMessages:
    @staticmethod
    def scan_message() -> bytes:
        return json.dumps(
            {
                "msg": {
                    "cmd": GoveeMessageType.Scan,
                    "data": {"account_topic": "reserve"},
                }
            }
        ).encode()

    @staticmethod
    def power_state_message(power_state: bool) -> bytes:
        return json.dumps(
            {
                "msg": {
                    "cmd": GoveeMessageType.Turn,
                    "data": {"value": power_state},
                }
            }
        ).encode()

    @staticmethod
    def status_query_message() -> bytes:
        return json.dumps(
            {"msg": {"cmd": GoveeMessageType.Status, "data": {}}}
        ).encode()

    @staticmethod
    def brightness_message(brightness: int) -> bytes:
        return json.dumps(
            {
                "msg": {
                    "cmd": GoveeMessageType.Brightness,
                    "data": {"value": brightness},
                }
            }
        ).encode()

    @staticmethod
    def color_message(
        rgb_color: Optional[GoveeColor], temperature: Optional[int]
    ) -> bytes:
        data: dict = {}
        if rgb_color:
            data["color"] = rgb_color.to_dict()
        if temperature:
            data["colorTemInKelvin"] = temperature
        return json.dumps(
            {"msg": {"cmd": GoveeMessageType.Color, "data": data}}
        ).encode()


GOVEE_INCOMING_MESSAGES = frozenset({GoveeMessageType.Status})
