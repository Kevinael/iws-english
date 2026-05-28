"""DC machine simulation executor.

Exports:
  execute_dc_simulation_flow — run DC sim and persist result to st.session_state
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from core.dc_machine_model import DCMachineParams, DCMachineODEs
from core.dc_solver import DCSolver
from core.dc_sources import create_dc_source


def calc_tmax_dc_auto(exp_config: dict, params: DCMachineParams) -> float:
    """Auto-calculate simulation time for DC machines.

    Base time: longest experiment duration + mechanical settling (10*J).
    """
    exp_type = exp_config.get("exp_type", "dol_dc")

    if exp_type == "dol_dc":
        t_last = exp_config.get("t_carga", 1.0) or 1.0
    elif exp_type == "resistencia_dc":
        t_last = exp_config.get("t_ramp", 1.0) + exp_config.get("t_carga", 1.0)
    elif exp_type == "plugging_dc":
        t_last = exp_config.get("t_switch", 1.0) + exp_config.get("t_after_switch", 2.0)
    elif exp_type == "pulso_dc":
        t_last = exp_config.get("t_retirada", 2.0)
    elif exp_type == "gerador_dc":
        t_last = exp_config.get("t_carga", 1.0)
    elif exp_type == "campo_fraco_dc":
        t_last = exp_config.get("t_weaken", 1.0) + exp_config.get("t_after_weaken", 2.0)
    else:
        t_last = 1.0

    # Settling time: 10× inertia (heuristic from MIT model)
    t_settle = float(min(max(10.0 * params.J, 1.0), 20.0))
    return t_last + t_settle


def execute_dc_simulation_flow(
    config: str,
    params: DCMachineParams,
    exp_config: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    tmax: float,
    h: float,
    dark: bool,
) -> None:
    """Run DC simulation and store result in st.session_state["dc_sim_result"].

    Parameters:
      config: 'sep_motor', 'shunt_motor', 'series_motor', 'sep_gen', 'shunt_gen'
      params: DCMachineParams instance
      exp_config: experiment configuration (mode, switches, etc.)
      var_keys: list of output variable keys to compute ('ia', 'ifd', 'wm', 'Te', 'Ea')
      var_labels: corresponding display labels
      tmax: simulation duration (s); if 0, auto-calculate
      h: integration step (s)
      dark: dark mode flag (for result storage)
    """

    if not var_keys:
        st.warning("Selecione ao menos uma variável para plotar.")
        return

    exp_type = exp_config.get("exp_type", "dol_dc")

    # ── Initial state ──
    if config == "series_motor":
        x0 = np.array([0.0, 0.0])  # [ia, wm]
    else:
        x0 = np.array([0.0, 0.0, 0.0])  # [ifd, ia, wm]

    # ── Auto tmax ──
    if tmax <= 0.0:
        tmax = calc_tmax_dc_auto(exp_config, params)

    # ── Create voltage source ──
    Va_nom = params.Va if exp_type != "gerador_dc" else 0.0

    try:
        if exp_type == "dol_dc":
            Va_func = create_dc_source("dol_dc", Va_nom=Va_nom)
        elif exp_type == "resistencia_dc":
            t_ramp = exp_config.get("t_ramp", 1.0)
            Va_func = create_dc_source("resistencia_dc", Va_nom=Va_nom, t_ramp=t_ramp)
        elif exp_type == "plugging_dc":
            t_switch = exp_config.get("t_switch", 1.0)
            Va_func = create_dc_source("plugging_dc", Va_nom=Va_nom, t_switch=t_switch)
        elif exp_type == "pulso_dc":
            Va_func = create_dc_source("pulso_dc", Va_nom=Va_nom)
        elif exp_type == "gerador_dc":
            Va_func = create_dc_source("gerador_dc")
        elif exp_type == "campo_fraco_dc":
            Va_func = create_dc_source("campo_fraco_dc", Va_nom=Va_nom)
        else:
            st.error(f"Unknown DC exp_type: {exp_type}")
            return

        # ── Time vector ──
        t_eval = np.arange(0, tmax + h / 2, h)

        # ── Solver ──
        solver = DCSolver(config, params, t_eval, x0)

        with st.spinner("Integrando ODE do motor CC..."):
            t, x, y = solver.run(Va_func)

        # ── Store result ──
        result = {
            "config": config,
            "exp_type": exp_type,
            "t": t,
            "x": x,
            "y": y,
            "var_keys": var_keys,
            "var_labels": var_labels,
            "params": params,
            "tmax": tmax,
            "h": h,
            "dark_mode": dark,
            "color": "#1f77b4",  # default Plotly blue
            "dash": "solid",
        }

        st.session_state["dc_sim_result"] = result
        st.success(f"Simulação DC completada: {len(t)} pontos, {tmax:.2f}s")

    except Exception as e:
        st.error(f"Erro na integração DC: {str(e)}")
        import traceback
        st.write(traceback.format_exc())
