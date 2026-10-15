"""Streamlit helpers shared by all pages.  Owner: Member C."""
import streamlit as st

from . import detection as det
from . import simulator as sim

DISCLAIMER = ("SIMULATED DATA: these numbers come from a software model of the rig, not from the real "
              "hardware. They show how the dashboard works. Do not present them as measured performance.")

STATUS_LABEL = {
    "IDLE": "Idle (pump off)",
    "NORMAL": "Normal",
    "LEAK": "LEAK",
    "MULTIPLE": "MULTIPLE LEAKS",
    "SENSOR_FAULT": "SENSOR FAULT",
}
BASELINE_RUNS = [(9000, 4.6), (9001, 5.0), (9002, 5.4), (9003, 5.0), (9004, 4.8)]


def sim_banner():
    st.warning(DISCLAIMER, icon="⚠️")


@st.cache_resource
def get_rig(seed: int = 7):
    return sim.Rig(seed)


@st.cache_resource
def get_baseline(seed: int = 7, noise_scale: float = 1.0):
    """Healthy fingerprint learned from five no-leak runs of the simulated rig."""
    rig = get_rig(seed)
    runs = [sim.simulate(rig, noise_seed=ns, nominal=q, noise_scale=noise_scale) for ns, q in BASELINE_RUNS]
    return det.fit_baseline(runs)


@st.cache_data(show_spinner=False)
def run_scenario(rig_seed, leaks, faults, stable_s, nominal, noise_seed, noise_scale=1.0):
    """leaks = ((zone, lpm, start_s, end_s), ...)  faults = ((meter, kind, start_s, end_s), ...)"""
    rig = get_rig(rig_seed)
    leak_objs = [sim.Leak(*x) for x in leaks]
    fault_objs = [sim.SensorFault(*x) for x in faults]
    df = sim.simulate(rig, leak_objs, fault_objs, stable_s, nominal, noise_seed, noise_scale)
    return det.analyse(df, get_baseline(rig_seed, noise_scale))


def status_box(status, text):
    if status in ("LEAK", "MULTIPLE"):
        st.error(text, icon="🚨")
    elif status == "SENSOR_FAULT":
        st.warning(text, icon="🛠️")
    elif status == "NORMAL":
        st.success(text, icon="✅")
    else:
        st.info(text, icon="⏸️")