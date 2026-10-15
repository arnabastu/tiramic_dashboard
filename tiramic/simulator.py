"""Software model of the TIRAMIC rig. Owner: Member A.

simulate() returns a DataFrame with the columns the real ESP32 will later send:
t, supply_state, pump_on, q1, q2, q3, q4
plus two ground-truth columns that exist ONLY in simulation:
true_zones (text such as "none", "2" or "1+3"), true_leak_lpm
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C

# Timeline of one pump cycle (seconds)
OFF_START_S = 20
STARTUP_S = 10
REFILL_S = 40
SHUTDOWN_S = 10
OFF_END_S = 20

# How pipe filling / draining is shared between the three zones
ZONE_SHARE = np.array([0.40, 0.35, 0.25])


@dataclass(frozen=True)
class Leak:
    zone: int  # 1, 2 or 3
    lpm: float  # leak rate at nominal flow
    start_s: float
    end_s: float = 1e9  # 1e9 = never repaired


@dataclass(frozen=True)
class SensorFault:
    meter: int  # 1..4
    kind: str  # "stuck" or "dropout"
    start_s: float
    end_s: float = 1e9


class Rig:
    """One physical rig. Its meters have fixed calibration errors (its 'personality')."""

    def __init__(self, seed: int = 7):
        self.seed = seed
        rng = np.random.default_rng(seed)
        self.gains = 1.0 + rng.normal(0.0, C.METER_GAIN_SPREAD, C.N_METERS)


def stable_window(stable_s: float = 240):
    """Return the (start, end) times of the STABLE state."""
    start = OFF_START_S + STARTUP_S + REFILL_S
    return start, start + stable_s


def total_duration(stable_s: float = 240) -> int:
    return int(stable_window(stable_s)[1] + SHUTDOWN_S + OFF_END_S)


def example_leak(zone: int, lpm: float, stable_s: float = 240, repair_s=None) -> Leak:
    """Create a leak that starts 60 s after the stable state begins."""
    start = stable_window(stable_s)[0] + 60
    return Leak(zone, lpm, start, repair_s if repair_s is not None else 1e9)


def simulate(
    rig,
    leaks=(),
    faults=(),
    stable_s=240,
    nominal=C.NOMINAL_FLOW_LPM,
    noise_seed=0,
    noise_scale=1.0,
):
    rng = np.random.default_rng(noise_seed)
    n = total_duration(stable_s)
    t = np.arange(n, dtype=float) * C.SAMPLE_PERIOD_S
    s0 = OFF_START_S
    s1 = s0 + STARTUP_S
    s2 = s1 + REFILL_S
    s3 = s2 + stable_s
    s4 = s3 + SHUTDOWN_S
    state = np.empty(n, dtype=object)
    q_in = np.zeros(n)  # true flow entering the rig
    absorb = np.zeros(n)  # + pipes filling (downstream sees less), - pipes draining

    for i, ti in enumerate(t):
        if ti < s0:
            state[i] = "OFF"
        elif ti < s1:
            state[i] = "STARTUP"
            q_in[i] = nominal * (ti - s0) / STARTUP_S
        elif ti < s2:
            state[i] = "REFILLING"
            q_in[i] = nominal
        elif ti < s3:
            state[i] = "STABLE"
            q_in[i] = nominal
        elif ti < s4:
            state[i] = "SHUTDOWN"
            q_in[i] = nominal * (1.0 - (ti - s3) / SHUTDOWN_S)
        else:
            state[i] = "OFF"

        if s0 <= ti < s2:
            absorb[i] = 0.9 * np.exp(-(ti - s0) / 18.0)
        elif s3 <= ti < s4:
            absorb[i] = -0.5 * np.exp(-(ti - s3) / 6.0)

    # A leak at zone z removes water from every meter after that zone.
    leak_loss = np.zeros((n, 3))
    pressure = np.clip(q_in / nominal, 0.0, 1.0)
    for lk in leaks:
        active = (t >= lk.start_s) & (t < lk.end_s)
        leak_loss[:, lk.zone - 1] += np.where(active, lk.lpm * pressure, 0.0)

    zone_loss = absorb[:, None] * ZONE_SHARE[None, :] + leak_loss
    true_q = np.zeros((n, 4))
    true_q[:, 0] = q_in
    for k in range(1, 4):
        true_q[:, k] = true_q[:, k - 1] - zone_loss[:, k - 1]
    true_q = np.clip(true_q, 0.0, None)

    # Meter readings include calibration error and noise (no pulses -> exactly 0).
    meas = true_q * rig.gains[None, :]
    noise = rng.normal(0.0, C.METER_NOISE_LPM * noise_scale, size=true_q.shape)
    meas = np.where(true_q > 0.05, meas + noise, 0.0)
    meas = np.clip(meas, 0.0, None)

    for fault in faults:
        k = fault.meter - 1
        mask = (t >= fault.start_s) & (t < fault.end_s)
        if not mask.any():
            continue
        if fault.kind == "dropout":
            meas[mask, k] = np.nan
        elif fault.kind == "stuck":
            first = int(np.argmax(mask))
            meas[mask, k] = meas[max(first - 1, 0), k]
        else:
            raise ValueError(f"unknown fault kind: {fault.kind}")

    zones_txt = []
    for i in range(n):
        zs = [str(z + 1) for z in range(3) if leak_loss[i, z] > 0.01]
        zones_txt.append("+".join(zs) if zs else "none")

    return pd.DataFrame(
        {
            "t": t,
            "supply_state": state,
            "pump_on": state != "OFF",
            "q1": meas[:, 0],
            "q2": meas[:, 1],
            "q3": meas[:, 2],
            "q4": meas[:, 3],
            "true_zones": zones_txt,
            "true_leak_lpm": leak_loss.sum(axis=1),
        }
    )