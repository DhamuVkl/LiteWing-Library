"""
LiteWing GUI — Live Sensor Plotting
=====================================
Built-in matplotlib dashboards for visualizing drone sensor data.

Usage:
    from litewing import LiteWing
    from litewing.gui import live_dashboard

    live_dashboard(LiteWing("192.168.43.42"))

Available functions:
    live_dashboard(drone)    — Full 4-panel dashboard
    live_height_plot(drone)  — Height: filtered vs raw
    live_imu_plot(drone)     — IMU: roll, pitch, yaw
"""

import time
import threading
from collections import deque

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib import style
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _check_matplotlib():
    """Raise helpful error if matplotlib is not installed."""
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for GUI features.\n"
            "Install it with:  pip install matplotlib"
        )


def _ensure_connected(drone):
    """Connect if not already connected, wait for data."""
    if not drone.is_connected:
        drone.connect()
        time.sleep(2)  # Wait for sensor data to start flowing


def _apply_dark_theme():
    """Apply a modern dark theme to matplotlib."""
    plt.rcParams.update({
        "figure.facecolor": "#1e1e2e",
        "axes.facecolor": "#2a2a3d",
        "axes.edgecolor": "#444466",
        "axes.labelcolor": "#cdd6f4",
        "text.color": "#cdd6f4",
        "xtick.color": "#a6adc8",
        "ytick.color": "#a6adc8",
        "grid.color": "#3a3a5c",
        "grid.alpha": 0.5,
        "lines.linewidth": 1.8,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "figure.titlesize": 14,
        "figure.titleweight": "bold",
    })


# ─── Color palette ───────────────────────────────────────────────────
COLORS = {
    "cyan":    "#89dceb",
    "green":   "#a6e3a1",
    "yellow":  "#f9e2af",
    "red":     "#f38ba8",
    "mauve":   "#cba6f7",
    "blue":    "#89b4fa",
    "peach":   "#fab387",
    "teal":    "#94e2d5",
    "pink":    "#f5c2e7",
}


class _DataCollector:
    """Background thread that polls sensor data into deques."""

    def __init__(self, drone, max_points=200, interval_ms=100):
        self.drone = drone
        self.interval = interval_ms / 1000.0
        self.max_points = max_points
        self._running = False
        self._thread = None

        # Data buffers
        self.timestamps = deque(maxlen=max_points)
        self.height = deque(maxlen=max_points)
        self.range_height = deque(maxlen=max_points)
        self.roll = deque(maxlen=max_points)
        self.pitch = deque(maxlen=max_points)
        self.yaw = deque(maxlen=max_points)
        self.vx = deque(maxlen=max_points)
        self.vy = deque(maxlen=max_points)
        self.battery = deque(maxlen=max_points)
        self.gyro_x = deque(maxlen=max_points)
        self.gyro_y = deque(maxlen=max_points)
        self.gyro_z = deque(maxlen=max_points)
        self._start_time = time.time()

    def start(self):
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _collect_loop(self):
        while self._running:
            try:
                s = self.drone.read_sensors()
                t = time.time() - self._start_time
                self.timestamps.append(t)
                self.height.append(s.height)
                self.range_height.append(s.range_height)
                self.roll.append(s.roll)
                self.pitch.append(s.pitch)
                self.yaw.append(s.yaw)
                self.vx.append(s.vx)
                self.vy.append(s.vy)
                self.battery.append(s.battery)
                self.gyro_x.append(s.gyro_x)
                self.gyro_y.append(s.gyro_y)
                self.gyro_z.append(s.gyro_z)
            except Exception:
                pass
            time.sleep(self.interval)


