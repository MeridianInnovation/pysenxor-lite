"""FastAPI MJPEG Streamer for Senxor thermal cameras.

This example demonstrates how to integrate Senxor non-blocking reads into an
asyncio-based web framework like FastAPI. It runs a background worker coroutine
to continuously grab frames from the thermal camera, encodes them to JPEG, and
serves them as a continuous Motion JPEG (MJPEG) HTTP stream.

You can view the stream in any web browser by navigating to:
http://127.0.0.1:8000

External dependencies:
- fastapi
- uvicorn
- opencv-python
"""

import asyncio
from contextlib import asynccontextmanager

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from senxor import connect, list_senxor
from senxor.core import Senxor
from senxor.log import get_logger, setup_console_logger
from senxor.proc import enlarge, normalize

setup_console_logger("INFO")
logger = get_logger("fastapi_streamer")


class SenxorWorker:
    def __init__(self, senxor_device: Senxor):
        self.latest_jpeg_frame = None
        self.senxor_device = senxor_device

    async def senxor_worker(self):
        """Background coroutine to fetch and encode thermal frames."""
        logger.info("senxor_worker_started")
        try:
            while True:
                if self.senxor_device is not None:
                    # Non-blocking read is safe to run inside the asyncio event loop
                    _, thermal_raw = self.senxor_device.read(block=False)
                    if thermal_raw is not None:
                        # Process and colorize the thermal data
                        norm_img = normalize(thermal_raw, dtype=np.uint8)
                        norm_img = enlarge(norm_img, 3)
                        color_img = cv2.applyColorMap(norm_img, cv2.COLORMAP_INFERNO)

                        # Encode as JPEG
                        ret, buffer = cv2.imencode(".jpg", color_img)
                        if ret:
                            self.latest_jpeg_frame = buffer.tobytes()

                # Yield control back to the event loop so API requests can be served
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info("senxor_worker_cancelled")

    async def frame_generator(self):
        """Generator for the MJPEG stream."""
        while True:
            if self.latest_jpeg_frame is not None:
                latest_jpeg_frame = self.latest_jpeg_frame
                self.latest_jpeg_frame = None
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + latest_jpeg_frame + b"\r\n")

            # Sleep briefly to control the framerate of the stream over the network
            await asyncio.sleep(0.03)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown events."""
    devices = list_senxor("serial")
    if not devices:
        logger.error("no_senxor_devices_found")
        yield
        return

    senxor_device = connect(devices[0])
    senxor_device.fields.FRAME_RATE_DIVIDER.set(0)
    senxor_device.start_stream()
    logger.info("senxor_device_connected", device=devices[0])

    worker_instance = SenxorWorker(senxor_device)
    # Start the worker coroutine
    worker_task = asyncio.create_task(worker_instance.senxor_worker())

    # Store worker in app state to avoid global variables
    app.state.worker = worker_instance

    yield  # Hand control back to the FastAPI application

    # Shutdown cleanup
    if worker_instance.senxor_device is not None:
        worker_instance.senxor_device.close()
        logger.info("senxor_device_closed")
    if worker_task is not None:
        worker_task.cancel()


app = FastAPI(title="Senxor Thermal Streamer", lifespan=lifespan)


@app.get("/")
async def index():
    """Simple HTML page to display the MJPEG stream."""
    html_content = """
    <html>
        <head>
            <title>Senxor Thermal Stream</title>
            <style>
                body { background-color: #222; color: white; text-align: center; font-family: sans-serif; }
                img { border: 2px solid #555; margin-top: 20px; box-shadow: 0 0 15px rgba(0,0,0,0.5); }
            </style>
        </head>
        <body>
            <h1>Senxor Thermal Live Stream</h1>
            <img src="/stream" alt="Thermal Stream" />
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/stream")
async def video_stream(request: Request):
    """Endpoint serving the MJPEG continuous stream."""
    worker_instance: SenxorWorker | None = getattr(request.app.state, "worker", None)
    if worker_instance is None:
        return HTMLResponse("Worker not initialized", status_code=500)

    return StreamingResponse(
        worker_instance.frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


if __name__ == "__main__":
    logger.info("starting_server", url="http://127.0.0.1:8000")
    # Run the uvicorn server
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
