"""
LiteWing Flight Logger
=======================
Record flight data to CSV files for later analysis.

Usage:
    drone.start_logging("my_flight.csv")
    drone.forward(1.0, 0.2)
    drone.stop_logging()

The CSV file will contain columns for:
    Timestamp, Position X/Y, Height, Range, Velocity X/Y, Correction VX/VY
"""

import csv
import os
from datetime import datetime


class FlightLogger:
    """
    Records flight data to CSV files.

    Each row is a snapshot of sensor state at a point in time.
    Useful for analysing flight performance, PID tuning, and drift patterns.
    """

    def __init__(self):
        self._file = None
        self._writer = None
        self._start_time = None
        self._filepath = None

    @property
    def is_logging(self):
        """True if currently recording data."""
        return self._writer is not None

    @property
    def filepath(self):
        """Path to the current log file, or None."""
        return self._filepath

    def start(self, filename=None, logger=None):
        """
        Start recording flight data to a CSV file.

        Args:
            filename: Optional custom filename. If None, generates a timestamped name.
            logger: Optional logging function for status messages.
        """
        if self.is_logging:
            if logger:
                logger("Logger: Already recording. Stop first before starting a new log.")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"drone_flight_log_{timestamp}.csv"

        self._filepath = filename
        self._file = open(filename, mode="w", newline="")
        self._writer = csv.writer(self._file)
        self._start_time = None  # Set on first log_row call

        # Write header
        self._writer.writerow([
            "Timestamp (s)",
            "Position X (m)",
            "Position Y (m)",
            "Height (m)",
            "Range (m)",
            "Velocity X (m/s)",
            "Velocity Y (m/s)",
            "Correction VX",
            "Correction VY",
        ])

        if logger:
            logger(f"Logging to CSV: {filename}")

    def log_row(self, pos_x, pos_y, height, range_height, vx, vy,
                correction_vx=0.0, correction_vy=0.0, start_time=None):
        """
        Write one row of flight data.

        Called internally by the flight engine at each control loop iteration.
        """
        if not self.is_logging:
            return

        import time
        if self._start_time is None:
            self._start_time = start_time or time.time()

        elapsed = time.time() - self._start_time
        self._writer.writerow([
            f"{elapsed:.3f}",
            f"{pos_x:.6f}",
            f"{pos_y:.6f}",
            f"{height:.6f}",
            f"{range_height:.6f}",
            f"{vx:.6f}",
            f"{vy:.6f}",
            f"{correction_vx:.6f}",
            f"{correction_vy:.6f}",
        ])

    def stop(self, logger=None):
        """Stop recording and close the CSV file."""
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
            if logger:
                logger(f"CSV log closed: {self._filepath}")
            self._filepath = None
            self._start_time = None
