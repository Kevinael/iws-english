# -*- coding: utf-8 -*-
"""
IWS_UI.py
=========
Main Streamlit orchestrator — configures the page, initialises session_state,
and routes to tabs via a machine registry.

Responsibilities:
  - Configure page_config and session_state with default values
  - Render sidebar, header, and machine selector (MIT / DCM)
  - Route to the registered machine spec (tabs, sim renderer, theory renderer)

Relationships:
  Imported by : (entry point — not imported by any project module)
  Imports     : ui.theme, ui.clean_view, ui_components.theory_view,
                ui_components.tim_config, ui_components.tim_results,
                ui_components.tim_runner, ui_components.sim_config_dc,
                ui_components.sim_results_dc, ui_components.sim_runner_dc

Extending:
  - To add a new machine type, write its sim-tab renderer and theory renderer,
    then register a _MachineSpec in _MACHINE_REGISTRY keyed by the machine code.
    No if/elif branches need to change.
"""

from __future__ import annotations

import dataclasses
from typing import Callable

import streamlit as st

from ui.theme import apply_css
from ui_components.reference_manager import save_reference
from core.constants import DC_SESSION_DEFAULTS, MIT_SESSION_DEFAULTS
from ui.clean_view import render_clean_view
from viz.tim_eqcircuit import render_circuit as _render_circuit_eqcircuit_plotter

from ui_components.theory_view import render_theory_tab
from data.ui_labels import MACHINES
from ui_components.tim_config import (
    _WK,
    _init_default_preset,
    render_machine_selector,
    render_machine_params,
    render_experiment_config,
)
from ui_components.tim_results import render_results, render_ref_panel
from ui_components.tim_runner import execute_simulation_flow

# MCC
from ui_components.sim_config_dc import render_dc_machine_params, render_experiment_config_dc
from ui_components.sim_runner_dc import execute_simulation_flow_dc
from ui_components.sim_results_dc import render_results_dc
from viz.eqcircuit_plotter_dc_v2 import render_circuit_dc_v2 as _render_circuit_dc_v2


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Web Simulation Infrastructure",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS LOCAIS
# ─────────────────────────────────────────────────────────────────────────────

def _render_circuit(mp, dark: bool) -> None:
    from ui.theme import _palette
    _render_circuit_eqcircuit_plotter(mp, dark, _palette)


def _on_machine_switch() -> None:
    """Clear simulation state when the user switches between MIT and DC."""
    prev = st.session_state.get("_prev_machine")
    cur  = st.session_state.get("selected_machine")
    if prev is not None and prev != cur:
        st.session_state["sim_result"] = None
        st.session_state["ref_list"]   = []
    st.session_state["_prev_machine"] = cur


def _render_save_ref_buttons(suffix: str) -> None:
    """Renders the Save/Clear reference buttons (shared between machines)."""
    _can_save = (
        st.session_state["sim_result"] is not None
        and len(st.session_state["ref_list"]) < 5
    )
    b1, b2 = st.columns(2)
    with b1:
        save_ref = st.button("Save as Reference", key=f"btn_save_ref{suffix}",
                             width="stretch", disabled=not _can_save,
                             help="Saves the current result for comparison (max. 5)")
    with b2:
        clear_ref = st.button("Clear References", key=f"btn_clear_ref{suffix}",
                              width="stretch",
                              disabled=not st.session_state["ref_list"],
                              help="Removes all saved references")
    if save_ref and _can_save:
        save_reference(st.session_state["sim_result"])
    if clear_ref:
        st.session_state["ref_list"] = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION TAB RENDERERS (one per machine)
# ─────────────────────────────────────────────────────────────────────────────

