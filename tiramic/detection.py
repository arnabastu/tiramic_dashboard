
import numpy as np
import pandas as pd
from . import config as C


ZONES = {
    "zone1": ("q1", "q2"),
    "zone2": ("q2", "q3"),
    "zone3": ("q3", "q4"),
}


def calculate_flow_differences(df):
    """Calculate flow differences across the three zones."""
    df = df.copy()

    for zone, (q_a, q_b) in ZONES.items():
        df[zone] = df[q_a] - df[q_b]

    return df


def smooth_flow_differences(df, window=None):
    """Smooth zone differences using a moving average."""
    df = df.copy()

    if window is None:
        window = C.SMOOTH_WINDOW

    for zone in ZONES:
        df[zone] = df[zone].rolling(
            window=window, min_periods=1
        ).mean()

    return df


def detect_possible_leaks(df, threshold=None):
    """Flag zone differences that exceed the leak threshold."""
    df = df.copy()

    if threshold is None:
        threshold = C.MIN_LEAK_LPM

    for zone in ZONES:
        df[zone + "_leak"] = df[zone] > threshold

    return df


def confirm_leaks(df, persistence=None):
    """Confirm alarms after consecutive positive readings."""
    df = df.copy()

    if persistence is None:
        persistence = C.PERSISTENCE

    for zone in ZONES:
        leak_column = zone + "_leak"

        df[zone + "_alarm"] = (
            df[leak_column]
            .rolling(
                window=persistence,
                min_periods=persistence
            )
            .sum()
            .eq(persistence)
        )

    return df


def check_sensor_health(df):
    """Flag missing, negative, or out-of-range meter readings."""
    df = df.copy()

    for col in ["q1", "q2", "q3", "q4"]:
        df[col + "_ok"] = (
            df[col].notna()
            & df[col].between(0, C.MAX_VALID_LPM)
        )

    return df


def check_stuck_sensors(df):
    """Flag readings unchanged for the configured window."""
    df = df.copy()

    for col in ["q1", "q2", "q3", "q4"]:
        unchanged = df[col].diff().eq(0)

        df[col + "_stuck"] = (
            unchanged.rolling(
                window=C.STUCK_WINDOW - 1,
                min_periods=C.STUCK_WINDOW - 1
            ).sum().eq(C.STUCK_WINDOW - 1)
        )

    return df


def analyse(df):
    """Run basic zone leak detection and sensor checks."""
    df = df.copy()

    required = [
        "t", "supply_state", "q1", "q2", "q3", "q4"
    ]

    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"Missing required column: {col}"
            )

    # Check sensor readings first.
    df = check_sensor_health(df)
    df = check_stuck_sensors(df)

    # Calculate and smooth zone differences.
    df = calculate_flow_differences(df)
    df = smooth_flow_differences(df)

    # Flag possible leaks and confirm persistent alarms.
    df = detect_possible_leaks(df)
    df = confirm_leaks(df)

    # Suppress alarms when either associated sensor is invalid
    # or flagged as stuck.
    for zone, (q_a, q_b) in ZONES.items():
        sensors_ok = (
            df[q_a + "_ok"]
            & df[q_b + "_ok"]
            & ~df[q_a + "_stuck"]
            & ~df[q_b + "_stuck"]
        )

        df[zone + "_alarm"] = (
            df[zone + "_alarm"] & sensors_ok
        )

    return df
