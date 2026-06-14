# -*- coding: utf-8 -*-
"""
theory_dc_interactive.py
========================
Interactive Plotly components for the DC machine Theory tab — comparative curves, current patterns, speed control, estimator, and block diagrams.

Responsibilities:
  - Render comparative excitation T×ωm curves (render_curvas_comparativas_excitacao).
  - Render current patterns for DCM excitation types (render_padrao_corrente_dc).
  - Render speed control strategies (render_controle_velocidade_dc).
  - Render parameter estimator UI (render_estimador_dc).
  - Render DCM block diagram (render_diagrama_blocos_mcc).

Relationships:
  Imported by : ui.theory_dc
  Imports     : viz.plotly_charts

Extending:
  - To add a new DCM interactive component, create render_<name>() here and register it in ui/theory_dc.py.
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from viz.tim_charts import _plot_theme


# ─────────────────────────────────────────────────────────────────────────────
# 1. Comparative T×ωm curves
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _build_fig_txwm_dc(dark: bool) -> go.Figure:
    """Pre-computes T×ωm frames for Va grid — zero-latency JS slider, no Streamlit rerun."""
    from viz.tim_charts import _plot_theme as _pt
    pt = _pt(dark)

    Ra    = 0.013
    kb    = 0.004
    Rf    = 1.43
    Tload = 2.493
    Rsf   = 0.026   # series field resistance
    N_STEPS = 40
    Va_grid = np.linspace(6.0, 48.0, N_STEPS)
    Va_init = 24.0
    init_idx = int(np.argmin(np.abs(Va_grid - Va_init)))

    C_SEP   = "#60a5fa"
    C_SHU   = "#34d399"
    C_SER   = "#f87171"
    C_LOAD  = "#f59e0b"

    def _curves(Va):
        wm_max = Va / (kb * 0.01) * 0.88
        wm = np.linspace(0, wm_max, 500)
        ifd_sep   = (Va * 0.5) / Rf
        ifd_shunt = Va / Rf
        ia_sep    = (Va - kb * ifd_sep   * wm) / Ra
        ia_shunt  = (Va - kb * ifd_shunt * wm) / Ra
        Te_sep    = np.maximum(kb * ifd_sep   * ia_sep,   0)
        Te_shunt  = np.maximum(kb * ifd_shunt * ia_shunt, 0)
        ia_s      = Va / (Ra + Rsf + kb * wm + 1e-9)
        Te_series = np.maximum(kb * ia_s**2, 0)
        return wm, Te_sep, Te_shunt, Te_series

    wm0, te_sep0, te_shu0, te_ser0 = _curves(Va_init)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wm0, y=te_sep0, mode="lines", name="Separately Excited",
                             line=dict(color=C_SEP, width=2.2)))
    fig.add_trace(go.Scatter(x=wm0, y=te_shu0, mode="lines", name="Shunt",
                             line=dict(color=C_SHU, width=2.2)))
    fig.add_trace(go.Scatter(x=wm0, y=te_ser0, mode="lines", name="Series",
                             line=dict(color=C_SER, width=2.2)))
    fig.add_trace(go.Scatter(
        x=[0, wm0[-1]], y=[Tload, Tload], mode="lines", name=f"Load ({Tload} N·m)",
        line=dict(color=C_LOAD, width=1.4, dash="dot"),
    ))

    frames = []
    slider_steps = []
    for i, Va in enumerate(Va_grid):
        wm, te_sep, te_shu, te_ser = _curves(Va)
        frames.append(go.Frame(
            name=str(i),
            data=[
                go.Scatter(x=wm, y=te_sep),
                go.Scatter(x=wm, y=te_shu),
                go.Scatter(x=wm, y=te_ser),
                go.Scatter(x=[0, wm[-1]], y=[Tload, Tload]),
            ],
            traces=[0, 1, 2, 3],
        ))
        slider_steps.append(dict(
            method="animate",
            label=f"{Va:.0f}",
            args=[[str(i)], dict(mode="immediate",
                                 frame=dict(duration=0, redraw=True),
                                 transition=dict(duration=0))],
        ))

    fig.frames = frames

    fig.update_layout(
        height=420,
        title=dict(text="T×ωm — DC Machine Excitation Comparison",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=50, b=110),
        xaxis=dict(title="ωm (rad/s)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]), rangemode="nonnegative"),
        yaxis=dict(title="Te (N·m)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]), rangemode="nonnegative"),
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                    font=dict(size=10, color=pt["fg"])),
        sliders=[dict(
            active=init_idx,
            currentvalue=dict(prefix="Va = ", suffix=" V", visible=True,
                              xanchor="center", font=dict(size=13, color=pt["fg"])),
            y=0, pad=dict(t=45, b=10), len=0.92, x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"], bordercolor=pt["grid"],
            tickcolor=pt["fg"], font=dict(color=pt["fg"], size=9),
        )],
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )
    return fig


def render_curvas_comparativas_excitacao() -> None:
    st.markdown("### Interactive T×ωm Curves")
    st.caption("Drag the Va slider — curves update instantly with no page reload. Fixed: Ra = 0.013 Ω, kb = 0.004, Rf = 1.43 Ω.")
    dark = st.session_state.get("dark_mode", False)
    fig  = _build_fig_txwm_dc(dark)
    st.plotly_chart(fig, use_container_width=True, key="theory_torque_speed_dc")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Current patterns
# ─────────────────────────────────────────────────────────────────────────────

def render_padrao_corrente_dc() -> None:
    st.markdown("### Armature Current $i_a(t)$ by Excitation Type")

    exc_opt = st.radio("Excitation", ["sep_motor", "shunt_motor", "series_motor"],
                       format_func=lambda x: {
                           "sep_motor": "Separately Excited",
                           "shunt_motor": "Shunt",
                           "series_motor": "Series",
                       }[x],
                       horizontal=True, key="theory_dc_exc_radio")

    if st.button("Simulate", key="theory_dc_simular"):
        from core.dc.machine_model import DCMachineParams
        from core.dc.solver import run_simulation_dc
        from core.dc.sources import make_voltage_fn_dc, make_torque_fn_dc

        presets = {
            "sep_motor":    dict(Va=24, Ra=0.013, La=0.01, Vf=12, Rf=1.43, Lf=0.167,
                                 kb=0.004, J=0.21, B=1.074e-6, Tload=2.493, excitation="sep_motor"),
            "shunt_motor":  dict(Va=24, Ra=0.013, La=0.01, Rf=1.43, Lf=0.167,
                                 kb=0.004, J=0.21, B=1.074e-6, Tload=2.493, excitation="shunt_motor"),
            "series_motor": dict(Va=24, Ra=0.013, La=0.01, Rf=0.026, Lf=0.167,
                                 kb=0.004, J=0.21, B=1.074e-6, Tload=2.493, excitation="series_motor"),
        }
        p = DCMachineParams(**presets[exc_opt])
        vfn = make_voltage_fn_dc("dol_dc", p, {})
        tfn = make_torque_fn_dc("dol_dc", p, {})
        with st.spinner("Simulating..."):
            res = run_simulation_dc(p, tmax=8.0, h=1e-3, voltage_fn=vfn, torque_fn=tfn)

        dark = st.session_state.get("dark_mode", False)
        pt   = _plot_theme(dark)
        fig  = go.Figure()
        fig.add_trace(go.Scatter(x=res["t"], y=res["ia"], mode="lines", name="$i_a$",
                                 line=dict(color="#60a5fa", width=1.8)))
        fig.update_layout(
            xaxis_title="Time (s)", yaxis_title="ia (A)",
            height=280,
            paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
            font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
            margin=dict(l=50, r=20, t=30, b=40),
        )
        st.plotly_chart(fig, use_container_width=True, key="theory_ia_dc")
        st.caption(f"Steady state: $i_{{a,ss}}$ = {res['ia_ss']:.3f} A | $n_{{ss}}$ = {res['n_ss']:.1f} RPM")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Speed control
# ─────────────────────────────────────────────────────────────────────────────

def render_controle_velocidade_dc() -> None:
    st.markdown("### Field Weakening — Speed Control")

    Va  = 24.0
    Ra  = 0.013
    kb  = 0.004
    Rf  = 1.43
    Tload = 2.493

    Vf_pct = st.slider("$V_f$ (% of rated)", 20, 100, 100, step=5,
                        key="theory_dc_Vf_pct")
    Vf = Va * Vf_pct / 100.0

    ifd  = Vf / Rf
    # Steady state: Te = Tload → kb*ifd*ia = Tload → ia = Tload/(kb*ifd)
    ia   = Tload / (kb * ifd) if ifd > 1e-9 else 0.0
    Ea   = Va - Ra * ia
    wm   = Ea / (kb * ifd) if ifd > 1e-9 else 0.0
    n    = wm * 60 / (2 * np.pi)

    c1, c2, c3 = st.columns(3)
    c1.metric("$i_{fd}$ (A)", f"{ifd:.3f}")
    c2.metric("$\\omega_m$ (rad/s)", f"{wm:.1f}")
    c3.metric("$n$ (RPM)", f"{n:.0f}")

    st.caption(
        "Reducing $V_f$ → $i_{fd}$ drops → $\\omega_m$ increases (field weakening). "
        "Note: $i_a$ increases to maintain $T_e$."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. DC Estimator
# ─────────────────────────────────────────────────────────────────────────────

def render_estimador_dc() -> None:
    st.markdown("### Parameter Estimator from Tests")

    with st.form("form_estimador_dc"):
        st.markdown("**DC resistance test** (rotor at standstill, field excited)")
        f1, f2 = st.columns(2)
        V_dc = f1.number_input("$V_{dc}$ (V)", min_value=0.01, value=1.0, format="%.3f")
        I_dc = f2.number_input("$I_{dc}$ (A)", min_value=0.001, value=0.1, format="%.3f")

        st.markdown("**No-load test** (no mechanical load)")
        g1, g2, g3, g4 = st.columns(4)
        V_nl  = g1.number_input("$V_{a,nl}$ (V)", min_value=0.01, value=24.0, format="%.3f")
        I_nl  = g2.number_input("$I_{a,nl}$ (A)", min_value=0.001, value=0.05, format="%.3f")
        If_nl = g3.number_input("$I_{fd,nl}$ (A)", min_value=0.001, value=8.4, format="%.3f")
        n_nl  = g4.number_input("$n_{nl}$ (RPM)", min_value=1.0, value=6500.0, format="%.1f")

        submitted = st.form_submit_button("Estimate")

    if submitted:
        Ra = V_dc / I_dc
        wm_nl = n_nl * 2 * np.pi / 60
        Ea_nl = V_nl - Ra * I_nl
        kb    = Ea_nl / (If_nl * wm_nl) if (If_nl * wm_nl) > 1e-9 else 0.0

        st.success(f"$R_a$ = **{Ra:.4f} Ω** | $k_b$ = **{kb:.5f} V·s/rad**")
        st.markdown(
            f"Verification: $E_{{a,nl}} = V_{{a,nl}} - R_a I_{{a,nl}} = "
            f"{V_nl:.3f} - {Ra:.4f}×{I_nl:.3f} = {Ea_nl:.4f}$ V"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Block diagram
# ─────────────────────────────────────────────────────────────────────────────

def render_diagrama_blocos_mcc() -> None:
    st.markdown("### State-Space Block Diagram")
    st.markdown(r"""
```
Va ──► [ 1/(La·s + Ra) ] ──► ia ──► kb·ifd ──► Te ──► [ 1/(J·s + B) ] ──► ωm
                  ▲                                              │
                  └──────────────── kb·ifd·ωm ◄──────────────────┘
                                    (back-EMF Ea)

Vf ──► [ 1/(Lf·s + Rf) ] ──► ifd ──►(both above)
```
- $T_e = k_b \, i_{fd} \, i_a$
- $E_a = k_b \, i_{fd} \, \omega_m$
- Series: $i_{fd} = i_a$ (field in series with armature)
""")
