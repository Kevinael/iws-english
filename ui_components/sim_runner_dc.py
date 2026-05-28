# -*- coding: utf-8 -*-
"""Execução da simulação MCC — orquestra fontes + solver e persiste resultado.

Exporta:
    execute_simulation_flow_dc — chamada única quando "Executar Simulação" é clicado.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.dc_machine_model import DCMachineParams
from core.dc_solver import run_simulation_dc
from core.dc_sources import make_voltage_fn_dc, make_torque_fn_dc


def execute_simulation_flow_dc(
    mp: DCMachineParams,
    exp_config: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    tmax: float,
    h: float,
    ref_code: int,
    dark: bool,
) -> None:
    """Valida, integra e salva o resultado em st.session_state["sim_result"].

    Segue o mesmo contrato de execute_simulation_flow (MIT): em erro exibe
    mensagem e não altera session_state.
    """
    if not var_keys:
        st.warning("Selecione ao menos uma grandeza para plotar antes de executar.")
        return

    mode = exp_config.get("exp_type", "dol_dc")

    # sentinel tmax==0 → usar valor automático calculado em sim_config_dc
    if tmax == 0.0:
        tmax = float(exp_config.get("_tmax_auto_val", 12.0))

    voltage_fn = make_voltage_fn_dc(mode, mp, exp_config)
    torque_fn  = make_torque_fn_dc(mode, mp, exp_config)

    with st.spinner("Executando integração numérica (MCC)..."):
        try:
            res = run_simulation_dc(mp, tmax, h, voltage_fn, torque_fn)

            st.session_state["pdf_bytes"] = None
            st.session_state["zoom_mode_dc"] = "Completo"
            st.session_state["sim_result"] = dict(
                res=res,
                var_keys=var_keys,
                var_labels=var_labels,
                t_events=[],
                dark=dark,
                mp=mp,
                exp_label=exp_config.get("exp_label", "Simulacao DC"),
                exp_type=mode,
                exp_config=exp_config,
                tmax=tmax,
                h=h,
                energy_tariff=0.0,
                torque_fn=torque_fn,
            )
            st.session_state["_sim_toast"] = (
                f"Simulação MCC concluída — "
                f"n = {res['n_ss']:.1f} RPM | "
                f"Te = {res['Te_ss']:.3f} N·m"
            )
            st.rerun()
        except Exception as e:
            st.error("Falha durante a integração numérica da simulação MCC.")
            st.markdown(
                "**Sugestões:**\n"
                "- Reduza o tempo de simulação ($t_{max}$).\n"
                "- Diminua o passo de integração $h$ (típico: 1×10⁻⁴ s).\n"
                "- Verifique consistência dos parâmetros ($R_a$, $L_a$, $k_b$, $J$)."
            )
            with st.expander("Detalhes do erro", expanded=False):
                st.code(f"{type(e).__name__}: {e}", language="text")
