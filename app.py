"""Home page.  Run the whole dashboard with:  streamlit run app.py"""
import streamlit as st

from tiramic import ui

st.set_page_config(page_title="TIRAMIC Dashboard", page_icon="💧", layout="wide")

st.title("💧 TIRAMIC 2.0 Dashboard")
st.caption("Zone-level leak detection for a three-zone pipe rig  |  SIH26254")
ui.sim_banner()

st.markdown(
    """
**What this dashboard does:** four flow meters sit along one pipe. Each pair of neighbouring meters
bounds one *zone*. If a zone loses water, the flow drops between its two meters. The dashboard
compares each zone with what is *normal for the current pump state*, flags the zone that is losing
water, says how sure it is, checks the sensors themselves, and proves a repair worked.
"""
)

c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("Operate")
    st.page_link("pages/1_Live_Monitor.py", label="Live Monitor", icon="💧")
    st.page_link("pages/3_Repair_Proof.py", label="Repair Proof", icon="🔧")
with c2:
    st.subheader("Prove")
    st.page_link("pages/2_System_Efficiency.py", label="System Efficiency", icon="📊")
with c3:
    st.subheader("Prepare")
    st.page_link("pages/4_Data_Lab.py", label="Data Lab", icon="🧪")
    st.page_link("pages/5_Scale_and_Cost.py", label="Scale and Cost", icon="📈")

with st.expander("Honest-claims rules for the demo", expanded=True):
    st.markdown(
        """
1. Anything on a page marked **SIMULATED** is model output, not rig performance.
2. The rig localises to a **zone (pipe section)**, not an exact point.
3. Report the **smallest leak** the real meters can detect, even if it is bigger than hoped.
4. Show failures and limits next to successes.
"""
    )