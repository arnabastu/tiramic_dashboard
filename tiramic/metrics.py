
def min_detectable(trials, target=0.9):
    """Find the smallest reliably detected leak size."""

    rate = trials.groupby("size_lpm")["detected"].mean().sort_index()
    best = None

    for size in rate.index[::-1]:
        if rate[size] >= target:
            best = float(size)
        else:
            break

    return best

import numpy as np



def summarise(trials, noleak):
    results = {}

    for name, group in trials.groupby("detector"):
        detected = group[group["detected"]]
        hours = noleak.get("hours", 0)
        false_alarms = noleak.get(name, 0)

        results[name] = {
            "trials": len(group),
            "detection_rate": group["detected"].mean(),
            "zone_accuracy": (
                detected["zone_correct"].mean()
                if len(detected) else np.nan
            ),
            "median_delay_s": (
                detected["delay_s"].median()
                if len(detected) else np.nan
            ),
            "false_alarms_per_hour": (
                false_alarms / hours if hours else np.nan
            ),
            "min_detectable_lpm": min_detectable(group),
        }

    return results
