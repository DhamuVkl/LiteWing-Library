"""
LiteWing Internal — CRTP Packet Helpers
=========================================
Low-level helpers that handle CRTP packet construction and transmission.
Learners should NOT need to touch anything in this file.
"""

import time
from .config import defaults


class _PacketObj:
    """Minimal CRTP packet representation."""

    def __init__(self, header, data: bytes):
        self.header = header
        self.data = data
        try:
            self.datat = tuple(data)
        except Exception:
            self.datat = tuple()

    def is_data_size_valid(self):
        return len(self.data) <= 30

    @property
    def size(self):
        return len(self.data)

    def raw(self):
        return bytes([self.header]) + self.data


def send_crtp_with_fallback(cf, port, channel, payload: bytes):
    """
    Send a CRTP packet, trying multiple methods for compatibility.
    Raises RuntimeError if no method works.
    """
    header = ((port & 0x0F) << 4) | (channel & 0x0F)
    pkt = _PacketObj(header, payload)

    # Method 1: Crazyflie.send_packet
    try:
        send_fn = getattr(cf, "send_packet", None)
        if callable(send_fn):
            try:
                send_fn(pkt)
                return
            except Exception:
                pass
    except Exception:
        pass

    # Method 2: Low-level link object
    try:
        link = getattr(cf, "_link", None) or getattr(cf, "link", None)
        if link is not None:
            if hasattr(link, "sendPacket"):
                try:
                    link.sendPacket(pkt)
                    return
                except Exception:
                    pass
            if hasattr(link, "send_packet"):
                try:
                    link.send_packet(pkt)
                    return
                except Exception:
                    pass
    except Exception:
        pass

    # Method 3: cflib.crtp.send_packet fallback
    try:
        import cflib.crtp as _crtp
        sendp = getattr(_crtp, "send_packet", None)
        if callable(sendp):
            try:
                sendp(pkt)
                return
            except Exception:
                try:
                    sendp(bytes([pkt.header]) + pkt.data)
                    return
                except Exception:
                    pass
    except Exception:
        pass

    raise RuntimeError(
        "Unable to send CRTP packet: no send method available on Crazyflie instance"
    )


def try_send_with_retries(cf, fn, *args, retries=None, logger=None):
    """
    Call a function with retries and small inter-packet delay.
    Returns True on success, False on failure.
    """
    if retries is None:
        retries = defaults.NP_SEND_RETRIES
    last_exc = None
    fn_name = getattr(fn, "__name__", repr(fn))
    for attempt in range(1, retries + 1):
        try:
            fn(cf, *args)
            return True
        except Exception as e:
            last_exc = e
            if logger:
                logger(f"[NeoPixel] Attempt {attempt} failed: {e}")
            time.sleep(defaults.NP_PACKET_DELAY)
    if logger:
        logger(f"[NeoPixel] Failed after {retries} attempts: {last_exc}")
    return False
