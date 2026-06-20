# -*- coding: utf-8 -*-
"""
tim_config.py
=============
Induction-machine selector, parameter inputs, presets, and experiment configuration widgets.

Responsibilities:
  - Render machine selector screen (render_machine_selector).
  - Render physical parameter inputs with lock/unlock experiment mode (render_machine_params).
  - Render experiment type and variable selection widgets (render_experiment_config).
  - Expose MACHINES, _WK, _PRESETS, and MIT_VAR_CATALOG for downstream consumers.

Relationships:
  Imported by : IWS_UI
  Imports     : core.tim.facade, core.tim.param_estimator,
                core.constants, data.machines_mit, ui.theme,
                ui_components.tim_runner, ui_components.tim_fault_ui

Sub-modules:
  tim_config_params.py  — parameter-source sub-renderers (Nameplate, IEEE, Manual, locked/editable)
  exp_renderers_tim.py  — nine _render_exp_* functions (one per experiment type)
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

import streamlit as st

from core.tim.facade import MachineParams
from core.constants import MIT_DEFAULTS
from data.experiment_modes import MIT_EXP_OPTIONS, MIT_CRITICAL_EVENTS
from data.machines_mit import MIT_PRESETS
from data.ui_labels import MACHINES
from data.variable_labels import MIT_VAR_MECANICAS, MIT_VAR_ELETRICAS, MIT_VAR_CATALOG
from ui_components.tim_fault_ui import render_imbalance_ui, render_broken_bar_ui
from ui.theme import _palette
from ui_components.tim_runner import calc_tmax_auto
from ui_components._shared_widgets import _pgroup, _ibox

# re-export render_machine_params so callers need only import from tim_config
from ui_components.tim_config_params import render_machine_params  # noqa: F401

from ui_components.exp_renderers_tim import (
    _render_exp_dol,
    _render_exp_yd,
    _render_exp_comp,
    _render_exp_soft,
    _render_exp_load_pulse,
    _render_exp_generator,
    _render_exp_shutdown,
    _render_exp_voltage_sag,
    _render_exp_braking,
)


# ─────────────────────────────────────────────────────────────────────────────
# LOGICAL FIELD → WIDGET KEY MAPPING
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class _WidgetKeys:
    # electrical parameters
    Vl:          str = "wi_Vl"
    f:           str = "wi_f"
    Rs:          str = "wi_Rs"
    Rr:          str = "wi_Rr"
    input_mode:  str = "wi_input_mode"
    f_ref:       str = "wi_f_ref"
    Xm:          str = "wi_Xm"      # reactance (Ω) in X mode
    Xls:         str = "wi_Xls"
    Xlr:         str = "wi_Xlr"
    Xm_L:        str = "wi_Xm_L"   # inductance (H) in L mode
    Xls_L:       str = "wi_Xls_L"
    Xlr_L:       str = "wi_Xlr_L"
    Rfe:         str = "wi_Rfe"
    p:           str = "wi_p"
    J:           str = "wi_J"
    B:           str = "wi_B"
    # experiment
    exp_type:     str = "exp_select"
    Tl_final:     str = "wi_Tl_final"
    t_load:      str = "wi_t_load"
    Tl_pulse:     str = "wi_Tl_pulse"
    Tl_pulse_abs: str = "wi_Tl_pulse_abs"
    t_pulse_on:   str = "wi_t_pulse_on"
    t_pulse_off:  str = "wi_t_pulse_off"
    Tl_mec:       str = "wi_Tl_mec"
    t_2_generator:  str = "wi_t_2_generator"
    tmax:         str = "wi_tmax"
    h:            str = "wi_h"
    # advanced models
    Rgrid:               str = "wi_Rgrid"
    Lgrid:               str = "wi_Lgrid"
    # Park reference frame (persisted for locked mode)
    ref_park:            str = "wi_ref_park"
    # digital twin and economic analysis
    broken_bar_severity: str = "wi_broken_bar_severity"
    energy_tariff:       str = "wi_energy_tariff"
    # voltage sag
    sag_magnitude: str = "wi_sag_magnitude"
    t_start_sag:   str = "wi_t_start_sag"
    t_duration_sag:str = "wi_t_duration_sag"
    sag_Tl:        str = "wi_sag_Tl"
    # nameplate estimator
    param_source: str = "wi_param_source"
    Pn_kW:        str = "wi_Pn_kW"
    N_nom:        str = "wi_N_nom"
    rend:         str = "wi_rend"
    fp_placa:     str = "wi_fp_placa"
    Ip_In:        str = "wi_Ip_In"
    Tp_Tn:        str = "wi_Tp_Tn"
    is_delta:     str = "wi_is_delta"
    # IEEE 112 estimator — physical tests
    ieee_split:    str = "wi_ieee_split"
    ieee_Xls_frac: str = "wi_ieee_Xls_frac"
    ieee_Pfw:      str = "wi_ieee_Pfw"
    ieee_V_dc:     str = "wi_ieee_V_dc"
    ieee_I_dc:     str = "wi_ieee_I_dc"
    ieee_Vl_nl:    str = "wi_ieee_Vl_nl"
    ieee_I_nl:     str = "wi_ieee_I_nl"
    ieee_P_nl:     str = "wi_ieee_P_nl"
    ieee_f_nl:     str = "wi_ieee_f_nl"
    ieee_Vl_lr:    str = "wi_ieee_Vl_lr"
    ieee_I_lr:     str = "wi_ieee_I_lr"
    ieee_P_lr:     str = "wi_ieee_P_lr"
    ieee_f_lr:     str = "wi_ieee_f_lr"
    # DOL — rated torque reference (used to compute starting-time KPI)
    Tl_nom_dol:    str = "wi_dol_Tl_nom"


_WK = _WidgetKeys()


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULTS AND PRESETS
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, float | int] = MIT_DEFAULTS

_PRESETS: dict[str, dict[str, Any]] = MIT_PRESETS

_KRAUSE_KEY = "Default — Krause 3 HP (2.2 kW / 12 N·m) 220 V/60 Hz"

_WK_PRESET_MAP: dict[str, str] = {
    "Vl": _WK.Vl, "f": _WK.f, "Rs": _WK.Rs, "Rr": _WK.Rr,
    "input_mode": _WK.input_mode, "f_ref": _WK.f_ref,
    "Xm": _WK.Xm, "Xls": _WK.Xls, "Xlr": _WK.Xlr,
    "Rfe": _WK.Rfe, "p": _WK.p, "J": _WK.J, "B": _WK.B,
    "exp_type": _WK.exp_type, "Tl_final": _WK.Tl_final,
}


def _init_default_preset() -> None:
    """Load Krause default preset into session_state on first run."""
    if "_preset_loaded" in st.session_state:
        return
    st.session_state["_preset_loaded"] = True
    pdata = _PRESETS.get(_KRAUSE_KEY, {})
    for field, widget_key in _WK_PRESET_MAP.items():
        if field in pdata:
            st.session_state[widget_key] = pdata[field]


def _tl_sugerido(mp: MachineParams) -> float:
    """Estimates rated motor torque from electrical parameters (s=5%)."""
    from ui_components.tim_config_params import _tl_sugerido as _tls
    return _tls(mp)


# ─────────────────────────────────────────────────────────────────────────────
# MACHINE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def render_machine_selector(dark: bool) -> None:
    """Equipment selection home screen."""
    _palette(dark)

    hc1, hc2 = st.columns([5, 2], vertical_alignment="center")
    with hc1:
        st.markdown("#### Select equipment")
    with hc2:
        st.toggle("Dark Mode", value=dark, key="dark_mode")

    available = [m for m in MACHINES if not m["disabled"]]

    if "machine" in st.query_params:
        st.session_state["selected_machine"] = st.query_params["machine"]

    c = _palette(dark)

    cols = st.columns(len(available), gap="small")
    for i, m in enumerate(available):
        with cols[i]:
            card_html = f"""
