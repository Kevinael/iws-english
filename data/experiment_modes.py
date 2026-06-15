# -*- coding: utf-8 -*-
"""
experiment_modes.py
===================
Static look-up tables for experiment/operating-mode metadata.

Exported names
--------------
DC_MODES_BY_EXC     — available modes per DC excitation type
DC_MODE_LABELS      — human-readable label per DC mode key
DC_BRAKE_LABELS     — human-readable label per DC braking sub-mode
DC_EXC_LABELS       — human-readable label per DC excitation key
MIT_EXP_OPTIONS     — {label: key} map for MIT experiment selectbox
MIT_CRITICAL_EVENTS — {exp_key: [(description, latex_sym, config_key), ...]}
"""

from __future__ import annotations

# ── DC ───────────────────────────────────────────────────────────────────────

DC_MODES_BY_EXC: dict[str, list[str]] = {
    "sep_motor":    ["campo_fraco_dc", "frenagem_dc", "gerador_dc", "resistencia_dc", "dol_dc", "pulso_dc"],
    "shunt_motor":  ["frenagem_dc", "resistencia_dc", "dol_dc", "pulso_dc"],
    "series_motor": ["frenagem_dc", "resistencia_dc", "dol_dc", "pulso_dc"],
    "sep_gen":      ["gerador_dc"],
    "shunt_gen":    ["gerador_dc"],
}

DC_MODE_LABELS: dict[str, str] = {
    "campo_fraco_dc": "Field Weakening",
    "frenagem_dc":    "Electric Braking",
    "gerador_dc":     "Generator — Resistive Load",
    "resistencia_dc": "Series Resistance Starting",
    "dol_dc":         "Direct-On-Line Starting (DOL)",
    "pulso_dc":       "Load Pulse",
}

DC_BRAKE_LABELS: dict[str, str] = {
    "plugging":     "Plugging (Polarity Reversal)",
    "injecao_cc":   "DC Injection Braking",
    "regenerativo": "Regenerative Braking",
}

DC_EXC_LABELS: dict[str, str] = {
    "sep_motor":    "Separately Excited — Motor",
    "shunt_motor":  "Shunt (Parallel) — Motor",
    "series_motor": "Series — Motor",
    "sep_gen":      "Separately Excited — Generator",
    "shunt_gen":    "Shunt (Parallel) — Generator",
}

# ── MIT ──────────────────────────────────────────────────────────────────────

MIT_EXP_OPTIONS: dict[str, str] = {
    "Voltage Sag":                           "voltage_sag",
    "Shutdown (Power Cut)":                  "shutdown",
    "Electric Braking":                      "frenagem",
    "Generator Operation":                   "gerador",
    "Autotransformer Starting":              "comp",
    "Direct-On-Line Starting (DOL)":         "dol",
    "Star-Delta Starting (Y-D)":             "yd",
    "Load Pulse (apply and remove)":         "pulso_carga",
    "Soft-Starter (Voltage Ramp)":           "soft",
}

MIT_CRITICAL_EVENTS: dict[str, list[tuple[str, str, str]]] = {
    "yd":         [("Y→D switching",                  r"t_2",       "t_2"),
                   ("load application",               r"t_{carga}", "t_carga")],
    "comp":       [("autotransformer switching",      r"t_2",       "t_2"),
                   ("load application",               r"t_{carga}", "t_carga")],
    "soft":       [("ramp start",                     r"t_2",       "t_2"),
                   ("rated voltage reached",          r"t_{pico}",  "t_pico"),
                   ("load application",               r"t_{carga}", "t_carga")],
    "pulso_carga":[("load application",               r"t_{on}",    "t_carga"),
                   ("load removal",                   r"t_{off}",   "t_retirada")],
    "gerador":    [("prime mover torque application", r"t_2",       "t_2")],
    "shutdown":   [("load application",               r"t_{carga}", "t_carga"),
                   ("shutdown",                       r"t_{des}",   "t_cutoff")],
}
