"""A example of how to stream frames from a TCP/IP port of a Senxor device and display them in a window using OpenCV.

External dependencies:
- opencv-python
"""

import cv2
import numpy as np

import senxor
from senxor.interface.tcpip_serial import TCPIPPort
from senxor.log import setup_console_logger
from senxor.proc import apply_colormap, colormaps, enlarge, normalize

DEVICE_HOST = "192.168.2.74"
DEVICE_PORT = 3333

cmap = colormaps["inferno"]

if __name__ == "__main__":
    # Setup the logger based on structlog.
    # This is optional.
    setup_console_logger()

    device = TCPIPPort(DEVICE_HOST, DEVICE_PORT)

    with senxor.connect(device) as dev:
        dev.start_stream()

        while True:
            header, frame = dev.read()

            image = normalize(frame, dtype=np.float32)
            image = apply_colormap(image, cmap)
            image = enlarge(image, 3)

            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imshow("senxor", image_bgr)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        dev.stop_stream()
