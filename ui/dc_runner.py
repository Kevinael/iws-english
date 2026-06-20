# -*- coding: utf-8 -*-
"""
dc_runner.py
================
Orchestrates DC machine simulation execution — validates parameters, calls dc_solver, and persists results to session_state.

Responsibilities:
  - Validate var_keys and simulation mode before dispatching to the solver.
  - Call run_simulation_dc with source functions constructed from make_voltage_fn_dc and make_torque_fn_dc.
  - Store the result dict in st.session_state["dc_sim_result"] for downstream consumers.

Relationships:
  Imported by : IWS_UI
  Imports     : core.dc_machine_model, core.dc_solver, core.dc_sources

Extending:
  - To add a new DCM simulation mode, register it in dc_sources and add the case to the runner dispatch logic.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.dc.facade import (
    DCMachineParams, run_simulation_dc,
    make_voltage_fn_dc, make_torque_fn_dc,
)


def execute_simulation_flow_dc(
    mp: DCMachineParams,
    exp_config: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    tmax: float,
    h: float,
    ref_code: int,
    dark: bool,
    energy_tariff: float = 0.75,
) -> None:
    """Validates, integrates, and saves the result to st.session_state["sim_result"].

    Follows the same contract as execute_simulation_flow (IM): on error displays
    a message and does not alter session_state.
    """
    if not var_keys:
        st.warning("Select at least one variable to plot before running the simulation.")
        return

    mode = exp_config.get("exp_type", "dol_dc")

    # sentinel tmax==0 → use automatic value computed in dc_config
    if tmax == 0.0:
        tmax = float(exp_config.get("_tmax_auto_val", 12.0))

    voltage_fn = make_voltage_fn_dc(mode, mp, exp_config)
    torque_fn  = make_torque_fn_dc(mode, mp, exp_config)

    with st.spinner("Running numerical integration (DC machine)..."):
        try:
            res = run_simulation_dc(mp, tmax, h, voltage_fn, torque_fn)

            st.session_state["pdf_bytes"] = None
            st.session_state["zoom_mode_dc"] = "Full"
            st.session_state["sim_result"] = dict(
                res=res,
                var_keys=var_keys,
                var_labels=var_labels,
                t_events=[],
                dark=dark,
                mp=mp,
                exp_label=exp_config.get("exp_label", "DC Simulation"),
                exp_type=mode,
                exp_config=exp_config,
                tmax=tmax,
                h=h,
                energy_tariff=energy_tariff,
                torque_fn=torque_fn,
            )
            st.session_state["_sim_toast"] = (
                f"DC machine simulation complete — "
                f"n = {res['n_ss']:.1f} RPM | "
                f"Te = {res['Te_ss']:.3f} N·m"
            )
            st.rerun()
        except Exception as e:
            st.error("Failure during numerical integration of the DC machine simulation.")
            st.markdown(
                "**Suggestions:**\n"
                "- Reduce the simulation time ($t_{max}$).\n"
                "- Decrease the integration step $h$ (typical: 1×10⁻⁴ s).\n"
                "- Verify parameter consistency ($R_a$, $L_a$, $k_b$, $J$)."
            )
            with st.expander("Error details", expanded=False):
                st.code(f"{type(e).__name__}: {e}", language="text")
