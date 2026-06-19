# -*- coding: utf-8 -*-
"""
curva_tn.py
===========
Computes the torque-speed curve (T×n) and power flow of the induction machine
via the full complex-impedance equivalent circuit.

Responsibilities:
  - Extract circuit parameters from MachineParams (_extract_params)
  - Compute torque as a function of slip s (_torque_array)
  - Compute input, air-gap, mechanical, and loss power (calc_fluxo_potencia)

Relationships:
  Imported by : ui.theory_interactive
  Imports     : (numpy, plotly, streamlit)

Extending:
  - To include the Thévenin simplified model, add _torque_thevenin and
    compare it against the full circuit.
"""
from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
from viz.tim_charts import _plot_theme


# ── Machine parameter mapping to circuit ─────────────────────────────────────
#   V1     = mp.Vl                 phase RMS voltage (simulation applies Va_rms = Vl per winding)
#   R1     = mp.Rs                stator resistance
#   X1     = mp.Xls_a             stator leakage reactance (wb·Lls)
#   R2     = mp.Rr                rotor resistance referred to stator
#   X2     = mp.Xlr_a             rotor leakage reactance (wb·Llr)
#   Xm     = mp.wb * mp.Lm        magnetising reactance at operating frequency
#   ws_mec = mp.wb * 2 / mp.p    synchronous mechanical speed (rad/s)


def _extract_params(mp):
    """Extracts circuit parameters from MachineParams.

    V1 = mp.Vl: phase RMS voltage applied per winding (consistent with simulation,
    which applies Va = sqrt(2)*Vl*sin(θ) → Va_rms = Vl per phase).
    """
    V1     = mp.Vl
    R1     = mp.Rs
    X1     = mp.Xls_a
    R2     = mp.Rr
    X2     = mp.Xlr_a
    Xm     = mp.wb * mp.Lm
    ws_mec = mp.wb * 2.0 / mp.p
    ns     = mp.n_sync
    return V1, R1, X1, R2, X2, Xm, ws_mec, ns


def _torque_array(s_arr: np.ndarray, V1, R1, X1, R2, X2, Xm, ws_mec) -> np.ndarray:
    """Computes electromagnetic torque for an array of slip values (vectorised)."""
    # replaces s=0 with a small value to avoid division by zero
    s = np.where(s_arr == 0.0, 1e-9, s_arr)

    Z2  = (R2 / s) + 1j * X2
    Zeq = (1j * Xm * Z2) / (1j * Xm + Z2)
    Zt  = R1 + 1j * X1 + Zeq
    I1  = V1 / Zt
    Veq = I1 * Zeq
    I2  = Veq / Z2
    P2  = 3.0 * np.abs(I2) ** 2 * (R2 / s)
    return P2 / ws_mec


