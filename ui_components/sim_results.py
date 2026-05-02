# -*- coding: utf-8 -*-
"""Renderização de resultados da simulação: KPIs, gráficos e exportação PDF.

Exporta:
    render_results   — KPIs + gráficos Plotly + botão de exportação PDF
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.EMS_PY import MachineParams
from viz.plotly_charts import build_fig_stacked, build_fig_sidebyside, build_fig_overlay, build_fig_torque_speed
from viz.pdf_report import generate_pdf_report
from core.harmonica_analysis import build_fig_fft


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _strip_latex(s: str) -> str:
    """Converte notação LaTeX $...$ para texto simples (uso em labels do Plotly)."""
    _greek = {
        '\\omega': 'ω', '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ',
        '\\delta': 'δ', '\\theta': 'θ', '\\tau': 'τ', '\\phi': 'φ',
        '\\psi': 'ψ', '\\lambda': 'λ', '\\mu': 'μ', '\\sigma': 'σ',
        '\\pi': 'π', '\\eta': 'η',
    }
    def _convert(m: re.Match) -> str:
        inner = m.group(1)
        for cmd, uni in _greek.items():
            inner = inner.replace(cmd, uni)
        inner = inner.replace('{', '').replace('}', '').replace('_', '').replace('\\', '')
        return inner
    return re.sub(r'\$([^$]+)\$', _convert, s)


_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "grafico_simulador",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICAS DE ENERGIA E ANÁLISE ECONÔMICA
# ─────────────────────────────────────────────────────────────────────────────

def compute_energy_metrics(res: dict, tarifa_brl_kwh: float) -> dict:
    """Calcula energia consumida, rendimento médio, custo operacional, THD e FP.

    Integra P_in = (3/2)·(Vqs·iqs + Vds·ids) sobre todo o intervalo de simulação.
    O rendimento é calculado na janela de regime permanente.
    THD = sqrt(Σ Ak² k≥2) / A1 × 100% via FFT de ias na janela de regime permanente.
    FP = P_in_ss / S_aparente onde S = 3 × Va_rms × ias_rms.

    Returns dict com:
        E_total_kwh   — energia total consumida no experimento (kWh)
        custo_exp_brl — custo do experimento (R$)
        horas_op_ano  — horas de operação projetadas por ano (baseado no perfil)
        custo_ano_brl — custo operacional anual projetado (R$)
        eta_ss        — rendimento em regime permanente (%)
        P_in_ss_kw    — potência de entrada em regime (kW)
        thd_pct       — THD de ias em regime permanente (%)
        fp            — Fator de Potência em regime permanente (adimensional)
    """
    t   = np.asarray(res["t"],   dtype=float)
    Vqs = np.asarray(res["Vqs"], dtype=float)
    Vds = np.asarray(res["Vds"], dtype=float)
    iqs = np.asarray(res["iqs"], dtype=float)
    ids = np.asarray(res["ids"], dtype=float)

    P_in_inst = (3.0 / 2.0) * (Vqs * iqs + Vds * ids)  # W instantâneo
    E_total_j   = float(np.trapezoid(np.where(np.isfinite(P_in_inst), P_in_inst, 0.0), t))
    E_total_kwh = E_total_j / 3_600_000.0
    custo_exp_brl = E_total_kwh * tarifa_brl_kwh

    # regime permanente
    ss_start    = int(res.get("_ss_start", 0))
    eta_ss      = float(res.get("eta", 0.0))
    P_in_ss     = float(res.get("P_in", 0.0))
    P_in_ss_kw  = P_in_ss / 1000.0

    # projeção anual: assume perfil de carga contínua (24 h × 365 d) baseado em P_in_ss
    horas_op_ano  = 8_760.0
    E_ano_kwh     = P_in_ss_kw * horas_op_ano
    custo_ano_brl = E_ano_kwh * tarifa_brl_kwh

    # ── THD de ias na janela de regime permanente ──────────────────────────
    thd_pct = 0.0
    fp      = 0.0
    try:
        ias_ss = np.asarray(res["ias"][ss_start:], dtype=float)
        t_ss   = t[ss_start:]
        if len(ias_ss) >= 16:
            dt_ss = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
            N     = len(ias_ss)
            spec  = np.abs(np.fft.rfft(ias_ss)) / N
            freqs = np.fft.rfftfreq(N, d=dt_ss)
            # fundamental: bin mais próximo de 60 Hz (ou 50 Hz) — usar maior pico abaixo de 2×f
            f_fund_approx = float(res.get("_f_fund", 60.0)) if "_f_fund" in res else 60.0
            mask_fund = (freqs > 0.5 * f_fund_approx) & (freqs < 1.5 * f_fund_approx)
            if mask_fund.any():
                A1 = float(spec[mask_fund].max())
                # harmônicas: todos os bins acima de 1,5×f_fund (excluindo DC e fundamental)
                mask_harm = freqs > 1.5 * f_fund_approx
                A_harm    = spec[mask_harm]
                if A1 > 0 and len(A_harm) > 0:
                    thd_pct = float(np.sqrt(np.sum(A_harm ** 2)) / A1 * 100.0)

        # ── Fator de Potência ──────────────────────────────────────────────
        # Va_rms: fase a — tensão de linha / sqrt(3). Vqs, Vds são componentes qd0.
        # |Va| = sqrt(Vqs² + Vds²) / sqrt(2) em pico→RMS assumindo balanço
        Vqs_ss  = Vqs[ss_start:]
        Vds_ss  = Vds[ss_start:]
        Va_pk   = float(np.sqrt(np.mean(Vqs_ss ** 2 + Vds_ss ** 2)))
        Va_rms  = Va_pk / np.sqrt(2.0)
        ias_rms = float(res.get("ias_rms", 0.0))
        S_ap    = 3.0 * Va_rms * ias_rms
        if S_ap > 0 and np.isfinite(P_in_ss):
            fp = float(np.clip(abs(P_in_ss) / S_ap, 0.0, 1.0))
    except Exception:
        pass

    return {
        "E_total_kwh":   E_total_kwh,
        "custo_exp_brl": custo_exp_brl,
        "horas_op_ano":  horas_op_ano,
        "custo_ano_brl": custo_ano_brl,
        "eta_ss":        eta_ss,
        "P_in_ss_kw":    P_in_ss_kw,
        "thd_pct":       thd_pct,
        "fp":            fp,
    }


# ─────────────────────────────────────────────────────────────────────────────
# KPIs POR EXPERIMENTO
# ─────────────────────────────────────────────────────────────────────────────

def _kpis_destaque(
    res: dict,
    exp_type: str,
    mp: MachineParams,
    d: int,
    t_events: list | None = None,
) -> list[tuple]:
    """Retorna lista de (label, valor, unidade) com KPIs prioritários por experimento."""
    ias_pk  = float(np.max(np.abs(res["ias"])))
    Te_max  = float(np.max(res["Te"]))
    n_ss    = res["n_ss"]
    ias_rms = res["ias_rms"]
    s_val   = res.get("s", 0.0)
    fator_pk = ias_pk / ias_rms if ias_rms > 0 else 0.0

    if exp_type in ("dol", "yd", "comp", "soft"):
        items = [
            ("Corrente de Pico $i_{as}$", f"{ias_pk:.{d}f}", "A"),
            ("Fator de Pico  ($I_{pk}$ / $I_{rms}$)", f"{fator_pk:.{d}f}", "—"),
            ("Torque Máximo $T_{e,max}$", f"{Te_max:.{d}f}", "N·m"),
            ("Velocidade Final", f"{n_ss:.{d}f}", "RPM"),
        ]
        if exp_type == "yd":
            _tevs = t_events or []
            t_ev  = _tevs[1] if len(_tevs) > 1 else (_tevs[0] if _tevs else 0.0)
            idx   = int(np.searchsorted(res["t"], t_ev))
            ias_pk2 = float(np.max(np.abs(res["ias"][idx:]))) if idx < len(res["t"]) else 0.0
            items.insert(1, ("Corrente de Pico pos-comutacao Y→D", f"{ias_pk2:.{d}f}", "A"))
        elif exp_type == "comp":
            _tevs      = t_events or []
            t_ev_comp  = _tevs[0] if _tevs else 0.0
            idx_comp   = int(np.searchsorted(res["t"], t_ev_comp))
            ias_pk2_comp = float(np.max(np.abs(res["ias"][idx_comp:]))) if idx_comp < len(res["t"]) else 0.0
            items.insert(1, ("Corrente de Pico pos-comutacao AT", f"{ias_pk2_comp:.{d}f}", "A"))

    elif exp_type == "carga":
        _tevs_c    = t_events or []
        t_carga_ev = _tevs_c[0] if _tevs_c else 0.0
        idx_tc     = max(int(np.searchsorted(res["t"], t_carga_ev)), 1)
        n_antes    = float(np.mean(res["n"][:idx_tc]))
        delta_n    = n_antes - n_ss
        delta_i    = ias_rms - float(np.sqrt(np.mean(res["ias"][:idx_tc]**2)))
        lbl_delta  = "Afundamento de Velocidade" if delta_n >= 0 else "Elevação de Velocidade"
        items = [
            ("Velocidade Antes da Perturbação",  f"{n_antes:.{d}f}",      "RPM"),
            ("Velocidade após Perturbação",       f"{n_ss:.{d}f}",         "RPM"),
            (lbl_delta,                           f"{abs(delta_n):.{d}f}", "RPM"),
            ("Variação de Corrente RMS",          f"{delta_i:.{d}f}",      "A"),
        ]

    elif exp_type == "gerador":
        P_out = res.get("P_out", 0.0)
        eta   = res.get("eta",   0.0)
        lbl_p = "kW" if abs(P_out) >= 1000 else "W"
        val_p = P_out / 1000 if abs(P_out) >= 1000 else P_out
        items = [
            ("Potencia Gerada para a Rede", f"{val_p:.{d}f}",        lbl_p),
            ("Escorregamento",              f"{s_val*100:.{d}f}",    "%"),
            ("Rendimento",                  f"{eta:.{d}f}",          "%"),
            ("Corrente RMS de Geracao",     f"{ias_rms:.{d}f}",      "A"),
        ]

    elif exp_type == "voltage_sag":
        _tevs  = t_events or []
        # t_end do sag é o último evento registrado (t_sag, t_end)
        t_sag_start = _tevs[0] if len(_tevs) >= 1 else 0.0
        t_sag_end   = _tevs[1] if len(_tevs) >= 2 else (t_sag_start + 0.1)
        t_arr       = np.asarray(res["t"])
        idx_sag     = int(np.searchsorted(t_arr, t_sag_start))
        idx_rec     = int(np.searchsorted(t_arr, t_sag_end))

        # profundidade do afundamento: tensão de linha durante o sag
        Vqs_sag = np.asarray(res["Vqs"])
        Vds_sag = np.asarray(res["Vds"])
        Va_pre  = float(np.sqrt(np.mean(Vqs_sag[:max(1,idx_sag)]**2 + Vds_sag[:max(1,idx_sag)]**2))) if idx_sag > 0 else 1.0
        Va_dur  = float(np.sqrt(np.mean(Vqs_sag[idx_sag:idx_rec]**2 + Vds_sag[idx_sag:idx_rec]**2))) if idx_rec > idx_sag else Va_pre
        depth_pct = (1.0 - Va_dur / Va_pre) * 100.0 if Va_pre > 0 else 0.0

        # corrente de re-partida após recuperação
        ias_arr   = np.abs(np.asarray(res["ias"]))
        ias_restart = float(np.max(ias_arr[idx_rec:])) if idx_rec < len(ias_arr) else 0.0

        # duração do transitório de recuperação: tempo até |ias| cair abaixo de 1,5×ias_rms
        ias_rms_val = float(res.get("ias_rms", 1.0))
        thresh_rec  = 1.5 * ias_rms_val if ias_rms_val > 0 else ias_restart * 0.5
        above       = np.where(ias_arr[idx_rec:] > thresh_rec)[0]
        t_trans     = float(t_arr[idx_rec + above[-1]] - t_arr[idx_rec]) if len(above) > 0 else 0.0

        items = [
            ("Profundidade do Afundamento",     f"{depth_pct:.{d}f}",    "%"),
            ("Corrente de Re-Partida (pico)",   f"{ias_restart:.{d}f}",  "A"),
            ("Corrente de Pico (inicial)",       f"{ias_pk:.{d}f}",       "A"),
            ("Duração do Transitório",          f"{t_trans:.{d}f}",      "s"),
            ("Velocidade Final",                f"{n_ss:.{d}f}",         "RPM"),
        ]

    elif exp_type == "shutdown":
        _tevs   = t_events or []
        t_cut   = _tevs[1] if len(_tevs) > 1 else (_tevs[0] if _tevs else 0.0)
        t_arr   = res["t"]
        idx_cut = int(np.searchsorted(t_arr, t_cut))
        w0      = max(1, idx_cut - max(1, idx_cut // 20))
        n_pre   = float(np.mean(res["n"][w0:idx_cut])) if idx_cut > 0 else 0.0
        n_final = float(np.mean(res["n"][-max(1, len(res["n"]) // 10):]))
        thresh  = 0.01 * n_pre if n_pre > 0 else 1.0
        stop_idx = int(np.searchsorted(np.abs(res["n"][idx_cut:]), thresh, side="right"))
        t_stop  = float(t_arr[idx_cut + stop_idx]) if stop_idx < len(t_arr) - idx_cut else float(t_arr[-1])
        items = [
            ("Velocidade pré-desligamento", f"{n_pre:.{d}f}",  "RPM"),
            ("Velocidade final simulada",   f"{n_final:.{d}f}", "RPM"),
            ("Instante do corte",           f"{t_cut:.{d}f}",   "s"),
            ("Tempo de parada estimado",    f"{t_stop:.{d}f}",  "s"),
            ("Corrente de pico (partida)",  f"{ias_pk:.{d}f}",  "A"),
        ]

    else:
        items = []

    return items


# ─────────────────────────────────────────────────────────────────────────────
# RENDERIZAÇÃO DE RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────

_REF_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
_REF_DASHES = ["dash", "dot", "solid", "dash", "dot"]


def render_ref_panel() -> None:
    """Painel de gerenciamento de referências salvas.

    Lê e escreve diretamente em st.session_state["ref_list"].
    Deve ser chamado antes de render_results para que as edições de cor/dash
    estejam disponíveis na renderização dos gráficos.
    """
    ref_list = st.session_state.get("ref_list", [])
    if not ref_list:
        return

    st.markdown('<p class="slabel">Referências Salvas</p>', unsafe_allow_html=True)
    _dash_opts = {"Tracejado": "dash", "Pontilhado": "dot", "Sólido": "solid"}
    _h1, _h2, _h3, _h4 = st.columns([5, 0.55, 1.5, 0.4])
    _h2.caption("Cor")
    _h3.caption("Linha")
    for _i, _ref in enumerate(ref_list):
        _c1, _c2, _c3, _c4 = st.columns([5, 0.55, 1.5, 0.4])
        with _c1:
            st.markdown(
                f'<div style="padding:0.38rem 0.75rem;border-radius:6px;'
                f'background:rgba(128,128,128,0.08);font-size:0.88rem;'
                f'border-left:3px solid {_ref.get("color","#888")};">'
                f'<strong>{_ref.get("exp_label","Referência")}</strong></div>',
                unsafe_allow_html=True,
            )
        with _c2:
            _ref["color"] = st.color_picker(
                "Cor", value=_ref.get("color", "#888888"),
                key=f"ref_color_{_i}", label_visibility="collapsed",
            )
        with _c3:
            _cur = _ref.get("dash", "dash")
            _idx = list(_dash_opts.values()).index(_cur) if _cur in _dash_opts.values() else 0
            _sel = st.selectbox(
                "Linha", list(_dash_opts.keys()), index=_idx,
                key=f"ref_dash_{_i}", label_visibility="collapsed",
            )
            _ref["dash"] = _dash_opts[_sel]
        with _c4:
            if st.button("✕", key=f"ref_del_{_i}", help="Remover esta referência"):
                st.session_state["ref_list"].pop(_i)
                st.rerun()


def render_results(
    res: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    mp: MachineParams,
    exp_label: str,
    exp_type: str = "dol",
    decimals: int = 3,
    ref_list: list | None = None,
    primary_color: str | None = None,
    is_mobile: bool = False,
    energy_tariff: float = 0.75,
) -> None:
    """KPIs + gráficos + análise econômica + FFT + botão PDF."""
    st.divider()
    d = decimals

    # ── helpers internos ─────────────────────────────────────────────────
    def fmt_pot(val: float, decimals: int) -> tuple[str, str]:
        if abs(val) >= 1000:
            return "kW", f"{val/1000:.{decimals}f}"
        return "W", f"{val:.{decimals}f}"

    def _render_plotly(fig: go.Figure, div_id: str = "ems-plot") -> None:
        st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key=div_id)

    # ── preparar fig PDF e zoom antes das abas (usados em múltiplas abas) ─
    var_labels_plot = [_strip_latex(lbl) for lbl in var_labels]

    # dark_plot: prefer session_state toggle se já existir, senão usa dark do tema
    dark_plot = st.session_state.get("plot_dark_toggle", dark)

    fig_pdf = build_fig_stacked(res, var_keys, var_labels_plot, dark_plot, t_events, d)

    chart_ref_list = [
        {
            "res":   r["res"],
            "color": r.get("color", "#888888"),
            "dash":  r.get("dash", "dash"),
            "label": r.get("exp_label", "Referência"),
        }
        for r in (ref_list or [])
        if r.get("res") is not None
    ]

    # ── cálculo de energia (necessário nas abas 1 e 4) ───────────────────
    _em = compute_energy_metrics(res, energy_tariff) if exp_type != "shutdown" else {}

    # ══════════════════════════════════════════════════════════════════════
    # ABAS DE RESULTADOS
    # ══════════════════════════════════════════════════════════════════════
    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs([
        "Visão Geral",
        "Análise Dinâmica",
        "Diagnóstico e Falhas",
        "Gestão de Ativos",
    ])

    # ══════════════════════════════════════════════════════════════════════
    # ABA 1 — VISÃO GERAL
    # ══════════════════════════════════════════════════════════════════════
    with tab_visao:
        destaques = _kpis_destaque(res, exp_type, mp, d, t_events)
        if destaques:
            st.markdown('<p class="slabel">Destaques do Experimento</p>', unsafe_allow_html=True)
            cols = st.columns(len(destaques))
            for col, (lbl, val, unit) in zip(cols, destaques):
                col.metric(f"{lbl} ({unit})", val)
            st.write("")

        # Trip Class
        if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
            try:
                _n_arr    = np.asarray(res["n"], dtype=float)
                _t_arr    = np.asarray(res["t"], dtype=float)
                _n_sync   = mp.f / mp.p * 60.0
                _thresh_n = 0.95 * _n_sync
                _above    = np.where(_n_arr >= _thresh_n)[0]
                if len(_above) > 0:
                    _t_accel = float(_t_arr[int(_above[0])])
                    if _t_accel < 10.0:
                        _trip_class, _trip_fn = 10, st.success
                        _trip_msg = f"Classe 10 — partida em **{_t_accel:.2f} s** (< 10 s)"
                    elif _t_accel < 20.0:
                        _trip_class, _trip_fn = 20, st.warning
                        _trip_msg = f"Classe 20 — partida em **{_t_accel:.2f} s** (10–20 s)"
                    else:
                        _trip_class, _trip_fn = 30, st.error
                        _trip_msg = f"Classe 30 — partida em **{_t_accel:.2f} s** (> 20 s)"
                    _trip_fn(
                        f"Recomendação de Proteção: Relé de Sobrecarga Classe {_trip_class} — "
                        f"{_trip_msg}. (Referência IEC 60947-4-1 / NEMA ICS 2)"
                    )
            except Exception:
                pass

        if exp_type != "shutdown":
            st.markdown('<p class="slabel">Indicadores de Regime Permanente</p>', unsafe_allow_html=True)

            n_ss    = res["n_ss"]
            Te_ss   = res["Te_ss"]
            wr_ss   = res["wr_ss"]
            ias_rms = res["ias_rms"]
            Te_max  = float(np.max(res["Te"]))
            ias_pk  = float(np.max(np.abs(res["ias"])))

            _show_Te_max = exp_type not in ("gerador",)
            _show_ias_pk = exp_type not in ("carga", "pulso_carga")

            _row1 = [
                ("Velocidade de Regime (RPM)",       f"{n_ss:.{d}f}"),
                ("Torque de Regime $T_e$ (N·m)",     f"{Te_ss:.{d}f}"),
            ]
            if _show_Te_max:
                _row1.append(("Torque Máximo $T_{e,max}$ (N·m)", f"{Te_max:.{d}f}"))
            if _show_ias_pk:
                _row1.append(("Corrente de Pico $i_{as}$ (A)",   f"{ias_pk:.{d}f}"))
            _row1 += [
                ("Corrente RMS $i_{as}$ (A)",        f"{ias_rms:.{d}f}"),
                ("Vel. Angular $\\omega_r$ (rad/s)", f"{wr_ss:.{d}f}"),
            ]
            k = st.columns(len(_row1))
            for col, (lbl, val) in zip(k, _row1):
                col.metric(lbl, val)

            s_val   = res.get("s", 0.0)
            gerador = s_val < 0

            u_in,  v_in  = fmt_pot(res.get("P_in",  0.0), d)
            u0,    v0    = fmt_pot(abs(res.get("P_gap",  0.0)), d)
            u1,    v1    = fmt_pot(abs(res.get("P_mec",  0.0)), d)
            u2,    v2    = fmt_pot(res.get("P_cu_r", 0.0), d)
            u_out, v_out = fmt_pot(res.get("P_out", 0.0), d)

            lbl_in  = f"P. Mec. Turbina ({u_in})"   if gerador else f"P. Entrada ({u_in})"
            lbl_gap = f"P. Entreferro Gerada ({u0})" if gerador else f"P. Entreferro ({u0})"
            lbl_mec = f"P. Mec. Entrada ({u1})"      if gerador else f"P. Mecanica ({u1})"

            k2 = st.columns(6)
            if gerador:
                k2[0].metric(lbl_in,                      v_in)
                k2[1].metric(lbl_gap,                     v0)
                k2[2].metric(f"P. Gerada Rede ({u_out})", v_out)
                k2[3].metric(f"Perdas Rotor ({u2})",      v2)
            else:
                k2[0].metric(lbl_in,                      v_in)
                k2[1].metric(lbl_gap,                     v0)
                k2[2].metric(lbl_mec,                     v1)
                k2[3].metric(f"Perdas Rotor ({u2})",      v2)
            k2[4].metric("Rendimento (%)",     f"{res.get('eta', 0.0):.{d}f}")
            k2[5].metric("Escorregamento (%)", f"{s_val*100:.{d}f}")

        # resumo econômico compacto na visão geral
        if _em:
            st.write("")
            st.markdown('<p class="slabel">Resumo Econômico</p>', unsafe_allow_html=True)
            _re1, _re2, _re3 = st.columns(3)
            _re1.metric("Rendimento em Regime", f"{_em['eta_ss']:.2f} %")
            _re2.metric("Potência Entrada (regime)", f"{_em['P_in_ss_kw']:.3f} kW")
            _re3.metric("Custo Operacional Anual", f"R$ {_em['custo_ano_brl']:,.2f}")

    # ══════════════════════════════════════════════════════════════════════
    # ABA 2 — ANÁLISE DINÂMICA
    # ══════════════════════════════════════════════════════════════════════
    with tab_dinamica:
        if not var_keys:
            st.info("Nenhuma grandeza selecionada. Retorne à configuração e escolha variáveis para plotar.")
        else:
            cv1, cv2, cv3 = st.columns([1.6, 1, 1.5])
            with cv1:
                _viz_opts = ["Empilhados", "Sobrepostos"] if is_mobile else ["Empilhados", "Lado a lado", "Sobrepostos"]
                _cur_modo = st.session_state.get("plot_mode", _viz_opts[0])
                if _cur_modo not in _viz_opts:
                    st.session_state["plot_mode"] = _viz_opts[0]
                modo = st.radio("Modo de Visualização", _viz_opts, horizontal=True, key="plot_mode")
            with cv2:
                dark_plot = st.toggle("Fundo escuro", value=dark, key="plot_dark_toggle")
            with cv3:
                zoom_mode = st.radio(
                    "Zoom", ["Completo", "Partida", "Regime Permanente"],
                    horizontal=True, key="zoom_mode",
                )

            st.write("")

            tmax_data = float(res["t"][-1])
            t_ss_idx  = int(res.get("_ss_start", 0))
            t_ss      = float(res["t"][t_ss_idx]) if t_ss_idx < len(res["t"]) else tmax_data
            x_zoom    = None
            if zoom_mode == "Regime Permanente":
                x_zoom = [max(0.0, t_ss - max(0.05 * tmax_data, 0.02)), tmax_data]
            elif zoom_mode == "Partida":
                x_zoom = [0.0, min(t_ss * 1.08 + 0.01, 0.2)]

            def _apply_zoom(fig: go.Figure) -> go.Figure:
                if x_zoom is None:
                    return fig
                x0, x1 = x_zoom
                fig.update_xaxes(range=[x0, x1], autorange=False)
                groups: dict = {}
                for trace in fig.data:
                    xs = getattr(trace, "x", None)
                    ys = getattr(trace, "y", None)
                    if xs is None or ys is None:
                        continue
                    ya   = getattr(trace, "yaxis", None) or "y"
                    xs_a = np.asarray(xs, dtype=float)
                    ys_a = np.asarray(ys, dtype=float)
                    mask = (xs_a >= x0) & (xs_a <= x1) & np.isfinite(ys_a)
                    if not mask.any():
                        continue
                    groups.setdefault(ya, []).append(ys_a[mask])
                for ya, arrays in groups.items():
                    all_y      = np.concatenate(arrays)
                    ymin, ymax = float(all_y.min()), float(all_y.max())
                    span       = ymax - ymin
                    pad        = span * 0.15 if span > 0 else (abs(ymax) * 0.10 if ymax != 0 else 0.1)
                    axis_key   = "yaxis" if ya == "y" else f"yaxis{ya[1:]}"
                    ax = getattr(fig.layout, axis_key, None)
                    if ax is not None:
                        ax.range     = [ymin - pad, ymax + pad]
                        ax.autorange = False
                return fig

            # recriar fig_pdf com dark_plot atualizado pelo toggle
            fig_pdf = build_fig_stacked(res, var_keys, var_labels_plot, dark_plot, t_events, d)

            if modo == "Empilhados":
                for i, fig_single in enumerate(build_fig_sidebyside(
                        res, var_keys, var_labels_plot, dark_plot, t_events, d,
                        ref_list=chart_ref_list, primary_color=primary_color,
                        compact=is_mobile)):
                    _render_plotly(_apply_zoom(fig_single), div_id=f"ems-emp-{i}")
            elif modo == "Lado a lado":
                figs   = build_fig_sidebyside(
                    res, var_keys, var_labels_plot, dark_plot, t_events, d,
                    ref_list=chart_ref_list, primary_color=primary_color,
                    compact=is_mobile)
                n_cols = min(len(figs), 3)
                rows   = [figs[i:i+n_cols] for i in range(0, len(figs), n_cols)]
                for ri, row in enumerate(rows):
                    cols = st.columns(len(row), gap="small")
                    for ci, (col, fig) in enumerate(zip(cols, row)):
                        with col:
                            _render_plotly(_apply_zoom(fig), div_id=f"ems-side-{ri}-{ci}")
            else:
                fig_overlay = build_fig_overlay(
                    res, var_keys, var_labels_plot, dark_plot, t_events, d,
                    ref_list=chart_ref_list, primary_color=primary_color,
                    compact=is_mobile)
                _render_plotly(_apply_zoom(fig_overlay), div_id="ems-overlay")

            # Conjugado vs. Velocidade
            st.write("")
            st.markdown('<p class="slabel">Conjugado vs. Velocidade</p>', unsafe_allow_html=True)
            _P_mec_ss = float(res.get("P_mec", 0.0))
            _P_nom_kw = max(_P_mec_ss / 1000.0, 0.5)
            _fig_ts = build_fig_torque_speed(
                res=res,
                P_nom_kw=_P_nom_kw,
                f=mp.f,
                p=mp.p,
                dark=dark_plot,
            )
            st.plotly_chart(_fig_ts, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    # ABA 3 — DIAGNÓSTICO E FALHAS
    # ══════════════════════════════════════════════════════════════════════
    with tab_diag:
        _ac_keys = [k for k in var_keys if k in ("ias", "ibs", "ics", "iar", "ibr", "icr")]
        if _ac_keys:
            st.markdown('<p class="slabel">Assinatura de Corrente (FFT)</p>', unsafe_allow_html=True)
            _fft_var = st.selectbox(
                "Variável para análise espectral",
                options=_ac_keys,
                format_func=lambda k: next((l for kk, l in zip(var_keys, var_labels) if kk == k), k),
                key="fft_var_select_results",
            )
            _fft_lbl = _strip_latex(
                next((l for kk, l in zip(var_keys, var_labels) if kk == _fft_var), _fft_var)
            )
            _dp = st.session_state.get("plot_dark_toggle", dark)
            fig_fft = build_fig_fft(res, _dp, key=_fft_var, label=_fft_lbl)

            _alpha = float(res.get("_broken_bar_severity", 0.0))
            if _alpha > 0:
                _s_val  = float(res.get("s", 0.0))
                _f_fund = mp.f
                _sb_lo  = _f_fund * (1.0 - 2.0 * abs(_s_val))
                _sb_hi  = _f_fund * (1.0 + 2.0 * abs(_s_val))
                for _freq, _lbl_sb in [(_sb_lo, f"(1−2s)f={_sb_lo:.1f}Hz"), (_sb_hi, f"(1+2s)f={_sb_hi:.1f}Hz")]:
                    fig_fft.add_vline(
                        x=_freq, line_dash="dash", line_color="#f59e0b", line_width=1.5,
                        annotation_text=_lbl_sb,
                        annotation_font_color="#f59e0b",
                        annotation_font_size=9,
                    )
                st.caption(
                    f"⚠ Barra quebrada ativa (α={_alpha:.2f}) — "
                    f"componentes laterais em **(1±2s)f**: "
                    f"{_sb_lo:.1f} Hz e {_sb_hi:.1f} Hz (s={_s_val*100:.2f}%)."
                )
            else:
                st.caption("Linhas vermelhas tracejadas: harmônicas ímpares (1ª, 3ª, 5ª, 7ª, 9ª).")
            _render_plotly(fig_fft, div_id="ems-fft-results")
        else:
            st.info("Selecione correntes de fase (ias, ibs, ics...) na configuração para habilitar a análise espectral.")

        # Qualidade de Energia
        if _em:
            _thd = _em.get("thd_pct", 0.0)
            _fp  = _em.get("fp", 0.0)
            if _thd > 0 or _fp > 0:
                st.divider()
                st.markdown('<p class="slabel">Qualidade de Energia</p>', unsafe_allow_html=True)
                _qe1, _qe2 = st.columns(2)
                _qe1.metric("Fator de Potência (FP)", f"{_fp:.3f}")
                _qe2.metric("THD de Corrente $i_{{as}}$", f"{_thd:.2f} %")

                _sat_active = float(res.get("_broken_bar_severity", 0.0)) > 0 or getattr(mp, "sat_enable", False)
                if _thd > 5.0:
                    if _sat_active:
                        st.warning(
                            f"THD elevado ({_thd:.1f}%) — provável contribuição da **saturação magnética**. "
                            f"Considere filtro passivo ou ativo."
                        )
                    else:
                        st.warning(
                            f"THD de corrente acima de 5% ({_thd:.1f}%). "
                            f"Verifique distorções na tensão de alimentação ou carga não-linear."
                        )
                else:
                    st.info("THD dentro do limite recomendado pela IEEE 519 (< 5%).")

                if _fp < 0.85:
                    st.warning(
                        f"Fator de Potência baixo ({_fp:.3f} < 0,85). "
                        f"Considere banco de capacitores para correção."
                    )
                st.caption(
                    "THD calculado via FFT de $i_{{as}}$ na janela de regime permanente. "
                    "FP = P_in / S_aparente, onde S = 3 × Va_rms × Ias_rms."
                )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 4 — GESTÃO DE ATIVOS (ROI / TÉRMICA)
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativos:
        if _em:
            st.markdown('<p class="slabel">Análise Econômica (IAS Energy Conservation)</p>', unsafe_allow_html=True)
            _ec1, _ec2, _ec3 = st.columns(3)
            _ec1.metric("Energia no Experimento",    f"{_em['E_total_kwh']:.5f} kWh")
            _ec2.metric("Custo do Experimento",      f"R$ {_em['custo_exp_brl']:.4f}")
            _ec3.metric("Potência Entrada (regime)", f"{_em['P_in_ss_kw']:.3f} kW")

            _ec4, _ec5, _ec6 = st.columns(3)
            _ec4.metric("Rendimento em Regime",    f"{_em['eta_ss']:.2f} %")
            _ec5.metric("Custo Operacional Anual", f"R$ {_em['custo_ano_brl']:,.2f}")
            _ec6.metric("Energia Anual Projetada", f"{_em['P_in_ss_kw'] * _em['horas_op_ano']:,.1f} kWh/ano")

            st.caption(
                f"Projeção anual baseada em operação contínua (8.760 h/ano) à tarifa de "
                f"R$ {energy_tariff:.2f}/kWh."
            )
        else:
            st.info("Análise econômica não disponível para o experimento de desligamento.")

        # Análise Térmica
        _temp_arr = res.get("Temp")
        if _temp_arr is not None and len(_temp_arr) > 0:
            _T_arr = np.asarray(_temp_arr, dtype=float)
            _T_max = float(np.nanmax(_T_arr))
            _T_fin = float(_T_arr[-1]) if np.isfinite(_T_arr[-1]) else _T_max
            _T_amb = float(getattr(mp, "T_amb", 25.0))

            st.divider()
            st.markdown('<p class="slabel">Análise Térmica (IEC 60085)</p>', unsafe_allow_html=True)

            _tc1, _tc2, _tc3 = st.columns(3)
            _tc1.metric("Temperatura Máxima",      f"{_T_max:.1f} °C")
            _tc2.metric("Temperatura Final",        f"{_T_fin:.1f} °C")
            _tc3.metric("Elevação de Temperatura",  f"{_T_max - _T_amb:.1f} °C acima de T_amb")

            if _T_max > 180.0:
                st.error(
                    f"⚠ SOBREAQUECIMENTO CRÍTICO: T_max = {_T_max:.1f}°C excede a Classe H "
                    f"(180°C). Risco iminente de queima do isolamento (IEC 60085)."
                )
            elif _T_max > 155.0:
                st.error(
                    f"⚠ Sobreaquecimento: T_max = {_T_max:.1f}°C excede o limite da Classe F "
                    f"(155°C — IEC 60085). Risco de degradação prematura do isolamento."
                )
            elif _T_max > 130.0:
                st.warning(
                    f"T_max = {_T_max:.1f}°C excede a Classe B (130°C). "
                    f"Verifique se o motor é de Classe F ou superior."
                )
            else:
                st.success(f"Temperatura dentro do limite da Classe B/F ({_T_max:.1f}°C ≤ 130°C).")

            with st.expander("Ver curva de temperatura", expanded=True):
                import plotly.graph_objects as _go_th
                _t_arr_plot = np.asarray(res["t"], dtype=float)
                _fig_th = _go_th.Figure()
                _fig_th.add_trace(_go_th.Scatter(
                    x=_t_arr_plot, y=_T_arr, mode="lines", name="Temperatura (°C)",
                    line=dict(color="#ef4444", width=2),
                ))
                for _cls_n, _cls_lim in [("Classe B", 130), ("Classe F", 155), ("Classe H", 180)]:
                    _fig_th.add_hline(
                        y=_cls_lim, line_dash="dot", line_color="#94a3b8", line_width=1,
                        annotation_text=_cls_n, annotation_position="bottom right",
                        annotation_font_size=9,
                    )
                _fig_th.add_hline(
                    y=_T_amb, line_dash="dash", line_color="#64748b", line_width=1,
                    annotation_text=f"T_amb={_T_amb:.0f}°C", annotation_position="bottom right",
                    annotation_font_size=9,
                )
                _fig_th.update_layout(
                    xaxis_title="Tempo (s)", yaxis_title="Temperatura (°C)",
                    height=320,
                    margin=dict(l=50, r=20, t=20, b=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(249,250,252,1)",
                )
                st.plotly_chart(_fig_th, use_container_width=True, config=_PLOT_CFG,
                                key="ems-thermal-plot")
                st.caption(
                    f"Modelo de 1ª ordem: τ = R_th·C_th = "
                    f"{getattr(mp,'Rth',1.5)*getattr(mp,'Cth',200.0):.0f} s. "
                    f"Limites IEC 60085: Classe B=130°C, F=155°C, H=180°C."
                )

    # ══════════════════════════════════════════════════════════════════════
    # PAINEL DE REFERÊNCIAS + EXPORTAÇÃO PDF  (fora das abas)
    # ══════════════════════════════════════════════════════════════════════
    st.write("")
    st.divider()
    st.markdown('<p class="slabel">Exportar</p>', unsafe_allow_html=True)
    if st.button("Gerar Relatório Técnico (PDF)", key="btn_pdf"):
        with st.spinner("Gerando PDF..."):
            st.session_state["pdf_bytes"] = generate_pdf_report(
                exp_label, mp, res, fig_pdf,
                var_keys, var_labels, t_events,
                exp_type=exp_type,
                ref_list=ref_list,
                energy_tariff=energy_tariff,
            )
    if st.session_state.get("pdf_bytes"):
        st.download_button(
            label="Baixar Relatório PDF",
            data=st.session_state["pdf_bytes"],
            file_name="relatorio_ems.pdf",
            mime="application/pdf",
            key="btn_pdf_download",
        )
