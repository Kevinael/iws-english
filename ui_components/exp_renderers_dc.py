# -*- coding: utf-8 -*-
"""
exp_renderers_dc.py
===================
Experiment sub-renderers for the DC machine — one _render_exp_dc_* function per
experiment type (DOL, series resistance, braking, field weakening, load pulse,
generator).

Responsibilities:
  - Render mode-specific experiment widgets and write them into the config dict.
  - Return (tmax_def, h_def) suggestions for the numerical-parameters block.
  - Expose _EXP_RENDERERS_DC dispatch table for the orchestrator.

Relationships:
  Imported by : ui_components.sim_config_dc
  Imports     : core.dc.facade, data.experiment_modes,
                ui_components.sim_config_dc_keys, ui_components._shared_widgets
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.dc.facade import DCMachineParams
from data.experiment_modes import DC_BRAKE_LABELS
from ui_components.sim_config_dc_keys import _WK_DC, _wi
from ui_components._shared_widgets import _ibox


def _render_exp_dc_dol(mp: DCMachineParams, config: dict) -> tuple[float, float]:
    tmax_def = 12.0
    h_def    = 1e-3
    _Tl_ref  = config["_Tl_ref"]
    start_no_load = st.checkbox(
        "Start unloaded (apply load after starting)",
        value=True, key=_WK_DC.dol_vazio,
        help="When active, the motor starts unloaded and receives torque at t_load. "
             "When inactive, the load is present from time zero.",
    )
    config["start_no_load"] = start_no_load
    if start_no_load:
        _wi(_WK_DC.dol_t_load, 2.0)
        config["t_load"] = st.number_input(
            "Load application instant — $t_{load}$ (s)",
            min_value=0.0, key=_WK_DC.dol_t_load, format="%.2f",
        )
        config["Tl_inicial"] = 0.0
        config["Tl_final"]   = _Tl_ref
        tmax_def = max(config["t_load"] + 8.0, 12.0)
        _ibox(
            f"<strong>t = 0 s</strong> — rated voltage ({mp.Va:.1f} V) applied; "
            f"motor accelerates unloaded (T<sub>l</sub> = 0).<br>"
            f"<strong>t = {config['t_load']:.2f} s</strong> — load of "
            f"<strong>{_Tl_ref:.3f} N·m</strong> applied to shaft; "
            f"motor settles to new steady-state operating point."
        )
    else:
        config["Tl_inicial"] = None
        config["Tl_final"]   = _Tl_ref
        config["t_load"]    = 0.0
        _ibox(
            f"<strong>t = 0 s</strong> — rated voltage ({mp.Va:.1f} V) and load of "
            f"<strong>{_Tl_ref:.3f} N·m</strong> applied simultaneously; "
            f"motor starts against full load and accelerates to steady state."
        )
    return tmax_def, h_def


def _render_exp_dc_resistance(mp: DCMachineParams, config: dict) -> tuple[float, float]:
    _Tl_ref = config["_Tl_ref"]
    c1, c2  = st.columns(2)
    _wi(_WK_DC.R_ini, 5.0)
    _wi(_WK_DC.t_ramp, 2.0)
    config["R_ini"]    = c1.number_input("$R_{ini}$ (Ω)", min_value=0.0, key=_WK_DC.R_ini,  format="%.2f")
    config["t_ramp"]   = c2.number_input("$t_{ramp}$ (s)", min_value=0.1, key=_WK_DC.t_ramp, format="%.2f")
    config["Tl_final"] = _Tl_ref
    tmax_def = config["t_ramp"] + 8.0
    h_def    = 1e-3
    _ibox(
        f"<strong>t = 0 s</strong> — motor starts with series resistance of "
        f"<strong>{config['R_ini']:.2f} Ω</strong> limiting starting current.<br>"
        f"<strong>t = {config['t_ramp']:.2f} s</strong> — resistance removed (short-circuited); "
        f"motor accelerates to steady state with load of {_Tl_ref:.3f} N·m."
    )
    return tmax_def, h_def


_BRAKE_DESC_DC: dict[str, str] = {
    "plugging":    "Reverses the armature voltage polarity while the motor is still rotating. "
                   "Produces torque opposing motion — very fast braking, but with high "
                   "armature current and possible direction reversal if no stopping switch is provided.",
    "dc_injection":  "Cuts the operating supply and injects a reduced DC voltage into the armature. "
                   "The maintained field flux produces braking torque without reversing direction. "
                   "Smooth and controlled braking — current limited by armature resistance.",
    "regenerative":"Reduces armature voltage below the motor back-EMF. Armature current "
                   "reverses — the motor operates as a generator, returning energy to the source. "
                   "Gentle braking; effective only for high-inertia or high-speed loads.",
}


def _render_exp_dc_braking(mp: DCMachineParams, config: dict) -> tuple[float, float]:
    _Tl_ref      = config["_Tl_ref"]
    brake_labels = list(DC_BRAKE_LABELS.values())
    brake_keys   = list(DC_BRAKE_LABELS.keys())
    _wi(_WK_DC.brake_method, brake_labels[0])
    brake_sel = st.selectbox(
        "Braking Method", brake_labels,
        index=brake_labels.index(st.session_state.get(_WK_DC.brake_method, brake_labels[0])),
        key=_WK_DC.brake_method,
    )
    brake = brake_keys[brake_labels.index(brake_sel)]
    config["brake_method"] = brake
    config["Tl_final"]     = _Tl_ref
    st.info(_BRAKE_DESC_DC[brake])

    if brake == "plugging":
        _wi(_WK_DC.t_freia, 3.0)
        config["t_freia"] = st.number_input(
            "Reversal instant — $t_{brake}$ (s)", min_value=0.1,
            key=_WK_DC.t_freia, format="%.2f",
        )
        tmax_def = config["t_freia"] * 2.5
        _ibox(
            f"<strong>t = 0 s</strong> — motor starts in positive direction with load {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {config['t_freia']:.2f} s</strong> — armature polarity reversed; "
            f"braking torque opposes motion; rotor decelerates and reverses direction."
        )

    elif brake == "dc_injection":
        c1, c2 = st.columns(2)
        _wi(_WK_DC.t_freia,  3.0)
        _wi(_WK_DC.Vdc_inj,  mp.Va * 0.1)
        config["t_freia"] = c1.number_input(
            "Cut-off instant — $t_{brake}$ (s)", min_value=0.1,
            key=_WK_DC.t_freia, format="%.2f",
        )
        config["Vdc_inj"] = c2.number_input(
            "Injected DC voltage — $V_{inj}$ (V)", min_value=0.0,
            key=_WK_DC.Vdc_inj, format="%.2f",
            help="DC voltage applied to the armature after supply cut. Typically 5–15% of Va.",
        )
        tmax_def = config["t_freia"] * 2.5
        _ibox(
            f"<strong>t = 0 s</strong> — motor operates in steady state with load {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {config['t_freia']:.2f} s</strong> — supply cut; "
            f"DC voltage of <strong>{config['Vdc_inj']:.2f} V</strong> injected into armature; "
            f"current produces torque opposing motion — controlled braking without reversal."
        )

    elif brake == "regenerative":
        c1, c2 = st.columns(2)
        _wi(_WK_DC.t_freia,  3.0)
        _wi(_WK_DC.Va_regen, mp.Va * 0.5)
        config["t_freia"]  = c1.number_input(
            "Braking instant — $t_{brake}$ (s)", min_value=0.1,
            key=_WK_DC.t_freia, format="%.2f",
        )
        config["Va_regen"] = c2.number_input(
            "Reduced armature voltage — $V_{a,regen}$ (V)", min_value=0.0,
            key=_WK_DC.Va_regen, format="%.2f",
            help="Voltage below back-EMF — motor operates as generator returning energy.",
        )
        tmax_def = config["t_freia"] * 2.5
        _ibox(
            f"<strong>t = 0 s</strong> — motor operates in steady state with load {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {config['t_freia']:.2f} s</strong> — armature voltage reduced to "
            f"<strong>{config['Va_regen']:.2f} V</strong> (below back-EMF); "
            f"current reverses — motor operates as generator, returning energy to source."
        )

    else:
        tmax_def = 12.0

    return tmax_def, 1e-3


def _render_exp_dc_field_weakening(mp: DCMachineParams, config: dict) -> tuple[float, float]:
    _Tl_ref    = config["_Tl_ref"]
    c1, c2, c3 = st.columns(3)
    _wi(_WK_DC.Vf_fraco, mp.Vf * 0.5 if mp.Vf > 0 else mp.Va * 0.5)
    _wi(_WK_DC.t_campo,  3.0)
    _wi(_WK_DC.t_trans,  0.5)
    config["Vf_fraco"] = c1.number_input("$V_f$ weakened (V)", min_value=0.0,
                                          key=_WK_DC.Vf_fraco, format="%.2f")
    config["t_campo"]  = c2.number_input("$t_{field}$ (s)", min_value=0.1,
                                          key=_WK_DC.t_campo, format="%.2f")
    config["t_trans"]  = c3.number_input("$t_{trans}$ (s)", min_value=0.05,
                                          key=_WK_DC.t_trans, format="%.2f")
    config["Tl_final"] = _Tl_ref
    tmax_def = config["t_campo"] + 10.0
    _ibox(
        f"<strong>t = 0 s</strong> — motor operates at rated field; load {_Tl_ref:.3f} N·m.<br>"
        f"<strong>t = {config['t_campo']:.2f} s</strong> — field voltage reduced to "
        f"<strong>{config['Vf_fraco']:.2f} V</strong> (field weakening); "
        f"flux drops, speed increases to maintain power — {config['t_trans']:.2f} s transient."
    )
    return tmax_def, 1e-3


def _render_exp_dc_pulse(mp: DCMachineParams, config: dict) -> tuple[float, float]:
    _Tl_ref = config["_Tl_ref"]
    c1, c2  = st.columns(2)
    _wi(_WK_DC.t_pulso,  4.0)
    _wi(_WK_DC.Tl_extra, _Tl_ref * 0.5)
    config["t_pulso"]  = c1.number_input("Pulse instant — $t_{pulse}$ (s)", min_value=0.1, key=_WK_DC.t_pulso,  format="%.2f")
    config["Tl_extra"] = c2.number_input("Additional $\\Delta T_l$ (N·m)", min_value=0.0, key=_WK_DC.Tl_extra, format="%.3f")
    config["Tl_final"] = _Tl_ref
    tmax_def = config["t_pulso"] + 8.0
    _ibox(
        f"<strong>t = 0 s</strong> — motor operates in steady state with load {_Tl_ref:.3f} N·m.<br>"
        f"<strong>t = {config['t_pulso']:.2f} s</strong> — additional load pulse of "
        f"<strong>{config['Tl_extra']:.3f} N·m</strong> applied; motor decelerates and settles.<br>"
        f"<strong>t = {config['t_pulso']*2:.2f} s</strong> — pulse removed; motor recovers steady-state speed."
    )
    return tmax_def, 1e-3


def _render_exp_dc_generator(mp: DCMachineParams, config: dict) -> tuple[float, float]:
    _wi(_WK_DC.Tl_gen, abs(mp.Tload))
    config["Tl_gen"] = st.number_input("Prime mover torque — $T_{mec}$ (N·m)", min_value=0.0, key=_WK_DC.Tl_gen, format="%.3f")
    _ibox(
        f"<strong>t = 0 s</strong> — machine accelerated by prime mover with torque of "
        f"<strong>{config['Tl_gen']:.3f} N·m</strong>; field excited.<br>"
        f"<strong>Steady state</strong> — terminal voltage $V_t$ stabilizes; resistive load $R_L$ receives generated power."
    )
    return 15.0, 1e-3


_EXP_RENDERERS_DC: dict[str, Any] = {
    "dol_dc":          _render_exp_dc_dol,
    "resistance_dc":  _render_exp_dc_resistance,
    "braking_dc":     _render_exp_dc_braking,
    "field_weakening_dc":  _render_exp_dc_field_weakening,
    "pulse_dc":        _render_exp_dc_pulse,
    "generator_dc":      _render_exp_dc_generator,
}
