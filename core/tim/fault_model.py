# -*- coding: utf-8 -*-
"""
fault_model.py
==============
Pure-physics fault models for the induction machine: unbalanced three-phase
voltage generation (symmetrical components) and the broken-bar rotor-resistance
modulation. No Streamlit / UI dependency — safe to import from the solver and
model layers.

Responsibilities:
  - Generate abc_voltages_deseq with per-phase amplitude and angle adjustments.
  - Support phase-loss mode (zero voltage on one phase).
  - Build make_broken_bar_rr_fn — Rr(t, theta_slip) modulation at slip frequency.

Relationships:
  Imported by : core.tim.machine_model, core.tim.solver, core.tim.facade,
                ui_components.tim_fault_ui, tests
  Imports     : math, numpy only
"""

from __future__ import annotations
import math
import numpy as np


# ── Voltage generation with unbalance/fault ──────────────────────────────────

def abc_voltages_deseq(t, Vl: float, f: float,
                       deseq_a: float = 0.0,
                       deseq_b: float = 0.0,
                       deseq_c: float = 0.0,
                       falta_fase_a: bool = False,
                       falta_fase_b: bool = False,
                       falta_fase_c: bool = False,
                       df_a: float = 0.0,
                       df_b: float = 0.0,
                       df_c: float = 0.0):
    """Generates abc voltages with unbalance and/or phase loss on any phase.

    deseq_a / deseq_b / deseq_c : fractional deviation in Vl (e.g. 0.1 = +10%, -0.1 = -10%).
    falta_fase_a/b/c             : if True, forces the phase voltage to zero.
    df_a / df_b / df_c           : per-phase frequency deviation in Hz (0 = nominal).
    Accepts t as scalar or np.ndarray; returns the same type.
    """
    scalar = np.ndim(t) == 0
    t_arr  = np.atleast_1d(np.asarray(t, dtype=float))
    zero   = np.zeros_like(t_arr)
    k      = np.sqrt(2.0 / 3.0)

    tetae_a = 2.0 * np.pi * (f + df_a) * t_arr
    tetae_b = 2.0 * np.pi * (f + df_b) * t_arr
    tetae_c = 2.0 * np.pi * (f + df_c) * t_arr

    Va = zero if falta_fase_a else k * Vl * (1.0 + deseq_a) * np.sin(tetae_a)
    Vb = zero if falta_fase_b else k * Vl * (1.0 + deseq_b) * np.sin(tetae_b - 2.0 * np.pi / 3.0)
    Vc = zero if falta_fase_c else k * Vl * (1.0 + deseq_c) * np.sin(tetae_c + 2.0 * np.pi / 3.0)

    if scalar:
        return float(Va[0]), float(Vb[0]), float(Vc[0])
    return Va, Vb, Vc


# ── Broken Bar Model ─────────────────────────────────────────────────────────

def make_broken_bar_rr_fn(Rr_nominal: float, severity: float, wb: float,
                          t_start: float = 0.0):
    """Returns function Rr(t, theta_slip) that modulates Rr at slip frequency from t_start.

    Model: Rr(t) = Rr0 · (1 + α · cos(2·θ_slip))  for t >= t_start
           Rr(t) = Rr0                               for t <  t_start

    Args:
        Rr_nominal: nominal rotor resistance (Ω).
        severity:   α — oscillation amplitude (0 = healthy, 0.1 = 10% breakage).
        wb:         base angular frequency (rad/s).
        t_start:    fault onset instant (s). 0 = fault present from the start.

    Returns:
        Callable[[float, float], float] — (t, theta_slip) → effective Rr.
        If severity == 0, returns None (signal to disable the model).
    """
    if severity == 0.0:
        return None

    def _rr_fn(t: float, theta_slip: float) -> float:
        if t < t_start:
            return Rr_nominal
        return Rr_nominal * (1.0 + severity * math.cos(2.0 * theta_slip))

    return _rr_fn
