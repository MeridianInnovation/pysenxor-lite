"""A basic example of how to stream frames from a Senxor device and display them in a window using OpenCV.

External dependencies:
- opencv-python
"""

import cv2
import numpy as np

import senxor
from senxor.log import setup_console_logger
from senxor.proc import apply_colormap, colormaps, enlarge, normalize

# Choose the colormap `inferno`
cmap = colormaps["inferno"]

if __name__ == "__main__":
    # Setup the logger based on structlog.
    # This is optional.
    setup_console_logger()

    # List all available devices.
    devices = senxor.list_senxor("serial")
    if not devices:
        raise ValueError("No devices found")

    # Use the `with` statement to ensure the connection is closed after the block.
    with senxor.connect(devices[0]) as dev:
        # Start the stream.
        dev.start_stream()

        while True:
            # Call the `read` function to get the next frame.
            header, frame = dev.read()

            # Normalize the frame to (0, 1).
            image = normalize(frame, dtype=np.float32)

            # Apply the colormap to the image.
            image = apply_colormap(image, cmap)

            # Enlarge the image to make it easier to see.
            image = enlarge(image, 3)

            # The `apply_colormap` returns a RGB image, so we need to convert it to BGR to display it with cv2.
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imshow("senxor", image_bgr)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        dev.stop_stream()
