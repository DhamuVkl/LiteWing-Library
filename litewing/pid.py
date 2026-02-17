"""
LiteWing PID Controller
========================
A PID (Proportional-Integral-Derivative) controller keeps the drone stable.

How it works:
    - P (Proportional): Pushes back proportional to the error.
      Big error → big correction. Small error → small correction.
    - I (Integral): Fixes small persistent errors over time.
      If the drone always drifts a tiny bit left, the integral term slowly
      builds up a correction.
    - D (Derivative): Dampens rapid changes to prevent overshooting.
      If the drone is flying back too fast, the derivative slows it down.

Usage:
    pid = PIDConfig(kp=1.0, ki=0.03, kd=0.0)
    pid.kp = 1.5   # Increase proportional gain

The LiteWing drone uses TWO PID controllers:
    drone.position_pid  → Corrects position error (where the drone IS vs. where
                          it SHOULD be)
    drone.velocity_pid  → Dampens velocity (prevents overshooting the target)
"""


class PIDConfig:
    """
    PID gain configuration.

    Attributes:
        kp (float): Proportional gain — how hard to correct errors.
        ki (float): Integral gain — how to fix persistent drift.
        kd (float): Derivative gain — how to dampen oscillation.
    """

    def __init__(self, kp=0.0, ki=0.0, kd=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def __repr__(self):
        return f"PIDConfig(kp={self.kp}, ki={self.ki}, kd={self.kd})"


class _PIDState:
    """
    Internal runtime state for a PID controller.
    Learners don't need to touch this — it tracks integrals and derivatives
    between control loop iterations.
    """

    def __init__(self):
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.last_error_x = 0.0
        self.last_error_y = 0.0

    def reset(self):
        """Reset accumulated state (call at start of flight)."""
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.last_error_x = 0.0
        self.last_error_y = 0.0

    def update(self, error_x, error_y, dt, config, integral_limit=0.1):
        """
        Compute PID output for X and Y axes.

        Args:
            error_x: Current error in X axis.
            error_y: Current error in Y axis.
            dt: Time step in seconds.
            config: PIDConfig with kp, ki, kd gains.
            integral_limit: Anti-windup clamp for the integral term.

        Returns:
            (correction_x, correction_y): PID outputs for each axis.
        """
        if dt <= 0:
            return 0.0, 0.0

        # Proportional
        p_x = error_x * config.kp
        p_y = error_y * config.kp

        # Integral with anti-windup
        self.integral_x += error_x * dt
        self.integral_y += error_y * dt
        self.integral_x = max(-integral_limit, min(integral_limit, self.integral_x))
        self.integral_y = max(-integral_limit, min(integral_limit, self.integral_y))
        i_x = self.integral_x * config.ki
        i_y = self.integral_y * config.ki

        # Derivative
        d_x = ((error_x - self.last_error_x) / dt) * config.kd
        d_y = ((error_y - self.last_error_y) / dt) * config.kd
        self.last_error_x = error_x
        self.last_error_y = error_y

        return p_x + i_x + d_x, p_y + i_y + d_y
