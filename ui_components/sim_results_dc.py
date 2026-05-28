# -*- coding: utf-8 -*-
"""Renderização de resultados MCC — 4 sub-abas espelhando sim_results.py MIT.

Exporta:
    render_results_dc — 4 abas (Visão Geral, Análise Dinâmica, Diagnóstico e Falhas, Gestão de Ativos)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.dc_machine_model import DCMachineParams
from viz.plotly_charts_dc import (
    build_fig_stacked_dc,
    build_fig_sidebyside_dc,
    build_fig_overlay_dc,
    build_fig_torque_speed_dc,
)


# ─────────────────────────────────────────────────────────────────────────────
# CACHE LAYER (espelha sim_results.py:28–56)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_fig_stacked_dc(
    res: dict,
    var_keys: tuple,
    var_labels: tuple,
    dark: bool,
    t_events: tuple,
    decimals: int,
    _cache_key: int = 0,
) -> go.Figure:
    return build_fig_stacked_dc(res, list(var_keys), list(var_labels), dark, list(t_events), decimals)


@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed_dc(
    res: dict,
    exc: str,
    dark: bool,
    _cache_key: int = 0,
) -> go.Figure:
    return build_fig_torque_speed_dc(res, exc, dark)


_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "mcc_simulacao",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
}

_EXC_LABELS: dict[str, str] = {
    "sep_motor":    "Excitação Separada — Motor",
    "shunt_motor":  "Shunt (Paralelo) — Motor",
    "series_motor": "Série — Motor",
    "sep_gen":      "Excitação Separada — Gerador",
    "shunt_gen":    "Shunt (Paralelo) — Gerador",
}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def render_results_dc(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    mp: DCMachineParams,
    exp_label: str,
    exp_type: str,
    exp_config: dict,
    tmax: float,
    h: float,
    decimals: int = 3,
    ref_list: list | None = None,
    **kwargs,
) -> None:
    """Renderiza as 4 sub-abas de resultados MCC."""
    d   = decimals
    exc = mp.excitation if mp else res.get("excitation", "sep_motor")
    is_gen = exc in ("sep_gen", "shunt_gen")

    _cache_key = hash(repr(res.get("ia", [])[:5]))

    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs(
        ["Visão Geral", "Análise Dinâmica", "Diagnóstico e Falhas", "Gestão de Ativos"],
        key="results_tabs_dc",
    )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 1 — VISÃO GERAL
    # ══════════════════════════════════════════════════════════════════════
    with tab_visao:
        n_ss   = res.get("n_ss",   0.0)
        Te_ss  = res.get("Te_ss",  0.0)
        ia_ss  = res.get("ia_ss",  0.0)
        ifd_ss = res.get("ifd_ss", 0.0)
        Ea_ss  = res.get("Ea_ss",  0.0)
        Vt_ss  = res.get("Vt_ss",  0.0)
        wm_ss  = res.get("wm_ss",  0.0)

        # Painel de saúde simplificado
        ia_peak = float(np.max(np.abs(res["ia"])))
        Va_nom  = mp.Va if mp else 24.0
        overcurrent = ia_peak > 10.0 * abs(ia_ss) if abs(ia_ss) > 1e-6 else False

        if not res.get("success", True):
            st.error("🔴 **Falha Numérica** — integrador não convergiu. Reduza $h$ ou revise parâmetros.")
        elif overcurrent:
            st.warning(f"🟡 **Atenção** — pico de $i_a$ = {ia_peak:.1f} A "
                       f"({ia_peak/max(abs(ia_ss),1e-6):.1f}× regime). "
                       f"Velocidade regime: **{n_ss:.0f} RPM**")
        else:
            st.success(f"🟢 **Operação Normal** — $n$ = **{n_ss:.0f} RPM** | "
                       f"$T_e$ = **{Te_ss:.{d}f} N·m** | "
                       f"$i_a$ = **{ia_ss:.{d}f} A**")

        st.write("")

        # KPIs
        st.markdown('<p class="slabel">Grandezas de Operação</p>', unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric("Velocidade (RPM)",       f"{n_ss:.{d}f}")
        k2.metric("$T_e$ (N·m)",            f"{Te_ss:.{d}f}")
        k3.metric("$i_a$ (A)",              f"{ia_ss:.{d}f}")

        k4, k5, k6 = st.columns(3)
        k4.metric("$\\omega_m$ (rad/s)",    f"{wm_ss:.{d}f}")
        k5.metric("$E_a$ (V)",              f"{Ea_ss:.{d}f}")
        k6.metric("$V_t$ (V)",              f"{Vt_ss:.{d}f}")

        if exc not in ("series_motor",):
            k7, k8, _ = st.columns(3)
            k7.metric("$i_{fd}$ (A)",       f"{ifd_ss:.{d}f}")
            k8.metric("Excitação",          _EXC_LABELS.get(exc, exc))

        # Transitório resumido
        with st.expander("Transitório de Partida", expanded=False):
            tc1, tc2 = st.columns(2)
            tc1.metric("Pico $i_a$ (A)",    f"{float(np.max(np.abs(res['ia']))):.{d}f}")
            tc2.metric("Pico $T_e$ (N·m)",  f"{float(np.max(res['Te'])):.{d}f}")

    # ══════════════════════════════════════════════════════════════════════
    # ABA 2 — ANÁLISE DINÂMICA
    # ══════════════════════════════════════════════════════════════════════
    with tab_dinamica:
        _cc1, _cc2, _cc3 = st.columns([2, 2, 1])
        with _cc1:
            viz_opts  = ["Empilhado", "Lado a Lado", "Sobreposto"]
            plot_mode = st.radio("Visualização", viz_opts, horizontal=True,
                                 key="plot_mode_dc", label_visibility="visible")
        with _cc2:
            zoom_opts = ["Completo", "Transitório", "Regime"]
            zoom_mode = st.radio("Zoom", zoom_opts, horizontal=True,
                                 key="zoom_mode_dc", label_visibility="visible")
        with _cc3:
            dark_plot = st.toggle("Fundo escuro", key="plot_dark_dc", value=dark)

        # Filtro de zoom temporal
        t_arr = res["t"]
        tmax_sim = float(t_arr[-1])
        if zoom_mode == "Transitório":
            t_cut = tmax_sim * 0.3
            mask  = t_arr <= t_cut
        elif zoom_mode == "Regime":
            t_cut = tmax_sim * 0.7
            mask  = t_arr >= t_cut
        else:
            mask = np.ones(len(t_arr), dtype=bool)

        res_zoom = {k: (v[mask] if isinstance(v, np.ndarray) and len(v) == len(t_arr) else v)
                    for k, v in res.items()}

        tl_arr = res_zoom.get("Tl")

        if plot_mode == "Empilhado":
            fig = _cached_fig_stacked_dc(
                res_zoom, tuple(var_keys), tuple(var_labels),
                dark_plot, tuple(t_events), d, _cache_key=_cache_key,
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key="dc-stacked")

        elif plot_mode == "Lado a Lado":
            figs = build_fig_sidebyside_dc(
                res_zoom, var_keys, var_labels, dark_plot, list(t_events), d,
                ref_list=ref_list, tl_arr=tl_arr,
            )
            for i, f in enumerate(figs):
                st.plotly_chart(f, use_container_width=True, config=_PLOT_CFG, key=f"dc-side-{i}")

        else:  # Sobreposto
            fig = build_fig_overlay_dc(
                res_zoom, var_keys, var_labels, dark_plot, list(t_events), d,
                ref_list=ref_list, tl_arr=tl_arr,
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key="dc-overlay")

        # Curva T×ωn
        st.markdown('<p class="slabel">Curva Conjugado × Velocidade</p>', unsafe_allow_html=True)
        fig_tn = _cached_fig_torque_speed_dc(res, exc, dark_plot, _cache_key=_cache_key)
        st.plotly_chart(fig_tn, use_container_width=True, config=_PLOT_CFG, key="dc-torque-speed")

    # ══════════════════════════════════════════════════════════════════════
    # ABA 3 — DIAGNÓSTICO E FALHAS
    # ══════════════════════════════════════════════════════════════════════
    with tab_diag:
        st.markdown('<p class="slabel">Análise de Comutação e Corrente</p>', unsafe_allow_html=True)

        ia_arr  = res["ia"]
        ia_max  = float(np.max(np.abs(ia_arr)))
        ia_min  = float(np.min(ia_arr[len(ia_arr)//2:]))  # metade final
        ia_std  = float(np.std(ia_arr[len(ia_arr)//2:]))

        d1, d2, d3 = st.columns(3)
        d1.metric("Pico $i_a$ (A)",         f"{ia_max:.{d}f}")
        d2.metric("$i_a$ regime (A)",        f"{ia_ss:.{d}f}")
        d3.metric("Ripple $\\sigma(i_a)$",   f"{ia_std:.{d}f}")

        # Verificações
        anomalias: list[tuple[str, str, str]] = []

        if ia_max > 15.0 * max(abs(ia_ss), 1e-6):
            anomalias.append(("🔴 Crítico", "Sobrecorrente extrema na partida",
                               f"Pico {ia_max:.1f} A = {ia_max/max(abs(ia_ss),1e-6):.0f}× regime. "
                               "Use resistência série ou reduza $V_a$."))

        if not res.get("success", True):
            anomalias.append(("🔴 Crítico", "Falha numérica do integrador",
                               "Reduza $h$ para 1×10⁻⁵ s ou verifique parâmetros."))

        if exc not in ("series_motor",):
            ifd_arr = res["ifd"]
            ifd_std = float(np.std(ifd_arr[len(ifd_arr)//2:]))
            if ifd_std > 0.05 * max(abs(ifd_ss), 1e-6):
                anomalias.append(("🟡 Alerta", "Instabilidade de campo",
                                   f"$\\sigma(i_{{fd}})$ = {ifd_std:.4f} A em regime. "
                                   "Verifique $R_f$ e $L_f$."))

        wm_arr = res["wm"]
        if len(wm_arr) > 10 and float(np.mean(wm_arr[-10:])) < 0.01 * abs(wm_ss) and abs(wm_ss) > 1:
            anomalias.append(("🟡 Alerta", "Regime não atingido",
                               f"$\\omega_m$ ainda em transitório ao fim da simulação. "
                               "Aumente $t_{{max}}$."))

        if not anomalias:
            st.success("🟢 Nenhuma anomalia detectada.")
        else:
            for sev, titulo, desc in anomalias:
                with st.expander(f"{sev} — {titulo}", expanded=True):
                    st.write(desc)

        # FFT de corrente de armadura
        with st.expander("FFT de $i_a$ (Ripple harmônico)", expanded=False):
            try:
                from numpy.fft import rfft, rfftfreq
                ia_half = ia_arr[len(ia_arr)//2:]
                N  = len(ia_half)
                dt = float(res["t"][1] - res["t"][0])
                f_fft = rfftfreq(N, d=dt)
                Y     = np.abs(rfft(ia_half - np.mean(ia_half))) * 2 / N
                fig_f = go.Figure()
                fig_f.add_trace(go.Bar(x=f_fft[:N//4], y=Y[:N//4], name="Amplitude"))
                fig_f.update_layout(
                    title="Espectro de $i_a$", xaxis_title="Frequência (Hz)",
                    yaxis_title="Amplitude (A)", height=300,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_f, use_container_width=True, config=_PLOT_CFG, key="dc-fft")
            except Exception:
                st.caption("FFT indisponível.")

    # ══════════════════════════════════════════════════════════════════════
    # ABA 4 — GESTÃO DE ATIVOS
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativos:
        st.markdown('<p class="slabel">Análise de Eficiência e Perdas</p>', unsafe_allow_html=True)

        Ra   = mp.Ra if mp else 1.0
        Rf   = mp.Rf if mp else 0.0
        B    = mp.B  if mp else 0.0
        Va   = mp.Va if mp else 24.0

        P_Ra   = float(ia_ss ** 2 * Ra)
        P_Rf   = float(ifd_ss ** 2 * Rf) if exc not in ("series_motor",) else 0.0
        P_mec  = float(B * wm_ss ** 2)
        P_elec = float(abs(Va) * abs(ia_ss)) if not is_gen else 0.0
        P_mec_out = float(abs(Te_ss) * abs(wm_ss))

        if is_gen:
            eta = P_elec / max(P_mec_out, 1e-9) * 100 if P_mec_out > 0 else 0.0
        else:
            eta = P_mec_out / max(P_elec, 1e-9) * 100 if P_elec > 0 else 0.0

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Eficiência η (%)",       f"{eta:.1f}")
        a2.metric("P. Joule $R_a$ (W)",     f"{P_Ra:.3f}")
        a3.metric("P. Joule $R_f$ (W)",     f"{P_Rf:.3f}")
        a4.metric("P. Atrito (W)",           f"{P_mec:.4f}")

        b1, b2 = st.columns(2)
        b1.metric("P. Elétrica (W)",         f"{P_elec:.3f}")
        b2.metric("P. Mecânica (W)",          f"{P_mec_out:.3f}")

        Te_nom = mp.Tload if mp else 2.493
        util   = abs(Te_ss) / max(abs(Te_nom), 1e-9) * 100
        st.metric("Fator de Utilização (%)", f"{util:.1f}")

        # Sankey simplificado
        with st.expander("Diagrama de Sankey (Potências)", expanded=False):
            try:
                if not is_gen and P_elec > 0:
                    labels = ["P. Elétrica", "P. Mecânica", "P. Joule Ra", "P. Joule Rf", "P. Atrito"]
                    source = [0, 0, 0, 0]
                    target = [1, 2, 3, 4]
                    value  = [max(P_mec_out, 0), max(P_Ra, 0), max(P_Rf, 0), max(P_mec, 0)]
                    fig_s  = go.Figure(go.Sankey(
                        node=dict(label=labels, pad=15, thickness=20),
                        link=dict(source=source, target=target, value=value),
                    ))
                    fig_s.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_s, use_container_width=True, config=_PLOT_CFG, key="dc-sankey")
                else:
                    st.caption("Sankey disponível apenas para modo motor.")
            except Exception:
                st.caption("Sankey indisponível.")
