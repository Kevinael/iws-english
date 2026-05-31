# -*- coding: utf-8 -*-
"""
machine_model.py — Parameters and RHS of the Krause 0dq model

Exports:
  MachineParams  — dataclass with all machine parameters (electrical,
                   mechanical, thermal, network) and derived fields
  _lm_saturado   — Froelich model for non-linear Lm (legacy, no effect on RHS)
  _xml_from_lm   — resulting mutual reactance given Lm
  _make_rhs      — builds and returns rhs(t, y) for solve_ivp

ODE states (8):
  [PSIqs, PSIds, PSIqr, PSIdr, wr, tetar, Temp, theta_slip]

Internal dependencies:
  core.thermal    — estimate_rth_cth, dTemp_dt
  core.transforms — abc_voltages, clarke_park_transform
  core.desequilibrio_falta — abc_voltages_deseq

Detailed documentation of each implementation decision:
  SME/2. Modulos/core/machine_model.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (secoes 1-2)
  SME/1. Fundamentos/4 - Modelo Matematico (RHS Krause).md
"""

from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass, field

from core.thermal import estimate_rth_cth
from core.transforms import abc_voltages, clarke_park_transform
from core.desequilibrio_falta import abc_voltages_deseq


# ═══════════════════════════════════════════════════════════════════════════
# MACHINE PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MachineParams:
    # ── Electrical ─────────────────────────────────────────────────────────
    Vl:    float = 220.0
    f:     float = 60.0
    Rs:    float = 0.435
    Rr:    float = 0.816
    Xm:    float = 26.13
    Xls:   float = 0.754
    Xlr:   float = 0.754
    # Rfe in parallel with Lm — use Rfe=1e9 to disable without changing UI
    Rfe:   float = 500.0

    # ── Mechanical ─────────────────────────────────────────────────────────
    p:     int   = 4
    J:     float = 0.089
    B:     float = 0.005

    # ── Magnetic saturation (legacy — no effect on RHS after rev-3) ────────
    # Fields kept for compatibility with saved sessions and tests.
    sat_enable: bool  = False
    Im_sat:     float = 0.0    # 0 -> auto (2 x Im0)

    # ── Network impedance ──────────────────────────────────────────────────
    Rgrid: float = 0.0    # Ohm per phase
    Lgrid: float = 0.0    # H per phase

    # ── Thermal Model ──────────────────────────────────────────────────────
    # Rth=0 -> auto: calibrated for T_ss = T_amb + 50 K (nominal TEFC operation)
    # Cth=0 -> auto: estimated by motor mass (P_mec_kW x 15 kg/kW x 460 J/kg.K)
    Rth:   float = 0.0    # K/W
    Cth:   float = 0.0    # J/K
    T_amb: float = 25.0   # degrees C

    # ── Magnetic parameter input mode ─────────────────────────────────────
    input_mode: str   = "X"    # "X" = reactances (Ohm) | "L" = inductances (H)
    f_ref:      float = 60.0   # frequency at which Xm/Xls/Xlr were tested (Hz)

    # ── Derived (computed in __post_init__) ──────────────────────────────────
    Xml:       float = field(init=False)
    wb:        float = field(init=False)
    Lm:        float = field(init=False)
    Lls:       float = field(init=False)
    Llr:       float = field(init=False)
    Xls_a:     float = field(init=False)
    Xlr_a:     float = field(init=False)
    Xls_a_eff: float = field(init=False)  # Xls_a + Lgrid*wb (absorbs network into stator)

    def __post_init__(self) -> None:
        self.wb = 2.0 * np.pi * self.f

        # conversion uses f_ref (test frequency), not f (operating frequency)
        # allows inserting catalog data at 50 Hz in a 60 Hz simulation
        if self.input_mode == "L":
            self.Lm  = self.Xm
            self.Lls = self.Xls
            self.Llr = self.Xlr
        else:
            _wb_ref  = 2.0 * np.pi * self.f_ref
            self.Lm  = self.Xm  / _wb_ref
            self.Lls = self.Xls / _wb_ref
            self.Llr = self.Xlr / _wb_ref
        self.Xls_a = self.wb * self.Lls
        self.Xlr_a = self.wb * self.Llr
        _Xm_a      = self.wb * self.Lm
        # Provisional Xml — needed for Im_sat; will be recalculated after Lgrid
        if _Xm_a <= 0.0 or self.Xls_a <= 0.0 or self.Xlr_a <= 0.0:
            raise ValueError(f"Invalid magnetic parameters: Xm_a={_Xm_a:.4f}, Xls_a={self.Xls_a:.4f}, Xlr_a={self.Xlr_a:.4f}")
        self.Xml   = 1.0 / (1.0 / _Xm_a + 1.0 / self.Xls_a + 1.0 / self.Xlr_a)

        # Automatic Im_sat: 2 x no-load magnetizing current
        if self.Im_sat == 0.0:
            _Vfase     = self.Vl / np.sqrt(3.0)
            _Im0       = _Vfase / (self.wb * self.Lm) if self.Lm > 0 else 5.0
            self.Im_sat = 2.0 * _Im0

        # Automatic Rth/Cth via T-circuit at nominal slip.
        # Uses wb*Lm as magnetizing branch (not Xml — T-circuit, not pi).
        # Must occur BEFORE Xls_a_eff is modified by Lgrid.
        if self.Rth == 0.0 or self.Cth == 0.0:
            _Xm_a_th = self.wb * self.Lm
            _Rth_est, _Cth_est = estimate_rth_cth(
                Vl=self.Vl, Rs=self.Rs, Rr=self.Rr,
                Xls_a=self.Xls_a, Xlr_a=self.Xlr_a, Xm_a=_Xm_a_th,
            )
            if self.Rth == 0.0:
                self.Rth = _Rth_est
            if self.Cth == 0.0:
                self.Cth = _Cth_est

        # Lgrid absorbed into Xls_a_eff (series impedance seen by stator)
        # Xml recalculated for consistency with new Xls_a_eff
        self.Xls_a_eff = self.Xls_a + self.Lgrid * self.wb
        _Xm_a_eff      = self.wb * self.Lm
        if _Xm_a_eff <= 0.0 or self.Xls_a_eff <= 0.0 or self.Xlr_a <= 0.0:
            raise ValueError(f"Invalid magnetic parameters (post-Lgrid): Xm_a={_Xm_a_eff:.4f}, Xls_a_eff={self.Xls_a_eff:.4f}, Xlr_a={self.Xlr_a:.4f}")
        self.Xml       = 1.0 / (1.0 / _Xm_a_eff + 1.0 / self.Xls_a_eff + 1.0 / self.Xlr_a)

    @property
    def n_sync(self) -> float:
        return 120.0 * self.f / self.p


