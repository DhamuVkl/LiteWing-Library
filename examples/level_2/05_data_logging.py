"""
Level 2 — Data Logging
========================
Record flight data to a CSV file for analysis.

What you'll learn:
    - Starting and stopping the flight logger
    - What data gets recorded (position, height, velocity)
    - How to review your flight data afterwards

The CSV file is saved in the current directory.
Open it in Excel, Google Sheets, or plot it with Python!
"""

import time
from litewing import LiteWing

drone = LiteWing("192.168.43.42")
drone.target_height = 0.3

drone.connect()
time.sleep(2)

print(f"Battery: {drone.battery:.2f}V")

# ── Start logging BEFORE flight ──────────────────────
drone.start_logging("my_flight_log.csv")
print("Logging started!")

# ── Fly ──────────────────────────────────────────────
drone.arm()
drone.takeoff()

drone.forward(0.3, speed=0.7)
drone.wait(2)

drone.backward(0.3, speed=0.7)
drone.wait(2)

drone.land()

# ── Stop logging AFTER landing ───────────────────────
drone.stop_logging()
print("Logging stopped!")

drone.disconnect()

# ── Review the data ──────────────────────────────────
print("\n--- Flight Log Preview ---")
try:
    with open("my_flight_log.csv", "r") as f:
        lines = f.readlines()
        # Print header + first 5 data rows
        for line in lines[:6]:
            print(line.strip())
        if len(lines) > 6:
            print(f"  ... ({len(lines) - 1} total data rows)")
except FileNotFoundError:
    print("Log file not found (flight may not have produced data).")

print("\nDone! Open 'my_flight_log.csv' in a spreadsheet to analyze.")
