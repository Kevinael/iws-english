# -*- coding: utf-8 -*-
"""
constants.py
============
Central repository for numeric constants, solver tuning parameters,
and machine default values used across the IWS simulator.

Responsibilities:
  - Expose solver tolerances and step-size limits (SOLVER_*).
  - Expose default parameter dicts for MIT and DC machines.
  - Single source of truth — no magic numbers scattered across modules.

Relationships:
  Imported by : core.solver, ui_components.sim_config, IWS_UI
  Imports     : (none)

Extending:
  - To add defaults for a new machine type, add a _DEFAULTS_<TYPE> dict
    and document the units in a comment block.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# SOLVER CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SOLVER_SS_TOL          = 0.005   # relative ωr tolerance to declare steady state (0.5 %)
SOLVER_MIN_SS_CYCLES   = 5       # minimum consecutive electrical cycles in steady state
SOLVER_NYQUIST_LIMIT   = 0.05    # max h·f — below 20 samples/cycle RMS becomes imprecise
SOLVER_F_ROTOR_FLOOR   = 0.01    # Hz — f_rotor floor to avoid astronomical LCM at s ≈ 0
SOLVER_RTOL            = 1e-6    # LSODA relative tolerance
SOLVER_ATOL            = 1e-9    # LSODA absolute tolerance (Wb, rad/s)
SOLVER_MAX_STEP_FACTOR = 20.0    # max_step = 1 / (20·f) → ≥ 20 samples/cycle


# ═══════════════════════════════════════════════════════════════════════════
# MIT DEFAULT PARAMETERS   (Krause 3 HP — 2.2 kW / 220 V / 60 Hz)
# ═══════════════════════════════════════════════════════════════════════════
# Units: Vl [V], f [Hz], resistances [Ω], reactances [Ω] at f,
#        p [pole pairs], J [kg·m²], B [N·m·s/rad]

MIT_DEFAULTS: dict[str, float | int] = dict(
    Vl=220.0, f=60.0,
    Rs=0.435, Rr=0.816,
    Xm=26.13, Xls=0.754, Xlr=0.754,
    Rfe=500.0,
    p=4, J=0.089, B=0.005,
)


# ═══════════════════════════════════════════════════════════════════════════
# DC MACHINE DEFAULT SESSION-STATE VALUES
# ═══════════════════════════════════════════════════════════════════════════
# Keys match st.session_state widget keys used in sim_config_dc.py.
# Units: voltages [V], resistances [Ω], inductances [H],
#        J [kg·m²], B [N·m·s/rad], Tload [N·m]

DC_SESSION_DEFAULTS: dict[str, object] = {
    "wi_dc_Va":         24.0,
    "wi_dc_Ra":         0.013,
    "wi_dc_La":         0.01,
    "wi_dc_Vf":         12.0,
    "wi_dc_Rf":         1.43,
    "wi_dc_Lf":         0.167,
    "wi_dc_Rl":         0.0,
    "wi_dc_Ll":         0.0,
    "wi_dc_kb":         0.004,
    "wi_dc_J":          0.21,
    "wi_dc_B":          1.074e-6,
    "wi_dc_Tload":      2.493,
    "wi_dc_excitation": "sep_motor",
}
