# -*- coding: utf-8 -*-
"""
plotly_charts_dc.py
===================
Builds interactive Plotly charts for DC machine simulation results,
mirroring plotly_charts.py for visual consistency.

Responsibilities:
  - Build stacked (build_fig_stacked_dc) figures for DCM time-series results.
  - Build side-by-side (build_fig_sidebyside_dc) and overlay
    (build_fig_overlay_dc) multi-trace figures.
  - Build torque-speed (build_fig_torque_speed_dc) characteristic figures.

Relationships:
  Imported by : ui.dc_results
  Imports     : viz.plotly_charts

Extending:
  - To add a new DCM chart type, create build_fig_<type>_dc() here following
    the MIT counterpart convention in viz.plotly_charts.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.tim_charts import _plot_theme, _colors, _TL_COLOR
from viz._chart_base import (
    _build_stacked_base,
    _build_sidebyside_base,
    _build_overlay_base,
)


# ─────────────────────────────────────────────────────────────────────────────
# STACKED CHART
# ─────────────────────────────────────────────────────────────────────────────

def build_fig_stacked_dc(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    decimals: int = 3,
    tl_arr=None,
) -> go.Figure:
    return _build_stacked_base(
        res, var_keys, var_labels, dark, t_events,
        decimals=decimals, tl_arr=tl_arr,
        key_guard=True, tl_label="$T_l$ (N·m)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SIDE-BY-SIDE CHART
# ─────────────────────────────────────────────────────────────────────────────

def build_fig_sidebyside_dc(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    decimals: int = 3,
    ref_list: list | None = None,
    primary_color: str | None = None,
    compact: bool = False,
    tl_arr=None,
) -> list[go.Figure]:
    return _build_sidebyside_base(
        res, var_keys, var_labels, dark, t_events,
        decimals=decimals, ref_list=ref_list, primary_color=primary_color,
        compact=compact, tl_arr=tl_arr,
        key_guard=True, tl_label="$T_l$ (N·m)", showlegend_always=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# OVERLAY CHART
# ─────────────────────────────────────────────────────────────────────────────

def build_fig_overlay_dc(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    decimals: int = 3,
    ref_list: list | None = None,
    primary_color: str | None = None,
    compact: bool = False,
    tl_arr=None,
) -> go.Figure:
    return _build_overlay_base(
        res, var_keys, var_labels, dark, t_events,
        decimals=decimals, ref_list=ref_list, primary_color=primary_color,
        compact=compact, tl_arr=tl_arr,
        key_guard=True, tl_label="$T_l$ (N·m)",
        dual_axis_keys=None, show_title=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TORQUE × SPEED CURVE
# ─────────────────────────────────────────────────────────────────────────────

def build_fig_torque_speed_dc(
    res: dict,
    excitation: str,
    dark: bool,
    ref_list: list | None = None,
) -> go.Figure:
    """Analytical T×ωm curve by excitation type + simulated trajectory + SS point."""
    pt = _plot_theme(dark)

    fig = go.Figure()

    wm_sim = res.get("wm", np.array([]))
    Te_sim = res.get("Te", np.array([]))
    wm_ss  = float(res.get("wm_ss", 0.0))
    Te_ss  = float(res.get("Te_ss", 0.0))

    # Overlay references
    for ref_item in (ref_list or []):
        rr = ref_item.get("res")
        if rr and "wm" in rr and "Te" in rr:
            fig.add_trace(go.Scatter(
                x=rr["wm"], y=rr["Te"], mode="lines",
                name=ref_item.get("label", "Ref"),
                line=dict(color=ref_item.get("color", "#888"), dash=ref_item.get("dash", "dash"),
                          width=1.3),
            ))

    # Dynamic trajectory
    if len(wm_sim) > 0:
        fig.add_trace(go.Scatter(
            x=wm_sim, y=Te_sim, mode="lines",
            name="Dynamic Trajectory",
            line=dict(color=pt["fg"], width=1.2, dash="dot"),
            opacity=0.6,
        ))

    # Analytical steady-state curve
    if len(wm_sim) > 0:
        wm_max = max(float(np.max(np.abs(wm_sim))) * 1.15, abs(wm_ss) * 1.3, 1.0)
        wm_range = np.linspace(0, wm_max, 300)

        if excitation == "series_motor":
            # T = kb² * Va / (Raf * (wm + kb²/Raf)²) — hyperbolic
            pass   # analytical series curve requires additional parameters; omitted here

        fig.add_trace(go.Scatter(
            x=wm_range, y=np.full_like(wm_range, abs(Te_ss)),
            mode="lines", name="Steady State (load)",
            line=dict(color="#6ee7b7", width=1.4, dash="dashdot"),
        ))

    # Steady-state operating point
    fig.add_trace(go.Scatter(
        x=[wm_ss], y=[Te_ss],
        mode="markers", name=f"SS: ω={wm_ss:.2f} rad/s, T={Te_ss:.3f} N·m",
        marker=dict(symbol="star", size=12, color="#f59e0b",
                    line=dict(color=pt["fg"], width=1)),
    ))

    fig.update_layout(
        title=dict(text="Torque × Angular Speed", x=0.5, xanchor="center",
                   font=dict(size=13, color=pt["fg"])),
        xaxis=dict(title="ωm (rad/s)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(title="Te (N·m)", showgrid=True, gridcolor=pt["grid"],
                   zeroline=True, zerolinecolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        height=380,
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=55, r=20, t=55, b=45),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        hovermode="closest",
    )
    return fig
