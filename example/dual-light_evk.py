import time

import cv2
import numpy as np

import senxor
from senxor.log import setup_console_logger
from senxor.proc import enlarge, normalize
from senxor.regs import REGS

if __name__ == "__main__":
    setup_console_logger()

    senxor = senxor.connect_senxor()
    senxor.reg_write(REGS.FRAME_RATE, 0)
    senxor.start_stream()

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    thermal_image = None
    rgb_image = None

    while True:
        thermal_resp = senxor.read(block=False)
        if thermal_resp is not None:
            thermal_header, thermal_raw = thermal_resp
            thermal_image = normalize(thermal_raw, dtype=np.float32)
            thermal_image = enlarge(thermal_image, 3)

        ret, rgb_raw = cam.read()
        if rgb_raw is not None:
            rgb_image = rgb_raw
            rgb_image = cv2.resize(rgb_image, (640, 360))

        if thermal_image is not None and rgb_image is not None:
            cv2.imshow("thermal", thermal_image)
            cv2.imshow("rgb", rgb_image)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    senxor.stop_stream()
    senxor.close()
