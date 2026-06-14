# -*- coding: utf-8 -*-
"""
data/machines_dc.py
===================
Single source of truth for all DC machine (MCC) presets.

UI selectors and scripts all read from DC_PRESETS_BY_EXC — add new machines
here and they appear everywhere automatically.

HOW TO ADD A NEW PRESET
-----------------------
1. Choose the excitation key that matches your machine:

       "sep_motor"    — Separately excited motor
       "shunt_motor"  — Shunt (parallel) motor
       "series_motor" — Series motor
       "sep_gen"      — Separately excited generator
       "shunt_gen"    — Shunt generator

2. Add an entry under that key. The dict key is the display name shown in the
   UI selector. Fields vary by excitation type — see the templates below.

   SEPARATELY EXCITED MOTOR / GENERATOR:
       "My Sep. Motor 48 V": {
           "Va": 48.0,   # armature voltage [V]
           "Ra": 0.2,    # armature resistance [Ω]
           "La": 0.005,  # armature inductance [H]
           "Vf": 24.0,   # field voltage [V]
           "Rf": 10.0,   # field resistance [Ω]
           "Lf": 1.0,    # field inductance [H]
           "kb": 0.5,    # back-EMF / torque constant [V·s/rad]
           "J":  0.1,    # rotor inertia [kg·m²]
           "B":  0.01,   # viscous friction [N·m·s/rad]
           "Tload": 5.0, # load torque [N·m]  (negative for generators)
           # Generator only — include load circuit:
           # "Rl": 2.0,  # load resistance [Ω]
           # "Ll": 0.01, # load inductance [H]
       },

   SHUNT MOTOR / GENERATOR (Vf = Va implicitly — omit Vf):
       "My Shunt Motor 200 V": {
           "Va": 200.0, "Ra": 0.3,   "La": 0.01,
           "Rf": 80.0,  "Lf": 4.0,
           "kb": 1.5,   "J": 1.0,   "B": 0.05,  "Tload": 100.0,
           # Generator: add "Rl" and "Ll", set Tload negative
       },

   SERIES MOTOR (field in series with armature — Rf/Lf are series winding):
       "My Series Motor 120 V": {
           "Va": 120.0, "Ra": 0.4,   "La": 0.01,
           "Rf": 0.3,   "Lf": 0.05,
           "kb": 3.0,   "J": 0.5,   "B": 0.02,  "Tload": 60.0,
       },

3. Optionally add UI control hints:
       "_dc_mode_sel": "Direct-On-Line Starting (DOL)",  # pre-select mode
       "dol_vazio":    False,                             # start under load

4. That is all. No other file needs to be touched.
   - The UI selector (ui_components/sim_config_dc.py) picks it up automatically.
   - Scripts (analysis/, utils/) should import DC_PRESETS_BY_EXC directly.
"""
from __future__ import annotations
from typing import Any

# ── DC Presets keyed by excitation type ──────────────────────────────────────
# Sources: Sen (2013), Fitzgerald/Umans (2014), Okoro et al. (2008)

