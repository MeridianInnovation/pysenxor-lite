import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, List

import numpy as np
from PIL import Image, ImageOps, ImageTk

from senxor import connect_senxor, list_senxor
from senxor.log import setup_console_logger
from senxor.proc import normalize
from senxor.regs import REGS


class DeviceControlFrame(ttk.Frame):
    """A frame for device selection, connection, and disconnection."""

    def __init__(
        self,
        master,
        on_connect: Callable[[int], None],
        on_disconnect: Callable[[], None],
        on_refresh: Callable[[], None],
    ):
        super().__init__(master)
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.on_refresh_callback = on_refresh

        self._setup_widgets()

    def _setup_widgets(self):
        ttk.Label(self, text="Device:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_combo = ttk.Combobox(self, state="readonly")
        self.device_combo.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.refresh_button = ttk.Button(self, text="Refresh", command=self.on_refresh_callback)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.connect_button = ttk.Button(self, text="Connect", command=self._on_connect, state=tk.DISABLED)
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.disconnect_button = ttk.Button(
            self,
            text="Disconnect",
            command=self.on_disconnect_callback,
            state=tk.DISABLED,
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

    def _on_connect(self):
        selected_index = self.device_combo.current()
        if selected_index >= 0:
            self.on_connect_callback(selected_index)

    def update_device_list(self, devices: List[str]):
        """Populates the dropdown with a list of device addresses."""
        self.device_combo["values"] = devices
        if devices:
            self.device_combo.current(0)
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.device_combo.set("No devices found")
            self.connect_button.config(state=tk.DISABLED)

    def set_connection_state(self, is_connected: bool):
        """Update button states based on connection status."""
        self.connect_button.config(state=tk.DISABLED if is_connected else tk.NORMAL)
        self.disconnect_button.config(state=tk.NORMAL if is_connected else tk.DISABLED)
        self.device_combo.config(state=tk.DISABLED if is_connected else "readonly")
        self.refresh_button.config(state=tk.DISABLED if is_connected else tk.NORMAL)


class ImageViewer(ttk.Frame):
    """A frame for displaying the thermal image."""

    def __init__(self, master):
        super().__init__(master)
        self.image_label = ttk.Label(self)
        self.image_label.pack(expand=True)
        self._img_ref = None  # Keep a reference to avoid garbage collection

    def update_image(self, pil_image: Image.Image):
        """Displays a new image."""
        self._img_ref = ImageTk.PhotoImage(pil_image)
        self.image_label.configure(image=self._img_ref)  # type: ignore

    def clear(self):
        """Clears the image."""
        blank_image = ImageTk.PhotoImage(Image.new("RGB", (1, 1)))
        self.image_label.configure(image=blank_image)  # type: ignore
        self._img_ref = blank_image


class StatusBar(ttk.Frame):
    """A simple status bar."""

    def __init__(self, master):
        super().__init__(master)
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, font=("Segoe UI", 10), relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)

    def set_status(self, text: str):
        self.status_var.set(text)


class MainApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.senxor = None
        self.running = True

        self._setup_ui()
        self._initialize_fps_counters()

    def _setup_ui(self):
        self.root.title("Thermal Senxor Demo")
        self.root.geometry("600x600")
        self.root.configure(bg="#f4f4f4")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Create and pack components
        self.image_viewer = ImageViewer(self.root)
        self.image_viewer.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.set_status("Disconnected")

        self.device_control = DeviceControlFrame(
            self.root,
            on_connect=self._connect_device,
            on_disconnect=self._disconnect_device,
            on_refresh=self._refresh_devices,
        )
        self.device_control.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self._refresh_devices()  # Initial scan

    def _initialize_fps_counters(self):
        self.frame_count = 0
        self.fps = 0.0
        self.fps_last_update_time = time.time()

    def _refresh_devices(self):
        """Scan for devices and update the control frame."""
        self.available_devices = list_senxor()
        self.device_control.update_device_list(self.available_devices)

    def _connect_device(self, device_index: int):
        if not self.available_devices or device_index >= len(self.available_devices):
            self.status_bar.set_status("Error: Invalid device index.")
            return

        address = self.available_devices[device_index]
        try:
            self.senxor = connect_senxor(address)
            self.senxor.start_stream()
            self.device_control.set_connection_state(True)
            self.status_bar.set_status(f"Connected to {address}")
            self._initialize_fps_counters()
            self.poll_images()
        except Exception as e:
            self.status_bar.set_status(f"Error connecting: {e}")

    def _disconnect_device(self):
        if self.senxor:
            try:
                self.senxor.stop_stream()
                self.senxor.close()
            except Exception as e:
                self.status_bar.set_status(f"Disconnection error: {e}")
            finally:
                self.senxor = None
                self.image_viewer.clear()
                self.device_control.set_connection_state(False)
                self.status_bar.set_status("Disconnected")

    def poll_images(self):
        if not self.senxor or not self.running:
            return

        resp = self.senxor.read(block=False)
        if resp:
            self.frame_count += 1
            _, thermal_frame = resp
            thermal_norm = normalize(thermal_frame, dtype=np.uint8)
            pil_image = Image.fromarray(thermal_norm)
            prepared_image = ImageOps.contain(pil_image.convert("RGB"), (500, 500))
            self.image_viewer.update_image(prepared_image)

        self._update_status()
        self.root.after(20, self.poll_images)

    def _update_status(self):
        now = time.time()
        elapsed = now - self.fps_last_update_time
        if elapsed > 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_last_update_time = now
        self.status_bar.set_status(f"Connected | FPS: {self.fps:.1f}")

    def on_close(self):
        self.running = False
        self._disconnect_device()
        self.root.destroy()


if __name__ == "__main__":
    setup_console_logger()
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