<div style="
    background:{c['surface']};
    border:1px solid {c['border']};
    border-radius:12px;
    padding:20px 16px 16px;
    text-align:center;
    min-height:160px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:8px;
">
  <div style="font-size:2.4rem;">{m['icon']}</div>
  <div style="font-weight:700;font-size:1.05rem;color:{c['text']}">{m['label']}</div>
  <div style="font-size:0.82rem;color:{c['muted']};line-height:1.4">{m['desc']}</div>
</div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            st.write("")
            if st.button(
                f"Select {m['label']}",
                key=f"btn_select_{m['id']}",
                use_container_width=True,
            ):
                st.session_state["selected_machine"] = m["id"]
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENT CONFIGURATION — public entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_experiment_config(
    mp: MachineParams,
    wk: _WidgetKeys = _WK,
) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    """Experiment, variable, and numerical parameter configuration.

    Args:
        mp: machine parameters already constructed.
        wk: widget key mapping (uses _WK singleton by default).

    Returns:
        (config, var_keys, var_labels, tmax, h)
    """
    st.markdown('<p class="slabel">Experiment</p>', unsafe_allow_html=True)

    exp_options = MIT_EXP_OPTIONS

    exp_label = st.selectbox("Experiment Type", list(exp_options.keys()), key=wk.exp_type)
    exp_type  = exp_options[exp_label]
    config: dict[str, Any] = {"exp_type": exp_type, "exp_label": exp_label}

    _pgroup("Load and Voltage Parameters")

    # Reference torque from loaded preset — ensures switching experiments doesn't reset to hardcoded 80 N·m.
    from ui_components.tim_config_params import _tl_sugerido
    _Tl_ref = float(st.session_state.get(wk.Tl_final, _tl_sugerido(mp)))
    st.caption(f"Estimated rated torque from electrical parameters (s = 5%): **{_tl_sugerido(mp):.2f} N·m**")

    _EXP_RENDERERS = {
        "dol":          _render_exp_dol,
        "yd":           _render_exp_yd,
        "comp":         _render_exp_comp,
        "soft":         _render_exp_soft,
        "load_pulse":  _render_exp_load_pulse,
        "generator":      _render_exp_generator,
        "shutdown":     _render_exp_shutdown,
        "voltage_sag":  _render_exp_voltage_sag,
        "braking":     _render_exp_braking,
    }
    h_def = _EXP_RENDERERS[exp_type](mp, config, _Tl_ref, wk)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── variable selection ──────────────────────────────────────────────
    st.write("")
    st.markdown('<p class="slabel">Variables for Visualization</p>', unsafe_allow_html=True)
    _pgroup("Mechanical Quantities")
    sel_mec = st.multiselect(
        "Mechanical quantities",
        options=list(MIT_VAR_MECANICAS.keys()),
        default=["Electromagnetic Torque  Tₑ  (N·m)", "Rotor Speed  n  (RPM)"],
        label_visibility="collapsed",
    )
    _pgroup("Electrical Quantities")
    sel_ele = st.multiselect(
        "Electrical quantities",
        options=list(MIT_VAR_ELETRICAS.keys()),
        default=["Phase A Current — Stator  iₐₛ  (A)"],
        label_visibility="collapsed",
    )
    selected_labels = sel_mec + sel_ele
    var_keys   = [MIT_VAR_CATALOG[v] for v in selected_labels]
    var_labels = list(selected_labels)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── time and step ─────────────────────────────────────────────────────
    st.write("")
    st.markdown('<p class="slabel">Simulation Numerical Parameters</p>', unsafe_allow_html=True)
    _pgroup("Total Time and Integration Step")

    if config.get("exp_type") == "shutdown" and "_t_end_shutdown" in config:
        _sd_hash = hashlib.md5(
            json.dumps([mp.J, mp.B, config.get("Tl_final"), config.get("t_cutoff")]).encode()
        ).hexdigest()
        if st.session_state.get("_sd_tmax_hash") != _sd_hash:
            st.session_state[wk.tmax] = round(float(config["_t_end_shutdown"]), 1)
            st.session_state["_sd_tmax_hash"] = _sd_hash

    tc1, tc2 = st.columns(2)
    with tc1:
        _tmax_auto = st.checkbox("Calculate tmax automatically (motor inertia)", value=True, key="wi_tmax_auto")
        tmax = st.number_input("Total time — $t_{max}$ (s)", min_value=0.001, max_value=3600.0, value=2.0, step=0.1, format="%.1f", key=wk.tmax, disabled=_tmax_auto)
        if _tmax_auto:
            tmax = 0.0  # sentinel: runner will compute the actual value

        _etype = config.get("exp_type", "")
        if _etype == "shutdown":
            _tmax_sug = round(float(config.get("_t_end_shutdown", config.get("t_cutoff", 1.5))), 1)
            st.caption(f"Set automatically: {_tmax_sug:.1f} s  (t_off + t_stop × 1.2 — analytical)")
            _tmax_auto_val = None
        else:
            _tmax_auto_val   = round(calc_tmax_auto(config, mp), 1)
            _t_acomo_preview = float(min(max(15.0 * mp.J, 2.0), 30.0))
            if _tmax_auto:
                st.caption(f"Automatic: **{_tmax_auto_val:.1f} s**  (events + {_t_acomo_preview:.1f} s mechanical settling, J={mp.J:.3f} kg·m²)")
            else:
                st.caption(f"Suggestion: ≥ {round(_tmax_auto_val - _t_acomo_preview + 0.5, 1):.1f} s  (last event + 0.5 s to reach steady state)")

        h = st.number_input("Integration step — $h$ (s)", min_value=0.000001, max_value=0.1, value=0.0001, step=0.000001, format="%.6f", key=wk.h)
        _tmax_display = _tmax_auto_val if (_tmax_auto and _tmax_auto_val is not None) else tmax
        n_steps = int(_tmax_display / h) if _tmax_display > 0 else 0
        st.caption(f"Total steps: {n_steps:,}")
        if n_steps > 100_000:
            st.warning("High number of steps. The simulation may take several seconds.")
        h_max_rec = 1.0 / (20.0 * mp.f)
        st.caption(f"Recommended h: ≤ {h_max_rec:.5f} s  (1/20 cycle at {mp.f:.0f} Hz)")
        if h > h_max_rec:
            st.warning(
                f"Step h={h:.5f} s exceeds the recommended limit "
                f"({h_max_rec:.5f} s for {mp.f:.0f} Hz). "
                "Reduce h to avoid numerical divergence."
            )

        _critical_raw = MIT_CRITICAL_EVENTS.get(_etype, [])
        if _etype == "dol":
            _tc_dol = config.get("t_load", 0)
            _critical = [("load application", r"t_{carga}", _tc_dol)] if _tc_dol > 0 else []
        else:
            _critical = [(lbl, sym, float(config.get(key, 0))) for lbl, sym, key in _critical_raw]
        if not _tmax_auto:
            for _lbl, _sym, _t in _critical:
                if _t >= tmax:
                    st.warning(
                        f"$t_{{max}}$ ({tmax:.2f} s) ≤ ${_sym}$ ({_t:.2f} s): "
                        f"the **{_lbl}** event will not occur in the simulation — increase $t_{{max}}$."
                    )
    with tc2:
        _ibox(
            "<strong>t<sub>max</sub>:</strong> the larger the value, the more of the transient is captured, but at higher "
            "computational cost.<br><br>"
            "<strong>h (step):</strong> the stability limit is h ≤ 1/(20·f). "
            "For f=60 Hz: h ≤ 0.00083 s. For higher frequencies, reduce h proportionally."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    render_imbalance_ui(config, tmax=tmax)
    render_broken_bar_ui(config, tmax=tmax, wk=wk)

    return config, var_keys, var_labels, tmax, h
