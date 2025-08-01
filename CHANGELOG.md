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
