# -*- coding: utf-8 -*-
"""
data/machines_mit.py
====================
Single source of truth for all MIT (Three-Phase Induction Motor) machine presets.

UI selectors, tests, and auto-load all read from MIT_PRESETS — add new machines
here and they appear everywhere automatically.

HOW TO ADD A NEW PRESET
-----------------------
1. Add an entry to MIT_PRESETS below. The key is the display name shown in the
   UI selector. Minimum required fields:

       "My Motor — 5 HP (3.7 kW) 380 V/50 Hz": {
           "Vl": 380.0,   # line voltage [V]
           "f":  50.0,    # frequency [Hz]
           "Rs": 1.20,    # stator resistance [Ω]
           "Rr": 0.90,    # rotor resistance [Ω]
           "input_mode": "Reactances (Ω)  —  measured at $f_{ref}$",
           "f_ref": 50.0, # frequency at which Xm/Xls/Xlr were measured [Hz]
           "Xm":  25.0,   # magnetising reactance [Ω]
           "Xls":  1.5,   # stator leakage reactance [Ω]
           "Xlr":  1.5,   # rotor leakage reactance [Ω]
           "Rfe": 300.0,  # core-loss resistance [Ω]  (tune so losses ≈ 3–6% of Pn)
           "p": 4,        # number of poles
           "J": 0.15,     # rotor inertia [kg·m²]
           "B": 0.002,    # viscous friction [N·m·s/rad]
           "exp_type": "Direct-On-Line Starting (DOL)",
           "Tl_final": 20.0,  # nominal load torque [N·m]
       },

2. That is all. No other file needs to be touched for the UI.
   - The UI selector (ui_components/sim_config.py) picks it up automatically.
   - get_mit_preset() and mit_preset_names() also update automatically.

3. OPTIONAL — only if the preset will be used frequently in tests:
   Add a named constant at the bottom of this file:

       MY_MOTOR = _mp_kwargs("My Motor — 5 HP (3.7 kW) 380 V/50 Hz")

   Then reference it in tests/conftest.py as a fixture:

       from data.machines_mit import MY_MOTOR

       @pytest.fixture
       def mp_my_motor():
           return MachineParams(**MY_MOTOR)

   If the preset is only used once or twice in tests, skip the constant and
   read MIT_PRESETS directly instead:

       from data.machines_mit import MIT_PRESETS
       p = MIT_PRESETS["My Motor — 5 HP (3.7 kW) 380 V/50 Hz"]
       mp = MachineParams(**{k: p[k] for k in ("Vl","f","Rs","Rr","Xm","Xls","Xlr","Rfe","p","J","B")})

OPTIONAL FIELDS (include only when relevant to the experiment type)
-------------------------------------------------------------------
   "tmax":          float  — simulation end time [s]          (default: auto)
   "t_load":       float  — load-ramp start time [s]         (DOL with slow J)
   "Tl_pulse":      float  — load before pulse [N·m]          (Load Pulse mode)
   "Tl_pulse_abs":  float  — load during pulse [N·m]          (Load Pulse mode)
   "t_pulse_on":    float  — pulse start time [s]             (Load Pulse mode)
   "t_pulse_off":   float  — pulse end time [s]               (Load Pulse mode)
"""
from __future__ import annotations
from typing import Any

# ── MIT Presets ──────────────────────────────────────────────────────────────
# Rfe note — Krause (2002) does not specify Rfe explicitly.
# Values below are calibrated so that core losses ≈ 3–6 % of rated power:
#   3 HP  : Rfe = 400 Ω → losses ≈ 3×(127²/400) ≈ 121 W (~5.5 % of 2200 W)
#   50 HP : Rfe = 150 Ω → losses ≈ 3×(265²/150) ≈ 1.4 kW (~3.8 % of 37 kW)
#   2250HP: Rfe =  80 Ω → losses ≈ 3×(1328²/80) ≈ 66 kW (~3.9 % of 1678 kW)
# conftest.py previously used Rfe=500 for all three — incorrect; fixed here.

