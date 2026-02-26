# LiteWing API Reference

Complete reference for every function, class, and property in the `litewing` library.

> **47+ public functions and properties** across 9 modules.

---

## `LiteWing` — Main Class

The single entry point for all drone operations.

```python
from litewing import LiteWing
drone = LiteWing("192.168.43.42")
```

### Constructor

| Method | Description |
|---|---|
| `LiteWing(ip="192.168.43.42")` | Create a drone controller. `ip` is the drone's IP address. |

### Context Manager

```python
with LiteWing("192.168.43.42") as drone:
    ...  # auto emergency_stop on exit
```

### Connection

| Method | Description |
|---|---|
| `connect()` | Connect to the drone and start reading sensor data. No motors are started. |
| `disconnect()` | Disconnect from the drone and stop sensor logging. Safe to call even if not connected. |

### Status Properties

| Property | Type | Description |
|---|---|---|
| `is_connected` | `bool` | `True` if currently connected to the drone. |
| `is_flying` | `bool` | `True` if the drone is currently in flight. |
| `flight_phase` | `str` | Current phase: `IDLE`, `CONNECTING`, `TAKEOFF`, `STABILIZING`, `HOVERING`, `LANDING`, `COMPLETE`, `ERROR`, etc. |

### Sensor Access

| Method / Property | Returns | Description |
|---|---|---|
| `read_sensors()` | `SensorData` | Snapshot of all current sensor readings (height, velocity, position, battery). |
| `battery` | `float` | Current battery voltage in volts. |
| `height` | `float` | Current estimated height in meters. |
| `position` | `(float, float)` | Current estimated `(x, y)` position in meters. |
| `velocity` | `(float, float)` | Current estimated `(vx, vy)` velocity in m/s. |

### Flight Commands

| Method | Description |
|---|---|
| `arm()` | Arm the drone — prepare for flight. Must be called before takeoff. |
| `takeoff(height=None, speed=None)` | Take off to specified height (meters). Blocking. |
| `hover(seconds)` | Hover in place for `seconds` duration while maintaining position hold. |
| `land()` | Land the drone safely. Descends and stops motors. |
| `emergency_stop()` | **Immediately** cuts all motors. Drone will fall! Use only in emergencies. |

### Movement Commands

| Method | Description |
|---|---|
| `pitch_forward(distance=None, speed=0.2)` | Pitch forward by `distance` meters at `speed` m/s. |
| `pitch_backward(distance=None, speed=0.2)` | Pitch backward by `distance` meters. |
| `roll_left(distance=None, speed=0.2)` | Roll left by `distance` meters. |
| `roll_right(distance=None, speed=0.2)` | Roll right by `distance` meters. |

### Raw Control (No Sensors Required)

| Method | Description |
|---|---|
| `send_control(roll=0.0, pitch=0.0, yawrate=0.0, thrust=0)` | Send raw motor commands directly. Bypasses height/position hold. `roll`/`pitch` in degrees (±30), `yawrate` in deg/s (±200), `thrust` 0–65535. |

> **Warning:** Too much thrust will flip the drone! Start low (~15000) and increase slowly.

### Position Hold Control

| Method | Description |
|---|---|
| `enable_position_hold()` | Activate optical flow-based position hold. |
| `disable_position_hold()` | Disable position hold, switch to raw velocity mode. |
| `reset_position()` | Reset estimated position to `(0, 0)`. Useful when drift accumulates. |

### Advanced Flight

| Method | Description |
|---|---|
| `fly(maneuver_fn=None, hover_duration=None)` | Execute a complete flight: connect → takeoff → hover/maneuver → land. If `maneuver_fn` is provided, it runs during the hover phase. |
| `fly_to(x, y, speed=0.3, threshold=None)` | Fly to absolute position `(x, y)` using position hold. Blocking. |
| `fly_path(waypoints, speed=0.3, threshold=None)` | Fly through a list of `(x, y)` waypoint tuples. |

### Manual / Keyboard Control

| Method | Description |
|---|---|
| `start_manual_control()` | Full automated flight with WASD control: connect → takeoff → keyboard loop → land. |
| `stop_manual_control()` | Exit manual mode: lands and disconnects. |
| `set_key(key, pressed)` | Set state of a manual key (`"w"`, `"a"`, `"s"`, `"d"`). `pressed` = `True`/`False`. |
| `on_key_press(callback)` | Register a callback for key press events. |
| `on_key_release(callback)` | Register a callback for key release events. |

