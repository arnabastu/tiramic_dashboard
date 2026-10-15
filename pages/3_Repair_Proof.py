"""Repair Proof page.  Owner: Member C."""
import streamlit as st

from tiramic import config as C, detection as det, plots, simulator as sim, ui

st.set_page_config(page_title="Repair Proof", page_icon="🔧", layout="wide")
st.title("🔧 Repair Proof")
ui.sim_banner()
st.write("After a repair, compare the zone's loss **before** and **after** at similar pump conditions.")

STABLE_S = 240
with st.sidebar:
    st.header("Scenario")
    zone = st.selectbox("Leaking zone", [1, 2, 3], index=1)
    size = st.slider("Leak size (L/min)", 0.2, 2.0, 0.8, 0.05)
    fixed = st.checkbox("Repair actually works", True,
                        help="Untick to simulate a repair that did NOT stop the leak.")
    t_repair = st.slider("Repair time (s)", 190, 260, 230)
    seed = int(st.number_input("Random seed", 0, 9999, 3))

start = sim.stable_window(STABLE_S)[0] + 60
leaks = ((zone, size, start, t_repair if fixed else 1e9),)
res = ui.run_scenario(7, leaks, (), STABLE_S, 5.0, seed, 1.0)
proof = det.repair_proof(res, zone, t_repair)

k = st.columns(4)
k[0].metric("Loss before repair", f"{proof['pre_lpm']:.2f} L/min")
k[1].metric("Loss after repair", f"{proof['post_lpm']:.2f} L/min")
k[2].metric("Reduction", f"{proof['reduction_pct']:.0f}%" if proof["reduction_pct"] == proof["reduction_pct"] else "-")
k[3].metric("Verdict", {True: "REPAIR VERIFIED", False: "NOT CONFIRMED", None: "NO DATA"}[proof["verified"]])

if proof["verified"] is True:
    st.success(proof["note"], icon="✅")
elif proof["verified"] is False:
    st.error(proof["note"], icon="🚨")
else:
    st.info(proof["note"])

st.plotly_chart(plots.repair_chart(res, zone, t_repair))

if proof["pre_lpm"] == proof["pre_lpm"]:
    per_day = proof["pre_lpm"] * 60 * 24
    st.caption(f"If this leak ran all day at {proof['pre_lpm']:.2f} L/min it would waste about "
               f"{per_day:,.0f} litres per day (simple arithmetic: L/min x 60 x 24).")