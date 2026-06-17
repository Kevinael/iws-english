# -*- coding: utf-8 -*-
"""
mcsa.py
=======
MCSA simulator — stator current spectrum with broken-bar sidebands.

Responsibilities:
  - Pre-compute N_STEPS spectra for a severity grid α.
  - Pack as Plotly frames with JS slider (zero latency).
  - Display IEC 60034-26 diagnostic table below chart.

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


def render_mcsa() -> None:
    """MCSA simulator — current spectrum with sidebands (1 ± 2k·s)·fe.

    Uses native Plotly slider (zero latency): pre-computes N_STEPS spectra
    for a severity grid α and packs them as frames. The JS slider moves
    between frames on the client without rerun.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    f_e   = float(mp.f)
    # typical nominal slip (or from the last result, if available)
    res   = st.session_state.get("sim_result")
    if res and "res" in res and "s" in res["res"]:
        s_op = float(res["res"]["s"])
        if not (0.001 < s_op < 0.20):
            s_op = 0.035
    else:
        s_op = 0.035

    # Severity grid α — 51 linear steps between 0 and 0.5
    N_STEPS = 51
    alpha_grid = np.linspace(0.0, 0.5, N_STEPS)
    nom_idx    = int(np.argmin(np.abs(alpha_grid - 0.15)))  # start at incipient fault

    # Relevant frequencies
    f_min = max(f_e - 12.0, 0.0)
    f_max = f_e + 12.0
    freqs = np.linspace(f_min, f_max, 1200)

    # Spectral width (Lorentzian) to visualise discrete peaks
    fwhm = 0.20  # Hz
    gamma = fwhm / 2.0

    def _lorentz(f, f0, A):
        return A * (gamma ** 2) / ((f - f0) ** 2 + gamma ** 2)

    A_fund = 1.0  # amplitude normalizada da fundamental

    def _spectrum(alpha: float) -> np.ndarray:
        """Sum of fundamental + 3 sideband pairs at (1 ± 2k·s)·f_e."""
        y = _lorentz(freqs, f_e, A_fund)
        # sideband amplitudes decrease with k and grow with α
        for k in (1, 2, 3):
            A_sb = (alpha / 2.0) * (1.0 / k) * A_fund
            f_low  = f_e * (1.0 - 2.0 * k * s_op)
            f_high = f_e * (1.0 + 2.0 * k * s_op)
            y = y + _lorentz(freqs, f_low,  A_sb)
            y = y + _lorentz(freqs, f_high, A_sb)
        # noise floor
        y = y + 0.002
        return y

    col_fund = "#4f8ef7" if dark else "#1d4ed8"
    col_sb   = "#f87171"
    col_th   = "#f97316"  # diagnostic threshold line

    # Initial spectrum (frame nom_idx)
    y_init = _spectrum(alpha_grid[nom_idx])

    # ── figura base ──────────────────────────────────────────────────────────
    fig = go.Figure()

    # Trace 0 — spectrum (varies per frame)
    fig.add_trace(go.Scatter(
        x=freqs, y=20.0 * np.log10(np.clip(y_init, 1e-6, None)),
        mode="lines",
        line=dict(color=col_fund, width=1.6),
        fill="tozeroy",
        fillcolor="rgba(79,142,247,0.10)" if dark else "rgba(29,78,216,0.10)",
        name="|I_s(f)| (dB)",
        hovertemplate="f = %{x:.2f} Hz<br>%{y:.1f} dB<extra></extra>",
    ))

    # Sideband frequencies (fixed, as they depend only on s, not on α)
    sb_x = []
    sb_text = []
    for k in (1, 2, 3):
        f_low  = f_e * (1.0 - 2.0 * k * s_op)
        f_high = f_e * (1.0 + 2.0 * k * s_op)
        sb_x.extend([f_low, f_high])
        sb_text.extend([f"k=-{k}", f"k=+{k}"])

    # Trace 1 — markers at sideband positions (height recalculated per frame)
    sb_y_init = [20.0 * np.log10(max(_spectrum(alpha_grid[nom_idx])[int(np.argmin(np.abs(freqs - fx)))], 1e-6)) for fx in sb_x]
    fig.add_trace(go.Scatter(
        x=sb_x, y=sb_y_init,
        mode="markers+text",
        marker=dict(color=col_sb, size=8, symbol="diamond"),
        text=sb_text,
        textposition="top center",
        textfont=dict(color=col_sb, size=9),
        name="Sidebands (1 ± 2k·s)·fe",
        hovertemplate="f = %{x:.2f} Hz<br>%{y:.1f} dB<extra></extra>",
    ))

    # Trace 2 — IEC 60034-26 threshold (-45 dB → confirmed fault)
    fig.add_trace(go.Scatter(
        x=[f_min, f_max], y=[-45.0, -45.0],
        mode="lines",
        line=dict(color=col_th, width=1.2, dash="dash"),
        name="IEC 60034-26 threshold (−45 dB)",
        hoverinfo="skip",
    ))

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    for i, alpha in enumerate(alpha_grid):
        y_f  = _spectrum(alpha)
        y_db = 20.0 * np.log10(np.clip(y_f, 1e-6, None))
        sb_y = [20.0 * np.log10(max(y_f[int(np.argmin(np.abs(freqs - fx)))], 1e-6)) for fx in sb_x]
        frames.append(go.Frame(
            name=str(i),
            data=[
                go.Scatter(x=freqs, y=y_db),
                go.Scatter(x=sb_x, y=sb_y, text=sb_text),
                go.Scatter(x=[f_min, f_max], y=[-45.0, -45.0]),
            ],
            traces=[0, 1, 2],
        ))
        slider_steps.append(dict(
            method="animate",
            label=f"{alpha:.2f}",
            args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                 transition=dict(duration=0))],
        ))

    fig.frames = frames

    # ── layout com slider JS ─────────────────────────────────────────────────
    fig.update_layout(
        height=440,
        title=dict(
            text=f"MCSA Spectrum — stator current (s = {s_op*100:.2f}%, f_e = {f_e:.0f} Hz)",
            x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=130),
        xaxis=dict(title="Frequency (Hz)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   range=[f_min, f_max]),
        yaxis=dict(title="Amplitude (dB rel. to fundamental)", showgrid=True,
                   gridcolor=pt["grid"], tickfont=dict(size=10, color=pt["fg"]),
                   range=[-70, 5]),
        showlegend=True,
        legend=dict(x=0.98, y=0.98, xanchor="right", yanchor="top",
                    font=dict(size=10, color=pt["fg"]),
                    bgcolor="rgba(0,0,0,0)"),
        sliders=[dict(
            active=nom_idx,
            currentvalue=dict(
                prefix="α = ", suffix="",
                visible=True, xanchor="center",
                font=dict(size=13, color=pt["fg"]),
            ),
            y=0, pad=dict(t=55, b=10), len=0.92, x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"], bordercolor=pt["grid"],
            tickcolor=pt["fg"], font=dict(color=pt["fg"], size=9),
        )],
        updatemenus=[dict(type="buttons", visible=False,
                          buttons=[dict(method="animate", args=[None])])],
    )

    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    # ── IEC 60034-26 diagnostic table ────────────────────────────────────────
    alpha_curr = alpha_grid[nom_idx]
    # compute amplitude of first sideband (k=1) for diagnosis
    A_sb_db = 20.0 * np.log10(max(alpha_curr / 2.0, 1e-6))
    if A_sb_db < -50:
        diag = "**Healthy rotor** — sidebands below typical noise floor."
    elif A_sb_db < -45:
        diag = "**Monitor** — possible incipient crack; re-evaluate in 30 days."
    elif A_sb_db < -40:
        diag = "**Confirmed fault** — schedule corrective maintenance."
    elif A_sb_db < -35:
        diag = "**Advanced fault** — urgent intervention recommended."
    else:
        diag = "**Critical risk** — ring rupture risk; immediate shutdown required."

    st.caption(
        f"For α = {alpha_curr:.2f}: first sideband amplitude ≈ {A_sb_db:.1f} dB → {diag}"
    )
