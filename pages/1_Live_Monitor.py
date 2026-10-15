"""Live Monitor page.  Owner: Member C."""
import time

import streamlit as st

from tiramic import data_io, detection as det, plots, simulator as sim, ui

st.set_page_config(page_title="Live Monitor", page_icon="💧", layout="wide")
st.title("💧 Live Monitor")

STABLE_S = 240
LEAK_START = sim.stable_window(STABLE_S)[0] + 60   # 130 s

# ------------------------------------------------------------------ sidebar: data source
with st.sidebar:
    st.header("Data source")
    source = st.radio("Source", ["Simulator", "Upload CSV"], horizontal=True)
    sig = [source]
    show_truth = False
    if source == "Simulator":
        scenario = st.selectbox("Scenario", ["Single leak", "Normal (no leak)", "Two leaks",
                                             "Stuck meter", "Meter dropout"])
        zone = st.selectbox("Leak zone", [1, 2, 3], index=1)
        size = st.slider("Leak size (L/min)", 0.1, 2.0, 0.6, 0.05)
        zone2 = st.selectbox("Second leak zone", [1, 2, 3], index=2) if scenario == "Two leaks" else 3
        meter = st.selectbox("Faulty meter", [1, 2, 3, 4], index=2) if scenario in ("Stuck meter", "Meter dropout") else 3
        nominal = st.slider("Pump flow (L/min)", 3.5, 6.5, 5.0, 0.1)
        noise_scale = st.slider("Meter noise (x normal)", 0.5, 4.0, 1.0, 0.5)
        noise_seed = int(st.number_input("Random seed", 0, 9999, 1))
        show_truth = st.checkbox("Show true leak on charts (simulation only)", True)
        sig += [scenario, zone, size, zone2, meter, nominal, noise_scale, noise_seed]
    else:
        base_file = st.file_uploader("1) No-leak baseline CSV", type="csv", key="base_csv")
        test_file = st.file_uploader("2) Test CSV", type="csv", key="test_csv")
        sig += [getattr(base_file, "name", None), getattr(test_file, "name", None)]

# ------------------------------------------------------------------ build the analysed table
if source == "Simulator":
    leaks, faults = (), ()
    if scenario == "Single leak":
        leaks = ((zone, size, LEAK_START, 1e9),)
    elif scenario == "Two leaks":
        leaks = ((zone, size, LEAK_START, 1e9), (zone2, size, LEAK_START + 40, 1e9))
    elif scenario == "Stuck meter":
        faults = ((meter, "stuck", 150.0, 1e9),)
    elif scenario == "Meter dropout":
        faults = ((meter, "dropout", 150.0, 1e9),)
    ui.sim_banner()
    res = ui.run_scenario(7, leaks, faults, STABLE_S, nominal, noise_seed, noise_scale)
else:
    if base_file is None or test_file is None:
        st.info("Upload a no-leak baseline CSV and a test CSV (columns: t, supply_state, q1, q2, q3, q4). "
                "Use the Data Lab page to check your files first.")
        st.stop()
    try:
        baseline = det.fit_baseline(data_io.load_csv(base_file))
        res = det.analyse(data_io.load_csv(test_file), baseline)
    except ValueError as err:
        st.error(f"Could not read the files: {err}")
        st.stop()
    st.info("Showing UPLOADED data. The baseline was learned from your no-leak file.")

n = len(res)

# ------------------------------------------------------------------ playback state (must be set BEFORE the slider)
if st.session_state.get("sig") != sig:
    st.session_state.sig = sig
    st.session_state.t_idx = 0
    st.session_state.playing = False
st.session_state.setdefault("t_idx", 0)
st.session_state.setdefault("playing", False)
st.session_state.t_idx = min(st.session_state.t_idx, n - 1)

with st.sidebar:
    st.header("Playback")
    speed = st.select_slider("Seconds of data per tick", [1, 2, 5, 10], value=2)
    b1, b2 = st.columns(2)
    if b1.button("Play / Pause"):
        st.session_state.playing = not st.session_state.playing
    if b2.button("Reset"):
        st.session_state.t_idx = 0
        st.session_state.playing = False
    if st.button("Jump to first alarm"):
        hit = res.index[res["status"].isin(["LEAK", "MULTIPLE", "SENSOR_FAULT"])]
        if len(hit):
            st.session_state.t_idx = int(hit[0])

if st.session_state.playing:
    st.session_state.t_idx = min(st.session_state.t_idx + speed, n - 1)
    if st.session_state.t_idx >= n - 1:
        st.session_state.playing = False

i = st.slider("Time (s)", 0, n - 1, key="t_idx")
row = res.iloc[i]

# ------------------------------------------------------------------ top row: KPIs
suspect = row["suspect_zone"]
suspect_txt = "-" if suspect == 0 else ("several" if suspect == -1 else f"Zone {suspect}")
healthy = sum(bool(row[f"ok_F{k}"]) for k in (1, 2, 3, 4))
k = st.columns(6)
k[0].metric("Status", ui.STATUS_LABEL[row["status"]])
k[1].metric("Supply state", row["supply_state"])
k[2].metric("Suspected section", suspect_txt)
k[3].metric("Confidence", row["confidence"] or "-")
k[4].metric("Estimated loss", f"{row['loss_est_lpm']:.2f} L/min")
k[5].metric("Sensors OK", f"{healthy}/4")

headline = {
    "LEAK": f"Possible leak in {suspect_txt}. Send someone to check that pipe section.",
    "MULTIPLE": "Several zones show abnormal loss. Inspect each flagged zone.",
    "SENSOR_FAULT": "A sensor looks faulty. Zones using it are INCONCLUSIVE until it is fixed.",
    "NORMAL": "All zones are within the healthy range for this pump state.",
    "IDLE": "Pump is off.",
}[row["status"]]
ui.status_box(row["status"], headline)

# ------------------------------------------------------------------ rig picture + reasons
left, right = st.columns([3, 2])
with left:
    st.subheader("Rig status")
    st.plotly_chart(plots.rig_figure(row))
with right:
    st.subheader("Why this result?")
    for line in det.explain(row):
        st.markdown(f"- {line}")

st.plotly_chart(plots.flow_chart(res, i, show_truth))
st.plotly_chart(plots.zone_chart(res, i, show_truth))

st.subheader("Alert log (up to the current time)")
episodes = det.alarm_episodes(res.iloc[: i + 1])
if episodes.empty:
    st.caption("No alerts yet.")
else:
    st.dataframe(episodes.round(2), hide_index=True)

if st.session_state.playing:
    time.sleep(0.5)
    st.rerun()