def _render_sim_tab_dc(dark: bool, experiment_mode: bool, dec: int) -> None:
    col_params, col_circuit = st.columns([1, 1], gap="large")

    with col_params:
        mp_dc, ref_code_dc, energy_tariff_dc = render_dc_machine_params(dark, experiment_mode)

    with col_circuit:
        st.markdown('<p class="slabel">Equivalent Circuit</p>', unsafe_allow_html=True)
        _render_circuit_dc_v2(mp_dc, dark)
        st.write("")
        exp_config_dc, var_keys_dc, var_labels_dc, tmax_dc, h_dc = \
            render_experiment_config_dc(mp_dc)

    st.write("")
    run_clicked_dc = st.button("Run Simulation", key="btn_run_dc", width="stretch")

    _render_save_ref_buttons("_dc")

    if run_clicked_dc:
        execute_simulation_flow_dc(
            mp=mp_dc, exp_config=exp_config_dc,
            var_keys=var_keys_dc, var_labels=var_labels_dc,
            tmax=tmax_dc, h=h_dc, ref_code=ref_code_dc, dark=dark,
            energy_tariff=energy_tariff_dc,
        )

    _toast = st.session_state.pop("_sim_toast", None)
    if _toast:
        st.success(_toast)

    sr_dc = st.session_state.get("sim_result")
    ref_list_dc = st.session_state["ref_list"]
    render_ref_panel(ref_list_dc)

    if sr_dc is not None:
        render_results_dc(
            res=sr_dc["res"],
            var_keys=var_keys_dc if var_keys_dc else sr_dc["var_keys"],
            var_labels=var_labels_dc if var_labels_dc else sr_dc["var_labels"],
            dark=sr_dc["dark"],
            t_events=sr_dc.get("t_events", []),
            mp=sr_dc["mp"],
            exp_label=sr_dc.get("exp_label", "Simulacao DC"),
            exp_type=sr_dc.get("exp_type", "dol_dc"),
            exp_config=sr_dc.get("exp_config", {}),
            tmax=sr_dc.get("tmax", tmax_dc),
            h=sr_dc.get("h", h_dc),
            decimals=dec,
            ref_list=ref_list_dc,
            energy_tariff=sr_dc.get("energy_tariff", energy_tariff_dc),
        )
    else:
        with st.container(border=True):
            st.markdown(
                "### No DC machine simulation has been run yet\n\n"
                "Configure the machine and experiment parameters above, "
                "then click **Run Simulation** to visualise:\n\n"
                "- Transient waveforms of $i_a$, $\\omega_m$, $T_e$\n"
                "- Steady-state metrics (speed, torque, current)\n"
                "- Commutation diagnostics and loss analysis"
            )


def _render_sim_tab_mit(dark: bool, experiment_mode: bool, dec: int) -> None:
    is_mobile = False

    col_params, col_circuit = st.columns([1, 1], gap="large")

    with col_params:
        mp, ref_code, energy_tariff = render_machine_params(dark, experiment_mode, _WK)

    with col_circuit:
        st.markdown('<p class="slabel">Single-Phase Equivalent Circuit</p>', unsafe_allow_html=True)
        _render_circuit(mp, dark)
        st.write("")
        exp_config, var_keys, var_labels, tmax, h = render_experiment_config(mp, _WK)

    st.write("")
    run_clicked = st.button("Run Simulation", key="btn_run", width="stretch")

    _render_save_ref_buttons("")

    if run_clicked:
        execute_simulation_flow(
            mp=mp, exp_config=exp_config, var_keys=var_keys, var_labels=var_labels,
            tmax=tmax, h=h, ref_code=ref_code, dark=dark,
            energy_tariff=energy_tariff,
        )

    _toast = st.session_state.pop("_sim_toast", None)
    if _toast:
        st.success(_toast)

    sr = st.session_state.get("sim_result")
    ref_list = st.session_state["ref_list"]
    render_ref_panel(ref_list)

    if sr is not None:
        render_results(
            res=sr["res"],
            var_keys=var_keys if var_keys else sr["var_keys"],
            var_labels=var_labels if var_labels else sr["var_labels"],
            dark=sr["dark"],
            t_events=sr["t_events"],
            mp=sr["mp"],
            exp_label=sr.get("exp_label", "Simulacao"),
            exp_type=sr.get("exp_type",   "dol"),
            decimals=dec,
            ref_list=ref_list,
            primary_color=None,
            is_mobile=is_mobile,
            energy_tariff=sr.get("energy_tariff", 0.75),
            exp_config=sr.get("exp_config"),
            torque_fn=sr.get("torque_fn"),
        )
    else:
        with st.container(border=True):
            st.markdown(
                "### No simulation has been run yet\n\n"
                "Configure the motor and experiment parameters above, "
                "then click **Run Simulation** to visualise:\n\n"
                "- Transient waveforms of current, torque and speed\n"
                "- Steady-state metrics (final speed, slip, efficiency)\n"
                "- Harmonic analysis (FFT) and diagnostics\n"
                "- Energy efficiency indicators and operational cost"
            )