### Firmware Parameters

| Method | Description |
|---|---|
| `apply_firmware_params()` | Send current `thrust_base`, `z_position_kp`, `z_velocity_kp` to the drone's onboard controller. Must be connected. |

### LED Control

| Method | Description |
|---|---|
| `set_led_color(r, g, b)` | Set all LEDs to solid RGB color (0–255 each). |
| `set_led(index, r, g, b)` | Set a single LED to RGB color. `index` = 0–3. |
| `blink_leds(on_ms=500, off_ms=500)` | Start blinking LEDs with specified timing. |
| `clear_leds()` | Turn off all LEDs. |

### Data Logging

| Method | Description |
|---|---|
| `start_logging(filename=None)` | Start recording flight data to CSV. Auto-generates timestamped filename if `None`. |
| `stop_logging()` | Stop recording and close the CSV file. |

### Utility

| Method | Description |
|---|---|
| `set_logger(fn)` | Set a custom output function for log messages (default: `print`). |

---

## Configurable Properties

All properties can be set directly on the `LiteWing` instance.

### Flight Parameters

| Property | Default | Description |
|---|---|---|
| `target_height` | `0.3` | Hover height in meters. |
| `takeoff_time` | `1.0` | Takeoff ramp duration (seconds). |
| `landing_time` | `2.0` | Landing descent timeout (seconds). |
| `descent_rate` | `0.3` | Landing descent speed in m/s. |
| `hover_duration` | `20.0` | Default hover time (seconds). |
| `enable_takeoff_ramp` | `False` | Smooth altitude ramp during takeoff. |
| `debug_mode` | `False` | If `True`, disables motors (sensors still work). |
| `enable_csv_logging` | `False` | Auto-create CSV log files during flight. |
| `enable_sensor_check` | `True` | Check ToF/flow sensors on `arm()`. Set `False` to skip. |

### Trim Corrections

| Property | Default | Description |
|---|---|---|
| `hover_trim_pitch` | `0.0` | Forward/backward drift correction (hover mode). Positive = nudge forward. |
| `hover_trim_roll` | `0.0` | Left/right drift correction (hover mode). Positive = nudge right. |
| `raw_trim_roll` | `0.0` | Roll trim for raw control mode (degrees). |
| `raw_trim_pitch` | `0.0` | Pitch trim for raw control mode (degrees). |

### Raw Control Safety

| Property | Default | Description |
|---|---|---|
| `max_thrust` | `35000` | Safety cap for `send_control()` thrust (0–65535). |

### PID Controllers

| Property | Default | Description |
|---|---|---|
| `position_pid.kp` | `1.0` | Proportional — correction strength. |
| `position_pid.ki` | `0.03` | Integral — fix persistent drift. |
| `position_pid.kd` | `0.0` | Derivative — dampen oscillation. |
| `velocity_pid.kp` | `0.7` | Velocity damping — proportional. |
| `velocity_pid.ki` | `0.01` | Velocity damping — integral. |
| `velocity_pid.kd` | `0.0` | Velocity damping — derivative. |

### Position Hold

| Property | Default | Description |
|---|---|---|
| `max_correction` | `0.7` | Maximum PID correction output. |
| `velocity_threshold` | `0.005` | Below this velocity = "stationary" (m/s). |
| `drift_compensation_rate` | `0.004` | Gentle pull toward zero when hovering. |
| `position_reset_interval` | `90.0` | Dead reckoning reset interval (seconds). |
| `max_position_error` | `2.0` | Clamp position error to prevent runaway (meters). |
| `optical_flow_scale` | `4.4` | Optical flow sensor calibration factor. |
| `use_height_scaling` | `True` | Whether velocity depends on altitude. |
| `velocity_smoothing` | `0.85` | Smoothing filter (0 = raw, 1 = max smooth). |

### Manual Control

| Property | Default | Description |
|---|---|---|
| `sensitivity` | `0.2` | How fast drone moves per key (m/s per key). |
| `hold_mode` | `"current"` | `"current"` = hold where you stop, `"origin"` = snap back to launch. |
| `momentum_compensation_time` | `0.10` | Predicted stopping distance (seconds). |
| `settling_duration` | `0.1` | Duration of gentle corrections after key release. |
| `settling_correction_factor` | `0.5` | Correction strength during settling (0.3–0.7). |

