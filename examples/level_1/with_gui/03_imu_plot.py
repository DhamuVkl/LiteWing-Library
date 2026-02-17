"""
Level 1 — Live IMU Plot (GUI)
===============================
Open a live 2-panel plot showing:
  - Orientation: roll, pitch, yaw (degrees)
  - Gyroscope: rotation speed X, Y, Z (°/s)

Try tilting the drone to see the IMU respond in real time!

Close the window or press Ctrl+C to stop.
"""

from litewing import LiteWing
from litewing.gui import live_imu_plot

drone = LiteWing("192.168.43.42")
live_imu_plot(drone)
