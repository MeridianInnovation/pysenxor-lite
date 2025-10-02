"""SenxorThread Tkinter MVC Example.

This example demonstrates how to use SenxorThread with the listener pattern
in a tkinter application following MVC (Model-View-Controller) architecture.

```
Architecture Diagram:
------------------
┌─────────────────┐       ┌────────────────┐
│  ThermalModel   │       │TemperatureModel│
│  (SenxorThread) │──────▶│                │
└────────┬────────┘       └────────┬───────┘
         │                         │
         │ Notifies                │ Updates
         │ (Listener)              │ (data_ready)
         ▼                         ▼
┌────────────────────────────────────────────┐
│              Controller                    │
│  ┌─────────────────────────────────────┐   │
│  │ 1. Registers listeners with models  │   │
│  │ 2. Updates view based on models     │   │
│  │ 3. Handles user input from view     │   │
│  └─────────────────────────────────────┘   │
└──────────────────┬─────────────────────────┘
                   │
                   │ Updates
                   ▼
┌─────────────────────────────────────────────┐
│                   View                      │
│   ┌───────────────────────────────────┐     │
│   │ 1. Displays temperature data      │     │
│   │ 2. Provides user interface        │     │
│   │ 3. Sends user events to controller│     │
│   └───────────────────────────────────┘     │
└─────────────────────────────────────────────┘
```

```
Observer Pattern Flow:
------------------
  ┌───────────┐                    ┌───────────┐
  │SenxorThread│                    │Temperature│
  │(Producer)  │                    │  Model    │
  └─────┬─────┘                    └─────┬─────┘
        │                                │
        │ Frame arrives                  │
        │ ┌───────────┐                  │
        └▶│ Listener  │                  │
          │ Callback  │                  │
          └─────┬─────┘                  │
                │                        │
                │ Updates                │
                └───────────────────────▶│
                                         │
  ┌─────────────┐                        │
  │   View      │                        │
  │ (Observer)  │                        │
  └─────┬───────┘                        │
        │                                │
        │                                │
        │       ┌────────────┐           │
        │◀──────│data_ready=T│◀──────────┘
        │       └────────────┘
        │
        │ Displays data
        │ ┌────────────┐
        └▶│data_ready=F│
          └────────────┘
```

Architecture Overview:
---------------------
1. Models:
   - TemperatureModel: Stores and processes temperature data
   - ThermalModel (SenxorThread): Handles device communication in background thread

2. View:
   - SenxorView: Responsible for UI rendering and user input collection

3. Controller:
   - SenxorController: Coordinates models and view, handles events

Observer Pattern Implementation:
------------------------------
Since tkinter is not thread-safe and doesn't directly support the observer pattern,
we implement a custom observer pattern using two approaches:

1. SenxorThread's Listener Pattern:
   - The SenxorThread (ThermalModel) provides a built-in listener mechanism
   - Controller registers a lightweight callback function with SenxorThread
   - When new frames arrive, the callback updates the TemperatureModel
   - The callback MUST be lightweight to avoid blocking the device reading thread

2. UI Thread Observation:
   - A 'data_ready' flag serves as a simple observer mechanism for the UI thread
   - When the listener updates the TemperatureModel, it sets data_ready = True
   - The UI thread periodically checks this flag and updates the view when data is ready
   - After updating the view, it resets the flag to False

Thread Safety Considerations:
---------------------------
1. SenxorThread's internal thread safety:
   - SenxorThread handles its own thread safety for reading device data
   - It ensures listeners are called in a dedicated notification thread

2. Model thread safety:
   - TemperatureModel uses a lock to protect data during updates
   - The controller only reads from the model in the UI thread
   - The data_ready flag prevents reading incomplete data

3. View thread safety:
   - All view updates happen exclusively in the main tkinter thread
   - No direct view manipulation from listener callbacks

MVC Decoupling:
-------------
1. Model independence:
   - Models have no knowledge of the view or controller
   - TemperatureModel focuses on data storage and processing
   - ThermalModel (SenxorThread) focuses on device communication

2. View independence:
   - View defines update methods but doesn't know about models
   - View has no direct access to models or business logic
   - View only exposes methods for the controller to call

3. Controller as coordinator:
   - Controller initializes and connects models and view
   - Controller translates user actions into model operations
   - Controller observes model changes and updates the view
"""

