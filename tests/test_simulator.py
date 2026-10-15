import numpy as np

from tiramic import simulator as sim


def test_columns_and_length():
    df = sim.simulate(sim.Rig(7))
    assert list(df.columns[:7]) == ["t", "supply_state", "pump_on", "q1", "q2", "q3", "q4"]
    assert len(df) == sim.total_duration(240)
    assert set(df["supply_state"]) == {"OFF", "STARTUP", "REFILLING", "STABLE", "SHUTDOWN"}


def test_leak_shows_in_correct_zone_difference():
    rig = sim.Rig(7)
    clean = sim.simulate(rig, noise_seed=1)
    leaky = sim.simulate(rig, [sim.example_leak(2, 0.8)], noise_seed=1)
    w = (leaky["t"] > 150) & (leaky["t"] < 300)
    d_clean = (clean.loc[w, "q2"] - clean.loc[w, "q3"]).mean()
    d_leaky = (leaky.loc[w, "q2"] - leaky.loc[w, "q3"]).mean()
    assert 0.6 < d_leaky - d_clean < 1.0           # about the leak size
    z1 = ((leaky.loc[w, "q1"] - leaky.loc[w, "q2"]).mean() - (clean.loc[w, "q1"] - clean.loc[w, "q2"]).mean())
    assert abs(z1) < 0.1                            # zone 1 unaffected


def test_faults():
    rig = sim.Rig(7)
    stuck = sim.simulate(rig, faults=[sim.SensorFault(3, "stuck", 150)])
    assert stuck.loc[stuck["t"] >= 150, "q3"].nunique() == 1
    drop = sim.simulate(rig, faults=[sim.SensorFault(2, "dropout", 150)])
    assert drop.loc[drop["t"] >= 150, "q2"].isna().all()


def test_pump_off_means_zero_flow():
    df = sim.simulate(sim.Rig(7))
    assert (df.loc[df["supply_state"] == "OFF", ["q1", "q2", "q3", "q4"]] == 0).all().all()