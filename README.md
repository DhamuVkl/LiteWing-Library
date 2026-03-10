# LiteWing

**Beginner-friendly Python library for LiteWing drone control.**

Using this library, you will be able to fly your drone using simple lines of Python code. For example, you can ask it to take off and hold its position at a particular height, then land automatically, or even move in a particular direction for a fixed distance and then land.

## Documentation
Read project Doc: [LiteWing Python Library](https://circuitdigest.com/articles/litewing-drone-python-library-documentation)

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
pip install .

```

### Requirements
- **Python 3.11** (required — other versions will not work)
  - Download: [Python 3.11.9](https://www.python.org/downloads/release/python-3119/)
  - Check **"Add Python to PATH"** during installation!
- [cflib](https://github.com/bitcraze/crazyflie-lib-python) (installed automatically)
- [matplotlib](https://matplotlib.org/) (installed automatically)


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
