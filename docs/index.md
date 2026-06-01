---
title: Overview
description: A Python library for Meridian Innovation's thermal imaging devices.
navigation:
  title: Overview
---

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

## Next Steps

- [Tutorials](guides/1.connect_device.md)
- [API Reference](api/regmap.md)
