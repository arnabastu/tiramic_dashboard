"""System Efficiency page.  Owner: Member B (numbers) with Member C (layout)."""
import numpy as np
import pandas as pd
import streamlit as st

from tiramic import metrics, plots, ui

st.set_page_config(page_title="System Efficiency", page_icon="📊", layout="wide")
st.title("📊 System Efficiency")
ui.sim_banner()

SIZES = [0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0]

with st.sidebar:
    st.header("Benchmark settings")
    sizes = tuple(st.multiselect("Leak sizes to test (L/min)", SIZES, default=SIZES[1:7]))
    repeats = st.slider("Repeats per zone and size", 3, 10, 5)
    noise_scale = st.slider("Meter noise (x normal)", 0.5, 4.0, 1.0, 0.5,
                            help="Raise this to see how noisier, cheaper meters hurt the system.")
    noleak_runs = st.slider("No-leak pump cycles (for false alarms)", 5, 30, 10)
    st.caption("A 'cycle' is one start-up, run and shut-down (about 6 minutes of data).")

if not sizes:
    st.info("Pick at least one leak size in the sidebar.")
    st.stop()


@st.cache_data(show_spinner="Running simulated trials...")
def benchmark(sizes, repeats, noise_scale, noleak_runs):
    rig = ui.get_rig(7)
    base = ui.get_baseline(7, noise_scale)
    trials = metrics.run_trials(rig, base, sizes=sizes, repeats=repeats, noise_scale=noise_scale)
    noleak = metrics.run_noleak(rig, base, runs=noleak_runs, noise_scale=noise_scale)
    return trials, noleak


trials, noleak = benchmark(sizes, repeats, noise_scale, noleak_runs)
summary = metrics.summarise(trials, noleak)
me, naive = summary["TIRAMIC"], summary["Naive"]


def pct(x):
    return "-" if x is None or np.isnan(x) else f"{100 * x:.0f}%"


def num(x, unit=""):
    return "-" if x is None or np.isnan(x) else f"{x:.2f}{unit}"


st.subheader("Headline numbers (TIRAMIC, simulated)")
k = st.columns(6)
k[0].metric("Leak trials", me["trials"])
k[1].metric("Detection rate", pct(me["detection_rate"]))
k[2].metric("Zone accuracy", pct(me["zone_accuracy"]))
k[3].metric("Median delay", num(me["median_delay_s"], " s"))
k[4].metric("False alarms / hour", num(me["false_alarms_per_hour"]))
k[5].metric("Smallest reliable leak",
            "not reached" if me["min_detectable_lpm"] is None else f"{me['min_detectable_lpm']} L/min")

st.subheader("TIRAMIC vs a naive detector")
st.caption("Naive = alarm when Q1 - Q4 exceeds a fixed 0.3 L/min; no baselines, no supply states, no sensor "
           "checks; zone guessed from the largest raw difference.")
table = pd.DataFrame({
    "Metric": ["Detection rate", "Zone accuracy (of detected)", "Median delay (s)",
               "False alarms per hour", "Smallest reliably detected leak (L/min)"],
    "TIRAMIC": [pct(me["detection_rate"]), pct(me["zone_accuracy"]), num(me["median_delay_s"]),
                num(me["false_alarms_per_hour"]), str(me["min_detectable_lpm"] or "not reached")],
    "Naive": [pct(naive["detection_rate"]), pct(naive["zone_accuracy"]), num(naive["median_delay_s"]),
              num(naive["false_alarms_per_hour"]), str(naive["min_detectable_lpm"] or "not reached")],
})
st.dataframe(table, hide_index=True)

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(plots.rate_vs_size_fig({"TIRAMIC": metrics.by_size(trials, "TIRAMIC"),
                                            "Naive": metrics.by_size(trials, "Naive")}))
with c2:
    st.plotly_chart(plots.delay_fig(metrics.by_size(trials, "TIRAMIC")))

c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(plots.heatmap_fig(metrics.heatmap_table(trials, "TIRAMIC")))
with c4:
    conf = metrics.confidence_table(trials)
    if conf.empty:
        st.info("No alarms to analyse.")
    else:
        st.plotly_chart(plots.confidence_fig(conf))

with st.expander("How to read this page"):
    st.markdown(
        """
- **Detection rate**: share of leak trials where the alarm fired during the stable run.
- **Zone accuracy**: of the detected leaks, how many pointed at the correct zone.
- **False alarms / hour**: alarms during healthy pump cycles with no leak.
- **Smallest reliable leak**: smallest size (and every larger size) detected in at least 90% of trials.
- **Confidence chart**: a useful confidence label means High results are right more often than Low ones.
- Zone accuracy is near 100% here because the simulated rig has no branches or unmetered demand.
  Expect lower numbers on the real rig, and report them.
- Move the **noise** slider up to see the smallest reliable leak grow. That is what cheap meters do.
"""
    )

with st.expander("Replace with REAL rig results (after validation)"):
    st.markdown("Upload your trial log with columns: `zone, size_lpm, detected, zone_correct, delay_s, confidence`.")
    up = st.file_uploader("Real trials CSV", type="csv", key="real_trials")
    hours = st.number_input("Hours of no-leak testing", 0.0, 1000.0, 1.0, 0.25)
    false_alarms = st.number_input("False alarms in that time", 0, 1000, 0)
    if up is not None:
        real = pd.read_csv(up)
        needed = {"zone", "size_lpm", "detected", "zone_correct", "delay_s", "confidence"}
        if not needed.issubset(real.columns):
            st.error(f"Missing columns: {sorted(needed - set(real.columns))}")
        else:
            real["detector"] = "TIRAMIC"
            real["confidence"] = real["confidence"].fillna("")
            r = metrics.summarise(real, {"hours": hours, "TIRAMIC": false_alarms})["TIRAMIC"]
            st.success("REAL measured results")
            kk = st.columns(5)
            kk[0].metric("Trials", r["trials"])
            kk[1].metric("Detection rate", pct(r["detection_rate"]))
            kk[2].metric("Zone accuracy", pct(r["zone_accuracy"]))
            kk[3].metric("Median delay", num(r["median_delay_s"], " s"))
            kk[4].metric("False alarms / hour", num(r["false_alarms_per_hour"]))