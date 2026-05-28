# -*- coding: utf-8 -*-
"""Componentes interativos da aba Teoria MCC.

Exporta:
    render_curvas_comparativas_excitacao
    render_padrao_corrente_dc
    render_controle_velocidade_dc
    render_estimador_dc
    render_diagrama_blocos_mcc
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from viz.plotly_charts import _plot_theme


# ─────────────────────────────────────────────────────────────────────────────
# 1. Curvas T×ωm comparativas
# ─────────────────────────────────────────────────────────────────────────────

def render_curvas_comparativas_excitacao() -> None:
    st.markdown("### Curvas T×ωm Interativas")
    st.caption("Ajuste os parâmetros e compare as três excitações.")

    c1, c2 = st.columns(2)
    Va  = c1.slider("$V_a$ (V)",   1.0, 48.0, 24.0, step=0.5, key="theory_dc_Va")
    Ra  = c2.slider("$R_a$ (Ω)",   0.01, 1.0,  0.013, step=0.001, key="theory_dc_Ra",
                    format="%.3f")
    kb  = c1.slider("$k_b$",       0.001, 0.02, 0.004, step=0.001, key="theory_dc_kb",
                    format="%.3f")
    Rf  = c2.slider("$R_f$ (Ω)",   0.1, 5.0,  1.43, step=0.01, key="theory_dc_Rf",
                    format="%.2f")

    dark = st.session_state.get("dark_mode", False)
    pt   = _plot_theme(dark)

    wm_max = Va / (kb * 0.1) * 1.1   # estimativa do máximo
    wm     = np.linspace(0, wm_max, 400)
    Tload  = 2.493

    # Separada / shunt: ifd = Va/Rf (shunt) ou Vf/Rf (sep → usamos Vf=Va/2)
    ifd_shunt = Va / Rf
    ifd_sep   = (Va * 0.5) / Rf

    def Te_lin(ifd: float, wm_arr: np.ndarray) -> np.ndarray:
        ia = (Va - kb * ifd * wm_arr) / Ra
        return kb * ifd * ia

    # Série: Te = kb² * ia², ia = Va / (Ra+Rf + kb*wm)
    Raf   = Ra + 0.026   # Ra_serie do preset dcms
    ia_s  = Va / (Raf + kb * wm + 1e-9)
    Te_serie = kb * ia_s * ia_s

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wm, y=Te_lin(ifd_sep, wm), mode="lines",
                             name="Separada", line=dict(color="#60a5fa", width=2)))
    fig.add_trace(go.Scatter(x=wm, y=Te_lin(ifd_shunt, wm), mode="lines",
                             name="Shunt", line=dict(color="#34d399", width=2)))
    fig.add_trace(go.Scatter(x=wm, y=np.maximum(Te_serie, 0), mode="lines",
                             name="Série", line=dict(color="#f87171", width=2)))
    fig.add_hline(y=Tload, line_dash="dot", line_color="#f59e0b",
                  annotation_text="Carga", annotation_position="right")

    fig.update_layout(
        xaxis_title="ωm (rad/s)", yaxis_title="Te (N·m)",
        height=320,
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=50, r=20, t=30, b=40),
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right", font=dict(size=9)),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True, key="theory_torque_speed_dc")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Padrões de corrente
# ─────────────────────────────────────────────────────────────────────────────

def render_padrao_corrente_dc() -> None:
    st.markdown("### Corrente de Armadura $i_a(t)$ por Excitação")

    exc_opt = st.radio("Excitação", ["sep_motor", "shunt_motor", "series_motor"],
                       format_func=lambda x: {
                           "sep_motor": "Separada",
                           "shunt_motor": "Shunt",
                           "series_motor": "Série",
                       }[x],
                       horizontal=True, key="theory_dc_exc_radio")

    if st.button("Simular", key="theory_dc_simular"):
        from core.dc_machine_model import DCMachineParams
        from core.dc_solver import run_simulation_dc
        from core.dc_sources import make_voltage_fn_dc, make_torque_fn_dc

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
        with st.spinner("Simulando..."):
            res = run_simulation_dc(p, tmax=8.0, h=1e-3, voltage_fn=vfn, torque_fn=tfn)

        dark = st.session_state.get("dark_mode", False)
        pt   = _plot_theme(dark)
        fig  = go.Figure()
        fig.add_trace(go.Scatter(x=res["t"], y=res["ia"], mode="lines", name="$i_a$",
                                 line=dict(color="#60a5fa", width=1.8)))
        fig.update_layout(
            xaxis_title="Tempo (s)", yaxis_title="ia (A)",
            height=280,
            paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
            font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
            margin=dict(l=50, r=20, t=30, b=40),
        )
        st.plotly_chart(fig, use_container_width=True, key="theory_ia_dc")
        st.caption(f"Regime: $i_{{a,ss}}$ = {res['ia_ss']:.3f} A | $n_{{ss}}$ = {res['n_ss']:.1f} RPM")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Controle de velocidade
# ─────────────────────────────────────────────────────────────────────────────

def render_controle_velocidade_dc() -> None:
    st.markdown("### Enfraquecimento de Campo — Controle de Velocidade")

    Va  = 24.0
    Ra  = 0.013
    kb  = 0.004
    Rf  = 1.43
    Tload = 2.493

    Vf_pct = st.slider("$V_f$ (% do nominal)", 20, 100, 100, step=5,
                        key="theory_dc_Vf_pct")
    Vf = Va * Vf_pct / 100.0

    ifd  = Vf / Rf
    # Regime: Te = Tload → kb*ifd*ia = Tload → ia = Tload/(kb*ifd)
    ia   = Tload / (kb * ifd) if ifd > 1e-9 else 0.0
    Ea   = Va - Ra * ia
    wm   = Ea / (kb * ifd) if ifd > 1e-9 else 0.0
    n    = wm * 60 / (2 * np.pi)

    c1, c2, c3 = st.columns(3)
    c1.metric("$i_{fd}$ (A)", f"{ifd:.3f}")
    c2.metric("$\\omega_m$ (rad/s)", f"{wm:.1f}")
    c3.metric("$n$ (RPM)", f"{n:.0f}")

    st.caption(
        "Reduzindo $V_f$ → $i_{fd}$ cai → $\\omega_m$ sobe (enfraquecimento de campo). "
        "Atenção: $i_a$ aumenta para manter $T_e$."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Estimador DC
# ─────────────────────────────────────────────────────────────────────────────

def render_estimador_dc() -> None:
    st.markdown("### Estimador de Parâmetros por Ensaios")

    with st.form("form_estimador_dc"):
        st.markdown("**Ensaio de resistência CC** (rotor parado, campo excitado)")
        f1, f2 = st.columns(2)
        V_dc = f1.number_input("$V_{dc}$ (V)", min_value=0.01, value=1.0, format="%.3f")
        I_dc = f2.number_input("$I_{dc}$ (A)", min_value=0.001, value=0.1, format="%.3f")

        st.markdown("**Ensaio a vazio** (sem carga mecânica)")
        g1, g2, g3, g4 = st.columns(4)
        V_nl  = g1.number_input("$V_{a,nl}$ (V)", min_value=0.01, value=24.0, format="%.3f")
        I_nl  = g2.number_input("$I_{a,nl}$ (A)", min_value=0.001, value=0.05, format="%.3f")
        If_nl = g3.number_input("$I_{fd,nl}$ (A)", min_value=0.001, value=8.4, format="%.3f")
        n_nl  = g4.number_input("$n_{nl}$ (RPM)", min_value=1.0, value=6500.0, format="%.1f")

        submitted = st.form_submit_button("Estimar")

    if submitted:
        Ra = V_dc / I_dc
        wm_nl = n_nl * 2 * np.pi / 60
        Ea_nl = V_nl - Ra * I_nl
        kb    = Ea_nl / (If_nl * wm_nl) if (If_nl * wm_nl) > 1e-9 else 0.0

        st.success(f"$R_a$ = **{Ra:.4f} Ω** | $k_b$ = **{kb:.5f} V·s/rad**")
        st.markdown(
            f"Verificação: $E_{{a,nl}} = V_{{a,nl}} - R_a I_{{a,nl}} = "
            f"{V_nl:.3f} - {Ra:.4f}×{I_nl:.3f} = {Ea_nl:.4f}$ V"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Diagrama de blocos
# ─────────────────────────────────────────────────────────────────────────────

def render_diagrama_blocos_mcc() -> None:
    st.markdown("### Diagrama de Blocos do Modelo de Estado")
    st.markdown(r"""
```
Va ──► [ 1/(La·s + Ra) ] ──► ia ──► kb·ifd ──► Te ──► [ 1/(J·s + B) ] ──► ωm
                  ▲                                              │
                  └──────────────── kb·ifd·ωm ◄──────────────────┘
                                    (back-EMF Ea)

Vf ──► [ 1/(Lf·s + Rf) ] ──► ifd ──►(ambos acima)
```
- $T_e = k_b \, i_{fd} \, i_a$
- $E_a = k_b \, i_{fd} \, \omega_m$
- Série: $i_{fd} = i_a$ (campo em série com armadura)
""")