# ═══════════════════════════════════════════════════════════════════════════
# MODEL AUXILIARIES
# ═══════════════════════════════════════════════════════════════════════════

def _lm_saturado(im_mag: float, Lm0: float, Im_sat: float) -> float:
    """Froelich model: Lm = Lm0 / (1 + |im| / Im_sat).

    Legacy — saturation removed from RHS in rev-3; function kept for
    compatibility with external code that references it.
    """
    if Im_sat <= 0.0:
        return Lm0
    return Lm0 / (1.0 + im_mag / Im_sat)


def _xml_from_lm(Lm: float, wb: float, Xls_a: float, Xlr_a: float) -> float:
    """Resulting mutual reactance given Lm."""
    Xm_a = wb * Lm
    if Xm_a <= 0.0:
        return 0.0
    return 1.0 / (1.0 / Xm_a + 1.0 / Xls_a + 1.0 / Xlr_a)


# ═══════════════════════════════════════════════════════════════════════════
# ODE RHS
# ═══════════════════════════════════════════════════════════════════════════
#
# States: [PSIqs, PSIds, PSIqr, PSIdr, wr, tetar, Temp, theta_slip]
#
# Thermal model (7th state):
#   dT/dt = (P_joule + P_fe) / Cth  -  (T - T_amb) / (Rth * Cth)
#   P_joule = (3/2) * (Rs*(iqs^2+ids^2) + Rr*(iqr^2+idr^2))
#   P_fe    = wb * (PSImq^2 + PSImd^2) / Rfe
#
# Network impedance:
#   Lgrid absorbed into Xls_a_eff; only resistive drop Rgrid remains in RHS.
#
# Generic reference frame (ref_code):
#   0 = stationary (w_ref=0), 1 = synchronous (w_ref=wb), 2 = rotor (w_ref=wr)

