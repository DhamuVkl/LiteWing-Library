"""
LiteWing LED Control
=====================
Control the NeoPixel LEDs on the drone for visual feedback.

Use LEDs to signal different states:
    drone.set_led_color(0, 255, 0)   # Green = ready
    drone.set_led_color(255, 0, 0)   # Red = error
    drone.blink_leds(500, 500)       # Blink every 500ms
"""

import time
from .config import defaults
from ._crtp import send_crtp_with_fallback, try_send_with_retries


class LEDController:
    """
    Controls the NeoPixel LEDs on the drone.

    This is used internally by the LiteWing class but can also be
    accessed directly for advanced LED patterns.
    """

    def __init__(self):
        self._cf = None
        self._blinking = False
        self._last_color = (255, 255, 255)

    def attach(self, cf):
        """Attach to a Crazyflie instance."""
        self._cf = cf

    def detach(self):
        """Detach from Crazyflie."""
        self._cf = None

    @property
    def is_attached(self):
        return self._cf is not None

    def set_color(self, r, g, b, logger=None):
        """
        Set all LEDs to the specified RGB color.

        Args:
            r: Red value (0–255).
            g: Green value (0–255).
            b: Blue value (0–255).
        """
        if not self.is_attached:
            if logger:
                logger("LED: Not connected to drone")
            return False

        self._last_color = (r, g, b)

        # Stop any active blinking first
        if self._blinking:
            self.stop_blink(logger=logger)

        cfg = defaults
        success = try_send_with_retries(
            self._cf, _np_set_all, r, g, b, logger=logger
        )
        if success:
            time.sleep(cfg.NP_PACKET_DELAY)
            try_send_with_retries(self._cf, _np_show, logger=logger)
        return success

    def blink(self, on_ms=500, off_ms=500, logger=None):
        """
        Start blinking the LEDs with the current color.

        Args:
            on_ms: Time LEDs stay ON each cycle (milliseconds).
            off_ms: Time LEDs stay OFF each cycle (milliseconds).
        """
        if not self.is_attached:
            return False

        r, g, b = self._last_color
        success = try_send_with_retries(
            self._cf, _np_set_all, r, g, b, logger=logger
        )
        if success:
            time.sleep(defaults.NP_PACKET_DELAY)
            try_send_with_retries(self._cf, _np_show, logger=logger)
            time.sleep(defaults.NP_PACKET_DELAY)
            success = try_send_with_retries(
                self._cf, _np_start_blink, on_ms, off_ms, logger=logger
            )
            if success:
                self._blinking = True
        return success

    def stop_blink(self, logger=None):
        """Stop blinking and restore the last set color."""
        if not self.is_attached:
            return False

        success = try_send_with_retries(self._cf, _np_stop_blink, logger=logger)
        if success:
            self._blinking = False
            time.sleep(defaults.NP_PACKET_DELAY)
            # Restore last color
            r, g, b = self._last_color
            try_send_with_retries(self._cf, _np_set_all, r, g, b, logger=logger)
            time.sleep(defaults.NP_PACKET_DELAY)
            try_send_with_retries(self._cf, _np_show, logger=logger)
        return success

    def clear(self, logger=None):
        """Turn off all LEDs."""
        if not self.is_attached:
            return False

        if self._blinking:
            self.stop_blink(logger=logger)
            time.sleep(defaults.NP_PACKET_DELAY)

        success = try_send_with_retries(self._cf, _np_clear, logger=logger)
        return success


# === Low-level NeoPixel functions ===

def _np_set_all(cf, r, g, b):
    """Set all NeoPixels to same color using broadcast index."""
    send_crtp_with_fallback(
        cf,
        defaults.CRTP_PORT_NEOPIXEL,
        defaults.NEOPIXEL_CHANNEL_SET_PIXEL,
        bytes([0xFF, r & 0xFF, g & 0xFF, b & 0xFF]),
    )


def _np_show(cf):
    """Push buffered pixel data to the LEDs."""
    send_crtp_with_fallback(
        cf, defaults.CRTP_PORT_NEOPIXEL, defaults.NEOPIXEL_CHANNEL_SHOW, b""
    )


def _np_clear(cf):
    """Clear all pixels."""
    send_crtp_with_fallback(
        cf, defaults.CRTP_PORT_NEOPIXEL, defaults.NEOPIXEL_CHANNEL_CLEAR, b""
    )


def _np_start_blink(cf, on_ms=500, off_ms=500):
    """Start hardware blinking."""
    data = bytes(
        [1, (on_ms >> 8) & 0xFF, on_ms & 0xFF, (off_ms >> 8) & 0xFF, off_ms & 0xFF]
    )
    send_crtp_with_fallback(
        cf, defaults.CRTP_PORT_NEOPIXEL, defaults.NEOPIXEL_CHANNEL_BLINK, data
    )


def _np_stop_blink(cf):
    """Stop hardware blinking."""
    send_crtp_with_fallback(
        cf,
        defaults.CRTP_PORT_NEOPIXEL,
        defaults.NEOPIXEL_CHANNEL_BLINK,
        bytes([0, 0, 0, 0, 0]),
    )


def _np_set_pixel(cf, index, r, g, b):
    """Set a single pixel by index."""
    send_crtp_with_fallback(
        cf,
        defaults.CRTP_PORT_NEOPIXEL,
        defaults.NEOPIXEL_CHANNEL_SET_PIXEL,
        bytes([index, r, g, b]),
    )
