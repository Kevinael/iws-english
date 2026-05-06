# -*- coding: utf-8 -*-
"""Execução da simulação — orquestra build_fns + run_simulation e persiste o resultado.

Exporta:
    execute_simulation_flow — chamada única quando o botão "Executar Simulação" é clicado.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.EMS_PY import MachineParams, build_fns, run_simulation


def calc_tmax_auto(exp_config: dict, mp: MachineParams) -> float:
    """Calcula tmax automático: último evento + acomodação mecânica por inércia.

    Retorna o tmax em segundos. Usado tanto pela UI (preview) quanto pelo runner.
    """
    exp_type = exp_config.get("exp_type", "")
    if exp_type == "dol":
        t_last = exp_config.get("t_carga", 1.0)
    elif exp_type in ("yd", "comp"):
        t_last = max(exp_config.get("t_2", 0.5), exp_config.get("t_carga", 1.0))
    elif exp_type == "soft":
        t_last = max(exp_config.get("t_pico", 5.0), exp_config.get("t_carga", 1.0))
    elif exp_type in ("carga", "pulso_carga"):
        t_last = exp_config.get("t_retirada", exp_config.get("t_carga", 1.0))
    elif exp_type == "gerador":
        t_last = exp_config.get("t_2", 1.0)
    elif exp_type == "voltage_sag":
        t_last = exp_config.get("t_start_sag", 0.5) + exp_config.get("t_duration_sag", 0.1)
    else:
        t_last = 1.0
    t_acomo = float(min(max(15.0 * mp.J, 2.0), 30.0))
    return t_last + t_acomo


def execute_simulation_flow(
    mp: MachineParams,
    exp_config: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    tmax: float,
    h: float,
    ref_code: int,
    dark: bool,
    energy_tariff: float = 0.75,
) -> None:
    """Valida, integra e salva o resultado em st.session_state["sim_result"].

    Em caso de erro de parâmetro ou divergência numérica, exibe mensagens na UI
    e não altera o estado da sessão.
    """
    if not var_keys:
        st.warning("Selecione ao menos uma grandeza para plotar antes de executar.")
        return

    if exp_config.get("_invalid"):
        st.error("Corrija os parâmetros do experimento antes de executar.")
        return

    vfn, tfn, t_events = build_fns(exp_config, mp)

    _exp_type = exp_config.get("exp_type", "")

    if _exp_type == "shutdown":
        _tmax_run = float(exp_config.get("_t_end_shutdown", tmax))
    elif tmax <= 0.0:
        _tmax_run = calc_tmax_auto(exp_config, mp)
    else:
        _tmax_run = tmax

    _deseq_a      = exp_config.get("deseq_a",      0.0)
    _deseq_b      = exp_config.get("deseq_b",      0.0)
    _deseq_c      = exp_config.get("deseq_c",      0.0)
    _falta_fase_a = exp_config.get("falta_fase_a", False)
    _falta_fase_b = exp_config.get("falta_fase_b", False)
    _falta_fase_c = exp_config.get("falta_fase_c", False)
    _t_deseq      = exp_config.get("t_deseq",      0.0)

    if (
        (_deseq_a or _deseq_b or _deseq_c or _falta_fase_a or _falta_fase_b or _falta_fase_c)
        and _t_deseq > 0.0
    ):
        t_events = t_events + [_t_deseq]

    with st.spinner("Executando integração numérica..."):
        try:
            _broken_bar = float(exp_config.get("broken_bar_severity", 0.0))
            res = run_simulation(
                mp=mp, tmax=_tmax_run, h=h,
                voltage_fn=vfn, torque_fn=tfn,
                ref_code=ref_code,
                deseq_a=_deseq_a, deseq_b=_deseq_b, deseq_c=_deseq_c,
                falta_fase_a=_falta_fase_a, falta_fase_b=_falta_fase_b,
                falta_fase_c=_falta_fase_c, t_deseq=_t_deseq,
                clamp_wr_at_zero=(exp_config.get("exp_type") == "shutdown"),
                t_cutoff=exp_config.get("t_cutoff") if exp_config.get("exp_type") == "shutdown" else None,
                broken_bar_severity=_broken_bar,
            )
            st.session_state["pdf_bytes"]  = None
            st.session_state["sim_result"] = dict(
                res=res, var_keys=var_keys, var_labels=var_labels,
                t_events=t_events, dark=dark, mp=mp,
                exp_label=exp_config.get("exp_label", "Simulacao"),
                exp_type=exp_config.get("exp_type",   "dol"),
                exp_config=exp_config,
                tmax=tmax, h=h,
                energy_tariff=energy_tariff,
            )
            st.session_state["_sim_toast"] = (
                f"Simulação concluída — "
                f"n = {res['n'][-1]:.1f} RPM | "
                f"Te = {res['Te'][-1]:.2f} N·m"
            )
            st.rerun()
        except Exception as e:
            st.error(f"Erro na simulação: {e}")
            st.info(
                "Verifique os parâmetros. Passos de integração muito grandes "
                "ou parâmetros fisicamente inválidos podem causar divergência numérica."
            )
