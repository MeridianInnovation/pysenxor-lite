# nuitka-project: --standalone
# nuitka-project: --onefile
# nuitka-project: --enable-plugin=tk-inter
# nuitka-project: --follow-imports
# nuitka-project: --include-package-data=colormap_tool
# nuitka-project: --product-name="Dual Light Viewer"
# nuitka-project: --product-version="0.1.0"
# nuitka-project: --file-description="Dual-light camera viewer"
# nuitka-project: --copyright="Copyright (c) 2025 Meridian Innovation"
# nuitka-project: --report=compilation-report.xml


# package command:
# nuitka example/dual_stream_tkinter.py --output-dir=dist/dual_stream_tkinter

# pyinstaller -y -F -p . --collect-data=colormap_tool -i ./assets/icon.ico -n dual_stream --distpath dist/dual_stream example/dual_stream_tkinter.py
import time
import tkinter as tk
from tkinter import ttk

import numpy as np

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    print("Required packages are not installed.")
    exit(1)

import senxor
from senxor.cam import LiteCamera, list_camera
from senxor.log import setup_console_logger
from senxor.proc import normalize
from senxor.regs import REGS


class DualLightApp:
    def __init__(self, root):
        self.root = root
        self.running = True
        self.senxor = None
        self.cam = None

        self._blank_image = ImageTk.PhotoImage(Image.new("RGB", (1, 1)))

        self._setup_ui()
        self._initialize_fps_counters()
        self._refresh_devices()

        self.update_interval = 20  # ms
        self.poll_images()

    def _setup_ui(self):
        """Create and arrange all UI elements."""
        self.root.title("Dual Light")
        self.root.geometry("1200x600")
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
        self.thermal_col = ttk.Frame(img_frame)
        self.thermal_col.pack(side=tk.LEFT, padx=20, fill=tk.BOTH, expand=True)
        self.thermal_col.pack_propagate(False)
        self.thermal_label = ttk.Label(self.thermal_col)
        self.thermal_label.pack()
        ttk.Label(self.thermal_col, text="Thermal Image", font=("Segoe UI", 12)).pack(pady=5)

        # Separator
        self.sep = ttk.Separator(img_frame, orient=tk.VERTICAL)
        self.sep.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # RGB image
        self.rgb_col = ttk.Frame(img_frame)
        self.rgb_col.pack(side=tk.LEFT, padx=20, fill=tk.BOTH, expand=True)
        self.rgb_col.pack_propagate(False)
        self.rgb_label = ttk.Label(self.rgb_col)
        self.rgb_label.pack()
        ttk.Label(self.rgb_col, text="RGB Image", font=("Segoe UI", 12)).pack(pady=5)

        # --- Controls Frame ---
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)

        # Thermal controls
        thermal_control_frame = ttk.LabelFrame(controls_frame, text="Thermal Camera")
        thermal_control_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        thermal_control_frame.columnconfigure(1, weight=1)

        ttk.Label(thermal_control_frame, text="Device:").grid(row=0, column=0, padx=(5, 5), sticky="w")
        self.thermal_device_combo = ttk.Combobox(thermal_control_frame, state="readonly", width=30)
        self.thermal_device_combo.grid(row=0, column=1, sticky="ew", padx=5)

        thermal_btn_frame = ttk.Frame(thermal_control_frame)
        thermal_btn_frame.grid(row=0, column=2, sticky="e")

        self.thermal_refresh_button = ttk.Button(thermal_btn_frame, text="Refresh", command=self._refresh_devices)
        self.thermal_refresh_button.pack(side=tk.LEFT, padx=5)

        self.thermal_connect_button = ttk.Button(thermal_btn_frame, text="Connect", command=self._connect_thermal)
        self.thermal_connect_button.pack(side=tk.LEFT, padx=5)

        self.thermal_disconnect_button = ttk.Button(
            thermal_btn_frame,
            text="Disconnect",
            command=self._disconnect_thermal,
            state=tk.DISABLED,
        )
        self.thermal_disconnect_button.pack(side=tk.LEFT, padx=5)

        # RGB controls
        rgb_control_frame = ttk.LabelFrame(controls_frame, text="RGB Camera")
        rgb_control_frame.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        rgb_control_frame.columnconfigure(1, weight=1)

        ttk.Label(rgb_control_frame, text="Device:").grid(row=0, column=0, padx=(5, 5), sticky="w")
        self.rgb_device_combo = ttk.Combobox(rgb_control_frame, state="readonly", width=30)
        self.rgb_device_combo.grid(row=0, column=1, sticky="ew", padx=5)

        rgb_btn_frame = ttk.Frame(rgb_control_frame)
        rgb_btn_frame.grid(row=0, column=2, sticky="e")

        self.rgb_refresh_button = ttk.Button(rgb_btn_frame, text="Refresh", command=self._refresh_devices)
        self.rgb_refresh_button.pack(side=tk.LEFT, padx=5)

        self.rgb_connect_button = ttk.Button(rgb_btn_frame, text="Connect", command=self._connect_rgb)
        self.rgb_connect_button.pack(side=tk.LEFT, padx=5)

        self.rgb_disconnect_button = ttk.Button(
            rgb_btn_frame,
            text="Disconnect",
            command=self._disconnect_rgb,
            state=tk.DISABLED,
        )
        self.rgb_disconnect_button.pack(side=tk.LEFT, padx=5)
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

    def _refresh_devices(self):
        # Thermal
        try:
            self.available_thermal_devices = senxor.list_senxor()
            self.thermal_device_combo["values"] = self.available_thermal_devices
            if self.available_thermal_devices:
                self.thermal_device_combo.current(0)
                self.thermal_connect_button.config(state=tk.NORMAL)
            else:
                self.thermal_device_combo.set("No devices found")
                self.thermal_connect_button.config(state=tk.DISABLED)
        except Exception as e:
            self.thermal_device_combo.set("Error listing devices")
            print(f"Error listing thermal devices: {e}")

        # RGB
        try:
            self.available_rgb_cameras = list_camera()
            self.rgb_device_combo["values"] = self.available_rgb_cameras
            if self.available_rgb_cameras:
                self.rgb_device_combo.current(0)
                self.rgb_connect_button.config(state=tk.NORMAL)
            else:
                self.rgb_device_combo.set("No devices found")
                self.rgb_connect_button.config(state=tk.DISABLED)
        except Exception as e:
            self.rgb_device_combo.set("Error listing devices")
            print(f"Error listing RGB cameras: {e}")

    def _connect_thermal(self):
        selected_index = self.thermal_device_combo.current()
        if selected_index < 0:
            return

        address = self.available_thermal_devices[selected_index]
        try:
            self.senxor = senxor.connect_senxor(address)
            self.senxor.reg_write(REGS.FRAME_RATE, 2)
            self.senxor.start_stream()
            self._set_thermal_connection_state(True)
        except Exception as e:
            print(f"Failed to connect to thermal camera: {e}")

    def _disconnect_thermal(self):
        if self.senxor:
            try:
                self.senxor.stop_stream()
                self.senxor.close()
            except Exception as e:
                print(f"Error disconnecting thermal camera: {e}")
            finally:
                self.senxor = None
                self._set_thermal_connection_state(False)
                self.thermal_label.configure(image=self._blank_image)  # type: ignore
                self._thermal_img_ref = None

    def _set_thermal_connection_state(self, is_connected: bool):
        self.thermal_connect_button.config(state=tk.DISABLED if is_connected else tk.NORMAL)
        self.thermal_disconnect_button.config(state=tk.NORMAL if is_connected else tk.DISABLED)
        self.thermal_device_combo.config(state=tk.DISABLED if is_connected else "readonly")
        self.thermal_refresh_button.config(state=tk.DISABLED if is_connected else tk.NORMAL)

    def _connect_rgb(self):
        selected_index = self.rgb_device_combo.current()
        if selected_index < 0:
            return

        try:
            self.cam = LiteCamera(selected_index)
            self.cam.setResolution(1280, 720)
            self._set_rgb_connection_state(True)
        except Exception as e:
            print(f"Failed to connect to RGB camera: {e}")

    def _disconnect_rgb(self):
        if self.cam:
            try:
                self.cam.release()
            except Exception as e:
                print(f"Error disconnecting RGB camera: {e}")
            finally:
                self.cam = None
                self._set_rgb_connection_state(False)
                self.rgb_label.configure(image=self._blank_image)  # type: ignore
                self._rgb_img_ref = None

    def _set_rgb_connection_state(self, is_connected: bool):
        self.rgb_connect_button.config(state=tk.DISABLED if is_connected else tk.NORMAL)
        self.rgb_disconnect_button.config(state=tk.NORMAL if is_connected else tk.DISABLED)
        self.rgb_device_combo.config(state=tk.DISABLED if is_connected else "readonly")
        self.rgb_refresh_button.config(state=tk.DISABLED if is_connected else tk.NORMAL)

    def _initialize_fps_counters(self):
        """Initialize variables for tracking FPS for each stream."""
        self.thermal_frame_count = 0
        self.rgb_frame_count = 0
        self.thermal_fps = 0.0
        self.rgb_fps = 0.0
        self.fps_last_update_time = time.time()

    def poll_images(self):
        """Main loop to poll for new images and update the UI."""
        target_size = (400, 300)

        thermal_image = self.get_thermal_image()
        if thermal_image:
            self.thermal_frame_count += 1
            thermal_resized = ImageOps.contain(thermal_image.convert("RGB"), target_size)
            self._thermal_img_ref = ImageTk.PhotoImage(thermal_resized)
            self.thermal_label.configure(image=self._thermal_img_ref)  # type: ignore

        rgb_image = self.get_rgb_image()
        if rgb_image:
            self.rgb_frame_count += 1
            rgb_resized = ImageOps.fit(rgb_image, target_size, method=Image.Resampling.LANCZOS)
            self._rgb_img_ref = ImageTk.PhotoImage(rgb_resized)
            self.rgb_label.configure(image=self._rgb_img_ref)  # type: ignore

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

        thermal_status = f"Thermal: {'Connected' if self.senxor else 'Disconnected'} | FPS: {self.thermal_fps:.1f}"
        rgb_status = f"RGB: {'Opened' if self.cam and self.cam.isOpened() else 'Closed'} | FPS: {self.rgb_fps:.1f}"

        self.thermal_status_var.set(thermal_status)
        self.rgb_status_var.set(rgb_status)

    def get_thermal_image(self):
        if not self.senxor:
            return None

        header, thermal_frame = self.senxor.read(block=False)
        if thermal_frame is not None:
            thermal_norm = normalize(thermal_frame, dtype=np.uint8)
            return Image.fromarray(thermal_norm)
        return None

    def get_rgb_image(self):
        if not self.cam:
            return None

        ret, frame = self.cam.read()
        if ret and frame is not None:
            # The camera returns BGR, but PIL needs RGB, so we convert it.
            rgb = frame[:, :, ::-1]
            return Image.fromarray(rgb)
        return None

    def on_close(self):
        self.running = False
        self._disconnect_thermal()
        self._disconnect_rgb()
        self.root.destroy()


if __name__ == "__main__":
    setup_console_logger()
    root = tk.Tk()
    app = DualLightApp(root)
    root.mainloop()
