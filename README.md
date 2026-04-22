# pysenxor

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)](https://img.shields.io/badge/python-%3E%3D3.9-blue)

A Python Library for Meridian Innovation's thermal imaging devices.

- **Github repository**: <https://github.com/MeridianInnovation/pysenxor-lite/>
- **Documentation** <https://MeridianInnovation.github.io/pysenxor-lite/>

## Overview

This package can let users interact with Meridian Innovation's thermal imaging devices.

## Features

- Device discovery and listing
- Multiple interfaces supported(USB serial, TCP/IP, GPIO, etc.)(Coming soon)
- Easy device connection and management
- Configuration and status read and write
- Non-blocking mode for frame reading
- Thermal data processing utilities
- Thread-safe for multi-threaded use
- Lightweight and minimal dependencies(no cv2 or matplotlib required)

## Installation

We strongly recommend using `uv` to manage the virtual environment.

To install `uv`, please refer to the [official documentation](https://docs.astral.sh/uv/getting-started/installation/).


On Linux, if you plan to use `pysenxor-lite` together with `opencv`, `qt`, `tkinter`, etc., `uv` can help avoid many system dependency issues.

### 1. Recommended: use `uv`

Create a virtual environment and install the package with `uv`:

```bash
uv init   # create a pyproject.toml file, if you already have one, skip this step
uv add pysenxor-lite # Add the package to the virtual environment
```

or without `pyproject.toml`:

```bash
uv venv --seed   # Create a virtual environment and install the dependencies
uv pip install pysenxor-lite # Install the package
```

### 2. Use `pip`

```bash
python -m pip install pysenxor-lite
```

### 3. Linux notes

If you are using SenXor via USB serial on Linux, ensure you have the proper permissions to access the serial port. You can add your user to the `dialout` group and reboot to apply the changes:

```bash
sudo usermod -aG dialout $USER
```

### 4. Development installation

For development, clone the repository and sync the environment with `uv`:

```bash
git clone https://github.com/MeridianInnovation/pysenxor-lite.git
cd pysenxor-lite
uv sync
```

This will create a virtual environment and install pysenxor-lite in editable mode.

If you prefer `pip`, you can use:

```bash
git clone https://github.com/MeridianInnovation/pysenxor-lite.git
cd pysenxor-lite
python -m pip install -e .
```

## Usage

This section gives a short overview of how to use the `pysenxor` library. For more detailed examples, see the [documentation](https://MeridianInnovation.github.io/pysenxor-lite/).

### Connect to a device

You can list available devices and connect to the first one:

```python
from senxor import connect, list_senxor

devices = list_senxor("serial")
if not devices:
    raise ValueError("No devices found")

dev = connect(devices[0])
```

To check the connection and device info:

```python
print(f"Connected to {dev.name}, is_streaming: {dev.is_streaming}")
print(f"Module: {dev.get_module_type()}, FW: {dev.get_fw_version()}, SN: {dev.get_sn()}")
```

When you are done, close the device:

```python
dev.close()
```

### Stream and read frames

After connecting, you can start the stream and read frames. `read()` returns `(header, frame)`: `header` is a uint16 array or None, and `frame` is a 2D float32 array of temperature in Celsius.

```python
dev.start_stream()

header, frame = dev.read()
print(f"Frame shape: {frame.shape}, dtype: {frame.dtype}")
print(f"Min: {frame.min()} C, max: {frame.max()} C, mean: {frame.mean():.1f} C")
```

By default `read()` blocks until a frame is available. If you pass `block=False`, it returns immediately and `header` and `frame` may be None when no frame is ready:

```python
header, frame = dev.read(block=False)
if frame is None:
    print("No new frame")
```

To stop streaming but keep the connection open, call `stop_stream()`. To stop and disconnect, use `close()`.

### Process and visualize data

Frames are NumPy arrays, so you can index, slice, and use methods like `.min()`, `.max()`, and `.mean()`. The `senxor.proc` module provides normalization, scaling, and colormaps (without requiring cv2 or matplotlib):

```python
import numpy as np
from senxor.proc import normalize, enlarge, colormaps, apply_colormap

uint8_image = normalize(frame, dtype=np.uint8)
float32_image = normalize(frame, dtype=np.float32)
enlarged = enlarge(frame, scale=2)
```

To get an RGB image, you can apply a built-in colormap such as `inferno`, `jet`, `viridis`, `magma`, `plasma`, or `turbo`:

```python
cmap = colormaps["inferno"]
normalized = normalize(frame, dtype=np.float32)
colored_image = apply_colormap(normalized, lut=cmap)
```

You can display or save the result with cv2 or matplotlib. Note that cv2 uses BGR order:

```python
import cv2
bgr = cv2.cvtColor(colored_image, cv2.COLOR_RGB2BGR)
cv2.imshow("senxor", bgr)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

```python
import matplotlib.pyplot as plt
plt.imshow(colored_image)
plt.show()
```

### Learn more

- [Documentation](https://MeridianInnovation.github.io/pysenxor-lite/)

## License

This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

You may freely use, modify, and distribute this software for both open-source and commercial purposes, subject to the terms of the license.

## Copyright

Unless otherwise specified, all files in the source code directory(`senxor/`) are copyrighted by Meridian Innovation.

Copyright (c) 2025 Meridian Innovation. All rights reserved.

## Contributing

We welcome contributions from the community.

By submitting a pull request, you certify compliance with the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). This means you assert that:

- You wrote the code or have the right to submit it;
- You grant us the right to use your contribution under the project license.

Please add the following line to your Git commit message to confirm DCO compliance:

`Signed-off-by: Your Name your.email@example.com`

You can automate this with `git commit -s`.

See more details in [Contributing Guide](./CONTRIBUTING.md).

## Contact

For support or inquiries, please contact:

- Email: info@meridianinno.com
