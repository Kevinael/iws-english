# -*- coding: utf-8 -*-
"""
ui/theory/tabs/config.py
========================
Theory Tab 8a — Simulation Settings and Alerts.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn


def render_tab_config() -> None:
    st.markdown(
        "Guidelines for choosing the **simulation time** $t_{max}$ and the "
        "**integration step** $h$, with numerical stability criteria "
        "and alerts for scenarios that may compromise the simulation."
    )

    st.divider()
    _h4("Simulation Time — $t_{max}$")
    st.markdown(
        "Defines the temporal horizon of the numerical integration. "
        "Must be sufficient to contain the **complete starting transient** "
        "and, if necessary, steady-state stabilization."
    )
    st.markdown("**Practical reference:**")
    st.markdown(
        "- Typical starting transient: $t_{start} \\approx 3$–$5 \\times \\tau_m$, "
        "where $\\tau_m = J\\,\\omega_s / T_{e,nom}$.\n"
        "- Steady state: observe at least $5$–$10$ electrical cycles after "
        "$t_{start}$ to compute reliable RMS values.\n"
        "- Load pulse experiments: include margin after $t_{off}$ "
        "to visualize the return to steady state."
    )
    st.markdown(
        "- **Larger $t_{max}$:** Allows observation of long-term phenomena and stability verification. "
        "Increases computational cost linearly.\n"
        "- **Smaller $t_{max}$:** Fast processing, but risks truncating the analysis before stabilization "
        "— RMS values and mean torque become incorrect."
    )
    _div_warn(
        "**Warning:** very large $t_{max}$ combined with very small $h$ "
        "may cause **browser memory overflow**. "
        "Verify: $N = t_{max}/h$ stored points."
    )

    st.divider()
    _h4("Integration Step — $h$")
    st.markdown(
        "Temporal discretization for the solver (**LSODA / scipy.odeint**). "
        "The step controls numerical precision and integration stability."
    )
    st.markdown("**Numerical stability criterion:**")
    _eq(r"h \;\leq\; \frac{1}{20\,f}")
    st.markdown(
        "This criterion ensures at least **20 points per electrical cycle**, "
        "sufficient to integrate the fundamental frequency without numerical aliasing."
    )
    st.markdown(
        """
| Frequency $f$ | Recommended $h_{max}$ | Points/cycle |
|---|---|---|
| 50 Hz | $1{,}00\\;$ms | 20 |
| 60 Hz | $0{,}83\\;$ms | 20 |
| 60 Hz (high fidelity) | $0{,}20\\;$ms | 83 |
"""
    )
    st.markdown(
        "- **Larger $h$ (coarse step):** Fast simulation, but risks imprecision in starting currents "
        "and possible numerical divergence.\n"
        "- **Smaller $h$ (fine step):** High fidelity and stability — indicated for harmonic analysis "
        "and comparison with experimental data."
    )
    _div_warn(
        "**Warning:** for $f = 60\\;$Hz, steps $h > 1\\;$ms typically "
        "cause **integrator divergence** — currents grow "
        "unboundedly during the first starting cycles."
    )

    st.divider()
    _h4("Calibration Alerts — Critical Scenarios")
    st.markdown(
        "The following parameter combinations may compromise the physical validity "
        "of the simulation or cause numerical failure:"
    )
    st.markdown(
        """
| Scenario | Condition | Risk |
|---|---|---|
| **Magnetic saturation** | $V_l/f \\gg (V_l/f)_{nom}$ or very low $X_m$ | Flux exits the linear region — $L_m$ decreases, $dq$ model becomes invalid. Symptom: excessive magnetizing current. |
| **Stalling** | $T_L > T_{max}$ or $V_l < 85\\%\\,V_n$ | Motor does not accelerate — trapped in the unstable region of the $T_e \\times n$ curve. Current remains high and the rotor overheats. |
| **Numerical divergence** | $h > 1/(20f)$, $R_s \\approx 0$, or $X_m \\approx 0$ | Currents grow without bound during the first cycles. Simulator displays absurd values (NaN, $\\infty$). |
| **Memory overflow** | $N = t_{max}/h > 5 \\times 10^6$ points | Excessive NumPy array allocation — extreme slowness or browser freeze. |
| **Steady state not reached** | $t_{max} < 3\\,\\tau_m$ | RMS values and mean torque are computed over transient data — incorrect steady-state results without explicit warning. |
"""
    )

    st.divider()
    _h4("Quick Configuration Guide")
    st.markdown("**Step-by-step for a reliable simulation:**")
    st.markdown(
        "1. Compute $\\tau_m \\approx J\\,\\omega_s / T_{e,nom}$ and set $t_{max} \\geq 5\\,\\tau_m$.\n"
        "2. Choose $h \\leq 1/(20f)$ — for 60 Hz use $h = 0{,}5\\;$ms as a safe default.\n"
        "3. Verify $T_L < T_{max}$ before simulating (prevents stall).\n"
        "4. Confirm $V_l/f$ close to the rated value (prevents saturation).\n"
        "5. If simulation diverges, halve $h$ and repeat.\n"
        "6. If steady state does not appear in the plots, double $t_{max}$."
    )
