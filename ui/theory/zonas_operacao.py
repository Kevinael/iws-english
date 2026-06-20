# -*- coding: utf-8 -*-
"""
zonas_operacao.py
=================
T×n chart with three colored operating zones and animated vector diagram.

Responsibilities:
  - Render T×n curve with Motor / Generator / Braking bands.
  - Render animated phasor diagram (requestAnimationFrame in iframe).

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts, core.tim.torque_speed
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme
from core.tim import _extract_params, _torque_array

from ui.theory._shared import _get_mp, _dark


@st.cache_data(show_spinner=False)
def _compute_zonas(
    V1: float, R1: float, X1: float, R2: float, X2: float,
    Xm: float, ws_mec: float, ns: float,
) -> dict:
    s_brake  = np.linspace(1.001, 2.0,  150)
    s_motor  = np.linspace(1e-4,  1.0,  400)
    s_gen    = np.linspace(-1.0, -1e-4, 150)
    return {
        "n_brake":  ns * (1.0 - s_brake),
        "n_motor":  ns * (1.0 - s_motor),
        "n_gen":    ns * (1.0 - s_gen),
        "Te_brake": _torque_array(s_brake, V1, R1, X1, R2, X2, Xm, ws_mec),
        "Te_motor": _torque_array(s_motor, V1, R1, X1, R2, X2, Xm, ws_mec),
        "Te_gen":   _torque_array(s_gen,   V1, R1, X1, R2, X2, Xm, ws_mec),
    }


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

    _z = _compute_zonas(V1, R1, X1, R2, X2, Xm, ws_mec, ns)
    n_brake  = _z["n_brake"];  Te_brake = _z["Te_brake"]
    n_motor  = _z["n_motor"];  Te_motor = _z["Te_motor"]
    n_gen    = _z["n_gen"];    Te_gen   = _z["Te_gen"]

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
  #gv {{ width:320px; height:420px; }}
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
    width:320, height:380,
    paper_bgcolor:colBg, plot_bgcolor:colBg,
    title:{{text:titulo, x:0.5, xanchor:"center",
            font:{{size:11, color:colField}}}},
    xaxis:{{range:[-1.6,1.6], showgrid:false, zeroline:false, showticklabels:false,
             scaleanchor:"y"}},
    yaxis:{{range:[-1.6,1.6], showgrid:false, zeroline:false, showticklabels:false}},
    margin:{{l:10, r:10, t:40, b:60}},
    font:{{color:colField}},
    legend:{{orientation:"h", x:0.5, xanchor:"center", y:-0.12,
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

    st.iframe(html_src, height=430)
    st.caption(desc)