# ─────────────────────────────────────────────────────────────────────────────
# THEORY TAB RENDERERS (one per machine)
# ─────────────────────────────────────────────────────────────────────────────

def _render_theory_dc(theory_containers: list) -> None:
    with theory_containers[0]:
        from ui.theory_dc import render_theory_dc_tab
        render_theory_dc_tab()


def _render_theory_mit(theory_containers: list) -> None:
    with theory_containers[0]:
        render_theory_tab()
    with theory_containers[1]:
        render_clean_view()


# ─────────────────────────────────────────────────────────────────────────────
# MACHINE REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class _MachineSpec:
    """Wiring for one machine type: tab labels + the two tab renderers.

    tab_labels[0] is always "Simulation"; the remaining labels are theory/extra
    tabs consumed by theory_renderer (in order).
    """
    tab_labels:      list[str]
    sim_renderer:    Callable[[bool, bool, int], None]
    theory_renderer: Callable[[list], None]


_MACHINE_REGISTRY: dict[str, _MachineSpec] = {
    "dc": _MachineSpec(
        tab_labels=["Simulation", "DC Machine Theory"],
        sim_renderer=_render_sim_tab_dc,
        theory_renderer=_render_theory_dc,
    ),
    "mit": _MachineSpec(
        tab_labels=["Simulation", "Theory", "Article Visualization"],
        sim_renderer=_render_sim_tab_mit,
        theory_renderer=_render_theory_mit,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTRADOR
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    for key, val in MIT_SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val

    for k, v in DC_SESSION_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    _on_machine_switch()
    _init_default_preset()

    dark = st.session_state.get("dark_mode", False)
    apply_css(dark)

    st.markdown(
        '<div class="app-header">'
        '<div class="app-title">Web Simulation Infrastructure</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # detect machine via query param (before checking selected_machine)
    if "machine" in st.query_params and not st.session_state["selected_machine"]:
        st.session_state["selected_machine"] = st.query_params["machine"]

    if not st.session_state["selected_machine"]:
        render_machine_selector(dark)
        return

    col_back, col_title = st.columns([1, 9], vertical_alignment="center")
    with col_back:
        if st.button("Back", key="btn_back"):
            st.session_state["selected_machine"] = None
            st.session_state["sim_result"]        = None
            st.rerun()
    with col_title:
        machine_name = next(
            m["name"] for m in MACHINES
            if m["key"] == st.session_state["selected_machine"]
        )
        st.markdown(f"### {machine_name}")

    st.divider()

    selected_machine = st.session_state.get("selected_machine", "mit")
    spec = _MACHINE_REGISTRY.get(selected_machine, _MACHINE_REGISTRY["mit"])

    tabs = st.tabs(spec.tab_labels)
    tab_sim, theory_containers = tabs[0], list(tabs[1:])

    # ── SIMULATION TAB ────────────────────────────────────────────────────
    with tab_sim:
        # global controls — grouped on the left; last column absorbs remaining space
        ct1, ct2, ct3, _ = st.columns([1.2, 1.8, 1.2, 6])
        with ct1:
            st.toggle("Dark Mode", value=dark, key="dark_mode")
        with ct2:
            st.toggle("Lock Parameters", value=False, key="experiment_mode",
                      help="When enabled, disables the motor parameter fields (Rs, Rr, Xm, Xls, Xlr, p, J, B). Useful for comparing results by varying only the experiment (load, voltage, fault) without changing the machine.")
        with ct3:
            st.number_input("Decimal places", min_value=0, max_value=6, value=3, step=1, key="decimals")

        experiment_mode = st.session_state.get("experiment_mode", False)
        dec = int(st.session_state.get("decimals", 3))

        spec.sim_renderer(dark, experiment_mode, dec)

    # ── THEORY / EXTRA TABS ───────────────────────────────────────────────
    spec.theory_renderer(theory_containers)


if __name__ == "__main__":
    main()
