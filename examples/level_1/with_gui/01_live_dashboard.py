"""
Level 1 — Live Sensor Dashboard (GUI)
=======================================
Open a full 4-panel live dashboard showing:
  - Height (filtered vs raw)
  - IMU attitude (roll, pitch, yaw)
  - Velocity (vx, vy)
  - Battery voltage

Just run this script — the GUI window opens automatically!
Close the window or press Ctrl+C to stop.
"""

from litewing import LiteWing
from litewing.gui import live_dashboard

drone = LiteWing("192.168.43.42")
live_dashboard(drone)
