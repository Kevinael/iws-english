# -*- coding: utf-8 -*-
"""
session_schema.py
=================
TypedDict definitions for all st.session_state keys used by IWS.

These types are documentation-only — Streamlit does not enforce them at
runtime. They exist to enable static analysis (mypy/pyright) and to
provide a single authoritative list of the 26+ keys scattered across
IWS_UI, ui_components, and viz modules.

Usage:
    from core.session_schema import MITSession, DCSession

Initialization helpers (runtime dicts with actual defaults):
    from core.constants import MIT_SESSION_DEFAULTS, DC_SESSION_DEFAULTS
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict, NotRequired


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL / SHARED KEYS
# ─────────────────────────────────────────────────────────────────────────────

class GlobalSession(TypedDict, total=False):
    """Keys shared by both MIT and DC machines."""
    dark_mode:         bool          # current theme; toggled in render_machine_selector
    selected_machine:  Optional[str] # "mit" | "dc" | None (home screen)
    experiment_mode:   bool          # locks all parameter inputs
    ref_list:          list          # list of saved reference simulation results
    decimals:          int           # display precision for numeric outputs
    pdf_bytes:         Optional[bytes]
    _prev_machine:     Optional[str] # previous selected_machine (for on-switch reset)


# ─────────────────────────────────────────────────────────────────────────────
# MIT (Three-Phase Induction Motor) KEYS
# ─────────────────────────────────────────────────────────────────────────────

class MITSession(GlobalSession):
    """All session_state keys for the MIT simulation tab."""
    # simulation output
    sim_result:        Optional[dict[str, Any]]

    # zoom / view state
    zoom_mode:         str   # "Full" | "Startup" | custom

    # preset loading flags
    _preset_loaded:    bool
    _reset_preset_select: bool
    _param_source_idx: int   # 0=Manual, 1=Nameplate, 2=IEEE

    # electrical parameter widgets (_WK.* keys)
    wi_Vl:         float
    wi_f:          float
    wi_Rs:         float
    wi_Rr:         float
    wi_input_mode: str
    wi_f_ref:      float
    wi_Xm:         float
    wi_Xls:        float
    wi_Xlr:        float
    wi_Xm_L:       float
    wi_Xls_L:      float
    wi_Xlr_L:      float
    wi_Rfe:        float
    wi_p:          int
    wi_J:          float
    wi_B:          float
    wi_Rgrid:      float
    wi_Lgrid:      float
    wi_ref_park:   str
    wi_energy_tariff: float

    # experiment widgets
    exp_select:            str
    wi_Tl_final:           float
    wi_t_carga:            float
    wi_Tl_pulso:           float
    wi_Tl_pulso_abs:       float
    wi_t_pulso_on:         float
    wi_t_pulso_off:        float
    wi_Tl_mec:             float
    wi_t_2_gerador:        float
    wi_tmax:               float
    wi_h:                  float
    wi_tmax_auto:          bool
    wi_dol_Tl_nom:         float
    wi_dol_partir_vazio:   bool
    wi_dol_pct_fin:        float

    # voltage sag
    wi_sag_magnitude:  float
    wi_t_start_sag:    float
    wi_t_duration_sag: float
    wi_sag_Tl:         float

    # nameplate estimator
    wi_param_source: str
    wi_Pn_kW:   float
    wi_N_nom:   float
    wi_rend:    float
    wi_fp_placa: float
    wi_Ip_In:   float
    wi_Tp_Tn:   float
    wi_is_delta: bool

    # IEEE 112 estimator
    wi_ieee_split:    str
    wi_ieee_Xls_frac: float
    wi_ieee_Pfw:      float
    wi_ieee_V_dc:     float
    wi_ieee_I_dc:     float
    wi_ieee_Vl_nl:    float
    wi_ieee_I_nl:     float
    wi_ieee_P_nl:     float
    wi_ieee_f_nl:     float
    wi_ieee_Vl_lr:    float
    wi_ieee_I_lr:     float
    wi_ieee_P_lr:     float
    wi_ieee_f_lr:     float

    # braking
    wi_brake_method:  str
    wi_brake_t_freia: float
    wi_brake_Vcc_inj: float
    wi_brake_V_regen: int

    # shutdown auto-tmax hash
    _sd_tmax_hash: str

    # broken bar
    wi_broken_bar_severity: float


# ─────────────────────────────────────────────────────────────────────────────
# DC MACHINE (Motor Corrente Contínua) KEYS
# ─────────────────────────────────────────────────────────────────────────────

class DCSession(GlobalSession):
    """All session_state keys for the DC machine simulation tab."""
    # simulation output
    dc_sim_result:  Optional[dict[str, Any]]

    # zoom / view state
    zoom_mode_dc:   str

    # parameter widgets
    wi_dc_Va:          float
    wi_dc_Ra:          float
    wi_dc_La:          float
    wi_dc_Vf:          float
    wi_dc_Rf:          float
    wi_dc_Lf:          float
    wi_dc_Rl:          float
    wi_dc_Ll:          float
    wi_dc_kb:          float
    wi_dc_J:           float
    wi_dc_B:           float
    wi_dc_Tload:       float
    wi_dc_excitation:  str   # "sep_motor" | "shunt_motor" | "series_motor" | ...

    # preset flags
    _dc_reset_preset:  bool
