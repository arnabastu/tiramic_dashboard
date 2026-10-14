
"""Read the real ESP32 over USB serial. Owner: Member A.

The ESP32 firmware must print ONE JSON object per line, once per second.
Example:
{"t": 12.0, "state": "STABLE", "q": [5.01, 4.98, 4.95, 4.97]}

q = flow in L/min for F1..F4.
"""

import csv
import json
import time


def parse_line(line):
    """Turn one serial line into a dict row, or None if invalid."""
    try:
        obj = json.loads(line.strip())
        q = obj["q"]

        if len(q) != 4:
            return None

        return {
            "t": float(obj["t"]),
            "supply_state": str(obj["state"]),
            "q1": float(q[0]),
            "q2": float(q[1]),
            "q3": float(q[2]),
            "q4": float(q[3]),
        }

    except (ValueError, KeyError, TypeError):
        return None


def record_serial(port, seconds, out_path, baud=115200):
    """Record ESP32 data and save it as CSV. Returns row count."""

    import serial

    rows = []

    with serial.Serial(port, baud, timeout=2) as ser:
        end = time.time() + seconds

        while time.time() < end:
            raw = ser.readline().decode("utf-8", errors="ignore")
            row = parse_line(raw)

            if row:
                rows.append(row)

    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "t",
                "supply_state",
                "q1",
                "q2",
                "q3",
                "q4",
            ],
        )

        w.writeheader()
        w.writerows(rows)

    return len(rows)
