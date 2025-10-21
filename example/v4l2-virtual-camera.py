"""Thermal Camera Streaming and Display Tool.

This script connects to a Senxor thermal camera, processes the thermal data,
and either displays it in a local window or streams it to a virtual video
device using FFmpeg.

-------------------------------------------------------------------------------
Usage
-------------------------------------------------------------------------------

1.  **Display Locally:**
    To view the thermal camera feed on your desktop, run the script without
    the `--stream` flag. You can customize the display with various options.

    `python thermal_toolbox.py --scale 6 --colormap viridis --smoothing-level 7`

2.  **Stream to a Virtual Camera (with FFmpeg):**
    This allows you to use the thermal camera feed as a webcam in other
    applications (e.g., Zoom, OBS, VLC).

    **Prerequisites:**
    a.  **FFmpeg:** Must be installed on your system.
    b.  **v4l2loopback:** A kernel module to create virtual video devices.
        -   Install: `sudo apt-get install v4l2loopback-dkms`
        -   Load module: `sudo modprobe v4l2loopback video_nr=1 card_label="Senxor Thermal Cam" exclusive_caps=1`
            (This creates a virtual device at `/dev/video1`)

    **Command:**
    Pipe the script's output directly into FFmpeg. The pixel format, video size,
    and framerate must match the script's output and FFmpeg's input parameters.

    python thermal_toolbox.py --stream | ffmpeg -f rawvideo -pixel_format rgb24 -video_size 640x480 -framerate 5 -i - -f v4l2 /dev/video1
    **Breakdown of the FFmpeg command:**
    -   `-f rawvideo`: Specifies the input format is raw video data.
    -   `-pixel_format rgb24`: The color format of the incoming stream (matches the script's output).
    -   `-video_size 640x480`: The resolution of the video stream.
    -   `-framerate 5`: The frames per second.
    -   `-i -`: Reads the input from stdin (the pipe from the Python script).
    -   `-f v4l2`: Specifies the output format is for a V4L2 device.
    -   `/dev/video1`: The path to your virtual video device.

-------------------------------------------------------------------------------
"""

import argparse
import logging
import signal
import sys
import time
from logging import StreamHandler

import cv2 as cv
import numpy as np

import senxor
from senxor.proc import apply_colormap, enlarge, get_colormaps, normalize

# Global constants
WHITE = [255, 255, 255]
CVFONT = cv.FONT_HERSHEY_SIMPLEX
CVFONT_SIZE = 0.7

# --- State Container (Replaces 'global') ---
# A mutable list to hold the state variables (logger, mi48, args)
# Accessing and setting elements in this list does NOT require the 'global' keyword.
# [0] = logger, [1] = mi48, [2] = args
STATE = [None, None, None]

# --- Helper Classes and Functions ---


class RollingAverageFilter:
    """A simple rolling average filter for temporal smoothing of frames."""

    def __init__(self, N=5):
        self.N = N
        self.buffer = []

    def __call__(self, frame):
        self.buffer.append(frame.copy())
        if len(self.buffer) > self.N:
            self.buffer.pop(0)
        return np.mean(self.buffer, axis=0)


def signal_handler(_sig, _frame):
    """Handles Ctrl+C and other termination signals for a clean exit."""
    # Unpack state variables from the container
    logger, mi48, args = STATE

    if logger:
        logger.info("Exiting due to SIGINT or SIGTERM")

    if mi48:
        mi48.stop_stream()
        mi48.close()

    # Check if args is available before accessing its properties
    if args and not args.stream:
        cv.destroyAllWindows()

    sys.exit(0)


def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Thermal Camera Streaming and Display Tool.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-tis",
        "--thermal-image-source",
        default=None,
        dest="tis_id",
        help="COM port name (str) for the Senxor device.",
    )
    parser.add_argument(
        "-fps",
        "--framerate",
        default=5,
        type=int,
        dest="fps",
        help="Frame rate per second for processing and streaming.",
    )
    parser.add_argument(
        "-c",
        "--colormap",
        default="jet",
        type=str,
        help="Colormap for the thermogram (e.g., jet, hot, viridis, inferno).",
    )
    parser.add_argument(
        "-e",
        "--emissivity",
        type=float,
        default=0.95,
        dest="emissivity",
        help="Target emissivity for temperature accuracy (0.0 to 1.0).",
    )
    parser.add_argument(
        "-s",
        "--scale",
        default=4,
        type=int,
        dest="img_scale",
        help="Integer scale factor to enlarge the thermal image (>= 1).",
    )
    parser.add_argument(
        "-smooth",
        "--smoothing-level",
        default=5,
        type=int,
        dest="smooth_level",
        help="Kernel size for spatial median blur (odd integer >= 3).",
    )
    parser.add_argument(
        "-ts",
        "--temporal-smooth",
        default=3,
        type=int,
        dest="temporal_smooth",
        help="Number of frames to average for temporal smoothing (>= 1).",
    )
    parser.add_argument(
        "--clahe",
        action="store_true",
        default=False,
        help="Enable Contrast Limited Adaptive Histogram Equalization (CLAHE).",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        default=False,
        help="Stream raw RGB video to stdout for piping to FFmpeg.",
    )
    args = parser.parse_args()

    # Validate arguments
    if args.smooth_level % 2 == 0 or args.smooth_level < 3:
        parser.error("Spatial smoothing level must be an odd integer >= 3.")
    if args.img_scale < 1:
        parser.error("Scale factor must be an integer >= 1.")
    if args.temporal_smooth < 1:
        parser.error("Temporal smoothing frame count must be an integer >= 1.")

    return args


