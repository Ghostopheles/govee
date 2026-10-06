import socket

from dataclasses import dataclass

# trick to get this machine's LAN IP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    LISTEN_ADDR = s.getsockname()[0]
finally:
    s.close()

LISTEN_PORT = 4002
BROADCAST_ADDR = "239.255.255.250"
BROADCAST_PORT = 4001
COMMAND_PORT = 4003


def create_color(r: int, g: int, b: int) -> dict:
    return {"r": r, "g": g, "b": b}


@dataclass
class GoveeColor:
    r: int
    g: int
    b: int

    def to_bgr(self) -> int:
        return (self.b << 16) | (self.g << 8) | self.r

    def to_dict(self) -> dict:
        return create_color(self.r, self.g, self.b)

    @classmethod
    def white(cls):
        return cls(255, 255, 255)

    @classmethod
    def red(cls):
        return cls(255, 0, 0)

    @classmethod
    def green(cls):
        return cls(0, 255, 0)

    @classmethod
    def blue(cls):
        return cls(0, 0, 255)

    @classmethod
    def gold(cls):
        return cls(255, 215, 0)

    @classmethod
    def purple(cls):
        return cls(102, 36, 126)
