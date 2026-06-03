---
title: Thermal + RGB Recorder
description: Record synchronized thermal and RGB video streams to disk.
navigation:
  title: Thermal + RGB Recorder
  order: 4
---

# Thermal + RGB Recorder

This example resolves the blocking nature of `cv2.VideoCapture` and `cv2.VideoWriter` by wrapping the RGB camera in a background thread using `senxor.cv_utils.CVCamThread`. It combines both frames side-by-side in real time and records the stream to a local video file.

```python
--8<-- "example/thermal_rgb_recorder.py"
```
