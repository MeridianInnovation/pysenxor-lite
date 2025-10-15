# pysenxor

A Python Library for Meridian Innovation's thermal imaging devices.

## Overview

This package can let users interact with Meridian Innovation's thermal imaging devices.

## Features

- Device discovery and listing
- Multiple interfaces supported (USB serial, TCP/IP, GPIO, etc.) (Coming soon)
- Easy device connection and management
- Configuration and status read and write
- Non-blocking mode for frame reading
- Thermal data processing utilities
- Thread-safe for multi-threaded use
- Lightweight and minimal dependencies (no cv2 or matplotlib required)

## Installation

To install the project, run the following command:

```bash
python -m pip install git+https://github.com/HefnySco/pysenxor-lite.git

# Install from local:
git clone https://github.com/HefnySco/pysenxor-lite.git
cd pysenxor-lite
python -m pip install .
```

## Usage

### Import

```python
import senxor
```

### List available devices

You can list all available devices by calling the `list_senxor` function.

```python
addrs = senxor.list_senxor()
for addr in addrs:
    print(addr)
```

You can also specify the type of device to list.

```python
addrs = senxor.list_senxor("serial") # list all usb serial devices
```

### Connect to senxor

Once you have the device address, you can connect to the device.

There are several ways to connect to a Senxor device.

0. Use the context manager provided by the `connect` function.

```python
addr = addrs[0]

with senxor.connect(addr, "serial") as dev:
    print(dev.is_connected)

print(dev.is_connected)
```

The `with` statement will ensure that the connection is closed after the block is executed.

It's equivalent to:

```python
dev = senxor.connect(addr, "serial")
print(dev.is_connected)
dev.close()
```

You can also use the `connect` without specifying the address or type.

In this case, the function will automatically find the first available device.

```python
dev = senxor.connect()
print(dev.is_connected)
```

To be compatible with the old version, below is the equivalent code.

```python
from senxor.utils import connect, connect_senxor

dev = connect()
print(dev.is_connected)

dev = connect_senxor()
print(dev.is_connected)
```

### Start Stream and Read Data

Once you have connected to the device, you can start the stream and read data from the device.

```python
dev.start_stream()

header, frame = dev.read()

if frame is not None:
    print(f"Frame shape: {frame.shape}, dtype: {frame.dtype}")
    # Output: Frame shape: (120, 160), dtype: float32

    print(f"Frame min: {frame.min()} C, max: {frame.max()} C, mean: {frame.mean():.1f} C")
    # Output: Frame min: 20.3 C, max: 34.1 C, mean: 27.2 C

dev.close() # Stop the stream and close the connection
```

The `read` method will return a tuple of `(header, frame)` or `(None, None)` if the frame is not available (if block is False).

The `header` is a uint16 np.ndarray with some information about the frame.

In default, the `frame` is a 2D float32 np.ndarray, which is the temperature in Celsius.

The `read` method is default in blocking mode, which means it will wait until a new frame is available.

You can set the `block` parameter to `False` to make the `read` method non-blocking.

```python
header, frame = dev.read(block=False)
if frame is None:
    print("No new frame is available")
```

### Process the data

You can use the `senxor.proc` module to process the data.

```python
import senxor.proc
```

Convert the frame to uint8 grayscale image.

Note: Due to the uint8 grayscale image has only 256 possible values, some information of the temperature frame may be lost.

```python
uint8_image = senxor.proc.normalize(frame, dtype=np.uint8)

# Or use the `remap`, it's equivalent to `normalize(frame, dtype=np.uint8)`
uint8_image = senxor.proc.remap(frame)
```

Convert the frame to float32 grayscale image.

The float grayscale image can keep all the information of the temperature frame.

```python
float32_image = senxor.proc.normalize(frame, dtype=np.float32)
```

Simply enlarge the image with a integer scale factor.

```python
enlarged_image = senxor.proc.enlarge(frame, scale=2) # only support integer scale factor
```

Get a built-in cv2 colormap or matplotlib colormap.

```python
cmap_cv_inferno = senxor.proc.get_colormap("inferno", "cv")
cmap_mpl_inferno = senxor.proc.get_colormap("inferno", "mpl")
```

Apply a colormap to the image.

```python
# This returns a RGB image
colored_image = senxor.proc.apply_colormap(frame, lut=cmap_cv_inferno)
```

!!! tip To keep the lightweight of the pysenxor, the `get_colormap` and `apply_colormap` doesn't need `cv2` or `matplotlib` as dependencies. They are based on the `colormap_tool` and `numpy` only.

### Display or save the thermal image

