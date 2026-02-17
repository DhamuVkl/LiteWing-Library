"""
LiteWing Example — Tier 1: Beginner
=====================================
Your first flight! Connect, take off, hover, and land.

What you'll learn:
    - How to connect to the drone
    - Arming as a safety concept
    - Basic flight commands
    - Reading battery voltage DURING flight
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from litewing import LiteWing

# Create the drone controller
drone = LiteWing("192.168.43.42")

# Set flight parameters
drone.target_height = 0.3    # Hover at 30cm
drone.hover_duration = 10    # Hover for 10 seconds

# Define what happens during flight
def my_flight(drone_ref, cf, has_pos_hold):
    """This runs while the drone is hovering."""
    import time
    from litewing._flight_engine import _hover_loop

    # NOW we can read sensors — the drone is connected and flying!
    sensors = drone_ref.read_sensors()
    print(f"Battery: {sensors.battery:.2f}V")
    print(f"Height: {sensors.height:.3f}m")
    print(f"Position: ({sensors.x:.2f}, {sensors.y:.2f})")

    # Check battery safety
    if sensors.battery > 0 and sensors.battery < 3.0:
        print("WARNING: Battery low!")

    # Hover for the remaining duration
    _hover_loop(drone_ref, cf, has_pos_hold, drone_ref.hover_duration)


# Arm and fly!
print("Hello LiteWing!")
drone.arm()
drone.fly(maneuver_fn=my_flight)
print("Flight complete!")
