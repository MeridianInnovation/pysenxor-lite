# Loading Settings from Files

pysenxor provides a powerful configuration system that allows you to load device settings from files and automatically apply them to SenXor devices. This system supports conditional configuration, enabling automatic selection of appropriate settings based on the device's current state (such as frame size, device type, etc.).

---

## Configuration File Format

The configuration system supports three file formats: YAML, TOML, and JSON. All formats follow the same structure:

### Basic Structure

```yaml
profiles:
  - name: "profile_name"
    desc: "profile_description" # optional
    when: "condition_expression" # optional
    settings:
      field_1: value
      field_2: value
```

### YAML Format Example

```yaml
profiles:
  - name: "default"
    desc: "Default settings for general use"
    settings:
      EMISSIVITY: 83
      FRAME_RATE_DIVIDER: 4

  - name: "Panther"
    desc: "Special settings for Panther Module" # Panther Module has image size: w:160, h:120
    when: "frame_shape == (120, 160)"
    settings:
      STARK_ENABLE: false
      EMISSIVITY: 95
```

### TOML Format Example

```toml
[[profiles]]
name = "default"
desc = "Default settings for general use"
[profiles.settings]
EMISSIVITY = 83
FRAME_RATE_DIVIDER = 4

[[profiles]]
name = "Panther"
desc = "Special settings for Panther Module"
when = "frame_shape == (120, 160)"
[profiles.settings]
STARK_ENABLE = false
EMISSIVITY = 95
```

### JSON Format Example

```json
{
  "profiles": [
    {
      "name": "default",
      "desc": "Default settings for general use",
      "settings": {
        "EMISSIVITY": 83,
        "FRAME_RATE_DIVIDER": 4
      }
    },
    {
      "name": "Panther",
      "desc": "Special settings for Panther Module",
      "when": "frame_shape == (120, 160)",
      "settings": {
        "STARK_ENABLE": false,
        "EMISSIVITY": 95
      }
    }
  ]
}
```

---

## Conditional Expressions (when field)

The `when` field allows you to conditionally apply configurations based on the device's current state. Conditional expressions use Python syntax and support the following operations:

### Supported Syntax

- **Comparison operators**: `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Logical operators**: `and`, `or`, `not`
- **Variables**: Device properties and field values
- **Constants**: Numbers, strings, boolean values

### Available Context Variables

Conditional expressions can access the following device information:

| Variable Name  | Type  | Description                               |
|----------------|-------|-------------------------------------------|
| `frame_shape`  | tuple | Device frame size, e.g., `(120, 160)`     |
| `address`      | str   | Device address, e.g., `"COM3"`            |
| `type`         | str   | Device type                               |
| `[field_name]` | int   | Current value of any non-auto-reset field |

---

## Usage

### Loading Configuration from File

```python
from senxor import connect
from senxor.settings import load, apply

# Load configuration from file
settings = load("my_settings.yaml")

# Connect to device
with connect() as senxor:
    # Apply configuration
    apply(senxor, settings)
```

### Loading Configuration from Various Sources

The `loads` function is designed to handle non-standard configuration sources such as network-transmitted byte streams, already opened file handles, or configuration data received from external systems.

```python
from senxor.settings import loads, apply

# From a file handle
with open("config.yaml", "r") as f:
    settings = loads(f, filetype="yaml")

# From bytes (e.g., network transmission)
config_bytes = b"""
profiles:
  - name: "default"
    settings:
      OTF: 2
      EMISSIVITY: 83
  - name: "panther"
    when: "frame_shape == (120, 160)"
    settings:
      STARK_ENABLE: false
      MEDIAN_ENABLE: false
"""
settings = loads(config_bytes, filetype="yaml")

```

### Applying Single Configuration

```python
# Apply specific configuration
profile = settings["default"]
apply(senxor, profile)
```

---

## Practical Examples

### Example 1: Module-specific settings

```yaml
# module_config.yaml
profiles:
  - name: "panther_module"
    desc: "Panther Module specific settings"
    when: "frame_shape == (120, 160)"
    settings:
      STARK_ENABLE: false
      MEDIAN_ENABLE: false
      EMISSIVITY: 85
      FRAME_RATE_DIVIDER: 2

  - name: "cougar_module"
    desc: "Cougar Module specific settings"
    when: "frame_shape == (60, 80)"
    settings:
      STARK_ENABLE: true
      MEDIAN_ENABLE: true
      EMISSIVITY: 90
      FRAME_RATE_DIVIDER: 3
```

```python
from senxor import connect
from senxor.settings import load, apply

with connect() as senxor:
    settings = load("module_config.yaml")
    apply(senxor, settings)
    print(f"Applied configuration for {senxor.get_shape()} device")
```

### Example 2: Firmware Version-Based Configuration

```yaml
# firmware_config.yaml
profiles:
  - name: "legacy_firmware"
    desc: "Settings for older firmware versions"
    when: "(FW_VERSION_MAJOR, FW_VERSION_MINOR) < (4, 3)"
    settings:
      STARK_ENABLE: true
      MEDIAN_ENABLE: true
      TEMPORAL_ENABLE: true
      FRAME_RATE_DIVIDER: 4

  - name: "modern_firmware"
    desc: "Settings for newer firmware versions with enhanced features"
    when: "(FW_VERSION_MAJOR, FW_VERSION_MINOR) >= (4, 3)"
    settings:
      STARK_ENABLE: false
      MEDIAN_ENABLE: false
      TEMPORAL_ENABLE: false
      FRAME_RATE_DIVIDER: 2
```
