"""Basic example demonstrating senxor.thread.SenxorThread."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from senxor import Senxor, list_senxor
from senxor.thread import SenxorThread

if TYPE_CHECKING:
    import numpy as np


def on_senxor_data(_: np.ndarray | None, data: np.ndarray | None):
    if data is None:
        return
    print(f"Temperature: max: {data.max():.1f}, min: {data.min():.1f}, mean: {data.mean():.1f}")


def main():
    # Search for available Senxor devices
    devices = list_senxor()

    if not devices:
        exit(1)

    address = devices[0]

    try:
        # Create and start a SenxorThread
        senx = Senxor(address)
        senxor_thread = SenxorThread(senx, on_senxor_data)
        senxor_thread.start()

        while True:
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
