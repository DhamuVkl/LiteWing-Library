# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2025-02-17

### Added
- Initial release of the LiteWing Python library.
- `LiteWing` main class with connection, flight, sensor, and LED control.
- Cascaded PID position hold controller using optical flow.
- Manual (keyboard/joystick) control with two hold modes: `"current"` and `"origin"`.
- `PIDConfig` class for tuning position and velocity PID gains.
- `SensorData` snapshot class for reading height, velocity, position, and battery.
- `LEDController` for NeoPixel LED color, blinking, and clearing.
- `FlightLogger` for CSV flight data recording.
- Firmware Z-axis parameter tuning (`thrust_base`, `z_position_kp`, `z_velocity_kp`).
- Waypoint navigation (`fly_to`, `fly_path`).
- Context manager support for safe emergency stops.
- Three tiered example scripts (beginner, intermediate, advanced).
- Full API reference documentation.
