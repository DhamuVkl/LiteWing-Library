"""
LiteWing — Beginner-Friendly Drone Library
=============================================
Control your LiteWing drone with simple, educational Python code.

Quick Start:
    from litewing import LiteWing

    with LiteWing("192.168.43.42") as drone:
        drone.arm()
        drone.takeoff()
        drone.forward(0.5, speed=0.2)
        drone.land()

The LiteWing class is your "remote control." It handles all the low-level
communication, but keeps drone engineering concepts visible so you can learn
about sensors, PID tuning, position hold, and flight control.
"""

import time
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
        self.hover_duration = defaults.HOVER_DURATION
        self.enable_takeoff_ramp = defaults.ENABLE_TAKEOFF_RAMP

        # Trim corrections
        self.trim_forward = defaults.TRIM_VX
        self.trim_right = defaults.TRIM_VY

        # Debug & safety
        self.debug_mode = defaults.DEBUG_MODE
        self.enable_height_sensor_safety = defaults.ENABLE_HEIGHT_SENSOR_SAFETY
        self.enable_csv_logging = defaults.ENABLE_CSV_LOGGING
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

    # === Context Manager (with statement) ===

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.emergency_stop()
        return False

    # === Connection ===

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

        This must be called before takeoff. Arming checks that the connection
        is ready and initializes the flight controller.
        """
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
        if height is not None:
            self.target_height = height

    def land(self):
        """
        Land the drone safely.

        Descends to ground and stops motors.
        """
        self._flight_active = False

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
                self._scf.cf.commander.send_setpoint(0, 0, 0, 0)
            except Exception:
                pass
        self._leds.clear()

    def wait(self, seconds):
        """
        Wait (hover in place) for the specified duration.

        Args:
            seconds: How long to hover in seconds.
        """
        time.sleep(seconds)

    # === Movement Commands (Tier 1) ===

    def forward(self, distance=None, speed=0.2):
        """
        Move forward by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Movement speed in m/s.
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(0.0, distance, speed)

    def backward(self, distance=None, speed=0.2):
        """
        Move backward by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Movement speed in m/s.
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(0.0, -distance, speed)

    def left(self, distance=None, speed=0.2):
        """
        Move left by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Movement speed in m/s.
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(distance, 0.0, speed)

    def right(self, distance=None, speed=0.2):
        """
        Move right by the specified distance.

        Args:
            distance: Distance in meters (default: drone.maneuver_distance).
            speed: Movement speed in m/s.
        """
        if distance is None:
            distance = self.maneuver_distance
        self._execute_movement(-distance, 0.0, speed)

    def _execute_movement(self, dx, dy, speed):
        """Queue a relative movement as a waypoint offset."""
        target_x = self._position_engine.x + dx
        target_y = self._position_engine.y + dy
        self._pending_waypoints = [(target_x, target_y)]
        if self._logger_fn:
            self._logger_fn(
                f"Moving to ({target_x:.2f}, {target_y:.2f}) at {speed} m/s"
            )

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

    def fly_to(self, x, y, threshold=None):
        """
        Fly to an absolute position (x, y) using position hold.

        This is a BLOCKING call — it returns when the drone reaches
        the target (within threshold) or times out.

        Args:
            x: Target X position in meters.
            y: Target Y position in meters.
            threshold: How close is "close enough" (meters).
        """
        if threshold is None:
            threshold = self.waypoint_threshold
        self._pending_waypoints = [(x, y)]

    def fly_path(self, waypoints, threshold=None):
        """
        Fly through a sequence of (x, y) waypoints.

        Args:
            waypoints: List of (x, y) tuples.
            threshold: How close is "close enough" (meters).
        """
        if threshold is None:
            threshold = self.waypoint_threshold
        self._pending_waypoints = list(waypoints)

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

    def set_logger(self, fn):
        """
        Set a custom output function for log messages.

        Args:
            fn: A callable that takes a string, e.g. print or your_logger.
        """
        self._logger_fn = fn
