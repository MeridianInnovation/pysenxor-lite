"""Dual camera streaming example using thermal and RGB sensors."""

import cv2
import numpy as np

import senxor
from senxor.log import setup_console_logger
from senxor.proc import enlarge, normalize
from senxor.thread import CVCamThread, SenxorThread

if __name__ == "__main__":
    setup_console_logger()

    # Initialize the Senxor device
    senxor_device = senxor.connect_senxor()
    senxor_device.regs.FRAME_RATE.set(0)

    # Create threaded wrappers
    senxor_thread = SenxorThread(senxor_device)

    # Initialize the OpenCV camera
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # Optional: Set the resolution of the camera
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Create threaded wrapper for camera
    cam_thread = CVCamThread(cam)

    # Start the threads
    senxor_thread.start()
    cam_thread.start()

    thermal_image = None
    rgb_image = None

    try:
        while True:
            # Read from SenxorThread (non-blocking)
            thermal_header, thermal_raw = senxor_thread.read()
            if thermal_raw is not None:
                thermal_image = normalize(thermal_raw, dtype=np.float32)
                thermal_image = enlarge(thermal_image, 3)

            # Read from CVCamThread (non-blocking)
            ret, rgb_raw = cam_thread.read()
            if ret and rgb_raw is not None:
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
        senxor_thread.stop()
        cam_thread.stop()
