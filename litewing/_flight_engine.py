"""
LiteWing Internal — Flight Engine
====================================
The takeoff → stabilize → hover → maneuver → land state machine.
This runs in a background thread and handles the control loop.
"""

import time
from .config import defaults
from ._safety import check_link_safety
from ._connection import (
    setup_sensor_logging, apply_firmware_parameters, stop_logging_configs
)


def run_flight_sequence(drone, maneuver_fn=None):
    """
    Execute a complete flight: connect → takeoff → hover/maneuver → land.

    Args:
        drone: LiteWing instance with all state.
        maneuver_fn: Optional callable(drone, cf) to execute during hover phase.
                     If None, hovers for drone._hover_duration seconds.
    """
    import cflib.crtp
    from cflib.crazyflie import Crazyflie
    from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

    cflib.crtp.init_drivers()
    cf = Crazyflie(rw_cache="./cache")
    log_motion = None
    log_battery = None

    # Reset battery for new connection
    drone._sensors.battery_voltage = 0.0
    drone._sensors.battery_data_ready = False

    uri = f"udp://{drone._ip}"

    try:
        drone._flight_phase = "CONNECTING"
        if drone._logger_fn:
            drone._logger_fn(f"Connecting to {uri}...")

        with SyncCrazyflie(uri, cf=cf) as scf:
            drone._scf = scf
            drone._flight_active = True

            # Apply firmware parameters if enabled
            if drone.enable_firmware_params:
                apply_firmware_parameters(
                    cf, drone.thrust_base, drone.z_position_kp, drone.z_velocity_kp,
                    logger=drone._logger_fn
                )

            # Attach LEDs to live connection
            drone._leds.attach(cf)

            # Setup sensor logging
            drone._flight_phase = "SETUP"
            log_motion, log_battery = setup_sensor_logging(
                cf,
                motion_callback=drone._motion_callback,
                battery_callback=drone._battery_callback,
                sensor_period_ms=drone.sensor_update_rate,
                logger=drone._logger_fn,
            )
            has_position_hold = log_motion is not None
            if has_position_hold:
                time.sleep(1.0)

            # Reset position tracking
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
            else:
                if drone._logger_fn:
                    drone._logger_fn("DEBUG MODE: Skipping flight initialization")

            # === TAKEOFF ===
            drone._flight_phase = "TAKEOFF"
            if drone._logger_fn:
                drone._logger_fn(f"Taking off to {drone.target_height}m...")

            if drone._flight_logger.is_logging or drone.enable_csv_logging:
                if not drone._flight_logger.is_logging:
                    drone._flight_logger.start(logger=drone._logger_fn)

            takeoff_start = time.time()
            takeoff_height_start = drone._sensors.height

            while (time.time() - takeoff_start < drone.takeoff_time and
                   drone._flight_active):
                if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                        drone._sensors.last_sensor_heartbeat,
                                        drone.debug_mode, drone._logger_fn):
                    drone._flight_active = False
                    break

                if not drone.debug_mode:
                    # Position hold during takeoff if height is sufficient
                    if (has_position_hold and drone._sensors.sensor_data_ready and
                            drone._sensors.height > 0.04):
                        mvx, mvy = drone._position_hold.calculate_corrections(
                            drone._position_engine.x, drone._position_engine.y,
                            drone._position_engine.vx, drone._position_engine.vy,
                            drone._sensors.height, True
                        )
                    else:
                        mvx, mvy = 0.0, 0.0

                    total_vx = drone.trim_forward + mvy
                    total_vy = drone.trim_right + mvx

                    # Takeoff ramp
                    if drone.enable_takeoff_ramp:
                        elapsed = time.time() - takeoff_start
                        progress = min(1.0, elapsed / drone.takeoff_time)
                        cmd_height = takeoff_height_start + (
                            drone.target_height - takeoff_height_start
                        ) * progress
                    else:
                        cmd_height = drone.target_height

                    cf.commander.send_hover_setpoint(total_vx, total_vy, 0, cmd_height)

                _log_csv_row(drone)
                time.sleep(drone.control_update_rate)

            # Post-takeoff height check
            if (drone.enable_height_sensor_safety and not drone.debug_mode):
                height_change = drone._sensors.height - takeoff_height_start
                if height_change < drone._height_sensor_min_change:
                    cf.commander.send_setpoint(0, 0, 0, 0)
                    raise Exception(
                        f"EMERGENCY: Height sensor failure! "
                        f"Height stuck at {drone._sensors.height:.3f}m"
                    )

            # === STABILIZE ===
            drone._flight_phase = "STABILIZING"
            if drone._logger_fn:
                drone._logger_fn("Stabilizing...")
            stab_start = time.time()

            while (time.time() - stab_start < 3.0 and drone._flight_active):
                if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                        drone._sensors.last_sensor_heartbeat,
                                        drone.debug_mode, drone._logger_fn):
                    drone._flight_active = False
                    break

                if has_position_hold and drone._sensors.sensor_data_ready:
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
                _log_csv_row(drone)
                time.sleep(drone.control_update_rate)

            # === HOVER / MANEUVER ===
            drone._flight_phase = "HOVERING"
            if drone._logger_fn:
                drone._logger_fn("Position hold active!")

            if maneuver_fn is not None:
                # Execute the provided maneuver function
                maneuver_fn(drone, cf, has_position_hold)
            else:
                # Default hover loop
                _hover_loop(drone, cf, has_position_hold, drone._hover_duration)

            # === LAND ===
            drone._flight_phase = "LANDING"
            if drone._logger_fn:
                drone._logger_fn("Landing...")
            land_start = time.time()

            while (time.time() - land_start < drone.landing_time and
                   drone._flight_active):
                if not drone.debug_mode:
                    cf.commander.send_hover_setpoint(
                        drone.trim_forward, drone.trim_right, 0, 0
                    )
                _log_csv_row(drone)
                time.sleep(0.01)

            # Stop motors
            if not drone.debug_mode:
                cf.commander.send_setpoint(0, 0, 0, 0)

            drone._flight_phase = "COMPLETE"
            if drone._logger_fn:
                drone._logger_fn("Flight complete!")

    except Exception as e:
        drone._flight_phase = "ERROR"
        if drone._logger_fn:
            drone._logger_fn(f"Flight error: {str(e)}")
        # Try to stop motors
        try:
            if not drone.debug_mode:
                cf.commander.send_setpoint(0, 0, 0, 0)
        except Exception:
            pass
    finally:
        drone._flight_logger.stop(logger=drone._logger_fn)
        stop_logging_configs(log_motion, log_battery)
        drone._leds.detach()
        drone._flight_active = False
        drone._scf = None


