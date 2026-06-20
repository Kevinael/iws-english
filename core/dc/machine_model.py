# -*- coding: utf-8 -*-
"""
dc_machine_model.py
===================
Defines DCMachineParams (dataclass) and _make_rhs_dc — supports six DC machine
configurations (sep/shunt/series × motor/generator).

Responsibilities:
  - Store electrical, mechanical, and load parameters for the DCM
  - Build the 4-state ODE system (ωr, ia, if or ψf) for each configuration
  - Decode excitation variants (sep, shunt, series)

Relationships:
  Imported by : core.dc_solver, core.dc_sources, core.dc_estimator,
                ui.sim_config_dc, ui.sim_results_dc,
                viz.pdf_dc, viz.pdf_commons
  Imports     : (dataclasses, typing only)

Extending:
  - For a compound configuration, add compound_motor to _make_rhs_dc with
    two independent field windings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class DCMachineParams:
    # --- armature ---
    Va: float
    Ra: float
    La: float
    # --- field (sep/shunt; series uses combined Ra/La) ---
    Vf: float = 0.0
    Rf: float = 0.0
    Lf: float = 0.0
    # --- load (generators) ---
    Rl: float = 0.0
    Ll: float = 0.0
    # --- mechanical ---
    J: float = 0.21
    B: float = 1.074e-6
    # --- electromechanical constant ---
    kb: float = 0.004
    # --- configuration ---
    excitation: str = "sep_motor"   # sep_motor|sep_gen|shunt_motor|shunt_gen|series_motor
    # --- nominal load torque (N·m) ---
    Tload: float = 2.493

    def __post_init__(self) -> None:
        if self.excitation in ("shunt_motor", "shunt_gen"):
            self.Vf = self.Va
        if self.excitation == "series_motor":
            # combine resistance and inductance in series
            self._Raf = self.Ra + self.Rf
            self._Laf = self.La + self.Lf
        if self.excitation in ("sep_gen", "shunt_gen"):
            self._Rla = self.Ra + self.Rl
            self._Lla = self.La + self.Ll


def _make_rhs_dc(
    params: DCMachineParams,
    voltage_fn: Callable[[float], tuple[float, float]],
    torque_fn: Callable[[float], float],
) -> Callable[[float, list[float]], list[float]]:
    """Returns rhs(t, y) for solve_ivp.

    States y = [ia, ifd, wm].
    series_motor: ifd = ia (field = armature); ifd slot for consistency only.
    shunt_gen: internal states [x1, x2, wm]; ia/ifd reconstructed.
    """
    p = params
    exc = p.excitation

    if exc == "sep_motor":
        def rhs(t: float, y: list[float]) -> list[float]:
            ia, ifd, wm = y
            Va, Vf = voltage_fn(t)
            Tl = torque_fn(t)
            dia  = -(p.Ra / p.La) * ia  + Va / p.La  - (p.kb / p.La) * ifd * wm
            difd = -(p.Rf / p.Lf) * ifd + Vf / p.Lf
            dwm  = -(p.B  / p.J)  * wm  + (p.kb / p.J) * ifd * ia  - Tl / p.J
            return [dia, difd, dwm]

    elif exc == "shunt_motor":
        def rhs(t: float, y: list[float]) -> list[float]:
            ia, ifd, wm = y
            Va, _ = voltage_fn(t)
            Tl = torque_fn(t)
            dia  = -(p.Ra / p.La) * ia  + Va / p.La  - (p.kb / p.La) * ifd * wm
            difd = -(p.Rf / p.Lf) * ifd + Va / p.Lf   # Vf = Va (shunt)
            dwm  = -(p.B  / p.J)  * wm  + (p.kb / p.J) * ifd * ia  - Tl / p.J
            return [dia, difd, dwm]

    elif exc == "series_motor":
        Raf = p._Raf
        Laf = p._Laf

        def rhs(t: float, y: list[float]) -> list[float]:
            ia, _, wm = y   # slot ifd ignorado; ifd = ia
            Va, _ = voltage_fn(t)
            Tl = torque_fn(t)
            dia = -(Raf / Laf) * ia + Va / Laf - (p.kb / Laf) * ia * wm
            dwm = -(p.B  / p.J) * wm + (p.kb / p.J) * ia * ia - Tl / p.J
            return [dia, ia, dwm]   # difd = dia (ifd segue ia)

    elif exc == "sep_gen":
        Rla = p._Rla
        Lla = p._Lla

        def rhs(t: float, y: list[float]) -> list[float]:
            ia, ifd, wm = y
            _, Vf = voltage_fn(t)
            Tl = torque_fn(t)
            difd = -(p.Rf / p.Lf) * ifd + Vf / p.Lf
            dia  = -(Rla  / Lla)  * ia   + (p.kb / Lla) * ifd * wm
            dwm  = -(p.B  / p.J)  * wm   - (p.kb / p.J) * ifd * ia + Tl / p.J
            return [dia, difd, dwm]

    elif exc == "shunt_gen":
        # Transformed state variables x1, x2 as per dcgp.sce
        Llf  = p.Ll + p.Lf
        Lla  = p.Ll + p.La
        Rlf  = p.Rl + p.Rf
        Rla  = p.Rl + p.Ra
        Leq  = Lla * Llf - p.Ll * p.Ll

        def rhs(t: float, y: list[float]) -> list[float]:
            x1, x2, wm = y
            _, _ = voltage_fn(t)   # shunt generator: no external excitation
            Tl = torque_fn(t)
            dx1 = (p.Rl * p.Ll - Rlf * Lla) * x1 / Leq + (p.Rl * Llf - Rlf * p.Ll) * x2 / Leq
            dx2 = ((p.kb * wm + p.Rl) * Lla - Rla * p.Ll) * x1 / Leq + \
                  ((p.kb * wm + p.Rl) * p.Ll - Rla * Llf) * x2 / Leq
            dwm = -(p.B / p.J) * wm - \
                  (p.kb / (p.J * Leq * Leq)) * (p.Ll * x1 + Llf * x2) * (Lla * x1 + p.Ll * x2) + \
                  Tl / p.J
            return [dx1, dx2, dwm]

    else:
        raise ValueError(f"Unknown excitation: {exc!r}")

    return rhs


def decode_shunt_gen(y: list[float], params: DCMachineParams) -> tuple[float, float]:
    """Reconstructs ia and ifd from states [x1, x2, wm] of the shunt generator."""
    p = params
    Llf = p.Ll + p.Lf
    Lla = p.Ll + p.La
    Leq = Lla * Llf - p.Ll * p.Ll
    x1, x2 = y[0], y[1]
    ia  = p.Ll  * x1 / Leq + Llf * x2 / Leq
    ifd = Lla   * x1 / Leq + p.Ll * x2 / Leq
    return ia, ifd
