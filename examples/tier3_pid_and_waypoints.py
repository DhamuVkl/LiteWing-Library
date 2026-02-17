"""
LiteWing Example — Tier 3: Advanced Beginner
===============================================
PID tuning, position hold configuration, waypoint navigation,
and firmware parameter tuning.

What you'll learn:
    - How PID gains affect flight stability
    - Position hold parameters and their effects
    - Flying autonomous waypoint paths
    - Firmware (Z-axis) tuning
    - LED feedback for flight states
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# === PID Tuning ===
# The drone has TWO PID loops for horizontal control (there's a third on
# the drone's firmware for vertical/height control).
#
# Position PID — how hard the drone corrects position error:
#   kp = 1.0  → mild corrections (good starting point)
#   kp = 2.0  → aggressive corrections (may oscillate!)
#   ki = 0.03 → slowly fixes persistent drift
#   kd = 0.0  → no derivative (add 0.01–0.05 if oscillating)
drone.position_pid.kp = 1.0
drone.position_pid.ki = 0.03
drone.position_pid.kd = 0.0

# Velocity PID — dampens velocity to prevent overshooting:
drone.velocity_pid.kp = 0.7
drone.velocity_pid.ki = 0.01
drone.velocity_pid.kd = 0.0

# === Position Hold Configuration ===
drone.max_correction = 0.7               # Max PID output (limits aggression)
drone.velocity_threshold = 0.005         # Below this = "stationary"
drone.drift_compensation_rate = 0.004    # Gentle pull toward zero
drone.optical_flow_scale = 4.4           # Sensor calibration (adjust for your drone!)
drone.position_reset_interval = 90.0     # Reset integration every 90s

# === Firmware Parameters ===
# The Z-axis (height) is controlled by the drone's firmware, not Python.
# You can tune the firmware PID from here:
drone.enable_firmware_params = True
drone.thrust_base = 24000     # Base motor power (increase if drone feels heavy)
drone.z_position_kp = 1.6     # Height position gain
drone.z_velocity_kp = 15.0    # Vertical velocity damping (reduce bouncing)

# === Waypoint Navigation ===
# Define a square path: 0.5m per side
square_path = [
    (0.5, 0.0),    # Forward
    (0.5, -0.5),   # Forward + Right
    (0.0, -0.5),   # Right
    (0.0, 0.0),    # Back to start
]

# Flight parameters
drone.target_height = 0.3
drone.waypoint_threshold = 0.10             # "Close enough" = 10cm
drone.waypoint_stabilization_time = 0.5     # Pause 0.5s at each corner
drone.enable_csv_logging = True
drone.trim_forward = 0.0
drone.trim_right = 0.0

# === LED Feedback ===
# We'll use LEDs to show flight state in the maneuver function

def my_mission(drone_ref, cf, has_pos_hold):
    """Custom mission: fly a square with LED color changes."""
    from litewing._flight_engine import run_waypoint_maneuver

    # Green = navigating
    drone_ref.set_led_color(0, 255, 0)

    # Fly the path
    run_waypoint_maneuver(drone_ref, cf, has_pos_hold, square_path)

    # Blue = mission complete, hovering
    drone_ref.set_led_color(0, 0, 255)

    import time
    time.sleep(3)  # Hover for 3s at the end
    drone_ref.clear_leds()


# Execute!
drone.arm()
print("Starting square path mission with PID tuning...")
drone.fly(maneuver_fn=my_mission)
print("Mission complete!")
