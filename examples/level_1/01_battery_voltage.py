"""
Level 1 — Read Battery Voltage
================================
Connect to the drone and read battery voltage.
No arming, no flying — just sensor reading.

What you'll learn:
    - Connecting to the drone
    - Reading battery voltage
    - Safe disconnection
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# Connect to the drone (no motors!)
drone.connect()

# Wait for battery data to arrive
time.sleep(2)

# Read battery
print(f"Battery Voltage: {drone.battery:.2f}V")

# Continuous reading for 10 seconds
print("\nLive battery readings (10 seconds):")
for i in range(20):
    print(f"  [{i+1:2d}] Battery: {drone.battery:.2f}V")
    time.sleep(0.5)

# Disconnect
drone.disconnect()
print("\nDone!")
