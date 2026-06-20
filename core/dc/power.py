# -*- coding: utf-8 -*-
"""
power.py
========
Canonical DC-machine steady-state loss/power computation. Single source of
truth for armature/field copper loss, friction loss, mechanical/electrical
power and efficiency.

Responsibilities:
  - compute_losses_dc(res, mp): full DC power balance + percentage breakdown

Relationships:
  Imported by : viz.pdf_dc, ui_components.sim_results_dc
  Imports     : (none — pure numeric, no streamlit/plotly)
"""

from __future__ import annotations

# Excitation tags that denote generator operation.
_GEN_EXC = ("sep_gen", "shunt_gen")


def _mp_get(mp, key: str, default: float = 0.0) -> float:
    if mp is None:
        return default
    if isinstance(mp, dict):
        return float(mp.get(key, default))
    return float(getattr(mp, key, default))


def compute_losses_dc(res: dict, mp) -> dict:
    """Compute the DC-machine steady-state power balance.

    Generator operation is inferred from ``mp.excitation``. Returns the loss
    components (``P_Ra``, ``P_Rf``, ``P_mec``, ``P_mec_out``, ``P_elec``),
    their percentages against the dominant power, and the efficiency ``eta``.
    """
    ia_ss  = float(res.get("ia_ss",  0.0))
    ifd_ss = float(res.get("ifd_ss", 0.0))
    wm_ss  = float(res.get("wm_ss",  0.0))
    Te_ss  = float(res.get("Te_ss",  0.0))

    Va  = _mp_get(mp, "Va", 0.0)
    Ra  = _mp_get(mp, "Ra", 0.0)
    Rf  = _mp_get(mp, "Rf", 0.0)
    B   = _mp_get(mp, "B",  0.0)
    exc = getattr(mp, "excitation", "sep_motor") if mp is not None else "sep_motor"
    is_gen = exc in _GEN_EXC

    P_Ra      = ia_ss ** 2 * Ra
    P_Rf      = ifd_ss ** 2 * Rf if exc not in ("series_motor",) else 0.0
    P_mec     = B * wm_ss ** 2
    P_mec_out = abs(Te_ss) * abs(wm_ss)
    P_elec    = abs(Va) * abs(ia_ss)

    if is_gen:
        eta = P_elec / max(P_mec_out, 1e-9) * 100.0 if P_mec_out > 0 else 0.0
    else:
        eta = P_mec_out / max(P_elec, 1e-9) * 100.0 if P_elec > 0 else 0.0

    total = max(P_elec, 1e-9)
    return {
        "P_Ra":        P_Ra,
        "P_Rf":        P_Rf,
        "P_mec":       P_mec,
        "P_mec_out":   P_mec_out,
        "P_elec":      P_elec,
        "eta":         eta,
        "pct_Ra":      P_Ra      / total * 100.0,
        "pct_Rf":      P_Rf      / total * 100.0,
        "pct_mec":     P_mec     / total * 100.0,
        "pct_mec_out": P_mec_out / total * 100.0,
    }
