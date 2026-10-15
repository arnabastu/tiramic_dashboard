"""Leak detection, sensor health, confidence and repair proof.  Owner: Member B.

Zone i lies between meter i and meter i+1:
    L1 = Q1 - Q2,  L2 = Q2 - Q3,  L3 = Q3 - Q4
Each difference is corrected with the no-leak baseline of the CURRENT supply state.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C

Q_COLS = ["q1", "q2", "q3", "q4"]
ALARM_STATUSES = ["LEAK", "MULTIPLE"]


# ---------------------------------------------------------------- baseline
@dataclass
class Baseline:
    mean: dict            # supply_state -> array of 3 (healthy zone differences)
    std: dict             # supply_state -> array of 3 (healthy noise)
    fallback_mean: np.ndarray
    fallback_std: np.ndarray

    def get(self, state):
        if state in self.mean:
            return self.mean[state], self.std[state]
        return self.fallback_mean, self.fallback_std


def diffs(q: np.ndarray) -> np.ndarray:
    """Zone differences, shape (n, 3)."""
    return q[:, :-1] - q[:, 1:]


def fit_baseline(dfs) -> Baseline:
    """Learn the healthy fingerprint of every supply state from NO-LEAK runs."""
    if isinstance(dfs, pd.DataFrame):
        dfs = [dfs]
    d = np.vstack([diffs(df[Q_COLS].to_numpy(float)) for df in dfs])
    s = np.concatenate([df["supply_state"].astype(str).to_numpy() for df in dfs])
    ok = ~np.isnan(d).any(axis=1)
    mean, std = {}, {}
    for st in C.SUPPLY_STATES:
        m = (s == st) & ok
        if m.sum() >= 5:
            mean[st] = d[m].mean(axis=0)
            std[st] = np.maximum(d[m].std(axis=0, ddof=1), C.MIN_STD_LPM)
    fb_mean = mean.get("STABLE", np.zeros(3))
    fb_std = std.get("STABLE", np.full(3, 0.1))
    return Baseline(mean, std, fb_mean, fb_std)


# ---------------------------------------------------------------- sensor health
def sensor_health(df: pd.DataFrame) -> pd.DataFrame:
    """True = meter looks healthy. Columns ok_F1 .. ok_F4."""
    state = df["supply_state"].astype(str)
    pump_on = state != "OFF"
    # "stuck" only makes sense once the pump has been running for the whole check window
    pump_long = pump_on.astype(int).rolling(C.STUCK_WINDOW, min_periods=C.STUCK_WINDOW).min().fillna(0).astype(bool)
    # "phantom flow": pump has been OFF for the whole window but a meter still shows flow
    pump_off_long = (~pump_on).astype(int).rolling(C.STUCK_WINDOW, min_periods=C.STUCK_WINDOW).min().fillna(0).astype(bool)
    out = pd.DataFrame(index=df.index)
    for i, c in enumerate(Q_COLS):
        s = df[c].astype(float)
        invalid = s.isna() | (s < 0) | (s > C.MAX_VALID_LPM)
        span = s.rolling(C.STUCK_WINDOW, min_periods=C.STUCK_WINDOW).max() - \
               s.rolling(C.STUCK_WINDOW, min_periods=C.STUCK_WINDOW).min()
        stuck = (span < 1e-9) & pump_long
        phantom = pump_off_long & (s > 0.3)
        bad = invalid | stuck | phantom
        if i == 0:   # pump says "running" but the first meter sees almost nothing
            bad = bad | (state.isin(["REFILLING", "STABLE"]) & (s < 0.3))
        out[f"ok_F{i + 1}"] = ~bad
    return out


# ---------------------------------------------------------------- main analysis
def analyse(df, baseline, window=C.SMOOTH_WINDOW, k=C.K_SIGMA, persistence=C.PERSISTENCE):
    """Run the whole detection chain. Returns one row per input row."""
    n = len(df)
    q = df[Q_COLS].to_numpy(float)
    states = df["supply_state"].astype(str).to_numpy()
    d = diffs(q)

    mean = np.zeros((n, 3))
    std = np.zeros((n, 3))
    for i, s in enumerate(states):
        mean[i], std[i] = baseline.get(s)

    # smoothed excess over the healthy baseline
    ex = pd.DataFrame(d - mean).rolling(window, min_periods=1).mean().to_numpy()
    ex = np.nan_to_num(ex, nan=0.0)
    # in STABLE averaging reduces noise; in transitions stay conservative
    sigma = np.where((states == "STABLE")[:, None], std / np.sqrt(window), std)
    thr = np.maximum(C.MIN_LEAK_LPM, k * sigma)
    snr = ex / sigma

    # sensor health (a zone is trusted only if both of its meters were healthy recently)
    ok = sensor_health(df)
    ok_recent = ok.astype(int).rolling(window, min_periods=1).min().astype(bool)
    trust = np.column_stack([
        ok_recent[f"ok_F{z}"].to_numpy() & ok_recent[f"ok_F{z + 1}"].to_numpy() for z in (1, 2, 3)
    ])

    flag = (ex > thr) & trust
    alarm = (pd.DataFrame(flag.astype(int)).rolling(persistence, min_periods=persistence)
             .min().fillna(0).to_numpy().astype(bool))

    n_alarm = alarm.sum(axis=1)
    all_trusted = ok_recent.all(axis=1).to_numpy()
    pump_on = states != "OFF"

    status = np.empty(n, dtype=object)
    suspect = np.zeros(n, dtype=int)
    for i in range(n):
        if n_alarm[i] == 1:
            status[i] = "LEAK"
            suspect[i] = int(np.argmax(alarm[i])) + 1
        elif n_alarm[i] > 1:
            status[i] = "MULTIPLE"
            suspect[i] = -1
        elif not all_trusted[i]:
            status[i] = "SENSOR_FAULT"
        elif not pump_on[i]:
            status[i] = "IDLE"
        else:
            status[i] = "NORMAL"

    # confidence: 1 point each (see README)
    conf = np.array([""] * n, dtype=object)
    loss = np.zeros(n)
    run = 0
    for i in range(n):
        if n_alarm[i] > 0:
            run += 1
            zs = np.where(alarm[i])[0]
            top = zs[np.argmax(snr[i, zs])]
            loss[i] = max(ex[i, zs].sum(), 0.0)
            score = int(snr[i, top] >= 8) + int(states[i] == "STABLE") + int(all_trusted[i]) + int(run >= 20)
            conf[i] = "High" if score >= 3 else ("Medium" if score == 2 else "Low")
        else:
            run = 0

    res = df.copy().reset_index(drop=True)
    for z in range(3):
        res[f"d{z + 1}"] = d[:, z]
        res[f"ex{z + 1}"] = ex[:, z]
        res[f"thr{z + 1}"] = thr[:, z]
        res[f"snr{z + 1}"] = snr[:, z]
        res[f"alarm{z + 1}"] = alarm[:, z]
        res[f"trust{z + 1}"] = trust[:, z]
    for c in ok.columns:
        res[c] = ok[c].to_numpy()
    res["status"] = status
    res["suspect_zone"] = suspect
    res["confidence"] = conf
    res["loss_est_lpm"] = loss
    return res


# ---------------------------------------------------------------- outputs for the UI
def alarm_episodes(res: pd.DataFrame) -> pd.DataFrame:
    """One row per continuous alert (leak, multiple leaks or sensor fault)."""
    active = res["status"].isin(ALARM_STATUSES + ["SENSOR_FAULT"])
    cols = ["start_s", "end_s", "duration_s", "type", "where", "peak_loss_lpm", "confidence"]
    if not active.any():
        return pd.DataFrame(columns=cols)
    key = res["status"].astype(str) + "|" + res["suspect_zone"].astype(str)
    grp = (key != key.shift()).cumsum()
    rows = []
    for _, sub in res[active].groupby(grp[active]):
        first = sub.iloc[0]
        if first["status"] == "SENSOR_FAULT":
            bad = [c.replace("ok_", "") for c in ["ok_F1", "ok_F2", "ok_F3", "ok_F4"] if not first[c]]
            where = "Check " + (", ".join(bad) if bad else "sensors")
        else:
            zs = [str(z) for z in (1, 2, 3) if first[f"alarm{z}"]]
            where = "Zone " + "+".join(zs)
        conf = sub["confidence"].replace("", np.nan).dropna()
        rows.append({
            "start_s": float(sub["t"].iloc[0]),
            "end_s": float(sub["t"].iloc[-1]),
            "duration_s": float(sub["t"].iloc[-1] - sub["t"].iloc[0] + C.SAMPLE_PERIOD_S),
            "type": first["status"],
            "where": where,
            "peak_loss_lpm": float(sub["loss_est_lpm"].max()),
            "confidence": conf.mode().iloc[0] if len(conf) else "-",
        })
    return pd.DataFrame(rows, columns=cols)


def explain(row) -> list:
    """Plain-language reasons for the current status (TrustExplain)."""
    lines = [f"Supply state: {row['supply_state']}"]
    bad = [c.replace("ok_", "") for c in ["ok_F1", "ok_F2", "ok_F3", "ok_F4"] if not row[c]]
    if row["status"] in ALARM_STATUSES:
        zs = [z for z in (1, 2, 3) if row[f"alarm{z}"]]
        lines.append("Suspected: " + ", ".join(C.ZONE_NAMES[z - 1] for z in zs))
        lines.append(f"Estimated loss: {row['loss_est_lpm']:.2f} L/min")
        for z in zs:
            lines.append(f"Zone {z}: excess {row[f'ex{z}']:.2f} L/min, alarm threshold {row[f'thr{z}']:.2f}, "
                         f"signal/noise {row[f'snr{z}']:.1f}")
        lines.append(f"Confidence: {row['confidence']}")
    elif row["status"] == "SENSOR_FAULT":
        lines.append("Result: INCONCLUSIVE for zones touching the faulty meter(s).")
    elif row["status"] == "IDLE":
        lines.append("Pump is off - nothing to evaluate.")
    else:
        lines.append("All zone differences are within the healthy range for this state.")
    if bad:
        lines.append("Sensor problem: " + ", ".join(bad) + " (stale, missing or invalid readings)")
    else:
        lines.append("All 4 sensors healthy.")
    return lines


def repair_proof(res, zone, t_repair, settle_s=15, window_s=40) -> dict:
    """Compare the zone's loss before and after a repair (STABLE samples only)."""
    t = res["t"]
    stable = res["supply_state"] == "STABLE"
    pre = res[(t >= t_repair - window_s) & (t < t_repair) & stable][f"ex{zone}"]
    post = res[(t >= t_repair + settle_s) & (t < t_repair + settle_s + window_s) & stable][f"ex{zone}"]
    if len(pre) < 5 or len(post) < 5:
        return {"verified": None, "pre_lpm": np.nan, "post_lpm": np.nan, "reduction_pct": np.nan,
                "note": "Not enough STABLE data before/after the repair."}
    pre_m, post_m = float(pre.mean()), float(post.mean())
    leaked_before = pre_m > C.MIN_LEAK_LPM
    verified = bool(leaked_before and post_m < max(C.MIN_LEAK_LPM, 0.25 * pre_m))
    reduction = 100.0 * (pre_m - post_m) / pre_m if pre_m > 0 else np.nan
    if not leaked_before:
        note = "No clear leak before the repair - nothing to verify."
    elif verified:
        note = "Loss in this zone is back to the healthy range."
    else:
        note = "Loss is still above the healthy range - repair not confirmed."
    return {"verified": verified, "pre_lpm": pre_m, "post_lpm": post_m,
            "reduction_pct": reduction, "note": note}


# ---------------------------------------------------------------- simple comparison detector
def naive_detect(df, thr=0.3, persistence=5):
    """Baseline detector for comparison: raw Q1-Q4 above a fixed number. No baseline,
    no supply states, no health checks. Zone guess = largest raw difference."""
    q = df[Q_COLS].to_numpy(float)
    total = q[:, 0] - q[:, 3]
    flag = pd.Series(np.nan_to_num(total, nan=0.0) > thr).astype(int)
    alarm = flag.rolling(persistence, min_periods=persistence).min().fillna(0).to_numpy().astype(bool)
    zone = np.argmax(np.nan_to_num(diffs(q), nan=-9.0), axis=1) + 1
    return pd.DataFrame({"alarm": alarm, "zone": zone})