DC_PRESETS_BY_EXC: dict[str, dict[str, dict[str, Any]]] = {
    "sep_motor": {
        "Sep. Motor 220 V — Sen Ex. 9.2": {
            "Va": 220.0, "Ra": 0.5,   "La": 0.01,
            "Vf": 220.0, "Rf": 220.0, "Lf": 10.0,
            "kb": 1.05,  "J": 2.5,    "B": 0.05,   "Tload": 25.0,
        },
        "Sep. Motor 24 V — Okoro et al. (2008)": {
            # Okoro (2008) — small lab motor, validated against Scilab dcmei.sce
            "Va": 24.0,  "Ra": 0.013, "La": 0.01,
            "Vf": 12.0,  "Rf": 1.43,  "Lf": 0.167,
            "kb": 0.004, "J": 0.21,   "B": 1.074e-6, "Tload": 2.493,
            "_dc_mode_sel": "Direct-On-Line Starting (DOL)",
            "dol_vazio": False,
        },
        "Sep. Motor 500 V 100 HP — Fitzgerald Ex. 10.2/10.3": {
            "Va": 500.0, "Ra": 0.084, "La": 0.01,
            "Vf": 300.0, "Rf": 109.0, "Lf": 5.0,
            "kb": 1.91,  "J": 17.5,   "B": 0.1,    "Tload": 286.0,
        },
    },
    "shunt_motor": {
        "Shunt Motor 24 V — Okoro et al. (2008)": {
            # Okoro (2008) — shunt variant; Va feeds both armature and field
            "Va": 24.0,  "Ra": 0.013, "La": 0.01,
            "Rf": 1.43,  "Lf": 0.167,
            "kb": 0.004, "J": 0.21,   "B": 1.074e-6, "Tload": 2.493,
            "_dc_mode_sel": "Direct-On-Line Starting (DOL)",
            "dol_vazio": False,
        },
        "Shunt Motor 100 V 12 kW — Sen Ex. 4.6": {
            "Va": 100.0, "Ra": 0.1,   "La": 0.01,
            "Rf": 101.0, "Lf": 5.0,
            "kb": 0.949, "J": 0.5,    "B": 0.054,  "Tload": 113.9,
        },
        "Shunt Motor 450 V 50 kW — Fitzgerald Ex. 7.4": {
            "Va": 450.0, "Ra": 0.242, "La": 0.02,
            "Rf": 167.0, "Lf": 8.0,
            "kb": 4.29,  "J": 5.0,    "B": 0.1,    "Tload": 497.0,
        },
    },
    "series_motor": {
        "Series Motor 24 V — Okoro et al. (2008)": {
            # Okoro (2008) — series variant; Rf/Lf are series field winding
            "Va": 24.0,  "Ra": 0.013, "La": 0.01,
            "Rf": 0.026, "Lf": 0.167,
            "kb": 0.004, "J": 0.21,   "B": 1.074e-6, "Tload": 2.493,
            "_dc_mode_sel": "Direct-On-Line Starting (DOL)",
            "dol_vazio": False,
        },
        "Series Motor 220 V 7 HP — Sen Ex. 4.9": {
            "Va": 220.0, "Ra": 0.6,  "La": 0.02,
            "Rf": 0.4,   "Lf": 0.05,
            "kb": 6.2,   "J": 2.0,   "B": 0.05,   "Tload": 155.2,
        },
        "Heavy Series Motor 600 V — Sen Prob. 4.39": {
            "Va": 600.0, "Ra": 0.5,  "La": 0.05,
            "Rf": 0.5,   "Lf": 0.1,
            "kb": 10.02, "J": 10.0,  "B": 0.1,    "Tload": 751.5,
        },
    },
    "sep_gen": {
        "Sep. Generator 200 V — Sen Ex. 9.1": {
            "Va": 200.0, "Ra": 0.25,  "La": 0.02,
            "Vf": 200.0, "Rf": 100.0, "Lf": 25.0,
            "kb": 1.91,  "J": 2.5,    "B": 0.1,    "Tload": -25.0,
            "Rl": 1.0,   "Ll": 0.15,
        },
        "Sep. Generator 250 V 100 kW — Fitzgerald Ex. 7.1": {
            "Va": 250.0, "Ra": 0.025, "La": 0.005,
            "Vf": 250.0, "Rf": 100.0, "Lf": 5.0,
            "kb": 1.99,  "J": 10.0,   "B": 0.2,    "Tload": -800.0,
            "Rl": 0.625, "Ll": 0.05,
        },
    },
    "shunt_gen": {
        "Shunt Generator 100 V 12 kW — Sen Ex. 4.2/4.3": {
            "Va": 100.0, "Ra": 0.1,   "La": 0.01,
            "Rf": 100.0, "Lf": 10.0,
            "kb": 0.95,  "J": 2.0,    "B": 0.05,   "Tload": -115.0,
            "Rl": 0.83,  "Ll": 0.01,
        },
        "Shunt Generator 250 V 100 kW — Fitzgerald Ex. 7.7": {
            "Va": 250.0, "Ra": 0.025, "La": 0.005,
            "Rf": 100.0, "Lf": 5.0,
            "kb": 1.99,  "J": 10.0,   "B": 0.1,    "Tload": -800.0,
            "Rl": 0.625, "Ll": 0.05,
        },
    },
}

# Flat dict for scripts that need a name → params mapping (legacy compat)
DC_PRESETS_FLAT: dict[str, dict[str, Any]] = {
    name: {**vals, "excitation": exc}
    for exc, presets in DC_PRESETS_BY_EXC.items()
    for name, vals in presets.items()
}
