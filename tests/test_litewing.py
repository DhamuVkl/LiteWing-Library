"""
LiteWing Library — Unit Tests
================================
Basic tests to verify the library loads and initializes correctly.
Run with: python -m pytest tests/ -v
"""

import sys
import os

# Ensure the package is importable without pip install
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


class TestImports:
    """Verify all public modules import cleanly."""

    def test_import_litewing(self):
        from litewing import LiteWing
        assert LiteWing is not None

    def test_import_sensor_data(self):
        from litewing import SensorData
        assert SensorData is not None

    def test_import_pid_config(self):
        from litewing import PIDConfig
        assert PIDConfig is not None

    def test_version_exists(self):
        import litewing
        assert hasattr(litewing, "__version__")
        assert litewing.__version__ == "0.1.0"


class TestLiteWingInit:
    """Verify LiteWing initializes with correct defaults."""

    def setup_method(self):
        from litewing import LiteWing
        self.drone = LiteWing("192.168.43.42")

    def test_default_ip(self):
        assert self.drone._ip == "192.168.43.42"

    def test_default_target_height(self):
        assert self.drone.target_height == 0.3

    def test_default_hover_duration(self):
        assert self.drone.hover_duration == 20.0

    def test_default_hold_mode(self):
        assert self.drone.hold_mode == "current"

    def test_default_sensitivity(self):
        assert self.drone.sensitivity == 0.2

    def test_default_debug_mode(self):
        assert self.drone.debug_mode is False

    def test_default_flight_phase(self):
        assert self.drone.flight_phase == "IDLE"

    def test_not_connected(self):
        assert self.drone.is_connected is False

    def test_not_flying(self):
        assert self.drone.is_flying is False

    def test_default_max_correction(self):
        assert self.drone.max_correction == 0.7

    def test_default_optical_flow_scale(self):
        assert self.drone.optical_flow_scale == 4.4

    def test_default_thrust_base(self):
        assert self.drone.thrust_base == 24000


class TestPIDConfig:
    """Verify PIDConfig works correctly."""

    def test_create_pid(self):
        from litewing import PIDConfig
        pid = PIDConfig(kp=1.0, ki=0.5, kd=0.1)
        assert pid.kp == 1.0
        assert pid.ki == 0.5
        assert pid.kd == 0.1

    def test_modify_pid(self):
        from litewing import PIDConfig
        pid = PIDConfig()
        pid.kp = 2.0
        assert pid.kp == 2.0

    def test_pid_repr(self):
        from litewing import PIDConfig
        pid = PIDConfig(kp=1.0, ki=0.03, kd=0.0)
        assert "PIDConfig" in repr(pid)
        assert "1.0" in repr(pid)

    def test_drone_position_pid(self):
        from litewing import LiteWing
        drone = LiteWing()
        assert drone.position_pid.kp == 1.0
        assert drone.position_pid.ki == 0.03
        assert drone.position_pid.kd == 0.0

    def test_drone_velocity_pid(self):
        from litewing import LiteWing
        drone = LiteWing()
        assert drone.velocity_pid.kp == 0.7
        assert drone.velocity_pid.ki == 0.01


class TestSensorData:
    """Verify SensorData snapshot works."""

    def test_sensor_snapshot(self):
        from litewing import LiteWing
        drone = LiteWing()
        sensors = drone.read_sensors()
        assert sensors.height == 0.0
        assert sensors.battery == 0.0
        assert sensors.vx == 0.0
        assert sensors.vy == 0.0
        assert sensors.x == 0.0
        assert sensors.y == 0.0

    def test_battery_property(self):
        from litewing import LiteWing
        drone = LiteWing()
        assert drone.battery == 0.0

    def test_position_property(self):
        from litewing import LiteWing
        drone = LiteWing()
        assert drone.position == (0.0, 0.0)

    def test_velocity_property(self):
        from litewing import LiteWing
        drone = LiteWing()
        assert drone.velocity == (0.0, 0.0)


class TestContextManager:
    """Verify context manager works."""

    def test_with_statement(self):
        from litewing import LiteWing
        with LiteWing() as drone:
            assert drone is not None
            assert drone.flight_phase == "IDLE"

    def test_context_manager_returns_drone(self):
        from litewing import LiteWing
        with LiteWing("192.168.43.42") as drone:
            assert drone._ip == "192.168.43.42"


class TestConfiguration:
    """Verify configuration properties can be set."""

    def setup_method(self):
        from litewing import LiteWing
        self.drone = LiteWing()

    def test_set_target_height(self):
        self.drone.target_height = 0.5
        assert self.drone.target_height == 0.5

    def test_set_trim(self):
        self.drone.trim_forward = 0.02
        self.drone.trim_right = -0.01
        assert self.drone.trim_forward == 0.02
        assert self.drone.trim_right == -0.01

    def test_set_hold_mode(self):
        self.drone.hold_mode = "origin"
        assert self.drone.hold_mode == "origin"

    def test_set_sensitivity(self):
        self.drone.sensitivity = 0.5
        assert self.drone.sensitivity == 0.5

    def test_set_firmware_params(self):
        self.drone.thrust_base = 30000
        self.drone.z_position_kp = 2.0
        self.drone.z_velocity_kp = 20.0
        assert self.drone.thrust_base == 30000
        assert self.drone.z_position_kp == 2.0
        assert self.drone.z_velocity_kp == 20.0


class TestInternalModules:
    """Verify internal modules work correctly."""

    def test_pid_state_update(self):
        from litewing.pid import _PIDState, PIDConfig
        state = _PIDState()
        config = PIDConfig(kp=1.0, ki=0.0, kd=0.0)
        cx, cy = state.update(1.0, 0.5, 0.02, config)
        assert cx == 1.0   # kp * error_x
        assert cy == 0.5   # kp * error_y

    def test_pid_state_reset(self):
        from litewing.pid import _PIDState, PIDConfig
        state = _PIDState()
        config = PIDConfig(kp=1.0, ki=1.0, kd=0.0)
        state.update(1.0, 1.0, 0.02, config)
        state.reset()
        assert state.integral_x == 0.0
        assert state.integral_y == 0.0

    def test_position_engine_reset(self):
        from litewing._position import PositionEngine
        engine = PositionEngine()
        assert engine.x == 0.0
        assert engine.y == 0.0
        engine.reset()
        assert engine.x == 0.0

    def test_position_hold_controller(self):
        from litewing.position_hold import PositionHoldController
        from litewing.pid import PIDConfig
        pos_pid = PIDConfig(kp=1.0, ki=0.0, kd=0.0)
        vel_pid = PIDConfig(kp=0.5, ki=0.0, kd=0.0)
        controller = PositionHoldController(pos_pid, vel_pid)
        assert controller.enabled is True
        controller.set_target(1.0, 2.0)
        assert controller.target_x == 1.0
        assert controller.target_y == 2.0
