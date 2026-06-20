# -*- coding: utf-8 -*-
"""
plotly_charts.py
================
Builds interactive Plotly waveform charts for induction-machine simulation
results with dark/light theme support and pre-computed frames for
zero-latency rendering.

Responsibilities:
  - Provide _plot_theme() and _colors() theming helpers for dark/light modes.
  - Build stacked, side-by-side, and overlay multi-trace figures.
  - Pre-compute animation frames to eliminate render lag in Streamlit.

Relationships:
  Imported by : ui.sim_results, core.harmonica_analysis,
                ui.theory_interactive, viz.plotly_charts_dc
  Imports     : (numpy, plotly only)

Extending:
  - To add a new chart layout, create a build_fig_<layout>() function
    following the existing pattern.
"""
from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
from core.constants import N_SYNC_FACTOR, RPM_TO_RAD
from viz._chart_base import (
    _build_stacked_base,
    _build_sidebyside_base,
    _build_overlay_base,
    _plot_theme,
    _colors,
    _TL_COLOR,
)

# Re-export theming symbols so existing callers (plotly_charts_dc, harmonic_analysis)
# that import from viz.tim_charts continue to work without changes.
__all__ = ["_plot_theme", "_colors", "_TL_COLOR"]


def build_fig_stacked(res, var_keys, var_labels, dark, t_events, decimals=2,
                      tl_arr=None) -> go.Figure:
    return _build_stacked_base(
        res, var_keys, var_labels, dark, t_events,
        decimals=decimals, tl_arr=tl_arr,
        key_guard=False, tl_label="TL (N·m)",
    )


def build_fig_sidebyside(res, var_keys, var_labels, dark, t_events, decimals=2,
                         ref_list=None, primary_color=None,
                         compact: bool = False, tl_arr=None) -> list[go.Figure]:
    return _build_sidebyside_base(
        res, var_keys, var_labels, dark, t_events,
        decimals=decimals, ref_list=ref_list, primary_color=primary_color,
        compact=compact, tl_arr=tl_arr,
        key_guard=False, tl_label="TL (N·m)", showlegend_always=False,
    )


def build_fig_overlay(res, var_keys, var_labels, dark, t_events, decimals=2,
                      ref_list=None, primary_color=None,
                      compact: bool = False, tl_arr=None) -> go.Figure:
    return _build_overlay_base(
        res, var_keys, var_labels, dark, t_events,
        decimals=decimals, ref_list=ref_list, primary_color=primary_color,
        compact=compact, tl_arr=tl_arr,
        key_guard=False, tl_label="TL (N·m)",
        dual_axis_keys={"n", "wr"}, show_title=True,
    )


def build_fig_torque_speed(
    res: dict,
    P_nom_kw: float,
    f: float,
    p: int,
    dark: bool = False,
) -> go.Figure:
    """Electromagnetic torque vs. rotor speed.

    Traces the full dynamic trajectory from start-up to steady state and
    overlays nominal design references (synchronous speed and rated torque).

    Args:
        res: solver results dictionary (fields "n" in RPM, "Te" in N·m).
        P_nom_kw: rated mechanical power in kW.
        f: rated frequency in Hz.
        p: number of poles.
        dark: True for dark theme.
    """
    pt = _plot_theme(dark)

    rpm_array = np.asarray(res["n"],  dtype=float)
    te_array  = np.asarray(res["Te"], dtype=float)

    # Discard the first 5 electrical cycles: over this interval Te oscillates
    # violently around wr≈0 (electromagnetic inrush), polluting the T×n trajectory.
    t_array = np.asarray(res.get("t", []), dtype=float)
    if len(t_array) > 1 and f > 0:
        h     = float(t_array[1] - t_array[0])
        n_skip = min(max(0, int(round(5.0 / (f * h)))), len(rpm_array) - 1)
    else:
        n_skip = 0
    rpm_plot = rpm_array[n_skip:]
    te_plot  = te_array[n_skip:]

    # Operating point: last valid sample (on the already-trimmed array)
    valid_mask   = np.isfinite(rpm_plot) & np.isfinite(te_plot)
    rpm_op       = float(rpm_plot[valid_mask][-1]) if valid_mask.any() else float(rpm_plot[-1])
    torque_op    = float(te_plot[valid_mask][-1])  if valid_mask.any() else float(te_plot[-1])

    # Nominal references
    n_sync       = N_SYNC_FACTOR * f / p                    # synchronous RPM
    n_nom        = n_sync * (1.0 - 0.03)                   # rated RPM (s = 3%)
    omega_nom    = n_nom * RPM_TO_RAD                       # rad/s
    torque_nom   = (P_nom_kw * 1000.0) / omega_nom         # N·m

    col_traj  = "#60a5fa" if dark else "#1d4ed8"   # blue
    col_op    = "#f59e0b"                           # amber — highlight
    col_ref   = "#6b7280"                           # grey — reference lines

    fig = go.Figure()

    # Dynamic trajectory (without initial electromagnetic transient)
    fig.add_trace(go.Scatter(
        x=rpm_plot, y=te_plot,
        mode="lines",
        name="Dynamic Trajectory",
        line=dict(color=col_traj, width=1.8),
        hovertemplate="<b>Trajectory</b><br>n = %{x:.1f} RPM<br>Te = %{y:.2f} N·m<extra></extra>",
    ))

    # Steady-state operating point
    fig.add_trace(go.Scatter(
        x=[rpm_op], y=[torque_op],
        mode="markers",
        name="Steady-State Operating Point",
        marker=dict(symbol="star", size=14, color=col_op,
                    line=dict(color=col_op, width=1)),
        hovertemplate=(
            "<b>Steady State</b><br>"
            "n = %{x:.1f} RPM<br>"
            "Te = %{y:.2f} N·m<extra></extra>"
        ),
    ))

    # Reference line: estimated rated torque
    fig.add_hline(
        y=torque_nom,
        line=dict(color=col_ref, width=1.2, dash="dash"),
        annotation_text=f"Est. Rated Torque ({torque_nom:.1f} N·m)",
        annotation_position="top left",
        annotation_font=dict(size=10, color=col_ref),
    )

    # Reference line: synchronous speed
    fig.add_vline(
        x=n_sync,
        line=dict(color=col_ref, width=1.2, dash="dot"),
        annotation_text=f"Sync. Speed ({n_sync:.0f} RPM)",
        annotation_position="top right",
        annotation_font=dict(size=10, color=col_ref),
    )

    fig.update_layout(
        height=380,
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=40, b=50),
        hovermode="closest",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="right", x=1,
            font=dict(size=10), bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title="Rotor Speed (RPM)",
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
            tickfont=dict(size=10, color=pt["fg"]),
            zeroline=False,
        ),
        yaxis=dict(
            title="Electromagnetic Torque Te (N·m)",
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
            zeroline=True, zerolinecolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
            exponentformat="none", autorange=True,
        ),
        uirevision="ts-chart",
    )
    return fig