# --- Main Application Logic ---


def main():
    # Setup logging to stderr
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, handlers=[StreamHandler(sys.stderr)])

    # Handle signals for a clean exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # Parse command-line arguments
    args = parse_args()

    # Store initial state in the container
    STATE[0] = logger
    STATE[2] = args

    # Connect to the thermal camera
    mi48 = None
    try:
        serials = senxor.list_senxor("serial")
        if not serials:
            logger.critical("No SenXor devices found. Please ensure the camera is connected.")
            sys.exit(1)

        # Connect to the first available device
        mi48 = senxor.connect(serials[0])
        if mi48 is None:
            logger.critical("Failed to connect to SenXor device.")
            sys.exit(1)

        # Store the mi48 object in the state container
        STATE[1] = mi48

        # Give the device a moment to initialize after connection
        time.sleep(0.1)
        logger.info("Successfully connected to SenXor device: %s", mi48.get_sn())

    except Exception as e:
        logger.critical("Cannot connect to SenXor: %s", e)
        if mi48:
            mi48.close()
        sys.exit(1)

    # Configure the camera
    mi48.write_reg("EMISSIVITY", int(args.emissivity * 100))
    mi48.start_stream()

    # Initialize processing tools
    temporal_filter = RollingAverageFilter(N=args.temporal_smooth)
    clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)) if args.clahe else None
    cmap = get_colormaps(args.colormap, namespace="cv")
    window_name = f"Thermal Image - {mi48.get_sn()}"
    stream_size = (640, 480)

    # Configure stdout for binary output if streaming
    if args.stream:
        sys.stdout = sys.stdout.buffer

    # --- Main Loop ---
    while True:
        header, frame = mi48.read()
        if frame is None:
            logger.warning("Failed to read a valid frame from the camera.")
            continue

        frame_float = frame.astype(np.float32)

        # Apply temporal smoothing
        frame_smoothed = temporal_filter(frame_float)

        # Normalize the frame to 0-255 uint8 for filtering and display
        frame_uint8 = normalize(frame_smoothed, dtype=np.uint8)

        # Apply spatial smoothing (median filter)
        smoothed_frame = cv.medianBlur(frame_uint8, ksize=args.smooth_level)

        # Apply CLAHE if enabled
        if args.clahe:
            smoothed_frame = clahe.apply(smoothed_frame)

        # Apply colormap and enlarge the image. The result is in RGB format.
        img_colored_rgb = apply_colormap(smoothed_frame, cmap)
        img_enlarged_rgb = enlarge(img_colored_rgb, args.img_scale)

        # Find and annotate min/max temperature points
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(frame_smoothed)
        scale = args.img_scale
        min_loc_scaled = (int(min_loc[0] * scale), int(min_loc[1] * scale))
        max_loc_scaled = (int(max_loc[0] * scale), int(max_loc[1] * scale))
        min_val = min_val / 10.0
        max_val = max_val / 10.0
        cv.putText(img_enlarged_rgb, "+", min_loc_scaled, CVFONT, CVFONT_SIZE, WHITE, 2)
        cv.putText(
            img_enlarged_rgb,
            f"{min_val:.1f}C",
            (min_loc_scaled[0] + 10, min_loc_scaled[1]),
            CVFONT,
            CVFONT_SIZE,
            WHITE,
            1,
        )
        cv.putText(img_enlarged_rgb, "+", max_loc_scaled, CVFONT, CVFONT_SIZE, WHITE, 2)
        cv.putText(
            img_enlarged_rgb,
            f"{max_val:.1f}C",
            (max_loc_scaled[0] + 10, max_loc_scaled[1]),
            CVFONT,
            CVFONT_SIZE,
            WHITE,
            1,
        )

        # --- Output Frame ---
        if args.stream:
            # Resize the RGB image and write directly to stdout for FFmpeg
            img_resized_rgb = cv.resize(img_enlarged_rgb, stream_size, interpolation=cv.INTER_LINEAR)
            sys.stdout.write(img_resized_rgb.tobytes())
            sys.stdout.flush()
        else:
            # For local display, convert the RGB image to BGR for OpenCV
            img_bgr = cv.cvtColor(img_enlarged_rgb, cv.COLOR_RGB2BGR)
            img_resized_bgr = cv.resize(img_bgr, stream_size, interpolation=cv.INTER_LINEAR)
            cv.imshow(window_name, img_resized_bgr)
            key = cv.waitKey(1)
            if key in [ord("q"), 27]:  # 'q' or Esc key
                break

    # --- Cleanup ---
    logger.info("Closing camera and cleaning up.")
    mi48.stop_stream()
    mi48.close()
    if not args.stream:
        cv.destroyAllWindows()


if __name__ == "__main__":
    main()