### Firmware (Z-Axis)

| Property | Default | Description |
|---|---|---|
| `enable_firmware_params` | `False` | Send custom Z-axis params on connect. |
| `thrust_base` | `24000` | Base motor thrust. Increase if drone feels heavy. |
| `z_position_kp` | `1.6` | Height position gain (firmware-side PID). |
| `z_velocity_kp` | `15.0` | Vertical velocity damping. |

### Control Loop Timing

| Property | Default | Description |
|---|---|---|
| `sensor_update_rate` | `10` | Sensor polling period (ms). |
| `control_update_rate` | `0.02` | Control loop interval (seconds, 50 Hz). |

### Waypoint Navigation

| Property | Default | Description |
|---|---|---|
| `maneuver_distance` | `0.5` | Default movement distance (meters). |
| `waypoint_timeout` | `60.0` | Abort waypoint after this many seconds. |
| `waypoint_threshold` | `0.10` | "Close enough" distance (meters). |
| `waypoint_stabilization_time` | `0.5` | Pause at each waypoint (seconds). |

---

## `SensorData` — Sensor Snapshot (`sensors.py`)

Returned by `drone.read_sensors()`. Read-only snapshot of all sensor values.

| Attribute | Type | Description |
|---|---|---|
| `height` | `float` | Kalman-filtered height estimate from VL53L1x ToF laser (meters). |
| `range_height` | `float` | Raw height from VL53L1x ToF laser (meters). |
| `vx` | `float` | Velocity in X axis (m/s). |
| `vy` | `float` | Velocity in Y axis (m/s). |
| `x` | `float` | Estimated X position (meters). |
| `y` | `float` | Estimated Y position (meters). |
| `battery` | `float` | Battery voltage (volts). |
| `delta_x` | `int` | Raw optical flow delta X. |
| `delta_y` | `int` | Raw optical flow delta Y. |
| `roll` | `float` | Roll angle (degrees). |
| `pitch` | `float` | Pitch angle (degrees). |
| `yaw` | `float` | Yaw angle (degrees). |
| `acc_x` | `float` | Accelerometer X (g). |
| `acc_y` | `float` | Accelerometer Y (g). |
| `acc_z` | `float` | Accelerometer Z (g). |
| `gyro_x` | `float` | Gyroscope X (deg/s). |
| `gyro_y` | `float` | Gyroscope Y (deg/s). |
| `gyro_z` | `float` | Gyroscope Z (deg/s). |

---

## `PIDConfig` — PID Gain Configuration (`pid.py`)

Holds PID gain values. Access via `drone.position_pid` and `drone.velocity_pid`.

| Attribute | Type | Description |
|---|---|---|
| `kp` | `float` | Proportional gain — correction strength. |
| `ki` | `float` | Integral gain — fix persistent errors. |
| `kd` | `float` | Derivative gain — dampen oscillation. |

---

## `PositionHoldController` (`position_hold.py`)

Cascaded PID controller for holding drone at a target position.

| Method | Description |
|---|---|
| `reset()` | Reset PID state (called at start of flight). |
| `set_target(x, y)` | Set target position for position hold. |
| `calculate_corrections(x, y, vx, vy, height, sensor_ready, dt, max_correction)` | Compute velocity corrections. Returns `(correction_vx, correction_vy)`. |

| Attribute | Description |
|---|---|
| `enabled` | `bool` — set `False` to disable corrections. |
| `target_x`, `target_y` | Current target position. |
| `correction_vx`, `correction_vy` | Last computed corrections. |

---

## `LEDController` (`leds.py`)

Controls NeoPixel LEDs on the drone.

| Method | Description |
|---|---|
| `set_color(r, g, b)` | Set all LEDs to RGB color. |
| `set_pixel(index, r, g, b)` | Set a single LED by index (0–3) to RGB color. |
| `blink(on_ms, off_ms)` | Start blinking with timing. |
| `stop_blink()` | Stop blink, restore last color. |
| `clear()` | Turn off all LEDs. |
| `attach(cf)` | Connect to a Crazyflie instance. |
| `detach()` | Disconnect from Crazyflie. |

---

## `FlightLogger` (`logger.py`)

