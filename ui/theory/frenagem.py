# -*- coding: utf-8 -*-
"""
frenagem.py
===========
Interactive comparator of three braking methods: Regenerative, Plugging, DC injection.

Responsibilities:
  - Pre-compute frames for intensity slider and dropdown for initial speed.
  - Render comparative summary table below chart.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme

from ui.theory._shared import _get_mp, _dark


def render_comparador_frenagem() -> None:
    """Interactive comparator of the 3 braking methods: Regenerative, Plugging, DC.

    Zero latency via Plotly frames:
    - JS slider for braking intensity (N_INTENS steps)
    - Plotly dropdown for initial speed n0 (N_N0 options)
    - 3 Streamlit checkboxes to show/hide each method (rerun OK as it changes trace structure)
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    n_sync = float(mp.n_sync)
    n_nom  = n_sync * 0.97

    # Streamlit checkboxes (rerun is acceptable — changes structure)
    c3, c4, c5 = st.columns(3)
    with c3:
        show_reg  = st.checkbox("Regenerative",              value=True, key="_frenagem_reg")
    with c4:
        show_plug = st.checkbox("Counter-current (Plugging)", value=True, key="_frenagem_plug")
    with c5:
        show_dc   = st.checkbox("DC Injection",               value=True, key="_frenagem_dc")

    col_reg  = "#34d399" if dark else "#059669"
    col_plug = "#f87171"
    col_dc   = "#fbbf24" if dark else "#d97706"

    t_max = 3.0
    t = np.linspace(0.0, t_max, 1200)

    # Grids
    N_INTENS = 45  # intensity: 0.3 → 2.5
    N_N0     = 11  # n0: 50% → 100% of n_sync, step 5

    intens_grid = np.linspace(0.3, 2.5, N_INTENS)
    n0_pct_grid = np.arange(50, 105, 5)  # [50, 55, ..., 100]

    # Initial indices
    nom_intens_idx = int(np.argmin(np.abs(intens_grid - 1.0)))
    nom_n0_idx     = int(np.argmin(np.abs(n0_pct_grid - int(round(n_nom / n_sync * 100)))))

    def _compute_curves(intensidade, n0_pct):
        n0 = n_sync * (n0_pct / 100.0)
        tau_reg = 0.55 * intensidade
        n_reg   = n0 * np.exp(-t / tau_reg)

        t_plug_stop  = max(0.05, 0.35 * intensidade) * (n0 / n_nom)
        n_plug_motor = n0 * (1.0 - t / t_plug_stop)
        mask_plug    = t <= t_plug_stop
        n_plug_no_disc = n_plug_motor.copy()

        tau_dc = 1.05 * intensidade
        n_dc   = n0 * np.exp(-t / tau_dc)

        def _t_stop(n_arr, n_ref):
            below = np.where(np.abs(n_arr) <= 0.05 * n_ref)[0]
            return float(t[below[0]]) if len(below) > 0 else float(t[-1])

        ts_reg  = _t_stop(n_reg, n0)
        ts_plug = t_plug_stop
        ts_dc   = _t_stop(n_dc, n0)

        return (n0, n_reg, n_plug_motor, mask_plug, n_plug_no_disc, n_dc,
                ts_reg, ts_plug, ts_dc)

    # ── Base figure (initial frame: nom_n0_idx, nom_intens_idx) ──────────────
    (n0_i, n_reg_i, n_plug_i, mask_i, n_nod_i, n_dc_i,
     ts_reg_i, ts_plug_i, ts_dc_i) = _compute_curves(
        intens_grid[nom_intens_idx], n0_pct_grid[nom_n0_idx])

    fig = go.Figure()

    # Trace 0 — Regenerative
    fig.add_trace(go.Scatter(
        x=t, y=n_reg_i if show_reg else [None]*len(t),
        mode="lines",
        name=f"Regenerative (t_p ≈ {ts_reg_i:.2f} s)",
        line=dict(color=col_reg, width=2.5, dash="dash"),
        hovertemplate="t = %{x:.2f} s<br>n = %{y:.0f} RPM<extra>Regenerative</extra>",
        visible=show_reg,
    ))

    # Trace 1 — Plugging (active portion)
    t_plug_x = t[mask_i].tolist() if show_plug else []
    n_plug_y = n_plug_i[mask_i].tolist() if show_plug else []
    fig.add_trace(go.Scatter(
        x=t_plug_x, y=n_plug_y,
        mode="lines",
        name=f"Plugging (t_p ≈ {ts_plug_i:.2f} s)",
        line=dict(color=col_plug, width=2.8),
        hovertemplate="t = %{x:.2f} s<br>n = %{y:.0f} RPM<extra>Plugging</extra>",
        visible=show_plug,
    ))

    # Trace 2 — Plugging without disconnection (dotted)
    t_ov = t[~mask_i][:60].tolist() if show_plug else []
    n_ov = n_nod_i[~mask_i][:60].tolist() if show_plug else []
    fig.add_trace(go.Scatter(
        x=t_ov, y=n_ov,
        mode="lines",
        line=dict(color=col_plug, width=1.4, dash="dot"),
        opacity=0.55,
        showlegend=False,
        hoverinfo="skip",
        visible=show_plug,
    ))

    # Trace 3 — DC Injection
    fig.add_trace(go.Scatter(
        x=t, y=n_dc_i if show_dc else [None]*len(t),
        mode="lines",
        name=f"DC Injection (t_p ≈ {ts_dc_i:.2f} s)",
        line=dict(color=col_dc, width=2.5, dash="dot"),
        hovertemplate="t = %{x:.2f} s<br>n = %{y:.0f} RPM<extra>DC</extra>",
        visible=show_dc,
    ))

    fig.add_hline(y=0.0,    line=dict(color=pt["fg"],   width=1.0))
    fig.add_hline(y=n_nom,  line=dict(color=pt["grid"], width=0.8, dash="dot"))

    # ── Frames: slider for intensity, dropdown for n0 ────────────────────────
    # Frames indexed by (n0_idx, intens_idx): frame_name = f"{n0_idx}_{intens_idx}"
    frames = []
    for ni, n0_pct in enumerate(n0_pct_grid):
        for ii, intens in enumerate(intens_grid):
            (n0_f, n_reg_f, n_plug_f, mask_f, n_nod_f, n_dc_f,
             ts_reg_f, ts_plug_f, ts_dc_f) = _compute_curves(intens, n0_pct)

            t_plug_xf = t[mask_f].tolist()
            n_plug_yf = n_plug_f[mask_f].tolist()
            t_ovf = t[~mask_f][:60].tolist()
            n_ovf = n_nod_f[~mask_f][:60].tolist()

            frames.append(go.Frame(
                name=f"{ni}_{ii}",
                data=[
                    go.Scatter(x=t, y=n_reg_f,
                               name=f"Regenerative (t_p ≈ {ts_reg_f:.2f} s)"),
                    go.Scatter(x=t_plug_xf, y=n_plug_yf,
                               name=f"Plugging (t_p ≈ {ts_plug_f:.2f} s)"),
                    go.Scatter(x=t_ovf, y=n_ovf),
                    go.Scatter(x=t, y=n_dc_f,
                               name=f"DC Injection (t_p ≈ {ts_dc_f:.2f} s)"),
                ],
                traces=[0, 1, 2, 3],
            ))

    fig.frames = frames

    # ── JS slider for intensity ────────────────────────────────────────────────
    slider_steps = []
    for ii, intens in enumerate(intens_grid):
        slider_steps.append(dict(
            method="animate",
            label=f"{intens:.1f}x",
            args=[[f"{nom_n0_idx}_{ii}"],
                  dict(mode="immediate",
                       frame=dict(duration=0, redraw=True),
                       transition=dict(duration=0))],
        ))

    # ── Plotly dropdown for n0 ───────────────────────────────────────────────
    dropdown_buttons = []
    for ni, n0_pct in enumerate(n0_pct_grid):
        dropdown_buttons.append(dict(
            method="animate",
            label=f"{n0_pct}%",
            args=[[f"{ni}_{nom_intens_idx}"],
                  dict(mode="immediate",
                       frame=dict(duration=0, redraw=True),
                       transition=dict(duration=0))],
        ))

    fig.update_layout(
        height=500,
        title=dict(text="Braking Method Comparison — n(t)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=160),
        xaxis=dict(title="Time since braking start (s)", showgrid=True,
                   gridcolor=pt["grid"], tickfont=dict(size=10, color=pt["fg"]),
                   range=[0, t_max]),
        yaxis=dict(title="Speed (RPM)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   range=[-n_sync * 0.15, n_sync * 1.05]),
        showlegend=True,
        legend=dict(x=0.98, y=0.98, xanchor="right", yanchor="top",
                    font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)"),
        # Dropdown para n0
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                x=0.01, y=1.13, xanchor="left", yanchor="top",
                showactive=True,
                active=nom_n0_idx,
                buttons=dropdown_buttons,
                bgcolor=pt["paper_bg"],
                bordercolor=pt["grid"],
                font=dict(color=pt["fg"], size=11),
            ),
            # Hidden button to activate animation system
            dict(
                type="buttons", visible=False,
                buttons=[dict(method="animate", args=[None])],
            ),
        ],
        annotations=[dict(
            text="Initial speed (% n_sync):",
            x=0.01, y=1.17, xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=11, color=pt["fg"]),
            xanchor="left",
        )],
        sliders=[dict(
            active=nom_intens_idx,
            currentvalue=dict(
                prefix="Braking intensity: ",
                suffix="x",
                visible=True,
                xanchor="center",
                font=dict(size=12, color=pt["fg"]),
            ),
            y=0,
            pad=dict(t=65, b=10),
            len=0.92,
            x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"],
            bordercolor=pt["grid"],
            tickcolor=pt["fg"],
            font=dict(color=pt["fg"], size=9),
        )],
    )

    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    # ── Comparative summary ───────────────────────────────────────────────────
    st.markdown("**Summary of selected methods:**")
    rows = []
    if show_reg:
        rows.append(("Regenerative", f"{ts_reg_i:.2f} s",  "Returns to grid",      "Low (grid absorbs)"))
    if show_plug:
        rows.append(("Plugging",     f"{ts_plug_i:.2f} s", "Dissipated in rotor",  "Very high (overcurrent)"))
    if show_dc:
        rows.append(("DC Injection", f"{ts_dc_i:.2f} s",   "Dissipated in rotor",  "Moderate"))
    if rows:
        st.table({
            "Method":               [r[0] for r in rows],
            "Time to 5% of n₀":    [r[1] for r in rows],
            "Energy destination":   [r[2] for r in rows],
            "Thermal cost":         [r[3] for r in rows],
        })
