"""
Level 0 — Basic Flight (No Sensors Required)
===============================================
Fly the drone using raw thrust — no ToF or optical flow needed!

What you'll learn:
    - send_control(): direct motor thrust
    - Roll, pitch, yaw basics
    - Why height sensors matter (you'll see the difference!)

How it works:
    Without sensors, the drone can't hold its height automatically.
    YOU control the throttle — like flying an RC drone.
    Start with low thrust and increase slowly!

    Thrust guide:
        0      = motors off
        15000  = propellers spinning, not enough to fly
        20000  = light lift (depends on battery)
        25000  = moderate lift
        35000  = max allowed (safety limit)

SAFETY:
    - Fly over a soft surface (bed, foam mat)
    - Start with LOW thrust values
    - Keep the flight SHORT (1-2 seconds)
    - Press Ctrl+C to emergency stop anytime
"""

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# Skip sensor check — we know sensors aren't attached!
drone.enable_sensor_check = False

# ── Trim corrections (adjust if drone drifts) ────────
# If the drone drifts left/right, adjust trim_roll
# If the drone drifts forward/back, adjust trim_pitch
# Positive trim_roll = tilts right, Positive trim_pitch = tilts backward
drone.trim_roll = 0.0    # degrees (try small values: -3.0 to 3.0)
drone.trim_pitch = 0.0   # degrees (try small values: -3.0 to 3.0)

# ── Connect ──────────────────────────────────────────
drone.connect()
time.sleep(1)

# Pre-flight check
print(f"Battery: {drone.battery:.2f}V")
if drone.battery < 3.3:
    print("Battery too low! Charge before flying.")
    drone.disconnect()
    exit()


# ── IMPORTANT: Unlock motors ────────────────────────
# Must send a zero-thrust setpoint first to unlock the commander
drone.send_control(thrust=0)
time.sleep(0.5)

# ── Fly! ─────────────────────────────────────────────
# STEP 1: Spin up motors gently (not enough to lift off)
print("Step 1: Spinning motors gently...")
drone.send_control(thrust=15000)
time.sleep(1)

# STEP 2: Increase thrust to lift off briefly
print("Step 2: Light liftoff...")
for thrust in range(15000, 25000, 1000):
    drone.send_control(thrust=thrust)
    time.sleep(0.1)

# STEP 3: Hold for 1 second
print("Step 3: Holding thrust for 1 second...")
drone.send_control(thrust=25000)
time.sleep(1)

# STEP 4: Cut motors — drone will descend
print("Step 4: Motors off!")
drone.send_control(thrust=0)
time.sleep(0.5)

# ── Done ─────────────────────────────────────────────
drone.send_control(thrust=0)
time.sleep(0.3)
drone.disconnect()
print("Flight complete!")
print()
print("Notice: Without height sensors, the drone couldn't hold")
print("a steady altitude. That's what the ToF sensor module does!")
