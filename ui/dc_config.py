# -*- coding: utf-8 -*-
"""
dc_config.py
================
DC machine selector, parameter inputs, and experiment configuration widgets.

Responsibilities:
  - Render DCM parameter selector by excitation type (render_dc_machine_params).
  - Render mode and variable selection for DCM experiments (render_experiment_config_dc).
  - Expose _PRESETS_BY_EXC with motor and generator presets keyed by excitation type.

Relationships:
  Imported by : IWS_UI
  Imports     : core.dc.facade, data.machines_dc,
                ui.dc_config_keys, ui.dc_config_params,
                ui.exp_renderers_dc

Sub-modules:
  dc_config_keys.py    — _WidgetKeysDC / _WK_DC / _wi (shared, cycle-free)
  dc_config_params.py  — parameter-source sub-renderers (Nameplate, IEEE, Manual)
  exp_renderers_dc.py      — six _render_exp_dc_* functions (one per experiment type)

Extending:
  - To add a new DCM preset, edit data/machines_dc.py — DC_PRESETS_BY_EXC dict.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.dc.facade import DCMachineParams
from data.machines_dc import DC_PRESETS_BY_EXC, DC_PRESETS_FLAT
from data.experiment_modes import (
    DC_MODES_BY_EXC,
    DC_MODE_LABELS,
    DC_EXC_LABELS,
)
from data.ui_labels import DC_PARAM_SOURCE_LABELS
from data.variable_labels import (
    DC_VAR_MECANICAS,
    DC_VAR_ELETRICAS,
    DC_VAR_OPTIONS,
    DC_DEFAULT_VARS_MEC,
    DC_DEFAULT_VARS_ELE,
    DC_DEFAULT_VARS,
)
from ui._shared_widgets import _pgroup, _ibox
from ui.dc_config_keys import _WidgetKeysDC, _WK_DC, _wi  # noqa: F401

# re-export parameter-source sub-renderers so callers need only import from dc_config
from ui.dc_config_params import (  # noqa: F401
    _render_dc_nameplate,
    _render_dc_ieee,
    _render_dc_manual_locked,
    _render_dc_manual_editable,
    _render_dc_manual,
    _PARAM_SOURCE_RENDERERS,
)
from ui.exp_renderers_dc import (  # noqa: F401
    _render_exp_dc_dol,
    _render_exp_dc_resistance,
    _render_exp_dc_braking,
    _render_exp_dc_field_weakening,
    _render_exp_dc_pulse,
    _render_exp_dc_generator,
    _EXP_RENDERERS_DC,
)


# ─────────────────────────────────────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────────────────────────────────────

_PRESETS_BY_EXC: dict[str, dict[str, dict[str, Any]]] = DC_PRESETS_BY_EXC
_PRESETS_DC: dict[str, dict[str, Any]] = DC_PRESETS_FLAT


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — MACHINE PARAMETERS (col_params) — public orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def render_dc_machine_params(dark: bool, experiment_mode: bool) -> tuple[DCMachineParams, int, float]:
    """Renders DC machine parameter selector.

    Returns (DCMachineParams, ref_code, energy_tariff).
    ref_code: integer hash for cache invalidation.
    energy_tariff: $/kWh tariff read from Advanced Parameters.
    """
    st.markdown('<p class="slabel">Machine Parameters</p>', unsafe_allow_html=True)

    # ── Automatic default preset load on first open ───────────────────────────
    if _WK_DC.Va not in st.session_state:
        _default_preset = _PRESETS_BY_EXC["sep_motor"]["Sep. Motor 220 V — Sen Ex. 9.2"]
        for k, v in _default_preset.items():
            st.session_state[f"wi_dc_{k}"] = v
        st.session_state[_WK_DC.excitation] = "sep_motor"
        st.session_state[_WK_DC.preset]     = "Sep. Motor 220 V — Sen Ex. 9.2"
        st.rerun()

    # ── Excitation configuration ──────────────────────────────────────────────
    _wi(_WK_DC.excitation, "sep_motor")
    exc_options   = list(DC_EXC_LABELS.keys())
    exc_labels    = [DC_EXC_LABELS[k] for k in exc_options]
    exc_stored    = st.session_state.get(_WK_DC.excitation, "sep_motor")
    exc_idx       = exc_options.index(exc_stored) if exc_stored in exc_options else 0
    exc_label_sel = st.selectbox(
        "Configuration", exc_labels, index=exc_idx,
        key="_dc_exc_sel", label_visibility="visible",
        disabled=experiment_mode,
    )
    exc = exc_options[exc_labels.index(exc_label_sel)]
    st.session_state[_WK_DC.excitation] = exc

    # ── Data source: Manual / Nameplate / Tests ───────────────────────────────
    _wi(_WK_DC.input_mode, DC_PARAM_SOURCE_LABELS[0])
    input_mode = st.radio(
        "Data source", DC_PARAM_SOURCE_LABELS,
        index=DC_PARAM_SOURCE_LABELS.index(
            st.session_state.get(_WK_DC.input_mode, DC_PARAM_SOURCE_LABELS[0])
        ),
        horizontal=True, key=_WK_DC.input_mode,
        disabled=experiment_mode,
    )

    # ── Estimator sub-renderers (nameplate / IEEE) — skip in experiment_mode ──
    if input_mode != DC_PARAM_SOURCE_LABELS[0] and not experiment_mode:
        _PARAM_SOURCE_RENDERERS[input_mode](exc)

    # ── Preset loader — only in manual mode ──────────────────────────────────
    if input_mode == DC_PARAM_SOURCE_LABELS[0]:
        if st.session_state.pop("_dc_reset_preset", False):
            st.session_state[_WK_DC.preset] = "— Select preset —"
        _presets_exc  = _PRESETS_BY_EXC.get(exc, {})
        _preset_names = ["— Select preset —"] + list(_presets_exc.keys())
        pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
        with pc1:
            preset_sel = st.selectbox(
                "Preset", _preset_names, key=_WK_DC.preset,
                label_visibility="collapsed",
                disabled=experiment_mode,
            )
        with pc2:
            if st.button("Load", key="btn_dc_load_preset", width="stretch",
                         disabled=(preset_sel == "— Select preset —" or experiment_mode)):
                ps = _presets_exc[preset_sel]
                _DIRECT_KEYS = {"_dc_mode_sel"}
                for k, v in ps.items():
                    if k in _DIRECT_KEYS:
                        st.session_state[k] = v
                    else:
                        st.session_state[f"wi_dc_{k}"] = v
                st.session_state["_dc_reset_preset"] = True
                st.rerun()

    _wi(_WK_DC.energy_tariff, 0.75)

    # ── Parameter input / display ─────────────────────────────────────────────
    p = _render_dc_manual(exc, experiment_mode, input_mode)

    mp = DCMachineParams(
        Va=p["va"], Ra=p["ra"], La=p["la"],
        Vf=p["vf"], Rf=p["rf"], Lf=p["lf"],
        Rl=p["rl"], Ll=p["ll"],
        J=p["J"], B=p["B"], kb=p["kb"],
        excitation=exc,
        Tload=p["Tload"],
    )

    ref_code      = hash((p["va"], p["ra"], p["la"], p["vf"], p["rf"], p["lf"],
                          p["rl"], p["ll"], p["J"], p["B"], p["kb"], exc, p["Tload"]))
    energy_tariff = float(st.session_state.get(_WK_DC.energy_tariff, 0.75))
    return mp, ref_code, energy_tariff


def _tl_sugerido_dc(mp: DCMachineParams) -> float:
    """Estimated rated torque: kb·ia_nominal, where ia_nominal = (Va-kb·wm_nom)/Ra."""
    try:
        wm_nom = mp.Tload if mp.Tload > 0 else mp.Va / mp.kb if mp.kb > 0 else 100.0
        ia_nom = (mp.Va - mp.kb * wm_nom) / mp.Ra if mp.Ra > 0 else mp.Va / mp.Ra
        return float(max(abs(mp.kb * ia_nom), 0.01))
    except Exception:
        return float(abs(mp.Tload)) if mp.Tload else 1.0


def _render_dc_var_selectors(config: dict) -> tuple[list[str], list[str]]:
    st.write("")
    st.markdown('<p class="slabel">Variables for Visualization</p>', unsafe_allow_html=True)
    _pgroup("Mechanical Quantities")
    sel_mec = st.multiselect(
        "Mechanical quantities",
        options=list(DC_VAR_MECANICAS.keys()),
        default=DC_DEFAULT_VARS_MEC,
        label_visibility="collapsed",
        key=_WK_DC.vars_mec,
    )
    _pgroup("Electrical Quantities")
    sel_ele = st.multiselect(
        "Electrical quantities",
        options=list(DC_VAR_ELETRICAS.keys()),
        default=DC_DEFAULT_VARS_ELE,
        label_visibility="collapsed",
        key=_WK_DC.vars_ele,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    selected_labels = sel_mec + sel_ele
    var_keys   = [DC_VAR_OPTIONS[v] for v in selected_labels if v in DC_VAR_OPTIONS]
    var_labels = [v for v in selected_labels if v in DC_VAR_OPTIONS]
    if not var_keys:
        var_keys   = DC_DEFAULT_VARS
        var_labels = [k for k, v in DC_VAR_OPTIONS.items() if v in DC_DEFAULT_VARS]
    return var_keys, var_labels


def _render_dc_numerical_params(
    config: dict, mode: str, mp: DCMachineParams, tmax_def: float, h_def: float
) -> tuple[float, float]:
    st.write("")
    st.markdown('<p class="slabel">Simulation Numerical Parameters</p>', unsafe_allow_html=True)
    _pgroup("Total Time and Integration Step")

    _t_acomo       = float(min(max(15.0 * mp.J, 2.0), 30.0))
    _tmax_auto_val = round(tmax_def + _t_acomo, 1)

    tc1, tc2 = st.columns(2)
    with tc1:
        _tmax_auto = st.checkbox("Calculate tmax automatically (motor inertia)", value=True, key=_WK_DC.tmax_auto)
        _wi(_WK_DC.tmax, tmax_def)
        tmax = st.number_input("Total time — $t_{max}$ (s)", min_value=0.001, max_value=3600.0,
                                value=tmax_def, step=0.1, format="%.1f",
                                key=_WK_DC.tmax, disabled=_tmax_auto)
        if _tmax_auto:
            tmax = 0.0  # sentinel: runner resolves
            st.caption(f"Automatic: **{_tmax_auto_val:.1f} s**  (mode + {_t_acomo:.1f} s mechanical settling, J={mp.J:.4f} kg·m²)")
        else:
            st.caption(f"Suggestion: ≥ {round(tmax_def + 0.5, 1):.1f} s  (last event + 0.5 s to reach steady state)")

        _wi(_WK_DC.h, h_def)
        h = st.number_input("Integration step — $h$ (s)", min_value=1e-6, max_value=0.1,
                             value=h_def, step=1e-4, format="%.6f", key=_WK_DC.h)

        _tmax_display = _tmax_auto_val if _tmax_auto else tmax
        n_steps = int(_tmax_display / h) if (_tmax_display > 0 and h > 0) else 0
        st.caption(f"Total steps: {n_steps:,}")
        if n_steps > 500_000:
            st.warning("High number of steps. The simulation may take several seconds.")

        if not _tmax_auto:
            _tmax_check   = tmax
            _critical_dc: list[tuple[str, str, float]] = []
            if mode == "dol_dc" and config.get("start_no_load"):
                _critical_dc = [("load application", "t_{load}", config.get("t_load", 0))]
            elif mode == "resistance_dc":
                _critical_dc = [("resistance removal", "t_{ramp}", config.get("t_ramp", 0))]
            elif mode == "braking_dc":
                _critical_dc = [("braking", "t_{brake}", config.get("t_freia", 0))]
            elif mode == "field_weakening_dc":
                _critical_dc = [("field weakening", "t_{field}", config.get("t_campo", 0))]
            elif mode == "pulse_dc":
                _critical_dc = [("load pulse", "t_{pulse}", config.get("t_pulso", 0))]
            for _lbl, _sym, _t in _critical_dc:
                if _t >= _tmax_check:
                    st.warning(
                        f"$t_{{max}}$ ({_tmax_check:.2f} s) ≤ ${_sym}$ ({_t:.2f} s): "
                        f"the **{_lbl}** event will not occur in the simulation — increase $t_{{max}}$."
                    )

    with tc2:
        _ibox(
            "<strong>t<sub>max</sub>:</strong> the larger the value, the more of the transient is captured, "
            "but at higher computational cost.<br><br>"
            "<strong>h (step):</strong> for DC machines, recommended h ≤ τ<sub>a</sub>/10, "
            "where τ<sub>a</sub> = L<sub>a</sub>/R<sub>a</sub> is the armature electrical time constant."
        )

    config["_tmax_auto_val"] = _tmax_auto_val
    return float(tmax), float(h)


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — EXPERIMENT (lower col_circuit) — public orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def render_experiment_config_dc(
    mp: DCMachineParams,
    _wk: Any = None,
) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    """Renders DC machine mode selector and experiment parameters.

    Returns (exp_config, var_keys, var_labels, tmax, h).
    """
    st.markdown('<p class="slabel">Experiment</p>', unsafe_allow_html=True)

    exc            = mp.excitation
    available_modes = DC_MODES_BY_EXC.get(exc, ["dol_dc"])
    mode_labels    = [DC_MODE_LABELS[m] for m in available_modes]

    mode_sel_label = st.selectbox(
        "Experiment Type", mode_labels, index=0, key="_dc_mode_sel",
        label_visibility="visible",
    )
    mode_sel_label = st.session_state.get("_dc_mode_sel", mode_labels[0])
    mode = available_modes[mode_labels.index(mode_sel_label)] if mode_sel_label in mode_labels else available_modes[0]

    exp_config: dict[str, Any] = {"exp_type": mode, "exp_label": DC_MODE_LABELS[mode]}

    _pgroup("Load and Voltage Parameters")
    _Tl_ref = float(st.session_state.get(_WK_DC.Tload, mp.Tload))
    exp_config["_Tl_ref"] = _Tl_ref
    st.caption(f"Configured load torque: **{_Tl_ref:.3f} N·m** | τ_a = L_a/R_a = {mp.La/mp.Ra:.4f} s")

    renderer = _EXP_RENDERERS_DC.get(mode)
    if renderer is not None:
        tmax_def, h_def = renderer(mp, exp_config)
    else:
        tmax_def, h_def = 12.0, 1e-3

    st.markdown('</div>', unsafe_allow_html=True)

    var_keys, var_labels = _render_dc_var_selectors(exp_config)
    tmax, h = _render_dc_numerical_params(exp_config, mode, mp, tmax_def, h_def)

    _ibox(f"<strong>Mode:</strong> {DC_MODE_LABELS[mode]} &nbsp;|&nbsp; "
          f"<strong>Excitation:</strong> {DC_EXC_LABELS.get(exc, exc)}")

    return exp_config, var_keys, var_labels, tmax, h
