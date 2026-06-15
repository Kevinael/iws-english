# -*- coding: utf-8 -*-
"""
data/ui_labels.py
=================
Single source of truth for UI selector labels and machine registry.

All UI modules (tim_config, sim_config_dc, IWS_UI) import from here so that
label changes propagate automatically without touching widget code.

CONTENTS
--------
MIT_INPUT_MODE_LABELS   — parameter input mode radio options (Reactances / Inductances)
MIT_PARAM_SOURCE_LABELS — data source radio options (manual / nameplate / IEEE)
MIT_IEEE_SPLIT_LABELS   — leakage split class labels keyed by NEMA class code
MACHINES                — available machine registry (key, name, icon, tag, disabled)
DC_PARAM_SOURCE_LABELS  — DC data source radio options (manual / nameplate / IEEE 113)
"""

from __future__ import annotations

MIT_INPUT_MODE_LABELS: list[str] = [
    "Reactances (Ω)  —  measured at $f_{ref}$",
    "Inductances (H)  —  frequency-independent",
]

MIT_PARAM_SOURCE_LABELS: list[str] = [
    "Enter parameters manually",
    "Estimate from nameplate data",
    "Determine from IEEE 112 tests",
]

MIT_IEEE_SPLIT_LABELS: dict[str, str] = {
    "B":      "Class B — 40% / 60% (NEMA default)",
    "A":      "Class A — 50% / 50%",
    "C":      "Class C — 30% / 70%",
    "D":      "Class D — 50% / 50%",
    "WR":     "Wound Rotor — 50% / 50%",
    "custom": "Custom (define Xls/Xk fraction)",
}

MACHINES: list[dict] = [
    {"key": "tim",  "name": "Three-Phase Induction Motor", "icon": "TIM", "tag": "Available",         "disabled": False},
    {"key": "dc",   "name": "DC Motor",                    "icon": "DCM", "tag": "Available",         "disabled": False},
    {"key": "sync", "name": "Synchronous Generator",       "icon": "SG",  "tag": "Under development", "disabled": True},
    {"key": "tr",   "name": "Transformer",                 "icon": "TR",  "tag": "Under development", "disabled": True},
]

DC_PARAM_SOURCE_LABELS: list[str] = [
    "Enter parameters manually",
    "Estimate from nameplate data",
    "Determine from IEEE 113 tests",
]
