
"""Scale and Cost page.   Owner: Member A."""
import math

import streamlit as st


st.set_page_config(page_title="Scale and Cost", page_icon="📈", layout="wide")
st.title("📈 Scale and Cost")
st.info(
    "PLANNING CALCULATOR. Every default below is an assumption. Replace each one with a real quote or "
    "measurement before showing these numbers to judges.",
    icon="ℹ️",
)


left, right = st.columns(2)
with left:
    st.subheader("Village network")
    km = st.number_input("Pipe length to monitor (km)", 0.5, 200.0, 5.0, 0.5)
    zone_len = st.number_input("Length of one monitored zone (m)", 100, 5000, 500, 50)
    households = st.number_input("Households served", 50, 100000, 800, 50)
    persons = st.number_input("People per household", 1, 12, 5)
    lpcd = st.number_input("Supply per person per day (litres)", 20, 300, 55)
    loss_pct = st.slider("Share of supplied water currently lost (%)", 5, 60, 30)
    recover_pct = st.slider("Share of that loss recovered through faster repair (%)", 5, 80, 25)
    price = st.number_input("Value of water (Rs per 1000 litres)", 1.0, 200.0, 10.0)
with right:
    st.subheader("Cost per monitoring point (Rs)")
    meter = st.number_input("Flow meter (field grade)", 100, 100000, 1500, 100)
    node = st.number_input("Node electronics + enclosure + wireless module", 100, 50000, 1500, 100)
    install = st.number_input("Installation per point", 0, 50000, 1000, 100)
    gateway = st.number_input("Gateway (one per 15 points)", 0, 100000, 6000, 500)


zones = math.ceil(km * 1000 / zone_len)
points = zones + 1                        # one meter per zone boundary on a single line
gateways = math.ceil(points / 15)
capex = points * (meter + node + install) + gateways * gateway


supplied_l_day = households * persons * lpcd
lost_l_day = supplied_l_day * loss_pct / 100
recovered_l_day = lost_l_day * recover_pct / 100
value_year = recovered_l_day * 365 / 1000 * price
payback_months = capex / (value_year / 12) if value_year > 0 else float("inf")


st.subheader("Result")
k = st.columns(5)
k[0].metric("Zones", zones)
k[1].metric("Monitoring points", points)
k[2].metric("Total cost", f"Rs {capex:,.0f}")
k[3].metric("Cost per km", f"Rs {capex / km:,.0f}")
k[4].metric("Payback", "n/a" if math.isinf(payback_months) else f"{payback_months:.1f} months")
st.caption(
    f"Water supplied about {supplied_l_day:,.0f} L/day; lost about {lost_l_day:,.0f} L/day; "
    f"recovered about {recovered_l_day:,.0f} L/day, worth about Rs {value_year:,.0f} per year."
)
st.warning(
    "Branched networks and house connections need extra meters or a hydraulic model. "
    "This estimate covers a single main line only.",
    icon="⚠️",
)


st.subheader("Battery life of one wireless node")
b = st.columns(3)
cap = b[0].number_input("Battery capacity (mAh)", 500, 20000, 3000, 500)
avg = b[1].number_input(
    "Average current (mA)",
    0.05,
    50.0,
    1.0,
    0.05,
    help="Measure this with a multimeter or power profiler. 1.0 is a placeholder.",
)
derate = b[2].slider("Usable fraction of capacity (%)", 40, 100, 70)
days = cap * derate / 100 / avg / 24
st.metric("Estimated battery life", f"{days:,.0f} days    ({days / 365:.1f} years)")
