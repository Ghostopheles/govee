import asyncio

from typing import Self

from govee.device import GoveeDevice
from govee.govee import GoveeConnectionListener

STATUS_GRACE = 1.0


class Govee:
    def __init__(self):
        self._listener: GoveeConnectionListener | None = None

    async def __aenter__(self) -> Self:
        self._listener = GoveeConnectionListener()
        await self._listener.start()
        return self

    async def __aexit__(self, *_) -> None:
        if self._listener:
            self._listener.cleanup()
            self._listener = None

    @property
    def devices(self) -> dict[str, GoveeDevice]:
        if self._listener is None:
            return {}
        return self._listener.devices

    async def wait_for_devices(
        self, timeout: float = 10.0
    ) -> list[GoveeDevice]:
        if self._listener is None:
            return []
        devices = await self._listener.wait_for_devices(timeout)
        device_list = sorted(devices.values(), key=lambda d: tuple(int(p) for p in (d.ip or "").split(".") if p.isdigit()))
        for device in device_list:
            device.get_status()
        await asyncio.sleep(STATUS_GRACE)
        return device_list

    @classmethod
    def discover(cls, timeout: float = 10.0) -> list[GoveeDevice]:
        async def _run():
            async with cls() as g:
                return await g.wait_for_devices(timeout)

        return asyncio.run(_run())
