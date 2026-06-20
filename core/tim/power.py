# -*- coding: utf-8 -*-
"""
power.py
========
Canonical MIT steady-state power flow. Single source of truth for stator
copper loss, iron loss, input/output power and efficiency.

Responsibilities:
  - compute_power_flow(res, mp): full power balance from steady-state RMS values
  - compute_losses_pct(power): percentage breakdown of losses vs input power

Design note — ABC vs dq formulas:
  Stator copper and iron losses are computed from the *ABC* phase RMS values,
  not from dq currents/voltages. The ABC form matches textbook copper loss
  (3*Rs*I_phase_rms^2) exactly. The dq form previously used in viz/pdf_commons
  understated P_cu_s by 1.5x and overstated P_fe (because the amplitude-invariant
  Park constants were mis-applied to RMS quantities). Both PDF and solver now
  delegate here so the power flow is identical everywhere.

Relationships:
  Imported by : core.tim.solver, viz.pdf_commons
  Imports     : (none — pure numeric, no streamlit/plotly/scipy)
"""

from __future__ import annotations


def _mp_get(mp, key: str, default: float = 0.0) -> float:
    """Accept both a MachineParams object and a plain dict."""
    if isinstance(mp, dict):
        return float(mp.get(key, default))
    return float(getattr(mp, key, default))


def compute_power_flow(res: dict, mp) -> dict:
    """Compute the MIT steady-state power balance from ABC RMS values.

    Expects ``res`` to carry the steady-state RMS keys produced by the solver
    (``ias_rms``..``ics_rms``, ``Va_rms``..``Vc_rms``) plus the gap-power split
    (``P_gap``, ``P_cu_r``, ``P_mec``, ``s``).

    Returns a dict with ``P_cu_s``, ``P_fe``, ``P_in``, ``P_out``, ``eta`` and
    echoes ``P_gap``, ``P_cu_r``, ``P_mec``, ``s``.
    """
    Rs  = _mp_get(mp, "Rs", 0.435)
    Rfe = _mp_get(mp, "Rfe", 0.0)

    ias = float(res.get("ias_rms", 0.0))
    ibs = float(res.get("ibs_rms", 0.0))
    ics = float(res.get("ics_rms", 0.0))
    Va  = float(res.get("Va_rms", 0.0))
    Vb  = float(res.get("Vb_rms", 0.0))
    Vc  = float(res.get("Vc_rms", 0.0))

    P_gap  = float(res.get("P_gap", 0.0))
    P_cu_r = float(res.get("P_cu_r", 0.0))
    P_mec  = float(res.get("P_mec", 0.0))
    s      = float(res.get("s", 0.0))

    # Stator copper loss: 3*Rs*I_phase_rms^2, summed over the three phases.
    P_cu_s = Rs * (ias**2 + ibs**2 + ics**2)

    # Iron loss: 3*Rs-free core branch, 3*V_phase_rms^2/Rfe.
    V_phase_avg = (Va + Vb + Vc) / 3.0
    P_fe = 3.0 * V_phase_avg**2 / Rfe if Rfe > 0 else 0.0

    if s >= 0:
        # motor mode: electrical input, mechanical output
        P_in  = P_gap + P_cu_s + P_fe
        P_out = P_mec
    else:
        # generator mode (s<0): mechanical input, electrical output
        P_in  = abs(P_mec)
        P_out = max(0.0, abs(P_gap) - P_cu_s - P_fe)
    eta = (P_out / P_in * 100.0) if P_in > 0 else 0.0

    return {
        "P_gap": P_gap, "P_cu_r": P_cu_r, "P_mec": P_mec, "s": s,
        "P_cu_s": P_cu_s, "P_fe": P_fe,
        "P_in": P_in, "P_out": P_out, "eta": eta,
    }


def compute_losses_pct(power: dict) -> dict:
    """Percentage breakdown of losses against input power.

    Returns ``P_loss`` (total) and ``pct_cu_s``/``pct_cu_r``/``pct_fe``/``pct_mec``.
    """
    P_in   = float(power.get("P_in", 0.0))
    P_cu_s = float(power.get("P_cu_s", 0.0))
    P_cu_r = float(power.get("P_cu_r", 0.0))
    P_fe   = float(power.get("P_fe", 0.0))
    P_mec  = float(power.get("P_mec", 0.0))

    P_loss = P_cu_s + P_cu_r + P_fe
    denom  = P_in if abs(P_in) > 1.0 else 1.0
    return {
        "P_loss": P_loss,
        "pct_cu_s": P_cu_s / denom * 100.0,
        "pct_cu_r": P_cu_r / denom * 100.0,
        "pct_fe":   P_fe   / denom * 100.0,
        "pct_mec":  P_mec  / denom * 100.0,
    }
