# `v4l2-virtual-camera.py`

This example, `v4l2-virtual-camera.py`, allows you to stream the thermal camera feed to a virtual video device using FFmpeg and v4l2loopback.

You can find the source code at [Here](https://github.com/MeridianInnovation/pysenxor/blob/main/example/v4l2-virtual-camera.py).

## Features

- **Flexible Output Options**: Supports local display of thermal images or streaming to a virtual video device (e.g., `/dev/video1`) using FFmpeg for integration with applications like Zoom, OBS, or VLC.
- **Advanced Image Processing**: Includes temporal smoothing, spatial median blur, and optional CLAHE (Contrast Limited Adaptive Histogram Equalization) for enhanced image quality.
- **Customizable Parameters**: Allows configuration of colormap, emissivity, scaling factor, and smoothing levels via command-line arguments.
- **Min/Max Temperature Annotation**: Automatically annotates the minimum and maximum temperature points on the displayed or streamed image.
- **Clean Exit Handling**: Gracefully handles interruptions (e.g., Ctrl+C) to ensure proper cleanup of camera resources and windows.

## Usage Examples

- **Local Display**:
  ```bash
  python thermal_toolbox.py --scale 6 --colormap viridis --smoothing-level 7
  ```
- **Streaming to Virtual Camera** (requires FFmpeg and v4l2loopback):
  ```bash
  python thermal_toolbox.py --stream | ffmpeg -f rawvideo -pixel_format rgb24 -video_size 640x480 -framerate 5 -i - -f v4l2 /dev/video1
  ```

## Advantages

- **Versatility**: Seamlessly switch between local visualization and streaming, making it ideal for diverse use cases like live monitoring or video conferencing.
- **Enhanced Image Quality**: Advanced processing options improve clarity and reduce noise in thermal images.
- **User-Friendly**: Intuitive command-line interface with sensible defaults for quick setup.
- **Integration with C++ Version**: This Python example complements the C++ MI48Dx Serial Driver ([HefnySco/mi48dx-serial-driver](https://github.com/HefnySco/mi48dx-serial-driver)), which offers a lightweight alternative for processing raw binary data streams and converting 16-bit pixel values into Kelvin temperatures with frame statistics (MIN/MAX/AVG). The C++ version is ideal for performance-critical applications or environments where Python dependencies are a constraint.

## C++ Alternative

For a lower-level, high-performance interface to the MI48 thermal imaging sensor, check out the [C++ MI48Dx Serial Driver](https://github.com/HefnySco/mi48dx-serial-driver). It provides direct access to raw data streams and is optimized for minimal overhead, making it suitable for embedded systems or real-time applications.
