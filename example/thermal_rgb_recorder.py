"""Dual-camera synchronous recording system using multithreading.

This example solves the blocking nature of cv2.VideoCapture and cv2.VideoWriter
by wrapping the RGB camera in a background thread using senxor.cv_utils.CVCamThread.
It non-blockingly polls both the thermal and RGB cameras, combines their frames
side-by-side, displays them in real time, and records them to a local video file.

External dependencies:
- opencv-python
"""

import time
from pathlib import Path

import cv2
import numpy as np

from senxor import connect, list_senxor
from senxor.cv_utils import CVCamThread
from senxor.proc import normalize


def main():
    # 1. Initialize Senxor Device
    devices = list_senxor("serial")
    if not devices:
        raise ValueError("No devices found")

    senxor_device = connect(devices[0])

    # Set frame rate divider to 0 to get the maximum frame rate
    senxor_device.fields.FRAME_RATE_DIVIDER.set(0)
    senxor_device.start_stream()

    # 2. Initialize RGB Camera using CVCamThread to prevent blocking
    # standard cv2.VideoCapture(0) would block the main loop
    raw_cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not raw_cam.isOpened():
        senxor_device.close()
        raise ValueError("No RGB camera found")

    raw_cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    raw_cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    rgb_cam = CVCamThread(raw_cam)
    rgb_cam.start()

    # 3. Setup Video Writer
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time() * 1000)
    out_path = f"data/record_{timestamp}.avi"

    # We will resize both frames to 640x480 and put them side-by-side -> 1280x480
    fourcc = cv2.VideoWriter_fourcc(*"XVID")  # type: ignore[reportUnknownMember]
    # Using ~30 fps as a baseline for the recording
    video_writer = cv2.VideoWriter(out_path, fourcc, 30.0, (1280, 480))

    thermal_image_resized = None
    rgb_image_resized = None

    try:
        print("System running, press 'q' or 'ESC' to exit")
        while True:
            # Non-blocking read from thermal camera
            _, thermal_raw = senxor_device.read(block=False)
            if thermal_raw is not None:
                # Convert 16-bit thermal data to 8-bit visual image
                norm_img = normalize(thermal_raw, dtype=np.uint8)
                color_img = cv2.applyColorMap(norm_img, cv2.COLORMAP_INFERNO)
                # Resize to standard height 480
                thermal_image_resized = cv2.resize(color_img, (640, 480))

            # Non-blocking read from the RGB camera thread
            rgb_raw = rgb_cam.read()
            if rgb_raw is not None:
                rgb_image_resized = cv2.resize(rgb_raw, (640, 480))

            if thermal_image_resized is None or rgb_image_resized is None:
                continue

            # Stack them side-by-side horizontally
            combined_frame = np.hstack((thermal_image_resized, rgb_image_resized))

            # Show in UI
            cv2.imshow("Thermal + RGB Recorder", combined_frame)

            # Write to disk(technically blocking I/O, but it is fast enough to run in the main loop)
            video_writer.write(combined_frame)

            # Wait for 30ms
            time.sleep(0.03)

            key = cv2.waitKey(1)
            if key in (27, ord("q")):  # ESC or 'q'
                break

    finally:
        cv2.destroyAllWindows()
        video_writer.release()
        rgb_cam.stop()
        senxor_device.close()


if __name__ == "__main__":
    main()
