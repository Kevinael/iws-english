# -*- coding: utf-8 -*-
"""Renderização de resultados da simulação: KPIs, gráficos e exportação PDF.

Exporta:
    render_results   — KPIs + gráficos Plotly + botão de exportação PDF
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.IWS_PY import MachineParams
from core.energy_analysis import compute_energy_metrics
from viz.plotly_charts import (
    build_fig_stacked, build_fig_sidebyside, build_fig_overlay, build_fig_torque_speed,
)
from viz.pdf_academico import generate_academico
from viz.pdf_industrial import generate_industrial
from core.harmonica_analysis import build_fig_fft
from core.sim_diagnostics import generate_insights
from utils.text_utils import _strip_latex
from ui.theme import REF_COLORS, REF_DASHES


@st.cache_data(show_spinner=False)
def _cached_energy_metrics(res: dict, tariff: float) -> dict:
    return compute_energy_metrics(res, tariff)


@st.cache_data(show_spinner=False)
def _cached_fig_fft(res: dict, dark: bool, key: str, label: str, _cache_key: int = 0) -> go.Figure:
    return build_fig_fft(res, dark, key=key, label=label)


@st.cache_data(show_spinner=False)
def _cached_fig_stacked(
    res: dict,
    var_keys: tuple,
    var_labels: tuple,
    dark: bool,
    t_events: tuple,
    decimals: int,
    _cache_key: int = 0,  # hash externo para invalidar cache quando res muda
) -> go.Figure:
    return build_fig_stacked(res, list(var_keys), list(var_labels), dark, list(t_events), decimals)


@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed(
    P_nom_kw: float, f: float, p: int, dark: bool, _cache_key: int = 0,
    *, res: dict | None = None,
) -> go.Figure:
    return build_fig_torque_speed(res=res, P_nom_kw=P_nom_kw, f=f, p=p, dark=dark)


_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "grafico_simulador",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
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
    ias_pk   = res.get("ias_pk",  float(np.max(np.abs(res["ias"]))))
    Te_max   = res.get("Te_max",  float(np.max(res["Te"])))
    n_ss     = res["n_ss"]
    ias_rms  = res["ias_rms"]
    s_val    = res.get("s", 0.0)
    fator_pk = res.get("fator_pk", ias_pk / ias_rms if ias_rms > 0 else 0.0)

    # DOL com partida em vazio: exibe KPIs de afundamento de velocidade ao aplicar carga
    _dol_em_vazio = exp_type == "dol" and bool(t_events)

    if _dol_em_vazio:
        _tevs_c    = t_events or []
        t_carga_ev = _tevs_c[0] if _tevs_c else 0.0
        idx_tc     = max(int(np.searchsorted(res["t"], t_carga_ev)), 1)
        _w         = max(1, idx_tc // 5)          # últimos 20% do trecho pré-carga
        n_antes    = float(np.mean(res["n"][idx_tc - _w:idx_tc]))
        delta_n    = n_antes - n_ss
        delta_i    = abs(ias_rms - float(np.sqrt(np.mean(res["ias"][idx_tc - _w:idx_tc]**2))))
        lbl_delta  = "Afundamento de Velocidade" if delta_n >= 0 else "Elevação de Velocidade"
        items = [
            ("Corrente de Pico $i_{as}$",        f"{ias_pk:.{d}f}",       "A"),
            ("Torque Máximo $T_{e,max}$",         f"{Te_max:.{d}f}",       "N·m"),
            ("Velocidade Antes da Carga",         f"{n_antes:.{d}f}",      "RPM"),
            ("Velocidade após Aplicação da Carga", f"{n_ss:.{d}f}",        "RPM"),
            (lbl_delta,                           f"{abs(delta_n):.{d}f}", "RPM"),
            ("Variação de Corrente RMS",          f"{delta_i:.{d}f}",      "A"),
        ]

    elif exp_type in ("dol", "yd", "comp", "soft"):
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
            items.insert(1, ("Corrente de Pico Pós-Comutação Y→D", f"{ias_pk2:.{d}f}", "A"))
        elif exp_type == "comp":
            _tevs      = t_events or []
            t_ev_comp  = _tevs[0] if _tevs else 0.0
            idx_comp   = int(np.searchsorted(res["t"], t_ev_comp))
            ias_pk2_comp = float(np.max(np.abs(res["ias"][idx_comp:]))) if idx_comp < len(res["t"]) else 0.0
            items.insert(1, ("Corrente de Pico Pós-Comutação AT", f"{ias_pk2_comp:.{d}f}", "A"))

    elif exp_type == "gerador":
        P_out = res.get("P_out", 0.0)
        eta   = res.get("eta",   0.0)
        lbl_p = "kW" if abs(P_out) >= 1000 else "W"
        val_p = P_out / 1000 if abs(P_out) >= 1000 else P_out
        items = [
            ("Potência Gerada para a Rede", f"{val_p:.{d}f}",        lbl_p),
            ("Escorregamento",              f"{s_val*100:.{d}f}",    "%"),
            ("Rendimento",                  f"{eta:.{d}f}",          "%"),
            ("Corrente RMS de Geração",     f"{ias_rms:.{d}f}",      "A"),
        ]

    elif exp_type == "voltage_sag":
        _tevs  = t_events or []
        # t_end do sag é o último evento registrado (t_sag, t_end)
        # t_events = sorted [tc?, t_sag, t_end] — sag always last two entries
        t_sag_start = _tevs[-2] if len(_tevs) >= 2 else (_tevs[0] if _tevs else 0.0)
        t_sag_end   = _tevs[-1] if len(_tevs) >= 1 else (t_sag_start + 0.1)
        t_arr       = np.asarray(res["t"])
        idx_sag     = int(np.searchsorted(t_arr, t_sag_start))
        idx_rec     = int(np.searchsorted(t_arr, t_sag_end))

        # profundidade do afundamento: tensão de linha durante o sag
        Vqs_sag = np.asarray(res["Vqs"])
        Vds_sag = np.asarray(res["Vds"])
        _idx_pre = max(1, idx_sag)
        Va_pre   = float(np.sqrt(np.mean(Vqs_sag[:_idx_pre]**2 + Vds_sag[:_idx_pre]**2)))
        Va_pre   = Va_pre if Va_pre > 0 else 1.0
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
        _win_sz = max(1, idx_cut // 20)
        w0      = max(0, idx_cut - _win_sz)
        n_pre   = float(np.mean(res["n"][w0:idx_cut])) if idx_cut > 0 else 0.0
        n_final = float(np.mean(res["n"][-max(1, len(res["n"]) // 10):]))
        thresh  = 0.01 * n_pre if n_pre > 0 else 1.0
        _n_abs   = np.abs(np.asarray(res["n"][idx_cut:]))
        _below   = np.where(_n_abs <= thresh)[0]
        stop_idx = int(_below[0]) if len(_below) > 0 else len(_n_abs) - 1
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
            if st.button("x", key=f"ref_del_{_i}", help="Remover esta referência"):
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
    exp_config: dict | None = None,
    torque_fn=None,
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
        st.plotly_chart(fig, width="stretch", config=_PLOT_CFG, key=div_id)

    # ── preparar fig PDF e zoom antes das abas (usados em múltiplas abas) ─
    var_labels_plot = [_strip_latex(lbl) for lbl in var_labels]

    # Pré-calcular TL(t) para sobrepor no subplot de Te
    _tl_arr = None
    if "Te" in var_keys and torque_fn is not None:
        try:
            if "TL" not in res:
                res["TL"] = np.fromiter((torque_fn(t) for t in res["t"]), dtype=float, count=len(res["t"]))
            _tl_arr = res["TL"]
        except Exception:
            pass
    _var_keys_plot   = list(var_keys)
    _var_labels_plot = list(var_labels_plot)

    # dark_plot: prefer session_state toggle se já existir, senão usa dark do tema
    dark_plot = st.session_state.get("plot_dark_toggle", dark)

    _res_hash = int(hash((res["Te"][-1], res["Te"].std(), res["t"][-1], res.get("_broken_bar_severity", 0))))
    fig_pdf = _cached_fig_stacked(res, tuple(var_keys), tuple(var_labels_plot), dark_plot, tuple(t_events), d, _cache_key=_res_hash)

    # Troca de experimento: descarta zoom_mode persistido para que o radio
    # respeite o `index` calculado dentro de _render_dinamica.
    if st.session_state.get("_last_exp_for_zoom") != exp_type:
        st.session_state.pop("zoom_mode", None)
        st.session_state["_last_exp_for_zoom"] = exp_type

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
    _em = _cached_energy_metrics(res, energy_tariff) if exp_type != "shutdown" else {}

    # ══════════════════════════════════════════════════════════════════════
    # ABAS DE RESULTADOS
    # ══════════════════════════════════════════════════════════════════════
    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs(
        ["Visão Geral", "Análise Dinâmica", "Diagnóstico e Falhas", "Gestão de Ativos"],
        key="results_tabs",
    )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 1 — VISÃO GERAL
    # ══════════════════════════════════════════════════════════════════════
    with tab_visao:
        # ── BLOCO 1: Painel de Saúde ─────────────────────────────────────────
        _load_torque = float((exp_config or {}).get("Tl_final", 0.0))
        _tmax_val    = float(res["t"][-1])
        _insights = generate_insights(res, mp, _load_torque, _tmax_val, exp_type=exp_type, exp_config=exp_config)
        _n_critico  = sum(1 for i in _insights if i.level == "error")
        _n_alerta   = sum(1 for i in _insights if i.level == "warning")
        _eta_val    = res.get("eta", 0.0)
        _s_pct      = res.get("s", 0.0) * 100.0
        _n_ss_disp  = res["n_ss"]

        if _n_critico > 0:
            _saude_cor, _saude_ico, _saude_txt = "#dc3545", "🔴", "Anomalia Detectada"
            _saude_fn = st.error
        elif _n_alerta > 0:
            _saude_cor, _saude_ico, _saude_txt = "#fd7e14", "🟡", "Atenção"
            _saude_fn = st.warning
        else:
            _saude_cor, _saude_ico, _saude_txt = "#198754", "🟢", "Operação Normal"
            _saude_fn = st.success

        _diag_suffix = ""
        if _n_critico or _n_alerta:
            _diag_suffix = f" — {_n_critico} crítico(s), {_n_alerta} alerta(s). Ver aba **Diagnóstico e Falhas**."

        if exp_type != "shutdown":
            _saude_fn(
                f"{_saude_ico} **{_saude_txt}** — "
                f"Escorregamento: **{_s_pct:.2f}%** | "
                f"Rendimento: **{_eta_val:.1f}%** | "
                f"Velocidade: **{_n_ss_disp:.0f} RPM**"
                + _diag_suffix
            )
        else:
            _saude_fn(f"{_saude_ico} **{_saude_txt}**" + _diag_suffix)

        st.write("")

        # ── BLOCO 2: Grandezas de Operação (regime, sem duplicatas) ──────────
        if exp_type != "shutdown":
            st.markdown('<p class="slabel">Grandezas de Operação</p>', unsafe_allow_html=True)

            n_ss    = res["n_ss"]
            Te_ss   = res["Te_ss"]
            wr_ss   = res["wr_ss"]
            ias_rms = res["ias_rms"]
            s_val   = res.get("s", 0.0)
            gerador = s_val < 0

            u_in,  v_in  = fmt_pot(res.get("P_in",  0.0), d)
            u0,    v0    = fmt_pot(abs(res.get("P_gap",  0.0)), d)
            u1,    v1    = fmt_pot(abs(res.get("P_mec",  0.0)), d)
            u2,    v2    = fmt_pot(res.get("P_cu_r", 0.0), d)
            u_out, v_out = fmt_pot(res.get("P_out", 0.0), d)

            lbl_in  = f"P. Mec. Turbina ({u_in})"   if gerador else f"P. Entrada ({u_in})"
            lbl_gap = f"P. Entreferro Gerada ({u0})" if gerador else f"P. Entreferro ({u0})"
            lbl_mec = f"P. Mec. Entrada ({u1})"      if gerador else f"P. Mecânica ({u1})"

            # Linha 1 — velocidade, torque, corrente RMS
            _op1 = st.columns(3)
            _op1[0].metric("Velocidade (RPM)",          f"{n_ss:.{d}f}")
            _op1[1].metric("Torque de Regime $T_e$ (N·m)", f"{Te_ss:.{d}f}")
            _op1[2].metric("Corrente RMS $i_{as}$ (A)", f"{ias_rms:.{d}f}")

            # Linha 2 — potência útil, rendimento, escorregamento
            _op2 = st.columns(3)
            if gerador:
                _op2[0].metric(f"P. Gerada Rede ({u_out})", v_out)
            else:
                _op2[0].metric(lbl_mec, v1)
            _op2[1].metric("Rendimento (%)",     f"{res.get('eta', 0.0):.{d}f}")
            _op2[2].metric("Escorregamento (%)", f"{s_val * 100:.{d}f}")

            # Linha 3 — fluxo de potência (entrada → entreferro → perdas rotor)
            _op3 = st.columns(3)
            _op3[0].metric(lbl_in,                f"{v_in}")
            _op3[1].metric(lbl_gap,               f"{v0}")
            _op3[2].metric(f"Perdas Rotor ({u2})", v2)

        # ── BLOCO 3: Transiente de Partida (colapsável) ───────────────────────
        destaques = _kpis_destaque(res, exp_type, mp, d, t_events)
        _prot_items_exist = exp_type in ("dol", "yd", "comp", "soft", "voltage_sag")
        if destaques or _prot_items_exist:
            st.write("")
            with st.expander("Transiente de Partida e Proteção", expanded=False):
                if destaques:
                    st.markdown('<p class="slabel">Grandezas de Partida</p>', unsafe_allow_html=True)
                    _MAX_COLS = 4
                    for i in range(0, len(destaques), _MAX_COLS):
                        chunk = destaques[i:i + _MAX_COLS]
                        cols = st.columns(_MAX_COLS)
                        for col, (lbl, val, unit) in zip(cols, chunk):
                            col.metric(f"{lbl} ({unit})", val)
                    st.write("")

                if _prot_items_exist:
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

                            st.markdown('<p class="slabel">Recomendações de Proteção</p>', unsafe_allow_html=True)
                            _trip_fn(
                                f"**Relé de Sobrecarga Classe {_trip_class}** — "
                                f"{_trip_msg}. (IEC 60947-4-1 / NEMA ICS 2)"
                            )

                            _In      = getattr(mp, "In", None)
                            _Vn      = getattr(mp, "Vn", None)
                            _ias_pk  = float(np.max(np.abs(res["ias"]))) if "ias" in res else None

                            if _In is not None and _ias_pk is not None:
                                _icp_ratio = _ias_pk / _In if _In > 0 else 0.0
                                _mpcb_lo  = 0.80 * _In
                                _mpcb_hi  = 1.00 * _In
                                _mpcb_icu = _ias_pk * 1.25
                                _mpcb_fn  = st.success if _icp_ratio <= 8 else (st.warning if _icp_ratio <= 12 else st.error)
                                _mpcb_fn(
                                    f"**Disjuntor Motor (MPCB)** — ajuste térmico: "
                                    f"{_mpcb_lo:.1f}–{_mpcb_hi:.1f} A; "
                                    f"capacidade de corte ≥ **{_mpcb_icu:.0f} A** "
                                    f"(Ipico simulado × 1,25). (IEC 60947-2)"
                                )

                            if _In is not None:
                                _fus_lo = 2.0 * _In
                                _fus_hi = 2.5 * _In
                                st.info(
                                    f"**Fusível de Proteção (gG/aM)** — "
                                    f"corrente nominal recomendada: **{_fus_lo:.0f}–{_fus_hi:.0f} A** "
                                    f"(2,0–2,5 × In = {_In:.1f} A). "
                                    f"Classe aM se coordenação com MPCB. (IEC 60269-1)"
                                )
                                _cont_rup = 6.0 * _In
                                st.info(
                                    f"**Contatora AC-3** — corrente de emprego: ≥ **{_In:.1f} A**; "
                                    f"capacidade de ruptura: ≥ **{_cont_rup:.0f} A** (6 × In). "
                                    f"(IEC 60947-4-1, cat. AC-3)"
                                )

                            if _Vn is not None:
                                _vn_ll = _Vn
                                if _vn_ll <= 230:
                                    _uc, _up_max = 275, 1500
                                elif _vn_ll <= 400:
                                    _uc, _up_max = 420, 2500
                                else:
                                    _uc, _up_max = int(_vn_ll * 1.1), 4000
                                st.info(
                                    f"**DPS (Surtos) Classe II** — Uc ≥ **{_uc} V**; "
                                    f"nível de proteção Up ≤ **{_up_max} V**. "
                                    f"Instalar no quadro de comando, entre fase e terra. (IEC 61643-11)"
                                )

                            _T_max = None
                            for _k in ("T_s", "Ts", "T_stator", "theta_s", "theta_stator"):
                                if _k in res:
                                    _T_max = float(np.max(res[_k]))
                                    break
                            if _T_max is not None:
                                _class_F, _class_H = 155, 180
                                if _T_max < _class_F:
                                    _prot_fn, _prot_iso = st.success, "F (155 °C)"
                                elif _T_max < _class_H:
                                    _prot_fn, _prot_iso = st.warning, "H (180 °C)"
                                else:
                                    _prot_fn, _prot_iso = st.error, "C (> 180 °C) — revisar isolamento"
                                _prot_fn(
                                    f"**Termistor PTC / RTD** — temperatura máxima simulada: "
                                    f"**{_T_max:.1f} °C** → classe de isolamento recomendada: **{_prot_iso}**. "
                                    f"(IEC 60085 / IEC 60034-1)"
                                )

                    except Exception:
                        pass

        # ── BLOCO 4: Resumo Econômico ────────────────────────────────────────
        if _em:
            st.write("")
            st.markdown('<p class="slabel">Resumo Econômico</p>', unsafe_allow_html=True)
            _re1, _re2, _re3 = st.columns(3)
            _re1.metric("Rendimento em Regime", f"{_em['eta_ss']:.2f} %")
            _re2.metric("Potência Entrada (regime)", f"{_em['P_in_ss_kw']:.3f} kW")
            _re3.metric("Custo Operacional Anual", f"R$ {_em['custo_ano_brl']:,.2f}",
                        help=(
                            f"Estimado como: P_in_regime × 8.760 h/ano × tarifa.\n"
                            f"Suposições: operação contínua 24 h/dia, 365 dias/ano, "
                            f"na potência de regime permanente.\n"
                            f"Tarifa atual: R$ {energy_tariff:.4f}/kWh "
                            f"(configurável em Parâmetros Avançados → Análise Econômica)."
                        ))

    # ══════════════════════════════════════════════════════════════════════
    # ABA 2 — ANÁLISE DINÂMICA
    # ══════════════════════════════════════════════════════════════════════
    with tab_dinamica:
        if not var_keys:
            st.info("Nenhuma grandeza selecionada. Retorne à configuração e escolha variáveis para plotar.")
        else:
            @st.fragment
            def _render_dinamica(
                res, var_keys, var_labels_plot, dark, t_events, decimals,
                exp_type, exp_config, mp, is_mobile,
                chart_ref_list, primary_color, tl_arr, res_hash,
            ):
                _PLOT_CFG_F: dict = {
                    "responsive": True, "scrollZoom": False, "displaylogo": False,
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                    "toImageButtonOptions": {"format": "png", "filename": "grafico_simulador",
                                             "scale": 3, "height": 600, "width": 1200},
                }

                _viz_opts = ["Empilhados", "Sobrepostos"] if is_mobile else ["Empilhados", "Lado a lado", "Sobrepostos"]
                _cur_modo = st.session_state.get("plot_mode", _viz_opts[0])
                if _cur_modo not in _viz_opts:
                    st.session_state["plot_mode"] = _viz_opts[0]

                _is_pulso    = (exp_type == "pulso_carga")
                _t_pulso_on  = float((exp_config or {}).get("t_carga",    0.0))
                _t_pulso_off = float((exp_config or {}).get("t_retirada", 0.0))
                _zoom_opts   = ["Completo"]
                if _is_pulso:
                    _zoom_opts.append("Pulso de Carga")
                else:
                    _zoom_opts.append("Partida")
                _zoom_opts.append("Regime Permanente")
                _zoom_default = "Pulso de Carga" if _is_pulso else _zoom_opts[0]
                _saved_zoom   = st.session_state.get("zoom_mode", _zoom_default)
                _zoom_idx     = _zoom_opts.index(_saved_zoom) if _saved_zoom in _zoom_opts else _zoom_opts.index(_zoom_default)

                # Controles numa única linha compacta
                _cc1, _cc2, _cc3 = st.columns([2, 2, 1])
                with _cc1:
                    modo = st.radio("Visualização", _viz_opts, horizontal=True, key="plot_mode")
                with _cc2:
                    zoom_mode = st.radio(
                        "Zoom", _zoom_opts, index=_zoom_idx,
                        horizontal=True, key="zoom_mode",
                    )
                with _cc3:
                    dark_plot = st.toggle("Fundo escuro", value=dark, key="plot_dark_toggle")

                st.write("")

                tmax_data = float(res["t"][-1])
                t_ss_idx  = int(res.get("_ss_start", 0))
                t_ss      = float(res["t"][t_ss_idx]) if t_ss_idx < len(res["t"]) else tmax_data
                t_window  = None
                if zoom_mode == "Regime Permanente":
                    t_window = (max(0.0, t_ss - max(0.05 * tmax_data, 0.02)), tmax_data)
                elif zoom_mode == "Partida":
                    _cfg  = exp_config or {}
                    _pad  = 0.1  # margem fixa pós-evento
                    if exp_type == "dol":
                        # instante em que wr_mec atinge 95% da vel. síncrona mecânica
                        _ws_mec = 2.0 * np.pi * mp.f / (mp.p / 2.0)
                        _wr     = np.asarray(res["wr"], dtype=float)
                        _above  = np.where(_wr >= 0.95 * _ws_mec)[0]
                        _t_acc  = float(res["t"][int(_above[0])]) if len(_above) > 0 else t_ss
                        _tend   = _t_acc + _pad
                    elif exp_type in ("yd", "comp"):
                        # chave em t_2, carga em t_carga — mostra até depois da carga
                        _tc   = float(_cfg.get("t_carga", 0.0))
                        _t2   = float(_cfg.get("t_2", 0.0))
                        _tend = max(_tc, _t2) + _pad
                    elif exp_type == "soft":
                        # rampa termina em t_pico, carga em t_carga
                        _tp   = float(_cfg.get("t_pico", 0.0))
                        _tc   = float(_cfg.get("t_carga", 0.0))
                        _tend = max(_tp, _tc) + _pad
                    elif exp_type == "voltage_sag":
                        # mostra desde antes do sag até após a recuperação
                        _ts   = float(_cfg.get("t_start_sag", 0.0))
                        _dur  = float(_cfg.get("t_duration_sag", 0.1))
                        _tend = _ts + _dur + _pad
                    else:
                        _tend = t_ss + _pad
                    t_window = (0.0, min(_tend, tmax_data))
                elif zoom_mode == "Pulso de Carga":
                    _dur     = max(_t_pulso_off - _t_pulso_on, 0.1)
                    _pad     = max(0.2 * _dur, 0.1)
                    t_window = (max(0.0, _t_pulso_on - _pad), min(tmax_data, _t_pulso_off + _pad))

                def _y_range(keys):
                    if t_window is None:
                        return {}
                    t_arr = np.asarray(res["t"], dtype=float)
                    mask  = (t_arr >= t_window[0]) & (t_arr <= t_window[1])
                    ranges = {}
                    for key in keys:
                        if key not in res:
                            continue
                        vals = np.asarray(res[key], dtype=float)[mask]
                        if tl_arr is not None and key == "Te":
                            vals = np.concatenate([vals, np.asarray(tl_arr, dtype=float)[mask]])
                        vals = vals[np.isfinite(vals)]
                        if len(vals) == 0:
                            continue
                        ymin, ymax = float(vals.min()), float(vals.max())
                        ymid     = (ymin + ymax) / 2.0
                        min_span = max(abs(ymid) * 0.01, 0.1)
                        if (ymax - ymin) < min_span:
                            ymin, ymax = ymid - min_span / 2, ymid + min_span / 2
                        pad = (ymax - ymin) * 0.12
                        ranges[key] = (ymin - pad, ymax + pad)
                    return ranges

                def _apply_zoom(fig, keys):
                    if t_window is None:
                        return fig
                    x0, x1 = t_window
                    fig.update_xaxes(range=[x0, x1], autorange=False)
                    yr = _y_range(keys)
                    if yr:
                        ylo, yhi = next(iter(yr.values()))
                        fig.update_layout(yaxis=dict(range=[ylo, yhi], autorange=False))
                    return fig

                def _apply_zoom_overlay(fig, keys):
                    if t_window is None:
                        return fig
                    x0, x1 = t_window
                    fig.update_xaxes(range=[x0, x1], autorange=False)
                    yr         = _y_range(keys)
                    right_units = {"n", "wr"}
                    left_keys  = [k for k in keys if k not in right_units]
                    right_keys = [k for k in keys if k in right_units]
                    if left_keys and any(k in yr for k in left_keys):
                        all_v = np.concatenate([np.array(yr[k]) for k in left_keys if k in yr])
                        fig.update_layout(yaxis=dict(range=[float(all_v.min()), float(all_v.max())], autorange=False))
                    if right_keys and any(k in yr for k in right_keys):
                        all_v = np.concatenate([np.array(yr[k]) for k in right_keys if k in yr])
                        fig.update_layout(yaxis2=dict(range=[float(all_v.min()), float(all_v.max())], autorange=False))
                    return fig

                # ── notas contextuais por grandeza ───────────────────────────
                _bb_sev   = float(res.get("_broken_bar_severity", 0.0))
                _s_val    = float(res.get("s", 0.0))
                _deseq_on = any((exp_config or {}).get(k, 0) for k in
                                ("deseq_a", "deseq_b", "deseq_c", "falta_fase_a", "falta_fase_b", "falta_fase_c"))
                _is_yd    = (exp_type == "yd")
                _is_gen   = (exp_type == "gerador")
                _is_sd    = (exp_type == "shutdown")
                _is_soft  = (exp_type == "soft")
                _Tl_cfg   = float((exp_config or {}).get("Tl_final", 0.0))
                _Te_max   = float(np.max(res["Te"])) if "Te" in res else 0.0

                def _nota_apos(key: str) -> None:
                    """Emite a nota contextual adequada para a grandeza 'key', se houver."""
                    _cfg = exp_config or {}
                    if key == "Te":
                        if _bb_sev > 0:
                            _f_osc = 2.0 * abs(_s_val) * mp.f
                            st.caption(
                                f"**Barra quebrada (α={_bb_sev:.2f})** — $T_e$ oscila a {_f_osc:.1f} Hz "
                                f"($2sf$). O torque de carga $T_L$ permanece essencialmente constante: "
                                f"a inércia $J$ amorte as oscilações de velocidade, tornando $\\Delta T_L \\ll \\Delta T_e$. "
                                f"A assinatura espectral aparece na corrente como sidebands em $(1\\pm2s)f_e$ Hz — "
                                f"veja a aba **Diagnóstico e Falhas**."
                            )
                        elif _deseq_on:
                            st.caption(
                                "**Desequilíbrio de tensão / Falta de fase** — a componente de sequência negativa "
                                "estabelece campo girante em sentido oposto a $\\omega_s$, com escorregamento efetivo "
                                "$s^- = 2 - s^+$, gerando torque frenante pulsante à frequência $2f$ e reduzindo "
                                "$T_e$ médio em relação ao regime equilibrado."
                            )
                        elif _is_yd:
                            st.caption(
                                "**Partida Estrela-Triângulo (Y-$\\Delta$)** — na comutação, a tensão de fase salta "
                                "de $V_n/\\sqrt{3}$ para $V_n$, impondo um degrau de excitação sobre o fluxo residual "
                                "no entreferro. O segundo pico de $T_e$ decai com constante $\\tau_s = L_s/R_s$ até "
                                "o novo regime permanente $T_e = T_L + B\\,\\omega_r$."
                            )
                        elif exp_type == "autotrafo":
                            _k = float(_cfg.get("voltage_ratio", 0.5))
                            st.caption(
                                f"**Partida com Autotransformador (tap $k$ = {_k:.0%})** — a tensão reduzida "
                                f"$V_s = k\\,V_n$ atenua $T_e$ por um fator $k^2 = {_k**2:.2f}$, reduzindo o "
                                f"pico de inrush sem eliminar as oscilações transitórias. Na comutação para tensão "
                                f"plena ocorre um segundo transitório análogo ao do modo Y-$\\Delta$."
                            )
                        elif _is_soft:
                            if _Te_max < _Tl_cfg * 1.05 and _Tl_cfg > 0:
                                st.caption(
                                    "**Soft-starter** — o torque máximo de partida está próximo do torque de carga. "
                                    "Se $T_{e,\\max} < T_L$ o motor não parte. Considere aumentar a tensão inicial "
                                    "ou reduzir a carga durante a aceleração."
                                )
                            else:
                                st.caption(
                                    "**Soft-starter** — a rampa de tensão suaviza o crescimento de $T_e$, "
                                    "eliminando o pico de inrush da partida direta. O torque cresce de forma "
                                    "aproximadamente proporcional a $V_s^2(t)$ até atingir $T_e = T_L + B\\,\\omega_r$ "
                                    "em regime permanente."
                                )
                        elif exp_type == "pulso_carga":
                            st.caption(
                                "**Pulso de Carga** — a inserção súbita de $T_L$ provoca queda transitória de "
                                "$\\omega_r$ e aumento de escorregamento $s$. O torque eletromagnético $T_e$ "
                                "eleva-se em resposta, com oscilações amortecidas pela constante $\\tau_m = J/B$, "
                                "até igualr-se a $T_L + B\\,\\omega_r$ no novo ponto de operação."
                            )
                        elif _is_gen:
                            st.caption(
                                "**Modo Gerador** — $T_e$ negativo indica que a máquina absorve torque mecânico "
                                "e injeta potência ativa na rede (escorregamento $s < 0$, rotor acima da "
                                "velocidade síncrona $\\omega_s$). A convenção de sinal adotada é motora: "
                                "positivo = motor, negativo = gerador."
                            )
                        elif _is_sd:
                            _tau_r = mp.Lr / mp.Rr if mp.Rr > 0 else 0.0
                            st.caption(
                                f"**Desligamento** — após o corte da tensão, o fluxo no entreferro decai com "
                                f"constante $\\tau_r = L_r/R_r$ = {_tau_r:.3f} s e $T_e$ cai rapidamente a zero. "
                                f"O rotor continua girando por inércia, desacelerando sob $T_L$ e atrito viscoso $B$."
                            )
                        elif exp_type == "voltage_sag":
                            _sag = float(_cfg.get("sag_magnitude", 0.5))
                            st.caption(
                                f"**Afundamento de Tensão (Voltage Sag, $V_{{sag}}$ = {_sag:.0%}$V_n$)** — "
                                f"$T_e$ cai proporcionalmente a $V_s^2$, reduzindo-se a $\\approx {_sag**2:.0%}$ "
                                f"do valor nominal durante o distúrbio. Se $T_{{e,\\min}} < T_L$ o motor perde "
                                f"sincronismo e pode estagnar ($s \\to 1$)."
                            )
                        elif exp_type == "dol":
                            st.caption(
                                "**Partida Direta (DOL)** — na energização com $\\omega_r = 0$ e $s = 1$, "
                                "a baixa impedância do circuito impõe corrente de inrush $I_s \\approx 5$–$8\\,I_n$. "
                                "O torque $T_e$ exibe oscilações amortecidas sobrepostas à envoltória crescente, "
                                "decorrentes dos fluxos transitórios nos eixos $d$-$q$, até estabilizar em "
                                "$T_e = T_L + B\\,\\omega_r$."
                            )

                    elif key in ("ias", "ibs", "ics"):
                        if _bb_sev > 0:
                            _f_osc = 2.0 * abs(_s_val) * mp.f
                            _f_lo  = (1.0 - 2.0 * abs(_s_val)) * mp.f
                            _f_hi  = (1.0 + 2.0 * abs(_s_val)) * mp.f
                            st.caption(
                                f"**Barra quebrada (α={_bb_sev:.2f})** — a assimetria do circuito do rotor "
                                f"induz modulação de amplitude na corrente do estator, gerando sidebands "
                                f"em $(1\\pm2s)f_e$ = {_f_lo:.1f} Hz e {_f_hi:.1f} Hz visíveis no espectro MCSA "
                                f"— veja a aba **Diagnóstico e Falhas**."
                            )
                        elif _deseq_on:
                            st.caption(
                                "**Desequilíbrio de tensão / Falta de fase** — correntes de fase assimétricas "
                                "indicam circulação de componente de sequência negativa $I_2$ no estator. "
                                "A fase com menor tensão tende a apresentar maior corrente, acelerando o "
                                "envelhecimento do isolamento elétrico."
                            )
                        elif _is_yd:
                            st.caption(
                                "**Partida Estrela-Triângulo (Y-$\\Delta$)** — na fase estrela, $I_s$ é "
                                "reduzida a $1/3$ do valor DOL equivalente. Na comutação para triângulo "
                                "ocorre um segundo pico de corrente, tipicamente $1{,}5$–$2\\,I_n$, "
                                "que decai com $\\tau_s = L_s/R_s$."
                            )
                        elif exp_type == "autotrafo":
                            _k = float(_cfg.get("voltage_ratio", 0.5))
                            st.caption(
                                f"**Autotransformador (tap $k$ = {_k:.0%})** — a corrente de inrush no estator "
                                f"é reduzida por $k^2 = {_k**2:.2f}$ em relação à partida direta, pois "
                                f"$I_{{s,\\text{{inrush}}}} \\propto V_s = k\\,V_n$."
                            )
                        elif _is_soft:
                            st.caption(
                                "**Soft-starter** — a rampa de tensão elimina o pico de inrush; a corrente "
                                "cresce gradualmente de $I_s \\approx 0$ até $I_n$ no regime permanente, "
                                "reduzindo o estresse elétrico e mecânico na partida."
                            )
                        elif exp_type == "dol":
                            st.caption(
                                "**Partida Direta (DOL)** — com $s = 1$, a corrente de partida atinge "
                                "$I_{{s,0}} \\approx V_n / Z_s$, tipicamente $5$–$8\\,I_n$. "
                                "À medida que $\\omega_r$ cresce e $s$ decresce, $I_s$ reduz até $I_n$ "
                                "em regime permanente."
                            )
                        elif exp_type == "voltage_sag":
                            st.caption(
                                "**Afundamento de Tensão** — durante o sag, $I_s$ pode elevar-se "
                                "transitoriamente se o motor desacelera e o escorregamento $s$ aumenta, "
                                "comportamento típico de cargas com torque proporcional a $\\omega_r^2$."
                            )

                    elif key in ("iar", "ibr", "icr"):
                        if _bb_sev > 0:
                            st.caption(
                                f"**Barra quebrada (α={_bb_sev:.2f})** — a assimetria das correntes do rotor "
                                f"indica que uma ou mais barras apresentam resistência elevada ($R_{{barra}} \\gg R_r$). "
                                f"A distribuição não uniforme gera pulsação de $T_e$ e aquecimento localizado."
                            )
                        elif _deseq_on:
                            st.caption(
                                "**Desequilíbrio de tensão** — a componente de sequência negativa induz "
                                "corrente de rotor à frequência $(2-s)f_e$, muito maior que $sf_e$ do "
                                "regime equilibrado, elevando as perdas Joule no rotor."
                            )

                    elif key in ("Va", "Vb", "Vc"):
                        if exp_type == "voltage_sag":
                            _sag = float(_cfg.get("sag_magnitude", 0.5))
                            _t0  = float(_cfg.get("t_start_sag", 0.5))
                            _dt  = float(_cfg.get("t_duration_sag", 0.1))
                            st.caption(
                                f"**Afundamento de Tensão** — tensão reduzida a {_sag:.0%}$V_n$ durante "
                                f"$\\Delta t_{{sag}}$ = {_dt:.3f} s (de $t$ = {_t0:.3f} s a "
                                f"$t$ = {_t0+_dt:.3f} s). A recuperação brusca após o sag pode gerar "
                                f"transitório de re-excitação no fluxo do estator."
                            )
                        elif _deseq_on:
                            _falta = any(_cfg.get(k, 0) for k in ("falta_fase_a", "falta_fase_b", "falta_fase_c"))
                            if _falta:
                                st.caption(
                                    "**Falta de fase** — a tensão da fase aberta cai a zero nos terminais; "
                                    "as fases remanescentes mantêm amplitude nominal, impondo tensão de "
                                    "sequência negativa $V_2 \\neq 0$ ao estator."
                                )
                            else:
                                st.caption(
                                    "**Desequilíbrio de tensão** — amplitudes de fase desiguais indicam "
                                    "assimetria na alimentação. A decomposição em componentes simétricas "
                                    "revela $V_2/V_1$ proporcional ao grau de desequilíbrio."
                                )

                    elif key in ("n", "wr"):
                        _lbl_v = "$\\omega_r$" if key == "wr" else "$n$"
                        _lbl_u = "rad/s" if key == "wr" else "rpm"
                        if _is_gen:
                            st.caption(
                                f"**Modo Gerador** — {_lbl_v} acima da velocidade síncrona corresponde a "
                                f"$s < 0$. A máquina opera como gerador de indução, injetando potência ativa "
                                f"na rede sem excitação independente (requer reativo da rede para magnetização)."
                            )
                        elif _is_sd:
                            _ws    = 2.0 * np.pi * mp.f / (mp.p / 2.0)
                            _t_cut = float(_cfg.get("t_cutoff", 0.0))
                            import math as _math
                            if mp.B > 0 and _Tl_cfg > 0:
                                _t_stop = _math.log(1.0 + mp.B * _ws / _Tl_cfg) * mp.J / mp.B
                            elif _Tl_cfg > 0:
                                _t_stop = mp.J * _ws / _Tl_cfg
                            else:
                                _t_stop = mp.J / mp.B if mp.B > 0 else 0.0
                            st.caption(
                                f"**Desligamento** — após $t_{{des}}$ = {_t_cut:.2f} s a tensão é cortada e "
                                f"o motor desacelera livremente. Tempo estimado de parada: **{_t_stop:.2f} s** "
                                f"($J/B \\cdot \\ln(1 + B\\omega_s/T_L)$)."
                            )
                        elif exp_type == "voltage_sag":
                            st.caption(
                                f"**Afundamento de Tensão** — a queda de $T_e \\propto V_s^2$ durante o sag "
                                f"provoca desaceleração transitória de {_lbl_v}. Se a margem de "
                                f"escorregamento for suficiente, o motor recupera a velocidade nominal "
                                f"após o restabelecimento da tensão; caso contrário, estagna ($s \\to 1$)."
                            )
                        elif exp_type == "pulso_carga":
                            st.caption(
                                f"**Pulso de Carga** — a inserção súbita de $T_L$ causa queda transitória "
                                f"de {_lbl_v}, aumentando $s$ e, consequentemente, $T_e$. O sistema "
                                f"amortece e converge para o novo ponto de equilíbrio com constante "
                                f"de tempo mecânica $\\tau_m \\approx J/B$."
                            )
                        elif _is_yd:
                            st.caption(
                                f"**Partida Estrela-Triângulo (Y-$\\Delta$)** — {_lbl_v} cresce monotonicamente "
                                f"durante a fase estrela. Na comutação, o transitório de $T_e$ provoca "
                                f"uma perturbação visível antes da estabilização em regime permanente."
                            )
                        elif exp_type == "autotrafo":
                            st.caption(
                                f"**Autotransformador** — a aceleração sob tensão reduzida é mais lenta que "
                                f"na DOL (torque proporcional a $k^2$). Na comutação para tensão plena, "
                                f"{_lbl_v} exibe perturbação transitória antes de atingir o regime."
                            )
                        elif _is_soft:
                            st.caption(
                                f"**Soft-starter** — {_lbl_v} cresce suavemente com o aumento progressivo "
                                f"de $V_s(t)$, sem o choque mecânico da partida direta. A aceleração "
                                f"é monotônica, limitada pelo perfil de rampa configurado."
                            )
                        elif exp_type == "dol":
                            _ws_rpm = 60.0 * mp.f / (mp.p / 2.0)
                            st.caption(
                                f"**Partida Direta (DOL)** — {_lbl_v} parte de zero e acelera até "
                                f"$\\approx (1-s_{{nom}})\\,\\omega_s$ ({_ws_rpm*(1-abs(_s_val)):.0f} {_lbl_u}). "
                                f"A aceleração é determinada pelo excesso de torque $T_e - T_L$ dividido "
                                f"pelo momento de inércia $J$."
                            )

                if modo == "Empilhados":
                    for i, (fig_single, key) in enumerate(zip(
                            build_fig_sidebyside(
                                res, var_keys, var_labels_plot, dark_plot, t_events, decimals,
                                ref_list=chart_ref_list, primary_color=primary_color,
                                compact=is_mobile, tl_arr=tl_arr),
                            var_keys)):
                        st.plotly_chart(_apply_zoom(fig_single, [key]),
                                        width="stretch", config=_PLOT_CFG_F, key=f"ems-emp-{i}")
                        _nota_apos(key)
                elif modo == "Lado a lado":
                    figs   = build_fig_sidebyside(
                        res, var_keys, var_labels_plot, dark_plot, t_events, decimals,
                        ref_list=chart_ref_list, primary_color=primary_color,
                        compact=is_mobile, tl_arr=tl_arr)
                    n_cols = min(len(figs), 3)
                    rows   = [list(zip(figs, var_keys))[i:i+n_cols] for i in range(0, len(figs), n_cols)]
                    for ri, row in enumerate(rows):
                        cols = st.columns(len(row), gap="small")
                        for ci, (col, (fig, key)) in enumerate(zip(cols, row)):
                            with col:
                                st.plotly_chart(_apply_zoom(fig, [key]),
                                                width="stretch", config=_PLOT_CFG_F,
                                                key=f"ems-side-{ri}-{ci}")
                                _nota_apos(key)
                else:
                    # overlay: uma única figura — exibe notas de todas as grandezas plotadas
                    fig_overlay = build_fig_overlay(
                        res, var_keys, var_labels_plot, dark_plot, t_events, decimals,
                        ref_list=chart_ref_list, primary_color=primary_color,
                        compact=is_mobile, tl_arr=tl_arr)
                    st.plotly_chart(_apply_zoom_overlay(fig_overlay, var_keys),
                                    width="stretch", config=_PLOT_CFG_F, key="ems-overlay")
                    for key in var_keys:
                        _nota_apos(key)

                # Conjugado vs. Velocidade (colapsável — análise secundária)
                with st.expander("Conjugado × Velocidade", expanded=False):
                    _P_mec_ss = float(res.get("P_mec", 0.0))
                    _fig_ts = _cached_fig_torque_speed(
                        P_nom_kw=max(_P_mec_ss / 1000.0, 0.5),
                        f=mp.f, p=mp.p, dark=dark_plot,
                        _cache_key=res_hash, res=res,
                    )
                    st.plotly_chart(_fig_ts, width="stretch")

            _render_dinamica(
                res=res,
                var_keys=_var_keys_plot,
                var_labels_plot=_var_labels_plot,
                dark=dark,
                t_events=t_events,
                decimals=d,
                exp_type=exp_type,
                exp_config=exp_config,
                mp=mp,
                is_mobile=is_mobile,
                chart_ref_list=chart_ref_list,
                primary_color=primary_color,
                tl_arr=_tl_arr,
                res_hash=_res_hash,
            )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 3 — DIAGNÓSTICO E FALHAS
    # ══════════════════════════════════════════════════════════════════════
    with tab_diag:
        # ── BLOCO 1: Banner de diagnóstico ───────────────────────────────────
        if _n_critico > 0:
            _diag_banner_fn = st.error
            _diag_banner_ico = "🔴"
        elif _n_alerta > 0:
            _diag_banner_fn = st.warning
            _diag_banner_ico = "🟡"
        else:
            _diag_banner_fn = st.success
            _diag_banner_ico = "🟢"

        _total_insights = len(_insights)
        _n_info = _total_insights - _n_critico - _n_alerta
        _diag_banner_fn(
            f"{_diag_banner_ico} **{_total_insights} insight(s)** — "
            f"{_n_critico} crítico(s) · {_n_alerta} alerta(s) · {_n_info} informativo(s)"
        )

        # ── BLOCO 2: Insights (cards diretos, sem expander) ──────────────────
        if not _insights:
            st.info(
                "Nenhum insight disponível para este tipo de experimento "
                "ou os dados de regime permanente não foram detectados."
            )
        else:
            _ICONS = {"info": "ℹ️", "warning": "⚠️", "error": "🔴"}
            _level_fn = {"info": st.info, "warning": st.warning, "error": st.error}
            for _ins in _insights:
                _fn   = _level_fn.get(_ins.level, st.info)
                _icon = _ICONS.get(_ins.level, "")
                _fn(f"**{_icon} {_ins.title}**\n\n{_ins.body}")

        # ── BLOCO 3: Qualidade de Energia (expander) ─────────────────────────
        if _em:
            _thd = _em.get("thd_pct", 0.0)
            _fp  = _em.get("fp", 0.0)
            if _thd > 0 or _fp > 0:
                with st.expander("Qualidade de Energia", expanded=False):
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
                        _Te_ss  = float(res.get("Te_ss",  res.get("Te",  [0])[-1]))
                        _T_nom  = float(getattr(mp, "T_nom", 0) or 0)
                        _fator_carga = (_Te_ss / _T_nom) if _T_nom > 0 else None
                        if _fator_carga is not None and _fator_carga < 0.5:
                            _causa = (
                                f"**Causa provável: motor operando em subcarga** "
                                f"(torque no eixo ≈ {_Te_ss:.1f} N·m = {_fator_carga*100:.0f}% do nominal). "
                                f"A corrente de magnetização $I_m = E_1/X_m$ permanece praticamente constante "
                                f"independente da carga — com torque baixo, a potência ativa $P$ é pequena "
                                f"enquanto a potência reativa $Q$ (dominada por $I_m$) permanece elevada, "
                                f"resultando em FP = P/√(P²+Q²) baixo. "
                                f"Motor superdimensionado para a carga aplicada."
                            )
                        else:
                            _causa = (
                                f"A corrente de magnetização ($I_m = E_1/X_m$) consome reativo "
                                f"independente da carga, elevando $Q$ em relação a $P$."
                            )
                        st.warning(
                            f"**Fator de Potência baixo** ({_fp:.3f} < 0,85).  \n"
                            f"{_causa}  \n"
                            f"Correção: banco de capacitores em paralelo para compensação do reativo."
                        )
                    st.caption(
                        "THD calculado via FFT de $i_{{as}}$ na janela de regime permanente. "
                        "FP = P_in / S_aparente, onde S = 3 × Va_rms × Ias_rms."
                    )

        # ── BLOCO 4: Assinatura de Corrente / FFT (expander) ─────────────────
        _ac_keys = [k for k in var_keys if k in ("ias", "ibs", "ics", "iar", "ibr", "icr")]
        with st.expander("Assinatura de Corrente (FFT / MCSA)", expanded=False):
            if _ac_keys:
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
                fig_fft = _cached_fig_fft(res, _dp, _fft_var, _fft_lbl, _cache_key=_res_hash)

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
                        f"Barra quebrada ativa (alfa={_alpha:.2f}) — "
                        f"componentes laterais em **(1±2s)f**: "
                        f"{_sb_lo:.1f} Hz e {_sb_hi:.1f} Hz (s={_s_val*100:.2f}%)."
                    )
                else:
                    st.caption("Linhas vermelhas tracejadas: harmônicas ímpares (1ª, 3ª, 5ª, 7ª, 9ª).")
                _render_plotly(fig_fft, div_id="ems-fft-results")
            else:
                st.info("Selecione correntes de fase (ias, ibs, ics...) na configuração para habilitar a análise espectral.")

    # ══════════════════════════════════════════════════════════════════════
    # ABA 4 — GESTÃO DE ATIVOS (ROI / TÉRMICA)
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativos:
        if _em:
            st.markdown('<p class="slabel">Análise Econômica</p>', unsafe_allow_html=True)

            # Linha primária — métricas de decisão
            _ec1, _ec2, _ec3 = st.columns(3)
            _ec1.metric("Rendimento em Regime",    f"{_em['eta_ss']:.2f} %")
            _ec2.metric("Custo Operacional Anual", f"R$ {_em['custo_ano_brl']:,.2f}",
                        help=(
                            f"Estimado como: P_in_regime × 8.760 h/ano × tarifa.\n"
                            f"Suposições: operação contínua 24 h/dia, 365 dias/ano, "
                            f"na potência de regime permanente.\n"
                            f"Tarifa atual: R$ {energy_tariff:.4f}/kWh."
                        ))
            _ec3.metric("Potência Entrada (regime)", f"{_em['P_in_ss_kw']:.3f} kW")

            # Detalhes de consumo (expander)
            with st.expander("Detalhes do Consumo", expanded=False):
                _ed1, _ed2, _ed3 = st.columns(3)
                _ed1.metric("Energia no Experimento", f"{_em['E_total_kwh']:.5f} kWh")
                _ed2.metric("Custo do Experimento",   f"R$ {_em['custo_exp_brl']:.4f}")
                _ed3.metric("Energia Anual Projetada",
                            f"{_em['P_in_ss_kw'] * _em['horas_op_ano']:,.1f} kWh/ano",
                            help=(
                                f"Energia elétrica que o motor consumiria em um ano de "
                                f"operação contínua à potência de regime "
                                f"({_em['P_in_ss_kw']:.3f} kW × 8.760 h/ano)."
                            ))
                st.caption(
                    f"Projeção anual baseada em operação contínua (8.760 h/ano) à tarifa de "
                    f"R$ {energy_tariff:.2f}/kWh."
                )
        else:
            st.info("Análise econômica não disponível para o experimento de desligamento.")


    # ══════════════════════════════════════════════════════════════════════
    # PAINEL DE REFERÊNCIAS + EXPORTAÇÃO PDF  (fora das abas)
    # ══════════════════════════════════════════════════════════════════════
    st.write("")
    st.divider()
    st.markdown('<p class="slabel">Exportar</p>', unsafe_allow_html=True)

    _tmax_exp = float(res["t"][-1]) if len(res.get("t", [])) > 0 else 1.0
    _h_exp    = float(res["t"][1] - res["t"][0]) if len(res.get("t", [])) > 1 else 1e-3

    # insights e load_torque para todos os PDFs
    _pdf_load_torque = float((exp_config or {}).get("Tl_final", 0.0))
    try:
        _pdf_insights = generate_insights(
            res=res, mp=mp,
            load_torque=_pdf_load_torque,
            tmax=_tmax_exp, exp_type=exp_type,
        )
    except Exception:
        _pdf_insights = []

    _ecol1, _ecol2 = st.columns(2)

    with _ecol1:
        if not st.session_state.get("pdf_bytes_academico"):
            if st.button("Relatório Acadêmico", key="btn_pdf_academico"):
                with st.spinner("Gerando Relatório Acadêmico..."):
                    st.session_state["pdf_bytes_academico"] = generate_academico(
                        exp_label=exp_label, mp=mp, res=res,
                        var_keys=var_keys, var_labels=var_labels, t_events=t_events,
                        exp_type=exp_type, ref_list=ref_list,
                        energy_tariff=energy_tariff,
                        tmax=_tmax_exp, h=_h_exp,
                        insights=_pdf_insights,
                        load_torque=_pdf_load_torque,
                    )
                st.rerun()
        else:
            st.download_button(
                label="Baixar Relatório Acadêmico (PDF)",
                data=st.session_state["pdf_bytes_academico"],
                file_name="relatorio_iws_academico.pdf",
                mime="application/pdf",
                key="btn_pdf_academico_download",
            )
            if st.button("Regerar Acadêmico", key="btn_pdf_academico_regen"):
                del st.session_state["pdf_bytes_academico"]
                st.rerun()

    with _ecol2:
        if not st.session_state.get("pdf_bytes_industrial"):
            if st.button("Relatório Industrial", key="btn_pdf_industrial"):
                with st.spinner("Gerando Relatório Industrial..."):
                    st.session_state["pdf_bytes_industrial"] = generate_industrial(
                        exp_label=exp_label, mp=mp, res=res,
                        var_keys=var_keys, var_labels=var_labels, t_events=t_events,
                        exp_type=exp_type, ref_list=ref_list,
                        energy_tariff=energy_tariff,
                        tmax=_tmax_exp, h=_h_exp,
                        insights=_pdf_insights,
                        load_torque=_pdf_load_torque,
                    )
                st.rerun()
        else:
            st.download_button(
                label="Baixar Relatório Industrial (PDF)",
                data=st.session_state["pdf_bytes_industrial"],
                file_name="relatorio_iws_industrial.pdf",
                mime="application/pdf",
                key="btn_pdf_industrial_download",
            )
            if st.button("Regerar Industrial", key="btn_pdf_industrial_regen"):
                del st.session_state["pdf_bytes_industrial"]
                st.rerun()

    # compatibilidade: pdf_bytes legado apontado para acadêmico
    if st.session_state.get("pdf_bytes_academico") and not st.session_state.get("pdf_bytes"):
        st.session_state["pdf_bytes"] = st.session_state["pdf_bytes_academico"]
