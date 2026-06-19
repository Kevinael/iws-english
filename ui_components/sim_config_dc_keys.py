# -*- coding: utf-8 -*-
"""
sim_config_dc_keys.py
=====================
Shared widget-key registry and session-state helper for the DC configuration
modules. Lives in a neutral module so the orchestrator (sim_config_dc.py) and
its sub-renderers (sim_config_dc_params.py, exp_renderers_dc.py) can all import
_WK_DC / _wi without creating an import cycle.

Relationships:
  Imported by : ui_components.sim_config_dc, ui_components.sim_config_dc_params,
                ui_components.exp_renderers_dc
  Imports     : streamlit
"""

from __future__ import annotations

import dataclasses
from typing import Any

import streamlit as st


@dataclasses.dataclass(frozen=True)
class _WidgetKeysDC:
    # machine parameters
    Va:            str = "wi_dc_Va"
    Ra:            str = "wi_dc_Ra"
    La:            str = "wi_dc_La"
    kb:            str = "wi_dc_kb"
    Vf:            str = "wi_dc_Vf"
    Rf:            str = "wi_dc_Rf"
    Lf:            str = "wi_dc_Lf"
    Rl:            str = "wi_dc_Rl"
    Ll:            str = "wi_dc_Ll"
    J:             str = "wi_dc_J"
    B:             str = "wi_dc_B"
    Tload:         str = "wi_dc_Tload"
    # selector / mode
    excitation:    str = "wi_dc_excitation"
    preset:        str = "wi_dc_preset"
    input_mode:    str = "wi_dc_input_mode"
    # nameplate estimator
    Pn_kW:         str = "wi_dc_Pn_kW"
    Vn_placa:      str = "wi_dc_Vn_placa"
    nn_rpm:        str = "wi_dc_nn_rpm"
    eta_placa:     str = "wi_dc_eta_placa"
    # DC resistance tests
    V_dc_test:     str = "wi_dc_V_dc_test"
    I_dc_test:     str = "wi_dc_I_dc_test"
    V_dc_f_test:   str = "wi_dc_V_dc_f_test"
    I_dc_f_test:   str = "wi_dc_I_dc_f_test"
    # AC inductance tests
    V_ac_test:     str = "wi_dc_V_ac_test"
    I_ac_test:     str = "wi_dc_I_ac_test"
    theta_test:    str = "wi_dc_theta_test"
    f_ac_test:     str = "wi_dc_f_ac_test"
    # field step / no-load tests
    tau_f_ms_test: str = "wi_dc_tau_f_ms_test"
    V_nl_test:     str = "wi_dc_V_nl_test"
    I_nl_test:     str = "wi_dc_I_nl_test"
    If_nl_test:    str = "wi_dc_If_nl_test"
    n_nl_test:     str = "wi_dc_n_nl_test"
    # economics
    energy_tariff: str = "wi_dc_energy_tariff"
    # experiment — DOL
    dol_vazio:     str = "wi_dc_dol_vazio"
    dol_t_carga:   str = "wi_dc_dol_t_carga"
    # experiment — series resistance
    R_ini:         str = "wi_dc_R_ini"
    t_ramp:        str = "wi_dc_t_ramp"
    # experiment — braking
    brake_method:  str = "wi_dc_brake_method"
    t_freia:       str = "wi_dc_t_freia"
    Vdc_inj:       str = "wi_dc_Vdc_inj"
    Va_regen:      str = "wi_dc_Va_regen"
    # experiment — field weakening
    Vf_fraco:      str = "wi_dc_Vf_fraco"
    t_campo:       str = "wi_dc_t_campo"
    t_trans:       str = "wi_dc_t_trans"
    # experiment — load pulse
    t_pulso:       str = "wi_dc_t_pulso"
    Tl_extra:      str = "wi_dc_Tl_extra"
    # experiment — generator
    Tl_gen:        str = "wi_dc_Tl_gen"
    # variable selection
    vars_mec:      str = "wi_dc_vars_mec"
    vars_ele:      str = "wi_dc_vars_ele"
    # simulation settings
    tmax_auto:     str = "wi_dc_tmax_auto"
    tmax:          str = "wi_dc_tmax"
    h:             str = "wi_dc_h"


_WK_DC = _WidgetKeysDC()


def _wi(key: str, default: Any) -> None:
    """Initializes session_state if absent."""
    if key not in st.session_state:
        st.session_state[key] = default