def _hover_loop(drone, cf, has_pos_hold, duration):
    """Run a simple timed hover with position hold."""
    hover_start = time.time()

    while (time.time() - hover_start < duration and drone._flight_active):
        if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                drone._sensors.last_sensor_heartbeat,
                                drone.debug_mode, drone._logger_fn):
            drone._flight_active = False
            break

        # Periodic position reset
        drone._position_engine.periodic_reset_check()

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
        _log_csv_row(drone)
        time.sleep(drone.control_update_rate)


def run_waypoint_maneuver(drone, cf, has_pos_hold, waypoints,
                          threshold=None, timeout=None, stabilize_time=None):
    """
    Fly through a list of (x, y) waypoints with position hold.

    Args:
        drone: LiteWing instance.
        cf: Crazyflie instance.
        has_pos_hold: Whether position hold is available.
        waypoints: List of (x, y) tuples.
        threshold: How close to each waypoint before advancing.
        timeout: Seconds before aborting a stuck waypoint.
        stabilize_time: Seconds to hover at each waypoint.
    """
    if threshold is None:
        threshold = drone.waypoint_threshold
    if timeout is None:
        timeout = drone.waypoint_timeout
    if stabilize_time is None:
        stabilize_time = drone.waypoint_stabilization_time

    for i, (wx, wy) in enumerate(waypoints):
        if not drone._flight_active:
            break

        drone._position_hold.set_target(wx, wy)
        wp_start = time.time()

        if drone._logger_fn:
            drone._logger_fn(
                f"Flying to waypoint {i+1}/{len(waypoints)}: ({wx:.2f}, {wy:.2f})"
            )

        # Fly toward waypoint
        while drone._flight_active:
            if not check_link_safety(cf, drone._sensors.sensor_data_ready,
                                    drone._sensors.last_sensor_heartbeat,
                                    drone.debug_mode, drone._logger_fn):
                drone._flight_active = False
                break

            # Timeout check
            if time.time() - wp_start > timeout:
                if drone._logger_fn:
                    drone._logger_fn(f"Waypoint {i+1} timeout!")
                break

            # Distance check
            dx = drone._position_engine.x - wx
            dy = drone._position_engine.y - wy
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < threshold:
                if drone._logger_fn:
                    drone._logger_fn(f"Reached waypoint {i+1}!")
                break

            # Position hold corrections
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
            _log_csv_row(drone)
            time.sleep(drone.control_update_rate)

        # Stabilize at waypoint
        if drone._flight_active and stabilize_time > 0:
            stab_start = time.time()
            while (time.time() - stab_start < stabilize_time and
                   drone._flight_active):
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
                _log_csv_row(drone)
                time.sleep(drone.control_update_rate)


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
