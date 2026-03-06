# Thermal + RGB Recorder

This example resolves the blocking nature of `cv2.VideoCapture` and `cv2.VideoWriter` by wrapping the RGB camera in a background thread using `senxor.cv_utils.CVCamThread`. It combines both frames side-by-side in real time and records the stream to a local video file.

```python
{% include-markdown "../../example/thermal_rgb_recorder.py" %}
```
