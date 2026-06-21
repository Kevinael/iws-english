# -*- coding: utf-8 -*-
"""
sankey_power.py
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
from core.tim import calc_power_flow

from ui.theory._shared import _get_mp, _dark


def render_sankey_power() -> None:
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

    # One horizontal bar per quantity, each on its own y-row, top → bottom in
    # flow order. Plotly draws categorical y-axes bottom-up, so the list is
    # reversed when assigned to keep P_input at the top.
    LABELS = ["P_input", "P_cu1 (stator copper)", "P_ag (air-gap)",
              "P_cu2 (rotor copper)", "P_mec (conv.)", "P_output"]
    COLS   = [COL_PIN, COL_CU1, COL_AG, COL_CU2, COL_MEC, COL_OUT]
    Y_ORDER = LABELS[::-1]  # category order (bottom-up) → P_input ends up on top

    def _make_bar(s: float) -> go.Bar:
        """Single horizontal Bar trace with signed power values (one row each)."""
        fp = calc_power_flow(s, mp)
        vals = [fp["P_in"], fp["P_cu1"], fp["P_ag"],
                fp["P_cu2"], fp["P_mec"], fp["P_out"]]
        txts = [_fmt(v) for v in vals]
        return go.Bar(
            x=vals,
            y=LABELS,
            orientation="h",
            marker_color=COLS,
            text=txts,
            textposition="outside",
            textfont=dict(size=11, color=pt["fg"]),
            cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra></extra>",
            showlegend=False,
        )

    def _x_range(s: float) -> list[float]:
        """X-axis range that follows the operating point (signed powers).

        Negative powers (generator / braking) require the axis to extend left;
        a 12% pad on each side leaves room for the outside text labels.
        """
        fp = calc_power_flow(s, mp)
        vals = [fp["P_in"], fp["P_cu1"], fp["P_ag"],
                fp["P_cu2"], fp["P_mec"], fp["P_out"]]
        lo, hi = min(vals + [0.0]), max(vals + [0.0])
        span = max(hi - lo, 1.0)
        pad  = 0.18 * span  # wider on the high side for outside labels
        return [lo - 0.05 * span, hi + pad]

    def _title(s: float) -> str:
        fp = calc_power_flow(s, mp)
        return (f"Power Flow — {fp['region']}  |  η = {fp['eta']:.1f}%  "
                f"|  s = {s:.2f}")

    # ── base figure ────────────────────────────────────────────────────────────
    s0  = float(s_grid[nom_idx])
    fig = go.Figure(data=[_make_bar(s0)])

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    anim_args = dict(mode="immediate", frame=dict(duration=0, redraw=True),
                     transition=dict(duration=0))

    for i, s in enumerate(s_grid):
        frames.append(go.Frame(
            name=str(i),
            data=[_make_bar(float(s))],
            layout=go.Layout(
                xaxis=dict(range=_x_range(float(s))),
                title=dict(text=_title(float(s))),
            ),
        ))
        slider_steps.append(dict(
            method="animate",
            label=f"{s:.2f}",
            args=[[str(i)], anim_args],
        ))

    fig.frames = frames

    fig.update_layout(
        height=300,
        title=dict(
            text=_title(s0),
            x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=20, r=20, t=55, b=90),
        xaxis=dict(
            title="Power (W)", showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
            range=_x_range(s0), zeroline=True, zerolinecolor=pt["grid"],
        ),
        yaxis=dict(
            showticklabels=True, showgrid=False,
            categoryorder="array", categoryarray=Y_ORDER,
            tickfont=dict(size=10, color=pt["fg"]),
        ),
        showlegend=False,
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