You can use the `cv2` or `matplotlib` to display or save the thermal image.

```python
import cv2

# Note: The cv2 uses BGR format instead of RGB format.
bgr_image = cv2.cvtColor(colored_image, cv2.COLOR_RGB2BGR)
cv2.imshow("senxor", bgr_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

```python
import matplotlib.pyplot as plt

plt.imshow(colored_image)
plt.show()
```

### Multi-threading

`senxor` is designed to be thread-safe.

You can interact with the device in multiple threads.

For example, you can read the data in a background thread, and read/write registers in the main thread. Which is useful for GUI applications.

### New Example: thermal_toolbox.py

This fork includes an additional example, `thermal_toolbox.py`, which enhances the interaction with SenXor thermal imaging devices. This script provides a flexible tool for both local display and streaming of thermal camera feeds, with advanced processing capabilities.

**Features of `thermal_toolbox.py`:**
- **Flexible Output Options**: Supports local display of thermal images or streaming to a virtual video device (e.g., `/dev/video1`) using FFmpeg for integration with applications like Zoom, OBS, or VLC.
- **Advanced Image Processing**: Includes temporal smoothing, spatial median blur, and optional CLAHE (Contrast Limited Adaptive Histogram Equalization) for enhanced image quality.
- **Customizable Parameters**: Allows configuration of colormap, emissivity, scaling factor, and smoothing levels via command-line arguments.
- **Min/Max Temperature Annotation**: Automatically annotates the minimum and maximum temperature points on the displayed or streamed image.
- **Clean Exit Handling**: Gracefully handles interruptions (e.g., Ctrl+C) to ensure proper cleanup of camera resources and windows.

**Usage Examples**:
- **Local Display**:
  ```bash
  python thermal_toolbox.py --scale 6 --colormap viridis --smoothing-level 7
  ```
- **Streaming to Virtual Camera** (requires FFmpeg and v4l2loopback):
  ```bash
  python thermal_toolbox.py --stream | ffmpeg -f rawvideo -pixel_format rgb24 -video_size 640x480 -framerate 5 -i - -f v4l2 /dev/video1
  ```

**Advantages**:
- **Versatility**: Seamlessly switch between local visualization and streaming, making it ideal for diverse use cases like live monitoring or video conferencing.
- **Enhanced Image Quality**: Advanced processing options improve clarity and reduce noise in thermal images.
- **User-Friendly**: Intuitive command-line interface with sensible defaults for quick setup.
- **Integration with C++ Version**: This Python example complements the C++ MI48Dx Serial Driver ([HefnySco/mi48dx-serial-driver](https://github.com/HefnySco/mi48dx-serial-driver)), which offers a lightweight alternative for processing raw binary data streams and converting 16-bit pixel values into Kelvin temperatures with frame statistics (MIN/MAX/AVG). The C++ version is ideal for performance-critical applications or environments where Python dependencies are a constraint.

**C++ Alternative**: For a lower-level, high-performance interface to the MI48 thermal imaging sensor, check out the [C++ MI48Dx Serial Driver](https://github.com/HefnySco/mi48dx-serial-driver). It provides direct access to raw data streams and is optimized for minimal overhead, making it suitable for embedded systems or real-time applications.

### More usage

For more usage and API reference, please refer to the Documentation.

## Examples

For beginners, there are some examples in the examples folder.

These examples provide a set of actual use cases of the `senxor` library.

* Connect device, read thermal data, convert data to image, use cv2 to display the image stream.
* Use thread to read data in background.
* Create a simple GUI application to display the thermal camera stream.
* `thermal_toolbox.py`: A versatile tool for displaying or streaming thermal camera feeds with advanced processing (see above).

## License

This project is licensed under the Apache License 2.0.

You may freely use, modify, and distribute this software for both open-source and commercial purposes, subject to the terms of the license.

## Copyright

Unless otherwise specified, all files in the source code directory (`senxor/`) are copyrighted by Meridian Innovation.

Copyright (c) 2025 Meridian Innovation. All rights reserved.

## Contributing

We welcome contributions from the community.

By submitting a pull request, you certify compliance with the Developer Certificate of Origin (DCO). This means you assert that:

* You wrote the code or have the right to submit it;
* You grant us the right to use your contribution under the project license.

Please add the following line to your Git commit message to confirm DCO compliance:

`Signed-off-by: mohammad.hefny@gmail.com`

You can automate this with `git commit -s`.

See more details in Contributing Guide.

## Contact

For support or inquiries, please contact:

## About

A python library to interact with SenXor thermal imaging devices.

## Footer

© 2025 GitHub, Inc.