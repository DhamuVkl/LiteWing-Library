"""
LiteWing Example — Tier 2: Intermediate
==========================================
Sensor reading, trim tuning, data logging, and manual control.

What you'll learn:
    - Reading and printing live sensor data
    - Adjusting trim to correct drift
    - Recording flight data to CSV
    - Using manual (joystick) control with position hold
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# === Trim Tuning ===
# If your drone drifts forward, add negative trim_forward.
# If it drifts right, add negative trim_right.
drone.trim_forward = 0.0   # Adjust this based on testing
drone.trim_right = 0.0     # Adjust this based on testing

# === Data Logging ===
# Enable automatic CSV logging — creates a file with position, velocity,
# and correction data that you can plot in Excel or Python.
drone.enable_csv_logging = True

# === Sensor & Height ===
drone.target_height = 0.3   # Hover at 30cm

# === Manual Control Example ===
# Switch between two hold modes to feel the difference:
drone.hold_mode = "current"  # Try changing to "origin"
drone.sensitivity = 0.2     # How fast the drone responds to keys

print("Starting manual control...")
print("Controls: W=forward, S=back, A=left, D=right")
print(f"Hold mode: {drone.hold_mode}")

drone.arm()
drone.start_manual_control()

# Simulate keyboard input for 20 seconds
# In a real application, you'd wire this to tkinter or pygame key events
try:
    start = time.time()
    while time.time() - start < 20:
        # Read and display live sensor data
        sensors = drone.read_sensors()
        print(
            f"  Pos: ({sensors.x:.2f}, {sensors.y:.2f})  "
            f"Height: {sensors.height:.2f}m  "
            f"Vel: ({sensors.vx:.3f}, {sensors.vy:.3f})  "
            f"Battery: {sensors.battery:.2f}V",
            end="\r"
        )
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nStopping...")

drone.stop_manual_control()
print("\nFlight complete! Check the CSV log file for data.")
