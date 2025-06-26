# Development Rules

This document outlines the coding standards and best practices for the pysenxor project.

It can be used to guide AI agent development behavior and ensure consistent development standards.

## Development Environment

### Tools

- **uv**: Package manager and virtual environment tool for Python
  - Create virtual environment: `uv venv --seed`
  - Install dependencies: `uv sync`
  - Install doc dependencies: `uv sync --group doc`
  - Run commands or scripts: `uv run pytest`, `uv run example/basic_stream.py`

- **mkdocs-material**: Documentation system
  - Build documentation: `uv run mkdocs build`
  - Serve documentation locally: `uv run mkdocs serve`
  - Uses `mkdocstrings[python]` to extract docstrings and generate API reference

## Logging Guidelines

### Structured Logging

We use `structlog` for logging to provide consistent, machine-parseable logs.

#### General Rules

- Use short, concise log messages (ideally 2-10 words)
- Avoid f-strings in log messages
- Pass contextual data as keyword arguments
- Use `bind()` to attach context to loggers
- Keep log messages in English, even in international projects

#### Message Style

```python
# Good
logger.info("connection established", address=addr)
logger.debug("frame received", shape=frame.shape, timestamp=ts)
logger.error("read failed", exc_info=exc, attempts=retry_count)

# Bad - using f-strings
logger.info(f"Connection established to {addr}")

# Bad - too verbose
logger.info("Successfully established a new connection to the remote server at the specified address and port")
```

#### Common Log Fields

Standardize field names across the codebase:

| Field Name | Description      | Example     |
| ---------- | ---------------- | ----------- |
| `address`  | Device address   | `"COM3"`    |
| `shape`    | Data dimensions  | `(32, 32)`  |
| `size`     | Data size        | `1024`      |
| `count`    | Number of items  | `5`         |
| `status`   | Operation status | `"success"` |

Note: To keep consistency, shape is always (height, width) to adopt numpy's convention. dsize is always (width, height).
size is always for the 1-dim array.

#### Logger Creation

```python
# Module-level logger
from structlog import get_logger
logger = get_logger("senxor.module_name")

# Context-bound logger
self._log = logger.bind(address=address)
```

#### Log Levels

- `debug`: Detailed information, typically of interest only when diagnosing problems
- `info`: Confirmation that things are working as expected
- `warning`: Indication that something unexpected happened, but the application still works
- `error`: Due to a more serious problem, the application has not been able to perform a function
- `exception`: An exception occurred, should exit the program

#### Error vs Exception Logging

- Use `logger.error()` when you want to log an error condition without the stack trace
- Use `logger.exception()` when you want to include the stack trace and raise the exception

```python
# Good - log error without stack trace
logger.error("connection failed", address=addr)

# Good - log exception with stack trace
try:
    connect_to_device(addr)
except ConnectionError as e:
    logger.exception("connection failed", address=addr)
    raise
```

## Error Handling

### Exception Messages

- Exception messages should be descriptive and helpful
- Use complete sentences with proper capitalization
- Include specific details about what went wrong
- Include guidance on how to fix the issue when appropriate
- Exception messages can be longer than log messages (medium length)
- Simple, clear messages are preferred when the error is self-explanatory

```python
# Good
raise ValueError("A listener with name 'my_listener' already exists")
raise TimeoutError(
    "Listener processing backlog detected: previous data is still being processed.",
    "Ensure all listener callbacks are lightweight and non-blocking.",
)
raise ConnectionError("Senxor not connected")

# Bad - too short/cryptic
raise ValueError("duplicate name")
raise TimeoutError("processing timeout")

# Bad - too verbose
raise ValueError("The system has detected that you are attempting to add a listener with a name that is already registered in the internal listener registry, which is not allowed because listener names must be unique within a single reader instance.")
```

### Error Handling Patterns

- Use specific exception types that match the error condition
- Catch exceptions at the appropriate level
- Use `contextlib.suppress` for ignoring specific exceptions during cleanup
- Include context in exception messages

```python
# Good - specific exception with context
if name in self._listeners:
    raise ValueError(f"A listener with name '{name}' already exists")

# Good - suppressing exceptions during cleanup
with contextlib.suppress(Exception):
    self._reader.stop()
```

### Balancing Log Messages and Exceptions