def _make_rhs(mp: MachineParams, voltage_fn, torque_fn, ref_code: int,
              deseq: tuple, t_deseq: float, deseq_active: bool,
              rr_fn=None):
    """Closes the RHS over parameters — returns rhs(t, y) ready for solve_ivp.

    Closure pattern: parameters captured as local scalars to minimize
    attribute lookup in the hot path (called ~50-200k times per second of simulation).
    use_grid evaluated once here, not inside rhs.
    Ver SME/2. Modulos/core/machine_model.md — secao _make_rhs.

    Args:
        rr_fn: callable(theta_slip) -> effective Rr (broken bar model).
               None = constant Rr — avoids call overhead in the common case.
    """
    # extract scalars — closure cell lookup is faster than object attribute
    Xls_a = mp.Xls_a_eff;  Xlr_a = mp.Xlr_a
    Xml   = mp.Xml
    Rs    = mp.Rs;          Rr    = mp.Rr;    wb = mp.wb
    p     = mp.p;           J     = mp.J;     B  = mp.B
    Rfe   = mp.Rfe
    Rgrid    = mp.Rgrid
    use_grid = (Rgrid != 0.0)   # evaluated once; branch in rhs is predictable
    Rth   = mp.Rth;  Cth = mp.Cth;  T_amb = mp.T_amb

    def rhs(t: float, y: list) -> list:
        # _tetar (rotor position) is a state but does not enter Krause equations
        # in synchronous reference — only integrated for post-processing
        PSIqs, PSIds, PSIqr, PSIdr, wr, _tetar, Temp, theta_slip = y

        # voltage source: unbalance activated conditionally by t_deseq
        Vl_a = voltage_fn(t)
        if deseq_active and t >= t_deseq:
            Va, Vb, Vc = abc_voltages_deseq(t, Vl_a, mp.f, *deseq)
        else:
            Va, Vb, Vc = abc_voltages(t, Vl_a, mp.f)
        tetae            = wb * t   # synchronous reference angle (exact, no integration)
        Vds_src, Vqs_src = clarke_park_transform(Va, Vb, Vc, tetae)

        # reference frame angular speed (ref_code: 0=stationary, 1=synchronous, 2=rotor)
        if   ref_code == 1: w_ref = wb
        elif ref_code == 2: w_ref = wr
        else:               w_ref = 0.0

        # mutual flux and leakage currents (algebraic relations — not ODEs)
        PSImq = Xml * (PSIqs / Xls_a + PSIqr / Xlr_a)
        PSImd = Xml * (PSIds / Xls_a + PSIdr / Xlr_a)
        iqs = (PSIqs - PSImq) / Xls_a
        ids = (PSIds - PSImd) / Xls_a
        iqr = (PSIqr - PSImq) / Xlr_a
        idr = (PSIdr - PSImd) / Xlr_a

        # network resistive drop (Lgrid already absorbed into Xls_a_eff — only Rgrid here)
        if use_grid:
            Vqs_eff = Vqs_src - Rgrid * iqs
            Vds_eff = Vds_src - Rgrid * ids
        else:
            Vqs_eff = Vqs_src
            Vds_eff = Vds_src

        slip_ref = (w_ref - wr) / wb
        # rr_fn=None in common case: avoids function call at each step
        Rr_cur   = rr_fn(t, theta_slip) if rr_fn is not None else Rr

        # Krause flux equations (2013), Eq. 6.5-17, normalized form by wb
        dPSIqs = wb * (Vqs_eff - (w_ref / wb) * PSIds + (Rs / Xls_a) * (PSImq - PSIqs))
        dPSIds = wb * (Vds_eff + (w_ref / wb) * PSIqs + (Rs / Xls_a) * (PSImd - PSIds))
        dPSIqr = wb * (-slip_ref * PSIdr + (Rr_cur / Xlr_a) * (PSImq - PSIqr))
        dPSIdr = wb * ( slip_ref * PSIqr + (Rr_cur / Xlr_a) * (PSImd - PSIdr))

        # factor 3/2 follows amplitude-invariant convention (not power-invariant)
        Te     = (3.0 / 2.0) * (p / 2.0) * (1.0 / wb) * (PSIds * iqs - PSIqs * ids)
        Tl_a   = torque_fn(t)

        # broken bar: additive torque perturbation at slip frequency
        # ΔTe = α * Te_base * cos(2*θ_slip) — oscillates at 2*s*f, produces sidebands at (1±2s)f
        if rr_fn is not None:
            _alpha = (Rr_cur - Rr) / Rr  # instantaneous alpha recovered from Rr_cur
            Te_bb  = _alpha * Te * 0.5
        else:
            Te_bb = 0.0

        dwr    = (p / (2.0 * J)) * (Te + Te_bb - Tl_a) - (B / J) * wr
        dtetar = wr

        # theta_slip integrated as state for broken bar model (rr_fn)
        d_theta_slip = wb - wr
        # state 7 (Temp) integrated in post-processing over vectorized P_joule;
        # dTemp=0 here prevents inrush peak (P_joule>>nominal at t<50ms)
        # from contaminating temperature via discretization error with h=1e-3.
        return [dPSIqs, dPSIds, dPSIqr, dPSIdr, dwr, dtetar, 0.0, d_theta_slip]

    return rhs
