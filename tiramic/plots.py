"""All Plotly figures (no Streamlit code in here).  Owner: Member C."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import config as C

GREEN, RED, AMBER, GREY, BLUE = "#2e9e5b", "#d64545", "#e0a030", "#9aa0a6", "#3b6ea8"
FLOW_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]


def _spans(mask, t):
    """Start/end times of continuous True stretches."""
    spans, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = t[i]
        if not m and start is not None:
            spans.append((start, t[i - 1]))
            start = None
    if start is not None:
        spans.append((start, t[-1]))
    return spans


def rig_figure(row):
    """Schematic of the rig for ONE time step (a row of the analysed DataFrame)."""
    xs = [2.0, 4.5, 7.0, 9.5]
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0.0, x1=0.9, y0=-0.45, y1=0.45, line=dict(color=BLUE), fillcolor="#dce8f5")
    fig.add_annotation(x=0.45, y=0.0, text="TANK<br>+ PUMP", showarrow=False, font=dict(size=11))
    fig.add_shape(type="line", x0=0.9, x1=xs[0], y0=0, y1=0, line=dict(color=GREY, width=8))
    for z in range(3):
        if bool(row[f"alarm{z + 1}"]):
            color = RED
        elif not bool(row[f"trust{z + 1}"]):
            color = AMBER
        elif row["supply_state"] == "OFF":
            color = GREY
        else:
            color = GREEN
        fig.add_shape(type="line", x0=xs[z], x1=xs[z + 1], y0=0, y1=0, line=dict(color=color, width=10))
        fig.add_annotation(x=(xs[z] + xs[z + 1]) / 2, y=0.62, showarrow=False,
                           text=f"<b>Zone {z + 1}</b><br>excess {row[f'ex{z + 1}']:+.2f} L/min",
                           font=dict(size=12, color=color))
    for k in range(4):
        ok = bool(row[f"ok_F{k + 1}"])
        q = row[f"q{k + 1}"]
        label = "no data" if np.isnan(q) else f"{q:.2f} L/min"
        fig.add_trace(go.Scatter(x=[xs[k]], y=[0], mode="markers",
                                 marker=dict(symbol="square", size=26, color="white",
                                             line=dict(color=GREEN if ok else RED, width=3)),
                                 hoverinfo="skip", showlegend=False))
        fig.add_annotation(x=xs[k], y=0, text=f"<b>F{k + 1}</b>", showarrow=False, font=dict(size=11))
        fig.add_annotation(x=xs[k], y=-0.5, showarrow=False, text=label,
                           font=dict(size=12, color=GREEN if ok else RED))
    fig.update_xaxes(visible=False, range=[-0.2, 10.3])
    fig.update_yaxes(visible=False, range=[-1.0, 1.1])
    fig.update_layout(height=260, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor="rgba(0,0,0,0)")
    return fig


def flow_chart(res, i, show_truth=True):
    """Q1..Q4 up to time step i."""
    r = res.iloc[: i + 1]
    fig = go.Figure()
    if show_truth and "true_zones" in res.columns:
        for a, b in _spans((res["true_zones"] != "none").to_numpy(), res["t"].to_numpy()):
            fig.add_vrect(x0=a, x1=b, fillcolor=RED, opacity=0.08, line_width=0)
    for k in range(4):
        fig.add_trace(go.Scatter(x=r["t"], y=r[f"q{k + 1}"], name=f"F{k + 1}",
                                 line=dict(color=FLOW_COLORS[k], width=2)))
    fig.update_xaxes(title="time (s)", range=[0, res["t"].iloc[-1]])
    fig.update_yaxes(title="flow (L/min)")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="Flow at the four meters",
                      legend=dict(orientation="h", y=1.15))
    return fig


def zone_chart(res, i, show_truth=True):
    """Smoothed excess loss per zone with its alarm threshold, up to time step i."""
    r = res.iloc[: i + 1]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=C.ZONE_NAMES)
    for z in range(1, 4):
        fig.add_trace(go.Scatter(x=r["t"], y=r[f"ex{z}"], name=f"excess zone {z}",
                                 line=dict(color=BLUE), showlegend=(z == 1)), row=z, col=1)
        fig.add_trace(go.Scatter(x=r["t"], y=r[f"thr{z}"], name="alarm threshold",
                                 line=dict(color=RED, dash="dash"), showlegend=(z == 1)), row=z, col=1)
        if show_truth and "true_zones" in res.columns:
            m = res["true_zones"].astype(str).str.contains(str(z)).to_numpy()
            for a, b in _spans(m, res["t"].to_numpy()):
                fig.add_vrect(x0=a, x1=b, fillcolor=RED, opacity=0.08, line_width=0, row=z, col=1)
        fig.update_yaxes(title_text="L/min", row=z, col=1)
    fig.update_xaxes(range=[0, res["t"].iloc[-1]])
    fig.update_xaxes(title_text="time (s)", row=3, col=1)
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=1.08))
    return fig


def repair_chart(res, zone, t_repair):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res["t"], y=res[f"ex{zone}"], name="excess loss", line=dict(color=BLUE)))
    fig.add_trace(go.Scatter(x=res["t"], y=res[f"thr{zone}"], name="alarm threshold",
                             line=dict(color=RED, dash="dash")))
    fig.add_vline(x=t_repair, line_dash="dot", line_color=GREEN, annotation_text="repair done")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_title="time (s)", yaxis_title="L/min", title=f"{C.ZONE_NAMES[zone - 1]}: loss before / after repair")
    return fig


def heatmap_fig(pivot):
    fig = go.Figure(go.Heatmap(z=pivot.to_numpy() * 100, x=[str(c) for c in pivot.columns],
                               y=[f"Zone {i}" for i in pivot.index], colorscale="RdYlGn", zmin=0, zmax=100,
                               text=np.round(pivot.to_numpy() * 100).astype(int), texttemplate="%{text}%",
                               colorbar=dict(title="detected %")))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), title="Detection rate by zone and leak size",
                      xaxis_title="leak size (L/min)")
    return fig


def rate_vs_size_fig(tables):
    """tables = {'TIRAMIC': by_size df, 'Naive': by_size df}"""
    fig = go.Figure()
    for name, t in tables.items():
        fig.add_trace(go.Scatter(x=t["size_lpm"], y=t["detection_rate"] * 100, mode="lines+markers", name=name))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="Detection rate vs leak size",
                      xaxis_title="leak size (L/min)", yaxis_title="detected (%)", yaxis_range=[0, 105])
    return fig


def delay_fig(table):
    fig = go.Figure(go.Bar(x=table["size_lpm"].astype(str), y=table["median_delay_s"], marker_color=BLUE))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="Median detection delay",
                      xaxis_title="leak size (L/min)", yaxis_title="seconds")
    return fig


def confidence_fig(table):
    fig = go.Figure(go.Bar(x=table["confidence"], y=table["zone_accuracy"] * 100,
                           text=table["alarms"].astype(str) + " alarms", marker_color=[GREEN, AMBER, RED][: len(table)]))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="Zone accuracy by confidence level",
                      yaxis_title="correct zone (%)", yaxis_range=[0, 105])
    return fig