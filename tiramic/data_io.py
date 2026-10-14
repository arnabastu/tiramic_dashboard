"""Loading, checking and saving rig data. Owner: Member A.
CSV contract (the ESP32 recorder must produce exactly this):
t,supply_state,q1,q2,q3,q4
t = seconds, supply_state = OFF/STARTUP/REFILLING/STABLE/SHUTDOWN, q1..q4 = flow in L/min.
"""
import pandas as pd
from . import config as C
REQUIRED_COLS = ["t", "supply_state", "q1", "q2", "q3", "q4"]
def validate(df: pd.DataFrame) -> list:
    """Return a list of problems (empty list = file is fine)."""
    problems = []
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        return [f"Missing columns: {missing}. Expected {REQUIRED_COLS}"]
    bad_states = sorted(set(df["supply_state"].astype(str)) - set(C.SUPPLY_STATES))
    if bad_states:
        problems.append(f"Unknown supply_state values: {bad_states}. Allowed: {C.SUPPLY_STATES}")
    if len(df) < 30:
        problems.append("Fewer than 30 rows - too short to analyse.")
    if not pd.to_numeric(df["t"], errors="coerce").is_monotonic_increasing:
        problems.append("Column t must increase from top to bottom.")
    return problems

def load_csv(file_or_path) -> pd.DataFrame:
    """Read a CSV, validate it and add the pump_on column."""
    df = pd.read_csv(file_or_path)
    problems = validate(df)
    if problems:
        raise ValueError(" | ".join(problems))
    df = df.copy()
    df["supply_state"] = df["supply_state"].astype(str)
    for c in ["t", "q1", "q2", "q3", "q4"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["pump_on"] = df["supply_state"] != "OFF"
    return df.reset_index(drop=True)

def to_csv_bytes(df: pd.DataFrame, include_truth: bool = False) -> bytes:
    """CSV text for download. Ground-truth columns are dropped unless asked for."""
    cols = list(REQUIRED_COLS)
    if include_truth:
        cols += [c for c in ["true_zones", "true_leak_lpm"] if c in df.columns]
    return df[cols].to_csv(index=False).encode("utf-8")