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
  Imported by : ui_components.sim_results_dc
  Imports     : viz.plotly_charts

Extending:
  - To add a new DCM chart type, create build_fig_<type>_dc() here following
    the MIT counterpart convention in viz.plotly_charts.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from viz.mit_charts import _plot_theme, _colors, _TL_COLOR


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
    n  = len(var_keys)
    pt = _plot_theme(dark)
    cl = _colors(dark)
    has_tl = tl_arr is not None and "Te" in var_keys

    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        vertical_spacing=max(0.05, 0.07 / max(n, 1)),
    )
    t = res["t"]
    for i, (key, lbl) in enumerate(zip(var_keys, var_labels), 1):
        if key not in res:
            continue
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=cl[(i - 1) % len(cl)], width=1.9),
            hovertemplate=f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>value = %{{y:.{decimals}f}}<extra></extra>",
        ), row=i, col=1)
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name="$T_l$ (N·m)",
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=f"<b>Tl</b><br>t = %{{x:.4f}} s<br>value = %{{y:.{decimals}f}} N·m<extra></extra>",
            ), row=i, col=1)
        for te in (t_events or []):
            fig.add_vline(x=te, line_dash="dot", line_color=pt["event_line"],
                          line_width=1.1, row=i, col=1)
        fig.update_yaxes(
            row=i, col=1,
            title_text=lbl,
            title_font=dict(size=12, color=pt["fg"]),
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
            zeroline=True, zerolinecolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
            exponentformat="none", autorange=True, rangemode="normal", fixedrange=False,
        )

    fig.update_xaxes(row=n, col=1, title_text="Time (s)",
                     showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
                     tickfont=dict(size=10, color=pt["fg"]))
    fig.update_layout(
        height=max(300, 280 * n),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=55, r=20, t=45, b=40),
        hovermode="x unified",
        showlegend=has_tl,
    )
    return fig


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
    cl  = _colors(dark)
    th  = _plot_theme(dark)
    t   = res["t"]
    has_tl = tl_arr is not None and "Te" in var_keys
    figs = []

    for i, (key, lbl) in enumerate(zip(var_keys, var_labels)):
        if key not in res:
            continue
        pcol = primary_color or cl[i % len(cl)]
        fig  = go.Figure()

        for ref_item in (ref_list or []):
            res_ref = ref_item.get("res")
            if res_ref is not None and key in res_ref:
                fig.add_trace(go.Scatter(
                    x=res_ref["t"], y=res_ref[key], mode="lines",
                    name=ref_item.get("label", "Reference"),
                    line=dict(color=ref_item.get("color", "#888"), width=1.4,
                              dash=ref_item.get("dash", "dash")),
                    hovertemplate=f"<b>{ref_item.get('label','Ref')}</b><br>t=%{{x:.4f}} s<br>%{{y:.{decimals}f}}<extra></extra>",
                ))

        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=pcol, width=1.8),
            hovertemplate=f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>value = %{{y:.{decimals}f}}<extra></extra>",
        ))
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name="$T_l$",
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
            ))
        for te in (t_events or []):
            fig.add_vline(x=te, line_dash="dot", line_color=th["event_line"], line_width=1.1)

        _h = 200 if compact else 230
        _m = dict(l=28, r=8, t=26, b=26) if compact else dict(l=45, r=12, t=36, b=36)
        fig.update_layout(
            title=dict(text=lbl, x=0.5, xanchor="center",
                       font=dict(size=11 if compact else 12, color=th["fg"])),
            height=_h,
            paper_bgcolor=th["paper_bg"], plot_bgcolor=th["plot_bg"],
            font=dict(family="Inter, system-ui", size=9 if compact else 10, color=th["fg"]),
            margin=_m,
            xaxis=dict(title="Time (s)", showgrid=True, gridcolor=th["grid"],
                       tickfont=dict(size=9, color=th["fg"])),
            yaxis=dict(showgrid=True, gridcolor=th["grid"], zeroline=True,
                       zerolinecolor=th["grid"], tickfont=dict(size=9, color=th["fg"]),
                       exponentformat="none", autorange=True, rangemode="normal",
                       fixedrange=False),
            hovermode="x unified",
            showlegend=True,
        )
        figs.append(fig)
    return figs


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
    pt   = _plot_theme(dark)
    cl   = _colors(dark)
    t    = res["t"]
    has_tl = tl_arr is not None and "Te" in var_keys

    fig = go.Figure()

    for ref_item in (ref_list or []):
        res_ref = ref_item.get("res")
        if res_ref is not None:
            for key, lbl in zip(var_keys, var_labels):
                if key not in res_ref:
                    continue
                fig.add_trace(go.Scatter(
                    x=res_ref["t"], y=res_ref[key], mode="lines",
                    name=f"{ref_item.get('label','Ref')} — {lbl}",
                    line=dict(color=ref_item.get("color", "#888"), width=1.3,
                              dash=ref_item.get("dash", "dash")),
                ))

    for i, (key, lbl) in enumerate(zip(var_keys, var_labels)):
        if key not in res:
            continue
        pcol = primary_color or cl[i % len(cl)]
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=pcol, width=1.8),
            hovertemplate=f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>value = %{{y:.{decimals}f}}<extra></extra>",
        ))

    if has_tl:
        fig.add_trace(go.Scatter(
            x=t, y=tl_arr, mode="lines", name="$T_l$",
            line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
        ))

    for te in (t_events or []):
        fig.add_vline(x=te, line_dash="dot", line_color=pt["event_line"], line_width=1.1)

    fig.update_layout(
        height=300 if compact else 400,
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=45, r=12, t=36, b=36),
        xaxis=dict(title="Time (s)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=9, color=pt["fg"])),
        yaxis=dict(showgrid=True, gridcolor=pt["grid"], zeroline=True,
                   zerolinecolor=pt["grid"], tickfont=dict(size=9, color=pt["fg"]),
                   autorange=True, rangemode="normal", fixedrange=False),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
    )
    return fig


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
