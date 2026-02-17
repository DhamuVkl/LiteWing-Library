# LiteWing 🛸

**Beginner-friendly Python library for LiteWing drone control.**

LiteWing removes the low-level plumbing from drone programming while keeping the core engineering concepts visible. Built on top of [cflib](https://github.com/bitcraze/crazyflie-lib-python), it provides a simple API for flying, sensor reading, PID tuning, and position hold.

## Installation

```bash
# From the project directory
pip install -e .

# Or install from source
pip install .
```

### Requirements
- Python 3.8+
- [cflib](https://github.com/bitcraze/crazyflie-lib-python) (installed automatically)

## Quick Start

### Tier 1 — Beginner: First Flight

```python
from litewing import LiteWing

drone = LiteWing("192.168.43.42")
drone.target_height = 0.3

drone.arm()
drone.fly(hover_duration=10)   # Takeoff, hover 10s, land
```

### Tier 2 — Intermediate: Sensors & Manual Control

```python
from litewing import LiteWing

drone = LiteWing("192.168.43.42")
drone.trim_forward = 0.02      # Correct drift
drone.hold_mode = "current"    # Hold at current position on key release

drone.arm()
drone.start_manual_control()   # WASD keyboard control
```

### Tier 3 — Advanced: PID Tuning & Waypoints

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
    drone_ref.set_led_color(0, 255, 0)   # Green = navigating
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
│   ├── pid.py              # PID controller (public)
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
├── examples/               # Example scripts
│   ├── tier1_first_flight.py
│   ├── tier2_sensors_and_control.py
│   └── tier3_pid_and_waypoints.py
└── tests/                  # Unit tests
    └── test_litewing.py
```

## License

MIT — see [LICENSE](LICENSE) for details.
