"""
Level 1 — Read Height Data
============================
Connect to the drone and read height from the VL53L1x ToF laser:
  - stateEstimate.z (Kalman-filtered height estimate)
  - range.zrange    (raw ToF laser measurement)

What you'll learn:
    - Two different ways to read height (raw vs filtered)
    - How the Kalman filter smooths the raw ToF reading
    - Reading live sensor data
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# Connect (no motors!)
drone.connect()

# Wait for sensor data to arrive
time.sleep(2)

# Read height from both sensors
print("Height Sensor Readings:")
print(f"  Kalman-filtered (stateEstimate.z): {drone.height:.3f}m")

sensors = drone.read_sensors()
print(f"  Raw ToF laser (range.zrange):      {sensors.range_height:.3f}m")

# Continuous reading for 10 seconds
print("\nLive height readings (10 seconds):")
print(f"  {'#':>3}  {'Filtered (m)':>13}  {'Raw ToF (m)':>12}")
print(f"  {'---':>3}  {'-' * 13}  {'-' * 12}")

for i in range(20):
    sensors = drone.read_sensors()
    print(
        f"  {i+1:3d}  "
        f"{sensors.height:13.3f}  "
        f"{sensors.range_height:12.3f}"
    )
    time.sleep(0.5)

# Disconnect
drone.disconnect()
print("\nDone!")
