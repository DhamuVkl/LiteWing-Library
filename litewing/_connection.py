"""
LiteWing Internal — Connection Management
============================================
Handles cflib initialization, SyncCrazyflie connections, and log config setup.

Log groups (each limited to ~26 bytes per CRTP packet):
    - Motion: deltaX, deltaY, stateEstimate.z, range.zrange
    - Battery: pm.vbat
    - IMU: stabilizer.roll/pitch/yaw, gyro.x/y/z
"""

import time
from cflib.crazyflie.log import LogConfig


def setup_sensor_logging(cf, motion_callback, battery_callback,
                         imu_callback=None,
                         sensor_period_ms=10, logger=None):
    """
    Set up cflib log configurations for motion, battery, and IMU data.

    Args:
        cf: Crazyflie instance.
        motion_callback: Callback function for motion data.
        battery_callback: Callback function for battery data.
        imu_callback: Callback function for IMU data (attitude + gyro).
        sensor_period_ms: Motion/IMU sensor polling period.
        logger: Optional logging function.

    Returns:
        (log_motion, log_battery, log_imu): LogConfig instances.
    """
    log_motion = LogConfig(name="Motion", period_in_ms=sensor_period_ms)
    log_battery = LogConfig(name="Battery", period_in_ms=500)
    log_imu = LogConfig(name="IMU", period_in_ms=sensor_period_ms)
    log_thrust = LogConfig(name="Thrust", period_in_ms=sensor_period_ms)

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

        # IMU variables (attitude + gyroscope)
        imu_variables = [
            ("stabilizer.roll", "float"),
            ("stabilizer.pitch", "float"),
            ("stabilizer.yaw", "float"),
            ("gyro.x", "float"),
            ("gyro.y", "float"),
            ("gyro.z", "float"),
        ]
        
        # Thrust variables (isolated because of 26-byte CRTP packet limit)
        thrust_variables = [
            ("stabilizer.thrust", "uint32_t"),
        ]
        
        added_imu = []
        for var_name, var_type in imu_variables:
            group, name = var_name.split(".")
            if group in toc and name in toc[group]:
                try:
                    log_imu.add_variable(var_name, var_type)
                    added_imu.append(var_name)
                except Exception as e:
                    if logger:
                        logger(f"Failed to add IMU variable {var_name}: {e}")
            else:
                if logger:
                    logger(f"IMU variable not found: {var_name}")
                    
        added_thrust = []
        for var_name, var_type in thrust_variables:
            group, name = var_name.split(".")
            if group in toc and name in toc[group]:
                try:
                    log_thrust.add_variable(var_name, var_type)
                    added_thrust.append(var_name)
                except Exception as e:
                    if logger:
                        logger(f"Failed to add Thrust variable {var_name}: {e}")
            else:
                if logger:
                    logger(f"Thrust variable not found: {var_name}")

        # Attach callbacks
        log_motion.data_received_cb.add_callback(motion_callback)
        if added_battery:
            log_battery.data_received_cb.add_callback(battery_callback)
        if added_imu and imu_callback:
            log_imu.data_received_cb.add_callback(imu_callback)
        if added_thrust and imu_callback:
            log_thrust.data_received_cb.add_callback(imu_callback)

        # Add configs to Crazyflie
        cf.log.add_config(log_motion)
        if added_battery:
            cf.log.add_config(log_battery)
        if added_imu:
            cf.log.add_config(log_imu)
        if added_thrust:
            cf.log.add_config(log_thrust)

        time.sleep(0.5)

        # Validate
        if not log_motion.valid:
            if logger:
                logger("ERROR: Motion log configuration invalid!")
            return None, None, None, None

        if added_battery and not log_battery.valid:
            if logger:
                logger("WARNING: Battery log configuration invalid!")
            log_battery = None

        if added_imu and not log_imu.valid:
            if logger:
                logger("WARNING: IMU log configuration invalid!")
            log_imu = None
            
        if added_thrust and not log_thrust.valid:
            if logger:
                logger("WARNING: Thrust log configuration invalid!")
            log_thrust = None

        # Start logging
        log_motion.start()
        if log_battery:
            log_battery.start()
        if log_imu:
            log_imu.start()
        if log_thrust:
            log_thrust.start()

        time.sleep(0.5)

        if logger:
            logger(
                f"Logging started \u2014 Motion: {len(added_motion)} vars, "
                f"Battery: {len(added_battery)} vars, "
                f"IMU: {len(added_imu)} vars, "
                f"Thrust: {len(added_thrust)} vars"
            )

        return log_motion, log_battery, log_imu, log_thrust

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


def stop_logging_configs(log_motion, log_battery, log_imu=None, log_thrust=None, logger=None):
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
    if log_imu:
        try:
            log_imu.stop()
        except Exception:
            pass
    if log_thrust:
        try:
            log_thrust.stop()
        except Exception:
            pass
