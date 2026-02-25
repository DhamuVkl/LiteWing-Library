# LiteWing 🛸

**Beginner-friendly Python library for LiteWing drone control.**

LiteWing removes the low-level plumbing from drone programming while keeping the core engineering concepts visible. Built on top of [cflib](https://github.com/bitcraze/crazyflie-lib-python), it provides a simple API for flying, sensor reading, PID tuning, and position hold.

## Installation

### Quick Install (Windows)
Double-click **`install.bat`** — it checks your Python version and installs everything automatically.

### Quick Install (macOS / Linux)
Open a terminal in the `litewing-library` folder and run:
```bash
chmod +x install.sh
./install.sh
```

### Manual Install
```bash
# Navigate to the litewing-library folder
cd litewing-library

# Install in development mode (recommended for students)
pip install -e .
```

### Requirements
- **Python 3.11** (required — other versions will not work)
  - Download: [Python 3.11.9](https://www.python.org/downloads/release/python-3119/)
  - ⚠️ Check **"Add Python to PATH"** during installation!
- [cflib](https://github.com/bitcraze/crazyflie-lib-python) (installed automatically)
- [matplotlib](https://matplotlib.org/) (installed automatically)

## Quick Start

### Level 1 — Read Sensors (No Flying!)

```python
from litewing import LiteWing
import time

drone = LiteWing("192.168.43.42")
drone.connect()          # Connect, no motors!
time.sleep(2)            # Wait for sensor data
print(f"Battery: {drone.battery:.2f}V")
print(f"Height:  {drone.height:.3f}m")
drone.disconnect()
```

### Level 2 — First Flight

```python
from litewing import LiteWing

drone = LiteWing("192.168.43.42")
drone.target_height = 0.3

drone.arm()
drone.fly(hover_duration=10)   # Takeoff, hover 10s, land
```

### Level 3 — PID Tuning & Waypoints

```python
from litewing import LiteWing

drone = LiteWing("192.168.43.42")

# Tune the position hold PID
drone.position_pid.kp = 1.5
drone.position_pid.ki = 0.03

# Fly a square path
square = [(0.5, 0), (0.5, -0.5), (0, -0.5), (0, 0)]

def mission(drone_ref, cf, has_pos_hold):
    from litewing._flight_engine import run_waypoint_maneuver
    drone_ref.set_led_color(0, 255, 0)
    run_waypoint_maneuver(drone_ref, cf, has_pos_hold, square)
    drone_ref.clear_leds()

drone.arm()
drone.fly(maneuver_fn=mission)
```

## What's Exposed vs Hidden

| You Configure (Educational)       | Library Handles (Plumbing)        |
|-----------------------------------|-----------------------------------|
| PID gains (kp, ki, kd)           | CRTP packet construction          |
| Position hold on/off             | Dead reckoning integration        |
| Optical flow scale               | cflib callbacks & threading       |
| Trim corrections                 | SyncCrazyflie context management  |
| Hold modes (current / origin)    | Axis swapping (vx ↔ vy)          |
| Firmware Z-axis PID              | LogConfig setup                   |
| Sensitivity, momentum comp.     | Retry & fallback logic            |

## API Reference

See [API_REFERENCE.md](litewing/API_REFERENCE.md) for the full list of every function, property, and configurable parameter.

## Project Structure

```
litewing-library/
├── pyproject.toml          # Package metadata & build config
├── README.md               # This file
├── LICENSE                  # MIT License
├── CHANGELOG.md            # Version history
├── litewing/               # The library package
│   ├── __init__.py         # Public exports: LiteWing, SensorData, PIDConfig
│   ├── litewing.py         # Main LiteWing class
│   ├── config.py           # All default constants
│   ├── pid.py              # PID controller
│   ├── sensors.py          # SensorData snapshot class
│   ├── position_hold.py    # Position hold controller
│   ├── manual_control.py   # Joystick/keyboard control
│   ├── leds.py             # NeoPixel LED control
│   ├── logger.py           # CSV flight data logger
│   ├── _connection.py      # Internal: cflib management
│   ├── _crtp.py            # Internal: CRTP packets
│   ├── _position.py        # Internal: dead reckoning
│   ├── _flight_engine.py   # Internal: flight state machine
│   └── _safety.py          # Internal: link/battery checks
├── examples/               # Example scripts (by level)
│   ├── level_1/            # Sensor reading — no flying
│   ├── level_2/            # Basic flight control
│   └── level_3/            # PID tuning, waypoints, advanced
└── tests/                  # Unit tests
    └── test_litewing.py
```

## License

MIT — see [LICENSE](LICENSE) for details.
