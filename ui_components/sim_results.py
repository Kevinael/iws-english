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
from viz.plotly_charts import build_fig_stacked, build_fig_sidebyside, build_fig_overlay
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
    """Calcula energia consumida, rendimento médio e custo operacional.

    Integra P_in = (3/2)·(Vqs·iqs + Vds·ids) sobre todo o intervalo de simulação.
    O rendimento é calculado na janela de regime permanente.

    Returns dict com:
        E_total_kwh   — energia total consumida no experimento (kWh)
        custo_exp_brl — custo do experimento (R$)
        horas_op_ano  — horas de operação projetadas por ano (baseado no perfil)
        custo_ano_brl — custo operacional anual projetado (R$)
        eta_ss        — rendimento em regime permanente (%)
        P_in_ss_kw    — potência de entrada em regime (kW)
    """
    t   = np.asarray(res["t"],   dtype=float)
    Vqs = np.asarray(res["Vqs"], dtype=float)
    Vds = np.asarray(res["Vds"], dtype=float)
    iqs = np.asarray(res["iqs"], dtype=float)
    ids = np.asarray(res["ids"], dtype=float)

    P_in_inst = (3.0 / 2.0) * (Vqs * iqs + Vds * ids)  # W instantâneo
    dt = float(t[1] - t[0]) if len(t) > 1 else 0.0
    E_total_j   = float(np.trapz(np.where(np.isfinite(P_in_inst), P_in_inst, 0.0), t))
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

    return {
        "E_total_kwh":   E_total_kwh,
        "custo_exp_brl": custo_exp_brl,
        "horas_op_ano":  horas_op_ano,
        "custo_ano_brl": custo_ano_brl,
        "eta_ss":        eta_ss,
        "P_in_ss_kw":    P_in_ss_kw,
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

    destaques = _kpis_destaque(res, exp_type, mp, decimals, t_events)
    if destaques:
        st.markdown('<p class="slabel">Destaques do Experimento</p>', unsafe_allow_html=True)
        cols = st.columns(len(destaques))
        for col, (lbl, val, unit) in zip(cols, destaques):
            col.metric(f"{lbl} ({unit})", val)
        st.write("")

    d = decimals

    if exp_type != "shutdown":
        st.markdown('<p class="slabel">Indicadores de Regime Permanente</p>', unsafe_allow_html=True)

        n_ss    = res["n_ss"]
        Te_ss   = res["Te_ss"]
        wr_ss   = res["wr_ss"]
        ias_rms = res["ias_rms"]
        Te_max  = float(np.max(res["Te"]))
        ias_pk  = float(np.max(np.abs(res["ias"])))

        def fmt_pot(val: float, d: int) -> tuple[str, str]:
            if abs(val) >= 1000:
                return "kW", f"{val/1000:.{d}f}"
            return "W", f"{val:.{d}f}"

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

        s_val  = res.get("s", 0.0)
        gerador = s_val < 0

        u_in,  v_in  = fmt_pot(res.get("P_in",  0.0), d)
        u0,    v0    = fmt_pot(abs(res.get("P_gap",  0.0)), d)
        u1,    v1    = fmt_pot(abs(res.get("P_mec",  0.0)), d)
        u2,    v2    = fmt_pot(res.get("P_cu_r", 0.0), d)

        lbl_in  = f"P. Mec. Turbina ({u_in})"   if gerador else f"P. Entrada ({u_in})"
        lbl_gap = f"P. Entreferro Gerada ({u0})" if gerador else f"P. Entreferro ({u0})"
        lbl_mec = f"P. Mec. Entrada ({u1})"      if gerador else f"P. Mecanica ({u1})"

        u_out, v_out = fmt_pot(res.get("P_out", 0.0), d)

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

    st.write("")

    if not var_keys:
        st.info("Nenhuma grandeza selecionada. Retorne à configuração e escolha variáveis para plotar.")
        return

    # controles de visualização
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
            "Zoom",
            ["Completo", "Partida", "Regime Permanente"],
            horizontal=True,
            key="zoom_mode",
        )

    st.write("")

    # janela de zoom
    x_zoom    = None
    tmax_data = float(res["t"][-1])
    t_ss_idx  = int(res.get("_ss_start", 0))
    t_ss      = float(res["t"][t_ss_idx]) if t_ss_idx < len(res["t"]) else tmax_data

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
            all_y    = np.concatenate(arrays)
            ymin, ymax = float(all_y.min()), float(all_y.max())
            span     = ymax - ymin
            pad      = span * 0.15 if span > 0 else (abs(ymax) * 0.10 if ymax != 0 else 0.1)
            axis_key = "yaxis" if ya == "y" else f"yaxis{ya[1:]}"
            ax = getattr(fig.layout, axis_key, None)
            if ax is not None:
                ax.range    = [ymin - pad, ymax + pad]
                ax.autorange = False
        return fig

    def _render_plotly(fig: go.Figure, div_id: str = "ems-plot") -> None:
        st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key=div_id)

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

    var_labels_plot = [_strip_latex(l) for l in var_labels]
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

    st.write("")

    # ── Assinatura de Corrente (FFT) + diagnóstico de barra quebrada ──────
    _ac_keys = [k for k in var_keys if k in ("ias", "ibs", "ics", "iar", "ibr", "icr")]
    if _ac_keys:
        st.divider()
        st.markdown('<p class="slabel">Assinatura de Corrente (FFT)</p>', unsafe_allow_html=True)
        with st.expander("Ver espectro de amplitudes", expanded=False):
            _fft_var = st.selectbox(
                "Variável para análise espectral",
                options=_ac_keys,
                format_func=lambda k: next((l for kk, l in zip(var_keys, var_labels) if kk == k), k),
                key="fft_var_select_results",
            )
            _fft_lbl = _strip_latex(
                next((l for kk, l in zip(var_keys, var_labels) if kk == _fft_var), _fft_var)
            )
            fig_fft = build_fig_fft(res, dark_plot, key=_fft_var, label=_fft_lbl)

            # ── sidebands de barra quebrada ──────────────────────────────
            _alpha = float(res.get("_broken_bar_severity", 0.0))
            if _alpha > 0:
                _s_val  = float(res.get("s", 0.0))
                _f_fund = mp.f
                _sb_lo  = _f_fund * (1.0 - 2.0 * abs(_s_val))
                _sb_hi  = _f_fund * (1.0 + 2.0 * abs(_s_val))
                for _freq, _lbl in [(_sb_lo, f"(1−2s)f={_sb_lo:.1f}Hz"), (_sb_hi, f"(1+2s)f={_sb_hi:.1f}Hz")]:
                    fig_fft.add_vline(
                        x=_freq, line_dash="dash", line_color="#f59e0b", line_width=1.5,
                        annotation_text=_lbl,
                        annotation_font_color="#f59e0b",
                        annotation_font_size=9,
                    )
                st.caption(
                    f"⚠ Barra quebrada ativa (α={_alpha:.2f}) — "
                    f"componentes laterais destacadas em **(1±2s)f**: "
                    f"{_sb_lo:.1f} Hz e {_sb_hi:.1f} Hz (s={_s_val*100:.2f}%)."
                )
            else:
                st.caption("Linhas vermelhas tracejadas: harmônicas ímpares (1ª, 3ª, 5ª, 7ª, 9ª).")

            _render_plotly(fig_fft, div_id="ems-fft-results")

    # ── Análise Econômica ─────────────────────────────────────────────────
    if exp_type != "shutdown":
        _em = compute_energy_metrics(res, energy_tariff)
        st.divider()
        st.markdown('<p class="slabel">Análise Econômica (IAS Energy Conservation)</p>', unsafe_allow_html=True)
        with st.expander("Ver análise de energia e custo operacional", expanded=False):
            _ec1, _ec2, _ec3 = st.columns(3)
            _ec1.metric("Energia no Experimento",    f"{_em['E_total_kwh']:.5f} kWh")
            _ec2.metric("Custo do Experimento",      f"R$ {_em['custo_exp_brl']:.4f}")
            _ec3.metric("Potência Entrada (regime)", f"{_em['P_in_ss_kw']:.3f} kW")

            _ec4, _ec5, _ec6 = st.columns(3)
            _ec4.metric("Rendimento em Regime",      f"{_em['eta_ss']:.2f} %")
            _ec5.metric("Custo Operacional Anual",   f"R$ {_em['custo_ano_brl']:,.2f}")
            _ec6.metric("Energia Anual Projetada",   f"{_em['P_in_ss_kw'] * _em['horas_op_ano']:,.1f} kWh/ano")

            st.caption(
                f"Projeção anual baseada em operação contínua (8.760 h/ano) à tarifa de "
                f"R$ {energy_tariff:.2f}/kWh. Energia calculada integrando $P_{{in}} = \\frac{{3}}{{2}}(V_{{qs}}i_{{qs}} + V_{{ds}}i_{{ds}})$."
            )

    st.write("")

    # botão PDF
    st.divider()
    st.markdown('<p class="slabel">Exportar</p>', unsafe_allow_html=True)
    if st.button("Gerar Relatório Técnico (PDF)", key="btn_pdf"):
        with st.spinner("Gerando PDF..."):
            st.session_state["pdf_bytes"] = generate_pdf_report(
                exp_label, mp, res, fig_pdf,
                var_keys, var_labels, t_events,
                exp_type=exp_type,
                ref_list=ref_list,
            )
    if st.session_state.get("pdf_bytes"):
        st.download_button(
            label="Baixar Relatório PDF",
            data=st.session_state["pdf_bytes"],
            file_name="relatorio_ems.pdf",
            mime="application/pdf",
            key="btn_pdf_download",
        )
