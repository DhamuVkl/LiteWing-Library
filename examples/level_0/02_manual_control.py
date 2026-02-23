"""
Level 0 — Manual Control (No Sensors Required)
=================================================
Fly the drone with WASD + throttle keys — no ToF or optical flow needed!

What you'll learn:
    - Raw thrust control with keyboard
    - How roll/pitch/yaw work
    - Why position hold sensors matter

Controls:
    R = Throttle UP (more power)
    F = Throttle DOWN (less power)
    W = Pitch forward
    S = Pitch backward
    A = Roll left
    D = Roll right
    Q = Spin left (yaw)
    E = Spin right (yaw)
    SPACE = Kill motors (emergency stop)

Throttle starts at 0 and increases/decreases in steps.

SAFETY:
    - Fly over a soft surface
    - Increase throttle SLOWLY with R key
    - Press SPACE immediately if drone tilts dangerously
    - Press Ctrl+C as backup emergency stop
"""

import time
import sys
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# Skip sensor check — we're doing raw control
drone.enable_sensor_check = False

# ── Trim corrections (adjust if drone drifts) ────────
# If the drone drifts left/right, adjust trim_roll
# If the drone drifts forward/back, adjust trim_pitch
drone.trim_roll = 0.0    # degrees (try -3.0 to 3.0)
drone.trim_pitch = 0.0   # degrees (try -3.0 to 3.0)

# ── Settings ─────────────────────────────────────────
THRUST_STEP = 1000       # How much thrust changes per R/F press
TILT_ANGLE = 5.0         # Roll/pitch in degrees per key
YAW_RATE = 30.0          # Yaw speed in degrees/sec
MAX_THRUST = 35000       # Safety cap

# ── Connect ──────────────────────────────────────────
drone.connect()
time.sleep(1)

print(f"Battery: {drone.battery:.2f}V")
if drone.battery < 3.3:
    print("Battery too low!")
    drone.disconnect()
    exit()

# Unlock the commander
drone.send_control(thrust=0)
time.sleep(0.5)

# ── Keyboard listener ────────────────────────────────
try:
    import msvcrt
except ImportError:
    print("ERROR: This script requires Windows (msvcrt)")
    drone.disconnect()
    exit()

thrust = 0
roll = 0.0
pitch = 0.0
yawrate = 0.0
running = True

print()
print("=== MANUAL RAW CONTROL ===")
print(f"  Thrust step:  {THRUST_STEP}")
print(f"  Tilt angle:   {TILT_ANGLE} degrees")
print(f"  Max thrust:   {MAX_THRUST}")
print()
print("Controls:")
print("  R/F = Throttle up/down")
print("  W/S = Pitch forward/back")
print("  A/D = Roll left/right")
print("  Q/E = Yaw left/right")
print("  SPACE = KILL MOTORS")
print()
print("Starting... use R to slowly increase throttle")

while running:
    # Reset tilt each loop (only held while key is pressed)
    roll = 0.0
    pitch = 0.0
    yawrate = 0.0

    if msvcrt.kbhit():
        ch = msvcrt.getch()

        # Handle Ctrl+C
        if ch == b'\x03':
            print("\n Ctrl+C -- EMERGENCY STOP!")
            drone.emergency_stop()
            break

        ch_str = ch.decode("utf-8", errors="ignore").lower()

        if ch_str == ' ':
            # SPACE = kill motors
            print("SPACE -- MOTORS OFF!")
            thrust = 0
            drone.send_control(thrust=0)
            running = False
            break

        elif ch_str == 'r':
            # Throttle UP
            thrust = min(thrust + THRUST_STEP, MAX_THRUST)
            print(f"  Thrust: {thrust}")

        elif ch_str == 'f':
            # Throttle DOWN
            thrust = max(thrust - THRUST_STEP, 0)
            print(f"  Thrust: {thrust}")

        elif ch_str == 'w':
            pitch = -TILT_ANGLE     # Forward

        elif ch_str == 's':
            pitch = TILT_ANGLE      # Backward

        elif ch_str == 'a':
            roll = -TILT_ANGLE      # Left

        elif ch_str == 'd':
            roll = TILT_ANGLE       # Right

        elif ch_str == 'q':
            yawrate = -YAW_RATE     # Spin left

        elif ch_str == 'e':
            yawrate = YAW_RATE      # Spin right

    # Send control at ~50Hz
    drone.send_control(roll=roll, pitch=pitch, yawrate=yawrate, thrust=thrust)



    time.sleep(0.02)

# ── Cleanup ──────────────────────────────────────────
drone.send_control(thrust=0)
time.sleep(0.3)
drone.disconnect()
print("Done!")
