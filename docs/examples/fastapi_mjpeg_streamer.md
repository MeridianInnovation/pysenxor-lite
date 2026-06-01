---
title: FastAPI MJPEG Streamer
description: Serve Senxor frames as an MJPEG HTTP stream with FastAPI and asyncio.
navigation:
  title: FastAPI MJPEG Streamer
  order: 5
---

# FastAPI MJPEG Streamer

This example integrates Senxor non-blocking reads into an asyncio-based web framework (FastAPI). A background worker coroutine fetches and encodes frames to JPEG, and serves them as a continuous Motion JPEG (MJPEG) HTTP stream viewable in any browser.

```python
{% include-markdown "../../example/fastapi_mjpeg_streamer.py" %}
```
