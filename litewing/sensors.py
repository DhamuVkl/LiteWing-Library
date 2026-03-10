"""
LiteWing Sensor Data
=====================
Access live sensor readings from the drone.

The drone has several sensors:
    - VL53L1x ToF (Time-of-Flight) laser — measures height to the ground
    - PMW3901 optical flow sensor — tracks ground movement for velocity/position
    - IMU (accelerometer + gyroscope) — measures orientation and motion
    - Battery voltage monitor — tracks remaining power

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
        height (float): Kalman-filtered height estimate (meters, from VL53L1x ToF laser).
        range_height (float): Raw height from VL53L1x ToF laser (meters).
        vx (float): Velocity in X axis (m/s, from optical flow).
        vy (float): Velocity in Y axis (m/s, from optical flow).
        x (float): Estimated X position (meters, from dead reckoning).
        y (float): Estimated Y position (meters, from dead reckoning).
        battery (float): Battery voltage (volts).
        delta_x (int): Raw optical flow delta X (sensor units).
        delta_y (int): Raw optical flow delta Y (sensor units).
        roll (float): Roll angle (degrees).
        pitch (float): Pitch angle (degrees).
        yaw (float): Yaw angle (degrees).
        acc_x (float): Accelerometer X (g).
        acc_y (float): Accelerometer Y (g).
        acc_z (float): Accelerometer Z (g).
        gyro_x (float): Gyroscope X (deg/s).
        gyro_y (float): Gyroscope Y (deg/s).
        gyro_z (float): Gyroscope Z (deg/s).
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
        # IMU data
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.acc_z = 0.0
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0
        self.thrust = 0.0

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
        # Raw firmware optical flow values (before any axis remapping)
        self.raw_delta_x = 0   # literal motion.deltaX from firmware
        self.raw_delta_y = 0   # literal motion.deltaY from firmware
        # IMU state
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.acc_z = 0.0
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0
        self.thrust = 0.0

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
        # IMU
        s.roll = self.roll
        s.pitch = self.pitch
        s.yaw = self.yaw
        s.acc_x = self.acc_x
        s.acc_y = self.acc_y
        s.acc_z = self.acc_z
        s.gyro_x = self.gyro_x
        s.gyro_y = self.gyro_y
        s.gyro_z = self.gyro_z
        s.thrust = self.thrust
        return s
