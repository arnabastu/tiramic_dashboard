import io

import pytest

from tiramic import data_io, serial_reader, simulator as sim


def test_validate_missing_columns():
    import pandas as pd
    assert data_io.validate(pd.DataFrame({"t": [1]}))


def test_csv_round_trip():
    df = sim.simulate(sim.Rig(7))
    back = data_io.load_csv(io.BytesIO(data_io.to_csv_bytes(df)))
    assert len(back) == len(df) and "pump_on" in back.columns


def test_bad_state_rejected():
    import pandas as pd
    df = pd.DataFrame({"t": range(40), "supply_state": ["RUNNING"] * 40, "q1": 1, "q2": 1, "q3": 1, "q4": 1})
    with pytest.raises(ValueError):
        data_io.load_csv(io.StringIO(df.to_csv(index=False)))


def test_parse_line():
    ok = serial_reader.parse_line('{"t": 12.0, "state": "STABLE", "q": [5.01, 4.98, 4.95, 4.97]}\n')
    assert ok["q4"] == 4.97 and ok["supply_state"] == "STABLE"
    assert serial_reader.parse_line("garbage") is None
    assert serial_reader.parse_line('{"t": 1, "state": "OFF", "q": [1, 2]}') is None