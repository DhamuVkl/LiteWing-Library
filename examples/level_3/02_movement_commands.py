"""
Level 3 — Movement Commands
=============================
Fly a square pattern using movement commands.

What you'll learn:
    - forward(), backward(), left(), right()
    - Combining movements into a pattern
    - The fly() helper for safe automated flights

 SAFETY: Make sure you have at least 2m × 2m of clear space!
"""

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")
drone.target_height = 0.3
drone.max_correction = 0.9

# ─── Method 1: Step-by-step ─────────────────────────
# This shows exactly what happens at each stage.

drone.connect()
time.sleep(2)

print(f"Battery: {drone.battery:.2f}V")

drone.set_led_color(0, 255, 0)  # Green = go
time.sleep(1)

drone.arm()
drone.takeoff()

# print("Flying a square pattern...")

# Fly a 30cm square
print("  → Forward")
drone.pitch_forward(0.3, speed=0.7)
drone.hover(1)

print("  → Right")
drone.roll_right(0.3, speed=0.7)
drone.hover(1)

print("  → Backward")
drone.pitch_backward(0.3, speed=0.7)
drone.hover(1)

print("  → Left")
drone.roll_left(0.3, speed=0.7)
drone.hover(1)

print("Square complete!")
drone.land()
drone.clear_leds()
drone.disconnect()

print("Done!")
