import numpy as np
import pytest

from tiramic import detection as det
from tiramic import simulator as sim


@pytest.fixture(scope="module")
def rig():
    return sim.Rig(7)


@pytest.fixture(scope="module")
def baseline(rig):
    runs = [sim.simulate(rig, noise_seed=9000 + i, nominal=q) for i, q in enumerate([4.6, 5.0, 5.4, 5.0, 4.8])]
    return det.fit_baseline(runs)


def test_no_false_alarms_without_leak(rig, baseline):
    for seed in range(10):
        res = det.analyse(sim.simulate(rig, noise_seed=100 + seed), baseline)
        assert not res["status"].isin(["LEAK", "MULTIPLE", "SENSOR_FAULT"]).any()


@pytest.mark.parametrize("zone", [1, 2, 3])
def test_leak_found_in_right_zone(rig, baseline, zone):
    res = det.analyse(sim.simulate(rig, [sim.example_leak(zone, 0.6)], noise_seed=5), baseline)
    hit = res[res["status"] == "LEAK"]
    assert len(hit) > 50
    assert (hit["suspect_zone"] == zone).all()
    assert hit["t"].iloc[0] < 160                    # found within ~30 s of the leak starting (t=130)


def test_stuck_and_dropout_flagged(rig, baseline):
    for kind in ("stuck", "dropout"):
        res = det.analyse(sim.simulate(rig, faults=[sim.SensorFault(3, kind, 150)], noise_seed=6), baseline)
        assert (res["status"] == "SENSOR_FAULT").sum() > 50
        assert not (res["status"] == "LEAK").any()


def test_two_leaks_gives_multiple(rig, baseline):
    leaks = [sim.Leak(1, 0.8, 130), sim.Leak(3, 0.8, 170)]
    res = det.analyse(sim.simulate(rig, leaks, noise_seed=2), baseline)
    assert (res["status"] == "MULTIPLE").any()


def test_repair_proof(rig, baseline):
    fixed = det.analyse(sim.simulate(rig, [sim.Leak(2, 0.8, 130, 230)], noise_seed=3), baseline)
    assert det.repair_proof(fixed, 2, 230)["verified"] is True
    broken = det.analyse(sim.simulate(rig, [sim.Leak(2, 0.8, 130)], noise_seed=3), baseline)
    assert det.repair_proof(broken, 2, 230)["verified"] is False


def test_alarm_episodes_and_explain(rig, baseline):
    res = det.analyse(sim.simulate(rig, [sim.example_leak(2, 0.6)], noise_seed=5), baseline)
    ep = det.alarm_episodes(res)
    assert len(ep) >= 1 and ep.iloc[0]["where"] == "Zone 2"
    lines = det.explain(res[res["status"] == "LEAK"].iloc[0])
    assert any("Zone 2" in x for x in lines)