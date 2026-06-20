# -*- coding: utf-8 -*-
"""
tim_runner.py
=============
Orchestrates induction-machine simulation execution — computes automatic time limits, calls core.tim.facade, and persists results to session_state.

Responsibilities:
  - Compute tmax_auto based on experiment type and motor inertia (calc_tmax_auto).
  - Validate inputs and construct MachineParams before calling run_simulation.
  - Store the result dict in st.session_state["sim_result"] for downstream consumers.

Relationships:
  Imported by : IWS_UI, ui_components.tim_config
  Imports     : core.tim.facade

Extending:
  - To change the automatic time limit formula, modify calc_tmax_auto for the relevant experiment key.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.tim.facade import MachineParams, build_fns, run_simulation


def calc_tmax_auto(exp_config: dict, mp: MachineParams) -> float:
    """Computes automatic tmax: last event + mechanical settling time based on inertia.

    Returns tmax in seconds. Used both by the UI (preview) and the runner.
    """
    exp_type = exp_config.get("exp_type", "")
    if exp_type == "dol":
        t_last = exp_config.get("t_load", 0.0) or 1.0
    elif exp_type in ("yd", "comp"):
        t_last = max(exp_config.get("t_2", 0.5), exp_config.get("t_load", 1.0))
    elif exp_type == "soft":
        t_last = max(exp_config.get("t_peak", 5.0), exp_config.get("t_load", 1.0))
    elif exp_type == "load_pulse":
        t_last = exp_config.get("t_removal", exp_config.get("t_load", 1.0))
    elif exp_type == "generator":
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
    """Validates, integrates, and saves the result to st.session_state["sim_result"].

    On parameter error or numerical divergence, displays messages in the UI
    and does not alter session state.
    """
    if not var_keys:
        st.warning("Select at least one variable to plot before running the simulation.")
        return

    if exp_config.get("_invalid"):
        st.error("Correct the experiment parameters before running.")
        return

    vfn, tfn, t_events = build_fns(exp_config, mp)

    _exp_type = exp_config.get("exp_type", "")

    if _exp_type == "shutdown":
        _tmax_run = float(exp_config.get("_t_end_shutdown", tmax))
    elif tmax <= 0.0:
        _tmax_run = calc_tmax_auto(exp_config, mp)
    else:
        _tmax_run = tmax

    _imbalance_a      = exp_config.get("imbalance_a",      0.0)
    _imbalance_b      = exp_config.get("imbalance_b",      0.0)
    _imbalance_c      = exp_config.get("imbalance_c",      0.0)
    _phase_loss_a = exp_config.get("phase_loss_a", False)
    _phase_loss_b = exp_config.get("phase_loss_b", False)
    _phase_loss_c = exp_config.get("phase_loss_c", False)
    _t_imbalance      = exp_config.get("t_imbalance",      0.0)
    _df_a         = exp_config.get("df_a",          0.0)
    _df_b         = exp_config.get("df_b",          0.0)
    _df_c         = exp_config.get("df_c",          0.0)

    if (
        (_imbalance_a or _imbalance_b or _imbalance_c or _phase_loss_a or _phase_loss_b or _phase_loss_c)
        and _t_imbalance > 0.0
    ):
        t_events = t_events + [_t_imbalance]

    _broken_bar   = float(exp_config.get("broken_bar_severity", 0.0))
    _t_broken_bar = float(exp_config.get("t_broken_bar", 0.0))


    with st.spinner("Running numerical integration..."):
        try:
            if _broken_bar > 0.0 and _t_broken_bar > 0.0:
                t_events = t_events + [_t_broken_bar]
            res = run_simulation(
                mp=mp, tmax=_tmax_run, h=h,
                voltage_fn=vfn, torque_fn=tfn,
                ref_code=ref_code,
                imbalance_a=_imbalance_a, imbalance_b=_imbalance_b, imbalance_c=_imbalance_c,
                phase_loss_a=_phase_loss_a, phase_loss_b=_phase_loss_b,
                phase_loss_c=_phase_loss_c, t_imbalance=_t_imbalance,
                df_a=_df_a, df_b=_df_b, df_c=_df_c,
                clamp_wr_at_zero=(exp_config.get("exp_type") == "shutdown"),
                t_cutoff=exp_config.get("t_cutoff") if exp_config.get("exp_type") == "shutdown" else None,
                broken_bar_severity=_broken_bar,
                t_broken_bar=_t_broken_bar,
            )
            st.session_state["pdf_bytes"] = None
            st.session_state["zoom_mode"] = "Full"
            st.session_state["sim_result"] = dict(
                res=res, var_keys=var_keys, var_labels=var_labels,
                t_events=t_events, dark=dark, mp=mp,
                exp_label=exp_config.get("exp_label", "Simulation"),
                exp_type=exp_config.get("exp_type",   "dol"),
                exp_config=exp_config,
                tmax=tmax, h=h,
                energy_tariff=energy_tariff,
                torque_fn=tfn,
            )
            st.session_state["_sim_toast"] = (
                f"Simulation complete — "
                f"n = {res['n'][-1]:.1f} RPM | "
                f"Te = {res['Te'][-1]:.2f} N·m"
            )
            st.rerun()
        except Exception as e:
            st.error("Failure during numerical integration of the simulation.")
            st.markdown(
                "**Suggestions to resolve:**\n"
                "- Reduce the total simulation time (tmax).\n"
                "- Decrease the integration step (h) — typical values: 1×10⁻⁴ to 1×10⁻⁵ s.\n"
                "- Verify that the motor parameters are physically consistent "
                "(Rfe positive and finite, Xm > Xls + Xlr, poles consistent with rated speed).\n"
                "- If the experiment involves phase loss or severe unbalance, "
                "reduce the duration — very high currents may cause divergence."
            )
            with st.expander("Technical error details (for debugging)", expanded=False):
                st.code(f"{type(e).__name__}: {e}", language="text")
