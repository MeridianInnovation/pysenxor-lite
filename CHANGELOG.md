## v3.1.0 (2026-01-28)

!!! BREAKING CHANGE !!!

This version is a breaking change, some interfaces and class names have changed, and the old code may not work properly.

### Feat

1. Support new Cheetah 50x50 module
2. Rrefactor and rename the `senxor._error` module to `senxor.error`.
3. Refactor and rename the `senxor._interface` module to `senxor.interface`
4. Introduce the `senxor.interface.registry` for interface registrations.
5. Refactor and rename the `senxor.interface.SenxorInterfaceProtocol` to `senxor.interface.ISenxorInterface`
6. Refactor and rename the `senxor.interface.serial_` to `senxor.interface.serial_port`
7. Refactor the `senxor.utils.list_senxor`, rename `type` parameter to `interface` and remove the `exclude` parameter, now the `list_senxor` function returns a list of `senxor.interface.protocol.IDevice` instances.
8. Refactor the `senxor.utils.connect`, rename `address` parameter to `device`, remove the `type` parameter, now the `connect` function will determine the interface type based on the device parameter. Remove the `stop_stream` parameter.
9. Remove the `connect_senxor` function, which is same as the `connect`.
10. Rename the `senxor._senxor` module to `senxor.core`.
11. Refactor the `senxor.regmap` module, see the API Reference for more details.
12. Force set TEMP_UNITS and NO_HEADER to 0 on device open, and prevent users from modifying them to avoid compatibility issues with older devices
13. Remove get_temp_units method as it is no longer used in pysenxor
14. Remove extra parameters from Senxor.read(), now it consistently returns 2D frame where data type and meaning depend on ADC_ENABLE field
15. Remove redundant processing functions from senxor.proc
16. Enhance the `Senxor` class, add `get_shape`, `disable_all_filters`, `get_filters_status`, `get_fw_version`, `get_module_type`, `get_mcu_type`, `get_module_gain`, `get_senxor_type`, etc. methods
17. Introduce the `Senxor.on(event, listener)` method for data and event listeners.
18. Refactor colormap handling and add lazy loading for improved performance

## v3.0.0 (2025-08-01)

### Feat

- Introduce settings management utility
- Enhance logging system
- Update senxor.cam
- Enhance the mechanism of `fields.get_field()`
- feat: Add backward compatibility methods to utils.py
- Add backward compatibility methods to Senxor class
- Add thread listener example for Senxor device
- Enhance Field, Fields, Registers classes.
- Update SENXOR_TYPE and add MODULE_TYPE and MCU_TYPE constants in consts.py
- Remove deprecated registers
- Load custom colormaps from JSON resource file in proc.py
- Add default colormaps dictionary in proc.py
- Add a logger utility function.
- Update the return value of Senxor.is_connected
- Add LiteCamThread for non-blocking camera frame reading with listener support
- Add examples for SenxorThread usage with threading and Tkinter
- Implement threaded background reading with listener support in SenxorThread
- Add `get_shape` method to `Senxor`
- Enhance dual_light_tkinter  demo
- Update the error handler
- Enhance dual_light_tkinter with improved device management and UI layout
- Integrate Nuitka for packaging dual_light_tkinter
- Add a light weight camera capture module
- Initial commit, include the following features:
  - Senxor devices discovery and listing
  - Senxor device connection and management
  - Senxor device configuration and register read/write
  - Thermal data processing utilities
  - usb-serial interface
  - logging system

### Fix

- Fix the issue in `_fetch_regs_values_by_fields`
- Fix some type hint issues
- fix logger error in `senxor.log`
- Fix some issues of  regmap
- Update address property in SenxorInterfaceSerial to handle ListPortInfo type
- Ensure stream stops only when connected
- Fix the error in cmaps.json
- Raise RuntimeError in read method if thread is not started for SenxorThread and LiteCamThread
- fix the AttributeError in SenxorThread.__del__ if failed to start thread
- Correct response handling in DualLightApp
- Remove unstable LiteWindow class from cam.py.
- Improve error handling when closing the Senxor interface
- fix the issue when closing the serial interface
- modify the logic of read_all_regs

### Refactor

- Update Senxor class to replace the bit-operation of regs with fields
- Simplify connection functions and improve documentation
- Introduce Fields classes for improved register management
- Replace REGS usage with new regmap structure
- Remove dual_light_tkinter.py and dual_stream_tkinter.py.
- Update Register class to compatible with py3.9
- Improve the  _BackgroundReader to manage listener backlog with queue.
- Enhance dual_light_cv.py
- Remove unusable LiteCamThread, Add a CvCamThread.
- Update SenxorThread/CamThread initialization to accept Senxor/Cam instance directly.
- Remove duplicate log messages
- Refactor the internal implementation of usb interface
- modify the return type of  Senxor.read()
- Update Senxor interface protocol and error handling
