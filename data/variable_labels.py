# -*- coding: utf-8 -*-
"""
data/variable_labels.py
=======================
Single source of truth for variable display labels and plot catalogs (MIT and DC).

UI components, tests, and selectors read from these dicts — add new variables
here and they appear everywhere automatically.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# MIT (Three-Phase Induction Motor)
# ─────────────────────────────────────────────────────────────────────────────

MIT_VAR_MECANICAS: dict[str, str] = {
    "Electromagnetic Torque  Tₑ  (N·m)":  "Te",
    "Rotor Speed  n  (RPM)":              "n",
    "Angular Velocity  ωᵣ  (rad/s)":      "wr",
}

MIT_VAR_ELETRICAS: dict[str, str] = {
    "Phase A Current — Stator  iₐₛ  (A)":  "ias",
    "Phase B Current — Stator  ibₛ  (A)":  "ibs",
    "Phase C Current — Stator  icₛ  (A)":  "ics",
    "Phase A Current — Rotor  iₐᵣ  (A)":   "iar",
    "Phase B Current — Rotor  ibᵣ  (A)":   "ibr",
    "Phase C Current — Rotor  icᵣ  (A)":   "icr",
    "d-Component — Stator  idₛ  (A)":       "ids",
    "q-Component — Stator  iqₛ  (A)":       "iqs",
    "d-Component — Rotor  idᵣ  (A)":        "idr",
    "q-Component — Rotor  iqᵣ  (A)":        "iqr",
    "Phase Voltage  Vₐ  (V)":               "Va",
    "Phase Voltage  Vb  (V)":               "Vb",
    "Phase Voltage  Vc  (V)":               "Vc",
}

MIT_VAR_CATALOG: dict[str, str] = {
    **MIT_VAR_MECANICAS,
    **MIT_VAR_ELETRICAS,
}

# ─────────────────────────────────────────────────────────────────────────────
# DC (Direct Current Machine)
# ─────────────────────────────────────────────────────────────────────────────

DC_VAR_MECANICAS: dict[str, str] = {
    "Angular Velocity  ωm  (rad/s)":          "wm",
    "Speed  n  (RPM)":                        "n",
    "Electromagnetic Torque  Tₑ  (N·m)":      "Te",
}

DC_VAR_ELETRICAS: dict[str, str] = {
    "Armature Current  iₐ  (A)":              "ia",
    "Field Current  i_fd  (A)":               "ifd",
    "Back-EMF  Eₐ  (V)":                      "Ea",
    "Terminal Voltage  Vt  (V)":              "Vt",
}

DC_VAR_OPTIONS: dict[str, str] = {**DC_VAR_MECANICAS, **DC_VAR_ELETRICAS}

DC_DEFAULT_VARS_MEC: list[str] = ["Electromagnetic Torque  Tₑ  (N·m)", "Speed  n  (RPM)"]
DC_DEFAULT_VARS_ELE: list[str] = ["Armature Current  iₐ  (A)"]
DC_DEFAULT_VARS: list[str] = ["ia", "wm", "Te"]
