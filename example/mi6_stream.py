"""Stream thermal and RGB frames from an MI6 device using OpenCV.

External dependencies:
- opencv-python
"""

import cv2
import numpy as np

from senxor.log import setup_console_logger
from senxor.mi6 import MI6
from senxor.proc import apply_colormap, colormaps, enlarge, normalize

cmap = colormaps["inferno"]

if __name__ == "__main__":
    setup_console_logger()

    with MI6("10.42.1.3", 5600) as dev:
        try:
            dev.disable_all_filters()
            dev.set_streams(thermal=True, rgb=True, fusion=False)
            dev.start_stream()

            while True:
                header, frame = dev.read(block=False)
                if frame is not None:
                    image = normalize(frame, dtype=np.float32)
                    image = apply_colormap(image, cmap)
                    image = enlarge(image, 2)
                    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    cv2.imshow("thermal", image_bgr)

                rgb = dev.read_rgb(block=False)
                if rgb is not None:
                    cv2.imshow("rgb", rgb)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            try:
                dev.stop_stream()
            finally:
                cv2.destroyAllWindows()
