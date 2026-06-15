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
# PROTECTION & THERMAL THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

STARTING_SPEED_THRESHOLD    = 0.95   # fraction of synchronous speed (95 %) for starting-time KPI
SPEED_RECOVERY_THRESHOLD    = 0.90   # fraction of pre-fault synchronous speed for recovery check
GEN_EFFICIENCY_FALLBACK     = 0.90   # generator mechanical-to-electrical efficiency when unmeasured

# Slip thresholds (motor overload / underload / generator — NEMA B reference)
SLIP_OVERLOAD_ERROR         = 0.08   # > 8 %: severe overload
SLIP_OVERLOAD_WARN          = 0.05   # > 5 %: moderate overload
SLIP_UNDERLOAD              = 0.005  # < 0.5 %: severe underload
SLIP_GEN_WARN               = 0.05   # negative slip > 5 %: generator warning
SLIP_GEN_ERROR              = 0.10   # negative slip > 10 %: generator error (unstable)

# Voltage Unbalance Factor thresholds (NEMA MG-1 §14.35)
VUF_DETECTABLE_MIN_PCT      = 0.3    # below this VUF: no diagnostic issued [%]
VUF_ERROR_PCT               = 5.0    # VUF ≥ 5 %: severe imbalance / error [%]
VUF_WARN_HIGH_PCT           = 2.0    # VUF ≥ 2 %: warning — efficiency loss [%]
VUF_WARN_LOW_PCT            = 1.0    # VUF ≥ 1 %: alert zone (NEMA MG-1 limit) [%]

# Broken bar severity index thresholds (α = sideband / fundamental ratio)
BBAR_ALPHA_ERROR            = 0.5    # α ≥ 0.5: severe fault
BBAR_ALPHA_WARN             = 0.2    # α ≥ 0.2: moderate fault

# Voltage sag severity thresholds [%]
SAG_ERROR_PCT               = 50.0   # sag ≥ 50 %: critical voltage sag
SAG_WARN_PCT                = 20.0   # sag ≥ 20 %: warning voltage sag

# Starting time relay class limits [s] (IEC 60947-4-1 / NEMA)
RELAY_CLASS_30_S            = 30.0   # Class 30 upper limit [s]
RELAY_CLASS_10_S            = 10.0   # IEC 60947-4-1 Class 10 upper limit [s]
RELAY_CLASS_20_S            = 20.0   # IEC 60947-4-1 Class 20 upper limit [s]
INSULATION_CLASS_F_C     = 155    # IEC 60085 Class F max temperature [°C]
INSULATION_CLASS_H_C     = 180    # IEC 60085 Class H max temperature [°C]
INSULATION_CLASS_C_C     = 180    # IEC 60085 Class C min temperature (above H) [°C]

# MIT PROTECTION SIZING (IEC)
MPCB_THERMAL_LO_RATIO    = 0.80   # IEC 60947-2 MPCB thermal setting lower bound (× In)
MPCB_THERMAL_HI_RATIO    = 1.00   # IEC 60947-2 MPCB thermal setting upper bound (× In)
MPCB_ICU_MULTIPLIER      = 1.25   # IEC 60947-2 MPCB breaking capacity (× peak current)
MPCB_RATIO_CLASS_8       = 8      # IEC 60947-2 peak/In boundary: ≤8 → satisfactory
MPCB_RATIO_CLASS_12      = 12     # IEC 60947-2 peak/In boundary: ≤12 → warning
FUSE_MULTIPLIER_MIN      = 2.0    # IEC 60269-1 gG/aM fuse minimum rating (× In)
FUSE_MULTIPLIER_MAX      = 2.5    # IEC 60269-1 gG/aM fuse maximum rating (× In)
CONTACTOR_RUPTURE_MULT   = 6.0    # IEC 60947-4-1 AC-3 contactor breaking capacity (× In)

# SPD SIZING (IEC 61643-11)
SPD_VN_LV                = 230    # line-to-neutral voltage upper boundary for LV SPD [V]
SPD_UC_LV                = 275    # SPD maximum continuous voltage for Vn ≤ 230 V [V]
SPD_UP_LV                = 1500   # SPD voltage protection level for Vn ≤ 230 V [V]
SPD_VN_MV                = 400    # line-to-neutral voltage upper boundary for MV SPD [V]
SPD_UC_MV                = 420    # SPD maximum continuous voltage for Vn ≤ 400 V [V]
SPD_UP_MV                = 2500   # SPD voltage protection level for Vn ≤ 400 V [V]
SPD_UC_HV_MULTIPLIER     = 1.1    # SPD Uc multiplier for Vn > 400 V (Uc = Vn × 1.1)
SPD_UP_HV                = 4000   # SPD voltage protection level for Vn > 400 V [V]

# POWER QUALITY (IEEE 519 / IEC 61000)
THD_LIMIT_IEEE519        = 5.0    # IEEE 519 current THD limit [%]
POWER_FACTOR_MIN         = 0.85   # IEC/IEEE recommended minimum power factor

# ENERGY / ECONOMIC
HOURS_PER_YEAR           = 8760   # hours per year (24 h × 365 d)
W_TO_KW                  = 1000   # conversion factor W → kW
P_NOM_MIN_KW             = 0.5    # minimum nominal power fallback [kW] — avoids zero-division in T×n KPI

# DC MACHINE PROTECTION & DIAGNOSTIC THRESHOLDS
DC_OVERCURRENT_WARN_RATIO       = 10.0   # peak/steady-state ratio → warning
DC_OVERCURRENT_CRIT_RATIO       = 15.0   # peak/steady-state ratio → critical alert
DC_RELAY_CLASS_10_RATIO         = 6.0    # IEC 60947-4-1: Class 10 boundary (peak/In < 6)
DC_RELAY_CLASS_20_RATIO         = 8.0    # IEC 60947-4-1: Class 20 boundary (peak/In < 8)
DC_FUSE_MULTIPLIER              = 2.0    # IEC 60269-1 fuse minimum rating (× rated current)
DC_BREAKER_LO_MULTIPLIER        = 1.0    # IEC 60947-2 breaker lower range (× rated current)
DC_BREAKER_HI_MULTIPLIER        = 1.25   # IEC 60947-2 breaker upper range (× rated current)
DC_ARMATURE_RIPPLE_WARN_PCT     = 5.0    # armature current ripple warning threshold [%]
DC_FIELD_INSTABILITY_RATIO      = 0.05   # field ripple / steady-state → instability warning
DC_STEADY_STATE_CONV_THRESHOLD  = 0.01   # speed fraction for steady-state convergence check


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

# ═══════════════════════════════════════════════════════════════════════════
# MIT SESSION-STATE DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════

MIT_SESSION_DEFAULTS: dict[str, object] = {
    "dark_mode":        False,
    "experiment_mode":  False,
    "selected_machine": None,
    "sim_result":       None,
    "ref_list":         [],
    "decimals":         3,
    "pdf_bytes":        None,
}


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
