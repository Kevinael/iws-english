# -*- coding: utf-8 -*-
"""
theory_interactive.py
=====================
Self-contained interactive Plotly components for the Theory tab — reads machine parameters from session_state and renders sliders and charts.

Responsibilities:
  - Render Boucherot circle, operating zones, starting comparison, Park dynamics, Sankey,
    phasor unbalance, MCSA, braking comparator, and Krause block diagram.
  - Read machine parameters from st.session_state (fallback: Krause 3 HP motor defaults).
  - Expose each component as a standalone render_*() function callable from ui/theory.py.

Relationships:
  Imported by : ui.theory
  Imports     : viz.plotly_charts, viz.eqcircuit_plotter, core.curva_tn

Extending:
  - To add a new interactive component, create render_<name>() here and register it in ui/theory.py.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import io
import matplotlib
try:
    matplotlib.use("Agg")
except Exception:
    pass
import matplotlib.pyplot as plt

from viz.plotly_charts import _plot_theme
from viz.eqcircuit_plotter import build_figure
from core.mit_torque_speed import _extract_params, _torque_array, calc_fluxo_potencia


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK PARAMETERS — Krause 3HP Motor (NEMA, 60 Hz)
# ─────────────────────────────────────────────────────────────────────────────

class _FallbackMP:
    """Minimal subset of MachineParams for interactive components."""
    Vl    = 220.0          # phase voltage RMS (V)
    f     = 60.0           # frequency (Hz)
    Rs    = 0.435          # stator resistance (Ω)
    Rr    = 0.816          # rotor resistance (Ω)
    Xm    = 26.13          # magnetizing reactance (Ω)
    Xls   = 0.754          # stator leakage reactance (Ω)
    Xlr   = 0.754          # rotor leakage reactance (Ω)
    Rfe   = 500.0
    p     = 4              # number of poles
    J     = 0.089          # inertia (kg·m²)
    B     = 0.0

    @property
    def wb(self):
        return 2.0 * np.pi * self.f

    @property
    def Lm(self):
        return self.Xm / self.wb

    @property
    def Xls_a(self):
        return self.Xls

    @property
    def Xlr_a(self):
        return self.Xlr

    @property
    def n_sync(self):
        return 120.0 * self.f / self.p


_MP_DEFAULT = _FallbackMP()


def _get_mp():
    """Returns MachineParams from the last simulation or the fallback."""
    res = st.session_state.get("sim_result")
    if res and "mp" in res:
        return res["mp"]
    return _MP_DEFAULT


def _dark() -> bool:
    return bool(st.session_state.get("dark_mode", False))


# ─────────────────────────────────────────────────────────────────────────────
# 1. BOUCHEROT INTERATIVO — Te×s com slider de R'₂
# ─────────────────────────────────────────────────────────────────────────────

def render_boucherot() -> None:
    """T×s chart with native Plotly slider (zero latency) — Boucherot's theorem.

    Pre-computes N_STEPS curves for the R'₂ grid and packs them as Plotly frames.
    The JS slider moves between frames on the client, without Streamlit rerun.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2_nom, X2, Xm, ws_mec, ns = _extract_params(mp)

    # Thevenin
    Zth  = (1j * Xm * (R1 + 1j * X1)) / (R1 + 1j * (X1 + Xm))
    Rth  = Zth.real
    Xth  = Zth.imag
    Vth  = abs(V1 * 1j * Xm / (R1 + 1j * (X1 + Xm)))
    Tmax = 3.0 * Vth**2 / (2.0 * ws_mec * (Rth + np.sqrt(Rth**2 + (Xth + X2)**2)))

    # R'₂ grid — 60 logarithmic steps between 0.2× and 5× nominal
    N_STEPS = 60
    r2_grid = np.geomspace(R2_nom * 0.2, 3.0, N_STEPS)
    # Initial index: closest nominal value
    nom_idx = int(np.argmin(np.abs(r2_grid - R2_nom)))

    def _make_s_arr(scr: float) -> np.ndarray:
        """Adaptive s grid: high density around s_cr."""
        wing = min(scr * 0.8, 0.15)
        return np.unique(np.concatenate([
            np.linspace(1e-4, max(1e-4, scr - wing), 200),
            np.linspace(max(1e-4, scr - wing), min(1.0, scr + wing), 300),
            np.linspace(min(1.0, scr + wing), 1.0, 100),
            np.linspace(1.001, 2.0, 60),
        ]))

    col_sel  = "#4f8ef7" if dark else "#1d4ed8"
    col_peak = "#f97316"
    col_scr  = "#a78bfa" if dark else "#7c3aed"

    # Initial curve (frame nom_idx)
    r2_init   = r2_grid[nom_idx]
    scr_init  = r2_init / np.sqrt(Rth**2 + (Xth + X2)**2)
    s_arr_i   = _make_s_arr(scr_init)
    Te_init   = _torque_array(s_arr_i, V1, R1, X1, r2_init, X2, Xm, ws_mec)
    peak_idx  = int(np.argmax(Te_init))
    s_peak_i  = float(s_arr_i[peak_idx])
    Te_peak_i = float(Te_init[peak_idx])

    # Fixed s_arr to compute Te_max_plot (worst case = min R2, smaller scr)
    s_ref     = _make_s_arr(R2_nom * 0.2 / np.sqrt(Rth**2 + (Xth + X2)**2))

    Te_max_plot = float(Tmax) * 1.25

    # ── figura base ──────────────────────────────────────────────────────────
    fig = go.Figure()

    # Trace 0 — main curve (varies per frame)
    fig.add_trace(go.Scatter(
        x=s_arr_i, y=Te_init,
        mode="lines",
        name=f"R'₂ = {r2_init:.3f} Ω",
        line=dict(color=col_sel, width=3),
    ))

    # Trace 1 — marcador no pico
    fig.add_trace(go.Scatter(
        x=[s_peak_i], y=[Te_peak_i],
        mode="markers+text",
        text=[f"T_max = {Te_peak_i:.1f} N·m"],
        textposition="top center",
        textfont=dict(color=col_peak, size=11),
        marker=dict(color=col_peak, size=12, symbol="circle",
                    line=dict(color=pt["paper_bg"], width=2)),
        showlegend=False,
    ))

    # Trace 2 — linha vertical pontilhada descendo do pico ao eixo X
    fig.add_trace(go.Scatter(
        x=[s_peak_i, s_peak_i], y=[0, Te_peak_i],
        mode="lines",
        line=dict(color=col_peak, width=1.5, dash="dot"),
        showlegend=False,
    ))

    # Trace 3 — s_cr marker on axis (y=0) with label
    fig.add_trace(go.Scatter(
        x=[s_peak_i], y=[0],
        mode="markers+text",
        text=[f"s_cr = {s_peak_i:.3f}"],
        textposition="top center",
        textfont=dict(color=col_scr, size=10),
        marker=dict(color=col_scr, size=8, symbol="triangle-up"),
        showlegend=False,
    ))

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    for i, r2 in enumerate(r2_grid):
        scr   = r2 / np.sqrt(Rth**2 + (Xth + X2)**2)
        s_f   = _make_s_arr(scr)
        Te    = _torque_array(s_f, V1, R1, X1, r2, X2, Xm, ws_mec)
        pidx  = int(np.argmax(Te))
        sp    = float(s_f[pidx])
        Tp    = float(Te[pidx])
        label = f"{r2:.3f}"
        frames.append(go.Frame(
            name=str(i),
            data=[
                go.Scatter(x=s_f, y=Te, name=f"R'₂ = {r2:.3f} Ω"),
                go.Scatter(x=[sp], y=[Tp],
                           text=[f"T_max = {Tp:.1f} N·m"],
                           textposition="top center"),
                go.Scatter(x=[sp, sp], y=[0, Tp]),
                go.Scatter(x=[sp], y=[0],
                           text=[f"s_cr = {sp:.3f}"]),
            ],
            traces=[0, 1, 2, 3],
        ))
        slider_steps.append(dict(
            method="animate",
            label=label,
            args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                 transition=dict(duration=0))],
        ))

    fig.frames = frames

    # ── layout com slider JS ─────────────────────────────────────────────────
    fig.update_layout(
        height=460,
        title=dict(text="T×s Curve — Boucherot's Theorem (T_max invariant with R'₂)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=130),
        xaxis=dict(title="Slip s", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]), range=[0, 2.0],
                   zeroline=True, zerolinecolor=pt["grid"]),
        yaxis=dict(title="Torque (N·m)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   range=[0, Te_max_plot]),
        showlegend=True,
        legend=dict(
            x=0.98, y=0.98, xanchor="right", yanchor="top",
            font=dict(size=10, color=pt["fg"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        sliders=[dict(
            active=nom_idx,
            currentvalue=dict(
                prefix="R'₂ = ",
                suffix=" Ω",
                visible=True,
                xanchor="center",
                font=dict(size=13, color=pt["fg"]),
            ),
            # y=0 anchors the slider at the bottom of the paper; pad pushes it below the X axis
            y=0,
            pad=dict(t=55, b=10),
            len=0.92,
            x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"],
            bordercolor=pt["grid"],
            tickcolor=pt["fg"],
            font=dict(color=pt["fg"], size=9),
        )],
        # hidden updatemenus required for slider animate to work
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )

    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


# ─────────────────────────────────────────────────────────────────────────────
# 2. OPERATING ZONES — Te×n with colored zones and vector diagram
# ─────────────────────────────────────────────────────────────────────────────

def render_zonas_operacao() -> None:
    """T×n chart with three colored zones and ωs/ωm vector diagram."""
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)

    # Select zone for the vector diagram
    zona = st.radio(
        "Operating region",
        options=["Motor (0 < s < 1)", "Generator (s < 0)", "Braking (s > 1)"],
        horizontal=True,
        key="th_zona_radio",
    )

    # Arrays per region
    s_brake  = np.linspace(1.001, 2.0,  150)
    s_motor  = np.linspace(1e-4,  1.0,  400)
    s_gen    = np.linspace(-1.0, -1e-4, 150)

    Te_brake = _torque_array(s_brake, V1, R1, X1, R2, X2, Xm, ws_mec)
    Te_motor = _torque_array(s_motor, V1, R1, X1, R2, X2, Xm, ws_mec)
    Te_gen   = _torque_array(s_gen,   V1, R1, X1, R2, X2, Xm, ws_mec)

    n_brake = ns * (1.0 - s_brake)
    n_motor = ns * (1.0 - s_motor)
    n_gen   = ns * (1.0 - s_gen)

    alpha_zone = 0.18

    col_motor = "#4f8ef7" if dark else "#1d4ed8"
    col_gen   = "#34d399" if dark else "#059669"
    col_brake = "#f87171" if dark else "#dc2626"

    fig = go.Figure()

    # Background bands per zone
    fig.add_vrect(x0=float(n_brake.min()), x1=float(n_brake.max()),
                  fillcolor=col_brake, opacity=alpha_zone, layer="below", line_width=0)
    fig.add_vrect(x0=0.0, x1=float(ns),
                  fillcolor=col_motor, opacity=alpha_zone, layer="below", line_width=0)
    fig.add_vrect(x0=float(ns), x1=float(n_gen.max()),
                  fillcolor=col_gen, opacity=alpha_zone, layer="below", line_width=0)

    # Curves
    fig.add_trace(go.Scatter(x=n_brake, y=Te_brake, mode="lines",
                             name="Braking", line=dict(color=col_brake, width=2.5)))
    fig.add_trace(go.Scatter(x=n_motor, y=Te_motor, mode="lines",
                             name="Motor", line=dict(color=col_motor, width=2.5)))
    fig.add_trace(go.Scatter(x=n_gen, y=Te_gen, mode="lines",
                             name="Generator", line=dict(color=col_gen, width=2.5)))

    # Synchronous speed line
    fig.add_vline(x=float(ns), line_dash="dash", line_color=pt["fg"],
                  line_width=1.5, annotation_text=f"ns = {ns:.0f} RPM",
                  annotation_font_color=pt["fg"])

    fig.update_layout(
        height=340,
        title=dict(text="T×n Curve — Three Operating Regions",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=45),
        xaxis=dict(title="Speed (RPM)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(title="Torque (N·m)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    # Animated phasor diagram
    _render_diagrama_vetorial(zona, dark, ns)


@st.fragment
def _render_diagrama_vetorial(zona: str, dark: bool, ns: float) -> None:
    """Animated vector diagram via requestAnimationFrame in HTML iframe.

    θs rotates continuously. θm = θs − s·2π (fixed phase shift).
    No play/pause buttons — animation starts automatically.
    """
    if zona.startswith("Motor"):
        s_val = st.slider("Slip s", 0.01, 0.99, 0.05, step=0.01,
                          format="%.2f", key="_vetorial_s_motor")
    elif zona.startswith("Generator"):
        s_val = st.slider("Slip s", -0.99, -0.01, -0.05, step=0.01,
                          format="%.2f", key="_vetorial_s_gen")
    else:
        s_val = st.slider("Slip s", 1.01, 2.50, 1.50, step=0.01,
                          format="%.2f", key="_vetorial_s_brake")

    wr_rpm = ns * (1.0 - s_val)
    st.caption(f"ωm = {wr_rpm:.0f} RPM  |  ωs = {ns:.0f} RPM  |  Δn = {wr_rpm - ns:.0f} RPM")

    if zona.startswith("Motor"):
        col_rotor = "#4f8ef7" if dark else "#1d4ed8"
        titulo    = f"Motor — ωm < ωs  (s = {s_val:.0%})"
        desc      = f"Field pulls the rotor. Fixed separation Δθ = {s_val*360:.0f}°. Torque in the direction of motion."
    elif zona.startswith("Generator"):
        col_rotor = "#34d399" if dark else "#059669"
        titulo    = f"Generator — ωm > ωs  (s = {s_val:.0%})"
        desc      = f"Rotor leads the field by {abs(s_val)*360:.0f}°. Torque opposes motion — generation."
    else:
        col_rotor = "#f87171" if dark else "#dc2626"
        titulo    = f"Braking — ωm < 0  (s = {s_val:.2f})"
        desc      = "Rotor spins opposite to the field. Kinetic + electrical energy dissipated as heat."

    bg_hex   = "#151a24" if dark else "#ffffff"
    fg_hex   = "#e5e7eb" if dark else "#111111"
    grid_hex = "#2a2a3a" if dark else "#cccccc"
    delta_deg = abs(s_val) * 360.0

    # visual cycle: 1 field revolution in 3 seconds
    cycle_ms = 3000.0

    html_src = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:{bg_hex}; display:flex; justify-content:center; }}
  #gv {{ width:320px; height:360px; }}
</style>
</head><body>
<div id="gv"></div>
<script>
(function(){{
  var PI2      = 2 * Math.PI;
  var sVal     = {s_val:.6f};
  var cycleMs  = {cycle_ms:.1f};
  var colRotor = "{col_rotor}";
  var colField = "{fg_hex}";
  var colGrid  = "{grid_hex}";
  var colBg    = "{bg_hex}";
  var deltaLbl = "{delta_deg:.0f}°  (s = {s_val:+.2f})";
  var titulo   = "{titulo}";

  // reference circle
  var N = 120;
  var cx = [], cy = [];
  for (var i = 0; i <= N; i++) {{
    cx.push(Math.cos(PI2 * i / N));
    cy.push(Math.sin(PI2 * i / N));
  }}

  var data = [
    // trace 0: circle
    {{ x: cx, y: cy, mode:"lines", line:{{color:colGrid, width:1, dash:"dot"}},
      showlegend:false, hoverinfo:"skip" }},
    // trace 1: centro
    {{ x:[0], y:[0], mode:"markers", marker:{{color:colField, size:6}},
      showlegend:false, hoverinfo:"skip" }},
    // trace 2: stator field vector
    {{ x:[0,1], y:[0,0], mode:"lines+markers",
      line:{{color:colField, width:3}},
      marker:{{size:[0,10], color:colField}},
      name:"ωs (field)" }},
    // trace 3: rotor vector
    {{ x:[0,1], y:[0,0], mode:"lines+markers",
      line:{{color:colRotor, width:3, dash:"dash"}},
      marker:{{size:[0,10], color:colRotor}},
      name:"ωm (rotor)" }},
    // trace 4: Δθ annotation
    {{ x:[0], y:[-1.35], mode:"text",
      text:["Δθ = " + deltaLbl],
      textfont:{{size:10, color:colRotor}},
      showlegend:false, hoverinfo:"skip" }},
  ];

  var layout = {{
    width:320, height:360,
    paper_bgcolor:colBg, plot_bgcolor:colBg,
    title:{{text:titulo, x:0.5, xanchor:"center",
            font:{{size:11, color:colField}}}},
    xaxis:{{range:[-1.6,1.6], showgrid:false, zeroline:false, showticklabels:false,
             scaleanchor:"y"}},
    yaxis:{{range:[-1.6,1.6], showgrid:false, zeroline:false, showticklabels:false}},
    margin:{{l:10, r:10, t:40, b:30}},
    font:{{color:colField}},
    legend:{{orientation:"h", x:0.5, xanchor:"center", y:-0.08,
             font:{{size:10, color:colField}}, bgcolor:"rgba(0,0,0,0)"}},
  }};

  var cfg = {{displaylogo:false, staticPlot:false, responsive:false}};
  var startTs = null;
  var gv;

  Plotly.newPlot('gv', data, layout, cfg).then(function(div){{
    gv = div;
    requestAnimationFrame(tick);
  }});

  function tick(ts) {{
    if (!startTs) startTs = ts;
    var frac  = ((ts - startTs) % cycleMs) / cycleMs;
    var theta = frac * PI2;
    var thetaM = theta - sVal * PI2;
    Plotly.restyle(gv,
      {{ x: [[0, Math.cos(theta)],  [0, Math.cos(thetaM)]],
         y: [[0, Math.sin(theta)],  [0, Math.sin(thetaM)]] }},
      [2, 3]
    );
    requestAnimationFrame(tick);
  }}
}})();
</script>
</body></html>"""

    st.iframe(html_src, height=370)
    st.caption(desc)


# ─────────────────────────────────────────────────────────────────────────────
# 3. COMPARATIVO DE PARTIDAS — corrente×tempo
# ─────────────────────────────────────────────────────────────────────────────

def render_comparativo_partidas() -> None:
    """Analytical phase current vs. time curves for DOL, Y-D and Soft-Starter."""
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)
    # Impedance at s=1 (starting)
    Z2_start  = R2 + 1j * X2
    Zeq_start = (1j * Xm * Z2_start) / (1j * Xm + Z2_start)
    Ztotal    = R1 + 1j * X1 + Zeq_start
    I_dol     = abs(V1 / Ztotal)           # pico de corrente DOL (A)
    # Nominal current: uses s ≈ 0.04
    Z2_nom   = (R2 / 0.04) + 1j * X2
    Zeq_nom  = (1j * Xm * Z2_nom) / (1j * Xm + Z2_nom)
    Zt_nom   = R1 + 1j * X1 + Zeq_nom
    I_nom    = abs(V1 / Zt_nom)

    # Approximate electrical time constant
    tau_e  = (X1 + Xm * X2 / (Xm + X2)) / (2.0 * np.pi * mp.f * max(R1 + R2, 0.01))
    t_acc  = max(tau_e * 4.0, 0.3)        # time to steady state
    t_max  = t_acc * 2.5

    t = np.linspace(0.0, t_max, 800)

    def _envelope(I_peak, tau):
        """Exponential decay envelope of the current transient."""
        env = I_nom + (I_peak - I_nom) * np.exp(-t / max(tau, 1e-6))
        return np.maximum(env, I_nom)

    # DOL
    i_dol = _envelope(I_dol, tau_e)

    # Y-D: Y phase uses V/√3 → current reduced to 1/3
    t_yd  = t_acc * 0.6          # Y→D switching instant
    i_yd  = np.where(
        t < t_yd,
        _envelope(I_dol / 3.0, tau_e),
        _envelope(I_dol * 0.7, tau_e * 0.5),   # smaller peak in second transient
    )

    # Soft-Starter: voltage ramp from 0 → V over t_ramp
    t_ramp = t_acc * 0.8
    v_ramp = np.clip(t / t_ramp, 0.0, 1.0)
    i_ss   = _envelope(I_dol * v_ramp, tau_e * 0.4) * v_ramp
    i_ss   = np.maximum(i_ss, I_nom * v_ramp)

    # Method selection
    metodos = st.multiselect(
        "Starting methods",
        options=["DOL (Direct)", "Star-Delta (Y-D)", "Soft-Starter"],
        default=["DOL (Direct)", "Star-Delta (Y-D)", "Soft-Starter"],
        key="th_partidas_sel",
    )

    col_dol = "#f87171" if dark else "#dc2626"
    col_yd  = "#4f8ef7" if dark else "#1d4ed8"
    col_ss  = "#34d399" if dark else "#059669"

    fig = go.Figure()

    if "DOL (Direct)" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_dol, mode="lines", name="DOL",
                                 line=dict(color=col_dol, width=2.5)))
    if "Star-Delta (Y-D)" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_yd, mode="lines", name="Y-D",
                                 line=dict(color=col_yd, width=2.5, dash="dash")))
        fig.add_vline(x=t_yd, line_dash="dot", line_color=col_yd, line_width=1,
                      annotation_text="Y→D", annotation_font_color=col_yd)
    if "Soft-Starter" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_ss, mode="lines", name="Soft-Starter",
                                 line=dict(color=col_ss, width=2.5, dash="longdash")))

    # Linha de corrente nominal
    fig.add_hline(y=I_nom, line_dash="dot", line_color=pt["fg"], line_width=1.2,
                  annotation_text=f"I_nom ≈ {I_nom:.1f} A",
                  annotation_font_color=pt["fg"])

    fig.update_layout(
        height=340,
        title=dict(text="Starting Method Comparison — Phase Current (analytical model)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=45),
        xaxis=dict(title="Time (s)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(title="Phase current (A)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


# ─────────────────────────────────────────────────────────────────────────────
# 4. DYNAMIC PARK TRANSFORM — vector plane + time series
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _build_fig_park(ref: str, dark: bool) -> tuple[go.Figure, str]:
    """Plotly frames animation of Clarke/Park transform — vector plane + time series."""
    from plotly.subplots import make_subplots

    bg_hex   = "#151a24" if dark else "#ffffff"
    fg_hex   = "#e5e7eb" if dark else "#111111"
    grid_hex = "#2a2a3a" if dark else "#cccccc"
    col_a    = "#4f8ef7" if dark else "#1d4ed8"
    col_b    = "#f87171" if dark else "#dc2626"
    col_vec  = "#f97316"

    s_typ    = 0.5
    n_cycles = round(1.0 / s_typ) if ref == "rotor" else 1
    N        = 60 * n_cycles
    t        = np.linspace(0.0, float(n_cycles), N, endpoint=False)
    th_e     = 2.0 * np.pi * t

    Vs_a = np.cos(th_e)
    Vs_b = np.sin(th_e)

    if ref == "dq":
        Vx = np.zeros(N)
        Vz = np.ones(N)
        lbl_x = "Vds  (direct axis)"
        lbl_z = "Vqs  (quadrature axis)"
        titulo = "Park — dq reference frame (synchronous)"
        desc   = ("In the dq reference frame, the d and q axes rotate at ωe together with the voltage vector (orange). "
                  "Therefore Vqs = constant and Vds = 0 in steady state — the vector appears stationary.")
        modo   = "dq"
        vec_x  = Vs_a
        vec_z  = Vs_b
    elif ref == "rotor":
        th_r = 2.0 * np.pi * s_typ * t
        Vx = np.cos(th_r)
        Vz = np.sin(th_r)
        lbl_x = "Vdr  (direct component — rotor-fixed)"
        lbl_z = "Vqr  (quadrature component)"
        titulo = f"Rotor reference frame — stator vector rotates at s·ωe  (s={s_typ} illustrative)"
        desc   = (f"In the rotor reference frame, the axes rotate at ωr = (1−s)·ωe. "
                  f"The stator voltage vector (orange) oscillates at the slip frequency fs = s·fe. "
                  f"In real motors s ≈ 0.02–0.08; s={s_typ} is used here to make the animation visible.")
        modo   = "rotor"
        vec_x  = Vx
        vec_z  = Vz
    else:
        Vx = Vs_a
        Vz = Vs_b
        lbl_x = "Vα  (horizontal component — stationary axis)"
        lbl_z = "Vβ  (vertical component — 90° from Vα)"
        titulo = "Clarke — αβ reference frame (stationary)"
        desc   = ("In the αβ reference frame, the axes are fixed in space. "
                  "The voltage vector (orange) rotates at ωe: "
                  "Vα and Vβ are sinusoidal with 90° phase shift between them.")
        modo   = "ab"
        vec_x  = Vs_a
        vec_z  = Vs_b

    circ = np.linspace(0, 2 * np.pi, 120)

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.42, 0.58],
        subplot_titles=[titulo, "Time series"],
        horizontal_spacing=0.12,
    )

    # ── Vector plane (col 1) ──────────────────────────────────────────────────
    # Reference circle
    fig.add_trace(go.Scatter(
        x=np.cos(circ), y=np.sin(circ), mode="lines",
        line=dict(color=grid_hex, width=1, dash="dot"),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    # Axis lines
    fig.add_trace(go.Scatter(
        x=[-1.4, 1.4], y=[0, 0], mode="lines",
        line=dict(color=grid_hex, width=0.8),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[-1.4, 1.4], mode="lines",
        line=dict(color=grid_hex, width=0.8),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    # Rotating d-axis (dq only)
    if modo == "dq":
        d_x0, d_y0 = 1.3 * np.cos(th_e[0]), 1.3 * np.sin(th_e[0])
        q_x0, q_y0 = 1.3 * np.cos(th_e[0] + np.pi/2), 1.3 * np.sin(th_e[0] + np.pi/2)
        fig.add_trace(go.Scatter(
            x=[-d_x0, d_x0], y=[-d_y0, d_y0], mode="lines",
            line=dict(color=col_a, width=1.5), name="d-axis", showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=[-q_x0, q_x0], y=[-q_y0, q_y0], mode="lines",
            line=dict(color=col_b, width=1.5), name="q-axis", showlegend=True,
        ), row=1, col=1)
    # Main vector (orange)
    fig.add_trace(go.Scatter(
        x=[0, vec_x[0]], y=[0, vec_z[0]], mode="lines+markers",
        line=dict(color=col_vec, width=3),
        marker=dict(size=[0, 12], color=col_vec, symbol=["circle", "arrow"],
                    angleref="previous"),
        name="V (voltage vector)",
    ), row=1, col=1)
    # α/d projection
    fig.add_trace(go.Scatter(
        x=[vec_x[0]], y=[0], mode="markers",
        marker=dict(color=col_a, size=8), name=lbl_x,
    ), row=1, col=1)
    # β/q projection
    fig.add_trace(go.Scatter(
        x=[0], y=[vec_z[0]], mode="markers",
        marker=dict(color=col_b, size=8), name=lbl_z,
    ), row=1, col=1)

    # ── Time series (col 2) ────────────────────────────────────────────────────
    # Ghost curves (full background)
    fig.add_trace(go.Scatter(
        x=t, y=Vx, mode="lines",
        line=dict(color=col_a, width=1.2, dash="dot"),
        opacity=0.3, showlegend=False, hoverinfo="skip",
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=t, y=Vz, mode="lines",
        line=dict(color=col_b, width=1.2, dash="dot"),
        opacity=0.3, showlegend=False, hoverinfo="skip",
    ), row=1, col=2)
    # Animated traces (grow frame by frame)
    fig.add_trace(go.Scatter(
        x=t[:1], y=Vx[:1], mode="lines",
        line=dict(color=col_a, width=2), showlegend=False,
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=t[:1], y=Vz[:1], mode="lines",
        line=dict(color=col_b, width=2, dash="dash"), showlegend=False,
    ), row=1, col=2)
    # Cursor (current instant marker)
    fig.add_trace(go.Scatter(
        x=[t[0]], y=[Vx[0]], mode="markers",
        marker=dict(color=col_a, size=7), showlegend=False,
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=[t[0]], y=[Vz[0]], mode="markers",
        marker=dict(color=col_b, size=7), showlegend=False,
    ), row=1, col=2)
    # Vertical cursor line
    fig.add_trace(go.Scatter(
        x=[t[0], t[0]], y=[-1.4, 1.4], mode="lines",
        line=dict(color=fg_hex, width=0.8, dash="dot"),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=2)

    # ── Trace indices ─────────────────────────────────────────────────────────
    # col1: 0=circ, 1=axis_h, 2=axis_v, [3=d, 4=q if dq], vec, proj_a, proj_b
    # col2: ghost_a, ghost_b, line_a, line_b, cur_a, cur_b, vline
    if modo == "dq":
        i_vec   = 5
        i_pja   = 6
        i_pjb   = 7
        i_ga    = 8
        i_gb    = 9
        i_la    = 10
        i_lb    = 11
        i_ca    = 12
        i_cb    = 13
        i_vl    = 14
    else:
        i_vec   = 3
        i_pja   = 4
        i_pjb   = 5
        i_ga    = 6
        i_gb    = 7
        i_la    = 8
        i_lb    = 9
        i_ca    = 10
        i_cb    = 11
        i_vl    = 12

    # ── Frames ────────────────────────────────────────────────────────────────
    frames = []
    for i in range(N):
        frame_data = [None] * (i_vl + 1)
        # static traces (circle, axes)
        frame_data[0] = go.Scatter(x=np.cos(circ), y=np.sin(circ))
        frame_data[1] = go.Scatter(x=[-1.4, 1.4], y=[0, 0])
        frame_data[2] = go.Scatter(x=[0, 0], y=[-1.4, 1.4])
        if modo == "dq":
            d_x = 1.3 * np.cos(th_e[i]); d_y = 1.3 * np.sin(th_e[i])
            q_x = 1.3 * np.cos(th_e[i] + np.pi/2); q_y = 1.3 * np.sin(th_e[i] + np.pi/2)
            frame_data[3] = go.Scatter(x=[-d_x, d_x], y=[-d_y, d_y])
            frame_data[4] = go.Scatter(x=[-q_x, q_x], y=[-q_y, q_y])
        frame_data[i_vec] = go.Scatter(x=[0, vec_x[i]], y=[0, vec_z[i]])
        frame_data[i_pja] = go.Scatter(x=[vec_x[i]], y=[0])
        frame_data[i_pjb] = go.Scatter(x=[0], y=[vec_z[i]])
        frame_data[i_ga]  = go.Scatter(x=t, y=Vx)
        frame_data[i_gb]  = go.Scatter(x=t, y=Vz)
        frame_data[i_la]  = go.Scatter(x=t[:i+1], y=Vx[:i+1])
        frame_data[i_lb]  = go.Scatter(x=t[:i+1], y=Vz[:i+1])
        frame_data[i_ca]  = go.Scatter(x=[t[i]], y=[Vx[i]])
        frame_data[i_cb]  = go.Scatter(x=[t[i]], y=[Vz[i]])
        frame_data[i_vl]  = go.Scatter(x=[t[i], t[i]], y=[-1.4, 1.4])
        frames.append(go.Frame(
            data=[d for d in frame_data if d is not None],
            traces=list(range(i_vl + 1)),
            name=str(i),
        ))
    fig.frames = frames

    fig.update_layout(
        height=420,
        paper_bgcolor=bg_hex, plot_bgcolor=bg_hex,
        font=dict(family="Inter, system-ui", size=11, color=fg_hex),
        margin=dict(l=40, r=20, t=55, b=90),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=fg_hex), bgcolor="rgba(0,0,0,0)"),
        updatemenus=[dict(
            type="buttons", showactive=False,
            x=0.5, xanchor="center", y=-0.28,
            buttons=[
                dict(label="▶ Play",
                     method="animate",
                     args=[None, dict(frame=dict(duration=50, redraw=True),
                                      fromcurrent=True, mode="immediate")]),
                dict(label="⏸ Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
            font=dict(color=fg_hex),
            bgcolor=bg_hex,
            bordercolor=grid_hex,
        )],
    )
    fig.update_xaxes(
        range=[-1.5, 1.5], showgrid=False, zeroline=False,
        showticklabels=False, scaleanchor="y", row=1, col=1,
    )
    fig.update_yaxes(
        range=[-1.5, 1.5], showgrid=False, zeroline=False,
        showticklabels=False, row=1, col=1,
    )
    fig.update_xaxes(
        title_text="ωe cycles", showgrid=True, gridcolor=grid_hex,
        range=[0, float(n_cycles)], row=1, col=2,
    )
    fig.update_yaxes(
        title_text="Amplitude (p.u.)", showgrid=True, gridcolor=grid_hex,
        range=[-1.4, 1.4], row=1, col=2,
    )
    fig.update_annotations(font_color=fg_hex)

    return fig, desc


def render_park_dinamico() -> None:
    """Plotly animation of Clarke/Park transform — rotating vector + time series."""
    dark = _dark()

    ref = st.radio(
        "Reference frame",
        options=["dq (synchronous — Park)", "rotor (ωref = ωr)", "αβ (stationary — Clarke)"],
        horizontal=True,
        key="th_park_ref",
    )
    if ref.startswith("dq"):
        ref_key = "dq"
    elif ref.startswith("rotor"):
        ref_key = "rotor"
    else:
        ref_key = "ab"

    fig, desc = _build_fig_park(ref_key, dark)
    st.plotly_chart(fig, config={"displaylogo": False}, width="stretch")
    st.caption(desc)


# ─────────────────────────────────────────────────────────────────────────────
# 5. POWER FLOW — horizontal bars with Plotly slider (zero latency)
# ─────────────────────────────────────────────────────────────────────────────

def render_sankey_potencia() -> None:
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

    LABELS = ["P_input", "P_cu1 (stator copper)", "P_ag (air-gap)",
              "P_cu2 (rotor copper)", "P_mec (conv.)", "P_output"]

    def _make_frame_data(s: float):
        fp     = calc_fluxo_potencia(s, mp)
        P_in   = fp["P_in"]
        P_cu1  = fp["P_cu1"]
        P_ag   = fp["P_ag"]
        P_cu2  = fp["P_cu2"]
        P_mec  = fp["P_mec"]
        P_out  = fp["P_out"]
        region = fp["region"]
        eta    = fp["eta"]

        vals   = [abs(P_in), abs(P_cu1), abs(P_ag), abs(P_cu2), abs(P_mec), abs(P_out)]
        cols   = [COL_PIN, COL_CU1, COL_AG, COL_CU2, COL_MEC, COL_OUT]
        txts   = [_fmt(P_in), _fmt(P_cu1), _fmt(P_ag),
                  _fmt(P_cu2), _fmt(P_mec), _fmt(P_out)]

        traces = []
        for i, (lbl, val, col, txt) in enumerate(zip(LABELS, vals, cols, txts)):
            traces.append(go.Bar(
                name=lbl,
                x=[val],
                y=["Power"],
                orientation="h",
                marker_color=col,
                text=[txt],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=11, color="#ffffff"),
                hovertemplate=f"{lbl}: {txt}<extra></extra>",
            ))

        # final trace: dynamic title as annotation via invisible scatter
        traces.append(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(opacity=0),
            showlegend=False,
            hoverinfo="skip",
            name=f"{region} | η={eta:.1f}% | s={s:.3f}",
        ))
        return traces, region, eta

    # ── figura base ──────────────────────────────────────────────────────────
    init_traces, region_0, eta_0 = _make_frame_data(s_grid[nom_idx])
    fig = go.Figure(data=init_traces)

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    anim_args = dict(mode="immediate", frame=dict(duration=0, redraw=True),
                     transition=dict(duration=0))

    for i, s in enumerate(s_grid):
        trs, region, eta = _make_frame_data(s)
        frames.append(go.Frame(
            name=str(i),
            data=trs,
            traces=list(range(len(trs))),
        ))
        slider_steps.append(dict(
            method="animate",
            label=f"{s:.2f}",
            args=[[str(i)], anim_args],
        ))

    fig.frames = frames

    fig.update_layout(
        height=260,
        barmode="stack",
        title=dict(
            text=f"Power Flow — {region_0}  |  η = {eta_0:.1f}%  |  s = {s_grid[nom_idx]:.2f}",
            x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=20, r=20, t=55, b=110),
        xaxis=dict(
            title="Power (W)", showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
        ),
        yaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=-0.28,
            font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
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


# ─────────────────────────────────────────────────────────────────────────────
# 6. SYNCHRONISED TRANSIENTS — n, Te and ias for 3 scenarios
# ─────────────────────────────────────────────────────────────────────────────

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
    wb  = float(mp.wb)
    p   = int(mp.p)
    J   = float(mp.J)
    B   = float(mp.B) if mp.B > 0 else 0.005
    f   = float(mp.f)

    # ── Equivalent circuit parameters ────────────────────────────────────────
    # Impedance at s=1 → starting current
    Z2s1  = R2 + 1j * X2
    Zeqs1 = (1j * Xm * Z2s1) / (1j * Xm + Z2s1)
    Ztot1 = R1 + 1j * X1 + Zeqs1
    I_pk  = abs(V1 / Ztot1)           # corrente de pico a s=1 (A)
    # Steady state (s≈0.04)
    s_ss  = 0.04
    Z2ss  = (R2 / s_ss) + 1j * X2
    Zeqss = (1j * Xm * Z2ss) / (1j * Xm + Z2ss)
    Ztss  = R1 + 1j * X1 + Zeqss
    I_ss  = abs(V1 / Ztss)            # corrente nominal (A)
    # Torque
    Te_ss = float(_torque_array(np.array([s_ss]), V1, R1, X1, R2, X2, Xm, ws_mec)[0])
    Tl    = Te_ss * 0.85               # load applied after starting
    n_ss  = ns * (1.0 - s_ss)
    # Mechanical time constant for starting
    tau_mec = J * ws_mec / max(Te_ss, 1.0)

    col_n   = "#4f8ef7" if dark else "#1d4ed8"
    col_Te  = "#34d399" if dark else "#059669"
    col_ias = "#f97316"

    # ─────────────────────────────────────────────────────────────────────────
    # Scenario A — DOL Start + load application
    # ─────────────────────────────────────────────────────────────────────────
    t_max_A = max(tau_mec * 3.5, 4.0)
    t_A = np.linspace(0.0, t_max_A, 1200)
    t_load = t_max_A * 0.55           # load application instant

    # n(t): exponential starting curve, slight speed dip under load
    tau_acc = max(tau_mec * 0.8, 0.5)
    n_pre   = n_ss * (1.0 - np.exp(-t_A / tau_acc))
    delta_n = n_ss * 0.025            # dip of ~2.5%
    tau_sag = tau_acc * 0.3
    n_post  = np.where(
        t_A < t_load, n_pre,
        n_ss - delta_n * np.exp(-(t_A - t_load) / tau_sag),
    )
    n_A = n_post

    # Te(t): starting peak, decays to steady-state value, second transient at load
    s_arr_A = np.maximum(1.0 - n_A / ns, 1e-4)
    Te_A_raw = _torque_array(s_arr_A, V1, R1, X1, R2, X2, Xm, ws_mec)
    Te_A = np.clip(Te_A_raw, 0.0, None)

    # ias(t): exponential decay envelope of the inrush
    tau_e = (X1 + X2) / (2.0 * np.pi * f * max(R1 + R2, 0.01))
    env_A = I_ss + (I_pk - I_ss) * np.exp(-t_A / max(tau_e, 1e-3))
    env_A = np.where(t_A < t_load, env_A, np.maximum(env_A, I_ss * 1.18))
    ias_A = env_A * np.abs(np.sin(2.0 * np.pi * f * t_A))
    # mark event
    t_events_A = [t_load]

    # ─────────────────────────────────────────────────────────────────────────
    # Scenario B — Voltage Sag (30% voltage dip for 0.2 s)
    # ─────────────────────────────────────────────────────────────────────────
    t_sag_start = 1.0
    t_sag_dur   = 0.20
    t_sag_end   = t_sag_start + t_sag_dur
    t_max_B     = t_sag_end + 1.5
    t_B = np.linspace(0.0, t_max_B, 1200)

    sag_depth = 0.30                  # 30% drop of nominal voltage

    # n(t): at steady state, slight drop during sag, recovery after
    n_sag_drop = n_ss * 0.06 * sag_depth / 0.30
    tau_sag_n  = 0.08
    n_B = np.where(
        t_B < t_sag_start, n_ss,
        np.where(
            t_B < t_sag_end,
            n_ss - n_sag_drop * (1.0 - np.exp(-(t_B - t_sag_start) / tau_sag_n)),
            n_ss - n_sag_drop * np.exp(-(t_B - t_sag_end) / tau_sag_n),
        ),
    )

    # Te(t): drops proportionally to V² during sag, recovers afterwards
    Te_sag = Te_ss * (1.0 - sag_depth) ** 2
    tau_Te_rec = 0.06
    Te_B = np.where(
        t_B < t_sag_start, Te_ss,
        np.where(
            t_B < t_sag_end,
            Te_sag + (Te_ss - Te_sag) * np.exp(-(t_B - t_sag_start) / 0.04),
            Te_ss - (Te_ss - Te_sag) * np.exp(-(t_B - t_sag_end) / tau_Te_rec),
        ),
    )

    # ias(t): re-start current after sag (peak smaller than cold start)
    I_restart = I_ss * (1.0 + 2.5 * sag_depth)
    ias_B_env = np.where(
        t_B < t_sag_start, I_ss,
        np.where(
            t_B < t_sag_end,
            I_ss * (1.0 - sag_depth * 0.6),
            I_ss + (I_restart - I_ss) * np.exp(-(t_B - t_sag_end) / max(tau_e, 0.05)),
        ),
    )
    ias_B = ias_B_env * np.abs(np.sin(2.0 * np.pi * f * t_B))
    t_events_B = [t_sag_start, t_sag_end]

    # ─────────────────────────────────────────────────────────────────────────
    # Scenario C — Shutdown (supply cut at steady state)
    # ─────────────────────────────────────────────────────────────────────────
    t_cutoff = 0.5
    t_max_C  = t_cutoff + max(J * ws_mec / max(Tl * 0.5, 1.0), 2.0)
    t_C = np.linspace(0.0, t_max_C, 1200)

    # decay tau of n after cut: inertia / load
    tau_n_off = J / max(B + Tl / max(float(ws_mec), 1.0), 0.01)
    n_C = np.where(
        t_C < t_cutoff, n_ss,
        np.maximum(n_ss * np.exp(-(t_C - t_cutoff) / max(tau_n_off, 0.1)), 0.0),
    )

    # Te(t): drops rapidly to zero (electrical time constant)
    tau_Te_off = float(Xm / (wb * max(R2, 0.01))) * 0.15
    Te_C = np.where(
        t_C < t_cutoff, Te_ss,
        Te_ss * np.exp(-(t_C - t_cutoff) / max(tau_Te_off, 0.02)),
    )
    Te_C = np.maximum(Te_C, 0.0)

    # ias(t): decays exponentially with the magnetising flux time constant
    ias_C_env = np.where(
        t_C < t_cutoff, I_ss,
        I_ss * np.exp(-(t_C - t_cutoff) / max(tau_Te_off * 2, 0.05)),
    )
    ias_C = ias_C_env * np.abs(np.sin(2.0 * np.pi * f * t_C))
    t_events_C = [t_cutoff]

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
    def _event_traces(t_events, row_count=3, x_axis_sfx=None):
        ev_traces = []
        for te in t_events:
            for row in range(1, row_count + 1):
                sfx = str(row) if row > 1 else ""
                ev_traces.append(dict(
                    type="scatter",
                    x=[te, te], y=[0, 1],
                    yref=f"y{sfx} domain",
                    mode="lines",
                    line=dict(color=pt["event_line"], width=1.2, dash="dot"),
                    xaxis=f"x{sfx}",
                    yaxis=f"y{sfx}",
                    showlegend=False,
                    hoverinfo="skip",
                ))
        return ev_traces

    # Y scale for events (domain 0..1 does not work in direct scatter)
    # Using shape via layout.shapes — added via update_layout
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

    init_traces = SCENARIOS[0][1]
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
    # Build data vectors for each scenario for restyle
    def _restyle_args(traces, t_end, y_n_max, y_Te_max, y_ias_max):
        x_data = [tr["x"] for tr in traces]
        y_data = [tr["y"] for tr in traces]
        return (
            {"x": x_data, "y": y_data},
            [0, 1, 2],
        )

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


# ─────────────────────────────────────────────────────────────────────────────
# 7. SWITCHABLE EQUIVALENT CIRCUIT — Full (with Rfe) vs. IEEE (without Rfe)
# ─────────────────────────────────────────────────────────────────────────────

def _palette_theory(dark: bool) -> dict[str, str]:
    if dark:
        return dict(muted="#8892b0", text="#e4e8f5", accent="#4f8ef7",
                    border="#2a3150", surface="#161b27")
    return dict(muted="#4b5563", text="#111827", accent="#2563eb",
                border="#d0d8f0", surface="#ffffff")


@st.cache_data(show_spinner="Generating circuit…")
def _build_circuit_png(mp_key: tuple, dark: bool, simplified: bool) -> bytes:
    """Generates PNG bytes of the equivalent circuit (cacheable)."""
    # Rebuilds a build_figure-compatible object from the key
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


# ─────────────────────────────────────────────────────────────────────────────
# 7. VOLTAGE UNBALANCE — sinusoids with δ slider (amplitude) + Δf (freq)
# ─────────────────────────────────────────────────────────────────────────────

@st.fragment
def render_fasorial_desequilibrio() -> None:
    """Va/Vb/Vc waveforms + animated phasor diagram with per-phase unbalance.

    Isolated in @st.fragment: Streamlit sliders rerun only this component.
    Phasor uses native Plotly animation (Play/Pause) — vectors rotate in the complex plane.
    Waveforms display a cursor synchronised with the phasor time slider.
    """
    dark = _dark()
    pt   = _plot_theme(dark)
    mp   = _get_mp()
    f0   = float(mp.f)

    col_Va  = "#f97316"
    col_Vb  = "#4f8ef7" if dark else "#1d4ed8"
    col_Vc  = "#34d399" if dark else "#059669"
    col_vuf = "#f87171"
    col_bg  = pt["paper_bg"]
    col_fg  = pt["fg"]
    col_gr  = pt["grid"]

    # ── controls: 3 vertical columns per phase + speed column ─────────────────
    col_a, col_b, col_c, col_vel = st.columns(4)

    with col_a:
        st.markdown(f"<b style='color:{col_Va};font-size:15px'>● Va</b>",
                    unsafe_allow_html=True)
        ativa_a = st.checkbox("Active", value=True, key="_fdeseq_ativa_a")
        delta_a = st.slider("Amplitude δ (%)", -30, 30, 0, key="_fdeseq_da",
                             disabled=not ativa_a, format="%+d%%")
        freq_a  = st.slider("Frequency (Hz)", 50.0, 70.0, float(np.clip(f0, 50.0, 70.0)),
                             key="_fdeseq_fa", step=0.5, disabled=not ativa_a,
                             format="%.1f Hz")

    with col_b:
        st.markdown(f"<b style='color:{col_Vb};font-size:15px'>● Vb</b>",
                    unsafe_allow_html=True)
        ativa_b = st.checkbox("Active", value=True, key="_fdeseq_ativa_b")
        delta_b = st.slider("Amplitude δ (%)", -30, 30, 0, key="_fdeseq_db",
                             disabled=not ativa_b, format="%+d%%")
        freq_b  = st.slider("Frequency (Hz)", 50.0, 70.0, float(np.clip(f0, 50.0, 70.0)),
                             key="_fdeseq_fb", step=0.5, disabled=not ativa_b,
                             format="%.1f Hz")

    with col_c:
        st.markdown(f"<b style='color:{col_Vc};font-size:15px'>● Vc</b>",
                    unsafe_allow_html=True)
        ativa_c = st.checkbox("Active", value=True, key="_fdeseq_ativa_c")
        delta_c = st.slider("Amplitude δ (%)", -30, 30, 0, key="_fdeseq_dc",
                             disabled=not ativa_c, format="%+d%%")
        freq_c  = st.slider("Frequency (Hz)", 50.0, 70.0, float(np.clip(f0, 50.0, 70.0)),
                             key="_fdeseq_fc", step=0.5, disabled=not ativa_c,
                             format="%.1f Hz")

    with col_vel:
        st.markdown("**Animation**")
        cycle_sec_pre = st.slider(
            "Cycle duration (s/cycle)",
            min_value=1, max_value=20, value=5, step=1,
            key="_fdeseq_vel", format="%d s",
        )

    amp_a = (1.0 + delta_a / 100.0) if ativa_a else 0.0
    amp_b = (1.0 + delta_b / 100.0) if ativa_b else 0.0
    amp_c = (1.0 + delta_c / 100.0) if ativa_c else 0.0
    fa    = float(freq_a) if ativa_a else f0
    fb    = float(freq_b) if ativa_b else f0
    fc    = float(freq_c) if ativa_c else f0

    # ── VUF via Fortescue ─────────────────────────────────────────────────────
    a_rot = np.exp(1j * 2 * np.pi / 3)
    F_mat = np.array([
        [1, 1,        1       ],
        [1, a_rot,    a_rot**2],
        [1, a_rot**2, a_rot**4],
    ]) / 3.0
    Va_f = amp_a * np.exp(1j * 0.0)
    Vb_f = amp_b * np.exp(1j * (-2 * np.pi / 3))
    Vc_f = amp_c * np.exp(1j * ( 2 * np.pi / 3))
    _, V1s, V2s = F_mat @ np.array([Va_f, Vb_f, Vc_f])
    vuf     = abs(V2s) / abs(V1s) * 100 if abs(V1s) > 1e-9 else 0.0
    v1_pu   = float(abs(V1s))
    v2_pu   = float(abs(V2s))
    vuf_txt = f"VUF = {vuf:.1f}%"

    # ── loop period: smallest k·T0 that approximates a full cycle of all phases ─
    # With distinct frequencies, sin(2π·f_i·t) only closes when k·T0 is (nearly) an
    # integer multiple of 1/f_i. Search k∈[1,30] minimising phase error at end of window.
    T0       = 1.0 / f0
    freqs_on = [fa if ativa_a else f0, fb if ativa_b else f0, fc if ativa_c else f0]
    k_best, err_best = 1, float("inf")
    for k in range(1, 31):
        Twin = k * T0
        err  = sum(abs(((fi * Twin) - round(fi * Twin))) for fi in freqs_on)
        if err < err_best - 1e-9:
            err_best, k_best = err, k
            if err < 1e-6:
                break
    T_loop = k_best * T0

    # ── time axis: loop cycle, N_T frames per nominal cycle ───────────────────
    N_T   = 72 * k_best   # 5°/frame per 60 Hz cycle, scaled by loop
    # endpoint=False: animation array (no repeat at t=T_loop)
    t_arr  = np.linspace(0.0, T_loop, N_T, endpoint=False)
    t_ms   = (t_arr * 1000).tolist()
    # endpoint=True: static curve includes t=T_loop to close the cycle visually
    t_plot = np.linspace(0.0, T_loop, N_T + 1, endpoint=True)
    t_ms_plot = t_plot * 1000  # ndarray — Plotly aceita direto

    # ── pre-compute all waveforms (vectorised) ────────────────────────────────
    Va_wave = amp_a * np.sin(2 * np.pi * fa * t_arr)
    Vb_wave = amp_b * np.sin(2 * np.pi * fb * t_arr - 2 * np.pi / 3)
    Vc_wave = amp_c * np.sin(2 * np.pi * fc * t_arr + 2 * np.pi / 3)
    # closed static curves (for the plot)
    Va_plot = amp_a * np.sin(2 * np.pi * fa * t_plot)
    Vb_plot = amp_b * np.sin(2 * np.pi * fb * t_plot - 2 * np.pi / 3)
    Vc_plot = amp_c * np.sin(2 * np.pi * fc * t_plot + 2 * np.pi / 3)

    y_max_wave = max(amp_a, amp_b, amp_c, 0.01) * 1.25
    r_max      = max(amp_a, amp_b, amp_c, 0.01) * 1.35

    # ── base waveform traces (static curves) ──────────────────────────────────
    base_wave: list = []
    if ativa_a:
        base_wave.append(go.Scatter(x=t_ms_plot, y=Va_plot, mode="lines",
            name="Va", line=dict(color=col_Va, width=2.5)))
    if ativa_b:
        base_wave.append(go.Scatter(x=t_ms_plot, y=Vb_plot, mode="lines",
            name="Vb", line=dict(color=col_Vb, width=2.5)))
    if ativa_c:
        base_wave.append(go.Scatter(x=t_ms_plot, y=Vc_plot, mode="lines",
            name=f"Vc ({fc:.1f} Hz)", line=dict(color=col_Vc, width=2.5)))
    n_static_wave = len(base_wave)

    # animated markers: one per active phase + vertical cursor + VUF text
    n_markers = sum([ativa_a, ativa_b, ativa_c]) + 1 + 1  # +cursor +VUF

    def _wave_anim_traces(ti: int) -> list:
        traces = []
        tx = t_ms[ti]
        for wave, col, ativa in [
            (Va_wave, col_Va, ativa_a),
            (Vb_wave, col_Vb, ativa_b),
            (Vc_wave, col_Vc, ativa_c),
        ]:
            if not ativa:
                continue
            traces.append(go.Scatter(
                x=[tx], y=[float(wave[ti])], mode="markers",
                marker=dict(color=col, size=10, line=dict(color=col_fg, width=1)),
                showlegend=False,
            ))
        traces.append(go.Scatter(
            x=[tx, tx], y=[-y_max_wave, y_max_wave],
            mode="lines", line=dict(color=col_fg, width=1, dash="dot"),
            showlegend=False,
        ))
        # Animated VUF (placeholder; real value computed in JS)
        traces.append(go.Scatter(
            x=[t_ms[-1] * 0.70], y=[y_max_wave * 0.88],
            mode="text", text=[vuf_txt],
            textfont=dict(size=13, color=col_vuf), showlegend=False,
        ))
        return traces

    # ── base phasor traces (reference circle only) ────────────────────────────
    theta_c = np.linspace(0, 2 * np.pi, 120)
    base_fas: list = [
        go.Scatter(
            x=np.cos(theta_c), y=np.sin(theta_c),
            mode="lines", line=dict(color=col_gr, width=1, dash="dot"),
            showlegend=False,
        ),
    ]
    n_static_fas = len(base_fas)

    # animated vectors: 2 traces per active phase (arrow + label) + VUF text
    n_arrows = sum([ativa_a, ativa_b, ativa_c]) * 2 + 1  # +1 VUF

    def _fas_anim_traces(ti: int) -> list:
        t = t_arr[ti]
        traces = []
        for amp, freq, ph0, col, lbl, ativa in [
            (amp_a, fa, 0.0,          col_Va, "Va", ativa_a),
            (amp_b, fb, -2*np.pi/3,   col_Vb, "Vb", ativa_b),
            (amp_c, fc,  2*np.pi/3,   col_Vc, "Vc", ativa_c),
        ]:
            if not ativa:
                continue
            theta  = 2 * np.pi * freq * t + ph0
            x_tip  = amp * np.cos(theta)
            y_tip  = amp * np.sin(theta)
            traces.append(go.Scatter(
                x=[0, x_tip], y=[0, y_tip], mode="lines+markers",
                name=lbl,
                line=dict(color=col, width=3),
                marker=dict(symbol=["circle", "arrow"], size=[5, 14],
                            color=col, angleref="previous"),
            ))
            traces.append(go.Scatter(
                x=[x_tip * 1.14], y=[y_tip * 1.14],
                mode="text", text=[f"{lbl} {amp:.2f}"],
                textfont=dict(size=9, color=col), showlegend=False,
            ))
        # Animated VUF (placeholder; real value computed in JS)
        traces.append(go.Scatter(
            x=[0], y=[-r_max * 0.88],
            mode="text", text=[vuf_txt],
            textfont=dict(size=13, color=col_vuf), showlegend=False,
        ))
        return traces

    # ── serialise figures and parameters for JS ───────────────────────────────
    import json

    fig_wave = go.Figure(data=base_wave + _wave_anim_traces(0))
    fig_fas  = go.Figure(data=base_fas  + _fas_anim_traces(0))

    wave_anim_idx = list(range(n_static_wave, n_static_wave + n_markers))
    fas_anim_idx  = list(range(n_static_fas,  n_static_fas  + n_arrows))

    layout_common = dict(
        paper_bgcolor=col_bg, plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=col_fg),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.22,
                    font=dict(size=9, color=col_fg), bgcolor="rgba(0,0,0,0)"),
    )
    fig_wave.update_layout(
        **layout_common,
        title=dict(text="Waveforms Va / Vb / Vc", x=0.5, xanchor="center",
                   font=dict(size=12, color=col_fg)),
        margin=dict(l=55, r=10, t=45, b=90),
        xaxis=dict(title="Time (ms)", showgrid=True, gridcolor=col_gr,
                   zeroline=False, tickfont=dict(size=9, color=col_fg)),
        yaxis=dict(title="Voltage (p.u.)", showgrid=True, gridcolor=col_gr,
                   zeroline=True, zerolinecolor=col_gr,
                   range=[-y_max_wave, y_max_wave],
                   tickfont=dict(size=9, color=col_fg)),
    )
    fig_fas.update_layout(
        **layout_common,
        title=dict(text="Phasor Diagram", x=0.5, xanchor="center",
                   font=dict(size=12, color=col_fg)),
        margin=dict(l=50, r=10, t=45, b=90),
        xaxis=dict(title="Re (p.u.)", showgrid=True, gridcolor=col_gr,
                   zeroline=True, zerolinecolor=col_gr,
                   range=[-r_max, r_max], scaleanchor="y",
                   tickfont=dict(size=9, color=col_fg)),
        yaxis=dict(title="Im (p.u.)", showgrid=True, gridcolor=col_gr,
                   zeroline=True, zerolinecolor=col_gr,
                   range=[-r_max, r_max],
                   tickfont=dict(size=9, color=col_fg)),
    )

    wave_json_str = fig_wave.to_json()
    fas_json_str  = fig_fas.to_json()

    phases_js = []
    for amp, freq, ph0, _, _, ativa in [
        (amp_a, fa, 0.0,        col_Va, "Va", ativa_a),
        (amp_b, fb, -2*np.pi/3, col_Vb, "Vb", ativa_b),
        (amp_c, fc,  2*np.pi/3, col_Vc, "Vc", ativa_c),
    ]:
        if not ativa:
            continue
        phases_js.append({"amp": amp, "freq": freq, "ph0": ph0})

    T_loop_ms = T_loop * 1000
    cycle_sec = cycle_sec_pre

    t_ms_max  = T_loop_ms   # janela de loop completa — fecha o ciclo visualmente
    html_src = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin:0; padding:0; }}
  body {{ background:{col_bg}; }}
  #plots {{ display:flex; }}
  #gw {{ flex:3; min-width:0; }}
  #gf {{ flex:1; min-width:0; }}
</style>
</head><body>
<div id="plots">
  <div id="gw"></div>
  <div id="gf"></div>
</div>
<script>
(function(){{
  var wSpec   = {wave_json_str};
  var fSpec   = {fas_json_str};
  var phases  = {json.dumps(phases_js)};
  var tMs     = {json.dumps(t_ms)};
  var wIdx    = {json.dumps(wave_anim_idx)};
  var fIdx    = {json.dumps(fas_anim_idx)};
  var T0real  = {T_loop_ms:.4f};   // loop window in ms (k·T0, closes all phases)
  var kBest   = {k_best};          // number of nominal cycles in the loop
  var tMax    = {t_ms_max:.4f}; // X axis duration in ms (== T0real)
  var yMax    = {y_max_wave * 1.25:.4f};
  var PI2      = 2 * Math.PI;
  var startTs  = null;
  var cycleSec = {cycle_sec};
  var gw, gf;

  var cfg = {{displaylogo: false, responsive: true}};
  Promise.all([
    Plotly.newPlot('gw', wSpec.data, wSpec.layout, cfg),
    Plotly.newPlot('gf', fSpec.data, fSpec.layout, cfg)
  ]).then(function(divs){{
    gw = divs[0]; gf = divs[1];
    // fix ranges so restyle does not compress the axes
    Plotly.relayout(gw, {{'xaxis.autorange': false, 'xaxis.range': [0, tMax],
                          'yaxis.autorange': false, 'yaxis.range': [-yMax, yMax]}});
    Plotly.relayout(gf, {{'xaxis.autorange': false, 'yaxis.autorange': false}});
    requestAnimationFrame(tick);
  }});

  function tick(ts){{
    if (!startTs) startTs = ts;
    var T0ms  = cycleSec * 1000 * kBest;         // visual duration of full loop (k nominal cycles)
    var frac  = ((ts - startTs) % T0ms) / T0ms;  // fraction 0..1 within visual loop
    var tx    = frac * tMax;                     // ms within loop for cursor (closes at tMax)
    var tNorm = frac * T0real / 1000;            // seconds: 0..T0real/1000 (full loop)

    // ── Instantaneous VUF via Fortescue ──────────────────────────────────────
    // complex phasors at tNorm
    var a120 = PI2 / 3;
    var fasors = [];
    for (var i = 0; i < phases.length; i++) {{
      var p  = phases[i];
      var th = PI2 * p.freq * tNorm + p.ph0;
      fasors.push([p.amp * Math.cos(th), p.amp * Math.sin(th)]);  // [Re, Im]
    }}
    // fill inactive phases with zero
    var Va_c = [0,0], Vb_c = [0,0], Vc_c = [0,0];
    var fi2 = 0;
    var actMask = [{int(ativa_a)}, {int(ativa_b)}, {int(ativa_c)}];
    var allFasors = [Va_c, Vb_c, Vc_c];
    for (var i = 0; i < 3; i++) {{
      if (actMask[i]) {{ allFasors[i] = fasors[fi2++]; }}
    }}
    // matriz Fortescue: V0=sum/3, V1=(Va+a*Vb+a2*Vc)/3, V2=(Va+a2*Vb+a*Vc)/3
    // a = e^(j*2π/3), a2 = e^(j*4π/3)
    function cmul(A, B) {{ return [A[0]*B[0]-A[1]*B[1], A[0]*B[1]+A[1]*B[0]]; }}
    function cadd(A, B) {{ return [A[0]+B[0], A[1]+B[1]]; }}
    function cscale(A, s) {{ return [A[0]*s, A[1]*s]; }}
    function cabs(A) {{ return Math.sqrt(A[0]*A[0]+A[1]*A[1]); }}
    var a_  = [Math.cos(a120),  Math.sin(a120)];
    var a2_ = [Math.cos(2*a120), Math.sin(2*a120)];
    var V1 = cscale(cadd(cadd(allFasors[0], cmul(a_,  allFasors[1])), cmul(a2_, allFasors[2])), 1/3);
    var V2 = cscale(cadd(cadd(allFasors[0], cmul(a2_, allFasors[1])), cmul(a_,  allFasors[2])), 1/3);
    var vuf = cabs(V1) > 1e-9 ? (cabs(V2) / cabs(V1) * 100) : 0;
    var vufTxt = 'VUF = ' + vuf.toFixed(1) + '%';

    // waveforms: markers + cursor + VUF text
    var wx = [], wy = [], wi = [], wt = [];
    for (var i = 0; i < phases.length; i++){{
      var p  = phases[i];
      var yv = p.amp * Math.sin(PI2 * p.freq * tNorm + p.ph0);
      wx.push([tx]); wy.push([yv]); wi.push(wIdx[i]); wt.push(null);
    }}
    wx.push([tx, tx]); wy.push([-yMax, yMax]); wi.push(wIdx[phases.length]); wt.push(null);
    wx.push([{t_ms[-1] * 0.70:.2f}]); wy.push([{y_max_wave * 0.88:.4f}]);
    wi.push(wIdx[phases.length + 1]); wt.push([vufTxt]);
    Plotly.restyle(gw, {{x: wx, y: wy, text: wt}}, wi);

    // phasor: vectors + labels + VUF text
    var fx = [], fy = [], fi_arr = [], ft = [];
    for (var i = 0; i < phases.length; i++){{
      var p  = phases[i];
      var th = PI2 * p.freq * tNorm + p.ph0;
      var xT = p.amp * Math.cos(th);
      var yT = p.amp * Math.sin(th);
      fx.push([0, xT]);    fy.push([0, yT]);       fi_arr.push(fIdx[i*2]);     ft.push(null);
      fx.push([xT*1.14]);  fy.push([yT*1.14]);     fi_arr.push(fIdx[i*2+1]);   ft.push(null);
    }}
    fx.push([0]); fy.push([{-r_max * 0.88:.4f}]); fi_arr.push(fIdx[phases.length*2]); ft.push([vufTxt]);
    Plotly.restyle(gf, {{x: fx, y: fy, text: ft}}, fi_arr);

    requestAnimationFrame(tick);
  }}
}})();
</script>
</body></html>"""

    st.iframe(html_src, height=540)


def render_circuito_alternavel() -> None:
    """Switchable equivalent circuit: Full (with Rfe) ↔ IEEE simplified (without Rfe)."""
    mp   = _get_mp()
    dark = _dark()

    modo = st.radio(
        "Circuit model",
        options=["Full — with $R_{fe}$", "IEEE simplified — without $R_{fe}$"],
        horizontal=True,
        key="th_circ_modo",
    )
    simplified = "IEEE" in modo

    mp_key = (
        float(mp.Vl), float(mp.f), float(mp.Rs), float(mp.Rr),
        float(mp.Xm), float(mp.Xls), float(mp.Xlr),
        float(getattr(mp, "Rfe", 500.0)), int(mp.p),
    )
    png_bytes = _build_circuit_png(mp_key, dark, simplified)
    st.image(png_bytes, width="stretch")

    if simplified:
        st.markdown(
            r"**Loop equation** — $R_{fe}$ branch removed ($R_{fe} \to \infty$, open circuit):"
        )
        st.latex(
            r"Z_{total} = R_s + jX_{ls} + jX_m \,\Big\|\,"
            r"\!\left(jX_{lr} + \tfrac{R_r}{s}\right)"
        )
        st.markdown(
            "Simplification valid when $P_{fe} \\lesssim 2\\%\\,P_{nom}$. "
            "Efficiency is calculated separately without loss of accuracy."
        )
    else:
        st.markdown(r"**Loop equation** — full model with core losses:")
        st.latex(
            r"Z_{total} = R_s + jX_{ls} + "
            r"\left(jX_m \,\Big\|\, R_{fe}\right) \,\Big\|\,"
            r"\!\left(jX_{lr} + \tfrac{R_r}{s}\right)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. MCSA — ASSINATURA DE CORRENTE COM BARRA QUEBRADA
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# 5. BRAKING METHOD COMPARATOR — n(t) and Te(t) interactive
# ─────────────────────────────────────────────────────────────────────────────

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
        # Frame of current n0 (nom_n0_idx) with this intens
        slider_steps.append(dict(
            method="animate",
            label=f"{intens:.1f}x",
            args=[[f"{nom_n0_idx}_{ii}"],
                  dict(mode="immediate",
                       frame=dict(duration=0, redraw=True),
                       transition=dict(duration=0))],
        ))

    # ── Plotly dropdown for n0 ───────────────────────────────────────────────
    # Each button animates to the frame corresponding to (ni, current_intens)
    # Uses initial intensity; when n0 changes via dropdown, slider stays at same intens step
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


# ─────────────────────────────────────────────────────────────────────────────
# 6. KRAUSE BLOCK DIAGRAM — expandable 0dq model
# ─────────────────────────────────────────────────────────────────────────────

def render_blocos_krause() -> None:
    """Block diagram of the Krause 0dq model, with expandable cards per equation.

    Layout: 6 main cards (Vqs/Vds → ψqs/ψds, ψqr/ψdr, ψmq/ψmd, iqs/ids,
    Te, ωr). Each card shows the simplified equation; the user can expand
    to see the full version and its physical meaning.
    """
    dark = _dark()
    pt   = _plot_theme(dark)

    col_bg     = pt["paper_bg"]
    col_fg     = pt["fg"]
    col_border = pt["grid"]
    col_accent = "#4f8ef7" if dark else "#1d4ed8"

    # Card CSS (reuses project pgroup aesthetics)
    st.markdown(
        f"""
        <style>
        .krause-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.9rem;
            margin: 0.5rem 0 0.8rem 0;
        }}
        .krause-card {{
            background: {col_bg};
            border: 1px solid {col_border};
            border-left: 3px solid {col_accent};
            border-radius: 10px;
            padding: 0.8rem 1.0rem 0.6rem 1.0rem;
        }}
        .krause-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: {col_fg};
            margin-bottom: 0.3rem;
        }}
        .krause-subtitle {{
            font-size: 0.78rem;
            color: {col_fg};
            opacity: 0.7;
            margin-bottom: 0.4rem;
        }}
        @media (max-width: 768px) {{
            .krause-grid {{ grid-template-columns: 1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── 2-column layout (side by side) ───────────────────────────────────────
    blocos = [
        {
            "titulo": "1. Voltages → Stator Flux Linkages",
            "sub":   "Integration of applied voltages",
            "eq_simples": r"\dot{\psi}_{qs},\,\dot{\psi}_{ds} = f(V_{qs},\,V_{ds},\,\omega_e,\,\psi_{mq},\,\psi_{md})",
            "eq_full":    [
                r"\dot{\psi}_{qs} = \omega_b\!\left(V_{qs} - \tfrac{\omega_e}{\omega_b}\psi_{ds} + \tfrac{R_s}{X_{ls}}(\psi_{mq}-\psi_{qs})\right)",
                r"\dot{\psi}_{ds} = \omega_b\!\left(V_{ds} + \tfrac{\omega_e}{\omega_b}\psi_{qs} + \tfrac{R_s}{X_{ls}}(\psi_{md}-\psi_{ds})\right)",
            ],
            "fisica": (
                "The voltages $V_{qs}$ and $V_{ds}$ (synchronous reference frame) impose the derivative of "
                "the stator flux linkages. The cross-coupling via $\\omega_e$ represents "
                "the reference frame rotation, and the $R_s/X_{ls}$ term is the resistive voltage drop."
            ),
        },
        {
            "titulo": "2. Rotor Flux Linkages",
            "sub":   "Short-circuited squirrel-cage rotor",
            "eq_simples": r"\dot{\psi}_{qr},\,\dot{\psi}_{dr} = f(\omega_e-\omega_r,\,\psi_{mq},\,\psi_{md})",
            "eq_full":    [
                r"\dot{\psi}_{qr} = \omega_b\!\left(-\tfrac{\omega_e-\omega_r}{\omega_b}\psi_{dr} + \tfrac{R_r}{X_{lr}}(\psi_{mq}-\psi_{qr})\right)",
                r"\dot{\psi}_{dr} = \omega_b\!\left(\tfrac{\omega_e-\omega_r}{\omega_b}\psi_{qr} + \tfrac{R_r}{X_{lr}}(\psi_{md}-\psi_{dr})\right)",
            ],
            "fisica": (
                "Since the rotor is short-circuited ($V_{qr} = V_{dr} = 0$), only the internal "
                "resistive drop term and the cross-coupling through the relative speed "
                "$\\omega_e - \\omega_r$ govern the evolution of the rotor flux linkages."
            ),
        },
        {
            "titulo": "3. Magnetising Flux Linkages",
            "sub":   "Air-gap coupling",
            "eq_simples": r"\psi_{mq},\,\psi_{md} = \text{weighted average of }\psi_s,\,\psi_r",
            "eq_full":    [
                r"\psi_{mq} = X_{ml}\!\left(\tfrac{\psi_{qs}}{X_{ls}} + \tfrac{\psi_{qr}}{X_{lr}}\right)",
                r"\psi_{md} = X_{ml}\!\left(\tfrac{\psi_{ds}}{X_{ls}} + \tfrac{\psi_{dr}}{X_{lr}}\right)",
                r"\tfrac{1}{X_{ml}} = \tfrac{1}{X_m} + \tfrac{1}{X_{ls}} + \tfrac{1}{X_{lr}}",
            ],
            "fisica": (
                "The air-gap fluxes are a weighted combination of stator and rotor flux linkages "
                "through the resultant mutual reactance $X_{ml}$. This is the point at which "
                "stator and rotor are magnetically coupled."
            ),
        },
        {
            "titulo": "4. Stator Currents",
            "sub":   "Magnetic Ohm's law",
            "eq_simples": r"i_{qs},\,i_{ds} = \tfrac{\psi_{qs}-\psi_{mq}}{X_{ls}},\;\tfrac{\psi_{ds}-\psi_{md}}{X_{ls}}",
            "eq_full":    [
                r"i_{qs} = \tfrac{\psi_{qs} - \psi_{mq}}{X_{ls}}",
                r"i_{ds} = \tfrac{\psi_{ds} - \psi_{md}}{X_{ls}}",
            ],
            "fisica": (
                "The currents are obtained directly from the difference between total flux linkage and "
                "magnetising flux linkage, divided by the leakage reactance. In steady state, the current "
                "is in phase with the resistive drop $R_s \\cdot i$ across the stator."
            ),
        },
        {
            "titulo": "5. Electromagnetic Torque",
            "sub":   "Cross product of flux linkages and currents",
            "eq_simples": r"T_e = \tfrac{3}{2}\cdot\tfrac{p}{2}\cdot\tfrac{1}{\omega_b}(\psi_{ds}\,i_{qs}-\psi_{qs}\,i_{ds})",
            "eq_full":    [
                r"T_e = \tfrac{3}{2}\cdot\tfrac{p}{2}\cdot\tfrac{1}{\omega_b}\,(\psi_{ds}\,i_{qs} - \psi_{qs}\,i_{ds})",
            ],
            "fisica": (
                "The cross product of stator flux linkage and stator current produces the torque. "
                "This is the dq analogue of the classical expression $T \\propto \\vec{\\psi}\\times\\vec{i}$. "
                "The $3/2$ factor arises from the power-invariant transformation; $p/2$ converts "
                "magnetic poles to mechanical pole pairs."
            ),
        },
        {
            "titulo": "6. Mechanical Equation",
            "sub":   "Shaft dynamics",
            "eq_simples": r"\dot{\omega}_r = \tfrac{p}{2J}(T_e - T_L) - \tfrac{B}{J}\,\omega_r",
            "eq_full":    [
                r"\dot{\omega}_r = \tfrac{p}{2J}\,(T_e - T_L) - \tfrac{B}{J}\,\omega_r",
            ],
            "fisica": (
                "Newton's second law for rotation: net torque ($T_e - T_L$) divided by "
                "inertia $J$ determines the angular acceleration. The $B\\,\\omega_r/J$ term models "
                "viscous friction. The mechanical time constant is typically 10–100× the electrical one."
            ),
        },
    ]

    # Render card grid (summary)
    cards_html = '<div class="krause-grid">'
    for b in blocos:
        cards_html += (
            f'<div class="krause-card">'
            f'  <div class="krause-title">{b["titulo"]}</div>'
            f'  <div class="krause-subtitle">{b["sub"]}</div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # Detailed expanders per block
    st.caption("Expand each block to view the complete equation and its physical meaning.")
    for b in blocos:
        with st.expander(b["titulo"], expanded=False):
            st.markdown(f"_{b['sub']}_")
            for eq in b["eq_full"]:
                st.latex(eq)
            st.markdown(b["fisica"])

    # Flow diagram between blocks (compact text)
    st.markdown("---")
    st.markdown(
        "**Solver computational flow:** "
        "$V_{qs},V_{ds}$ → (1) → $\\psi_s$ ⇄ (3) ⇄ $\\psi_r$ ← (2) ← $\\omega_e-\\omega_r$ ; "
        "$\\psi_s,\\psi_m$ → (4) → $i_s$ ; $\\psi_s,i_s$ → (5) → $T_e$ → (6) → $\\omega_r$ "
        "(feeds back into 2)."
    )