- **Log Messages**: Short, concise, focused on the event
- **Exception Messages**: More detailed, focused on explaining the problem and potential solutions

Example:

```python
# Log message is short
self._log.error("listener timeout")

# Exception message is more detailed
raise TimeoutError(
    "Listener processing backlog detected: previous data is still being processed.",
    "Ensure all listener callbacks are lightweight and non-blocking.",
)
```

## Code Organization

### Class Structure

- Place public methods first
- Group related methods together
- Use private methods (with `_` prefix) for implementation details
- Implement special methods (`__enter__`, `__exit__`, etc.) at the end of the class

### Threading Patterns

- Use descriptive thread names for debugging
- Always join threads during cleanup
- Use locks to protect shared resources
- Set daemon=True for background threads
- Use events for signaling between threads

```python
self._reader_thread = threading.Thread(
    target=self._run,
    name=f"{self._name}Read",
    daemon=True,
)
```

## Documentation

### Docstrings

- Use NumPy-style docstrings for all public methods and classes
- Document parameters, return values, and exceptions
- Include examples for complex functionality

```python
def add_listener(self, fn: Callable[[Any], None], name: str | None = None) -> str:
    """Register a listener callback.

    Parameters
    ----------
    fn
        Callable invoked with the latest data object. **Must be
        lightweight and non-blocking**.
    name
        Optional unique identifier. If omitted, an automatic ``listener_X``
        name is assigned.

    Returns
    -------
    str
        The listener name actually registered.

    Raises
    ------
    RuntimeError
        If the listener pattern is disabled.
    ValueError
        If *name* already exists.
    """
```

## Testing

### Test Structure

- Use pytest for testing
- Group tests by class/module in test files
- Use descriptive test names that explain what is being tested
- Use fixtures for common setup
- Mock external dependencies

### Test Coverage

- Test happy paths (normal operation)
- Test edge cases and error conditions
- Test thread safety for concurrent code
- Test resource cleanup

```python
def test_slow_listener(self, mock_reader_func):
    """Test that slow listeners cause TimeoutError."""
    reader = _BackgroundReader(mock_reader_func, "SlowListener")

    # Create a slow listener that blocks
    def slow_listener(data):
        time.sleep(0.5)  # Block for a long time

    reader.add_listener(slow_listener)
    reader.start()

    # Wait for the first notification to start
    time.sleep(0.1)

    # Force a second read while the first is still processing
    # This should raise a TimeoutError in the reader thread
    with patch.object(reader, "_reader_func") as mock_read:
        # Make sure the mock returns a value
        mock_read.return_value = 999

        # Call _read_once directly to simulate the reader thread
        with pytest.raises(TimeoutError, match="Listener processing backlog detected"):
            reader._read_once()
```

## Code Examples and Usage Patterns

### Example Code in Documentation

- Include usage examples in module and class docstrings
- Show both simple and advanced use cases
- Highlight best practices and common patterns

```python
"""
Examples
--------
Basic usage:

>>> from senxor import SenxorThread
>>> with SenxorThread("COM3") as senxor:
...     header, frame = senxor.read()
...     process_frame(frame)

Using the listener pattern:

>>> def on_new_frame(header, frame):
...     print(f"New frame received: {frame.shape}")
...
>>> with SenxorThread("COM3") as senxor:
...     senxor.add_listener(on_new_frame)
...     time.sleep(5)  # Process frames in background
"""
```

### Common Design Patterns

#### Consumer-Producer Pattern

```python
# Producer thread
def producer():
    while running:
        data = generate_data()
        queue.put(data)

# Consumer thread
def consumer():
    while running:
        data = queue.get()
        process_data(data)
        queue.task_done()
```

#### Observer/Listener Pattern

```python
class Subject:
    def __init__(self):
        self._listeners = {}

    def add_listener(self, fn, name=None):
        # Add listener implementation

    def remove_listener(self, name):
        # Remove listener implementation

    def notify_listeners(self, data):
        # Notify all listeners
```

#### Background Processing Pattern

```python
class BackgroundProcessor:
    def __init__(self):
        self._thread = None
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _run(self):
        while self._running:
            self._process_once()
```

### API Design Principles

- Provide both simple and advanced interfaces
- Use context managers for resource management
- Support both synchronous and asynchronous patterns when appropriate
- Follow the principle of least surprise
