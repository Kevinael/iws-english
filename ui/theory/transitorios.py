# -*- coding: utf-8 -*-
"""
transitorios.py
===============
Synchronised transient plots — n(t), Te(t) and ias(t) for three scenarios.

Responsibilities:
  - Build analytical models for DOL start, voltage sag and shutdown.
  - Render Plotly figure with updatemenus (scenario buttons, zero latency).
  - Provide _palette_theory() and _build_circuit_png() helpers used by
    render_circuito_alternavel (circuito_alternavel.py).

Relationships:
  Imported by : ui.theory_interactive (re-export)
               ui.theory.circuito_alternavel (_palette_theory, _build_circuit_png)
  Imports     : ui.theory._shared, viz.tim_charts, viz.tim_eqcircuit,
                core.tim.torque_speed
"""

from __future__ import annotations

import io

import matplotlib
try:
    matplotlib.use("Agg")
except Exception:
    pass
import matplotlib.pyplot as plt

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme
from viz.tim_eqcircuit import build_figure
from core.tim import _extract_params, _torque_array

from ui.theory._shared import _get_mp, _dark
from ui.theory.tabs._shared import _z2

@st.cache_data(show_spinner=False)
def _compute_transitorios(
    V1: float, R1: float, X1: float, R2: float, X2: float,
    Xm: float, ws_mec: float, ns: float,
    wb: float, p: int, J: float, B: float, f: float,
) -> dict:
    """Compute all three transient scenarios. Pure numerics, no Streamlit."""
    Z2s1  = _z2(R2, 1.0, X2)
    Zeqs1 = (1j * Xm * Z2s1) / (1j * Xm + Z2s1)
    I_pk  = abs(V1 / (R1 + 1j * X1 + Zeqs1))
    s_ss  = 0.04
    Z2ss  = _z2(R2, s_ss, X2)
    Zeqss = (1j * Xm * Z2ss) / (1j * Xm + Z2ss)
    I_ss  = abs(V1 / (R1 + 1j * X1 + Zeqss))
    Te_ss = float(_torque_array(np.array([s_ss]), V1, R1, X1, R2, X2, Xm, ws_mec)[0])
    Tl    = Te_ss * 0.85
    n_ss  = ns * (1.0 - s_ss)
    tau_mec = J * ws_mec / max(Te_ss, 1.0)
    tau_e   = (X1 + X2) / (2.0 * np.pi * f * max(R1 + R2, 0.01))

    # Scenario A
    t_max_A = max(tau_mec * 3.5, 4.0)
    t_A     = np.linspace(0.0, t_max_A, 1200)
    t_load  = t_max_A * 0.55
    tau_acc = max(tau_mec * 0.8, 0.5)
    n_pre   = n_ss * (1.0 - np.exp(-t_A / tau_acc))
    delta_n = n_ss * 0.025
    tau_sag = tau_acc * 0.3
    n_A     = np.where(t_A < t_load, n_pre,
                       n_ss - delta_n * np.exp(-(t_A - t_load) / tau_sag))
    s_arr_A = np.maximum(1.0 - n_A / ns, 1e-4)
    Te_A    = np.clip(_torque_array(s_arr_A, V1, R1, X1, R2, X2, Xm, ws_mec), 0.0, None)
    env_A   = I_ss + (I_pk - I_ss) * np.exp(-t_A / max(tau_e, 1e-3))
    env_A   = np.where(t_A < t_load, env_A, np.maximum(env_A, I_ss * 1.18))
    ias_A   = env_A * np.abs(np.sin(2.0 * np.pi * f * t_A))

    # Scenario B
    t_sag_start = 1.0; t_sag_dur = 0.20; t_sag_end = t_sag_start + t_sag_dur
    t_B         = np.linspace(0.0, t_sag_end + 1.5, 1200)
    sag_depth   = 0.30
    n_sag_drop  = n_ss * 0.06 * sag_depth / 0.30
    tau_sag_n   = 0.08
    n_B = np.where(t_B < t_sag_start, n_ss,
          np.where(t_B < t_sag_end,
                   n_ss - n_sag_drop * (1.0 - np.exp(-(t_B - t_sag_start) / tau_sag_n)),
                   n_ss - n_sag_drop * np.exp(-(t_B - t_sag_end) / tau_sag_n)))
    Te_sag   = Te_ss * (1.0 - sag_depth) ** 2
    Te_B = np.where(t_B < t_sag_start, Te_ss,
           np.where(t_B < t_sag_end,
                    Te_sag + (Te_ss - Te_sag) * np.exp(-(t_B - t_sag_start) / 0.04),
                    Te_ss - (Te_ss - Te_sag) * np.exp(-(t_B - t_sag_end) / 0.06)))
    I_restart   = I_ss * (1.0 + 2.5 * sag_depth)
    ias_B_env   = np.where(t_B < t_sag_start, I_ss,
                  np.where(t_B < t_sag_end, I_ss * (1.0 - sag_depth * 0.6),
                           I_ss + (I_restart - I_ss) * np.exp(-(t_B - t_sag_end) / max(tau_e, 0.05))))
    ias_B = ias_B_env * np.abs(np.sin(2.0 * np.pi * f * t_B))

    # Scenario C
    t_cutoff    = 0.5
    t_C         = np.linspace(0.0, t_cutoff + max(J * ws_mec / max(Tl * 0.5, 1.0), 2.0), 1200)
    tau_n_off   = J / max(B + Tl / max(float(ws_mec), 1.0), 0.01)
    n_C  = np.where(t_C < t_cutoff, n_ss,
                    np.maximum(n_ss * np.exp(-(t_C - t_cutoff) / max(tau_n_off, 0.1)), 0.0))
    tau_Te_off  = float(Xm / (wb * max(R2, 0.01))) * 0.15
    Te_C = np.maximum(np.where(t_C < t_cutoff, Te_ss,
                               Te_ss * np.exp(-(t_C - t_cutoff) / max(tau_Te_off, 0.02))), 0.0)
    ias_C_env = np.where(t_C < t_cutoff, I_ss,
                         I_ss * np.exp(-(t_C - t_cutoff) / max(tau_Te_off * 2, 0.05)))
    ias_C = ias_C_env * np.abs(np.sin(2.0 * np.pi * f * t_C))

    return dict(
        t_A=t_A, n_A=n_A, Te_A=Te_A, ias_A=ias_A, t_load=t_load,
        t_B=t_B, n_B=n_B, Te_B=Te_B, ias_B=ias_B,
        t_sag_start=t_sag_start, t_sag_end=t_sag_end, sag_depth=sag_depth,
        t_sag_dur=t_sag_dur,
        t_C=t_C, n_C=n_C, Te_C=Te_C, ias_C=ias_C, t_cutoff=t_cutoff,
        I_ss=I_ss, I_pk=I_pk, Te_ss=Te_ss, n_ss=n_ss, J=J,
    )


