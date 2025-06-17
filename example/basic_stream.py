"""A basic example of how to stream frames from a Senxor device and display them in a window using cv2."""

import cv2
import numpy as np

import senxor
from senxor.log import setup_console_logger
from senxor.proc import apply_colormap, enlarge, get_colormaps, normalize

# Choose the colormap `inferno` from the built-in cv2 colormaps.
# This method does not require the cv2 package actually.
cmap = get_colormaps("inferno", namespace="cv", n=1024)

if __name__ == "__main__":
    # Setup the logger based on structlog.
    # This is optional.
    setup_console_logger()

    # List all available devices.
    serials = senxor.list_senxor("serial")

    # Use the `with` statement to ensure the connection is closed after the block.
    with senxor.connect(serials[0], "serial") as dev:
        # Start the stream.
        dev.start_stream()

        while True:
            # Call the `read` function to get the next frame.
            resp = dev.read(block=True, celsius=True)

            # Even most time the `read` function does not return None,
            # it's still a good practice to check if the response is None.
            if resp is not None:
                header, frame = resp

                # Let's say we're looking at a typical thermal image where temps are around 20-70°C.
                # These images can have 500+ distinct values to show tiny temperature differences.
                # Converting straight to uint8 grayscale (0-255) would cut our detail in half - not great!
                # That's why we first convert to float32 - it keeps all the original temperature info intact.
                image = normalize(frame, dtype=np.float32)

                # Now for adding colors - here's the tricky part:
                # Regular cv2.applyColorMap needs uint8 input and only has 256 colors to work with.
                # Using that would mean losing half our temperature detail again. Not what we want!
                # Instead, we use senxor.proc.get_colormaps to get more colors (bigger LUT)
                # and senxor.proc.apply_colormap to work directly with our detailed float32 image.

                # The uint8 parameter means the output image will be converted to uint8 after applying the colormap.
                # Converting to uint8 after applying the colormap is recommended since:
                # 1. uint8 RGB provides 16M colors (256^3).
                # 2. Most GUI frameworks expect uint8 RGB images as input
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
