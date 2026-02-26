"""
Level 2 — LED Control
======================
Control the NeoPixel LEDs on the drone.

What you'll learn:
    - Setting solid LED colors (RGB) — all LEDs
    - Setting individual LED colors (4 LEDs: 0–3)
    - Making LEDs blink
    - Turning LEDs off

No motors are started — safe to run on your desk!
"""

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")
drone.connect()

# ── Solid colors (all LEDs) ──────────────────────────

print("Red...")
drone.set_led_color(255, 0, 0)
time.sleep(1)

print("Green...")
drone.set_led_color(0, 255, 0)
time.sleep(1)

print("Blue...")
drone.set_led_color(0, 0, 255)
time.sleep(1)

print("White...")
drone.set_led_color(255, 255, 255)
time.sleep(1)

print("Purple...")
drone.set_led_color(128, 0, 255)
time.sleep(1)

# ── Individual LED colors ────────────────────────────

print("Each LED a different color...")
drone.set_led(0, 255, 0,   0)    # LED 0 = Red
drone.set_led(1, 0,   255, 0)    # LED 1 = Green
drone.set_led(2, 0,   0,   255)  # LED 2 = Blue
drone.set_led(3, 255, 255, 0)    # LED 3 = Yellow
time.sleep(2)

print("Rotating pattern...")
colors = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
]
for _ in range(4):  # 4 rotations
    for i in range(4):
        r, g, b = colors[(i + _) % 4]
        drone.set_led(i, r, g, b)
    time.sleep(0.5)

# ── Blinking ─────────────────────────────────────────

print("Blinking (fast)...")
drone.set_led_color(128, 0, 255)
drone.blink_leds(on_ms=200, off_ms=200)
time.sleep(3)

print("Blinking (slow)...")
drone.blink_leds(on_ms=800, off_ms=800)
time.sleep(3)

# ── Turn off ─────────────────────────────────────────

print("LEDs off.")
drone.clear_leds()
time.sleep(1)

# Disconnect
drone.disconnect()
print("Done!")
