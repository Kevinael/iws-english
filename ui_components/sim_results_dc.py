# -*- coding: utf-8 -*-
"""Renderização de resultados da simulação MCC: KPIs, gráficos e exportação PDF.

Exporta:
    render_dc_results   — 4 sub-abas: Visão Geral, Análise Dinâmica,
                          Diagnóstico DC, Gestão de Ativos DC
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import streamlit as st

from core.dc_machine_model import DCMachineParams
from viz.plotly_charts_dc import build_dc_stacked, build_dc_sidebyside


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


# ─────────────────────────────────────────────────────────────────────────────
# KPIs POR MODO
# ─────────────────────────────────────────────────────────────────────────────

def _kpis_destaque_dc(
    y: dict[str, np.ndarray],
    t: np.ndarray,
    exp_type: str,
    params: DCMachineParams,
    d: int,
) -> list[tuple[str, str, str]]:
    """Retorna lista de (label, valor_str, unidade) com KPIs prioritários por modo DC."""

    ia  = np.asarray(y.get("ia",  [0.0]))
    wm  = np.asarray(y.get("wm",  [0.0]))
    Te  = np.asarray(y.get("Te",  [0.0]))
    Ea  = np.asarray(y.get("Ea",  [0.0]))
    ifd = np.asarray(y.get("ifd", [0.0]))

    ia_pk   = float(np.max(np.abs(ia)))
    ia_ss   = float(ia[-1])
    wm_ss   = float(wm[-1])
    Te_ss   = float(Te[-1])
    Te_max  = float(np.max(Te))
    n_rpm   = wm_ss * 60.0 / (2.0 * np.pi)
    Ea_ss   = float(Ea[-1])
    ifd_ss  = float(ifd[-1])

    # Velocidade de regime estimada analiticamente: wm_nom = (Va - ia_ss*Ra) / kb / ifd_ss
    # Simplificado: wm_nom = Va / (kb * ifd_ss) se Ra*ia << Va
    kb = params.kb
    Va = params.Va
    Ra = params.Ra
    Vf = params.Vf
    Rf = params.Rf

    if exp_type == "dol_dc":
        items = [
            ("Corrente de Pico $i_a$",    f"{ia_pk:.{d}f}",   "A"),
            ("Corrente de Regime $i_a$",  f"{ia_ss:.{d}f}",   "A"),
            ("Velocidade Final $\\omega_m$", f"{wm_ss:.{d}f}", "rad/s"),
            ("Velocidade (RPM)",           f"{n_rpm:.{d}f}",   "RPM"),
            ("Torque Máximo $T_e$",        f"{Te_max:.{d}f}",  "N·m"),
            ("Torque de Regime $T_e$",     f"{Te_ss:.{d}f}",   "N·m"),
        ]

    elif exp_type == "resistencia_dc":
        items = [
            ("Corrente Inicial $i_a$",    f"{ia[0]:.{d}f}",   "A"),
            ("Corrente de Regime $i_a$",  f"{ia_ss:.{d}f}",   "A"),
            ("Velocidade Final $\\omega_m$", f"{wm_ss:.{d}f}", "rad/s"),
            ("Velocidade (RPM)",           f"{n_rpm:.{d}f}",   "RPM"),
            ("Torque de Regime $T_e$",     f"{Te_ss:.{d}f}",   "N·m"),
        ]

    elif exp_type == "plugging_dc":
        # Detectar instante de comutação (wm muda de sinal ou atinge mínimo)
        idx_switch = int(np.argmin(np.abs(wm))) if len(wm) > 0 else 0
        wm_pre  = float(wm[max(0, idx_switch - 1)])
        wm_post = float(wm[-1])
        items = [
            ("Velocidade Pré-Plugging",    f"{wm_pre:.{d}f}",  "rad/s"),
            ("Velocidade Final $\\omega_m$", f"{wm_post:.{d}f}","rad/s"),
            ("Corrente de Pico $i_a$",    f"{ia_pk:.{d}f}",   "A"),
            ("Torque Máximo (frenagem)",   f"{Te_max:.{d}f}",  "N·m"),
            ("Torque de Regime $T_e$",     f"{Te_ss:.{d}f}",   "N·m"),
        ]

    elif exp_type == "pulso_dc":
        # Antes e depois do pulso de carga
        half = len(t) // 2
        ia_antes = float(np.mean(ia[:max(1, half // 2)]))
        ia_depois = float(np.mean(ia[half:]))
        wm_antes  = float(np.mean(wm[:max(1, half // 2)]))
        wm_depois = float(np.mean(wm[half:]))
        items = [
            ("Corrente Pré-Pulso $i_a$",   f"{ia_antes:.{d}f}",  "A"),
            ("Corrente Pós-Pulso $i_a$",   f"{ia_depois:.{d}f}", "A"),
            ("Velocidade Pré-Pulso",        f"{wm_antes:.{d}f}",  "rad/s"),
            ("Velocidade Pós-Pulso",        f"{wm_depois:.{d}f}", "rad/s"),
            ("Corrente de Pico $i_a$",     f"{ia_pk:.{d}f}",     "A"),
        ]

    elif exp_type == "gerador_dc":
        # Gerador: Ea = tensão gerada; ia = corrente de saída
        Ea_max = float(np.max(Ea))
        P_out  = float(Ea_ss * ia_ss)  # potência elétrica de saída (aprox.)
        items = [
            ("Tensão Gerada $E_a$",        f"{Ea_ss:.{d}f}",   "V"),
            ("Tensão Máxima Gerada",        f"{Ea_max:.{d}f}",  "V"),
            ("Corrente de Saída $i_a$",    f"{ia_ss:.{d}f}",   "A"),
            ("Potência de Saída (aprox.)", f"{P_out:.{d}f}",   "W"),
            ("Velocidade $\\omega_m$",     f"{wm_ss:.{d}f}",   "rad/s"),
        ]

    elif exp_type == "campo_fraco_dc":
        ifd_ini = float(ifd[0])
        wm_ini  = float(wm[0])
        items = [
            ("Velocidade Inicial $\\omega_m$", f"{wm_ini:.{d}f}", "rad/s"),
            ("Velocidade Final $\\omega_m$",   f"{wm_ss:.{d}f}",  "rad/s"),
            ("Velocidade (RPM)",               f"{n_rpm:.{d}f}",  "RPM"),
            ("Corrente de Campo Inicial",      f"{ifd_ini:.{d}f}", "A"),
            ("Corrente de Campo Final",        f"{ifd_ss:.{d}f}",  "A"),
            ("Corrente de Armadura Final",     f"{ia_ss:.{d}f}",   "A"),
        ]

    else:
        items = [
            ("Corrente de Regime $i_a$",   f"{ia_ss:.{d}f}",   "A"),
            ("Velocidade Final $\\omega_m$", f"{wm_ss:.{d}f}", "rad/s"),
            ("Torque de Regime $T_e$",     f"{Te_ss:.{d}f}",   "N·m"),
        ]

    return items


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNÓSTICO DC
# ─────────────────────────────────────────────────────────────────────────────

def _gera_diagnostico_dc(
    y: dict[str, np.ndarray],
    t: np.ndarray,
    exp_type: str,
    params: DCMachineParams,
    config: str,
) -> list[dict]:
    """Gera lista de diagnósticos DC: {level, msg}.

    level: 'error' | 'warning' | 'info'
    """
    diags: list[dict] = []

    ia  = np.asarray(y.get("ia",  [0.0]))
    wm  = np.asarray(y.get("wm",  [0.0]))
    Te  = np.asarray(y.get("Te",  [0.0]))
    ifd = np.asarray(y.get("ifd", [0.0]))

    ia_ss  = float(ia[-1])
    wm_ss  = float(wm[-1])
    Te_ss  = float(Te[-1])
    ia_pk  = float(np.max(np.abs(ia)))

    Ra  = params.Ra
    kb  = params.kb
    Va  = params.Va
    Rf  = params.Rf
    Vf  = params.Vf
    Tload = params.Tload

    # ── Rotor travado ──────────────────────────────────────────────────────
    if exp_type not in ("plugging_dc",) and abs(wm_ss) < 0.1 and t[-1] > 2.0:
        diags.append({
            "level": "error",
            "msg": "**Rotor travado** — ωm ≈ 0 após {:.1f}s. Verificar Tload vs torque disponível.".format(t[-1]),
        })

    # ── Sobrecorrente de armadura ──────────────────────────────────────────
    # Corrente nominal estimada: In_a ≈ Va / (Ra + kb²/Rf) (sep) ou Va/Ra (série)
    if Ra > 0:
        ia_nom_est = Va / (Ra * 10.0)  # heurística conservadora: pico típico ≤ 10× nominal
        if ia_pk > ia_nom_est and ia_nom_est > 0:
            diags.append({
                "level": "warning",
                "msg": f"**Corrente de pico elevada** — ia_pk = {ia_pk:.2f} A. "
                       f"Verificar limitador de corrente de partida ou resistência de partida.",
            })

    # ── Sobrecarga de regime ───────────────────────────────────────────────
    if exp_type in ("dol_dc", "resistencia_dc", "pulso_dc", "campo_fraco_dc"):
        # Corrente de regime esperada ≈ Tload / (kb * ifd_ss) para campo independente
        ifd_ss = float(ifd[-1]) if len(ifd) > 0 else 1.0
        if kb > 0 and ifd_ss > 0:
            ia_esperado = Tload / (kb * ifd_ss) if Tload > 0 else 0.0
            if ia_esperado > 0 and abs(ia_ss - ia_esperado) / (ia_esperado + 1e-9) > 0.30:
                diags.append({
                    "level": "warning",
                    "msg": f"**Corrente de regime desviada** — simulado: {ia_ss:.2f} A, "
                           f"estimado analítico: {ia_esperado:.2f} A ({abs(ia_ss-ia_esperado)/ia_esperado*100:.1f}% desvio). "
                           "Verificar parâmetros kb, Tload ou configuração de excitação.",
                })

    # ── Campo fraco: velocidade acima do nominal ───────────────────────────
    if exp_type == "campo_fraco_dc":
        wm_nominal = Va / kb if kb > 0 else 0.0
        if wm_ss > 1.5 * wm_nominal:
            diags.append({
                "level": "warning",
                "msg": f"**Velocidade acima de 1,5× nominal** — ωm = {wm_ss:.1f} rad/s "
                       f"(nominal: {wm_nominal:.1f} rad/s). Risco de instabilidade mecânica.",
            })

    # ── Plugging: verificar parada ─────────────────────────────────────────
    if exp_type == "plugging_dc":
        if abs(wm_ss) > 0.5 * abs(float(wm[0])):
            diags.append({
                "level": "info",
                "msg": "**Plugging em andamento** — motor ainda em desaceleração ao final da simulação. "
                       "Aumentar tmax para observar parada completa.",
            })
        else:
            diags.append({
                "level": "info",
                "msg": f"**Frenagem por plugging concluída** — ωm final = {wm_ss:.3f} rad/s.",
            })

    # ── Gerador: excitação insuficiente ───────────────────────────────────
    if exp_type == "gerador_dc":
        Ea_ss = float(y.get("Ea", [0.0])[-1])
        if Ea_ss < 0.5 * Va and Va > 0:
            diags.append({
                "level": "warning",
                "msg": f"**Tensão gerada baixa** — Ea = {Ea_ss:.2f} V (Va nominal = {Va:.2f} V). "
                       "Verificar velocidade de acionamento (Tload) e parâmetros de campo.",
            })

    # ── Torque de regime vs carga ──────────────────────────────────────────
    if Tload > 0 and exp_type not in ("gerador_dc", "plugging_dc"):
        delta_Te = abs(Te_ss - Tload) / (Tload + 1e-9)
        if delta_Te > 0.15:
            diags.append({
                "level": "info",
                "msg": f"**Desequilíbrio torque-carga** — Te_regime = {Te_ss:.3f} N·m, "
                       f"Tload = {Tload:.3f} N·m (desvio: {delta_Te*100:.1f}%). "
                       "Verificar parâmetros mecânicos (J, B) ou tempo de simulação.",
            })

    # ── Comportamento esperado por modo ──────────────────────────────────
    _modo_desc = {
        "dol_dc":        "DOL — partida direta. ωm deve subir monotonicamente e estabilizar.",
        "resistencia_dc": "Partida por resistência — transiente suavizado vs DOL.",
        "plugging_dc":   "Plugging — torque de frenagem até parada; cuidado com corrente de pico.",
        "pulso_dc":      "Pulso de carga — observe afundamento de ωm e recuperação.",
        "gerador_dc":    "Gerador — ωm imposta mecanicamente; Ea e ia determinados pela carga.",
        "campo_fraco_dc": "Campo fraco — redução de ifd aumenta ωm acima do nominal.",
    }
    if exp_type in _modo_desc:
        diags.append({"level": "info", "msg": _modo_desc[exp_type]})

    return diags


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISE ENERGÉTICA DC
# ─────────────────────────────────────────────────────────────────────────────

def _compute_energy_dc(
    y: dict[str, np.ndarray],
    t: np.ndarray,
    params: DCMachineParams,
    config: str,
    exp_type: str,
    tariff: float = 0.75,
) -> dict:
    """Computa métricas energéticas para MCC."""
    ia  = np.asarray(y.get("ia",  [0.0]))
    ifd = np.asarray(y.get("ifd", [0.0]))
    wm  = np.asarray(y.get("wm",  [0.0]))
    Te  = np.asarray(y.get("Te",  [0.0]))
    Ea  = np.asarray(y.get("Ea",  [0.0]))

    ia_ss  = float(ia[-1])
    wm_ss  = float(wm[-1])
    Te_ss  = float(Te[-1])
    ifd_ss = float(ifd[-1])
    Ea_ss  = float(Ea[-1])

    Ra  = params.Ra
    Rf  = params.Rf
    Va  = params.Va
    Vf  = params.Vf

    # Potências de regime
    P_campo    = Vf * ifd_ss if config.startswith("sep") else Va * ifd_ss  # circuito de campo
    P_entrada  = Va * ia_ss + P_campo                                        # total elétrica entrada
    P_perdas_a = Ra * ia_ss**2                                               # perdas cobre armadura
    P_perdas_f = Rf * ifd_ss**2                                              # perdas cobre campo
    P_mecanica = Ea_ss * ia_ss                                               # potência convertida
    P_carga    = Te_ss * wm_ss                                               # potência mecânica útil
    P_atrito   = params.B * wm_ss**2                                         # perdas por atrito

    eta = (P_carga / P_entrada * 100.0) if P_entrada > 1e-6 else 0.0
    eta = max(0.0, min(100.0, eta))

    # Custo operacional anual (regime permanente, operação contínua)
    P_entrada_kw = P_entrada / 1000.0
    custo_ano    = P_entrada_kw * 8760.0 * tariff

    return {
        "P_entrada":   P_entrada,
        "P_campo":     P_campo,
        "P_perdas_a":  P_perdas_a,
        "P_perdas_f":  P_perdas_f,
        "P_mecanica":  P_mecanica,
        "P_carga":     P_carga,
        "P_atrito":    P_atrito,
        "eta":         eta,
        "custo_ano":   custo_ano,
        "P_entrada_kw": P_entrada_kw,
        "ia_ss":       ia_ss,
        "wm_ss":       wm_ss,
        "n_rpm":       wm_ss * 60.0 / (2.0 * np.pi),
        "Te_ss":       Te_ss,
        "Ea_ss":       Ea_ss,
        "ifd_ss":      ifd_ss,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RENDERIZAÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def render_dc_results(
    result: dict[str, Any],
    decimals: int = 3,
    dark: bool = False,
    energy_tariff: float = 0.75,
) -> None:
    """Renderiza resultados MCC em 4 sub-abas (padrão MIT).

    Parâmetros
    ----------
    result : dict
        Saída de execute_dc_simulation_flow. Chaves: config, exp_type,
        t, y, var_keys, var_labels, params.
    decimals : int
        Casas decimais para KPIs.
    dark : bool
        Tema escuro.
    energy_tariff : float
        Tarifa de energia (R$/kWh) para análise econômica.
    """
    config   = result.get("config", "sep_motor")
    exp_type = result.get("exp_type", "dol_dc")
    params   = result.get("params")
    t        = np.asarray(result.get("t", [0.0]))
    y        = result.get("y", {})
    var_keys   = result.get("var_keys",   [])
    var_labels = result.get("var_labels", [])

    if params is None or len(t) < 2:
        st.error("Resultado de simulação inválido.")
        return

    d = decimals

    st.divider()

    # Pré-calcula métricas (usadas em múltiplas abas)
    em = _compute_energy_dc(y, t, params, config, exp_type, energy_tariff)
    diags = _gera_diagnostico_dc(y, t, exp_type, params, config)

    n_erro   = sum(1 for dg in diags if dg["level"] == "error")
    n_alerta = sum(1 for dg in diags if dg["level"] == "warning")

    # ══════════════════════════════════════════════════════════════════════
    # ABAS DE RESULTADOS
    # ══════════════════════════════════════════════════════════════════════
    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs(
        ["Visão Geral", "Análise Dinâmica", "Diagnóstico DC", "Gestão de Ativos"],
        key="dc_results_tabs",
    )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 1 — VISÃO GERAL
    # ══════════════════════════════════════════════════════════════════════
    with tab_visao:
        # ── Painel de saúde ──────────────────────────────────────────────
        if n_erro > 0:
            _saude_ico, _saude_txt, _saude_fn = "🔴", "Anomalia Detectada", st.error
        elif n_alerta > 0:
            _saude_ico, _saude_txt, _saude_fn = "🟡", "Atenção", st.warning
        else:
            _saude_ico, _saude_txt, _saude_fn = "🟢", "Operação Normal", st.success

        _diag_suffix = ""
        if n_erro or n_alerta:
            _diag_suffix = f" — {n_erro} crítico(s), {n_alerta} alerta(s). Ver aba **Diagnóstico DC**."

        n_rpm = em["n_rpm"]
        eta   = em["eta"]

        _saude_fn(
            f"{_saude_ico} **{_saude_txt}** — "
            f"Velocidade: **{n_rpm:.0f} RPM** | "
            f"Rendimento: **{eta:.1f}%** | "
            f"Corrente Armadura: **{em['ia_ss']:.{d}f} A**"
            + _diag_suffix
        )
        st.write("")

        # ── Grandezas de operação ─────────────────────────────────────────
        st.markdown('<p class="slabel">Grandezas de Operação</p>', unsafe_allow_html=True)

        _op1 = st.columns(3)
        _op1[0].metric("Velocidade (RPM)", f"{n_rpm:.{d}f}")
        _op1[1].metric("Torque de Regime $T_e$ (N·m)", f"{em['Te_ss']:.{d}f}")
        _op1[2].metric("Corrente Armadura $i_a$ (A)", f"{em['ia_ss']:.{d}f}")

        _op2 = st.columns(3)
        _op2[0].metric("Tensão Induzida $E_a$ (V)", f"{em['Ea_ss']:.{d}f}")
        _op2[1].metric("Rendimento (%)", f"{eta:.{d}f}")

        if "sep" in config or "shunt" in config:
            _op2[2].metric("Corrente de Campo $i_{fd}$ (A)", f"{em['ifd_ss']:.{d}f}")
        else:
            _op2[2].metric("Velocidade (rad/s)", f"{em['wm_ss']:.{d}f}")

        _op3 = st.columns(3)
        def _fmt_pot(v: float) -> tuple[str, str]:
            return ("kW", f"{v/1000:.{d}f}") if abs(v) >= 1000 else ("W", f"{v:.{d}f}")

        u_in,  v_in  = _fmt_pot(em["P_entrada"])
        u_mec, v_mec = _fmt_pot(em["P_mecanica"])
        u_pa,  v_pa  = _fmt_pot(em["P_perdas_a"])

        _op3[0].metric(f"P. Entrada ({u_in})", v_in)
        _op3[1].metric(f"P. Mecânica ({u_mec})", v_mec)
        _op3[2].metric(f"Perdas Armadura ({u_pa})", v_pa)

        # ── KPIs por modo ────────────────────────────────────────────────
        destaques = _kpis_destaque_dc(y, t, exp_type, params, d)
        if destaques:
            st.write("")
            with st.expander("Grandezas de Transiente e Modo de Operação", expanded=False):
                _MAX_COLS = 4
                for i in range(0, len(destaques), _MAX_COLS):
                    chunk = destaques[i:i + _MAX_COLS]
                    cols  = st.columns(_MAX_COLS)
                    for col, (lbl, val, unit) in zip(cols, chunk):
                        col.metric(f"{lbl} ({unit})", val)

        # ── Resumo econômico ─────────────────────────────────────────────
        st.write("")
        st.markdown('<p class="slabel">Resumo Econômico</p>', unsafe_allow_html=True)
        _re1, _re2, _re3 = st.columns(3)
        _re1.metric("Rendimento em Regime", f"{eta:.2f} %")
        _re2.metric("Potência Entrada (regime)", f"{em['P_entrada_kw']:.3f} kW")
        _re3.metric(
            "Custo Operacional Anual",
            f"R$ {em['custo_ano']:,.2f}",
            help=(
                f"Estimado como P_entrada_regime × 8.760 h/ano × tarifa.\n"
                f"Tarifa atual: R$ {energy_tariff:.4f}/kWh."
            ),
        )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 2 — ANÁLISE DINÂMICA
    # ══════════════════════════════════════════════════════════════════════
    with tab_dinamica:
        if not var_keys:
            st.info("Nenhuma grandeza selecionada. Configure as variáveis e re-execute a simulação.")
        else:
            @st.fragment
            def _render_dinamica_dc(
                y_data, t_arr, var_keys, var_labels, dark, exp_type, decimals, res_hash,
            ):
                _viz_opts = ["Empilhados", "Lado a lado"]
                _cc1, _cc2 = st.columns([2, 1])
                with _cc1:
                    modo = st.radio("Visualização", _viz_opts, horizontal=True, key="dc_plot_mode")
                with _cc2:
                    dark_plot = st.toggle("Fundo escuro", value=dark, key="dc_plot_dark_toggle")

                st.write("")

                _res_for_plot = {"t": t_arr, **y_data}

                if modo == "Empilhados":
                    fig = build_dc_stacked(
                        _res_for_plot, var_keys, var_labels, dark_plot
                    )
                else:
                    fig = build_dc_sidebyside(
                        _res_for_plot, var_keys, var_labels, dark_plot
                    )

                st.plotly_chart(fig, width="stretch", config=_PLOT_CFG, key=f"dc_fig_{res_hash}")

            _res_hash = int(hash((
                float(y.get("wm", [0])[-1]),
                float(y.get("ia", [0])[-1]),
                float(t[-1]),
            )))

            _render_dinamica_dc(y, t, var_keys, var_labels, dark, exp_type, d, _res_hash)

    # ══════════════════════════════════════════════════════════════════════
    # ABA 3 — DIAGNÓSTICO DC
    # ══════════════════════════════════════════════════════════════════════
    with tab_diag:
        st.markdown("### Diagnóstico Automatizado")

        if not diags:
            st.success("Nenhuma anomalia detectada.")
        else:
            for dg in diags:
                lvl = dg["level"]
                msg = dg["msg"]
                if lvl == "error":
                    st.error(msg)
                elif lvl == "warning":
                    st.warning(msg)
                else:
                    st.info(msg)

        st.divider()

        # ── Tabela de regime permanente vs analítico ──────────────────────
        st.markdown("### Regime Permanente — Comparação Analítica")

        kb = params.kb
        Ra = params.Ra
        Va = params.Va
        Rf = params.Rf
        Vf = params.Vf

        ia_ss  = em["ia_ss"]
        wm_ss  = em["wm_ss"]
        ifd_ss = em["ifd_ss"]

        # Estimativa analítica (sep_motor / shunt / series)
        if "sep" in config:
            ifd_anl = Vf / Rf if Rf > 0 else 0.0
            wm_anl  = (Va - ia_ss * Ra) / (kb * ifd_anl) if (kb * ifd_anl) > 0 else 0.0
            ia_anl  = params.Tload / (kb * ifd_anl) if (kb * ifd_anl) > 0 else 0.0
        elif "shunt" in config:
            ifd_anl = Va / Rf if Rf > 0 else 0.0
            wm_anl  = (Va - ia_ss * Ra) / (kb * ifd_anl) if (kb * ifd_anl) > 0 else 0.0
            ia_anl  = params.Tload / (kb * ifd_anl) if (kb * ifd_anl) > 0 else 0.0
        else:  # series
            ifd_anl = ia_ss  # ia == ifd para série
            wm_anl  = (Va - ia_ss * (Ra + Rf)) / (kb * ia_ss) if (kb * ia_ss) > 0 else 0.0
            ia_anl  = float(np.sqrt(params.Tload / kb)) if kb > 0 and params.Tload > 0 else 0.0

        n_anl = wm_anl * 60.0 / (2.0 * np.pi)
        n_sim = wm_ss  * 60.0 / (2.0 * np.pi)

        def _desvio(sim: float, anl: float) -> str:
            if abs(anl) < 1e-9:
                return "—"
            return f"{abs(sim - anl) / abs(anl) * 100:.2f}%"

        st.markdown(f"""
