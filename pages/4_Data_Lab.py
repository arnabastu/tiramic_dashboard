"""Data Lab page.   Owner: Member A."""
import streamlit as st

from tiramic import data_io, serial_reader, simulator as sim, ui


st.set_page_config(page_title="Data Lab", page_icon="🧪", layout="wide")
st.title("Data Lab")

tab1, tab2, tab3 = st.tabs(["Generate simulated data", "Check a CSV", "Record from the ESP32"])


with tab1:
    ui.sim_banner()
    c = st.columns(4)
    zone = c[0].selectbox("Leak zone (0 = none)", [0, 1, 2, 3], index=2)
    size = c[1].slider("Leak size (L/min)", 0.1, 2.0, 0.6, 0.05)
    noise_scale = c[2].slider("Meter noise (x normal)", 0.5, 4.0, 1.0, 0.5)
    seed = int(c[3].number_input("Random seed", 0, 9999, 1))
    rig = ui.get_rig(7)
    leaks = [sim.example_leak(zone,85,size)] if zone else []
    df = sim.simulate(rig, leaks, noise_seed=seed, noise_scale=noise_scale)
    truth = st.checkbox("Include ground-truth columns in the download", False)
    st.dataframe(df.head(60), hide_index=True)
    st.download_button(
        "Download CSV",
        data_io.to_csv_bytes(df, truth),
        file_name="simulated_run.csv",
        mime="text/csv",
    )
    st.line_chart(df.set_index("t")[["q1", "q2", "q3", "q4"]])


with tab2:
    st.write("Check that a CSV follows the team contract before using it anywhere else.")
    st.code("t,supply_state,q1,q2,q3,q4\n0,OFF,0,0,0,0\n21,STARTUP,0.54,0.02,0,0", language="text")
    up = st.file_uploader("CSV to check", type="csv", key="check_csv")
    if up is not None:
        try:
            data = data_io.load_csv(up)
        except ValueError as err:
            st.error(str(err))
        else:
            st.success(f"File is valid: {len(data)} rows, {data['t'].iloc[-1] - data['t'].iloc[0]:.0f} s long.")
            st.dataframe(data.head(30), hide_index=True)
            st.line_chart(data.set_index("t")[["q1", "q2", "q3", "q4"]])


with tab3:
    st.write("The ESP32 must print one JSON line per second:")
    st.code('{"t": 12.0, "state": "STABLE", "q": [5.01, 4.98, 4.95, 4.97]}', language="json")
    port = st.text_input(
        "Serial port",
        value="COM3",
        help="Windows: COM3. Mac: /dev/cu.usbserial-XXXX. Linux: /dev/ttyUSB0",
    )
    seconds = st.number_input("Record for (seconds)", 10, 3600, 60)
    out = st.text_input("Save as", value="data/recorded_run.csv")
    if st.button("Start recording"):
        try:
            with st.spinner(f"Recording {seconds} s from {port} ..."):
                rows = serial_reader.record_serial(port, seconds, out)
            st.success(f"Saved {rows} rows to {out}")
        except Exception as err:    # missing pyserial, wrong port, permission, folder missing ...
            st.error(f"Recording failed: {err}")
