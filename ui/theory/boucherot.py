# -*- coding: utf-8 -*-
"""
boucherot.py
============
Interactive T×s chart with native Plotly slider — Boucherot's theorem.

Responsibilities:
  - Pre-compute N_STEPS T×s curves for an R'₂ grid and pack as Plotly frames.
  - JS slider switches frames on the client without Streamlit rerun.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts, core.tim.torque_speed
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme
from core.tim import _extract_params, _torque_array

from ui.theory._shared import _get_mp, _dark


def render_boucherot() -> None:
    """T×s chart with native Plotly slider (zero latency) — Boucherot's theorem.

    Pre-computes N_STEPS curves for the R'₂ grid and packs them as Plotly frames.
    The JS slider moves between frames on the client, without Streamlit rerun.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2_nom, X2, Xm, ws_mec, ns = _extract_params(mp)

    # Thevenin
    Zth  = (1j * Xm * (R1 + 1j * X1)) / (R1 + 1j * (X1 + Xm))
    Rth  = Zth.real
    Xth  = Zth.imag
    Vth  = abs(V1 * 1j * Xm / (R1 + 1j * (X1 + Xm)))
    Tmax = 3.0 * Vth**2 / (2.0 * ws_mec * (Rth + np.sqrt(Rth**2 + (Xth + X2)**2)))

    # R'₂ grid — 60 logarithmic steps between 0.2× and 5× nominal
    N_STEPS = 60
    r2_grid = np.geomspace(R2_nom * 0.2, 3.0, N_STEPS)
    # Initial index: closest nominal value
    nom_idx = int(np.argmin(np.abs(r2_grid - R2_nom)))

    def _make_s_arr(scr: float) -> np.ndarray:
        """Adaptive s grid: high density around s_cr."""
        wing = min(scr * 0.8, 0.15)
        return np.unique(np.concatenate([
            np.linspace(1e-4, max(1e-4, scr - wing), 200),
            np.linspace(max(1e-4, scr - wing), min(1.0, scr + wing), 300),
            np.linspace(min(1.0, scr + wing), 1.0, 100),
            np.linspace(1.001, 2.0, 60),
        ]))

    col_sel  = "#4f8ef7" if dark else "#1d4ed8"
    col_peak = "#f97316"
    col_scr  = "#a78bfa" if dark else "#7c3aed"

    # Initial curve (frame nom_idx)
    r2_init   = r2_grid[nom_idx]
    scr_init  = r2_init / np.sqrt(Rth**2 + (Xth + X2)**2)
    s_arr_i   = _make_s_arr(scr_init)
    Te_init   = _torque_array(s_arr_i, V1, R1, X1, r2_init, X2, Xm, ws_mec)
    peak_idx  = int(np.argmax(Te_init))
    s_peak_i  = float(s_arr_i[peak_idx])
    Te_peak_i = float(Te_init[peak_idx])

    Te_max_plot = float(Tmax) * 1.25

    # ── figura base ──────────────────────────────────────────────────────────
    fig = go.Figure()

    # Trace 0 — main curve (varies per frame)
    fig.add_trace(go.Scatter(
        x=s_arr_i, y=Te_init,
        mode="lines",
        name=f"R'₂ = {r2_init:.3f} Ω",
        line=dict(color=col_sel, width=3),
    ))

    # Trace 1 — marcador no pico
    fig.add_trace(go.Scatter(
        x=[s_peak_i], y=[Te_peak_i],
        mode="markers+text",
        text=[f"T_max = {Te_peak_i:.1f} N·m"],
        textposition="top center",
        textfont=dict(color=col_peak, size=11),
        marker=dict(color=col_peak, size=12, symbol="circle",
                    line=dict(color=pt["paper_bg"], width=2)),
        showlegend=False,
    ))

    # Trace 2 — linha vertical pontilhada descendo do pico ao eixo X
    fig.add_trace(go.Scatter(
        x=[s_peak_i, s_peak_i], y=[0, Te_peak_i],
        mode="lines",
        line=dict(color=col_peak, width=1.5, dash="dot"),
        showlegend=False,
    ))

    # Trace 3 — s_cr marker on axis (y=0) with label
    fig.add_trace(go.Scatter(
        x=[s_peak_i], y=[0],
        mode="markers+text",
        text=[f"s_cr = {s_peak_i:.3f}"],
        textposition="top center",
        textfont=dict(color=col_scr, size=10),
        marker=dict(color=col_scr, size=8, symbol="triangle-up"),
        showlegend=False,
    ))

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    for i, r2 in enumerate(r2_grid):
        scr   = r2 / np.sqrt(Rth**2 + (Xth + X2)**2)
        s_f   = _make_s_arr(scr)
        Te    = _torque_array(s_f, V1, R1, X1, r2, X2, Xm, ws_mec)
        pidx  = int(np.argmax(Te))
        sp    = float(s_f[pidx])
        Tp    = float(Te[pidx])
        label = f"{r2:.3f}"
        frames.append(go.Frame(
            name=str(i),
            data=[
                go.Scatter(x=s_f, y=Te, name=f"R'₂ = {r2:.3f} Ω"),
                go.Scatter(x=[sp], y=[Tp],
                           text=[f"T_max = {Tp:.1f} N·m"],
                           textposition="top center"),
                go.Scatter(x=[sp, sp], y=[0, Tp]),
                go.Scatter(x=[sp], y=[0],
                           text=[f"s_cr = {sp:.3f}"]),
            ],
            traces=[0, 1, 2, 3],
        ))
        slider_steps.append(dict(
            method="animate",
            label=label,
            args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                 transition=dict(duration=0))],
        ))

    fig.frames = frames

    # ── layout com slider JS ─────────────────────────────────────────────────
    fig.update_layout(
        height=460,
        title=dict(text="T×s Curve — Boucherot's Theorem (T_max invariant with R'₂)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=130),
        xaxis=dict(title="Slip s", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]), range=[0, 2.0],
                   zeroline=True, zerolinecolor=pt["grid"]),
        yaxis=dict(title="Torque (N·m)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   range=[0, Te_max_plot]),
        showlegend=True,
        legend=dict(
            x=0.98, y=0.98, xanchor="right", yanchor="top",
            font=dict(size=10, color=pt["fg"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        sliders=[dict(
            active=nom_idx,
            currentvalue=dict(
                prefix="R'₂ = ",
                suffix=" Ω",
                visible=True,
                xanchor="center",
                font=dict(size=13, color=pt["fg"]),
            ),
            y=0,
            pad=dict(t=55, b=10),
            len=0.92,
            x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"],
            bordercolor=pt["grid"],
            tickcolor=pt["fg"],
            font=dict(color=pt["fg"], size=9),
        )],
        # hidden updatemenus required for slider animate to work
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )

    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
