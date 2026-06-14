# -*- coding: utf-8 -*-
"""
IWS_UI.py
=========
Main Streamlit orchestrator — configures the page, initialises session_state,
and routes to tabs.

Responsibilities:
  - Configure page_config and session_state with default values
  - Render sidebar, header, and machine selector (MIT / DCM)
  - Instantiate MIT and DCM tabs and delegate to ui_components

Relationships:
  Imported by : (entry point — not imported by any project module)
  Imports     : ui.theme, ui.clean_view, ui_components.theory_view,
                ui_components.sim_config, ui_components.sim_results,
                ui_components.sim_runner, ui_components.sim_config_dc,
                ui_components.sim_results_dc, ui_components.sim_runner_dc

Extending:
  - To add a new machine type, create a new tab and matching
    sim_config_X / sim_results_X / sim_runner_X modules, following the
    same delegation pattern used for MIT and DCM.
"""

from __future__ import annotations

import streamlit as st

from ui.theme import apply_css, REF_COLORS, REF_DASHES
from core.constants import DC_SESSION_DEFAULTS
from ui.clean_view import render_clean_view
from viz.tim_eqcircuit import render_circuit as _render_circuit_eqcircuit_plotter

from ui_components.theory_view import render_theory_tab
from ui_components.tim_config import (
    MACHINES,
    _WK,
    _PRESETS,
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


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTRADOR
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _defaults = {
        "dark_mode":        False,
        "experiment_mode":  False,
        "selected_machine": None,
        "sim_result":       None,
        "ref_list":         [],
        "decimals":         3,
        "pdf_bytes":        None,
    }
    for key, val in _defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    for k, v in DC_SESSION_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Reset when switching machine
    _prev_machine = st.session_state.get("_prev_machine")
    _cur_machine  = st.session_state.get("selected_machine")
    if _prev_machine is not None and _prev_machine != _cur_machine:
        st.session_state["sim_result"] = None
        st.session_state["ref_list"]   = []
    st.session_state["_prev_machine"] = _cur_machine

    # Loads Krause preset automatically on first session run
    _KRAUSE_KEY = "Default — Krause 3 HP (2.2 kW / 12 N·m) 220 V/60 Hz"
    if "_preset_loaded" not in st.session_state:
        st.session_state["_preset_loaded"] = True
        _pdata = _PRESETS.get(_KRAUSE_KEY, {})
        _wk_map = {
            "Vl": _WK.Vl, "f": _WK.f, "Rs": _WK.Rs, "Rr": _WK.Rr,
            "input_mode": _WK.input_mode, "f_ref": _WK.f_ref,
            "Xm": _WK.Xm, "Xls": _WK.Xls, "Xlr": _WK.Xlr,
            "Rfe": _WK.Rfe, "p": _WK.p, "J": _WK.J, "B": _WK.B,
            "exp_type": _WK.exp_type, "Tl_final": _WK.Tl_final,
        }
        for field, widget_key in _wk_map.items():
            if field in _pdata:
                st.session_state[widget_key] = _pdata[field]

    # responsiveness via pure CSS — no viewport JS
    is_mobile = False

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
    if selected_machine == "dc":
        tab_sim, tab_teoria_dc = st.tabs(["Simulation", "DC Machine Theory"])
    else:
        tab_sim, tab_teoria, tab_clean = st.tabs(["Simulation", "Theory", "Article Visualization"])

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

        if selected_machine == "dc":
            # ── DC BRANCH ─────────────────────────────────────────────────
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

            _can_save_dc = (
                st.session_state["sim_result"] is not None
                and len(st.session_state["ref_list"]) < 5
            )
            dc1, dc2 = st.columns(2)
            with dc1:
                save_ref_dc = st.button("Save as Reference", key="btn_save_ref_dc",
                                        width="stretch", disabled=not _can_save_dc,
                                        help="Saves the current result for comparison (max. 5)")
            with dc2:
                clear_ref_dc = st.button("Clear References", key="btn_clear_ref_dc",
                                          width="stretch",
                                          disabled=not st.session_state["ref_list"],
                                          help="Removes all saved references")

            if save_ref_dc and _can_save_dc:
                new_ref_dc = dict(st.session_state["sim_result"])
                _idx_dc = len(st.session_state["ref_list"])
                new_ref_dc["color"] = REF_COLORS[_idx_dc % len(REF_COLORS)]
                new_ref_dc["dash"]  = REF_DASHES[_idx_dc % len(REF_DASHES)]
                st.session_state["ref_list"].append(new_ref_dc)
                st.rerun()
            if clear_ref_dc:
                st.session_state["ref_list"] = []
                st.rerun()

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

        else:
            # ── MIT BRANCH ────────────────────────────────────────────────
            # parameters + circuit
            col_params, col_circuit = st.columns([1, 1], gap="large")

            with col_params:
                mp, ref_code, energy_tariff = render_machine_params(dark, experiment_mode, _WK)

            with col_circuit:
                st.markdown('<p class="slabel">Single-Phase Equivalent Circuit</p>', unsafe_allow_html=True)
                _render_circuit(mp, dark)
                st.write("")
                exp_config, var_keys, var_labels, tmax, h = render_experiment_config(mp, _WK)

            # ── main CTA ──────────────────────────────────────────────────
            st.write("")
            run_clicked = st.button(
                "Run Simulation", key="btn_run",
                width="stretch",
            )

            _can_save = (
                st.session_state["sim_result"] is not None
                and len(st.session_state["ref_list"]) < 5
            )
            ba1, ba2 = st.columns(2)
            with ba1:
                save_ref = st.button(
                    "Save as Reference", key="btn_save_ref",
                    width="stretch",
                    disabled=not _can_save,
                    help="Saves the current result for comparison (max. 5)",
                )
            with ba2:
                clear_ref = st.button(
                    "Clear References", key="btn_clear_ref",
                    width="stretch",
                    disabled=not st.session_state["ref_list"],
                    help="Removes all saved references",
                )

            if save_ref and _can_save:
                new_ref = dict(st.session_state["sim_result"])
                _idx    = len(st.session_state["ref_list"])
                new_ref["color"] = REF_COLORS[_idx % len(REF_COLORS)]
                new_ref["dash"]  = REF_DASHES[_idx % len(REF_DASHES)]
                st.session_state["ref_list"].append(new_ref)
                st.rerun()
            if clear_ref:
                st.session_state["ref_list"] = []
                st.rerun()

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

    if selected_machine == "dc":
        # ── DC THEORY TAB ─────────────────────────────────────────────────
        with tab_teoria_dc:
            from ui.theory_dc import render_theory_dc_tab
            render_theory_dc_tab()
    else:
        # ── THEORY TAB ────────────────────────────────────────────────────
        with tab_teoria:
            render_theory_tab()

        # ── ARTICLE VISUALIZATION TAB ─────────────────────────────────────
        with tab_clean:
            render_clean_view()


if __name__ == "__main__":
    main()