MIT_PRESETS: dict[str, dict[str, Any]] = {
    "Default — Krause 3 HP (2.2 kW / 12 N·m) 220 V/60 Hz": {
        # Krause (2002) — induction motor 220 V / 60 Hz / 4 poles / ~3 hp
        "Vl": 220.0, "f": 60.0, "Rs": 0.435, "Rr": 0.816,
        "input_mode": "Reactances (Ω)  —  measured at $f_{ref}$",
        "f_ref": 60.0, "Xm": 26.13, "Xls": 0.754, "Xlr": 0.754, "Rfe": 400.0,
        "p": 4, "J": 0.089, "B": 0.005,
        "exp_type": "Direct-On-Line Starting (DOL)",
        "Tl_final": 12.0,
    },
    "Usta (2024) — 0.37 kW (2.4 N·m) 220 V/50 Hz": {
        # Laboratory motor 220 V / 50 Hz / 4 poles / ~0.37 kW
        # T_nom = 370 / (1455×π/30) ≈ 2.4 N·m
        "Vl": 220.0, "f": 50.0, "Rs": 2.65, "Rr": 2.85,
        "input_mode": "Reactances (Ω)  —  measured at $f_{ref}$",
        "f_ref": 50.0, "Xm": 60.98, "Xls": 4.43, "Xlr": 5.69, "Rfe": 800.0,
        "p": 4, "J": 0.025, "B": 0.001,
        "exp_type": "Load Pulse (apply and remove)",
        "Tl_pulse": 0.0, "Tl_pulse_abs": 2.4, "t_pulse_on": 0.6, "t_pulse_off": 0.8,
        "tmax": 1.0,
        "Tl_final": 2.4,
    },
    "Krause 50 HP (37 kW / 202 N·m) — 460 V/60 Hz": {
        # Krause (2002) — medium-sized industrial motor, 460 V / 60 Hz / 4 poles / 50 hp
        # T_nom = 37000 / (1746×π/30) ≈ 202 N·m
        "Vl": 460.0, "f": 60.0, "Rs": 0.087, "Rr": 0.228,
        "input_mode": "Reactances (Ω)  —  measured at $f_{ref}$",
        "f_ref": 60.0, "Xm": 13.08, "Xls": 0.302, "Xlr": 0.302, "Rfe": 150.0,
        "p": 4, "J": 1.662, "B": 0.0,
        "exp_type": "Direct-On-Line Starting (DOL)",
        "Tl_final": 202.0,
    },
    "Krause 2250 HP (1678 kW / 9180 N·m) — 2300 V/60 Hz": {
        # Krause (2002) — large motor, medium voltage, 2300 V / 60 Hz / 4 poles
        # T_nom = 1678000 / (1746×π/30) ≈ 9180 N·m; J = 63.87 kg·m² → ~8 s to reach 95% n_s
        "Vl": 2300.0, "f": 60.0, "Rs": 0.029, "Rr": 0.022,
        "input_mode": "Reactances (Ω)  —  measured at $f_{ref}$",
        "f_ref": 60.0, "Xm": 13.04, "Xls": 0.226, "Xlr": 0.226, "Rfe": 80.0,
        "p": 4, "J": 63.87, "B": 0.05,
        "exp_type": "Direct-On-Line Starting (DOL)",
        "Tl_final": 9180.0, "t_load": 8.0,
    },
}

# ── Convenience accessors ────────────────────────────────────────────────────

def get_mit_preset(name: str) -> dict[str, Any]:
    """Return a copy of the preset dict (safe for session_state mutation)."""
    return dict(MIT_PRESETS[name])


def mit_preset_names() -> list[str]:
    return list(MIT_PRESETS.keys())


# ── MachineParams kwargs for tests ───────────────────────────────────────────
# These dicts expose only the fields needed to instantiate MachineParams,
# extracted from MIT_PRESETS so tests and presets stay in sync.

def _mp_kwargs(name: str) -> dict[str, Any]:
    p = MIT_PRESETS[name]
    return {k: p[k] for k in ("Vl", "f", "Rs", "Rr", "Xm", "Xls", "Xlr", "Rfe", "p", "J", "B")}


KRAUSE_3HP   = _mp_kwargs("Default — Krause 3 HP (2.2 kW / 12 N·m) 220 V/60 Hz")
KRAUSE_50HP  = _mp_kwargs("Krause 50 HP (37 kW / 202 N·m) — 460 V/60 Hz")
KRAUSE_2250HP = _mp_kwargs("Krause 2250 HP (1678 kW / 9180 N·m) — 2300 V/60 Hz")
