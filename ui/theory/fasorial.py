# -*- coding: utf-8 -*-
"""
fasorial.py
===========
Voltage unbalance component — Va/Vb/Vc waveforms + animated phasor diagram.

Responsibilities:
  - Render per-phase amplitude/frequency sliders.
  - Compute VUF via Fortescue in Python and continuously in JS.
  - Drive animated phasor + waveform via requestAnimationFrame in HTML iframe.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts
"""

from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from viz.tim_charts import _plot_theme

from ui.theory._shared import _get_mp, _dark


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
    t_arr  = np.linspace(0.0, T_loop, N_T, endpoint=False)
    t_ms   = (t_arr * 1000).tolist()
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

    t_ms_max  = T_loop_ms
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
