"""
LiteWing Manual Control
========================
Keyboard/joystick-based real-time drone control with position hold.

There are two hold modes:
    "current"  — Hold at Current Position (Flying Mode)
                 When keys are released, the drone holds at whatever
                 position it reached. Like driving a car.

    "origin"   — Hold at Origin (Spring Mode)
                 When keys are released, the drone snaps back to launch.
                 Like a rubber band attached to the starting point.
"""

import time
import math
from .config import defaults
from ._safety import check_link_safety
from ._connection import (
    setup_sensor_logging, apply_firmware_parameters, stop_logging_configs
)


def run_manual_control(drone):
    """
    Execute manual (joystick) control flight.

    Connects to the drone, takes off, then enters a control loop where
    the drone responds to key inputs while maintaining position hold.
    """
    import cflib.crtp
    from cflib.crazyflie import Crazyflie
    from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

    cflib.crtp.init_drivers()
    cf = Crazyflie(rw_cache="./cache")
    log_motion = None
    log_battery = None

    drone._sensors.battery_voltage = 0.0
    drone._sensors.battery_data_ready = False

    uri = f"udp://{drone._ip}:{drone._port}"

    try:
        drone._flight_phase = "CONNECTING"
        if drone._logger_fn:
            drone._logger_fn(f"Manual control: connecting to {uri}...")

        with SyncCrazyflie(uri, cf=cf) as scf:
            drone._scf = scf
            drone._flight_active = True

            if drone.enable_firmware_params:
                apply_firmware_parameters(
                    cf, drone.thrust_base, drone.z_position_kp, drone.z_velocity_kp,
                    logger=drone._logger_fn
                )

            drone._leds.attach(cf)

            # Setup logging
            log_motion, log_battery, log_imu = setup_sensor_logging(
                cf,
                motion_callback=drone._motion_callback,
                battery_callback=drone._battery_callback,
                imu_callback=getattr(drone, '_imu_callback', None),
                sensor_period_ms=drone.sensor_update_rate,
                logger=drone._logger_fn,
            )
            has_pos_hold = log_motion is not None
            if has_pos_hold:
                time.sleep(1.0)

            # Sensor health check
            if drone.enable_sensor_check:
                health = drone._check_sensor_health(cf)
                drone._sensor_health = health
                missing = []
                if not health.get('tof', False):
                    missing.append('ToF sensor (VL53L1x)')
                if not health.get('flow', False):
                    missing.append('Optical flow (PMW3901)')
                if missing:
                    msg = (
                        "Cannot fly -- sensors not detected:\n"
                        + "\n".join(f"  - {s}" for s in missing)
                        + "\n\nCheck wiring and power cycle the drone."
                        + "\nTo skip this check: drone.enable_sensor_check = False"
                    )
                    raise RuntimeError(msg)

            drone._position_engine.reset()
            drone._position_hold.reset()

            # Safety check
            if (not drone._position_engine.integration_enabled or
                    drone._position_engine.x != 0.0 or
                    drone._position_engine.y != 0.0):
                raise Exception("SAFETY: Position integration reset failed!")

            # Initialize commander
            if not drone.debug_mode:
                cf.commander.send_setpoint(0, 0, 0, 0)
                time.sleep(0.1)
                cf.param.set_value("commander.enHighLevel", "1")
                time.sleep(0.5)

            # === TAKEOFF ===
            drone._flight_phase = "MANUAL_TAKEOFF"
            if drone._logger_fn:
                drone._logger_fn(f"Manual control: taking off to {drone.target_height}m...")

            if drone.enable_csv_logging and not drone._flight_logger.is_logging:
                drone._flight_logger.start(logger=drone._logger_fn)

            takeoff_start = time.time()
            while (time.time() - takeoff_start < drone.takeoff_time and
                   drone._manual_active):
                if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                        drone._sensors.last_sensor_heartbeat,
                                        drone.debug_mode, drone._logger_fn):
                    drone._manual_active = False
                    break
                if not drone.debug_mode:
                    if (has_pos_hold and drone._sensors.sensor_data_ready and
                            drone._sensors.height > 0.05):
                        mvx, mvy = drone._position_hold.calculate_corrections(
                            drone._position_engine.x, drone._position_engine.y,
                            drone._position_engine.vx, drone._position_engine.vy,
                            drone._sensors.height, True
                        )
                    else:
                        mvx, mvy = 0.0, 0.0
                    total_vx = drone.trim_forward + mvy
                    total_vy = drone.trim_right + mvx
                    cf.commander.send_hover_setpoint(
                        total_vx, total_vy, 0, drone.target_height
                    )
                _log_csv_row(drone)
                time.sleep(0.01)

            # === STABILIZE ===
            drone._flight_phase = "MANUAL_STABILIZING"
            stab_start = time.time()
            while (time.time() - stab_start < 3.0 and drone._manual_active):
                if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                        drone._sensors.last_sensor_heartbeat,
                                        drone.debug_mode, drone._logger_fn):
                    drone._manual_active = False
                    break
                if has_pos_hold and drone._sensors.sensor_data_ready:
                    mvx, mvy = drone._position_hold.calculate_corrections(
                        drone._position_engine.x, drone._position_engine.y,
                        drone._position_engine.vx, drone._position_engine.vy,
                        drone._sensors.height, True
                    )
                else:
                    mvx, mvy = 0.0, 0.0
                total_vx = drone.trim_forward + mvy
                total_vy = drone.trim_right + mvx
                if not drone.debug_mode:
                    cf.commander.send_hover_setpoint(
                        total_vx, total_vy, 0, drone.target_height
                    )
                time.sleep(drone.control_update_rate)

            # === MANUAL CONTROL LOOP ===
            drone._flight_phase = "MANUAL_CONTROL"
            if drone._logger_fn:
                drone._logger_fn("Manual control active! Use WASD to move.")

            # Start keyboard listener thread (Windows: msvcrt)
            import threading as _threading
            _key_timeout = 0.15  # seconds before key auto-releases

            def _keyboard_listener():
                """Poll for keyboard input and update _manual_keys."""
                try:
                    import msvcrt
                except ImportError:
                    if drone._logger_fn:
                        drone._logger_fn(
                            "WARNING: msvcrt not available, "
                            "keyboard control disabled"
                        )
                    return

                key_timers = {}
                while drone._manual_active:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        ch_str = ch.decode("utf-8", errors="ignore").lower()
                        if ch_str in ("q", " ") or ch == b'\x03':
                            # Quit / land / Ctrl+C
                            if ch == b'\x03':
                                print("\n Ctrl+C detected — EMERGENCY STOP!")
                                drone.emergency_stop()
                            drone._manual_active = False
                            break
                        if ch_str in drone._manual_keys:
                            drone._manual_keys[ch_str] = True
                            key_timers[ch_str] = time.time()

                    # Auto-release keys after timeout
                    now = time.time()
                    for k in list(key_timers):
                        if now - key_timers[k] > _key_timeout:
                            drone._manual_keys[k] = False
                            del key_timers[k]

                    time.sleep(0.02)

            kb_thread = _threading.Thread(
                target=_keyboard_listener, daemon=True
            )
            kb_thread.start()

            last_loop_time = time.time()

            while drone._manual_active:
                if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                        drone._sensors.last_sensor_heartbeat,
                                        drone.debug_mode, drone._logger_fn):
                    drone._manual_active = False
                    break

                current_time = time.time()
                dt = current_time - last_loop_time
                last_loop_time = current_time
                if dt > 0.1:
                    dt = 0.1

                # Get joystick input from key states
                joystick_vx = 0.0
                joystick_vy = 0.0

                if drone._manual_keys.get("w", False):
                    joystick_vy += drone.sensitivity
                if drone._manual_keys.get("s", False):
                    joystick_vy -= drone.sensitivity
                if drone._manual_keys.get("a", False):
                    joystick_vx += drone.sensitivity
                if drone._manual_keys.get("d", False):
                    joystick_vx -= drone.sensitivity

                # Update target position based on hold mode
                if has_pos_hold and drone._sensors.sensor_data_ready:
                    if drone.hold_mode == "current":
                        # Target moves with joystick input
                        drone._position_hold.target_x += joystick_vx * dt
                        drone._position_hold.target_y += joystick_vy * dt
                        # Clamp target
                        dx = drone._position_hold.target_x - drone._position_engine.x
                        dy = drone._position_hold.target_y - drone._position_engine.y
                        if abs(dx) > drone.max_position_error:
                            drone._position_hold.target_x = (
                                drone._position_engine.x +
                                math.copysign(drone.max_position_error, dx)
                            )
                        if abs(dy) > drone.max_position_error:
                            drone._position_hold.target_y = (
                                drone._position_engine.y +
                                math.copysign(drone.max_position_error, dy)
                            )
                    else:
                        # Origin mode — target is always (0, 0)
                        drone._position_hold.target_x = 0.0
                        drone._position_hold.target_y = 0.0

                    # Calculate PID corrections
                    mvx, mvy = drone._position_hold.calculate_corrections(
                        drone._position_engine.x, drone._position_engine.y,
                        drone._position_engine.vx, drone._position_engine.vy,
                        drone._sensors.height, True
                    )
                else:
                    mvx, mvy = 0.0, 0.0

                # Combine feedforward (joystick) + feedback (PID)
                total_vx = drone.trim_forward + mvy + joystick_vy
                total_vy = drone.trim_right + mvx + joystick_vx

                if not drone.debug_mode:
                    cf.commander.send_hover_setpoint(
                        total_vx, total_vy, 0, drone.target_height
                    )

                _log_csv_row(drone)
                time.sleep(drone.control_update_rate)

            # === LANDING ===
            drone._flight_phase = "MANUAL_LANDING"
            if drone._logger_fn:
                drone._logger_fn("Manual control: landing...")
            land_start = time.time()
            current_land_height = drone.target_height
            dt = 0.02  # 50Hz control loop

            # Gradual descent: lower target height smoothly with position hold
            while (current_land_height > 0.02 and
                   time.time() - land_start < drone.landing_time and
                   drone._flight_active):
                current_land_height -= drone.descent_rate * dt
                current_land_height = max(current_land_height, 0.0)

                # Keep position hold active during descent
                if (has_pos_hold and drone._sensors.sensor_data_ready and
                        current_land_height > 0.03):
                    mvx, mvy = drone._position_hold.calculate_corrections(
                        drone._position_engine.x, drone._position_engine.y,
                        drone._position_engine.vx, drone._position_engine.vy,
                        drone._sensors.height, True
                    )
                else:
                    mvx, mvy = 0.0, 0.0

                total_vx = drone.trim_forward + mvy
                total_vy = drone.trim_right + mvx

                if not drone.debug_mode:
                    cf.commander.send_hover_setpoint(
                        total_vx, total_vy, 0, current_land_height
                    )
                _log_csv_row(drone)
                time.sleep(dt)

            # Brief settle at ground level before killing motors
            settle_start = time.time()
            while time.time() - settle_start < 0.3 and drone._flight_active:
                if not drone.debug_mode:
                    cf.commander.send_hover_setpoint(
                        drone.trim_forward, drone.trim_right, 0, 0
                    )
                time.sleep(0.02)

            if not drone.debug_mode:
                cf.commander.send_setpoint(0, 0, 0, 0)

            drone._flight_phase = "MANUAL_COMPLETE"
            if drone._logger_fn:
                drone._logger_fn("Manual control complete!")

    except Exception as e:
        drone._flight_phase = "MANUAL_ERROR"
        if drone._logger_fn:
            drone._logger_fn(f"Manual control error: {str(e)}")
        try:
            if not drone.debug_mode:
                cf.commander.send_setpoint(0, 0, 0, 0)
        except Exception:
            pass
    finally:
        drone._flight_logger.stop(logger=drone._logger_fn)
        stop_logging_configs(log_motion, log_battery, log_imu)
        drone._leds.detach()
        drone._flight_active = False
        drone._manual_active = False
        drone._scf = None


def _log_csv_row(drone):
    """Log current state to CSV if logging is active."""
    drone._flight_logger.log_row(
        drone._position_engine.x,
        drone._position_engine.y,
        drone._sensors.height,
        drone._sensors.range_height,
        drone._position_engine.vx,
        drone._position_engine.vy,
        drone._position_hold.correction_vx,
        drone._position_hold.correction_vy,
    )