def _palette_theory(dark: bool) -> dict[str, str]:
    if dark:
        return dict(muted="#8892b0", text="#e4e8f5", accent="#4f8ef7",
                    border="#2a3150", surface="#161b27")
    return dict(muted="#4b5563", text="#111827", accent="#2563eb",
                border="#d0d8f0", surface="#ffffff")


@st.cache_data(show_spinner="Generating circuit…")
def _build_circuit_png(mp_key: tuple, dark: bool, simplified: bool) -> bytes:
    """Generates PNG bytes of the equivalent circuit (cacheable)."""
    class _MP:
        pass
    mp_obj = _MP()
    (mp_obj.Vl, mp_obj.f, mp_obj.Rs, mp_obj.Rr,
     mp_obj.Xm, mp_obj.Xls, mp_obj.Xlr, rfe_real, mp_obj.p) = mp_key
    mp_obj.Rfe = 1e9 if simplified else rfe_real  # Rfe → ∞ removes the shunt branch

    bg_hex = "#0d1117" if dark else "#ffffff"
    with matplotlib.rc_context({"mathtext.fontset": "dejavusans", "text.usetex": False}):
        fig = build_figure(mp_obj, dark, _palette_theory)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=bg_hex, bbox_inches="tight")
        plt.close(fig)
    return buf.getvalue()


