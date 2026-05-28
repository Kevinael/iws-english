"""Modelo de MCC — DCMachineParams + _make_rhs_dc().

ODEs derivadas dos modelos Scilab de referência:
  sep_motor / sep_gen  → dcmei.sce, dgmei.sce
  shunt_motor          → dcmp.sce
  shunt_gen            → dcgp.sce  (variáveis x1, x2 preservadas)
  series_motor         → dcms.sce  (Raf = Ra+Rf, Laf = La+Lf)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class DCMachineParams:
    # --- armadura ---
    Va: float
    Ra: float
    La: float
    # --- campo (sep/shunt; series usa Ra/La combinados) ---
    Vf: float = 0.0
    Rf: float = 0.0
    Lf: float = 0.0
    # --- carga (geradores) ---
    Rl: float = 0.0
    Ll: float = 0.0
    # --- mecânico ---
    J: float = 0.21
    B: float = 1.074e-6
    # --- constante eletromecânica ---
    kb: float = 0.004
    # --- configuração ---
    excitation: str = "sep_motor"   # sep_motor|sep_gen|shunt_motor|shunt_gen|series_motor
    # --- torque de carga nominal (N·m) ---
    Tload: float = 2.493

    def __post_init__(self) -> None:
        if self.excitation in ("shunt_motor", "shunt_gen"):
            self.Vf = self.Va
        if self.excitation == "series_motor":
            # combina resistência e indutância em serie
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
    """Retorna rhs(t, y) para solve_ivp.

    Estados y = [ia, ifd, wm].
    series_motor: ifd = ia (campo = armadura); slot ifd apenas por consistência.
    shunt_gen: estados internos [x1, x2, wm]; ia/ifd reconstituídos.
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
        # Variáveis de estado transformadas x1, x2 conforme dcgp.sce
        Llf  = p.Ll + p.Lf
        Lla  = p.Ll + p.La
        Rlf  = p.Rl + p.Rf
        Rla  = p.Rl + p.Ra
        Leq  = Lla * Llf - p.Ll * p.Ll

        def rhs(t: float, y: list[float]) -> list[float]:
            x1, x2, wm = y
            _, _ = voltage_fn(t)   # gerador shunt: sem excitação externa
            Tl = torque_fn(t)
            dx1 = (p.Rl * p.Ll - Rlf * Lla) * x1 / Leq + (p.Rl * Llf - Rlf * p.Ll) * x2 / Leq
            dx2 = ((p.kb * wm + p.Rl) * Lla - Rla * p.Ll) * x1 / Leq + \
                  ((p.kb * wm + p.Rl) * p.Ll - Rla * Llf) * x2 / Leq
            dwm = -(p.B / p.J) * wm - \
                  (p.kb / (p.J * Leq * Leq)) * (p.Ll * x1 + Llf * x2) * (Lla * x1 + p.Ll * x2) + \
                  Tl / p.J
            return [dx1, dx2, dwm]

    else:
        raise ValueError(f"Excitação desconhecida: {exc!r}")

    return rhs


def decode_shunt_gen(y: list[float], params: DCMachineParams) -> tuple[float, float]:
    """Reconstrói ia e ifd a partir dos estados [x1, x2, wm] do gerador shunt."""
    p = params
    Llf = p.Ll + p.Lf
    Lla = p.Ll + p.La
    Leq = Lla * Llf - p.Ll * p.Ll
    x1, x2 = y[0], y[1]
    ia  = p.Ll  * x1 / Leq + Llf * x2 / Leq
    ifd = Lla   * x1 / Leq + p.Ll * x2 / Leq
    return ia, ifd
