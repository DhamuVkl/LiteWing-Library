"""
LiteWing Internal — Connection Management
============================================
Handles cflib initialization, SyncCrazyflie connections, and log config setup.
"""

import time
from cflib.crazyflie.log import LogConfig


def setup_sensor_logging(cf, motion_callback, battery_callback,
                         sensor_period_ms=10, logger=None):
    """
    Set up cflib log configurations for motion and battery sensor data.

    Args:
        cf: Crazyflie instance.
        motion_callback: Callback function for motion data.
        battery_callback: Callback function for battery data.
        sensor_period_ms: Motion sensor polling period.
        logger: Optional logging function.

    Returns:
        (log_motion, log_battery): LogConfig instances, or (None, None) on failure.
    """
    log_motion = LogConfig(name="Motion", period_in_ms=sensor_period_ms)
    log_battery = LogConfig(name="Battery", period_in_ms=500)

    try:
        toc = cf.log.toc.toc

        # Motion variables
        motion_variables = [
            ("motion.deltaX", "int16_t"),
            ("motion.deltaY", "int16_t"),
            ("stateEstimate.z", "float"),
            ("range.zrange", "uint16_t"),
        ]
        added_motion = []
        for var_name, var_type in motion_variables:
            group, name = var_name.split(".")
            if group in toc and name in toc[group]:
                try:
                    log_motion.add_variable(var_name, var_type)
                    added_motion.append(var_name)
                except Exception as e:
                    if logger:
                        logger(f"Failed to add motion variable {var_name}: {e}")
            else:
                if logger:
                    logger(f"Motion variable not found: {var_name}")

        if len(added_motion) < 2:
            if logger:
                logger("ERROR: Not enough motion variables found!")
            return None, None

        # Battery variables
        battery_variables = [("pm.vbat", "float")]
        added_battery = []
        for var_name, var_type in battery_variables:
            group, name = var_name.split(".")
            if group in toc and name in toc[group]:
                try:
                    log_battery.add_variable(var_name, var_type)
                    added_battery.append(var_name)
                except Exception as e:
                    if logger:
                        logger(f"Failed to add battery variable {var_name}: {e}")
            else:
                if logger:
                    logger(f"Battery variable not found: {var_name}")

        # Attach callbacks
        log_motion.data_received_cb.add_callback(motion_callback)
        if added_battery:
            log_battery.data_received_cb.add_callback(battery_callback)

        # Add configs to Crazyflie
        cf.log.add_config(log_motion)
        if added_battery:
            cf.log.add_config(log_battery)

        time.sleep(0.5)

        # Validate
        if not log_motion.valid:
            if logger:
                logger("ERROR: Motion log configuration invalid!")
            return None, None

        if added_battery and not log_battery.valid:
            if logger:
                logger("WARNING: Battery log configuration invalid!")
            log_battery = None

        # Start logging
        log_motion.start()
        if log_battery:
            log_battery.start()

        time.sleep(0.5)

        if logger:
            logger(
                f"Logging started — Motion: {len(added_motion)} vars, "
                f"Battery: {len(added_battery)} vars"
            )

        return log_motion, log_battery

    except Exception as e:
        if logger:
            logger(f"Logging setup failed: {str(e)}")
        raise


def apply_firmware_parameters(cf, thrust_base, z_pos_kp, z_vel_kp, logger=None):
    """
    Send custom vertical PID and thrust parameters to the drone's firmware.
    """
    try:
        if logger:
            logger("Applying custom firmware parameters (Z-Axis/Thrust)...")

        cf.param.set_value('posCtlPid.thrustBase', str(thrust_base))
        cf.param.set_value('posCtlPid.zKp', str(z_pos_kp))
        cf.param.set_value('velCtlPid.vzKp', str(z_vel_kp))

        time.sleep(0.2)

        actual_thrust = cf.param.get_value('posCtlPid.thrustBase')
        if logger:
            logger(
                f"Firmware configured: thrustBase={actual_thrust}, "
                f"zKp={z_pos_kp}, vzKp={z_vel_kp}"
            )
    except Exception as e:
        if logger:
            logger(f"WARNING: Failed to set firmware parameters: {str(e)}")


def stop_logging_configs(log_motion, log_battery, logger=None):
    """Safely stop all log configurations."""
    if log_motion:
        try:
            log_motion.stop()
        except Exception:
            pass
    if log_battery:
        try:
            log_battery.stop()
        except Exception:
            pass
