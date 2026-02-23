# Level 0 — Raw Flight (No Sensors Required)

These scripts work with the **base drone only** — no ToF or optical flow module needed!

## How it works

Without sensors, the drone can't hold its height or position automatically. You control the **raw motor thrust** directly, like flying an RC drone.

## Scripts

| # | Script | What it does |
|---|--------|---|
| 01 | `01_basic_flight.py` | Spin motors → brief liftoff → land |
| 02 | `02_manual_control.py` | WASD + throttle keyboard control |

## Key Differences from Level 1-3

| Feature | Level 0 (raw) | Level 1-3 (with sensors) |
|---|---|---|
| Height control | **You** control thrust | Drone auto-holds height |
| Position hold | None — drone drifts | Optical flow holds position |
| Difficulty | Hard (RC-style) | Easy (automated) |
| `send_control()` | Yes — raw roll/pitch/thrust | Not used |
| `takeoff()` / `land()` | Not used | Yes — automated |

## Thrust Guide

```
  0      = motors off
 15000   = propellers spinning, no lift
 20000   = light lift (depends on battery + weight)
 25000   = moderate lift
 35000   = safety limit (drone.max_thrust)
```

## Safety Tips

- Fly over a **soft surface** (bed, foam mat, carpet)
- Start with **low thrust** and increase slowly
- Keep flights **short** (1-2 seconds)
- Press **Ctrl+C** or **SPACE** to emergency stop anytime
- Tie the drone down with string for first tests!
