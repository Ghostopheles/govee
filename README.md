# govee

LAN-only UDP controller for Govee smart lights. No cloud API, no account required — communicates directly with devices on your local network.

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Govee lights on the same LAN (tested with devices that support the local UDP API)

## Installation

```bash
# library only
uv add git+https://github.com/Ghostopheles/govee

# library + CLI
uv add 'govee[cli] @ git+https://github.com/Ghostopheles/govee'
```

Or install the CLI as a standalone tool:

```bash
uv tool install 'govee[cli] @ git+https://github.com/Ghostopheles/govee'
```

Or from source:

```bash
git clone https://github.com/Ghostopheles/govee.git
cd govee
uv sync
```

## CLI

Install with the `cli` extra (see [Installation](#installation)) to get the `govee` command, then:

```bash
govee --help
```

### Commands

```bash
govee discover                        # list all devices on LAN
govee status                          # show power/brightness/color for all devices
govee on                              # turn all devices on
govee off                             # turn all devices off
govee toggle                          # flip power on all devices
govee brightness 75                   # set brightness to 75%
govee color red                       # named color (white/red/green/blue/gold/purple)
govee color 255,128,0                 # custom RGB
govee color 255,128,0 --temp 4000     # RGB + color temperature in Kelvin
```

Target a specific device with an optional second argument — matches by 1-based index, IP substring, or SKU substring:

```bash
govee on 1                  # first discovered device
govee brightness 50 H6056   # any device whose SKU contains "H6056"
govee off 192.168.1.42      # exact or partial IP match
```

Discovery timeout defaults to 3 seconds. Override with `--timeout`:

```bash
govee discover --timeout 10
```

## Usage

### High-level (recommended)

**Async:**

```python
import asyncio
from govee import Govee, GoveeColor

async def main():
    async with Govee() as g:
        devices = await g.wait_for_devices(timeout=10)
        for device in devices:
            device.set_power_state(True)
            device.set_brightness(80)
            device.set_color_and_temperature(GoveeColor.red())

asyncio.run(main())
```

**Sync (blocking):**

```python
from govee import Govee, GoveeColor

devices = Govee.discover(timeout=10)
for device in devices:
    device.set_power_state(True)
    device.set_brightness(50)
    device.set_color_and_temperature(GoveeColor.white(), temperature=4000)
```

### Colors

`GoveeColor` has named constructors for common colors:

```python
GoveeColor.white()
GoveeColor.red()
GoveeColor.green()
GoveeColor.blue()
GoveeColor.gold()
GoveeColor.purple()

# Or construct directly:
GoveeColor(r=255, g=128, b=0)
```

### Device control

```python
device.set_power_state(True)          # on
device.set_power_state(False)         # off
device.toggle_power_state()           # flip current state
device.set_brightness(50)             # 0-100
device.set_color_and_temperature(GoveeColor.blue(), temperature=5000)
device.get_status()                   # requests a status update from the device
```

### Status callbacks

Device state (`powerState`, `brightness`, `color`) is automatically updated when status replies arrive. You can also register callbacks:

```python
from govee import GoveeMessageType

def on_status(device, data):
    print(f"{device.ip}: power={device.powerState}, brightness={device.brightness}")

device.add_callback(GoveeMessageType.Status, on_status)
device.remove_callback(GoveeMessageType.Status, on_status)
```

Callbacks fire after the device's internal state has already been updated, so reading `device.powerState` inside a callback reflects the new value.

### Low-level API

`GoveeConnectionListener` and `GoveeDevice` are available directly for use cases that need finer control:

```python
import asyncio
from govee import GoveeConnectionListener

async def main():
    listener = GoveeConnectionListener()
    await listener.start()
    devices = await listener.wait_for_devices(timeout=10)
    # ...
    listener.cleanup()

asyncio.run(main())
```

## Development

```bash
uv sync --all-groups   # install dev dependencies
uv run pytest          # run tests
```

## Network topology

| Direction | Address | Port |
|-----------|---------|------|
| Discovery broadcast (out) | `239.255.255.250` | `4001` |
| Device responses (in) | local LAN IP | `4002` |
| Commands (out, per device) | device IP | `4003` |

All packets are JSON: `{"msg": {"cmd": "<type>", "data": {...}}}`.
