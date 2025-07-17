"""A example shows how to use the SenxorThread class and listener pattern to read thermal data from a Senxor device."""

import time

from senxor import connect, list_senxor
from senxor.thread import SenxorThread


def temp_info(_, frame):
    if frame is None:
        return
    print(f"min: {frame.min()}, max: {frame.max()}, mean: {frame.mean():.1f}")


def save_frame(_, frame):
    if frame is None:
        return
    # Write your save logic here
    print("save frame to file...")


if __name__ == "__main__":
    addrs = list_senxor()

    if len(addrs) == 0:
        print("No device found")
        exit()

    with connect(addrs[0]) as dev:
        # Create a thread to read thermal data in background
        thread = SenxorThread(dev)

        # Add listeners to the thread
        # The listener pattern is a simple way to handle the data in the background thread
        # The listener function will be called when a new frame is available
        # The listener function will be called with the header and frame data

        thread.add_listener(temp_info, name="temp_info")
        thread.add_listener(save_frame, name="save_frame")
        # Name is optional if you want to remove the listener later

        # Start the thread
        thread.start()
        time.sleep(5)

        thread.remove_listener("save_frame")
        time.sleep(5)


"""
Notes
-----

Listener functions must be extremely lightweight and non-blocking.

If a listener takes too long to execute and is still running when the next frame arrives, it can block the processing
pipeline. This may eventually prevent the background thread from keeping up with incoming data.

SenxorThread is designed to mitigate this: if a listener falls behind by more than 5 frames, the thread will raise an
error and exit.

For heavy or time-consuming tasks, use `asyncio` or a `ThreadPoolExecutor` to offload processing outside the listener.
"""