Records flight data to CSV files.

| Method / Property | Description |
|---|---|
| `start(filename=None)` | Start recording. Auto-generates timestamped name if `None`. |
| `stop()` | Stop recording and close the file. |
| `log_row(pos_x, pos_y, height, range_height, vx, vy, correction_vx, correction_vy)` | Write one row of data. Called by the flight engine each loop iteration. |
| `is_logging` | `bool` — `True` if recording. |
| `filepath` | Path to the current log file (or `None`). |

### CSV Columns

| Column | Unit | Description |
|---|---|---|
| `Timestamp (s)` | seconds | Time since logging started. |
| `Position X (m)` | meters | Estimated X position. |
| `Position Y (m)` | meters | Estimated Y position. |
| `Height (m)` | meters | Kalman-filtered height from ToF laser. |
| `Range (m)` | meters | Raw ToF laser height. |
| `Velocity X (m/s)` | m/s | X velocity from optical flow. |
| `Velocity Y (m/s)` | m/s | Y velocity from optical flow. |
| `Correction VX` | — | PID correction applied to X. |
| `Correction VY` | — | PID correction applied to Y. |

---

## `gui` — Live Sensor Visualization (`gui.py`)

Built-in matplotlib dashboards for real-time sensor plotting.

```python
from litewing.gui import live_dashboard
live_dashboard(drone)
```

| Function | Description |
|---|---|
| `live_dashboard(drone, max_points=200, update_ms=100)` | Full 4-panel dashboard: height, attitude, velocity, battery. |
| `live_height_plot(drone, max_points=200, update_ms=100)` | Single plot: Kalman-filtered + raw ToF height. |
| `live_imu_plot(drone, max_points=200, update_ms=100)` | Single plot: roll, pitch, yaw attitude angles. |
| `live_position_plot(drone, max_points=500, update_ms=100)` | 2D XY position trail from optical flow dead reckoning. |

All functions auto-connect the drone if not already connected. Requires `matplotlib`.

---

## Internal Modules

These are used internally by the library. Learners don't need to touch them.

### `_flight_engine` (`_flight_engine.py`)

| Function | Description |
|---|---|
| `run_flight_sequence(drone, maneuver_fn)` | Full flight lifecycle: connect → takeoff → hover/maneuver → land. |
| `run_waypoint_maneuver(drone, cf, has_pos_hold, waypoints, ...)` | Navigate through a list of `(x, y)` waypoints with position hold. |

### `manual_control` (`manual_control.py`)

| Function | Description |
|---|---|
| `run_manual_control(drone)` | Full manual control flight: connect → takeoff → keyboard loop → land. |

### `_connection` (`_connection.py`)

| Function | Description |
|---|---|
| `setup_sensor_logging(cf, motion_cb, battery_cb, imu_cb, period_ms)` | Set up cflib LogConfig for motion, battery, and IMU. Returns `(log_motion, log_battery, log_imu)`. |
| `apply_firmware_parameters(cf, thrust_base, z_pos_kp, z_vel_kp)` | Send custom Z-axis PID values to drone firmware. |
| `stop_logging_configs(log_motion, log_battery, log_imu)` | Safely stop all log configurations. |

### `_position` (`_position.py`)

| Method | Description |
|---|---|
| `PositionEngine.reset()` | Reset position to `(0, 0)`. |
| `PositionEngine.calculate_velocity(delta, altitude)` | Convert optical flow delta to velocity (m/s). |
| `PositionEngine.update_from_sensor(dx, dy, altitude)` | Process new sensor data → velocity → position. |
| `PositionEngine.periodic_reset_check()` | Reset if interval has elapsed. Returns `True` on reset. |

### `_safety` (`_safety.py`)

| Function | Description |
|---|---|
| `check_link_safety(cf, data_ready, last_heartbeat, debug_mode)` | Check connection + sensor freshness. Returns `True` if safe. |
| `check_battery_safe(voltage, threshold)` | Check battery above threshold. Returns `True` if safe. |

### `_crtp` (`_crtp.py`)

| Function | Description |
|---|---|
| `send_crtp_with_fallback(cf, port, channel, payload)` | Send CRTP packet with multiple method fallbacks. |
| `try_send_with_retries(cf, fn, *args, retries)` | Call a function with retries and delay. Returns `True` on success. |
