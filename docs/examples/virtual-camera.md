# Virtual Camera

This example streams the Senxor thermal imaging feed to a **virtual webcam** that works as a system camera. You can use it in Zoom, OBS, Teams, or any application that uses a camera.

It runs on **Windows**, **Linux**, and **macOS**.

Source: [virtual-camera.py](https://github.com/MeridianInnovation/pysenxor-lite/blob/main/example/virtual-camera.py).

## Prerequisites by platform

### Windows

Install [OBS](https://obsproject.com/) (OBS Virtual Camera) or Unity Capture.

### Linux

Install and load v4l2loopback.

```bash
sudo apt-get install v4l2loopback-dkms
sudo modprobe v4l2loopback video_nr=1 card_label="Senxor Thermal" exclusive_caps=1
```

### macOS

Install OBS and enable OBS Virtual Camera.

## Usage

Default run:

```bash
python example/virtual-camera.py
```

View all options:

```bash
python example/virtual-camera.py --help
```

## Dependencies

- **pyvirtualcam**: virtual camera output.
- **typer**: CLI.
