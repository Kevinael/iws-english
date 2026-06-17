# -*- coding: utf-8 -*-
"""
park_dinamico.py
================
Plotly animation of Clarke/Park transform — rotating vector plane + time series.

Responsibilities:
  - Build cached Plotly frames animation for αβ, dq and rotor reference frames.
  - Render radio selector and Play/Pause controls.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ui.theory._shared import _dark


@st.cache_data(show_spinner=False)
def _build_fig_park(ref: str, dark: bool) -> tuple[go.Figure, str]:
    """Plotly frames animation of Clarke/Park transform — vector plane + time series."""
    from plotly.subplots import make_subplots

    bg_hex   = "#151a24" if dark else "#ffffff"
    fg_hex   = "#e5e7eb" if dark else "#111111"
    grid_hex = "#2a2a3a" if dark else "#cccccc"
    col_a    = "#4f8ef7" if dark else "#1d4ed8"
    col_b    = "#f87171" if dark else "#dc2626"
    col_vec  = "#f97316"

    s_typ    = 0.5
    n_cycles = round(1.0 / s_typ) if ref == "rotor" else 1
    N        = 60 * n_cycles
    t        = np.linspace(0.0, float(n_cycles), N, endpoint=False)
    th_e     = 2.0 * np.pi * t

    Vs_a = np.cos(th_e)
    Vs_b = np.sin(th_e)

    if ref == "dq":
        Vx = np.zeros(N)
        Vz = np.ones(N)
        lbl_x = "Vds  (direct axis)"
        lbl_z = "Vqs  (quadrature axis)"
        titulo = "Park — dq reference frame (synchronous)"
        desc   = ("In the dq reference frame, the d and q axes rotate at ωe together with the voltage vector (orange). "
                  "Therefore Vqs = constant and Vds = 0 in steady state — the vector appears stationary.")
        modo   = "dq"
        vec_x  = Vs_a
        vec_z  = Vs_b
    elif ref == "rotor":
        th_r = 2.0 * np.pi * s_typ * t
        Vx = np.cos(th_r)
        Vz = np.sin(th_r)
        lbl_x = "Vdr  (direct component — rotor-fixed)"
        lbl_z = "Vqr  (quadrature component)"
        titulo = f"Rotor reference frame — stator vector rotates at s·ωe  (s={s_typ} illustrative)"
        desc   = (f"In the rotor reference frame, the axes rotate at ωr = (1−s)·ωe. "
                  f"The stator voltage vector (orange) oscillates at the slip frequency fs = s·fe. "
                  f"In real motors s ≈ 0.02–0.08; s={s_typ} is used here to make the animation visible.")
        modo   = "rotor"
        vec_x  = Vx
        vec_z  = Vz
    else:
        Vx = Vs_a
        Vz = Vs_b
        lbl_x = "Vα  (horizontal component — stationary axis)"
        lbl_z = "Vβ  (vertical component — 90° from Vα)"
        titulo = "Clarke — αβ reference frame (stationary)"
        desc   = ("In the αβ reference frame, the axes are fixed in space. "
                  "The voltage vector (orange) rotates at ωe: "
                  "Vα and Vβ are sinusoidal with 90° phase shift between them.")
        modo   = "ab"
        vec_x  = Vs_a
        vec_z  = Vs_b

    circ = np.linspace(0, 2 * np.pi, 120)

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.42, 0.58],
        subplot_titles=[titulo, "Time series"],
        horizontal_spacing=0.12,
    )

    # ── Vector plane (col 1) ──────────────────────────────────────────────────
    # Reference circle
    fig.add_trace(go.Scatter(
        x=np.cos(circ), y=np.sin(circ), mode="lines",
        line=dict(color=grid_hex, width=1, dash="dot"),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    # Axis lines
    fig.add_trace(go.Scatter(
        x=[-1.4, 1.4], y=[0, 0], mode="lines",
        line=dict(color=grid_hex, width=0.8),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[-1.4, 1.4], mode="lines",
        line=dict(color=grid_hex, width=0.8),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    # Rotating d-axis (dq only)
    if modo == "dq":
        d_x0, d_y0 = 1.3 * np.cos(th_e[0]), 1.3 * np.sin(th_e[0])
        q_x0, q_y0 = 1.3 * np.cos(th_e[0] + np.pi/2), 1.3 * np.sin(th_e[0] + np.pi/2)
        fig.add_trace(go.Scatter(
            x=[-d_x0, d_x0], y=[-d_y0, d_y0], mode="lines",
            line=dict(color=col_a, width=1.5), name="d-axis", showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=[-q_x0, q_x0], y=[-q_y0, q_y0], mode="lines",
            line=dict(color=col_b, width=1.5), name="q-axis", showlegend=True,
        ), row=1, col=1)
    # Main vector (orange)
    fig.add_trace(go.Scatter(
        x=[0, vec_x[0]], y=[0, vec_z[0]], mode="lines+markers",
        line=dict(color=col_vec, width=3),
        marker=dict(size=[0, 12], color=col_vec, symbol=["circle", "arrow"],
                    angleref="previous"),
        name="V (voltage vector)",
    ), row=1, col=1)
    # α/d projection
    fig.add_trace(go.Scatter(
        x=[vec_x[0]], y=[0], mode="markers",
        marker=dict(color=col_a, size=8), name=lbl_x,
    ), row=1, col=1)
    # β/q projection
    fig.add_trace(go.Scatter(
        x=[0], y=[vec_z[0]], mode="markers",
        marker=dict(color=col_b, size=8), name=lbl_z,
    ), row=1, col=1)

    # ── Time series (col 2) ────────────────────────────────────────────────────
    # Ghost curves (full background)
    fig.add_trace(go.Scatter(
        x=t, y=Vx, mode="lines",
        line=dict(color=col_a, width=1.2, dash="dot"),
        opacity=0.3, showlegend=False, hoverinfo="skip",
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=t, y=Vz, mode="lines",
        line=dict(color=col_b, width=1.2, dash="dot"),
        opacity=0.3, showlegend=False, hoverinfo="skip",
    ), row=1, col=2)
    # Animated traces (grow frame by frame)
    fig.add_trace(go.Scatter(
        x=t[:1], y=Vx[:1], mode="lines",
        line=dict(color=col_a, width=2), showlegend=False,
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=t[:1], y=Vz[:1], mode="lines",
        line=dict(color=col_b, width=2, dash="dash"), showlegend=False,
    ), row=1, col=2)
    # Cursor (current instant marker)
    fig.add_trace(go.Scatter(
        x=[t[0]], y=[Vx[0]], mode="markers",
        marker=dict(color=col_a, size=7), showlegend=False,
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=[t[0]], y=[Vz[0]], mode="markers",
        marker=dict(color=col_b, size=7), showlegend=False,
    ), row=1, col=2)
    # Vertical cursor line
    fig.add_trace(go.Scatter(
        x=[t[0], t[0]], y=[-1.4, 1.4], mode="lines",
        line=dict(color=fg_hex, width=0.8, dash="dot"),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=2)

    # ── Trace indices ─────────────────────────────────────────────────────────
    # col1: 0=circ, 1=axis_h, 2=axis_v, [3=d, 4=q if dq], vec, proj_a, proj_b
    # col2: ghost_a, ghost_b, line_a, line_b, cur_a, cur_b, vline
    if modo == "dq":
        i_vec   = 5
        i_pja   = 6
        i_pjb   = 7
        i_ga    = 8
        i_gb    = 9
        i_la    = 10
        i_lb    = 11
        i_ca    = 12
        i_cb    = 13
        i_vl    = 14
    else:
        i_vec   = 3
        i_pja   = 4
        i_pjb   = 5
        i_ga    = 6
        i_gb    = 7
        i_la    = 8
        i_lb    = 9
        i_ca    = 10
        i_cb    = 11
        i_vl    = 12

    # ── Frames ────────────────────────────────────────────────────────────────
    frames = []
    for i in range(N):
        frame_data = [None] * (i_vl + 1)
        # static traces (circle, axes)
        frame_data[0] = go.Scatter(x=np.cos(circ), y=np.sin(circ))
        frame_data[1] = go.Scatter(x=[-1.4, 1.4], y=[0, 0])
        frame_data[2] = go.Scatter(x=[0, 0], y=[-1.4, 1.4])
        if modo == "dq":
            d_x = 1.3 * np.cos(th_e[i]); d_y = 1.3 * np.sin(th_e[i])
            q_x = 1.3 * np.cos(th_e[i] + np.pi/2); q_y = 1.3 * np.sin(th_e[i] + np.pi/2)
            frame_data[3] = go.Scatter(x=[-d_x, d_x], y=[-d_y, d_y])
            frame_data[4] = go.Scatter(x=[-q_x, q_x], y=[-q_y, q_y])
        frame_data[i_vec] = go.Scatter(x=[0, vec_x[i]], y=[0, vec_z[i]])
        frame_data[i_pja] = go.Scatter(x=[vec_x[i]], y=[0])
        frame_data[i_pjb] = go.Scatter(x=[0], y=[vec_z[i]])
        frame_data[i_ga]  = go.Scatter(x=t, y=Vx)
        frame_data[i_gb]  = go.Scatter(x=t, y=Vz)
        frame_data[i_la]  = go.Scatter(x=t[:i+1], y=Vx[:i+1])
        frame_data[i_lb]  = go.Scatter(x=t[:i+1], y=Vz[:i+1])
        frame_data[i_ca]  = go.Scatter(x=[t[i]], y=[Vx[i]])
        frame_data[i_cb]  = go.Scatter(x=[t[i]], y=[Vz[i]])
        frame_data[i_vl]  = go.Scatter(x=[t[i], t[i]], y=[-1.4, 1.4])
        frames.append(go.Frame(
            data=[d for d in frame_data if d is not None],
            traces=list(range(i_vl + 1)),
            name=str(i),
        ))
    fig.frames = frames

    fig.update_layout(
        height=420,
        paper_bgcolor=bg_hex, plot_bgcolor=bg_hex,
        font=dict(family="Inter, system-ui", size=11, color=fg_hex),
        margin=dict(l=40, r=20, t=55, b=90),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=fg_hex), bgcolor="rgba(0,0,0,0)"),
        updatemenus=[dict(
            type="buttons", showactive=False,
            x=0.5, xanchor="center", y=-0.28,
            buttons=[
                dict(label="▶ Play",
                     method="animate",
                     args=[None, dict(frame=dict(duration=50, redraw=True),
                                      fromcurrent=True, mode="immediate")]),
                dict(label="⏸ Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
            font=dict(color=fg_hex),
            bgcolor=bg_hex,
            bordercolor=grid_hex,
        )],
    )
    fig.update_xaxes(
        range=[-1.5, 1.5], showgrid=False, zeroline=False,
        showticklabels=False, scaleanchor="y", row=1, col=1,
    )
    fig.update_yaxes(
        range=[-1.5, 1.5], showgrid=False, zeroline=False,
        showticklabels=False, row=1, col=1,
    )
    fig.update_xaxes(
        title_text="ωe cycles", showgrid=True, gridcolor=grid_hex,
        range=[0, float(n_cycles)], row=1, col=2,
    )
    fig.update_yaxes(
        title_text="Amplitude (p.u.)", showgrid=True, gridcolor=grid_hex,
        range=[-1.4, 1.4], row=1, col=2,
    )
    fig.update_annotations(font_color=fg_hex)

    return fig, desc


def render_park_dinamico() -> None:
    """Plotly animation of Clarke/Park transform — rotating vector + time series."""
    dark = _dark()

    ref = st.radio(
        "Reference frame",
        options=["dq (synchronous — Park)", "rotor (ωref = ωr)", "αβ (stationary — Clarke)"],
        horizontal=True,
        key="th_park_ref",
    )
    if ref.startswith("dq"):
        ref_key = "dq"
    elif ref.startswith("rotor"):
        ref_key = "rotor"
    else:
        ref_key = "ab"

    fig, desc = _build_fig_park(ref_key, dark)
    st.plotly_chart(fig, config={"displaylogo": False}, width="stretch")
    st.caption(desc)