import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror

import numpy as np

from senxor import Senxor, list_senxor
from senxor.thread import SenxorThread


class TemperatureModel:
    """Model component that stores the latest thermal data."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reset_model()

    def reset_model(self):
        self.frame = None
        self.header = None
        self.min_temp = 0
        self.max_temp = 0
        self.avg_temp = 0
        self.frame_count = 0
        self.last_update_time = time.time()
        self.fps = 0

    def update_frame(self, header, frame):
        """Update the model with new frame data."""
        with self._lock:
            self.header = header
            self.frame = frame

            if frame is not None:
                self.frame_count += 1
                self.min_temp = np.min(frame)
                self.max_temp = np.max(frame)
                self.avg_temp = np.mean(frame)

                # Calculate FPS
                current_time = time.time()
                time_diff = current_time - self.last_update_time
                if time_diff > 0:
                    self.fps = 1.0 / time_diff
                self.last_update_time = current_time


class SenxorView(tk.Tk):
    """Base View component that displays the temperature data."""

    def __init__(self):
        super().__init__()

        self.title("SenxorThread Tkinter Example")
        self.geometry("600x400")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._create_widgets()

    def _create_widgets(self):
        """Create the UI widgets without binding events."""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Connection frame
        conn_frame = ttk.LabelFrame(main_frame, text="Device Connection", padding="10")
        conn_frame.pack(fill=tk.X, pady=10)

        # Device selection
        ttk.Label(conn_frame, text="Device:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.device_combo = ttk.Combobox(conn_frame, width=30, state="readonly")
        self.device_combo.grid(row=0, column=1, padx=5)

        # Buttons
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.grid(row=0, column=2, padx=5)

        self.refresh_btn = ttk.Button(btn_frame, text="Refresh")
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        self.connect_btn = ttk.Button(btn_frame, text="Connect")
        self.connect_btn.pack(side=tk.LEFT, padx=2)

        self.disconnect_btn = ttk.Button(btn_frame, text="Disconnect", state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=2)

        # Temperature display
        temp_frame = ttk.LabelFrame(main_frame, text="Temperature Data", padding="10")
        temp_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Temperature values
        info_frame = ttk.Frame(temp_frame)
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text="Min Temp:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.min_temp_var = tk.StringVar(value="--")
        ttk.Label(info_frame, textvariable=self.min_temp_var).grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(info_frame, text="Max Temp:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.max_temp_var = tk.StringVar(value="--")
        ttk.Label(info_frame, textvariable=self.max_temp_var).grid(row=0, column=3, padx=5, sticky=tk.W)

        ttk.Label(info_frame, text="Avg Temp:").grid(row=0, column=4, padx=5, sticky=tk.W)
        self.avg_temp_var = tk.StringVar(value="--")
        ttk.Label(info_frame, textvariable=self.avg_temp_var).grid(row=0, column=5, padx=5, sticky=tk.W)

        # Frame info
        frame_info = ttk.Frame(temp_frame)
        frame_info.pack(fill=tk.X, pady=5)

        ttk.Label(frame_info, text="Frame Count:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.frame_count_var = tk.StringVar(value="0")
        ttk.Label(frame_info, textvariable=self.frame_count_var).grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(frame_info, text="FPS:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.fps_var = tk.StringVar(value="0.0")
        ttk.Label(frame_info, textvariable=self.fps_var).grid(row=0, column=3, padx=5, sticky=tk.W)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # View update methods for controller to call

    def update_device_list(self, devices):
        """Update the device dropdown with available devices."""
        self.device_combo["values"] = devices
        if devices:
            self.device_combo.current(0)
            self.connect_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Found {len(devices)} device(s)")
        else:
            self.device_combo.set("No devices found")
            self.connect_btn.config(state=tk.DISABLED)
            self.status_var.set("No devices found")

    def update_connection_state(self, is_connected, device_address=None):
        """Update UI elements based on connection state."""
        if is_connected:
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.device_combo.config(state=tk.DISABLED)
            self.status_var.set(f"Connected to {device_address}")
        else:
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.device_combo.config(state="readonly")
            self.status_var.set("Disconnected")

    def update_temperature_display(self, min_temp, max_temp, avg_temp, frame_count, fps):
        """Update the temperature display with new values."""
        self.min_temp_var.set(f"{min_temp:.1f} °C")
        self.max_temp_var.set(f"{max_temp:.1f} °C")
        self.avg_temp_var.set(f"{avg_temp:.1f} °C")
        self.frame_count_var.set(str(frame_count))
        self.fps_var.set(f"{fps:.1f}")

    def reset_temperature_display(self):
        """Reset the temperature display to default values."""
        self.min_temp_var.set("--")
        self.max_temp_var.set("--")
        self.avg_temp_var.set("--")
        self.frame_count_var.set("0")
        self.fps_var.set("0.0")

    def set_status(self, message):
        """Update the status bar message."""
        self.status_var.set(message)

    def get_selected_device_index(self):
        """Get the currently selected device index."""
        return self.device_combo.current()

    def on_close(self):
        """Handle window close event."""
        self.destroy()


class SenxorController:
    """Controller component that manages models and handles events."""

    def __init__(self):
        self._update_interval = 50  # ms

        # Create models
        self.temp_model = TemperatureModel()
        self.thermal_model = None  # SenxorThread will be our device model

        # Data ready flag, observed by the UI thread
        self.data_ready = False

        # Create the view
        self.view = SenxorView()

        # Device state
        self.available_devices = []

        # Bind events to view components
        self._bind_events()

        # Start UI update loop
        self._schedule_ui_update()

        # Initial device refresh
        self._refresh_devices()

    def _bind_events(self):
        """Bind event handlers to view components."""
        self.view.refresh_btn.config(command=self._refresh_devices)
        self.view.connect_btn.config(command=self._connect)
        self.view.disconnect_btn.config(command=self._disconnect)
        self.view.protocol("WM_DELETE_WINDOW", self._on_close)

    def _refresh_devices(self):
        """Refresh the list of available devices."""
        try:
            self.available_devices = list_senxor()
            self.view.update_device_list(self.available_devices)
        except Exception as e:
            self.view.set_status(f"Error listing devices: {e}")
            showerror("Device Error", f"Error listing devices: {e}")

    def _connect(self):
        """Connect to the selected device and initialize device model."""
        selected_index = self.view.get_selected_device_index()
        if selected_index < 0:
            return

        address = self.available_devices[selected_index]

        try:
            # Create and initialize the device model (SenxorThread)
            self.senxor = Senxor(address)
            self.thermal_model = SenxorThread(self.senxor, self._frame_listener)

            # Start the device model
            self.thermal_model.start()

            # Update UI state
            self.view.update_connection_state(True, address)
        except Exception as e:
            self.thermal_model = None
            showerror("Connection Error", f"Failed to connect: {e}")

    def _disconnect(self):
        """Disconnect from the current device and cleanup device model."""
        if self.thermal_model:
            self.thermal_model.stop()
            self.thermal_model = None

        # Reset the temperature model
        self.temp_model.reset_model()

        # Reset the temperature display
        self.view.reset_temperature_display()

        # Update UI state
        self.view.update_connection_state(False)

    def _frame_listener(self, header, frame):
        """Listener callback for new frames from the device model.

        This is called in the device model's notification thread, so it must be
        lightweight and non-blocking. We just update the temperature model and return.
        """
        self.temp_model.update_frame(header, frame)
        self.data_ready = True

    def _update_ui(self):
        """Update the UI with the latest data from the temperature model."""
        # This runs in the main thread
        if self.data_ready:
            self.view.update_temperature_display(
                self.temp_model.min_temp,
                self.temp_model.max_temp,
                self.temp_model.avg_temp,
                self.temp_model.frame_count,
                self.temp_model.fps,
            )
            self.data_ready = False

    def _schedule_ui_update(self):
        """Schedule the next UI update."""
        self._update_ui()
        self.view.after(self._update_interval, self._schedule_ui_update)

    def _on_close(self):
        """Handle window close event."""
        # Cleanup device model
        if self.thermal_model:
            self.thermal_model.stop()
        self.view.on_close()

    def run(self):
        """Start the application."""
        self.view.mainloop()


def main():
    # Create and run the application
    app = SenxorController()
    app.run()


if __name__ == "__main__":
    main()
