import threading
import time
import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageTk

import senxor
from senxor.log import setup_console_logger
from senxor.proc import normalize
from senxor.regs import REGS


class DualLightApp:
    def __init__(self, root):
        self.root = root
        self.running = True

        self._setup_ui()
        self._initialize_devices()
        self._initialize_fps_counters()

        self.update_interval = 20  # ms
        self.poll_images()

    def _setup_ui(self):
        """Create and arrange all UI elements."""
        self.root.title("Dual Light")
        self.root.geometry("900x500")
        self.root.configure(bg="#f4f4f4")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Title
        title = ttk.Label(self.root, text="Dual Light", font=("Segoe UI", 20, "bold"))
        title.pack(pady=(10, 0))

        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Image frames
        img_frame = ttk.Frame(main_frame)
        img_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Thermal image
        thermal_col = ttk.Frame(img_frame)
        thermal_col.pack(side=tk.LEFT, padx=20, fill=tk.BOTH, expand=True)
        self.thermal_label = ttk.Label(thermal_col)
        self.thermal_label.pack()
        ttk.Label(thermal_col, text="Thermal Image", font=("Segoe UI", 12)).pack(pady=5)

        # Separator
        sep = ttk.Separator(img_frame, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # RGB image
        rgb_col = ttk.Frame(img_frame)
        rgb_col.pack(side=tk.LEFT, padx=20, fill=tk.BOTH, expand=True)
        self.rgb_label = ttk.Label(rgb_col)
        self.rgb_label.pack()
        ttk.Label(rgb_col, text="RGB Image", font=("Segoe UI", 12)).pack(pady=5)

        # Status bar (two columns)
        self.thermal_status_var = tk.StringVar()
        self.rgb_status_var = tk.StringVar()
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        thermal_status_bar = ttk.Label(
            status_frame,
            textvariable=self.thermal_status_var,
            anchor=tk.W,
            font=("Segoe UI", 10),
            relief=tk.SUNKEN,
        )
        thermal_status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        rgb_status_bar = ttk.Label(
            status_frame,
            textvariable=self.rgb_status_var,
            anchor=tk.E,
            font=("Segoe UI", 10),
            relief=tk.SUNKEN,
        )
        rgb_status_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def _initialize_devices(self):
        """Connect to Senxor and open the RGB camera."""
        self.senxor = senxor.connect_senxor()
        self.senxor.reg_write(REGS.FRAME_RATE, 2)
        self.senxor.start_stream()

        self.cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cam.set(cv2.CAP_PROP_FPS, 10)

    def _initialize_fps_counters(self):
        """Initialize variables for tracking FPS for each stream."""
        self.thermal_frame_count = 0
        self.rgb_frame_count = 0
        self.thermal_fps = 0.0
        self.rgb_fps = 0.0
        self.fps_last_update_time = time.time()

    def poll_images(self):
        """Main loop to poll for new images and update the UI."""
        thermal_image = self.get_thermal_image()
        if thermal_image:
            self.thermal_frame_count += 1

        rgb_image = self.get_rgb_image()
        if rgb_image:
            self.rgb_frame_count += 1

        if thermal_image and rgb_image:
            thermal_pil, rgb_pil = self.prepare_images(thermal_image, rgb_image)
            self.display_images(thermal_pil, rgb_pil)

        self._update_status()

        if self.running:
            self.root.after(self.update_interval, self.poll_images)

    def _update_status(self):
        """Calculate FPS and update the status bar."""
        now = time.time()
        elapsed = now - self.fps_last_update_time
        if elapsed > 1.0:  # Update FPS every second
            self.thermal_fps = self.thermal_frame_count / elapsed
            self.rgb_fps = self.rgb_frame_count / elapsed

            self.thermal_frame_count = 0
            self.rgb_frame_count = 0
            self.fps_last_update_time = now

        thermal_status = (
            f"Thermal: {'Connected' if self.senxor.is_connected else 'Disconnected'} | FPS: {self.thermal_fps:.1f}"
        )
        rgb_status = f"RGB: {'Opened' if self.cam.isOpened() else 'Closed'} | FPS: {self.rgb_fps:.1f}"

        self.thermal_status_var.set(thermal_status)
        self.rgb_status_var.set(rgb_status)

    def get_thermal_image(self):
        resp = self.senxor.read(block=False)
        if resp is not None:
            _, thermal_frame = resp
            thermal_norm = normalize(thermal_frame, dtype=np.uint8)
            return Image.fromarray(thermal_norm)
        return None

    def get_rgb_image(self):
        ret, frame = self.cam.read()
        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)
        return None

    def prepare_images(self, thermal_img, rgb_img):
        target_size = (400, 300)
        thermal_resized = ImageOps.contain(thermal_img.convert("RGB"), target_size)
        rgb_resized = ImageOps.fit(rgb_img, target_size, method=Image.Resampling.LANCZOS)
        return thermal_resized, rgb_resized

    def display_images(self, thermal_img, rgb_img):
        self._thermal_img_ref = ImageTk.PhotoImage(thermal_img)
        self._rgb_img_ref = ImageTk.PhotoImage(rgb_img)
        self.thermal_label.configure(image=self._thermal_img_ref)  # type: ignore  # noqa: PGH003
        self.rgb_label.configure(image=self._rgb_img_ref)  # type: ignore  # noqa: PGH003

    def on_close(self):
        self.running = False
        if self.senxor:
            self.senxor.stop_stream()
            self.senxor.close()
        if self.cam:
            self.cam.release()
        self.root.destroy()


if __name__ == "__main__":
    setup_console_logger()
    root = tk.Tk()
    app = DualLightApp(root)
    root.mainloop()