def render_transitorios_sincronizados() -> None:
    """Synchronised plots of n(t), Te(t) and ias(t) for three transient scenarios.

    Uses updatemenus (Plotly buttons) to switch between scenarios without rerun:
      1. DOL start at no load followed by load application
      2. Voltage Sag
      3. Shutdown (supply cut after steady state)

    Scenarios are approximate analytical models — pedagogically representative,
    not a substitute for the full numerical simulation of the solver.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)
    wb = float(mp.wb)
    p  = int(mp.p)
    J  = float(mp.J)
    B  = float(mp.B) if mp.B > 0 else 0.005
    f  = float(mp.f)

    _d = _compute_transitorios(V1, R1, X1, R2, X2, Xm, ws_mec, ns, wb, p, J, B, f)
    t_A = _d["t_A"]; n_A = _d["n_A"]; Te_A = _d["Te_A"]; ias_A = _d["ias_A"]
    t_B = _d["t_B"]; n_B = _d["n_B"]; Te_B = _d["Te_B"]; ias_B = _d["ias_B"]
    t_C = _d["t_C"]; n_C = _d["n_C"]; Te_C = _d["Te_C"]; ias_C = _d["ias_C"]
    t_load = _d["t_load"]; t_sag_start = _d["t_sag_start"]; t_sag_end = _d["t_sag_end"]
    t_sag_dur = _d["t_sag_dur"]; sag_depth = _d["sag_depth"]; t_cutoff = _d["t_cutoff"]
    I_ss = _d["I_ss"]; Te_ss = _d["Te_ss"]; n_ss = _d["n_ss"]
    t_events_A = [t_load]
    t_events_B = [t_sag_start, t_sag_end]
    t_events_C = [t_cutoff]

    col_n   = "#4f8ef7" if dark else "#1d4ed8"
    col_Te  = "#34d399" if dark else "#059669"
    col_ias = "#f97316"

    # ─────────────────────────────────────────────────────────────────────────
    # Figure with subplots — 3 rows (n, Te, ias)
    # ─────────────────────────────────────────────────────────────────────────
    from plotly.subplots import make_subplots

    def _make_subplots_for(t, n, Te, ias, t_events):
        traces = []
        for row, (y_arr, col, name) in enumerate([
            (n,   col_n,   "n (RPM)"),
            (Te,  col_Te,  "Te (N·m)"),
            (ias, col_ias, "ias (A)"),
        ], 1):
            traces.append(dict(
                type="scatter", x=t, y=y_arr,
                mode="lines", name=name,
                line=dict(color=col, width=2.2),
                xaxis=f"x{row}", yaxis=f"y{row}",
                showlegend=(row == 1),
            ))
        return traces, t_events

    traces_A, tevs_A = _make_subplots_for(t_A, n_A, Te_A, ias_A, t_events_A)
    traces_B, tevs_B = _make_subplots_for(t_B, n_B, Te_B, ias_B, t_events_B)
    traces_C, tevs_C = _make_subplots_for(t_C, n_C, Te_C, ias_C, t_events_C)

    # Event line: add as shape-like vertical scatter trace
    def _event_shapes(t_events, yref_count=3):
        shapes = []
        for te in t_events:
            for row in range(1, yref_count + 1):
                sfx = str(row) if row > 1 else ""
                shapes.append(dict(
                    type="line",
                    xref=f"x{sfx}", yref=f"y{sfx} domain",
                    x0=te, x1=te, y0=0, y1=1,
                    line=dict(color=pt["event_line"], width=1.2, dash="dot"),
                ))
        return shapes

    # Build base figure with scenario A
    SCENARIOS = [
        ("DOL Start + Load", traces_A, _event_shapes(tevs_A),
         f"n₀ → {n_ss:.0f} RPM → speed dip under load",
         t_A[-1], max(n_A) * 1.15, max(Te_A) * 1.15, max(ias_A) * 1.15),
        ("Voltage Sag", traces_B, _event_shapes(tevs_B),
         f"{int(sag_depth*100)}% sag of {t_sag_dur*1000:.0f} ms — transient re-start",
         t_B[-1], max(n_B) * 1.05, max(Te_B) * 1.25, max(ias_B) * 1.25),
        ("Shutdown", traces_C, _event_shapes(tevs_C),
         f"Supply cut at t={t_cutoff:.2f} s — inertial decay (J={J:.3f} kg·m²)",
         t_C[-1], n_ss * 1.10, Te_ss * 1.25, I_ss * 1.25),
    ]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.06,
                        row_heights=[0.34, 0.33, 0.33])

    # Initialise with scenario A
    for tr in SCENARIOS[0][1]:
        row = int(tr["xaxis"][-1]) if tr["xaxis"][-1].isdigit() else 1
        fig.add_trace(go.Scatter(
            x=tr["x"], y=tr["y"],
            mode=tr["mode"], name=tr["name"],
            line=tr["line"],
            showlegend=tr["showlegend"],
            hovertemplate=f"t = %{{x:.4f}} s<br>{tr['name']} = %{{y:.2f}}<extra></extra>",
        ), row=row, col=1)

    y_titles = ["Speed (RPM)", "Torque $T_e$ (N·m)", "Current $i_{as}$ (A)"]
    for i, ytitle in enumerate(y_titles, 1):
        fig.update_yaxes(
            title_text=ytitle, row=i, col=1,
            showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
            title_font=dict(size=11, color=pt["fg"]),
        )
    fig.update_xaxes(
        title_text="Time (s)", row=3, col=1,
        showgrid=True, gridcolor=pt["grid"],
        tickfont=dict(size=10, color=pt["fg"]),
    )

    # ── updatemenus: scenario buttons (zero latency via restyle) ─────────────
    buttons = []
    for label, traces, shapes, desc, t_end, yn, yte, yia in SCENARIOS:
        x_data = [tr["x"] for tr in traces]
        y_data = [tr["y"] for tr in traces]
        buttons.append(dict(
            method="restyle",
            label=label,
            args=[{"x": x_data, "y": y_data}],
        ))

    fig.update_layout(
        height=520,
        title=dict(
            text="Synchronised Transients — n(t) · Te(t) · ias(t)",
            x=0.5, xanchor="center",
            font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=70, r=20, t=100, b=45),
        hovermode="x unified",
        showlegend=False,
        shapes=SCENARIOS[0][2],
        updatemenus=[dict(
            type="buttons",
            direction="right",
            x=0.5, xanchor="center",
            y=1.13, yanchor="top",
            showactive=True,
            bgcolor=pt["paper_bg"],
            bordercolor=pt["grid"],
            font=dict(color=pt["fg"], size=11),
            buttons=buttons,
            active=0,
        )],
    )

    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    st.caption(
        "Approximate analytical model — pedagogically representative. "
        "For precise numerical curves, use the **Simulator** with your machine parameters. "
        "Amber dashed lines indicate event instants (load application, sag start/end, supply cut)."
    )
