"""Shared UI helpers for the TIRAMIC dashboard."""

import streamlit as st
from tiramic import simulator


def sim_banner():
    st.info("Simulation mode: Using generated sensor readings, not live hardware data.")


def get_rig(n=7):
    return simulator.Rig(n)