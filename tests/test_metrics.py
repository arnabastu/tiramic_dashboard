import numpy as np

from tiramic import detection as det
from tiramic import metrics
from tiramic import simulator as sim


def _setup():
    rig = sim.Rig(7)
    base = det.fit_baseline([sim.simulate(rig, noise_seed=9000 + i, nominal=q)
                             for i, q in enumerate([4.6, 5.0, 5.4, 5.0, 4.8])])
    return rig, base


def test_big_leaks_are_detected_and_summary_keys():
    rig, base = _setup()
    trials = metrics.run_trials(rig, base, sizes=(0.5, 1.0), repeats=3)
    noleak = metrics.run_noleak(rig, base, runs=3)
    s = metrics.summarise(trials, noleak)
    assert set(s) == {"TIRAMIC", "Naive"}
    assert s["TIRAMIC"]["detection_rate"] >= 0.9
    assert s["TIRAMIC"]["false_alarms_per_hour"] == 0
    assert {"detection_rate", "zone_accuracy", "median_delay_s", "min_detectable_lpm"} <= set(s["TIRAMIC"])


def test_min_detectable_logic():
    import pandas as pd
    g = pd.DataFrame({"size_lpm": [0.1, 0.1, 0.3, 0.3, 0.5, 0.5], "detected": [False, True, True, True, True, True]})
    assert metrics.min_detectable(g) == 0.3