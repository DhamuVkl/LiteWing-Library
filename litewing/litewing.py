"""
LiteWing — Beginner-Friendly Drone Library
=============================================
Control your LiteWing drone with simple, educational Python code.

Quick Start:
    from litewing import LiteWing

    with LiteWing("192.168.43.42") as drone:
        drone.arm()
        drone.takeoff()
        drone.pitch_forward(0.5, speed=0.2)
        drone.land()

The LiteWing class is your "remote control." It handles all the low-level
communication, but keeps drone engineering concepts visible so you can learn
about sensors, PID tuning, position hold, and flight control.
"""

import time
import atexit
import signal
import threading

from .config import defaults
from .pid import PIDConfig
from .sensors import SensorData, _SensorState
from .leds import LEDController
from .logger import FlightLogger
from ._position import PositionEngine
from .position_hold import PositionHoldController
from . import _flight_engine
from . import manual_control as _manual_control


class LiteWing:
    """
    Main drone controller — your "remote control."

    Use this class to connect, fly, read sensors, and tune the drone.
    Supports context manager (with statement) for safe auto-disconnects.

    Args:
        ip: The IP address of the drone (default: "192.168.43.42").
    """

    def __init__(self, ip=None):
        # === Connection ===
        self._ip = ip or defaults.DRONE_IP
        self._port = defaults.DRONE_PORT
        self._scf = None
        self._flight_active = False
        self._flight_phase = "IDLE"
        self._flight_thread = None
        self._manual_active = False
        self._manual_thread = None
        self._logger_fn = print  # Default output function

        # === Exposed Configuration (Tier 1–3) ===

        # Flight parameters
        self.target_height = defaults.TARGET_HEIGHT
        self.takeoff_time = defaults.TAKEOFF_TIME
        self.landing_time = defaults.LANDING_TIME
        self.descent_rate = defaults.DESCENT_RATE
        self.hover_duration = defaults.HOVER_DURATION
        self.enable_takeoff_ramp = defaults.ENABLE_TAKEOFF_RAMP

        # Trim corrections
        self.hover_trim_pitch = defaults.TRIM_VX
        self.hover_trim_roll = defaults.TRIM_VY
        self.raw_trim_roll = 0.0    # Raw-mode roll trim (degrees)
        self.raw_trim_pitch = 0.0   # Raw-mode pitch trim (degrees)

        # Debug & safety
        self.debug_mode = defaults.DEBUG_MODE
        self.enable_height_sensor_safety = defaults.ENABLE_HEIGHT_SENSOR_SAFETY
        self.enable_csv_logging = defaults.ENABLE_CSV_LOGGING
        self.enable_sensor_check = True  # Check ToF / flow sensors on connect
        self.max_thrust = 35000  # Safety cap for raw thrust (0-65535)
        self._height_sensor_min_change = defaults.HEIGHT_SENSOR_MIN_CHANGE

        # PID controllers (VISIBLE — learners tune these!)
        self.position_pid = PIDConfig(
            kp=defaults.POSITION_KP,
            ki=defaults.POSITION_KI,
            kd=defaults.POSITION_KD,
        )
        self.velocity_pid = PIDConfig(
            kp=defaults.VELOCITY_KP,
            ki=defaults.VELOCITY_KI,
            kd=defaults.VELOCITY_KD,
        )

        # Position hold settings
        self.max_correction = defaults.MAX_CORRECTION
        self.velocity_threshold = defaults.VELOCITY_THRESHOLD
        self.drift_compensation_rate = defaults.DRIFT_COMPENSATION_RATE
        self.position_reset_interval = defaults.PERIODIC_RESET_INTERVAL
        self.max_position_error = defaults.MAX_POSITION_ERROR
        self.optical_flow_scale = defaults.OPTICAL_FLOW_SCALE
        self.use_height_scaling = defaults.USE_HEIGHT_SCALING
        self.velocity_smoothing = defaults.VELOCITY_SMOOTHING_ALPHA

        # Joystick / manual control
        self.sensitivity = defaults.JOYSTICK_SENSITIVITY
        self.hold_mode = defaults.JOYSTICK_HOLD_MODE
        self.momentum_compensation_time = defaults.MOMENTUM_COMPENSATION_TIME
        self.settling_duration = defaults.SETTLING_DURATION
        self.settling_correction_factor = defaults.SETTLING_CORRECTION_FACTOR
        self._manual_keys = {"w": False, "s": False, "a": False, "d": False}

        # Firmware parameters
        self.enable_firmware_params = defaults.ENABLE_FIRMWARE_PARAMS
        self.thrust_base = defaults.FW_THRUST_BASE
        self.z_position_kp = defaults.FW_Z_POS_KP
        self.z_velocity_kp = defaults.FW_Z_VEL_KP

        # Control loop timing
        self.sensor_update_rate = defaults.SENSOR_PERIOD_MS
        self.control_update_rate = defaults.CONTROL_UPDATE_RATE

        # Waypoint parameters
        self.waypoint_timeout = defaults.WAYPOINT_TIMEOUT
        self.waypoint_threshold = defaults.MANEUVER_THRESHOLD
        self.waypoint_stabilization_time = defaults.WAYPOINT_STABILIZATION_TIME
        self.maneuver_distance = defaults.MANEUVER_DISTANCE

        # === Internal state (hidden from learners) ===
        self._sensors = _SensorState()
        self._position_engine = PositionEngine()
        self._position_hold = PositionHoldController(
            self.position_pid, self.velocity_pid
        )
        self._leds = LEDController()
        self._flight_logger = FlightLogger()
        self._hover_duration = defaults.HOVER_DURATION

        # Callbacks for events
        self._on_key_press_cb = None
        self._on_key_release_cb = None

        # === System-wide Ctrl+C emergency stop ===
        # This ensures pressing Ctrl+C ALWAYS kills motors immediately,
        # even if the student forgot to add error handling.
        def _ctrl_c_handler(sig, frame):
            print("\n Ctrl+C detected — EMERGENCY STOP!")
            self.emergency_stop()
            raise SystemExit(1)

        signal.signal(signal.SIGINT, _ctrl_c_handler)

    # === Context Manager (with statement) ===

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    # === Connection ===

    def connect(self):
        """
        Connect to the drone and start reading sensor data.

        After calling this, you can read battery, height, position, etc.
        No motors are started — the drone stays on the ground.

        Usage:
            drone.connect()
            print(drone.battery)
            drone.disconnect()

        Or use the context manager:
            with LiteWing("192.168.43.42") as drone:
                drone.connect()
                print(drone.battery)
        """
        if self._scf is not None:
            if self._logger_fn:
                self._logger_fn("Already connected!")
            return

        import cflib.crtp
        from cflib.crazyflie import Crazyflie
        from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
        from ._connection import setup_sensor_logging

        cflib.crtp.init_drivers()
        uri = f"udp://{self._ip}:{self._port}"

        self._flight_phase = "CONNECTING"
        if self._logger_fn:
            self._logger_fn(f"Connecting to {uri}...")

        # Auto-retry with port recovery (up to 3 attempts)
        last_error = None
        for attempt in range(3):
            cf = Crazyflie(rw_cache="./cache")
            self._cf_instance = cf
            self._sync_cf = SyncCrazyflie(uri, cf=cf)

            try:
                self._sync_cf.open_link()
                last_error = None
                break  # Success!
            except Exception as e:
                last_error = e
                self._cf_instance = None
                self._sync_cf = None

                # Check if it's a port conflict (WinError 10048)
                if "10048" in str(e) or "Address already in use" in str(e):
                    if self._logger_fn:
                        self._logger_fn(
                            f"Port 2399 busy (previous session). "
                            f"Recovering... (attempt {attempt + 1}/3)"
                        )
                    self._free_port_2399()
                    time.sleep(2)
                else:
                    # Not a port conflict — fail immediately
                    self._flight_phase = "IDLE"
                    raise ConnectionError(
                        f"Failed to connect to {uri}: {e}"
                    ) from e

        if last_error is not None:
            self._flight_phase = "IDLE"
            raise ConnectionError(
                f"Failed to connect to {uri} after 3 attempts. "
                f"Try closing all other Python scripts and wait a few seconds.\n"
                f"Error: {last_error}"
            )

        self._scf = self._sync_cf

        # Register cleanup so port is ALWAYS freed, even on crash
        atexit.register(self._atexit_cleanup)

        # Attach LEDs
        self._leds.attach(cf)

        # Start sensor logging
        self._log_motion, self._log_battery, self._log_imu = setup_sensor_logging(
            cf,
            motion_callback=self._motion_callback,
            battery_callback=self._battery_callback,
            imu_callback=self._imu_callback,
            sensor_period_ms=self.sensor_update_rate,
            logger=self._logger_fn,
        )

        # Apply firmware parameters if enabled
        if self.enable_firmware_params:
            from ._connection import apply_firmware_parameters
            apply_firmware_parameters(
                cf, self.thrust_base, self.z_position_kp, self.z_velocity_kp,
                logger=self._logger_fn,
            )

        # Reset position tracking
        self._position_engine.reset()
        self._position_hold.reset()

        # === Sensor health check ===
        # Read firmware params to verify external sensors initialized OK
        self._sensor_health = self._check_sensor_health(cf)

        self._flight_phase = "CONNECTED"
        if self._logger_fn:
            self._logger_fn("Connected! Sensor data streaming.")

    def disconnect(self):
        """
        Disconnect from the drone and stop sensor logging.

        Safe to call even if not connected.
        """
        from ._connection import stop_logging_configs

        # Stop motors if flying
        if self._flight_active:
            self._flight_active = False
            if self._scf and not self.debug_mode:
                try:
                    self._scf.cf.commander.send_setpoint(0, 0, 0, 0)
                except Exception:
                    pass

        # Stop logging (suppress errors during teardown)
        try:
            log_m = getattr(self, '_log_motion', None)
            log_b = getattr(self, '_log_battery', None)
            log_i = getattr(self, '_log_imu', None)
            stop_logging_configs(log_m, log_b, log_i)
        except Exception:
            pass
        try:
            self._flight_logger.stop(logger=self._logger_fn)
        except Exception:
            pass

        # Detach LEDs
        try:
            self._leds.clear()
            self._leds.detach()
        except Exception:
            pass

        # Close link
        if self._scf is not None:
            try:
                sync = getattr(self, '_sync_cf', None)
                if sync:
                    sync.close_link()
            except Exception:
                pass
            self._scf = None
            self._sync_cf = None
            self._cf_instance = None

        self._flight_phase = "IDLE"
        if self._logger_fn:
            self._logger_fn("Disconnected.")

    def _atexit_cleanup(self):
        """Called automatically when Python exits — ensures port is freed."""
        try:
            if self._scf is not None:
                self.disconnect()
        except Exception:
            pass

    @staticmethod
    def _free_port_2399():
        """
        Kill any zombie Python process holding UDP port 2399.
        This happens when a previous script crashed without disconnecting.
        """
        import subprocess
        import os

        try:
            # Find process using port 2399
            result = subprocess.run(
                ["netstat", "-ano", "-p", "UDP"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if ":2399 " in line:
                    parts = line.split()
                    pid = int(parts[-1])
                    # Don't kill ourselves!
                    if pid != os.getpid() and pid != 0:
                        try:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(pid)],
                                capture_output=True, timeout=5
                            )
                        except Exception:
                            pass
        except Exception:
            pass

    def _check_sensor_health(self, cf):
        """
        Check if external sensors (ToF, optical flow) initialized OK.

        Reads firmware params that the drone sets during boot:
            deck.bcZRanger2  → 1 if VL53L1x ToF sensor initialized
            deck.bcFlow2     → 1 if PMW3901 optical flow initialized

        Returns:
            dict: {"tof": bool, "flow": bool} — True if sensor is OK.
        """
        health = {"tof": False, "flow": False}

        try:
            tof_ok = int(cf.param.get_value("deck.bcZRanger2"))
            flow_ok = int(cf.param.get_value("deck.bcFlow2"))

            health["tof"] = bool(tof_ok)
            health["flow"] = bool(flow_ok)

            if self._logger_fn:
                # ToF status
                if health["tof"]:
                    self._logger_fn("  [OK] ToF sensor (VL53L1x) detected")
                else:
                    self._logger_fn(
                        "  [FAIL] ToF sensor (VL53L1x) NOT detected!\n"
                        "         -> Check I2C wiring to the ToF module"
                    )

                # Optical flow status
                if health["flow"]:
                    self._logger_fn("  [OK] Optical flow (PMW3901) detected")
                else:
                    self._logger_fn(
                        "  [FAIL] Optical flow (PMW3901) NOT detected!\n"
                        "         -> Check SPI wiring to the flow sensor"
                    )
        except Exception as e:
            if self._logger_fn:
                self._logger_fn(
                    f"  [WARN] Could not read sensor status: {e}"
                )

        return health

    @property
    def is_connected(self):
        """True if the drone is currently connected."""
        return self._scf is not None

    @property
    def is_flying(self):
        """True if the drone is currently in flight."""
        return self._flight_active

    @property
    def flight_phase(self):
        """Current phase: IDLE, CONNECTING, TAKEOFF, HOVERING, LANDING, etc."""
        return self._flight_phase

    # === Sensor Access ===

    def read_sensors(self):
        """
        Get a snapshot of all current sensor readings.

        Returns:
            SensorData: Object with height, vx, vy, x, y, battery, etc.
        """
        return self._sensors.snapshot(self._position_engine)

    @property
    def battery(self):
        """Current battery voltage in volts."""
        return self._sensors.battery_voltage

    @property
    def height(self):
        """Current estimated height in meters."""
        return self._sensors.height

    @property
    def position(self):
        """Current estimated (x, y) position in meters."""
        return (self._position_engine.x, self._position_engine.y)

    @property
    def velocity(self):
        """Current estimated (vx, vy) velocity in m/s."""
        return (self._position_engine.vx, self._position_engine.vy)

    # === Flight Commands (Tier 1) ===

    def arm(self):
        """
        Arm the drone — prepare it for flight.

        This must be called before takeoff. Arming initializes the
        flight commander so motors can spin.
        """
        if self._scf is None:
            raise RuntimeError("Not connected! Call connect() first.")

        # Block flight if sensors are missing (safety for students)
        if self.enable_sensor_check:
            health = getattr(self, '_sensor_health', {})
            missing = []
            if not health.get('tof', False):
                missing.append('ToF sensor (VL53L1x)')
            if not health.get('flow', False):
                missing.append('Optical flow (PMW3901)')
            if missing:
                msg = (
                    "Cannot arm — sensors not detected:\n"
                    + "\n".join(f"  - {s}" for s in missing)
                    + "\n\nCheck wiring and power cycle the drone."
                    + "\nTo skip this check: drone.enable_sensor_check = False"
                )
                raise RuntimeError(msg)

        cf = self._cf_instance
        if not self.debug_mode:
            cf.commander.send_setpoint(0, 0, 0, 0)
            time.sleep(0.1)
            cf.param.set_value("commander.enHighLevel", "1")
            time.sleep(0.5)

        self._flight_active = True
        self._position_engine.reset()
        self._position_hold.reset()

        if self._logger_fn:
            self._logger_fn("Drone armed and ready!")

    def takeoff(self, height=None, speed=None):
        """
        Take off and hover at the specified height.

        This is a BLOCKING call — it won't return until the drone is
        hovering at the target height.

        Args:
            height: Target height in meters (default: drone.target_height).
            speed: Not used yet, reserved for future takeoff speed control.
        """
        if self._scf is None:
            raise RuntimeError("Not connected! Call connect() first.")
        if not self._flight_active:
            raise RuntimeError("Not armed! Call arm() first.")

        if height is not None:
            self.target_height = height

        cf = self._cf_instance
        self._flight_phase = "TAKEOFF"
        if self._logger_fn:
            self._logger_fn(f"Taking off to {self.target_height}m...")

        # Start CSV logging if enabled
        if self.enable_csv_logging and not self._flight_logger.is_logging:
            self._flight_logger.start(logger=self._logger_fn)

        takeoff_start = time.time()
        takeoff_height_start = self._sensors.height

        while (time.time() - takeoff_start < self.takeoff_time and
               self._flight_active):
            if not self.debug_mode:
                # Position hold during takeoff if height is sufficient
                if (self._sensors.sensor_data_ready and
                        self._sensors.height > 0.04):
                    mvx, mvy = self._position_hold.calculate_corrections(
                        self._position_engine.x, self._position_engine.y,
                        self._position_engine.vx, self._position_engine.vy,
                        self._sensors.height, True
                    )
                else:
                    mvx, mvy = 0.0, 0.0

                total_vx = self.hover_trim_pitch + mvy
                total_vy = self.hover_trim_roll + mvx

                # Takeoff ramp
                if self.enable_takeoff_ramp:
                    elapsed = time.time() - takeoff_start
                    progress = min(1.0, elapsed / self.takeoff_time)
                    cmd_height = takeoff_height_start + (
                        self.target_height - takeoff_height_start
                    ) * progress
                else:
                    cmd_height = self.target_height

                cf.commander.send_hover_setpoint(total_vx, total_vy, 0, cmd_height)

            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

        # Post-takeoff safety check
        if self.enable_height_sensor_safety and not self.debug_mode:
            height_change = self._sensors.height - takeoff_height_start
            if height_change < self._height_sensor_min_change:
                cf.commander.send_setpoint(0, 0, 0, 0)
                self._flight_active = False
                raise RuntimeError(
                    f"EMERGENCY: Height sensor failure! "
                    f"Height stuck at {self._sensors.height:.3f}m"
                )

        # Stabilize at hover height
        self._flight_phase = "HOVERING"
        stab_start = time.time()
        while (time.time() - stab_start < 2.0 and self._flight_active):
            if not self.debug_mode:
                if self._sensors.sensor_data_ready:
                    mvx, mvy = self._position_hold.calculate_corrections(
                        self._position_engine.x, self._position_engine.y,
                        self._position_engine.vx, self._position_engine.vy,
                        self._sensors.height, True
                    )
                else:
                    mvx, mvy = 0.0, 0.0
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch + mvy, self.hover_trim_roll + mvx,
                    0, self.target_height
                )
            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

    def land(self):
        """
        Land the drone safely.

        Descends to ground and stops motors.
        """
        if self._scf is None or not self._flight_active:
            self._flight_active = False
            return

        cf = self._cf_instance
        self._flight_phase = "LANDING"
        if self._logger_fn:
            self._logger_fn("Landing...")

        land_start = time.time()
        current_land_height = self.target_height
        dt = 0.02  # 50Hz control loop

        # Gradual descent: lower target height smoothly with position hold
        while (current_land_height > 0.02 and
               time.time() - land_start < self.landing_time and
               self._flight_active):
            current_land_height -= self.descent_rate * dt
            current_land_height = max(current_land_height, 0.0)

            # Keep position hold active during descent
            if self._sensors.sensor_data_ready and current_land_height > 0.03:
                mvx, mvy = self._position_hold.calculate_corrections(
                    self._position_engine.x, self._position_engine.y,
                    self._position_engine.vx, self._position_engine.vy,
                    self._sensors.height, True
                )
            else:
                mvx, mvy = 0.0, 0.0

            total_vx = self.hover_trim_pitch + mvy
            total_vy = self.hover_trim_roll + mvx

            if not self.debug_mode:
                cf.commander.send_hover_setpoint(
                    total_vx, total_vy, 0, current_land_height
                )
            self._log_csv_if_active()
            time.sleep(dt)

        # Brief settle at ground level before killing motors
        settle_start = time.time()
        while time.time() - settle_start < 0.3 and self._flight_active:
            if not self.debug_mode:
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch, self.hover_trim_roll, 0, 0
                )
            time.sleep(0.02)

        # Stop motors
        if not self.debug_mode:
            cf.commander.send_setpoint(0, 0, 0, 0)

        self._flight_active = False
        self._flight_phase = "IDLE"

        # Stop CSV logging
        self._flight_logger.stop(logger=self._logger_fn)

        if self._logger_fn:
            self._logger_fn("Landed!")

    def emergency_stop(self):
        """
        EMERGENCY STOP — immediately cuts all motors.

        Use only in emergencies! The drone will fall from whatever height
        it's at. For normal stops, use land().
        """
        self._flight_active = False
        self._manual_active = False
        if self._scf and not self.debug_mode:
            try:
                self._cf_instance.commander.send_setpoint(0, 0, 0, 0)
            except Exception:
                pass
        self._leds.clear()

    # === Raw Control (no sensors needed) ===

    def send_control(self, roll=0.0, pitch=0.0, yawrate=0.0, thrust=0):
        """
        Send raw flight commands directly to motors.

        No sensors required! This bypasses height/position hold entirely.
        YOU control throttle, tilt, and rotation manually.

        Args:
            roll:    Tilt left/right in degrees (-30 to +30).
            pitch:   Tilt forward/back in degrees (-30 to +30).
            yawrate: Spin rate in degrees/sec (-200 to +200).
            thrust:  Motor power (0 to 65535). ~20000 = hover for light drone.

        Warning:
            Too much thrust will flip the drone! Start low (~15000) and
            increase slowly. Use emergency_stop() or Ctrl+C if needed.
        """
        if self._scf is None:
            raise RuntimeError("Not connected! Call connect() first.")

        # Apply trim corrections
        roll = float(roll) + self.raw_trim_roll
        pitch = float(pitch) + self.raw_trim_pitch

        # Clamp for safety
        thrust = max(0, min(int(thrust), self.max_thrust))
        roll = max(-30, min(30, roll))
        pitch = max(-30, min(30, pitch))
        yawrate = max(-200, min(200, float(yawrate)))

        if not self.debug_mode:
            self._cf_instance.commander.send_setpoint(
                roll, pitch, yawrate, thrust
            )

    def hover(self, seconds):
        """
        Hover in place for the specified duration.

        Actively maintains position hold while waiting.

        Args:
            seconds: How long to hover in seconds.
        """
        if self._scf is None or not self._flight_active:
            # Not in flight — just sleep
            time.sleep(seconds)
            return

        cf = self._cf_instance
        start = time.time()
        while (time.time() - start < seconds and self._flight_active):
            if not self.debug_mode:
                if self._sensors.sensor_data_ready:
                    mvx, mvy = self._position_hold.calculate_corrections(
                        self._position_engine.x, self._position_engine.y,
                        self._position_engine.vx, self._position_engine.vy,
                        self._sensors.height, True
                    )
                else:
                    mvx, mvy = 0.0, 0.0
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch + mvy, self.hover_trim_roll + mvx,
                    0, self.target_height
                )
            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

    def _log_csv_if_active(self):
        """Log a CSV row if flight logging is active."""
        if self._flight_logger.is_logging:
            self._flight_logger.log_row(
                self._position_engine.x, self._position_engine.y,
                self._sensors.height, self._sensors.range_height,
                self._position_engine.vx, self._position_engine.vy,
            )

    # === Movement Commands (Tier 1) ===

    def pitch_forward(self, distance=None, speed=0.2):
        """
        Pitch forward by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Maximum velocity setpoint (m/s).
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(0.0, distance, speed)

    def pitch_backward(self, distance=None, speed=0.2):
        """
        Pitch backward by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Maximum velocity setpoint (m/s).
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(0.0, -distance, speed)

    def roll_left(self, distance=None, speed=0.2):
        """
        Roll left by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Maximum velocity setpoint (m/s).
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(distance, 0.0, speed)

    def roll_right(self, distance=None, speed=0.2):
        """
        Roll right by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Maximum velocity setpoint (m/s).
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(-distance, 0.0, speed)

    def _execute_movement(self, dx, dy, speed):
        """
        Execute a relative movement using position hold.

        This is a BLOCKING call — it sets the position hold target to the
        new position and runs a hover loop until the drone arrives (within
        waypoint_threshold) or times out (waypoint_timeout).

        The `speed` parameter controls the maximum velocity (m/s) by
        overriding max_correction in the PID controller.
        """
        if self._scf is None or not self._flight_active:
            if self._logger_fn:
                self._logger_fn("Cannot move — not in flight!")
            return

        cf = self._cf_instance
        target_x = self._position_engine.x + dx
        target_y = self._position_engine.y + dy

        # Set position hold target to the new position
        self._position_hold.set_target(target_x, target_y)

        if self._logger_fn:
            self._logger_fn(
                f"Moving to ({target_x:.2f}, {target_y:.2f}) "
                f"at {speed:.1f} m/s"
            )

        # Use speed as the velocity clamp (max_correction)
        move_max_correction = min(speed, self.max_correction)

        start = time.time()
        while (time.time() - start < self.waypoint_timeout and
               self._flight_active):

            # Check if we've reached the target
            dist = ((self._position_engine.x - target_x) ** 2 +
                    (self._position_engine.y - target_y) ** 2) ** 0.5
            if dist < self.waypoint_threshold:
                break

            if not self.debug_mode and self._sensors.sensor_data_ready:
                mvx, mvy = self._position_hold.calculate_corrections(
                    self._position_engine.x, self._position_engine.y,
                    self._position_engine.vx, self._position_engine.vy,
                    self._sensors.height, True,
                    max_correction=move_max_correction,
                )
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch + mvy, self.hover_trim_roll + mvx,
                    0, self.target_height
                )

            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

        # Stabilize at target
        stab_start = time.time()
        while (time.time() - stab_start < self.waypoint_stabilization_time and
               self._flight_active):
            if not self.debug_mode and self._sensors.sensor_data_ready:
                mvx, mvy = self._position_hold.calculate_corrections(
                    self._position_engine.x, self._position_engine.y,
                    self._position_engine.vx, self._position_engine.vy,
                    self._sensors.height, True,
                )
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch + mvy, self.hover_trim_roll + mvx,
                    0, self.target_height
                )
            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

    # === Position Hold Control (Tier 3) ===

    def enable_position_hold(self):
        """Activate optical flow-based position hold."""
        self._position_hold.enabled = True
        if self._logger_fn:
            self._logger_fn("Position hold: ENABLED")

    def disable_position_hold(self):
        """Disable position hold — switch to raw velocity mode."""
        self._position_hold.enabled = False
        if self._logger_fn:
            self._logger_fn("Position hold: DISABLED (raw velocity mode)")

    def reset_position(self):
        """
        Reset the estimated position to (0, 0).

        Useful when drift accumulates or you want to establish a new
        "home" position.
        """
        self._position_engine.reset()
        self._position_hold.reset()
        if self._logger_fn:
            self._logger_fn("Position reset to origin (0, 0)")

    # === Advanced Flight (Tier 3) ===

    def fly_to(self, x, y, speed=0.3, threshold=None):
        """
        Fly to an absolute position (x, y) using position hold.

        This is a BLOCKING call — it returns when the drone reaches
        the target (within threshold) or times out.

        Args:
            x: Target X position in meters.
            y: Target Y position in meters.
            speed: Maximum velocity setpoint (m/s).
            threshold: How close is "close enough" (meters).
        """
        if self._scf is None or not self._flight_active:
            if self._logger_fn:
                self._logger_fn("Cannot fly_to — not in flight!")
            return
        if threshold is None:
            threshold = self.waypoint_threshold

        cf = self._cf_instance
        self._position_hold.set_target(x, y)

        if self._logger_fn:
            self._logger_fn(
                f"Flying to ({x:.2f}, {y:.2f}) at {speed:.1f} m/s"
            )

        move_max_correction = min(speed, self.max_correction)

        start = time.time()
        while (time.time() - start < self.waypoint_timeout and
               self._flight_active):
            dist = ((self._position_engine.x - x) ** 2 +
                    (self._position_engine.y - y) ** 2) ** 0.5
            if dist < threshold:
                break

            if not self.debug_mode and self._sensors.sensor_data_ready:
                mvx, mvy = self._position_hold.calculate_corrections(
                    self._position_engine.x, self._position_engine.y,
                    self._position_engine.vx, self._position_engine.vy,
                    self._sensors.height, True,
                    max_correction=move_max_correction,
                )
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch + mvy, self.hover_trim_roll + mvx,
                    0, self.target_height
                )

            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

        # Stabilize at target
        stab_start = time.time()
        while (time.time() - stab_start < self.waypoint_stabilization_time and
               self._flight_active):
            if not self.debug_mode and self._sensors.sensor_data_ready:
                mvx, mvy = self._position_hold.calculate_corrections(
                    self._position_engine.x, self._position_engine.y,
                    self._position_engine.vx, self._position_engine.vy,
                    self._sensors.height, True,
                )
                cf.commander.send_hover_setpoint(
                    self.hover_trim_pitch + mvy, self.hover_trim_roll + mvx,
                    0, self.target_height
                )
            self._log_csv_if_active()
            time.sleep(self.control_update_rate)

    def fly_path(self, waypoints, speed=0.3, threshold=None):
        """
        Fly through a sequence of (x, y) waypoints.

        This is a BLOCKING call — it returns when all waypoints have
        been reached or a timeout occurs.

        Args:
            waypoints: List of (x, y) tuples.
            speed: Maximum velocity setpoint (m/s).
            threshold: How close is "close enough" (meters).
        """
        if threshold is None:
            threshold = self.waypoint_threshold
        for i, (x, y) in enumerate(waypoints):
            if not self._flight_active:
                break
            if self._logger_fn:
                self._logger_fn(f"Waypoint {i + 1}/{len(waypoints)}")
            self.fly_to(x, y, speed=speed, threshold=threshold)

    # === Complete Flight Execution ===

    def fly(self, maneuver_fn=None, hover_duration=None):
        """
        Execute a complete flight: connect → takeoff → hover/maneuver → land.

        This is the main entry point for scripted flights. It handles
        connection, takeoff, your maneuver code, and safe landing.

        Args:
            maneuver_fn: Optional function(drone, cf, has_pos_hold) to execute
                         during the hover phase. If None, hovers for
                         hover_duration seconds.
            hover_duration: How long to hover in seconds (default: drone.hover_duration).
        """
        if hover_duration is not None:
            self._hover_duration = hover_duration
        _flight_engine.run_flight_sequence(self, maneuver_fn)

    # === Manual Control (Tier 2–3) ===

    def start_manual_control(self):
        """
        Start joystick/keyboard control mode.

        Takes off and enters a real-time control loop where the drone
        responds to keyboard inputs (WASD) while maintaining position hold.

        Hold mode determines behavior when keys are released:
            "current" — hold at current position (Flying Mode)
            "origin"  — snap back to launch point (Spring Mode)

        Call stop_manual_control() or press emergency stop to end.
        """
        if self._manual_active:
            if self._logger_fn:
                self._logger_fn("Manual control already active!")
            return

        self._manual_active = True
        self._manual_thread = threading.Thread(
            target=_manual_control.run_manual_control,
            args=(self,),
            daemon=True,
        )
        self._manual_thread.start()

    def stop_manual_control(self):
        """Stop manual control mode and land the drone."""
        self._manual_active = False
        if self._manual_thread:
            self._manual_thread.join(timeout=10)
            self._manual_thread = None

    def set_key(self, key, pressed):
        """
        Set the state of a manual control key.

        Args:
            key: Key name ("w", "a", "s", "d").
            pressed: True if pressed, False if released.
        """
        if key in self._manual_keys:
            self._manual_keys[key] = pressed

    def on_key_press(self, callback):
        """Register a callback for key press events."""
        self._on_key_press_cb = callback

    def on_key_release(self, callback):
        """Register a callback for key release events."""
        self._on_key_release_cb = callback

    # === Firmware Parameters (Tier 3) ===

    def apply_firmware_params(self):
        """
        Send current firmware parameters to the drone's onboard controller.

        Must be called while connected. Parameters include:
            drone.thrust_base    — base motor thrust
            drone.z_position_kp  — height position gain
            drone.z_velocity_kp  — vertical velocity damping
        """
        if self._scf:
            from ._connection import apply_firmware_parameters
            apply_firmware_parameters(
                self._scf.cf,
                self.thrust_base, self.z_position_kp, self.z_velocity_kp,
                logger=self._logger_fn,
            )
        else:
            if self._logger_fn:
                self._logger_fn("Cannot apply firmware params: not connected")

    # === LED Control ===

    def set_led_color(self, r, g, b):
        """
        Set all LEDs to a solid RGB color.

        Args:
            r: Red (0–255).
            g: Green (0–255).
            b: Blue (0–255).
        """
        self._leds.set_color(r, g, b, logger=self._logger_fn)

    def set_led(self, index, r, g, b):
        """
        Set a single LED to a specific RGB color.

        The drone has 4 LEDs numbered 0–3.

        Args:
            index: LED number (0–3).
            r: Red (0–255).
            g: Green (0–255).
            b: Blue (0–255).

        Example:
            drone.set_led(0, 255, 0, 0)  # LED 0 = red
            drone.set_led(1, 0, 255, 0)  # LED 1 = green
        """
        self._leds.set_pixel(index, r, g, b, logger=self._logger_fn)

    def blink_leds(self, on_ms=500, off_ms=500):
        """
        Start blinking the LEDs.

        Args:
            on_ms: Duration LEDs stay ON (milliseconds).
            off_ms: Duration LEDs stay OFF (milliseconds).
        """
        self._leds.blink(on_ms, off_ms, logger=self._logger_fn)

    def clear_leds(self):
        """Turn off all LEDs."""
        self._leds.clear(logger=self._logger_fn)

    # === Data Logging ===

    def start_logging(self, filename=None):
        """
        Start recording flight data to a CSV file.

        Args:
            filename: Optional custom filename.
        """
        self._flight_logger.start(filename, logger=self._logger_fn)

    def stop_logging(self):
        """Stop recording and close the CSV file."""
        self._flight_logger.stop(logger=self._logger_fn)

    # === Internal Callbacks (hidden from learners) ===

    def _motion_callback(self, timestamp, data, logconf):
        """Internal: called when new motion sensor data arrives."""
        self._sensors.last_sensor_heartbeat = time.time()
        self._sensors.sensor_data_ready = True

        # Extract sensor values
        delta_x = data.get("motion.deltaX", 0)
        delta_y = data.get("motion.deltaY", 0)
        z_estimate = data.get("stateEstimate.z", self._sensors.height)
        z_range = data.get("range.zrange", 0)

        # Update height
        self._sensors.height = z_estimate
        self._sensors.range_height = z_range / 1000.0  # mm → meters

        # Use range if available and reasonable, otherwise state estimate
        altitude_for_calc = z_estimate
        if z_range > 0:
            altitude_for_calc = z_range / 1000.0

        # Update position engine
        self._position_engine.update_from_sensor(delta_x, delta_y, altitude_for_calc)

    def _battery_callback(self, timestamp, data, logconf):
        """Internal: called when new battery data arrives."""
        voltage = data.get("pm.vbat", 0.0)
        if voltage > 0:
            self._sensors.battery_voltage = voltage
            self._sensors.battery_data_ready = True

    def _imu_callback(self, timestamp, data, logconf):
        """Internal: called when new IMU data arrives."""
        self._sensors.roll = data.get("stabilizer.roll", 0.0)
        self._sensors.pitch = data.get("stabilizer.pitch", 0.0)
        self._sensors.yaw = data.get("stabilizer.yaw", 0.0)
        self._sensors.gyro_x = data.get("gyro.x", 0.0)
        self._sensors.gyro_y = data.get("gyro.y", 0.0)
        self._sensors.gyro_z = data.get("gyro.z", 0.0)

    def set_logger(self, fn):
        """
        Set a custom output function for log messages.

        Args:
            fn: A callable that takes a string, e.g. print or your_logger.
        """
        self._logger_fn = fn
