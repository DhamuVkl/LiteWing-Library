"""
Level 1 — Read Height Data
============================
Connect to the drone and read height from two sensors:
  - stateEstimate.z (barometric altimeter)
  - range.zrange    (laser/sonar range finder)

What you'll learn:
    - Two different ways to measure height
    - Barometric vs range-based altitude
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
print(f"  State Estimate (barometer): {drone.height:.3f}m")

sensors = drone.read_sensors()
print(f"  Range Finder:               {sensors.range_height:.3f}m")

# Continuous reading for 10 seconds
print("\nLive height readings (10 seconds):")
print(f"  {'#':>3}  {'Barometer (m)':>14}  {'Range (m)':>10}")
print(f"  {'---':>3}  {'-' * 14}  {'-' * 10}")

for i in range(20):
    sensors = drone.read_sensors()
    print(
        f"  {i+1:3d}  "
        f"{sensors.height:14.3f}  "
        f"{sensors.range_height:10.3f}"
    )
    time.sleep(0.5)

# Disconnect
drone.disconnect()
print("\nDone!")
