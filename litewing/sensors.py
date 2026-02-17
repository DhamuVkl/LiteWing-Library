"""
LiteWing Sensor Data
=====================
Access live sensor readings from the drone.

The drone has several sensors:
    - Height sensor (barometer + range finder) — how high the drone is
    - Optical flow sensor — tracks ground movement to estimate velocity
    - Battery voltage — monitors remaining power

Usage:
    sensors = drone.read_sensors()
    print(f"Height: {sensors.height} m")
    print(f"Velocity: ({sensors.vx}, {sensors.vy}) m/s")
    print(f"Position: ({sensors.x}, {sensors.y}) m")
    print(f"Battery: {sensors.battery} V")
"""

import time


class SensorData:
    """
    A snapshot of all sensor readings at a moment in time.

    Attributes:
        height (float): Estimated height from barometer (meters).
        range_height (float): Height from range finder (meters).
        vx (float): Velocity in X axis (m/s, from optical flow).
        vy (float): Velocity in Y axis (m/s, from optical flow).
        x (float): Estimated X position (meters, from dead reckoning).
        y (float): Estimated Y position (meters, from dead reckoning).
        battery (float): Battery voltage (volts).
        delta_x (int): Raw optical flow delta X (sensor units).
        delta_y (int): Raw optical flow delta Y (sensor units).
    """

    def __init__(self):
        self.height = 0.0
        self.range_height = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.x = 0.0
        self.y = 0.0
        self.battery = 0.0
        self.delta_x = 0
        self.delta_y = 0

    def __repr__(self):
        return (
            f"SensorData(height={self.height:.3f}m, "
            f"vel=({self.vx:.3f}, {self.vy:.3f})m/s, "
            f"pos=({self.x:.3f}, {self.y:.3f})m, "
            f"battery={self.battery:.2f}V)"
        )


class _SensorState:
    """Internal mutable sensor state, updated by callbacks."""

    def __init__(self):
        self.height = 0.0
        self.range_height = 0.0
        self.battery_voltage = 0.0
        self.sensor_data_ready = False
        self.battery_data_ready = False
        self.last_sensor_heartbeat = time.time()

    def snapshot(self, position_engine):
        """Create a SensorData snapshot from current internal state."""
        s = SensorData()
        s.height = self.height
        s.range_height = self.range_height
        s.vx = position_engine.vx
        s.vy = position_engine.vy
        s.x = position_engine.x
        s.y = position_engine.y
        s.battery = self.battery_voltage
        s.delta_x = position_engine.delta_x
        s.delta_y = position_engine.delta_y
        return s
