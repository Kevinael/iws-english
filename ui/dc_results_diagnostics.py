# -*- coding: utf-8 -*-
"""
dc_results_diagnostics.py
=========================
Tab 3 — Diagnostics & Faults: commutation/current analysis and automated anomaly flags (DC machine).

Responsibilities:
  - Render peak/steady/ripple armature-current metrics.
  - Flag overcurrent, numerical failure, field instability and non-convergence.

Relationships:
  Imported by : ui.dc_results
  Imports     : core.dc.facade, core.constants, numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.dc.facade import DCMachineParams
from core.constants import (
    DC_OVERCURRENT_CRIT_RATIO,
    DC_ARMATURE_RIPPLE_WARN_PCT,
    DC_FIELD_INSTABILITY_RATIO,
    DC_STEADY_STATE_CONV_THRESHOLD,
)


def render_dc_tab_diagnostics(
    res: dict,
    mp: DCMachineParams,
    exc: str,
    d: int,
) -> None:
    n_ss   = res.get("n_ss",   0.0)
    ia_ss  = res.get("ia_ss",  0.0)
    ifd_ss = res.get("ifd_ss", 0.0)
    wm_ss  = res.get("wm_ss",  0.0)

    st.markdown('<p class="slabel">Commutation and Current Analysis</p>', unsafe_allow_html=True)

    ia_arr  = res["ia"]
    ia_max  = float(np.max(np.abs(ia_arr)))
    ia_std  = float(np.std(ia_arr[len(ia_arr)//2:]))

    d1, d2, d3 = st.columns(3)
    d1.metric("Peak $i_a$ (A)",              f"{ia_max:.{d}f}")
    d2.metric("$i_a$ steady state (A)",      f"{ia_ss:.{d}f}")
    d3.metric("Ripple $\\sigma(i_a)$",       f"{ia_std:.{d}f}")

    _ripple_rel = ia_std / max(abs(ia_ss), 1e-6) * 100
    if _ripple_rel > DC_ARMATURE_RIPPLE_WARN_PCT:
        st.warning(f"Relative $i_a$ ripple = {_ripple_rel:.1f}% — check $L_a$ and switching frequency.")

    anomalias: list[tuple[str, str, str]] = []

    if ia_max > DC_OVERCURRENT_CRIT_RATIO * max(abs(ia_ss), 1e-6):
        anomalias.append(("🔴 Critical", "Extreme overcurrent at starting",
                           f"Peak {ia_max:.1f} A = {ia_max/max(abs(ia_ss),1e-6):.0f}× steady state. "
                           "Use series resistance or reduce $V_a$."))

    if not res.get("success", True):
        anomalias.append(("🔴 Critical", "Integrator numerical failure",
                           "Reduce $h$ to 1×10⁻⁵ s or check parameters."))

    if exc not in ("series_motor",):
        ifd_arr = res["ifd"]
        ifd_std = float(np.std(ifd_arr[len(ifd_arr)//2:]))
        if ifd_std > DC_FIELD_INSTABILITY_RATIO * max(abs(ifd_ss), 1e-6):
            anomalias.append(("🟡 Warning", "Field instability",
                               f"$\\sigma(i_{{fd}})$ = {ifd_std:.4f} A in steady state. "
                               "Check $R_f$ and $L_f$."))

    wm_arr = res["wm"]
    if len(wm_arr) > 10 and float(np.mean(wm_arr[-10:])) < DC_STEADY_STATE_CONV_THRESHOLD * abs(wm_ss) and abs(wm_ss) > 1:
        anomalias.append(("🟡 Warning", "Steady state not reached",
                           f"$\\omega_m$ still in transient at end of simulation. "
                           "Increase $t_{{max}}$."))

    if not anomalias:
        st.success("🟢 No anomalies detected.")
    else:
        for sev, titulo, desc in anomalias:
            with st.expander(f"{sev} — {titulo}", expanded=True):
                st.write(desc)
