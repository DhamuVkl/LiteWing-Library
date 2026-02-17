"""
Level 1 — Live Height Plot (GUI)
==================================
Open a live plot comparing:
  - Kalman-filtered height (smooth)
  - Raw ToF laser reading (noisy)

Try moving your hand above the drone's ToF sensor to see
the difference between filtered and raw readings!

Close the window or press Ctrl+C to stop.
"""

from litewing import LiteWing
from litewing.gui import live_height_plot

drone = LiteWing("192.168.43.42")
live_height_plot(drone)
