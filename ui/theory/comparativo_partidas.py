# -*- coding: utf-8 -*-
"""
comparativo_partidas.py
=======================
Analytical phase current vs. time curves for starting method comparison.

Responsibilities:
  - Render DOL, Y-D and Soft-Starter current envelopes.
  - Allow method selection via Streamlit multiselect.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts, core.tim.torque_speed
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme
from core.tim import _extract_params

from ui.theory._shared import _get_mp, _dark
from ui.theory.tabs._shared import _z2


def render_comparativo_partidas() -> None:
    """Analytical phase current vs. time curves for DOL, Y-D and Soft-Starter."""
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)
    # Impedance at s=1 (starting)
    Z2_start  = _z2(R2, 1.0, X2)
    Zeq_start = (1j * Xm * Z2_start) / (1j * Xm + Z2_start)
    Ztotal    = R1 + 1j * X1 + Zeq_start
    I_dol     = abs(V1 / Ztotal)           # pico de corrente DOL (A)
    # Nominal current: uses s ≈ 0.04
    Z2_nom   = _z2(R2, 0.04, X2)
    Zeq_nom  = (1j * Xm * Z2_nom) / (1j * Xm + Z2_nom)
    Zt_nom   = R1 + 1j * X1 + Zeq_nom
    I_nom    = abs(V1 / Zt_nom)

    # Approximate electrical time constant
    tau_e  = (X1 + Xm * X2 / (Xm + X2)) / (2.0 * np.pi * mp.f * max(R1 + R2, 0.01))
    t_acc  = max(tau_e * 4.0, 0.3)        # time to steady state
    t_max  = t_acc * 2.5

    t = np.linspace(0.0, t_max, 800)

    def _envelope(I_peak, tau):
        """Exponential decay envelope of the current transient."""
        env = I_nom + (I_peak - I_nom) * np.exp(-t / max(tau, 1e-6))
        return np.maximum(env, I_nom)

    # DOL
    i_dol = _envelope(I_dol, tau_e)

    # Y-D: Y phase uses V/√3 → current reduced to 1/3
    t_yd  = t_acc * 0.6          # Y→D switching instant
    i_yd  = np.where(
        t < t_yd,
        _envelope(I_dol / 3.0, tau_e),
        _envelope(I_dol * 0.7, tau_e * 0.5),   # smaller peak in second transient
    )

    # Soft-Starter: voltage ramp from 0 → V over t_ramp
    t_ramp = t_acc * 0.8
    v_ramp = np.clip(t / t_ramp, 0.0, 1.0)
    i_ss   = _envelope(I_dol * v_ramp, tau_e * 0.4) * v_ramp
    i_ss   = np.maximum(i_ss, I_nom * v_ramp)

    # Method selection
    metodos = st.multiselect(
        "Starting methods",
        options=["DOL (Direct)", "Star-Delta (Y-D)", "Soft-Starter"],
        default=["DOL (Direct)", "Star-Delta (Y-D)", "Soft-Starter"],
        key="th_partidas_sel",
    )

    col_dol = "#f87171" if dark else "#dc2626"
    col_yd  = "#4f8ef7" if dark else "#1d4ed8"
    col_ss  = "#34d399" if dark else "#059669"

    fig = go.Figure()

    if "DOL (Direct)" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_dol, mode="lines", name="DOL",
                                 line=dict(color=col_dol, width=2.5)))
    if "Star-Delta (Y-D)" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_yd, mode="lines", name="Y-D",
                                 line=dict(color=col_yd, width=2.5, dash="dash")))
        fig.add_vline(x=t_yd, line_dash="dot", line_color=col_yd, line_width=1,
                      annotation_text="Y→D", annotation_font_color=col_yd)
    if "Soft-Starter" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_ss, mode="lines", name="Soft-Starter",
                                 line=dict(color=col_ss, width=2.5, dash="longdash")))

    # Linha de corrente nominal
    fig.add_hline(y=I_nom, line_dash="dot", line_color=pt["fg"], line_width=1.2,
                  annotation_text=f"I_nom ≈ {I_nom:.1f} A",
                  annotation_font_color=pt["fg"])

    fig.update_layout(
        height=340,
        title=dict(text="Starting Method Comparison — Phase Current (analytical model)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=45),
        xaxis=dict(title="Time (s)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(title="Phase current (A)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
