# Device Control and Status

Most day-to-day interaction with a SenXor device happens through its registers (raw 8-bit values) and the higher-level fields (individual bits or bit-ranges inside those registers). This page shows you how to inspect device status and apply configuration changes using these two powerful APIs.

---

## How the Register System Works

The core of every SenXor device is the MI48 chip, which exposes a bank of 8-bit registers. Each register has:

- Address (e.g., `0xB1`)
- Value (e.g., `0b00000000`)

To save space, small pieces of configuration, called fields, are packed into those 8-bit registers. Each field represents a specific function or status bit, and several fields may share a single register.

### Example: Unpacking a Register

Take the `FRAME_MODE` register at address `0xB1` as an example. It's an 8-bit value structured as follows:

| Bit 7    | Bit 6    | Bit 5     | Bits 4-2     | Bit 1             | Bit 0            |
|:---------|:---------|:----------|:-------------|:------------------|:-----------------|
| Reserved | Reserved | NO_HEADER | READOUT_MODE | CONTINUOUS_STREAM | GET_SINGLE_FRAME |

Instead of forcing you to do binary math (like `(value & 0b00000010) >> 1`), `pysenxor` provides a simple, name-based API: `dev.fields.CONTINUOUS_STREAM`.

---

## Getting Help: Discovering Registers and Fields

After connecting to your device (see Quick Start for details), you can easily explore available registers and fields, as well as their descriptions and help texts.

```python
>>> import senxor
>>> addrs = senxor.list_senxor()
>>> addrs
['COM3']
>>> dev = senxor.connect(addrs[0])
>>> print(f"Connected to device {dev.address}")
Connected to device COM3
```

### Inspecting Registers

```python
>>> regs = dev.regs
>>> print(regs.FRAME_MODE)
FRAME_MODE (0xB1)
>>> print(regs.FRAME_MODE.desc)
Control capture and readout of thermal data
```

---

### Inspecting Fields

```python
fields = dev.fields
print(fields.FRAME_RATE_DIVIDER)
print(fields.FRAME_RATE_DIVIDER.desc)
print(fields.FRAME_RATE_DIVIDER.help)
```

All `regs` and `fields` support autocompletion in most editors.

You can also access register and field metadata statically, without connecting to a device:

```python
from senxor.regmap import Fields, Registers
print(Fields.FRAME_RATE_DIVIDER.desc)
print(Registers.FRAME_MODE.desc)
```

---

## Reading Device Status and Configuration

You can use fields and registers to read device information, configuration, and status.

### Example: Reading Device Information

```python
>>> mcu_type = dev.fields.MCU_TYPE
>>> mcu_type.get(), mcu_type.display()
(3, 'MI48G')
```

The `.display()` method provides a human-readable string for enumerated or mapped values.

### Example: Reading Device Configuration

```python
>>> emissivity = dev.fields.EMISSIVITY
>>> emissivity.display()
'56%'

>>> dev.fields.OTF.display()
'1.06'

# Dictionary-style access
>>> dev.fields["OTF"].get()
6
```

### Example: Reading Device Status

Some fields and registers reflect the device's current state. For general usage. For example:

```python
>>> dev.fields.CONTINUOUS_STREAM.get()
0  # 0 = disabled, 1 = enabled

>>> dev.regs.FRAME_MODE.get()
0b00000000
```

---
## Understanding Caching and IO

The `.get()` method on registers and fields reads the value from the device and caches it. Subsequent `.get()` calls will return the cached value, unless the register/field is marked as auto-reset (i.e., its value may change due to hardware events).

For example, `DATA_READY` indicates the frame data readiness status: if `DATA_READY` is 0, the frame data is not ready; if it is 1, the frame data is ready.


For auto-reset fields (such as `DATA_READY`), `.get()` always queries the device directly, bypassing the cache. Frequent polling of such fields may impact device performance, especially for high-frequency operations.

The `.display()` and `.value` properties both call `.get()` internally.

To force a direct hardware read and update the cache, use the `.read()` method on registers:

```python
fresh_value = dev.regs.FRAME_MODE.read()
```

If you want a snapshot of all cached values (without triggering any IO), use:

```python
cached_regs = dev.regs.status
cached_fields = dev.fields.status
```

### When (and Why) to Call `refresh_regmap()`

Sometimes you need a full, up-to-date picture of the device's configuration—for example, right before saving a diagnostic log or after an external system has modified the camera settings. Instead of crawling through every register one-by-one (which could generate hundreds of I/O transactions), you can issue a *single* bulk read:

```python
dev.refresh_regmap()  # single round-trip to the device

```

What just happened?

1. The library performed one low-level operation to read all registers.
2. Both register and field caches were refreshed in RAM.
3. Subsequent `.get()` calls will now hit the fresh cache, keeping I/O traffic to zero until you ask for another live read.

> Performance Tip – For normal UI updates or tight acquisition loops, rely on cached values (`.status`) and refresh only when real-time accuracy is essential. A polling rate faster than 10 Hz (every 100 ms) is generally unnecessary and may congest the bus.

---

## Configuring the Device

You can change device settings by writing to fields or registers. The recommended way is to use field-level access for clarity and safety.

### Example: Setting the Frame Rate

```python
>>> dev.fields.FRAME_RATE_DIVIDER.get()
4
>>> dev.fields.FRAME_RATE_DIVIDER.set(1)
>>> dev.fields.FRAME_RATE_DIVIDER.get()
1
```

### Example: Adjusting Emissivity

```python
>>> dev.fields.EMISSIVITY.set(98)
>>> dev.fields.EMISSIVITY.get()
98
```

---

## Alternative APIs and Best Practices

While attribute-style access (`dev.fields.FIELD_NAME`) is recommended for its clarity and auto-completion support, other helpers exist:

- Dictionary access – `dev.fields["FIELD_NAME"]`
- Register-level direct access – `dev.regs.read_reg(0xCA)` and `dev.regs.write_reg(0xCA, 98)`
- Batch operations – `dev.regs.read_regs([0x00, 0x01, 0xB1])` or `dev.fields.set_fields({"FRAME_RATE_DIVIDER": 2, "EMISSIVITY": 90})`
- Iteration –
  ```python
  >>> for reg in dev.regs:
  ...     print(hex(reg.addr), reg.name)
  >>> for field in dev.fields:
  ...     print(field.name)
  ```

  For more details, please refer to the [API Reference](../api/regmap.md).

### Best Practices

- Prefer fields when available – less bit-twiddling, fewer mistakes.
- Refresh sparingly – call `refresh_regmap()` only when you need a full, live snapshot.
- Leverage `.display()` – convert raw values into human-readable strings.
- Monitor error flags – e.g., `dev.fields.CAPTURE_ERROR` – to keep your application robust.
