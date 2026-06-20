# -*- coding: utf-8 -*-
"""
_chart_base.py
==============
Shared Plotly base builders for stacked, side-by-side, and overlay waveform
charts.  MIT and DC wrappers in tim_charts.py / plotly_charts_dc.py call these
with machine-specific parameters instead of duplicating layout code.

Parameters common to all three builders
----------------------------------------
key_guard : bool
    When True, silently skip keys absent from *res* (DC behaviour).  MIT never
    has missing keys so this is always False for MIT wrappers.
tl_label : str
    Legend/hover label for the TL trace.  MIT uses plain text; DC uses LaTeX.
showlegend_always : bool
    When True the legend is shown regardless of whether TL is present.
    MIT shows the legend only when TL is present; DC always shows it.
dual_axis_keys : set[str] | None
    Keys that should be plotted on the secondary y-axis (right side).
    MIT passes {"n", "wr"}; DC passes None (no dual axis).
"""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots


_LINE_COLORS_DARK  = ["#ffffff"] * 12
_LINE_COLORS_LIGHT = ["#000000"] * 12

_TL_COLOR = "#f59e0b"  # amber — distinguishes TL from Te in charts


def _colors(dark: bool) -> list:
    return _LINE_COLORS_DARK if dark else _LINE_COLORS_LIGHT


def _plot_theme(dark: bool) -> dict:
    if dark:
        return dict(
            plot_bg    = "#151a24",
            paper_bg   = "#0f1218",
            fg         = "#e5e7eb",
            grid       = "rgba(255,255,255,0.15)",
            event_line = "#f59e0b",
        )
    return dict(
        plot_bg    = "#ffffff",
        paper_bg   = "#ffffff",
        fg         = "#000000",
        grid       = "#B9ADAD",
        event_line = "#000000",
    )


def _build_stacked_base(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    decimals: int,
    tl_arr,
    key_guard: bool,
    tl_label: str,
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
        if key_guard and key not in res:
            continue
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=cl[(i - 1) % len(cl)], width=1.9),
            hovertemplate=(
                f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>"
                f"value = %{{y:.{decimals}f}}<extra></extra>"
            ),
        ), row=i, col=1)
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name=tl_label,
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=(
                    f"<b>Tl</b><br>t = %{{x:.4f}} s<br>"
                    f"value = %{{y:.{decimals}f}} N·m<extra></extra>"
                ),
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
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)") if has_tl else {},
    )
    return fig


def _build_sidebyside_base(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    decimals: int,
    ref_list,
    primary_color,
    compact: bool,
    tl_arr,
    key_guard: bool,
    tl_label: str,
    showlegend_always: bool,
) -> list[go.Figure]:
    cl     = _colors(dark)
    th     = _plot_theme(dark)
    t      = res["t"]
    has_tl = tl_arr is not None and "Te" in var_keys
    figs   = []

    for i, (key, lbl) in enumerate(zip(var_keys, var_labels)):
        if key_guard and key not in res:
            continue
        pcol = primary_color or cl[i % len(cl)]
        fig  = go.Figure()

        for ref_item in (ref_list or []):
            res_ref = ref_item.get("res")
            if res_ref is not None and key in res_ref:
                fig.add_trace(go.Scatter(
                    x=res_ref["t"], y=res_ref[key], mode="lines",
                    name=ref_item.get("label", "Reference"),
                    line=dict(color=ref_item.get("color", "#888888"), width=1.4,
                              dash=ref_item.get("dash", "dash")),
                    hovertemplate=(
                        f"<b>{ref_item.get('label','Ref')}</b><br>"
                        f"t = %{{x:.4f}} s<br>value = %{{y:.{decimals}f}}<extra></extra>"
                    ),
                ))

        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=pcol, width=1.8),
            hovertemplate=(
                f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>"
                f"value = %{{y:.{decimals}f}}<extra></extra>"
            ),
        ))
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name=tl_label,
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=(
                    f"<b>Tl</b><br>t = %{{x:.4f}} s<br>"
                    f"value = %{{y:.{decimals}f}} N·m<extra></extra>"
                ),
            ))
        for te in (t_events or []):
            fig.add_vline(x=te, line_dash="dot", line_color=th["event_line"], line_width=1.1)

        _h   = 200 if compact else 230
        _m   = dict(l=28, r=8, t=26, b=26) if compact else dict(l=45, r=12, t=36, b=36)
        _fsz = 9 if compact else 10

        show_legend = showlegend_always or (key == "Te" and has_tl)
        legend_cfg  = (
            dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                 font=dict(size=9), bgcolor="rgba(0,0,0,0)")
            if show_legend else {}
        )
        fig.update_layout(
            title=dict(text=lbl, x=0.5, xanchor="center",
                       font=dict(size=11 if compact else 12, color=th["fg"])),
            height=_h,
            paper_bgcolor=th["paper_bg"], plot_bgcolor=th["plot_bg"],
            font=dict(family="Inter, system-ui", size=_fsz, color=th["fg"]),
            margin=_m,
            xaxis=dict(title="Time (s)", showgrid=True, gridcolor=th["grid"],
                       tickfont=dict(size=9, color=th["fg"])),
            yaxis=dict(showgrid=True, gridcolor=th["grid"], zeroline=True,
                       zerolinecolor=th["grid"], tickfont=dict(size=9, color=th["fg"]),
                       exponentformat="none", autorange=True, rangemode="normal",
                       fixedrange=False),
            hovermode="x unified",
            showlegend=show_legend,
            legend=legend_cfg,
        )
        figs.append(fig)
    return figs