# ─────────────────────────────────────────────────────────────────────
#  PUBLIC FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def live_dashboard(drone, max_points=200, update_ms=100):
    """
    Open a full sensor dashboard with 4 live-updating subplots:
      - Height (filtered + raw)
      - Attitude (roll, pitch, yaw)
      - Velocity (vx, vy)
      - Battery voltage

    Args:
        drone: LiteWing instance (will auto-connect if needed).
        max_points: Number of data points visible on screen.
        update_ms: Plot refresh interval in milliseconds.
    """
    _check_matplotlib()
    _apply_dark_theme()
    _ensure_connected(drone)

    collector = _DataCollector(drone, max_points=max_points, interval_ms=update_ms)
    collector.start()

    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    fig.suptitle("LiteWing — Live Sensor Dashboard", color=COLORS["cyan"])
    fig.subplots_adjust(hspace=0.4, wspace=0.3)

    ax_h, ax_imu, ax_vel, ax_bat = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # Height subplot
    line_hf, = ax_h.plot([], [], color=COLORS["cyan"], label="Filtered")
    line_hr, = ax_h.plot([], [], color=COLORS["peach"], label="Raw ToF", alpha=0.7)
    ax_h.set_title("Height")
    ax_h.set_ylabel("meters")
    ax_h.legend(loc="upper right", fontsize=8)
    ax_h.grid(True)

    # IMU subplot
    line_r, = ax_imu.plot([], [], color=COLORS["red"], label="Roll")
    line_p, = ax_imu.plot([], [], color=COLORS["green"], label="Pitch")
    line_y, = ax_imu.plot([], [], color=COLORS["yellow"], label="Yaw")
    ax_imu.set_title("Attitude (IMU)")
    ax_imu.set_ylabel("degrees")
    ax_imu.legend(loc="upper right", fontsize=8)
    ax_imu.grid(True)

    # Velocity subplot
    line_vx, = ax_vel.plot([], [], color=COLORS["blue"], label="VX")
    line_vy, = ax_vel.plot([], [], color=COLORS["mauve"], label="VY")
    ax_vel.set_title("Velocity (Optical Flow)")
    ax_vel.set_ylabel("m/s")
    ax_vel.set_xlabel("time (s)")
    ax_vel.legend(loc="upper right", fontsize=8)
    ax_vel.grid(True)

    # Battery subplot
    line_bat, = ax_bat.plot([], [], color=COLORS["green"], linewidth=2.5)
    ax_bat.set_title("Battery")
    ax_bat.set_ylabel("volts")
    ax_bat.set_xlabel("time (s)")
    ax_bat.grid(True)

    def update(frame):
        t = list(collector.timestamps)
        if len(t) < 2:
            return

        # Height
        line_hf.set_data(t, list(collector.height))
        line_hr.set_data(t, list(collector.range_height))
        ax_h.set_xlim(t[0], t[-1])
        h_all = list(collector.height) + list(collector.range_height)
        if h_all:
            ax_h.set_ylim(min(h_all) - 0.05, max(h_all) + 0.05)

        # IMU
        line_r.set_data(t, list(collector.roll))
        line_p.set_data(t, list(collector.pitch))
        line_y.set_data(t, list(collector.yaw))
        ax_imu.set_xlim(t[0], t[-1])
        imu_all = list(collector.roll) + list(collector.pitch) + list(collector.yaw)
        if imu_all:
            margin = max(abs(min(imu_all)), abs(max(imu_all)), 5) * 0.2
            ax_imu.set_ylim(min(imu_all) - margin, max(imu_all) + margin)

        # Velocity
        line_vx.set_data(t, list(collector.vx))
        line_vy.set_data(t, list(collector.vy))
        ax_vel.set_xlim(t[0], t[-1])
        v_all = list(collector.vx) + list(collector.vy)
        if v_all:
            margin = max(abs(min(v_all)), abs(max(v_all)), 0.01) * 0.3
            ax_vel.set_ylim(min(v_all) - margin, max(v_all) + margin)

        # Battery
        line_bat.set_data(t, list(collector.battery))
        ax_bat.set_xlim(t[0], t[-1])
        bat = list(collector.battery)
        if bat:
            bat_f = [v for v in bat if v > 0]
            if bat_f:
                ax_bat.set_ylim(min(bat_f) - 0.1, max(bat_f) + 0.1)

    ani = animation.FuncAnimation(fig, update, interval=update_ms, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        drone.disconnect()


def live_height_plot(drone, max_points=200, update_ms=100):
    """
    Open a single live plot showing height data:
      - Kalman-filtered height (stateEstimate.z)
      - Raw ToF laser reading (range.zrange)

    Args:
        drone: LiteWing instance (will auto-connect if needed).
        max_points: Number of data points visible on screen.
        update_ms: Plot refresh interval in milliseconds.
    """
    _check_matplotlib()
    _apply_dark_theme()
    _ensure_connected(drone)

    collector = _DataCollector(drone, max_points=max_points, interval_ms=update_ms)
    collector.start()

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("LiteWing — Live Height", color=COLORS["cyan"])

    line_filt, = ax.plot([], [], color=COLORS["cyan"], linewidth=2, label="Filtered (Kalman)")
    line_raw,  = ax.plot([], [], color=COLORS["peach"], linewidth=1.5, alpha=0.7, label="Raw ToF Laser")
    ax.set_ylabel("Height (meters)")
    ax.set_xlabel("Time (seconds)")
    ax.legend(loc="upper right")
    ax.grid(True)

    def update(frame):
        t = list(collector.timestamps)
        if len(t) < 2:
            return
        line_filt.set_data(t, list(collector.height))
        line_raw.set_data(t, list(collector.range_height))
        ax.set_xlim(t[0], t[-1])
        h_all = list(collector.height) + list(collector.range_height)
        if h_all:
            ax.set_ylim(min(h_all) - 0.05, max(h_all) + 0.05)

    ani = animation.FuncAnimation(fig, update, interval=update_ms, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        drone.disconnect()


def live_imu_plot(drone, max_points=200, update_ms=100):
    """
    Open a live plot showing IMU attitude data:
      - Roll (tilt left/right)
      - Pitch (tilt forward/back)
      - Yaw (rotation)

    Args:
        drone: LiteWing instance (will auto-connect if needed).
        max_points: Number of data points visible on screen.
        update_ms: Plot refresh interval in milliseconds.
    """
    _check_matplotlib()
    _apply_dark_theme()
    _ensure_connected(drone)

    collector = _DataCollector(drone, max_points=max_points, interval_ms=update_ms)
    collector.start()

    fig, (ax_att, ax_gyro) = plt.subplots(2, 1, figsize=(10, 7))
    fig.suptitle("LiteWing — Live IMU Data", color=COLORS["cyan"])
    fig.subplots_adjust(hspace=0.35)

    # Attitude
    line_r, = ax_att.plot([], [], color=COLORS["red"], label="Roll")
    line_p, = ax_att.plot([], [], color=COLORS["green"], label="Pitch")
    line_y, = ax_att.plot([], [], color=COLORS["yellow"], label="Yaw")
    ax_att.set_title("Orientation")
    ax_att.set_ylabel("degrees")
    ax_att.legend(loc="upper right", fontsize=8)
    ax_att.grid(True)

    # Gyroscope
    line_gx, = ax_gyro.plot([], [], color=COLORS["blue"], label="Gyro X")
    line_gy, = ax_gyro.plot([], [], color=COLORS["mauve"], label="Gyro Y")
    line_gz, = ax_gyro.plot([], [], color=COLORS["teal"], label="Gyro Z")
    ax_gyro.set_title("Gyroscope")
    ax_gyro.set_ylabel("°/s")
    ax_gyro.set_xlabel("Time (seconds)")
    ax_gyro.legend(loc="upper right", fontsize=8)
    ax_gyro.grid(True)

    def update(frame):
        t = list(collector.timestamps)
        if len(t) < 2:
            return

        # Attitude
        line_r.set_data(t, list(collector.roll))
        line_p.set_data(t, list(collector.pitch))
        line_y.set_data(t, list(collector.yaw))
        ax_att.set_xlim(t[0], t[-1])
        att = list(collector.roll) + list(collector.pitch) + list(collector.yaw)
        if att:
            margin = max(abs(min(att)), abs(max(att)), 5) * 0.2
            ax_att.set_ylim(min(att) - margin, max(att) + margin)

        # Gyroscope
        line_gx.set_data(t, list(collector.gyro_x))
        line_gy.set_data(t, list(collector.gyro_y))
        line_gz.set_data(t, list(collector.gyro_z))
        ax_gyro.set_xlim(t[0], t[-1])
        gyro = list(collector.gyro_x) + list(collector.gyro_y) + list(collector.gyro_z)
        if gyro:
            margin = max(abs(min(gyro)), abs(max(gyro)), 1) * 0.3
            ax_gyro.set_ylim(min(gyro) - margin, max(gyro) + margin)

    ani = animation.FuncAnimation(fig, update, interval=update_ms, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        drone.disconnect()
