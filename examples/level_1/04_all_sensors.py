"""
Level 1 — Read All Sensors
=============================
Connect to the drone and read ALL available sensor data
in one combined view.

What you'll learn:
    - Complete sensor overview
    - How SensorData snapshot works
    - Understanding what data the drone provides
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

# Read everything at once
sensors = drone.read_sensors()

print("=" * 50)
print("     LiteWing — All Sensor Readings")
print("=" * 50)
print()
print(f"  Battery:     {sensors.battery:.2f} V")
print()
print(f"  Height:      {sensors.height:.3f} m  (barometer)")
print(f"  Range:       {sensors.range_height:.3f} m  (range finder)")
print()
print(f"  Position X:  {sensors.x:.3f} m")
print(f"  Position Y:  {sensors.y:.3f} m")
print()
print(f"  Velocity X:  {sensors.vx:.4f} m/s")
print(f"  Velocity Y:  {sensors.vy:.4f} m/s")
print()
print(f"  Flow dX:     {sensors.delta_x}")
print(f"  Flow dY:     {sensors.delta_y}")
print()
print("=" * 50)

# Live dashboard for 15 seconds
print("\nLive sensor dashboard (15 seconds):")
print("Press Ctrl+C to stop early.\n")

try:
    for i in range(30):
        s = drone.read_sensors()
        print(
            f"  [{i+1:2d}]  "
            f"Bat: {s.battery:.2f}V  |  "
            f"H: {s.height:.3f}m  |  "
            f"Pos: ({s.x:.2f}, {s.y:.2f})  |  "
            f"Vel: ({s.vx:.3f}, {s.vy:.3f})"
        )
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n  Stopped by user.")

# Disconnect
drone.disconnect()
print("\nDone!")
