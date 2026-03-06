# Multi-Senxor Alarm

This example scans all available Senxor devices, connects to them, and registers a data callback. If a certain temperature threshold is exceeded, it triggers an alarm, logs the event as JSON, and asynchronously saves an image without blocking other sensors.

```python
{% include-markdown "../../example/multi_senxor.py" %}
```
