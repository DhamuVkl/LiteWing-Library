"""
LiteWing Configuration Defaults
================================
All tunable constants for the LiteWing drone library.
Each value has a comment explaining what it does and sensible defaults.

Learners can override these by setting properties on the LiteWing object:
    drone.target_height = 0.4   # Override default hover height

Advanced users can import this module to see all available constants:
    from litewing.config import defaults
"""


class _Defaults:
    """Container for all default configuration values."""

    # === CONNECTION ===
    # The IP address or URI of the drone. Usually "udp://<ip>"
    DRONE_IP = "192.168.43.42"

    # === FLIGHT PARAMETERS ===
    # Target hover height in meters (0.3m = 30cm above ground)
    TARGET_HEIGHT = 0.3
    # Time in seconds for the takeoff ramp
    TAKEOFF_TIME = 1.0
    # How long to hover by default (seconds)
    HOVER_DURATION = 20.0
    # Time in seconds for the landing descent (safety timeout)
    LANDING_TIME = 2.0
    # Descent rate in m/s for gradual landing (0.3 = 30cm per second)
    DESCENT_RATE = 0.3

    # === DEBUG & SAFETY ===
    # Set True to disable motors (sensors and logging still work)
    DEBUG_MODE = False
    # Set True to enable emergency stop if height sensor seems stuck during takeoff
    ENABLE_HEIGHT_SENSOR_SAFETY = False
    # Minimum height change expected during takeoff (meters)
    HEIGHT_SENSOR_MIN_CHANGE = 0.005
    # Low battery warning threshold in volts
    LOW_BATTERY_THRESHOLD = 2.9
    # Max allowed time between sensor packets before declaring timeout (seconds)
    DATA_TIMEOUT_THRESHOLD = 0.2

    # === TRIM CORRECTIONS ===
    # Offsets to counteract mechanical drift.
    # Positive TRIM_VX nudges the drone forward; positive TRIM_VY nudges right.
    TRIM_VX = 0.0  # Forward/backward trim
    TRIM_VY = 0.0  # Left/right trim

    # === PID CONTROLLER — POSITION LOOP ===
    # Controls how the drone corrects its X/Y position error.
    # Kp = proportional (how hard to push back), Ki = integral (fix steady-state drift),
    # Kd = derivative (dampen oscillation).
    POSITION_KP = 1.0
    POSITION_KI = 0.03
    POSITION_KD = 0.0

    # === PID CONTROLLER — VELOCITY LOOP ===
    # Second PID layer that dampens velocity to prevent overshooting.
    VELOCITY_KP = 0.7
    VELOCITY_KI = 0.01
    VELOCITY_KD = 0.0

    # === POSITION HOLD PARAMETERS ===
    # Maximum control correction allowed (limits how aggressively the drone corrects)
    MAX_CORRECTION = 0.7
    # Below this velocity (m/s) the drone is considered "stationary"
    VELOCITY_THRESHOLD = 0.005
    # Gentle pull toward zero when the drone is moving slowly (drift compensation)
    DRIFT_COMPENSATION_RATE = 0.004
    # Reset integrated position every N seconds to prevent drift accumulation
    PERIODIC_RESET_INTERVAL = 90.0
    # Clamp position error to prevent runaway PID corrections (meters)
    MAX_POSITION_ERROR = 2.0

    # === OPTICAL FLOW / VELOCITY ===
    # Sensor update rate in milliseconds
    SENSOR_PERIOD_MS = 10
    # Control loop update interval in seconds (0.02 = 50 Hz)
    CONTROL_UPDATE_RATE = 0.02
    # Empirical scaling factor for optical flow sensor (adjust for your setup)
    OPTICAL_FLOW_SCALE = 4.4
    # True = velocity calculation depends on altitude, False = fixed scaling
    USE_HEIGHT_SCALING = True
    # Velocity smoothing filter strength (0.0 = raw, 1.0 = maximum smoothing)
    VELOCITY_SMOOTHING_ALPHA = 0.85
    # Enable smooth altitude climb during takeoff (vs. instant target height)
    ENABLE_TAKEOFF_RAMP = False

    # === MANEUVER / WAYPOINT PARAMETERS ===
    # Default maneuver distance in meters
    MANEUVER_DISTANCE = 0.5
    # Threshold: "close enough" to the target position (meters)
    MANEUVER_THRESHOLD = 0.10
    # Abort waypoint if not reached within this many seconds
    WAYPOINT_TIMEOUT = 60.0
    # Pause at each waypoint for this many seconds
    WAYPOINT_STABILIZATION_TIME = 0.5

    # === JOYSTICK / MANUAL CONTROL ===
    # How fast the drone moves per key press (m/s per key held)
    JOYSTICK_SENSITIVITY = 0.2
    # "current" = hold at wherever you stop, "origin" = snap back to launch
    JOYSTICK_HOLD_MODE = "current"

    # === MOMENTUM COMPENSATION ===
    # When keys are released, predicts stopping position to prevent overshoot
    MOMENTUM_COMPENSATION_TIME = 0.10   # seconds (0.05 – 0.15 recommended)
    # Time to use gentler corrections after key release
    SETTLING_DURATION = 0.1             # seconds (0.1 – 0.3)
    # Correction strength during settling (lower = gentler stop)
    SETTLING_CORRECTION_FACTOR = 0.5    # 0.3 – 0.7

    # === FIRMWARE PARAMETERS (Z-AXIS) ===
    # These are sent to the drone's onboard controller (separate from Python PID)
    ENABLE_FIRMWARE_PARAMS = False
    FW_THRUST_BASE = 24000    # Base motor thrust (increase if drone feels heavy)
    FW_Z_POS_KP = 1.6         # Height position gain
    FW_Z_VEL_KP = 15.0        # Vertical velocity damping (stop height bouncing)

    # === CSV LOGGING ===
    # Set True to automatically create CSV log files
    ENABLE_CSV_LOGGING = False

    # === NEOPIXEL LED ===
    CRTP_PORT_NEOPIXEL = 0x09
    NEOPIXEL_CHANNEL_SET_PIXEL = 0x00
    NEOPIXEL_CHANNEL_SHOW = 0x01
    NEOPIXEL_CHANNEL_CLEAR = 0x02
    NEOPIXEL_CHANNEL_BLINK = 0x03
    NP_SEND_RETRIES = 3
    NP_PACKET_DELAY = 0.02
    NP_LINK_SETUP_DELAY = 0.12

    # === INTERNAL CONSTANTS ===
    import math
    DEG_TO_RAD = math.pi / 180.0


# Singleton instance that the library uses
defaults = _Defaults()