def calc_curva_tn(mp, n_points: int = 600) -> dict:
    """Computes the T×n curve via the full equivalent circuit.

    Covers all 3 regions: generator (s<0), motor (0<s≤1) and braking (s>1).
    Returns dict with arrays and scalars of interest.
    """
    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)

    # ── slip sweep covering all 3 regions ────────────────────────────────────
    s_neg  = np.linspace(-1.0, -1e-4, n_points // 4)          # generator
    s_pos1 = np.linspace(1e-4,  1.0,  n_points // 2)          # motor
    s_pos2 = np.linspace(1.001, 2.0,  n_points // 4)          # braking
    s_all  = np.concatenate([s_neg, s_pos1, s_pos2])

    Te_all = _torque_array(s_all, V1, R1, X1, R2, X2, Xm, ws_mec)
    n_rpm  = ns * (1.0 - s_all)

    # ── peak torque in motor region ───────────────────────────────────────────
    mask_motor = (s_all > 0) & (s_all <= 1.0)
    Te_motor   = Te_all[mask_motor]
    s_motor    = s_all[mask_motor]
    idx_max    = int(np.argmax(Te_motor))
    Te_max     = float(Te_motor[idx_max])
    s_max      = float(s_motor[idx_max])
    n_max      = float(ns * (1.0 - s_max))

    # ── starting torque (s = 1) ───────────────────────────────────────────────
    Te_part = float(_torque_array(np.array([1.0]), V1, R1, X1, R2, X2, Xm, ws_mec)[0])
    # Return parameters:
    return {
        "n_rpm":   n_rpm,
        "Te":      Te_all,
        "s":       s_all,
        "Te_max":  Te_max,
        "Te_part": Te_part,
        "s_max":   s_max,
        "n_sinc":  ns,
        "n_max":   n_max,
    }


def calc_fluxo_potencia(s: float, mp) -> dict:
    """Computes the power flow at the operating point.

    Parameters extracted from mp (user parameters).
    Returns P_in, P_cu1, P_ag, P_cu2, P_mec, P_out, eta, I1_rms, I2_rms, region.
    """
    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)

    if abs(s) < 1e-9:
        s = 1e-9

    Z2  = (R2 / s) + 1j * X2
    Zeq = (1j * Xm * Z2) / (1j * Xm + Z2)
    Zt  = R1 + 1j * X1 + Zeq
    I1  = V1 / Zt
    Veq = I1 * Zeq
    I2  = Veq / Z2

    P_in  = 3.0 * (V1 * np.conj(I1)).real
    P_cu1 = 3.0 * abs(I1) ** 2 * R1
    P_ag  = 3.0 * abs(I2) ** 2 * (R2 / s)    # = P_in - P_cu1
    P_cu2 = s * P_ag
    P_mec = (1.0 - s) * P_ag
    P_out = P_mec                              # no rotational losses modelled

    eta = (P_out / P_in * 100.0) if P_in != 0 else 0.0

    if s < 0:
        region = "Generator"
    elif s > 1:
        region = "Braking"
    else:
        region = "Motor"

    return {
        "P_in":   float(P_in),
        "P_cu1":  float(P_cu1),
        "P_ag":   float(P_ag),
        "P_cu2":  float(P_cu2),
        "P_mec":  float(P_mec),
        "P_out":  float(P_out),
        "eta":    float(eta),
        "I1_rms": float(abs(I1)),
        "I2_rms": float(abs(I2)),
        "region": region,
        "slip":   float(s),
    }


def build_fig_tn(tn: dict, dark: bool,
                 Te_op: float | None = None, n_op: float | None = None) -> go.Figure:
    """Plots the T×n curve with all 3 operating regions."""
    pt  = _plot_theme(dark)
    ns  = tn["n_sinc"]

    # region colours
    col_motor   = "#4f8ef7" if dark else "#1d4ed8"
    col_gen     = "#34d399" if dark else "#059669"
    col_brake   = "#f87171" if dark else "#dc2626"
    col_op      = "#fbbf24" if dark else "#d97706"

    s_arr = tn["s"]
    Te    = tn["Te"]
    n_rpm = tn["n_rpm"]
    n_max_pct = tn["n_max"] / ns * 100.0

    mask_motor  = (s_arr > 0) & (s_arr <= 1.0)
    mask_gen    = s_arr < 0
    mask_brake  = s_arr > 1.0

    fig = go.Figure()

    # ── regions ──────────────────────────────────────────────────────────────
    for mask, col, name in [
        (mask_motor, col_motor, "Motor (0 < s ≤ 1)"),
        (mask_gen,   col_gen,   "Generator (s < 0)"),
        (mask_brake, col_brake, "Braking (s > 1)"),
    ]:
        if mask.any():
            fig.add_trace(go.Scatter(
                x=n_rpm[mask] / ns * 100.0, y=Te[mask],
                mode="lines", name=name,
                line=dict(color=col, width=2.2),
                hovertemplate="n = %{x:.1f} %ns<br>Te = %{y:.2f} N·m<extra>" + name + "</extra>",
            ))

    # ── pull-out (peak) point ─────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[n_max_pct], y=[tn["Te_max"]],
        mode="markers+text", name="Te,max (pull-out)",
        marker=dict(color=col_motor, size=9, symbol="circle"),
        text=[f"Te,max = {tn['Te_max']:.1f} N·m"],
        textposition="top right",
        textfont=dict(color=pt["fg"], size=10),
        hovertemplate=f"n = {n_max_pct:.1f} %ns<br>Te,max = {tn['Te_max']:.2f} N·m<extra>Pull-out</extra>",
    ))

    # ── starting point (s=1) ─────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[0.0], y=[tn["Te_part"]],
        mode="markers+text", name="Te,start (s=1)",
        marker=dict(color=col_motor, size=7, symbol="circle-open"),
        text=[f"Te,s = {tn['Te_part']:.1f} N·m"],
        textposition="top right",
        textfont=dict(color=pt["fg"], size=10),
        hovertemplate=f"Te,start = {tn['Te_part']:.2f} N·m<extra>Starting</extra>",
    ))

    # ── simulation operating point ────────────────────────────────────────────
    if Te_op is not None and n_op is not None:
        fig.add_trace(go.Scatter(
            x=[n_op / ns * 100.0], y=[Te_op],
            mode="markers", name="Operating Point",
            marker=dict(color=col_op, size=10, symbol="diamond"),
            hovertemplate=f"n = {n_op:.1f} rpm<br>Te = {Te_op:.2f} N·m<extra>Operating</extra>",
        ))

    # ── synchronous speed line ────────────────────────────────────────────────
    fig.add_vline(x=100.0, line_dash="dash", line_color=pt["grid"], line_width=1,
                  annotation_text="ns", annotation_font_color=pt["fg"],
                  annotation_position="top right")

    # ── region annotations ────────────────────────────────────────────────────
    for txt, xref, col in [
        ("Motor",     50.0, col_motor),
        ("Generator", 115.0, col_gen),
        ("Braking",   -50.0, col_brake),
    ]:
        fig.add_annotation(x=xref, y=tn["Te_max"] * 0.15,
                           text=txt, showarrow=False,
                           font=dict(color=col, size=10, family="Inter, system-ui"),
                           xref="x", yref="y")

    fig.update_layout(
        height=420,
        title=dict(text="Characteristic T×n Curve — Three Operating Regions",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=50, b=50),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(title="Speed (% of synchronous speed)",
                   showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
                   zeroline=True, zerolinecolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   ticksuffix=" %"),
        yaxis=dict(title="Electromagnetic Torque Te (N·m)",
                   showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
                   tickfont=dict(size=10, color=pt["fg"]),
                   autorange=True),
    )
    return fig


