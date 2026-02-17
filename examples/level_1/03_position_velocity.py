"""
Level 1 — Read Position & Velocity Data
==========================================
Connect to the drone and read optical flow-based position
and velocity estimates.

What you'll learn:
    - Dead reckoning: how position is estimated from optical flow
    - Velocity measurement from optical flow sensor
    - X and Y axes and what they mean
    - Raw vs processed sensor data

Note: Position and velocity readings are most meaningful when
the drone is in the air. On the ground, optical flow may give
noisy readings depending on surface texture.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# Connect (no motors!)
drone.connect()

# Wait for sensor data
time.sleep(2)

# Single reading
pos = drone.position
vel = drone.velocity
print("Position & Velocity:")
print(f"  Position: X = {pos[0]:.3f}m, Y = {pos[1]:.3f}m")
print(f"  Velocity: VX = {vel[0]:.4f} m/s, VY = {vel[1]:.4f} m/s")

# Read raw optical flow deltas
sensors = drone.read_sensors()
print(f"\n  Raw optical flow: deltaX = {sensors.delta_x}, deltaY = {sensors.delta_y}")

# Continuous reading for 10 seconds
print("\nLive position & velocity (10 seconds):")
print(f"  {'#':>3}  {'X (m)':>7}  {'Y (m)':>7}  {'VX (m/s)':>9}  {'VY (m/s)':>9}")
print(f"  {'---':>3}  {'-'*7}  {'-'*7}  {'-'*9}  {'-'*9}")

for i in range(20):
    sensors = drone.read_sensors()
    print(
        f"  {i+1:3d}  "
        f"{sensors.x:7.3f}  "
        f"{sensors.y:7.3f}  "
        f"{sensors.vx:9.4f}  "
        f"{sensors.vy:9.4f}"
    )
    time.sleep(0.5)

# Disconnect
drone.disconnect()
print("\nDone!")
