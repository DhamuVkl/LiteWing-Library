"""
LiteWing — Beginner-Friendly Drone Library
=============================================

from litewing import LiteWing, SensorData, PIDConfig

Quick Start (Tier 1):
    with LiteWing("192.168.43.42") as drone:
        drone.arm()
        drone.fly(hover_duration=10)

Intermediate (Tier 2):
    drone = LiteWing("192.168.43.42")
    drone.hover_trim_pitch = 0.02
    sensors = drone.read_sensors()
    print(sensors.battery)

Advanced (Tier 3):
    drone.position_pid.kp = 1.5
    drone.optical_flow_scale = 5.0
    drone.hold_mode = "origin"
"""

from .litewing import LiteWing
from .sensors import SensorData
from .pid import PIDConfig

__all__ = ["LiteWing", "SensorData", "PIDConfig"]
__version__ = "0.1.0"
