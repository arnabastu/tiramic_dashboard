"""Create example CSV files in data/."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tiramic import data_io, simulator as sim

out = Path("data")
out.mkdir(exist_ok=True)

rig = sim.Rig(7)

runs = {
    "sample_noleak_baseline.csv": sim.simulate(
        rig, noise_seed=11
    ),
    "sample_leak_zone2.csv": sim.simulate(
        rig, [sim.example_leak(2, 0.6)], noise_seed=12
    ),
    "sample_stuck_meter3.csv": sim.simulate(
        rig,
        faults=[sim.SensorFault(3, "stuck", 150)],
        noise_seed=13
    ),
}

for name, df in runs.items():
    (out / name).write_bytes(data_io.to_csv_bytes(df))
    print("wrote", out / name)