def build_fig_fluxo_potencia(fp: dict, dark: bool) -> go.Figure:
    """Horizontal bar chart showing the power flow."""
    pt = _plot_theme(dark)

    labels = ["P_in", "P_cu1 (stator\ncopper)", "P_ag\n(air gap)",
              "P_cu2 (rotor\ncopper)", "P_mec\n(mechanical)", "P_out\n(output)"]
    values = [fp["P_in"], fp["P_cu1"], fp["P_ag"], fp["P_cu2"], fp["P_mec"], fp["P_out"]]
    colors = ["#94a3b8", "#f87171", "#4f8ef7", "#f87171", "#34d399", "#059669"]
    if not dark:
        colors = ["#64748b", "#dc2626", "#1d4ed8", "#dc2626", "#059669", "#065f46"]

    texts = [f"{v:,.1f} W" for v in values]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=texts,
        textposition="outside",
        textfont=dict(size=10, color=pt["fg"]),
        hovertemplate="%{y}: %{x:,.1f} W<extra></extra>",
    ))

    eta_str = f"η = {fp['eta']:.1f} %"
    region_str = fp["region"]

    fig.update_layout(
        height=320,
        title=dict(
            text=f"Power Flow at Operating Point — {region_str} | {eta_str}",
            x=0.5, xanchor="center", font=dict(size=12, color=pt["fg"])
        ),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=130, r=80, t=50, b=30),
        xaxis=dict(title="Power (W)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(tickfont=dict(size=10, color=pt["fg"]), autorange="reversed"),
        showlegend=False,
    )
    return fig


def _op_on_curve(tn: dict, res: dict):
    """Returns (Te_op, n_op) projected onto the T×n curve.

    Uses Te_ss from the simulation and interpolates in the stable region (0 < s < s_max)
    to find the corresponding speed on the curve. This ensures the
    point lies on the curve with the correct torque value.
    """
    Te_ss = float(res.get("Te_ss", 0.0))
    if Te_ss <= 0:
        return None, None

    s_arr  = tn["s"]
    Te_arr = tn["Te"]
    n_arr  = tn["n_rpm"]

    # stable motor region: s between 0 and s_max (Te increases monotonically with s)
    mask = (s_arr > 0) & (s_arr <= tn["s_max"])
    if not mask.any():
        return None, None

    Te_stable = Te_arr[mask]
    n_stable  = n_arr[mask]

    if Te_ss > Te_stable.max():
        return None, None  # beyond pull-out torque

    # interpolation: Te_stable increasing → n_stable decreasing
    n_op  = float(np.interp(Te_ss, Te_stable, n_stable))
    return Te_ss, n_op


