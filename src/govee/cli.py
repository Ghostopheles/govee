import sys
import json
import asyncio
from typing import Annotated, Optional

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print(
        "CLI dependencies not installed. Install the 'cli' extra: "
        "uv add 'govee[cli] @ git+https://github.com/Ghostopheles/govee'",
        file=sys.stderr,
    )
    sys.exit(1)

from govee import Govee, GoveeColor, GoveeDevice

app = typer.Typer(
    name="govee",
    help="Control Govee lights over LAN.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err = Console(stderr=True)

NAMED_COLORS: dict[str, GoveeColor] = {
    "white": GoveeColor.white(),
    "red": GoveeColor.red(),
    "green": GoveeColor.green(),
    "blue": GoveeColor.blue(),
    "gold": GoveeColor.gold(),
    "purple": GoveeColor.purple(),
}

_DeviceArg = Annotated[
    Optional[str],
    typer.Argument(
        help="IP substring, SKU substring, or 1-based index. Omit for all."
    ),
]
_TimeoutOpt = Annotated[
    float,
    typer.Option("--timeout", "-t", help="Discovery timeout in seconds."),
]
_JsonOpt = Annotated[
    bool,
    typer.Option("--json", "-j", help="Output as JSON."),
]


def _device_to_dict(d: GoveeDevice) -> dict:
    return {
        "sku": d.sku,
        "ip": d.ip,
        "device": d.device,
        "power": d.powerState,
        "brightness": d.brightness,
        "color": d.color,
        "colorTemInKelvin": d.colorTemInKelvin,
    }


def _filter(
    devices: list[GoveeDevice], pattern: Optional[str]
) -> list[GoveeDevice]:
    if pattern is None:
        return devices
    try:
        idx = int(pattern)
        if 1 <= idx <= len(devices):
            return [devices[idx - 1]]
        err.print(f"[red]Index {idx} out of range (1–{len(devices)})[/red]")
        raise typer.Exit(1)
    except ValueError:
        pass
    lower = pattern.lower()
    matches = [
        d
        for d in devices
        if lower in (d.ip or "").lower() or lower in (d.sku or "").lower()
    ]
    if not matches:
        err.print(f"[red]No device matches '{pattern}'[/red]")
        raise typer.Exit(1)
    return matches


def _label(d: GoveeDevice) -> str:
    name = d.sku or d.device or d.ip or "unknown"
    return f"[yellow]{name}[/yellow] [[dim]{d.ip}[/dim]]"


def _color_str(color: dict, temp: int = 0) -> str:
    if not color:
        return ""
    r, g, b = color.get("r", 0), color.get("g", 0), color.get("b", 0)
    s = f"rgb({r},{g},{b})"
    if temp:
        s += f" {temp}K"
    return s


def _run(timeout: float, pattern: Optional[str], action):
    async def _inner():
        async with Govee() as g:
            devices = await g.wait_for_devices(timeout)
            if not devices:
                err.print("[yellow]No devices found on LAN.[/yellow]")
                raise typer.Exit(1)
            targets = _filter(devices, pattern)
            await action(targets)
            await asyncio.sleep(0.15)

    asyncio.run(_inner())


@app.command()
def discover(timeout: _TimeoutOpt = 3.0, as_json: _JsonOpt = False):
    """List all Govee devices found on the local network."""

    async def _show(devices: list[GoveeDevice]):
        if as_json:
            print(json.dumps([_device_to_dict(d) for d in devices], indent=2))
            return
        table = Table(title="[yellow]Govee Devices[/yellow]", show_lines=False)
        table.add_column("#", style="dim", width=3)
        table.add_column("SKU", style="yellow")
        table.add_column("IP Address", style="cyan")
        table.add_column("Power")
        table.add_column("Brightness")
        table.add_column("Color")
        for i, d in enumerate(devices, 1):
            table.add_row(
                str(i),
                d.sku or "-",
                d.ip or "-",
                "[green]on[/green]" if d.powerState else "[dim]off[/dim]",
                f"{d.brightness}%",
                _color_str(d.color, d.colorTemInKelvin),
            )
        console.print(table)

    _run(timeout, None, _show)


@app.command()
def status(
    device: _DeviceArg = None,
    timeout: _TimeoutOpt = 3.0,
    as_json: _JsonOpt = False,
):
    """Show current status of device(s)."""

    async def _show(devices: list[GoveeDevice]):
        if as_json:
            print(json.dumps([_device_to_dict(d) for d in devices], indent=2))
            return
        for d in devices:
            power = "[green]on[/green]" if d.powerState else "[dim]off[/dim]"
            parts = [_label(d), power, f"{d.brightness}%"]
            if d.color:
                parts.append(_color_str(d.color, d.colorTemInKelvin))
            console.print("  ".join(parts))

    _run(timeout, device, _show)


@app.command()
def on(device: _DeviceArg = None, timeout: _TimeoutOpt = 3.0):
    """Turn device(s) on."""

    async def _on(devices: list[GoveeDevice]):
        for d in devices:
            d.set_power_state(True)
            console.print(f"✓ {_label(d)} → [green]on[/green]")

    _run(timeout, device, _on)


@app.command()
def off(device: _DeviceArg = None, timeout: _TimeoutOpt = 3.0):
    """Turn device(s) off."""

    async def _off(devices: list[GoveeDevice]):
        for d in devices:
            d.set_power_state(False)
            console.print(f"✓ {_label(d)} → [dim]off[/dim]")

    _run(timeout, device, _off)


@app.command()
def toggle(device: _DeviceArg = None, timeout: _TimeoutOpt = 3.0):
    """Toggle power on device(s)."""

    async def _toggle(devices: list[GoveeDevice]):
        for d in devices:
            d.toggle_power_state()
            state = "[green]on[/green]" if d.powerState else "[dim]off[/dim]"
            console.print(f"✓ {_label(d)} → {state}")

    _run(timeout, device, _toggle)


@app.command()
def brightness(
    value: Annotated[int, typer.Argument(help="Brightness level 0-100.")],
    device: _DeviceArg = None,
    timeout: _TimeoutOpt = 3.0,
):
    """Set brightness of device(s)."""
    if not 0 <= value <= 100:
        err.print(f"[red]Brightness must be 0-100, got {value}[/red]")
        raise typer.Exit(1)

    async def _brightness(devices: list[GoveeDevice]):
        for d in devices:
            d.set_brightness(value)
            console.print(f"✓ {_label(d)} → brightness {value}%")

    _run(timeout, device, _brightness)


@app.command()
def color(
    value: Annotated[
        str,
        typer.Argument(help="Named color (red, white, gold…) or 'R,G,B'."),
    ],
    device: _DeviceArg = None,
    timeout: _TimeoutOpt = 3.0,
    temp: Annotated[
        int, typer.Option("--temp", help="Color temperature in Kelvin.")
    ] = 0,
):
    """Set color of device(s). Use a name or 'R,G,B' (e.g. '255,128,0')."""
    lower = value.lower().strip()
    if lower in NAMED_COLORS:
        gc = NAMED_COLORS[lower]
    else:
        parts = lower.split(",")
        if len(parts) != 3:
            err.print(
                f"[red]Color must be a name or 'R,G,B' — got '{value}'[/red]"
            )
            err.print(f"[dim]Named colors: {', '.join(NAMED_COLORS)}[/dim]")
            raise typer.Exit(1)
        try:
            r, g, b = (
                int(parts[0].strip()),
                int(parts[1].strip()),
                int(parts[2].strip()),
            )
        except ValueError:
            err.print(f"[red]Invalid RGB values: '{value}'[/red]")
            raise typer.Exit(1)
        if not all(0 <= c <= 255 for c in (r, g, b)):
            err.print("[red]RGB values must each be 0-255[/red]")
            raise typer.Exit(1)
        gc = GoveeColor(r, g, b)

    async def _color(devices: list[GoveeDevice]):
        for d in devices:
            d.set_color_and_temperature(gc, temp)
            console.print(f"✓ {_label(d)} → color rgb({gc.r},{gc.g},{gc.b})")

    _run(timeout, device, _color)


def main():
    app()
