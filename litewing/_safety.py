"""
LiteWing Internal — Safety Checks
====================================
Link health, sensor freshness, and battery monitoring.
"""

import time
from .config import defaults


def check_link_safety(cf, sensor_data_ready, last_sensor_heartbeat,
                      debug_mode=None, logger=None):
    """
    Check if the Crazyflie is still connected and sensor data is fresh.
    Returns True if safe to continue, False if something is wrong.
    """
    if debug_mode is None:
        debug_mode = defaults.DEBUG_MODE

    # 1. Connection check
    if not cf.is_connected():
        if logger:
            logger("CRITICAL: Crazyflie disconnected!")
        return False

    # 2. Sensor heartbeat check (only if not in debug mode)
    if not debug_mode and sensor_data_ready:
        elapsed = time.time() - last_sensor_heartbeat
        if elapsed > defaults.DATA_TIMEOUT_THRESHOLD:
            if logger:
                logger(f"CRITICAL: Sensor data timeout! ({elapsed:.2f}s delay)")
            return False

    return True


def check_battery_safe(voltage, threshold=None):
    """
    Check if battery voltage is above the safety threshold.
    Returns True if safe, False if too low.
    """
    if threshold is None:
        threshold = defaults.LOW_BATTERY_THRESHOLD
    if voltage > 0 and voltage < threshold:
        return False
    return True
