# -*- coding: utf-8 -*-
"""
ui/theory/tabs/manual.py
========================
Theory Tab 6 — Simulator User Manual.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn


def render_tab_manual_de_uso() -> None:
    st.markdown(
        "This manual describes, in sequence, the steps required to configure, "
        "run, and analyze a test in the Electrical Machines Simulator (EMS). Each step "
        "indicates the corresponding files and functions in the implementation, enabling "
        "traceability between the interface, code, and theoretical foundations."
    )

    _h4("Workflow Overview")
    st.markdown(
        "Using the simulator follows five steps in chronological order:"
    )
    st.markdown(
        "1. **Equipment selection** — choose a motor from the catalog or enter "
        "custom parameters.\n"
        "2. **Physical parameter entry** — electrical, magnetic, mechanical, "
        "grid, and thermal parameters.\n"
        "3. **Source and Park reference frame definition** — balanced sinusoidal source, "
        "grid impedance, choice of $dq$ reference frame.\n"
        "4. **Experiment configuration** — select the test type "
        "(DOL, Y-Δ, Soft-Starter, etc.) and disturbances.\n"
        "5. **Execution, plot analysis, and export** — reading transient and steady-state "
        "plots, PDF export."
    )

    st.divider()

    _h4("Step 1 — Equipment Selection")
    st.markdown(
        "In the sidebar, the `render_machine_selector` selector "
        "(`ui_components/sim_config.py`) offers two paths:"
    )
    st.markdown(
        "- **NEMA motor catalog** — pre-fills the `MachineParams` dataclass with "
        "tabulated values for typical motors (3 HP, 25 HP, 500 HP, among others). "
        "Indicated for quick validation and comparative studies.\n"
        "- **Custom** — all fields are editable and must be entered manually. "
        "Indicated for reproducing real tests or specific bibliographic references."
    )

    st.divider()

    _h4("Step 2 — Physical Parameter Entry")
    st.markdown(
        "All fields of the `MachineParams` dataclass "
        "(`core/machine_model.py:40–76`) must be filled in. The groups are:"
    )

    st.markdown("**Electrical parameters** (T-equivalent circuit):")
    st.markdown(
        "- $V_l$ — RMS line voltage applied at the terminals (V).\n"
        "- $f$ — source frequency (Hz). Defines $\\omega_e = 2\\pi f$.\n"
        "- $R_s$ — stator resistance per phase (Ω).\n"
        "- $R_r'$ — rotor resistance referred to the stator (Ω).\n"
        "- $X_m$ — magnetizing reactance (Ω).\n"
        "- $X_{ls}$ — stator leakage reactance (Ω).\n"
        "- $X_{lr}'$ — referred rotor leakage reactance (Ω).\n"
        "- $R_{fe}$ — parallel resistance representing core losses (Ω)."
    )

    st.markdown("**Magnetic parameters** — input mode:")
    st.markdown(
        "The user chooses between providing **reactances** (mode $X$) or **inductances** "
        "(mode $L$), via the `input_mode` switch. In both cases the reference frequency "
        "$f_{ref}$ at which the values were measured must be supplied. The internal conversion "
        "uses $\\omega_{b,ref} = 2\\pi f_{ref}$ "
        "(cf. `core/machine_model.py:88–101`):"
    )
    _eq(r"L_m = \frac{X_m}{\omega_{b,ref}}, \qquad L_{ls} = \frac{X_{ls}}{\omega_{b,ref}}, \qquad L_{lr}' = \frac{X_{lr}'}{\omega_{b,ref}}")
    st.markdown(
        "When $f$ (operating frequency) is changed, the operational reactances "
        "$X_{ls,a}$, $X_{lr,a}$, and $X_{m,a}$ are recalculated via "
        "$X = \\omega_b\\,L$."
    )

    st.markdown("**Mechanical parameters**:")
    st.markdown(
        "- $p$ — number of poles (integer). Defines synchronous speed "
        "$n_s = 120\\,f / p$ (rpm).\n"
        "- $J$ — total rotational moment of inertia (kg·m²).\n"
        "- $B$ — viscous friction coefficient (N·m·s/rad). If zero, estimated by "
        "empirical rule from rated torque.\n"
        "- $T_{nom}$ — rated load torque, e.g. $T_{nom} = 80\\;\\text{N·m}$ "
        "(used as reference in constant-load tests)."
    )

    st.markdown("**Grid impedance** (Voltage Sag and line voltage drop):")
    st.markdown(
        "- $R_{grid}$ — per-phase line resistance (Ω).\n"
        "- $L_{grid}$ — per-phase line inductance (H). Absorbed into "
        "$X_{ls,eff} = X_{ls,a} + \\omega_b\\,L_{grid}$ "
        "(cf. `core/machine_model.py:132`)."
    )

    st.divider()

    _h4("Step 3 — Electrical Parameter Acquisition Modes")
    st.markdown(
        "The parameters $R_s, R_r', X_m, X_{ls}, X_{lr}', R_{fe}$ can be obtained by "
        "three distinct paths:"
    )
    st.markdown(
        "1. **Manual** — values entered directly. Requires prior knowledge "
        "(previous tests or bibliography).\n"
        "2. **Nameplate Estimator** — estimate from nameplate data, without "
        "physical tests. Indicated for preliminary analyses and sensitivity studies "
        "(see Tab 7, section 7.1).\n"
        "3. **IEEE Std 112-2017 Estimator** — estimate from three physical tests "
        "(DC, no-load, locked rotor). Indicated for model validation "
        "and commissioning (see Tab 7, section 7.2)."
    )
    _div_warn(
        "The Nameplate and IEEE Std 112-2017 methods are **complementary**, not "
        "alternatives: use Nameplate when only nameplate data are available; use IEEE "
        "112 when physical test data are available."
    )

    st.divider()

    _h4("Step 4 — Park Transform Reference Frame")
    st.markdown(
        "The user selects the reference frame in which the $dq$ variables are expressed. "
        "Three options are available in the simulator:"
    )
    st.markdown(
        "- **Synchronous** ($\\omega_{ref} = \\omega_e$) — in steady state, all "
        "$dq$ components become constant (DC). Recommended for steady-state analysis "
        "and vector control.\n"
        "- **Rotor-fixed** ($\\omega_{ref} = \\omega_r$) — locked to the rotor. Useful for "
        "rotor fault diagnosis (broken bars) and synchronous machine analysis.\n"
        "- **Stationary** ($\\omega_{ref} = 0$) — $dq$ variables oscillate at the "
        "grid frequency. Useful for visualizing $\\alpha\\beta$ waveforms."
    )
    st.markdown(
        "The choice **does not alter the physical results** ($T_e$, $\\omega_r$, $abc$ currents, "
        "powers) — only the internal representation basis of the $dq$ variables. "
        "The complete mathematical background is in Tab 5 (Operating Dynamics)."
    )

    st.divider()

    _h4("Step 5 — Experiment Configuration")
    st.markdown(
        "The simulator offers a catalog of pre-configured tests. The simulation time "
        "$t_{max}$ is estimated automatically in "
        "`ui_components/sim_runner.py:calc_tmax_auto` for each type:"
    )
    st.markdown(
        "| Experiment | Description | Typical $t_{max}$ |\n"
        "|---|---|---|\n"
        "| **DOL** | Direct-on-line starting at full voltage | $0{,}5\\;\\text{s}$ |\n"
        "| **Y-Δ** | Star-delta starting, switchover at $t_{sw}$ | $0{,}8$–$1{,}2\\;\\text{s}$ |\n"
        "| **Soft-Starter** | Voltage ramp via angle control | $1{,}0$–$2{,}0\\;\\text{s}$ |\n"
        "| **Load Pulse** | Load step after steady state | $1{,}5$–$2{,}0\\;\\text{s}$ |\n"
        "| **Generator** | Operation as generator (mechanical drive) | $1{,}0$–$3{,}0\\;\\text{s}$ |\n"
        "| **Voltage Sag** | Momentary voltage sag | $1{,}0$–$2{,}0\\;\\text{s}$ |\n"
        "| **Shutdown** | Power cut-off and coast-down | $2{,}0$–$5{,}0\\;\\text{s}$ |\n"
        "| **Comparative** | Overlay of multiple starting methods | $0{,}8\\;\\text{s}$ |"
    )
    st.markdown(
        "For each experiment, the specific parameters (starting voltage, switchover instant, "
        "sag magnitude, etc.) are visible in the sidebar after selection. "
        "The complete catalog is in Tab 8."
    )

    st.divider()

    _h4("Step 6 — Reading the Plots")
    st.markdown(
        "After execution, the **Results** tab presents five groups of plots. "
        "The following analysis order is recommended:"
    )

    st.markdown("**1. Starting transient** — current and torque peaks:")
    st.markdown(
        "- Typical inrush current: $I_{start} \\approx 6\\text{–}8\\,I_n$ "
        "in the first $50$–$100\\;\\text{ms}$.\n"
        "- Electromagnetic torque peak: may reach $2$–$3\\,T_{nom}$.\n"
        "- Acceleration time to $95\\%\\,\\omega_{sync}$: depends on $J$, $T_L$, and the "
        "starting method used."
    )

    st.markdown("**2. Steady state** — reliable RMS window:")
    st.markdown(
        "- Wait for complete stabilization before collecting RMS values — "
        "typically $5$–$10$ electrical cycles after the last transient.\n"
        "- In the synchronous reference frame, $i_{ds}$ and $i_{qs}$ should be constant in steady state."
    )

    st.markdown("**3. $abc$ currents** — symmetry check:")
    st.markdown(
        "- Symmetry $|i_a| \\approx |i_b| \\approx |i_c|$ confirms phase balance.\n"
        "- Asymmetry indicates voltage unbalance, phase loss, or rotor fault."
    )

    st.markdown("**4. $dq$ components** — convergence test:")
    st.markdown(
        "- In the synchronous reference frame, $i_{ds}$ and $i_{qs}$ become constant in steady state.\n"
        "- Persistent ripple suggests numerical resonance or inconsistent parameters."
    )

    st.markdown("**5. Dynamic $T_e \\times n$ curve** — comparison with static curve:")
    st.markdown(
        "- The dynamic trajectory spirals around the static curve "
        "(`viz/plotly_charts.build_fig_torque_speed`).\n"
        "- In steady state, the operating point coincides with the intersection of the static curve "
        "and the load line $T_L(\\omega_r)$."
    )

    st.divider()

    _h4("Step 7 — Result Export")
    st.markdown(
        "Three PDF report formats are available "
        "(cf. `ui_components/sim_results.py:904–963`):"
    )
    st.markdown(
        "- **PDF v1** — summary report with main plots and parameter table.\n"
        "- **PDF v2 (AC)** — extended technical report with AC steady-state analysis, "
        "harmonics, and $dq$ components.\n"
        "- **PDF v2 (DB)** — dynamic-ballistic report with transient overlay "
        "and power flow diagram."
    )
    st.markdown(
        "Export buttons are generated via `st.download_button`. The content "
        "includes all rendered Plotly plots and the final `MachineParams` table "
        "used in the simulation."
    )

    st.divider()

    _h4("Internal References")
    st.markdown(
        "For theoretical background and details, refer to:"
    )
    st.markdown(
        "- **Tab 1** — Modeling and Equivalent Circuits (static and Krause $0dq$ model).\n"
        "- **Tab 2** — Dynamic Behavior and Torque, with the $T_e(s)$ curve and Boucherot theorem.\n"
        "- **Tab 3** — Energy balance and power flow.\n"
        "- **Tab 4** — Parameter sensitivity of the equivalent circuit.\n"
        "- **Tab 5** — Operating dynamics and Park transform.\n"
        "- **Tab 7** — Nameplate and IEEE Std 112-2017 estimators.\n"
        "- **Tab 8** — Numerical settings and complete experiment catalog."
    )
