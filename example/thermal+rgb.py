"""Dual camera streaming example using thermal and RGB cameras.

External dependencies:
- opencv-python
"""

import cv2
import numpy as np

from senxor import connect, list_senxor
from senxor.log import setup_console_logger
from senxor.proc import enlarge, normalize

if __name__ == "__main__":
    setup_console_logger()

    # Initialize the Senxor device
    devices = list_senxor("serial")
    if not devices:
        raise ValueError("No devices found")

    senxor_device = connect(devices[0])

    # Set frame rate divider to 0 to get the maximum frame rate
    senxor_device.fields.FRAME_RATE_DIVIDER.set(0)
    senxor_device.start_stream()

    # Initialize the OpenCV camera
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # Optional: Set the resolution of the camera
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    thermal_image = None
    rgb_image = None

    try:
        while True:
            # Read from SenxorDevice (non-blocking)
            thermal_header, thermal_raw = senxor_device.read(block=False)
            if thermal_raw is not None:
                thermal_image = normalize(thermal_raw, dtype=np.float32)
                thermal_image = enlarge(thermal_image, 3)

            # Read from OpenCV camera(blocking)
            ret, rgb_raw = cam.read()
            if rgb_raw is not None:
                rgb_image = rgb_raw
                rgb_image = cv2.resize(rgb_image, (640, 360))

            if thermal_image is not None and rgb_image is not None:
                cv2.imshow("thermal", thermal_image)
                cv2.imshow("rgb", rgb_image)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        # Clean up resources
        cv2.destroyAllWindows()
        senxor_device.close()
        cam.release()
