"""Quick verification script for the litewing library."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from litewing import LiteWing, SensorData, PIDConfig
import litewing

print("1. Import OK")
print(f"2. version: {litewing.__version__}")

d = LiteWing("192.168.43.42")
print(f"3. target_height: {d.target_height}")
print(f"4. position_pid: {d.position_pid}")
print(f"5. velocity_pid: {d.velocity_pid}")
print(f"6. hold_mode: {d.hold_mode}")
print(f"7. sensitivity: {d.sensitivity}")
print(f"8. max_correction: {d.max_correction}")
print(f"9. optical_flow_scale: {d.optical_flow_scale}")
print(f"10. thrust_base: {d.thrust_base}")
print(f"11. flight_phase: {d.flight_phase}")
print(f"12. is_connected: {d.is_connected}")
print(f"13. is_flying: {d.is_flying}")

s = d.read_sensors()
print(f"14. sensors: height={s.height}, battery={s.battery}")
print(f"15. position: {d.position}")
print(f"16. velocity: {d.velocity}")

pid = PIDConfig(kp=2.0, ki=0.1, kd=0.05)
print(f"17. PIDConfig: {pid}")

# Context manager
with LiteWing() as drone:
    assert drone.flight_phase == "IDLE"
print("18. Context manager OK")

# Config modification
d.target_height = 0.5
assert d.target_height == 0.5
d.hold_mode = "origin"
assert d.hold_mode == "origin"
print("19. Config modification OK")

print("\nALL PASSED")
