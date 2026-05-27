"""DC Machine parametrization and ODE definitions.

5 configurations: sep_motor, sep_gen, shunt_motor, shunt_gen, series_motor.
States: [ifd, ia, wm] (sep/shunt) or [ia, wm] (series).
Source: dcmei.sce, dcmp.sce, dcms.sce, dgmei.sce, dcgp.sce (Marcus Fernandes)
Reference: O.I. Okoro et al. 2008 (Simulation of D.C. Machines Transient Behaviors)
"""

from dataclasses import dataclass
from typing import Callable, Tuple, Union
import numpy as np


@dataclass
class DCMachineParams:
    """DC machine parameters."""

    # Field circuit
    Rf: float  # Field resistance (Ω)
    Lf: float  # Field inductance (H)

    # Armature circuit
    Ra: float  # Armature resistance (Ω)
    La: float  # Armature inductance (H)

    # Mechanical
    J: float  # Moment of inertia (kg·m²)
    B: float  # Viscous friction (N·m·s/rad)
    kb: float  # Back-EMF constant (V·s/rad)

    # Field and armature voltages
    Vf: float = 0.0  # Field voltage (V) — sep only
    Va: float = 0.0  # Armature voltage (V)

    # Load
    Tload: float = 0.0  # Load torque (N·m)

    # Generator shunt load
    Rl: float = 0.0  # Load resistance (Ω) — gen only
    Ll: float = 0.0  # Load inductance (H) — gen only

    @property
    def n_states(self) -> int:
        """Number of ODE states."""
        return 3  # [ifd, ia, wm] or [ifd, ia, wm]


