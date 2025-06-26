"""Basic example demonstrating SenxorThread's read functionality.

This example shows how to use SenxorThread to read data from a Senxor device
in a background thread without using listeners.

Note that in most basic use cases, using Senxor.read(block=False) is simpler and introduces
negligible latency compared to using SenxorThread. This example demonstrates SenxorThread
for cases where background thread processing is specifically needed.
"""

import time

import numpy as np

from senxor import list_senxor
from senxor.thread import SenxorThread


def main():
    # Search for available Senxor devices
    print("Searching for Senxor devices...")
    devices = list_senxor()

    if not devices:
        print("No Senxor devices found.")
        return

    print(f"Found {len(devices)} device(s): {devices}")
    address = devices[0]

    try:
        # Create and start a SenxorThread instance using context manager
        with SenxorThread(address, frame_unit="C") as senxor_thread:
            print(f"Started streaming from {address}. Press Ctrl+C to stop.")

            # Track frame statistics
            frame_count = 0
            start_time = time.time()
            last_stats_time = start_time

            while True:
                # Read the latest frame (non-blocking)
                header, frame = senxor_thread.read()

                # Process the frame if available
                if frame is not None and header is not None:
                    frame_count += 1

                    # Calculate temperature statistics
                    min_temp = np.min(frame)
                    max_temp = np.max(frame)
                    avg_temp = np.mean(frame)

                    # Print frame information occasionally
                    current_time = time.time()
                    if current_time - last_stats_time >= 1.0:  # Print stats every second
                        elapsed = current_time - start_time
                        fps = frame_count / elapsed
                        print(
                            f"Frame {frame_count}: {frame.shape}, "
                            f"Temperature (°C): Min={min_temp:.1f}, Max={max_temp:.1f}, Avg={avg_temp:.1f}, "
                            f"FPS: {fps:.1f}",
                        )
                        last_stats_time = current_time

                # Small sleep to prevent CPU hogging
                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"An error occurred: {e}")

    print("Program finished.")


if __name__ == "__main__":
    main()