def _build_overlay_base(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    decimals: int,
    ref_list,
    primary_color,
    compact: bool,
    tl_arr,
    key_guard: bool,
    tl_label: str,
    dual_axis_keys: set | None,
    show_title: bool,
) -> go.Figure:
    pt     = _plot_theme(dark)
    cl     = _colors(dark)
    t      = res["t"]
    has_tl = tl_arr is not None and "Te" in var_keys

    right_units = dual_axis_keys or set()
    has_right   = bool(right_units) and any(k in right_units for k in var_keys)

    fig = go.Figure()

    for ref_item in (ref_list or []):
        res_ref = ref_item.get("res")
        if res_ref is not None:
            for key, lbl in zip(var_keys, var_labels):
                if key not in res_ref:
                    continue
                yaxis = "y2" if (key in right_units and has_right) else "y"
                fig.add_trace(go.Scatter(
                    x=res_ref["t"], y=res_ref[key], mode="lines",
                    name=f"{ref_item.get('label','Ref')} — {lbl}", yaxis=yaxis,
                    line=dict(color=ref_item.get("color", "#888888"), width=1.4,
                              dash=ref_item.get("dash", "dash")),
                    hovertemplate=(
                        f"<b>{ref_item.get('label','Ref')}</b><br>"
                        f"t = %{{x:.4f}} s<br>value = %{{y:.{decimals}f}}<extra></extra>"
                    ),
                ))

    for i, (key, lbl) in enumerate(zip(var_keys, var_labels)):
        if key_guard and key not in res:
            continue
        pcol  = primary_color or cl[i % len(cl)]
        yaxis = "y2" if (key in right_units and has_right) else "y"
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=pcol, width=1.9), yaxis=yaxis,
            hovertemplate=(
                f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>"
                f"value = %{{y:.{decimals}f}}<extra></extra>"
            ),
        ))
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name=tl_label,
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=(
                    f"<b>Tl</b><br>t = %{{x:.4f}} s<br>"
                    f"value = %{{y:.{decimals}f}} N·m<extra></extra>"
                ),
            ))

    for te in (t_events or []):
        fig.add_vline(x=te, line_dash="dot", line_color=pt["event_line"], line_width=1.1)

    y2_cfg = dict(
        overlaying="y", side="right",
        showgrid=False, zeroline=False,
        tickfont=dict(size=10, color=pt["fg"]),
        exponentformat="none",
        autorange=True, rangemode="normal", fixedrange=False,
    ) if has_right else {}

    _r_val = (45 if has_right else 8)  if compact else (65 if has_right else 20)
    _ov_m  = (dict(l=35, r=_r_val, t=32, b=28)
              if compact else dict(l=55, r=65 if has_right else 20, t=48, b=40))

    title_cfg = (
        dict(text="Overlaid Curves", x=0.5, xanchor="center",
             font=dict(size=11 if compact else 12, color=pt["fg"]))
        if show_title else {}
    )

    fig.update_layout(
        height=320 if compact else 380,
        title=title_cfg,
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10 if compact else 11, color=pt["fg"]),
        margin=_ov_m,
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(title="Time (s)", showgrid=True,
                   gridcolor=pt["grid"], gridwidth=0.4,
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(showgrid=True, gridcolor=pt["grid"],
                   zeroline=True, zerolinecolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   exponentformat="none",
                   autorange=True, rangemode="normal", fixedrange=False),
        yaxis2=y2_cfg if has_right else {},
    )
    return fig
