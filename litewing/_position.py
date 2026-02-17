"""
LiteWing Internal — Dead Reckoning Position Engine
====================================================
Converts optical flow sensor data into velocity and position estimates.
This is the math behind drone.position and drone.velocity.
"""

import time
from .config import defaults


class PositionEngine:
    """
    Tracks the drone's estimated X/Y position using dead reckoning.

    Dead reckoning integrates velocity over time to estimate position.
    It drifts over time (that's why periodic resets exist), but it's
    good enough for short-distance position hold and maneuvers.
    """

    def __init__(self):
        # Current estimated position (meters from origin)
        self.x = 0.0
        self.y = 0.0
        # Current smoothed velocity (m/s)
        self.vx = 0.0
        self.vy = 0.0
        # Raw motion deltas from sensor
        self.delta_x = 0
        self.delta_y = 0
        # Velocity smoothing history (2-point filter)
        self._vx_history = [0.0, 0.0]
        self._vy_history = [0.0, 0.0]
        # Timing
        self._last_integration_time = time.time()
        self._last_reset_time = time.time()
        # Integration enabled flag
        self.integration_enabled = False

    def reset(self):
        """Reset position estimate to origin (0, 0)."""
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self._vx_history = [0.0, 0.0]
        self._vy_history = [0.0, 0.0]
        self._last_integration_time = time.time()
        self._last_reset_time = time.time()
        self.integration_enabled = True

    def calculate_velocity(self, delta_value, altitude, cfg=None):
        """
        Convert optical flow delta to linear velocity.

        Args:
            delta_value: Raw sensor delta (pixels of motion).
            altitude: Current height in meters.
            cfg: Config defaults override (optional).

        Returns:
            Velocity in m/s.
        """
        if cfg is None:
            cfg = defaults
        if altitude <= 0:
            return 0.0

        dt = cfg.SENSOR_PERIOD_MS / 1000.0

        if cfg.USE_HEIGHT_SCALING:
            velocity_constant = (5.4 * cfg.DEG_TO_RAD) / (30.0 * dt)
            return delta_value * altitude * velocity_constant
        else:
            return delta_value * cfg.OPTICAL_FLOW_SCALE * dt

    def _smooth_velocity(self, new_velocity, history, cfg=None):
        """Simple 2-point smoothing filter."""
        if cfg is None:
            cfg = defaults
        history[1] = history[0]
        history[0] = new_velocity
        alpha = cfg.VELOCITY_SMOOTHING_ALPHA
        smoothed = (history[0] * alpha) + (history[1] * (1 - alpha))
        if abs(smoothed) < cfg.VELOCITY_THRESHOLD:
            smoothed = 0.0
        return smoothed

    def _integrate(self, vx, vy, dt, cfg=None):
        """Dead reckoning: integrate velocity into position."""
        if cfg is None:
            cfg = defaults
        if dt <= 0 or dt > 0.1:
            return

        self.x += vx * dt
        self.y += vy * dt

        # Drift compensation when moving slowly
        velocity_magnitude = (vx * vx + vy * vy) ** 0.5
        if velocity_magnitude < cfg.VELOCITY_THRESHOLD * 2:
            self.x -= self.x * cfg.DRIFT_COMPENSATION_RATE * dt
            self.y -= self.y * cfg.DRIFT_COMPENSATION_RATE * dt

        # Clamp position error
        self.x = max(-cfg.MAX_POSITION_ERROR, min(cfg.MAX_POSITION_ERROR, self.x))
        self.y = max(-cfg.MAX_POSITION_ERROR, min(cfg.MAX_POSITION_ERROR, self.y))

    def periodic_reset_check(self, cfg=None):
        """Reset position if the periodic interval has elapsed."""
        if cfg is None:
            cfg = defaults
        current_time = time.time()
        if current_time - self._last_reset_time >= cfg.PERIODIC_RESET_INTERVAL:
            self.x = 0.0
            self.y = 0.0
            self._last_reset_time = current_time
            return True
        return False

    def update_from_sensor(self, delta_x, delta_y, altitude, cfg=None):
        """
        Process new sensor data — calculates velocity and integrates position.
        Called by the sensor callback.

        Args:
            delta_x: Raw optical flow delta X.
            delta_y: Raw optical flow delta Y.
            altitude: Current height in meters.
            cfg: Config defaults override.
        """
        if cfg is None:
            cfg = defaults

        self.delta_x = delta_x
        self.delta_y = delta_y

        # Calculate raw velocities
        raw_vx = self.calculate_velocity(delta_x, altitude, cfg)
        raw_vy = self.calculate_velocity(delta_y, altitude, cfg)

        # Apply smoothing
        self.vx = self._smooth_velocity(raw_vx, self._vx_history, cfg)
        self.vy = self._smooth_velocity(raw_vy, self._vy_history, cfg)

        # Integrate position
        current_time = time.time()
        dt = current_time - self._last_integration_time
        if 0.001 <= dt <= 0.1 and self.integration_enabled:
            self._integrate(self.vx, self.vy, dt, cfg)
        self._last_integration_time = current_time