class DCMachineODEs:
    """ODE definitions for 5 DC machine configurations."""

    def __init__(self, config: str, params: DCMachineParams):
        self.config = config
        self.params = params
        self.validate_config()

    def validate_config(self):
        """Check parameter consistency."""
        configs = {"sep_motor", "sep_gen", "shunt_motor", "shunt_gen", "series_motor"}
        if self.config not in configs:
            raise ValueError(f"Unknown config: {self.config}. Must be {configs}")

        p = self.params

        # All: Ra, La, J, B, kb required
        for attr in ["Ra", "La", "J", "B", "kb"]:
            if getattr(p, attr) == 0:
                raise ValueError(f"{attr} cannot be 0")

        # sep_*: Rf, Lf, Vf required
        if "sep" in self.config:
            if p.Rf == 0 or p.Lf == 0 or p.Vf == 0:
                raise ValueError(f"{self.config} requires Rf, Lf, Vf > 0")

        # shunt_*: Rf, Lf required; Va set by source
        if "shunt" in self.config:
            if p.Rf == 0 or p.Lf == 0:
                raise ValueError(f"{self.config} requires Rf, Lf > 0")

        # series_motor: no Vf, no Rl/Ll
        if "series" in self.config:
            if p.Vf != 0 or p.Rl != 0 or p.Ll != 0:
                raise ValueError(f"{self.config} should not have Vf, Rl, Ll")

        # gen: Rl, Ll required for shunt; diode for sep (Vf is source)
        if "gen" in self.config and "sep" not in self.config:
            if p.Rl == 0 or p.Ll == 0:
                raise ValueError(f"{self.config} requires Rl, Ll > 0")

    def get_ode_func(self) -> Tuple[Callable, int]:
        """Return (ode_func, n_states)."""
        if self.config == "sep_motor":
            return self._sep_motor_odes, 3
        elif self.config == "shunt_motor":
            return self._shunt_motor_odes, 3
        elif self.config == "series_motor":
            return self._series_motor_odes, 2
        elif self.config == "sep_gen":
            return self._sep_gen_odes, 3
        elif self.config == "shunt_gen":
            return self._shunt_gen_odes, 4  # [x1, x2, wm] + aux
        else:
            raise ValueError(f"Unknown config: {self.config}")

    # ─────────────────────────────────────────────────────────────
    # sep_motor: independent field, motor mode
    # States: [ifd, ia, wm]
    # Source: dcmei.sce:38-46
    # ─────────────────────────────────────────────────────────────
    def _sep_motor_odes(self, t: float, x: np.ndarray, Va: float) -> np.ndarray:
        """Separate excitation motor ODEs.

        x = [ifd, ia, wm]
        difd/dt = -(Rf/Lf)*ifd + Vf/Lf
        dia/dt = -(Ra/La)*ia + Va/La - (kb/La)*ifd*wm
        dwm/dt = -(B/J)*wm + (kb/J)*ifd*ia - Tload/J
        """
        p = self.params
        ifd, ia, wm = x

        difd_dt = -(p.Rf / p.Lf) * ifd + p.Vf / p.Lf
        dia_dt = -(p.Ra / p.La) * ia + Va / p.La - (p.kb / p.La) * ifd * wm
        dwm_dt = -(p.B / p.J) * wm + (p.kb / p.J) * ifd * ia - p.Tload / p.J

        return np.array([difd_dt, dia_dt, dwm_dt])

    # ─────────────────────────────────────────────────────────────
    # shunt_motor: parallel field, motor mode
    # States: [ifd, ia, wm]
    # Source: dcmp.sce:37-45
    # ─────────────────────────────────────────────────────────────
    def _shunt_motor_odes(self, t: float, x: np.ndarray, Va: float) -> np.ndarray:
        """Shunt motor ODEs.

        x = [ifd, ia, wm]
        difd/dt = -(Rf/Lf)*ifd + Va/Lf
        dia/dt = -(Ra/La)*ia + Va/La - (kb/La)*ifd*wm
        dwm/dt = -(B/J)*wm + (kb/J)*ifd*ia - Tload/J

        Note: Field and armature share Va (parallel).
        """
        p = self.params
        ifd, ia, wm = x

        difd_dt = -(p.Rf / p.Lf) * ifd + Va / p.Lf
        dia_dt = -(p.Ra / p.La) * ia + Va / p.La - (p.kb / p.La) * ifd * wm
        dwm_dt = -(p.B / p.J) * wm + (p.kb / p.J) * ifd * ia - p.Tload / p.J

        return np.array([difd_dt, dia_dt, dwm_dt])

    # ─────────────────────────────────────────────────────────────
    # series_motor: series field, motor mode
    # States: [ia, wm]  (no separate ifd — they are the same)
    # Source: dcms.sce:38-43
    # ─────────────────────────────────────────────────────────────
    def _series_motor_odes(self, t: float, x: np.ndarray, Va: float) -> np.ndarray:
        """Series motor ODEs (2 states only).

        x = [ia, wm]
        Raf = Ra + Rf
        Laf = La + Lf
        dia/dt = -(Raf/Laf)*ia + Va/Laf - (kb/Laf)*ia*wm
        dwm/dt = -(B/J)*wm + (kb/J)*ia² - Tload/J

        Note: Field and armature in series, so Te = kb*ia²
        """
        p = self.params
        ia, wm = x

        Raf = p.Ra + p.Rf
        Laf = p.La + p.Lf

        dia_dt = -(Raf / Laf) * ia + Va / Laf - (p.kb / Laf) * ia * wm
        dwm_dt = -(p.B / p.J) * wm + (p.kb / p.J) * ia * ia - p.Tload / p.J

        return np.array([dia_dt, dwm_dt])

    # ─────────────────────────────────────────────────────────────
    # sep_gen: independent field, generator mode
    # States: [ifd, ia, wm]
    # Source: dgmei.sce:43-51
    # ─────────────────────────────────────────────────────────────
    def _sep_gen_odes(self, t: float, x: np.ndarray, Va: float = None) -> np.ndarray:
        """Separate excitation generator ODEs.

        x = [ifd, ia, wm]
        difd/dt = -(Rf/Lf)*ifd + Vf/Lf
        dia/dt = -(Rla/Lla)*ia + (kb/Lla)*ifd*wm
        dwm/dt = -(B/J)*wm - (kb/J)*ifd*ia + Tload/J

        where Rla = Ra + Rl, Lla = La + Ll (load in series).
        Note: Generator — torque opposes motion, so Te term is negative.
        """
        p = self.params
        ifd, ia, wm = x

        Rla = p.Ra + p.Rl
        Lla = p.La + p.Ll

        difd_dt = -(p.Rf / p.Lf) * ifd + p.Vf / p.Lf
        dia_dt = -(Rla / Lla) * ia + (p.kb / Lla) * ifd * wm
        dwm_dt = -(p.B / p.J) * wm - (p.kb / p.J) * ifd * ia + p.Tload / p.J

        return np.array([difd_dt, dia_dt, dwm_dt])

    # ─────────────────────────────────────────────────────────────
    # shunt_gen: parallel field, generator mode (full state-space)
    # States: [x1, x2, wm] where x1 = Llf*ifd - Ll*ia, x2 = Lla*ia - Ll*ifd
    # Source: dcgp.sce:33-36
    # ─────────────────────────────────────────────────────────────
    def _shunt_gen_odes(
        self, t: float, x: np.ndarray, Va: float = None
    ) -> np.ndarray:
        """Shunt generator ODEs (coupled field-load dynamics).

        x = [x1, x2, wm]
        where x1 = Llf*ifd - Ll*ia, x2 = Lla*ia - Ll*ifd.

        dx1/dt = (Rl*Ll - Rlf*Lla)*x1/Leq + (Rl*Llf - Rlf*Ll)*x2/Leq
        dx2/dt = ((kb*wm + Rl)*Lla - Rla*Ll)*x1/Leq + ((kb*wm + Rl)*Ll - Rla*Llf)*x2/Leq
        dwm/dt = -(B/J)*wm - (kb/(J*Leq²))*(Ll*x1 + Llf*x2)*(Lla*x1 + Ll*x2) + Tl/J

        Derived variables:
        ia = (Ll*x1 + Llf*x2) / Leq
        ifd = (Lla*x1 + Ll*x2) / Leq
        Te = kb*ia*ifd (for output)

        Abbreviations:
        Llf = Ll + Lf, Lla = Ll + La
        Rlf = Rl + Rf, Rla = Rl + Ra
        Leq = Lla*Llf - Ll²
        """
        p = self.params
        x1, x2, wm = x

        Llf = p.Ll + p.Lf
        Lla = p.Ll + p.La
        Rlf = p.Rl + p.Rf
        Rla = p.Rl + p.Ra
        Leq = Lla * Llf - p.Ll * p.Ll

        if abs(Leq) < 1e-12:
            raise ValueError("Shunt generator: Leq ≈ 0 (singular inductance matrix)")

        dx1_dt = (
            (p.Rl * p.Ll - Rlf * Lla) * x1 / Leq + (p.Rl * Llf - Rlf * p.Ll) * x2 / Leq
        )

        dx2_dt = (
            ((p.kb * wm + p.Rl) * Lla - Rla * p.Ll) * x1 / Leq
            + ((p.kb * wm + p.Rl) * p.Ll - Rla * Llf) * x2 / Leq
        )

        dwm_dt = (
            -(p.B / p.J) * wm
            - (p.kb / (p.J * Leq * Leq))
            * (p.Ll * x1 + Llf * x2)
            * (Lla * x1 + p.Ll * x2)
            + p.Tload / p.J
        )

        return np.array([dx1_dt, dx2_dt, dwm_dt])

    @staticmethod
    def compute_outputs(config: str, x: np.ndarray, params: DCMachineParams) -> dict:
        """Compute output variables (Te, Ea, ifd, ia) from state vector.

        For shunt_gen, requires decoding x1, x2 → ifd, ia.
        """
        outputs = {}

        if config == "series_motor":
            ia, wm = x
            outputs["ia"] = ia
            outputs["ifd"] = ia  # Field and armature are the same
            outputs["wm"] = wm
            outputs["Te"] = params.kb * ia * ia
            outputs["Ea"] = params.kb * wm * ia

        elif config in ["sep_motor", "shunt_motor", "sep_gen"]:
            ifd, ia, wm = x
            outputs["ifd"] = ifd
            outputs["ia"] = ia
            outputs["wm"] = wm
            outputs["Te"] = params.kb * ia * ifd
            outputs["Ea"] = params.kb * wm * ifd

        elif config == "shunt_gen":
            x1, x2, wm = x
            Llf = params.Ll + params.Lf
            Lla = params.Ll + params.La
            Leq = Lla * Llf - params.Ll * params.Ll
            ia = (params.Ll * x1 + Llf * x2) / Leq
            ifd = (Lla * x1 + params.Ll * x2) / Leq
            outputs["x1"] = x1
            outputs["x2"] = x2
            outputs["ia"] = ia
            outputs["ifd"] = ifd
            outputs["wm"] = wm
            outputs["Te"] = params.kb * ia * ifd
            outputs["Ea"] = params.kb * wm * ifd

        return outputs
