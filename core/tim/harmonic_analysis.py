# -*- coding: utf-8 -*-
"""
harmonica_analysis.py
=====================
Generates FFT amplitude spectra of steady-state variables and provides unit
mapping for MCSA diagnostic display.

Responsibilities:
  - Map result key to physical unit (_fft_unit_for_key)
  - Build a Plotly FFT figure (build_fig_fft)

Relationships:
  Imported by : ui_components.sim_results
  Imports     : viz.plotly_charts, utils.text_utils

Extending:
  - To automatically detect broken-bar sidebands, add a peak-detection
    function around (1±2s)f.
"""

from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from viz.tim_charts import _plot_theme
from utils.text_utils import _strip_latex


def _fft_unit_for_key(key: str) -> str:
    """Returns the expected physical unit for the FFT variable.

    Simple mapping based on the prefix of the results dictionary key.
    """
    k = key.lower()
    if k.startswith("i"):       # ias, ibs, ics, iar, ids, iqs, ...
        return "A"
    if k.startswith("v"):       # Va, Vb, Vc
        return "V"
    if k.startswith("te") or k == "te":
        return "N·m"
    if k.startswith("wr") or k == "n":
        return "rad/s" if k.startswith("w") else "RPM"
    return ""


def build_fig_fft(res: dict, dark: bool, key: str = "ias", label: str = "ias") -> go.Figure:
    """Amplitude spectrum (FFT) of a variable in steady state."""
    pt   = _plot_theme(dark)
    col  = "#4f8ef7" if dark else "#1d4ed8"
    unit = _fft_unit_for_key(key)
    unit_suffix = f" ({unit}, RMS)" if unit else ""
    unit_hover  = f" {unit}" if unit else ""

    ss_start     = int(res.get("_ss_start", 0))
    t_broken_bar = float(res.get("_t_broken_bar", 0.0))
    t_full       = np.asarray(res["t"], dtype=float)
    # when broken bar is active, the FFT window must start after t_broken_bar
    # to capture the spectrum with the fault active — _ss_start may be earlier
    if t_broken_bar > 0.0 and len(t_full) > 0:
        bb_idx   = int(np.searchsorted(t_full, t_broken_bar))
        ss_start = max(ss_start, bb_idx)
    y = np.asarray(res[key][ss_start:], dtype=float)
    t = np.asarray(res["t"][ss_start:], dtype=float)
    if len(y) < 4:
        fig = go.Figure()
        fig.update_layout(title="Insufficient data for FFT", height=300,
                          paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"])
        return fig

    dt   = float(t[1] - t[0]) if len(t) > 1 else 1e-3
    N    = len(y)
    yf   = np.abs(np.fft.rfft(y)) * 2.0 / N
    freq = np.fft.rfftfreq(N, d=dt)

    # detects fundamental (largest peak above 1 Hz)
    f1_mask  = freq > 1.0
    mask_idx = np.where(f1_mask)[0]
    if len(mask_idx) == 0:
        f1, A1, f1_idx = 60.0, 0.0, 0
    else:
        f1_idx = int(mask_idx[0]) + int(np.argmax(yf[f1_mask]))
        f1     = float(freq[f1_idx])
        A1     = float(yf[f1_idx])

    # window: up to the 11th harmonic or 1200 Hz
    x_max = min(f1 * 11, 1200.0)
    mask  = freq <= x_max
    freq, yf = freq[mask], yf[mask]
    y_max = float(yf.max()) if len(yf) else 1.0

    # threshold: only annotate harmonics with amplitude ≥ 1% of the fundamental
    threshold = A1 * 0.01

    # identifies odd harmonic peaks above threshold
    harm_orders = [1, 3, 5, 7, 9, 11]
    labeled: list[tuple[float, float, int]] = []  # (real_freq, amplitude, order)
    for k in harm_orders:
        hf = f1 * k
        if hf > x_max:
            break
        idx = int(np.argmin(np.abs(freq - hf)))
        lo, hi = max(0, idx - 3), min(len(yf), idx + 4)
        local_idx = lo + int(np.argmax(yf[lo:hi]))
        amp = float(yf[local_idx])
        if amp >= threshold:
            labeled.append((float(freq[local_idx]), amp, k))

    # continuous spectrum trace with filled area
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=freq, y=yf,
        mode="lines",
        line=dict(color=col, width=1.5),
        fill="tozeroy",
        fillcolor="rgba(79,142,247,0.12)" if dark else "rgba(29,78,216,0.12)",
        name=label,
        hovertemplate="f = %{x:.1f} Hz<br>A = %{y:.4f}" + unit_hover + "<extra></extra>",
    ))

    # markers only on peaks with relevant energy
    if labeled:
        fig.add_trace(go.Scatter(
            x=[p[0] for p in labeled],
            y=[p[1] for p in labeled],
            mode="markers+text",
            marker=dict(color="#ef4444", size=8, symbol="diamond"),
            text=[f"{p[2]}th ({p[0]:.0f} Hz)" for p in labeled],
            textposition="top center",
            textfont=dict(size=9, color="#ef4444"),
            name="Harmonics",
            hovertemplate="f = %{x:.1f} Hz<br>A = %{y:.4f}" + unit_hover + "<extra></extra>",
        ))

    # X-axis ticks: multiples of the fundamental, at most 8 ticks
    n_ticks = min(8, int(x_max / f1)) if f1 > 0 else 8
    tick_step = max(1, round((x_max / f1) / n_ticks)) * f1

    fig.update_layout(
        height=340,
        title=dict(text=f"Amplitude Spectrum — {label} (steady state)",
                   x=0.5, xanchor="center", font=dict(size=12, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=55, r=20, t=50, b=45),
        xaxis=dict(
            title="Frequency (Hz)", showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=9, color=pt["fg"]), exponentformat="none",
            range=[0, x_max * 1.03],
            dtick=tick_step,
        ),
        yaxis=dict(
            title="Amplitude" + unit_suffix, showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=9, color=pt["fg"]), exponentformat="none",
            range=[0, y_max * 1.30],
        ),
        showlegend=False,
    )
    return fig


def render_harmonicas(res: dict, var_keys: list, var_labels: list,
                      dark: bool, render_plotly_fn) -> None:
    """Renders the spectral analysis (FFT) section in the UI."""
    ac_keys = [k for k in var_keys if k in ("ias", "ibs", "ics", "iar", "ibr", "icr", "Va", "Vb", "Vc")]
    if not ac_keys:
        return

    st.divider()
    st.markdown('<p class="slabel">Spectral Analysis</p>', unsafe_allow_html=True)
    with st.expander("View Harmonic Spectrum (FFT)", expanded=False):
        fft_var = st.selectbox(
            "Variable for analysis",
            options=ac_keys,
            format_func=lambda k: next((lbl for kk, lbl in zip(var_keys, var_labels) if kk == k), k),
            key="fft_var_select",
        )
        fft_lbl      = next((lbl for kk, lbl in zip(var_keys, var_labels) if kk == fft_var), fft_var)
        fft_lbl_plot = _strip_latex(fft_lbl)
        fig_fft = build_fig_fft(res, dark, key=fft_var, label=fft_lbl_plot)
        render_plotly_fn(fig_fft, div_id="ems-fft")
        st.caption("Red diamonds indicate odd harmonics (1st, 3rd, 5th, 7th, 9th, 11th). X-axis limited to the 11th harmonic or 1200 Hz.")