| Grandeza | Simulado | Analítico | Desvio |
|---|---|---|---|
| $i_a$ (A) | {ia_ss:.{d}f} | {ia_anl:.{d}f} | {_desvio(ia_ss, ia_anl)} |
| $i_{{fd}}$ (A) | {ifd_ss:.{d}f} | {ifd_anl:.{d}f} | {_desvio(ifd_ss, ifd_anl)} |
| $\\omega_m$ (rad/s) | {wm_ss:.{d}f} | {wm_anl:.{d}f} | {_desvio(wm_ss, wm_anl)} |
| $n$ (RPM) | {n_sim:.{d}f} | {n_anl:.{d}f} | {_desvio(n_sim, n_anl)} |
""")

        st.caption(
            "Analítico: equações de regime permanente (resistências DC). "
            "Desvio > 5% indica parâmetro fora de consistência ou regime não atingido."
        )

    # ══════════════════════════════════════════════════════════════════════
    # ABA 4 — GESTÃO DE ATIVOS
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativos:
        st.markdown("### Fluxo de Potência")

        # Sankey DC: Entrada → Armadura + Campo → Mecânica → Carga + Atrito
        P_in  = em["P_entrada"]
        P_pa  = em["P_perdas_a"]
        P_pf  = em["P_perdas_f"]
        P_mec = em["P_mecanica"]
        P_car = em["P_carga"]
        P_atr = em["P_atrito"]

        try:
            import plotly.graph_objects as _pgo

            def _label(v: float) -> str:
                return f"{v/1000:.2f} kW" if abs(v) >= 1000 else f"{v:.2f} W"

            fig_sk = _pgo.Figure(_pgo.Sankey(
                node=dict(
                    label=["Entrada Elétrica", "Perdas Armadura", "Perdas Campo", "Mecânica", "Carga Útil", "Atrito"],
                    color=["#1f77b4", "#d62728", "#ff7f0e", "#2ca02c", "#17becf", "#8c564b"],
                    pad=15,
                    thickness=20,
                ),
                link=dict(
                    source=[0, 0, 0, 3, 3],
                    target=[1, 2, 3, 4, 5],
                    value=[
                        max(P_pa, 0.001),
                        max(P_pf, 0.001),
                        max(P_mec, 0.001),
                        max(P_car, 0.001),
                        max(P_atr, 0.001),
                    ],
                    label=[
                        _label(P_pa),
                        _label(P_pf),
                        _label(P_mec),
                        _label(P_car),
                        _label(P_atr),
                    ],
                    color=["rgba(214,39,40,0.4)", "rgba(255,127,14,0.4)",
                           "rgba(44,160,44,0.4)", "rgba(23,190,207,0.4)",
                           "rgba(140,86,75,0.4)"],
                ),
            ))
            fig_sk.update_layout(  # type: ignore[union-attr]
                title="Fluxo de Potência (Regime Permanente)",
                height=400,
                paper_bgcolor="#0f1218" if dark else "#ffffff",
                font=dict(family="Inter, system-ui", size=12,
                          color="#e5e7eb" if dark else "#000000"),
                margin=dict(l=30, r=30, t=50, b=30),
            )
            st.plotly_chart(fig_sk, width="stretch",
                            config={"displaylogo": False, "responsive": True},
                            key="dc_sankey")
        except Exception:
            # Fallback: tabela de potências
            def _fmt_p(v: float) -> str:
                return f"{v/1000:.3f} kW" if abs(v) >= 1000 else f"{v:.3f} W"

            st.markdown(f"""
