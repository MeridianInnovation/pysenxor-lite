"""Multi-device alarm system using event-driven callbacks.

This example scans all available Senxor devices, connects to them,
and registers a data callback using `dev.on("data")`.
The callback calculates the maximum value in the frame. If it exceeds
a threshold, it logs the event as JSON and saves an image to the disk.
These I/O operations happen in background threads, so they do not block
the main loop or other devices.

External dependencies:
- opencv-python
"""

from __future__ import annotations

import time
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from senxor import connect, list_senxor
from senxor.log import get_logger, setup_file_logger
from senxor.proc import normalize, parse_header

if TYPE_CHECKING:
    from senxor.core import Senxor

ALARM_THRESHOLD = 50  # Example threshold for temperature in Celsius

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Setup JSON file logging for structured alarm records
app_log = get_logger("alarm_system")
setup_file_logger(DATA_DIR / "alarm_log.json", log_level="INFO", json_format=True, logger_name="alarm_system")


def on_data(
    header: np.ndarray | None,
    frame: np.ndarray,
    senxor: Senxor,
):
    if header is None:
        app_log.error("header_is_none", device=senxor.name)

    else:
        parsed_header = parse_header(header)
        frame_counter = parsed_header.frame_counter
        vdd = parsed_header.vdd
        die_temp = parsed_header.die_temp

        app_log.info(
            "frame_received",
            device=senxor.name,
            frame_counter=frame_counter,
            vdd=vdd,
            die_temp=die_temp,
        )

    max_val = np.max(frame)
    if max_val > ALARM_THRESHOLD:
        app_log.info("alarm_triggered", senxor=senxor, max_val=float(max_val))

        image = normalize(frame, dtype=np.uint8)
        color_image = cv2.applyColorMap(image, cv2.COLORMAP_INFERNO)

        timestamp = int(time.time() * 1000)

        # Blocking I/O: save image to disk
        # Because this runs in the callback's background thread,
        # it won't block the main thread or other sensors.
        filename = f"data/alarm_{senxor.name}_{timestamp}.png"
        cv2.imwrite(filename, color_image)
        app_log.info("image_saved", filename=filename)


def main():
    devices = list_senxor("serial")
    if not devices:
        raise ValueError("No devices found")

    app_log.info("devices_found", count=len(devices))

    print("Devices found:")
    for dev in devices:
        print(f"- {dev.name}")

    connected_devices = []

    try:
        for port in devices:
            dev = connect(port)
            connected_devices.append(dev)
            callback = partial(on_data, senxor=dev)
            dev.on("data", callback)
            dev.start_stream()
            app_log.info("device_started", device=dev.name)

        app_log.info("system_running")

        print("System running, press Ctrl+C to exit")

        # The main thread can remain completely idle or do other lightweight tasks
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        app_log.info("system_shutting_down")
    finally:
        for dev in connected_devices:
            dev.close()
            app_log.info("device_closed", device=dev.name)


if __name__ == "__main__":
    print("=" * 80)
    print("Start senxor alarm system")
    print("=" * 80)
    main()
    print("=" * 80)
    print("Senxor alarm system stopped")
    print("=" * 80)
