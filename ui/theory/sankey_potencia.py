# -*- coding: utf-8 -*-
"""
sankey_potencia.py
==================
Power flow chart with native Plotly slider — zero latency.

Responsibilities:
  - Pre-compute N_STEPS slip values and pack horizontal bar frames.
  - JS slider switches frames without Streamlit rerun.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts, core.tim.torque_speed
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme
from core.tim.torque_speed import calc_fluxo_potencia

from ui.theory._shared import _get_mp, _dark


def render_sankey_potencia() -> None:
    """Power flow with native Plotly slider (zero latency).

    go.Sankey does not support Plotly frames; replaced by horizontal bars
    stacked (go.Bar) that represent the same flow and animate normally.
    Pre-computes N_STEPS slip values; JS slider switches frames without rerun.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    N_STEPS = 80
    s_grid  = np.linspace(-0.20, 2.00, N_STEPS)
    nom_idx = int(np.argmin(np.abs(s_grid - 0.05)))

    def _fmt(v: float) -> str:
        av = abs(v)
        return f"{v/1000:.2f} kW" if av >= 1000 else f"{v:.1f} W"

    COL_PIN  = "#4f8ef7"
    COL_CU1  = "#f87171"
    COL_AG   = "#a78bfa"
    COL_CU2  = "#fb923c"
    COL_MEC  = "#34d399"
    COL_OUT  = "#22c55e"

    LABELS = ["P_input", "P_cu1 (stator copper)", "P_ag (air-gap)",
              "P_cu2 (rotor copper)", "P_mec (conv.)", "P_output"]

    def _make_frame_data(s: float):
        fp     = calc_fluxo_potencia(s, mp)
        P_in   = fp["P_in"]
        P_cu1  = fp["P_cu1"]
        P_ag   = fp["P_ag"]
        P_cu2  = fp["P_cu2"]
        P_mec  = fp["P_mec"]
        P_out  = fp["P_out"]
        region = fp["region"]
        eta    = fp["eta"]

        vals   = [abs(P_in), abs(P_cu1), abs(P_ag), abs(P_cu2), abs(P_mec), abs(P_out)]
        cols   = [COL_PIN, COL_CU1, COL_AG, COL_CU2, COL_MEC, COL_OUT]
        txts   = [_fmt(P_in), _fmt(P_cu1), _fmt(P_ag),
                  _fmt(P_cu2), _fmt(P_mec), _fmt(P_out)]

        traces = []
        for i, (lbl, val, col, txt) in enumerate(zip(LABELS, vals, cols, txts)):
            traces.append(go.Bar(
                name=lbl,
                x=[val],
                y=["Power"],
                orientation="h",
                marker_color=col,
                text=[txt],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=11, color="#ffffff"),
                hovertemplate=f"{lbl}: {txt}<extra></extra>",
            ))

        # final trace: dynamic title as annotation via invisible scatter
        traces.append(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(opacity=0),
            showlegend=False,
            hoverinfo="skip",
            name=f"{region} | η={eta:.1f}% | s={s:.3f}",
        ))
        return traces, region, eta

    # ── figura base ──────────────────────────────────────────────────────────
    init_traces, region_0, eta_0 = _make_frame_data(s_grid[nom_idx])
    fig = go.Figure(data=init_traces)

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    anim_args = dict(mode="immediate", frame=dict(duration=0, redraw=True),
                     transition=dict(duration=0))

    for i, s in enumerate(s_grid):
        trs, region, eta = _make_frame_data(s)
        frames.append(go.Frame(
            name=str(i),
            data=trs,
            traces=list(range(len(trs))),
        ))
        slider_steps.append(dict(
            method="animate",
            label=f"{s:.2f}",
            args=[[str(i)], anim_args],
        ))

    fig.frames = frames

    fig.update_layout(
        height=260,
        barmode="stack",
        title=dict(
            text=f"Power Flow — {region_0}  |  η = {eta_0:.1f}%  |  s = {s_grid[nom_idx]:.2f}",
            x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=20, r=20, t=55, b=110),
        xaxis=dict(
            title="Power (W)", showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
        ),
        yaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=-0.28,
            font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        sliders=[dict(
            active=nom_idx,
            currentvalue=dict(
                prefix="Slip  s = ",
                visible=True, xanchor="center",
                font=dict(size=13, color=pt["fg"]),
            ),
            y=0, pad=dict(t=45, b=5),
            len=0.92, x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"], bordercolor=pt["grid"],
            tickcolor=pt["fg"], font=dict(color=pt["fg"], size=9),
        )],
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )

    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
