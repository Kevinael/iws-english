# -*- coding: utf-8 -*-
"""
thermal.py
==========
First-order thermal model for the induction machine — estimates thermal
resistance/capacitance and provides the temperature ODE.

Responsibilities:
  - Estimate Rth and Cth from electrical parameters (estimate_rth_cth)
  - Compute the temperature derivative dTemp_dt for coupled integration

Relationships:
  Imported by : core.machine_model
  Imports     : (math only)

Extending:
  - For a two-node model (stator/rotor independently), create
    estimate_rth_cth_2node and dTemp_dt_2node.

----
thermal.py — First-order thermal model for induction motors

Exports:
  estimate_rth_cth(mp)  — estimates Rth and Cth from electrical parameters
  dTemp_dt(Temp, P_joule, P_fe, Rth, Cth, T_amb)  — thermal ODE (scalar)

Model:
  dT/dt = (P_joule + P_fe) / Cth  −  (T − T_amb) / (Rth · Cth)
  T_ss = T_amb + Rth · (P_joule + P_fe)   (thermal equilibrium)

Rth is calibrated for ΔT = 50 K at rated load — typical operating target for
well-sized TEFC motors (T_ss ≈ 75°C with T_amb = 25°C).
This value is representative of field measurements; 105 K (Class B) is the
design limit, not the normal operating condition.

Cth is derived from empirical τ_th (TEFC WEG/ABB/Siemens catalogues):
τ_th ≈ 1500 s for 2.2 kW (3 HP), scaling as τ ∝ P_mec^0.25 for larger motors.
Temperature is computed in post-processing (not as an ODE state) to avoid
the electromagnetic inrush peak (P_joule >> P_nom at t < 50 ms) producing
artificially high heating due to discretisation error at the main simulation step h.

Detailed documentation for each implementation decision:
  SME/2. Modulos/core/thermal.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (section 6)
  SME/1. Fundamentos/4 - Modelo Matematico (RHS Krause).md
"""

from __future__ import annotations
import math


# Nominal operating ΔT for well-sized TEFC motors
# (75°C at steady state with T_amb=25°C); 105 K (Class B) is the design limit.
_DELTA_T_NOMINAL: float = 50.0   # K

# Reference thermal time constant (s) for a 2.2 kW (3 HP) TEFC motor.
# Calibrated against WEG/ABB/Siemens catalogues: τ_th ≈ 20–25 min for small motors.
# Scaled by power via _TAU_EXPONENT to reproduce τ growing with motor size.
_TAU_REF_S: float  = 1500.0   # s  — τ_th for P_ref = 2.2 kW
_TAU_P_REF: float  =    2.2   # kW — reference power
_TAU_EXPONENT: float = 0.25   # τ ∝ P^0.25 (sublinear — validated: 37 kW → ~2000 s, 1678 kW → ~3200 s)


def estimate_rth_cth(
    Vl: float,
    Rs: float, Rr: float,
    Xls_a: float, Xlr_a: float, Xm_a: float,
    s_nom: float = 0.03,
) -> tuple[float, float]:
    """Estimates Rth (K/W) and Cth (J/K) via T equivalent circuit at nominal slip.

    Args:
        Vl:     Line voltage (V).
        Rs, Rr: Stator and rotor resistances (Ω), referred to stator.
        Xls_a:  Stator leakage reactance at rated frequency (Ω).
        Xlr_a:  Rotor leakage reactance at rated frequency (Ω).
        Xm_a:   Magnetising reactance at rated frequency (Ω) — pure parallel branch (wb·Lm).
        s_nom:  Nominal slip (default 0.03 = 3%).

    Returns:
        (Rth, Cth) — both in SI units.
    """
    Vfase = Vl / math.sqrt(3.0)

    # T circuit (not pi): Xm_a is the pure magnetising branch (wb*Lm).
    # Using Xml (pi circuit) would overestimate nominal currents — see SME/2. Modulos/core/thermal.md
    Z_rotor    = complex(Rr / s_nom, Xlr_a)
    Z_mag      = complex(0.0, Xm_a)
    Z_paralelo = (Z_rotor * Z_mag) / (Z_rotor + Z_mag)
    Z_total    = complex(Rs, Xls_a) + Z_paralelo

    I_estator = Vfase / abs(Z_total)
    # current divider: fraction of I_stator flowing through the rotor branch
    I_rotor   = I_estator * abs(Z_mag / (Z_rotor + Z_mag))

    # max(..., 10.0) and max(..., 0.5): guard against division by zero with extreme parameters
    P_perdas  = max(3.0 * (Rs * I_estator**2 + Rr * I_rotor**2), 10.0)
    P_mec_kw  = max(
        (3.0 * I_rotor**2 * (Rr / s_nom) * (1.0 - s_nom)) / 1000.0,
        0.5,
    )

    # Rth calibrated for ΔT=50 K — typical T_ss of a well-sized TEFC motor
    Rth = _DELTA_T_NOMINAL / P_perdas

    # Cth derived from empirical τ_th (TEFC catalogues): τ = Rth · Cth
    # τ scales sublinearly with power — larger motors have larger τ but smaller Rth
    tau_th = _TAU_REF_S * (P_mec_kw / _TAU_P_REF) ** _TAU_EXPONENT
    Cth = tau_th / Rth

    return Rth, Cth


def dTemp_dt(
    Temp: float,
    P_joule: float,
    P_fe: float,
    Rth: float,
    Cth: float,
    T_amb: float,
) -> float:
    """Motor temperature derivative (first-order ODE, lumped parameters).

    dT/dt = (P_joule + P_fe) / Cth  −  (T − T_amb) / (Rth · Cth)

    Integrated inside the main ODE (state 7) so that LSODA controls the
    thermal integration step together with the electromagnetic states.
    See SME/2. Modulos/core/thermal.md — section 'Why integrate inside the ODE'.
    """
    return (P_joule + P_fe) / Cth - (Temp - T_amb) / (Rth * Cth)
