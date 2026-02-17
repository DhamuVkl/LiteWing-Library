"""
LiteWing Position Hold Controller
===================================
Uses PID control and optical flow to keep the drone at a target position.

The position hold system works like this:
    1. Optical flow sensor detects ground movement → velocity
    2. Velocity is integrated over time → estimated position
    3. PID controller compares estimated position to target → correction
    4. Correction is sent to the drone as velocity setpoints

The learner can tune:
    - PID gains (drone.position_pid, drone.velocity_pid)
    - Max correction limit (drone.max_correction)
    - Drift compensation rate
    - Optical flow scaling
"""

from .pid import _PIDState
from .config import defaults


class PositionHoldController:
    """
    Calculates velocity corrections to hold the drone at a target position.

    Uses cascaded PID control:
        Position PID → desired velocity correction
        Velocity PID → dampens the correction to prevent oscillation
    """

    def __init__(self, position_pid_config, velocity_pid_config):
        self.position_pid = position_pid_config
        self.velocity_pid = velocity_pid_config
        self._pos_state = _PIDState()
        self._vel_state = _PIDState()
        # Target position (where the drone should be)
        self.target_x = 0.0
        self.target_y = 0.0
        # Last computed corrections (for logging/display)
        self.correction_vx = 0.0
        self.correction_vy = 0.0
        # Enabled flag
        self.enabled = True

    def reset(self):
        """Reset PID state (call at start of flight)."""
        self._pos_state.reset()
        self._vel_state.reset()
        self.target_x = 0.0
        self.target_y = 0.0
        self.correction_vx = 0.0
        self.correction_vy = 0.0

    def set_target(self, x, y):
        """Set the target position for position hold."""
        self.target_x = x
        self.target_y = y

    def calculate_corrections(self, current_x, current_y, current_vx, current_vy,
                              current_height, sensor_ready, dt=None,
                              max_correction=None):
        """
        Calculate control corrections using cascaded PID.

        Args:
            current_x: Current estimated X position.
            current_y: Current estimated Y position.
            current_vx: Current X velocity.
            current_vy: Current Y velocity.
            current_height: Current height (corrections disabled if <= 0).
            sensor_ready: Whether sensor data is available.
            dt: Control loop time step.
            max_correction: Override for maximum correction limit.

        Returns:
            (correction_vx, correction_vy): Velocity corrections to apply.
        """
        if not self.enabled or not sensor_ready or current_height <= 0:
            self.correction_vx = 0.0
            self.correction_vy = 0.0
            return 0.0, 0.0

        if dt is None:
            dt = defaults.CONTROL_UPDATE_RATE
        if max_correction is None:
            max_correction = defaults.MAX_CORRECTION

        # Position error (negative = correct toward target)
        pos_error_x = -(current_x - self.target_x)
        pos_error_y = -(current_y - self.target_y)

        # Velocity error (negative = dampen current velocity)
        vel_error_x = -current_vx
        vel_error_y = -current_vy

        # Position PID
        pos_cx, pos_cy = self._pos_state.update(
            pos_error_x, pos_error_y, dt, self.position_pid, integral_limit=0.1
        )

        # Velocity PID
        vel_cx, vel_cy = self._vel_state.update(
            vel_error_x, vel_error_y, dt, self.velocity_pid, integral_limit=0.05
        )

        # Combine corrections
        total_vx = pos_cx + vel_cx
        total_vy = pos_cy + vel_cy

        # Approach damping — reduce corrections when close to target
        distance = ((current_x - self.target_x) ** 2 +
                     (current_y - self.target_y) ** 2) ** 0.5
        if distance < 0.1:
            vel_magnitude = (current_vx ** 2 + current_vy ** 2) ** 0.5
            if vel_magnitude > 0.05:
                total_vx *= 0.8
                total_vy *= 0.8

        # Clamp corrections
        total_vx = max(-max_correction, min(max_correction, total_vx))
        total_vy = max(-max_correction, min(max_correction, total_vy))

        self.correction_vx = total_vx
        self.correction_vy = total_vy
        return total_vx, total_vy
