"""Convert Senxor thermal imaging stream to a virtual camera (Windows, Linux, macOS).

This script reads the live thermal stream from a connected Senxor device and outputs it as a virtual webcam.
The virtualcamera can be used in Zoom, OBS, Teams, or any app that uses a system camera.

Cross-platform: Windows (OBS Virtual Camera / Unity Capture), Linux (v4l2loopback),
macOS (OBS Virtual Camera).

Usage
-----
Run the default:
    python example/virtual-camera.py

For more options, run:
    python example/virtual-camera.py --help


External dependencies:
- pyvirtualcam
- typer
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyvirtualcam
import typer

import senxor
from senxor.proc import ColormapKey, apply_colormap, colormaps, enlarge, normalize


def resize_frame(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    if h == 62 and w == 80:
        frame_cut = frame[1:-1, :]
        frame_resized = enlarge(frame_cut, 8)
    elif h == 120 and w == 160:
        frame_resized = enlarge(frame, 4)
    elif h == 50 and w == 50:
        new_frame = np.zeros((48, 64, 3), dtype=np.uint8)
        new_frame[:, 7:-7] = frame[1:-1, :]
        frame_resized = enlarge(new_frame, 10)
    else:
        raise ValueError(f"Unknown frame shape: {h}x{w}")
    return frame_resized


@dataclass(frozen=True)
class VirtualCameraConfig:
    colormap: ColormapKey
    gray: bool
    index: int
    fps: int


def run_virtual_camera(
    config: VirtualCameraConfig,
) -> None:
    devices = senxor.list_senxor("serial")
    if not devices:
        raise ValueError("No available devices found")
    if config.index >= len(devices):
        raise ValueError(
            f"Invalid device index {config.index}, available: 0..{len(devices) - 1}",
        )
    device_address = devices[config.index]
    device = None
    cam = None
    try:
        device = senxor.connect(device_address)
        device.fields.FRAME_RATE_DIVIDER.set(0)
        cam = pyvirtualcam.Camera(width=640, height=480, fps=config.fps)
        device.start_stream()
        typer.echo(f"Using virtual camera: {cam.device}")
        while True:
            _, frame = device.read(block=True)
            if frame is None:
                continue
            frame = normalize(frame, dtype=np.uint8)
            if config.gray:
                frame_rgb = np.stack([frame] * 3, axis=-1)
            else:
                frame_rgb = apply_colormap(frame, colormaps[config.colormap])
            frame_resized = resize_frame(frame_rgb)
            cam.send(frame_resized)
    finally:
        if device is not None:
            device.close()
        if cam is not None:
            cam.close()


app = typer.Typer()


@app.command()
def run(
    colormap: ColormapKey = typer.Option(  # noqa: B008
        "inferno",
        "--colormap",
        "-c",
        help="Colormap to use when not in gray mode.",
    ),
    gray: bool = typer.Option(
        False,
        "--gray",
        "-g",
        help="Render grayscale image; ignore colormap.",
    ),
    index: int = typer.Option(
        0,
        "--index",
        "-i",
        min=0,
        help="Device index in senxor.list_senxor('serial').",
    ),
    fps: int = typer.Option(
        30,
        "--fps",
        "-f",
        min=1,
        help="Virtual camera frame rate.",
    ),
) -> None:
    config = VirtualCameraConfig(colormap=colormap, gray=gray, index=index, fps=fps)
    try:
        run_virtual_camera(config)
    except KeyboardInterrupt:
        typer.secho(
            "Interrupted by user, shutting down...",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(0) from None
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