| Componente | Potência |
|---|---|
| Entrada Elétrica | {_fmt_p(P_in)} |
| Perdas Armadura (Ra·ia²) | {_fmt_p(P_pa)} |
| Perdas Campo (Rf·ifd²) | {_fmt_p(P_pf)} |
| Potência Mecânica Convertida | {_fmt_p(P_mec)} |
| Potência Útil (Te·ωm) | {_fmt_p(P_car)} |
| Perdas por Atrito (B·ωm²) | {_fmt_p(P_atr)} |
| **Rendimento** | **{em['eta']:.2f} %** |
""")

        st.divider()

        # ── Análise de custo e ciclo de vida ─────────────────────────────
        st.markdown("### Análise Econômica e Ciclo de Vida")

        _ec1, _ec2, _ec3 = st.columns(3)
        _ec1.metric("Rendimento em Regime", f"{em['eta']:.2f} %")
        _ec2.metric("Custo Anual (24h/dia)", f"R$ {em['custo_ano']:,.2f}",
                    help=f"Tarifa: R$ {energy_tariff:.4f}/kWh, operação contínua.")
        _ec3.metric("Potência Entrada (kW)", f"{em['P_entrada_kw']:.4f}")

        st.write("")
        _ec4, _ec5, _ec6 = st.columns(3)
        horas_semana = 40.0
        custo_semana = em["P_entrada_kw"] * horas_semana * energy_tariff
        custo_mes    = em["P_entrada_kw"] * horas_semana * 4.33 * energy_tariff
        _ec4.metric("Custo/Semana (40h)", f"R$ {custo_semana:.2f}")
        _ec5.metric("Custo/Mês (40h/sem)", f"R$ {custo_mes:.2f}")
        _ec6.metric("Perdas Totais (W)", f"{P_pa + P_pf + P_atr:.3f}")

        st.divider()

        # ── Exportar PDF ──────────────────────────────────────────────────
        st.markdown("### Exportar Relatório")

        exp_label = f"MCC_{config}_{exp_type}_{int(time.time() % 10000)}"
        pdf_key   = "pdf_bytes_dc_academico"

        if not st.session_state.get(pdf_key):
            if st.button("📄 Gerar PDF Acadêmico", use_container_width=True, key="btn_pdf_dc"):
                try:
                    from viz.pdf_dc import generate_academico

                    mp_dict = {
                        "Rf": float(params.Rf), "Lf": float(params.Lf),
                        "Ra": float(params.Ra), "La": float(params.La),
                        "kb": float(params.kb), "J":  float(params.J),
                        "B":  float(params.B),  "Va": float(params.Va),
                        "Vf": float(params.Vf), "Tload": float(params.Tload),
                        "f":  60.0, "Rs": params.Ra, "Rfe": 500.0,
                    }

                    with st.spinner("Gerando Relatório Acadêmico..."):
                        st.session_state[pdf_key] = generate_academico(
                            exp_label=exp_label,
                            mp=mp_dict,
                            res=result,
                            var_keys=["ia", "ifd", "wm", "Te", "Ea"],
                            var_labels=[
                                "Corrente de Armadura (A)",
                                "Corrente de Campo (A)",
                                "Velocidade Mecânica (rad/s)",
                                "Torque (N·m)",
                                "Força Contra-Eletromotriz (V)",
                            ],
                            exp_type=config + "_" + exp_type,
                            energy_tariff=energy_tariff,
                            tmax=float(t[-1]),
                            h=float(t[1] - t[0]) if len(t) > 1 else 1e-3,
                        )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao gerar PDF: {exc}")
        else:
            st.download_button(
                label="⬇️ Baixar Relatório (PDF)",
                data=st.session_state[pdf_key],
                file_name=f"{exp_label}_relatorio.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_dl_pdf_dc",
            )
            if st.button("🔄 Regerar PDF", use_container_width=True, key="btn_regen_pdf_dc"):
                del st.session_state[pdf_key]
                st.rerun()
