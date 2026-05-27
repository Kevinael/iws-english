"""DC machine voltage sources for 6 modes of operation.

Modes: dol_dc, resistencia_dc, plugging_dc, pulso_dc, gerador_dc, campo_fraco_dc.
Each mode defines Va(t) for the integrator.
"""

from typing import Callable
import numpy as np


class DCSourceMode:
    """Base class for DC source modes."""

    def __init__(self, name: str):
        self.name = name

    def Va(self, t: float) -> float:
        """Armature voltage at time t."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────
# dol_dc: Direct On-Line (constant Va)
# ─────────────────────────────────────────────────────────────────────
class DOL_DC(DCSourceMode):
    """Direct On-Line: constant armature voltage from t=0."""

    def __init__(self, Va_nom: float):
        super().__init__("dol_dc")
        self.Va_nom = Va_nom

    def Va(self, t: float) -> float:
        return self.Va_nom


# ─────────────────────────────────────────────────────────────────────
# resistencia_dc: Series resistance (soft-start equivalent)
# ─────────────────────────────────────────────────────────────────────
class Resistencia_DC(DCSourceMode):
    """Series resistance: Va ramps from 0 to Va_nom over t_ramp."""

    def __init__(self, Va_nom: float, t_ramp: float = 1.0):
        super().__init__("resistencia_dc")
        self.Va_nom = Va_nom
        self.t_ramp = t_ramp

    def Va(self, t: float) -> float:
        if t <= self.t_ramp:
            return self.Va_nom * (t / self.t_ramp)
        else:
            return self.Va_nom


# ─────────────────────────────────────────────────────────────────────
# plugging_dc: Plugging (reverse voltage reversal)
# ─────────────────────────────────────────────────────────────────────
class Plugging_DC(DCSourceMode):
    """Plugging: DOL until t_switch, then Va → -Va_nom for braking."""

    def __init__(self, Va_nom: float, t_switch: float):
        super().__init__("plugging_dc")
        self.Va_nom = Va_nom
        self.t_switch = t_switch

    def Va(self, t: float) -> float:
        if t <= self.t_switch:
            return self.Va_nom
        else:
            return -self.Va_nom


# ─────────────────────────────────────────────────────────────────────
# pulso_dc: Load pulse (step up, then step down)
# ─────────────────────────────────────────────────────────────────────
class Pulso_DC(DCSourceMode):
    """Load pulse: constant Va, but Tload changes at t_pulse.

    (This is a load perturbation, not a voltage source change.
    Va remains constant; used with adjustable Tload in sim context.)
    """

    def __init__(self, Va_nom: float):
        super().__init__("pulso_dc")
        self.Va_nom = Va_nom

    def Va(self, t: float) -> float:
        """Constant armature voltage."""
        return self.Va_nom

    # Tload pulse is handled separately in simulator


# ─────────────────────────────────────────────────────────────────────
# gerador_dc: Generator (no source; driven mechanically)
# ─────────────────────────────────────────────────────────────────────
class Gerador_DC(DCSourceMode):
    """Generator mode: Va = 0 (driven by mechanical torque Tload > 0)."""

    def __init__(self):
        super().__init__("gerador_dc")

    def Va(self, t: float) -> float:
        """No armature source voltage."""
        return 0.0


# ─────────────────────────────────────────────────────────────────────
# campo_fraco_dc: Field weakening (reduce Vf for speed boost)
# ─────────────────────────────────────────────────────────────────────
class CampoFraco_DC(DCSourceMode):
    """Field weakening: constant Va, but Vf reduces at t_weaken for speed boost."""

    def __init__(self, Va_nom: float):
        super().__init__("campo_fraco_dc")
        self.Va_nom = Va_nom

    def Va(self, t: float) -> float:
        """Constant armature voltage (Vf reduction handled separately)."""
        return self.Va_nom

    # Vf reduction is handled separately in simulator


# ─────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────
def create_dc_source(
    mode: str, Va_nom: float = None, **kwargs
) -> Callable[[float], float]:
    """
    Create a voltage source function.

    Parameters:
      mode: 'dol_dc', 'resistencia_dc', 'plugging_dc', 'pulso_dc', 'gerador_dc', 'campo_fraco_dc'
      Va_nom: nominal armature voltage (V) [required for all except gerador_dc]
      **kwargs: mode-specific parameters (t_ramp, t_switch, etc.)

    Returns:
      Va(t) function.
    """
    if mode == "dol_dc":
        if Va_nom is None:
            raise ValueError("dol_dc requires Va_nom")
        source = DOL_DC(Va_nom)

    elif mode == "resistencia_dc":
        if Va_nom is None:
            raise ValueError("resistencia_dc requires Va_nom")
        t_ramp = kwargs.get("t_ramp", 1.0)
        source = Resistencia_DC(Va_nom, t_ramp)

    elif mode == "plugging_dc":
        if Va_nom is None:
            raise ValueError("plugging_dc requires Va_nom")
        t_switch = kwargs.get("t_switch", 1.0)
        source = Plugging_DC(Va_nom, t_switch)

    elif mode == "pulso_dc":
        if Va_nom is None:
            raise ValueError("pulso_dc requires Va_nom")
        source = Pulso_DC(Va_nom)

    elif mode == "gerador_dc":
        source = Gerador_DC()

    elif mode == "campo_fraco_dc":
        if Va_nom is None:
            raise ValueError("campo_fraco_dc requires Va_nom")
        source = CampoFraco_DC(Va_nom)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    return source.Va
