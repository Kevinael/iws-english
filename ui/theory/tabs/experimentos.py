# -*- coding: utf-8 -*-
"""
ui/theory/tabs/experimentos.py
================================
Theory Tab 8b — Experiments and Grid Disturbances.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn
from ui.theory_interactive import (
    render_startup_comparison,
    render_imbalance_phasor,
    render_mcsa,
)


def render_tab_experimentos() -> None:
    st.markdown(
        "Each simulator experiment corresponds to a distinct physical scenario — "
        "starting, loading, generation, or grid fault. "
        "This tab describes the principle of each test, the governing equations, "
        "and the observable phenomena in the plots."
    )

    st.divider()
    st.markdown("### Starting Methods")

    _h4("Direct-On-Line Starting — DOL")
    st.markdown(
        "The stator is connected directly to the grid at full voltage $V_l$ at $t=0$. "
        "Simplest method, but most aggressive: starting current typically reaches "
        "6 to 8 times the rated value, generating a torque peak and voltage sag in the grid."
    )
    _eq(r"I_{start} \approx (6\text{ to }8)\,I_n \quad (s=1,\; V = V_{nom})")
    st.markdown(
        "The simulator offers two operating modes:"
    )
    st.markdown(
        "- **No-load start:** $t = 0$ — rated voltage applied, motor accelerates without load ($T_l = 0$). "
        "At $t_{load}$, resistive torque applied as a step — allows observing the speed dip "
        "and current transient when connecting the load.\n"
        "- **Loaded start:** $t = 0$ — rated voltage and load $T_l$ applied simultaneously; "
        "motor accelerates against full load from the initial instant."
    )
    st.markdown(
        "- **Observe:** starting current peak, maximum torque (pull-out), acceleration time, "
        "speed dip upon load application.\n"
        "- **Risk:** thermal overload if $T_l > T_{max}$ — motor stalls."
    )

    st.write("")
    _h4("Star-Delta Starting — Y-Δ")
    st.markdown(
        "During the star phase ($0 < t < t_2$), each winding receives $V_l/\\sqrt{3}$, "
        "reducing starting current and torque to $1/3$ of the delta values:"
    )
    _eq(r"I_{start,Y} = \frac{1}{3}\,I_{start,\Delta}, \quad T_{start,Y} = \frac{1}{3}\,T_{start,\Delta}")
    st.markdown(
        "At $t_2$, the contactor switches to delta: voltage jumps to $V_l$ and a "
        "**second current peak** occurs — often overlooked in practice, "
        "but clearly visible in the simulator. Load $T_l$ is applied at $t_{load} > t_2$."
    )
    st.markdown(
        "- **Observe:** two current peaks (Y start and Y→Δ switchover), reduced starting torque.\n"
        "- **Limitation:** applicable only to motors designed for delta connection at line voltage."
    )

    st.write("")
    _h4("Autotransformer Starting")
    st.markdown(
        "An autotransformer with tap $k$ ($0 < k < 1$) applies $k\\,V_l$ to the motor during starting. "
        "Grid current is reduced by factor $k^2$:"
    )
    _eq(r"I_{grid} = k^2\,I_{start,\,V_{nom}}, \quad T_{start} = k^2\,T_{start,\,V_{nom}}")
    st.markdown(
        "At $t_2$, switchover to full voltage occurs. The simulator allows choosing tap "
        "$k$ via slider and observing the trade-off between current reduction and available starting torque."
    )
    st.markdown(
        "- **Observe:** reduced grid current at starting, peak at switchover, limited starting torque.\n"
        "- **Advantage over Y-Δ:** adjustable tap allows optimizing the current × torque trade-off."
    )

    st.write("")
    _h4("Soft-Starter — Voltage Ramp")
    st.markdown(
        "An electronic converter applies a rising voltage from $V_0 = k\\,V_l$ to $V_l$ "
        "over the ramp $[t_2,\\, t_{peak}]$:"
    )
    _eq(r"V(t) = V_0 + (V_l - V_0)\,\frac{t - t_2}{t_{peak} - t_2}, \quad t_2 \leq t \leq t_{peak}")
    st.markdown(
        "The event sequence in the simulator is:"
    )
    st.markdown(
        "- $t = 0$ — motor starts at initial voltage $V_0 = k\\,V_l$; limited starting current and torque.\n"
        "- $t = t_2$ — voltage ramp initiated: voltage rises linearly from $V_0$ to $V_l$.\n"
        "- $t = t_{peak}$ — rated voltage reached; Soft-Starter disconnected, motor in direct operation "
        "(ramp duration: $t_{peak} - t_2$).\n"
        "- $t = t_{load}$ — load $T_l$ applied to the shaft."
    )
    st.markdown(
        "Current and torque grow smoothly over the ramp, eliminating the abrupt peak of switched starting methods."
    )
    st.markdown(
        "- **Observe:** no current peak, slower acceleration, nearly constant current during the ramp.\n"
        "- **Risk:** excessively long ramp increases rotor Joule losses during acceleration ($P_{cu,2} = s\\,P_{ag}$)."
    )

    st.divider()
    _h4("Starting Current Comparison — Interactive Visualization")
    render_startup_comparison()

    st.divider()
    st.markdown("### Load Tests")

    _h4("Load Application — No-Load Start")
    st.markdown(
        "Motor starts at no load ($T_l = 0$) and, at $t_{load}$, receives resistive torque "
        "$T_l$ as a step. Reference test to measure the **speed dip** "
        "$\\Delta n$ and the current increase upon load connection:"
    )
    _eq(r"\Delta n = n_{no-load} - n_{loaded} = n_s\,(s_{loaded} - s_{no-load})")
    st.markdown(
        "Load percentage can be adjusted: 100% = rated load, above = overload, "
        "below = partial load."
    )
    st.markdown(
        "- **Observe:** speed dip, increase in RMS current, new steady-state operating point.\n"
        "- **Risk:** $T_l > T_{max}$ causes stall — motor does not return to stable steady state."
    )

    st.write("")
    _h4("Load Pulse — Apply and Remove")
    st.markdown(
        "Load is applied at $t_{on}$ and removed at $t_{off}$, simulating a "
        "temporary disturbance (e.g., load impact in presses, reciprocating compressors). "
        "After $t_{off}$, the motor returns to no-load steady state with observable "
        "speed and current transients."
    )
    st.markdown(
        "- **Observe:** speed drop and recovery, current peaks at both switching instants.\n"
        "- **Key parameter:** $J$ — high inertia dampens speed drop; low inertia amplifies the transient."
    )

    st.divider()
    st.markdown("### Shutdown")

    _h4("Shutdown — Supply Cut-off")
    st.markdown(
        "At $t_{shutdown}$, the supply voltage is set to zero, simulating contactor opening "
        "or total grid loss. The rotating field disappears within microseconds (electrical transient); "
        "speed decays dominated by the mechanical time constant:"
    )
    st.markdown(
        "The event sequence in the simulator is:"
    )
    st.markdown(
        "- $t = 0$ — motor starts at no load and accelerates to steady state.\n"
        "- $t = t_{load}$ — load $T_l$ applied; motor settles to new operating point.\n"
        "- $t = t_{shutdown}$ — voltage cut off (contactor opens); electromagnetic torque decays within milliseconds.\n"
        "- **Post-cutoff** — mechanical load $T_l$ remains active and brakes the rotor to complete standstill."
    )
    st.markdown(
        "With $B > 0$ and $T_l > 0$, the analytical stopping time is computed by the simulator as:"
    )
    _eq(r"t_{stop} = \frac{J}{B}\,\ln\!\left(1 + \frac{B\,\omega_0}{T_l}\right)")
    st.markdown(
        "where $\\omega_0 = \\omega_r(t_{shutdown})$ is the speed at the instant of cutoff. "
        "$t_{max}$ is set automatically as $t_{shutdown} + 1{,}2\\,t_{stop}$ "
        "(20% margin over the analytical stopping time)."
    )
    st.markdown(
        "Special cases:\n"
        "- $B = 0$, $T_l > 0$: linear deceleration — $t_{stop} = J\\,\\omega_0 / T_l$.\n"
        "- $B > 0$, $T_l = 0$: exponential decay — $\\omega_r(t) \\approx \\omega_0\\,e^{-(t-t_{shutdown})/\\tau_m}$, $\\tau_m = J/B$.\n"
        "- $B \\approx 0$ and $T_l = 0$: rotor stops only by residual friction — very long time."
    )
    st.markdown(
        "- **Observe:** abrupt current extinction, post-cutoff speed decay, stopping time.\n"
        "- **t_max:** automatically computed by the simulator based on parameters $J$, $B$, $T_l$, and $t_{shutdown}$."
    )

    st.divider()
    st.markdown("### Voltage Sag")

    _h4("Voltage Sag")
    st.markdown(
        "A voltage sag is a **temporary reduction** in the supply voltage amplitude, "
        "with duration typically ranging from a few cycles to a few seconds. "
        "It is classified by IEC 61000-4-11 / IEEE 1159 as a high-occurrence power-quality "
        "disturbance — caused by faults on adjacent feeders, heavy-load starting, or "
        "switching failures in the grid."
    )
    st.markdown(
        "In the simulator, the sag is modelled as a rectangular reduced-voltage window "
        "over the interval $[t_{sag},\\, t_{sag} + \\Delta t_{sag}]$:"
    )
    _eq(
        r"V(t) = \begin{cases}"
        r"V_l & t < t_{sag} \\"
        r"k_{\!sag}\,V_l & t_{sag} \leq t < t_{sag} + \Delta t_{sag} \\"
        r"V_l & t \geq t_{sag} + \Delta t_{sag}"
        r"\end{cases}"
    )
    st.markdown(
        "where $k_{sag} \\in (0,\\,1]$ is the **residual magnitude** — for example, "
        "$k_{sag} = 0{,}7$ represents a 30% sag ($V = 0{,}7\\,V_l$ during the event)."
    )
    st.markdown("**Dynamic machine response during the sag:**")
    st.markdown(
        "With the voltage drop, the electromagnetic torque falls approximately as $V^2$ "
        "(since $T_e \\propto V_{th}^2$). If the load torque $T_l$ remains constant, "
        "the equation of motion has a negative acceleration:"
    )
    _eq(r"J\,\dot{\omega}_r = T_e(V_{sag}) - T_l - B\,\omega_r < 0")
    st.markdown(
        "The rotor decelerates. The speed drop $\\Delta n$ depends on the depth and "
        "duration of the sag and on the system inertia $J$. Upon restoration of rated voltage, "
        "the motor re-accelerates — provided it has not left the stable region of the "
        "$T_e \\times n$ curve (stall)."
    )
    _div_warn(
        "**Recovery criterion:** if, during the sag, the speed falls below the "
        "critical slip $s_{cr}$, the motor enters the unstable region and does not return "
        "to steady state even after voltage restoration — **post-sag stalling** occurs. "
        "This phenomenon is one of the main causes of cascading trips in industrial networks."
    )
    st.markdown(
        "- **Observe:** speed drop during the event, current peak at voltage restoration, "
        "recovery time to steady state.\n"
        "- **Critical parameters:** $k_{sag}$ (depth), $\\Delta t_{sag}$ (duration), "
        "$J$ (inertia), and $T_l$ (applied load).\n"
        "- **Relevant plot outputs:** $\\omega_r(t)$, $i_{as}(t)$, $T_e(t)$ — "
        "monitor the restoration transient and verify whether steady state is re-established."
    )

    st.divider()
    st.markdown("### Voltage Unbalance and Phase Loss")

    _h4("Voltage Unbalance — Symmetrical Components")
    st.markdown(
        "Under ideal conditions, the three phase voltages have equal amplitudes and are "
        "displaced by 120°. Any asymmetry is decomposed by **Fortescue's Theorem** "
        "into three sequences:"
    )
    _eq(r"\bar{V}_a = \bar{V}_{a1} + \bar{V}_{a2} + \bar{V}_{a0}")
    st.markdown(
        "Only the **positive sequence** $\\bar{V}_1$ produces a rotating field "
        "in the direction of motor rotation. The **negative sequence** $\\bar{V}_2$ creates "
        "a reverse rotating field, generating a *braking* torque component:"
    )
    _eq(r"T_e = T_{e,1}(s) \;+\; T_{e,2}(2-s)")
    st.markdown(
        "The practical result is reduced torque, increased current, and asymmetric phase "
        "heating — the phase with the lowest voltage tends to carry the highest current."
    )
    st.markdown("The **Voltage Unbalance Factor (VUF)** standardized by NEMA is:")
    _eq(r"\text{VUF} = \frac{|\bar{V}_2|}{|\bar{V}_1|} \times 100\%")
    st.markdown(
        "- VUF $= 1\\%$ can cause up to $6$–$10\\%$ current rise and $10\\%$ reduction in maximum torque.\n"
        "- NEMA MG-1: motors should operate with VUF $\\leq 1\\%$; above $5\\%$ operation must be discontinued."
    )
    st.markdown("In the simulator, per-phase fractional deviations are applied as:")
    _eq(r"V_a = \sqrt{\tfrac{2}{3}}\,V_l\,(1 + \delta_a)\sin(\omega_e t)")
    _eq(r"V_b = \sqrt{\tfrac{2}{3}}\,V_l\,(1 + \delta_b)\sin\!\left(\omega_e t - \tfrac{2\pi}{3}\right)")
    _eq(r"V_c = \sqrt{\tfrac{2}{3}}\,V_l\,(1 + \delta_c)\sin\!\left(\omega_e t + \tfrac{2\pi}{3}\right)")
    st.markdown("where $\\delta_a,\\,\\delta_b,\\,\\delta_c \\in [-0{,}30,\\;+0{,}30]$ are the deviations set via sliders.")

    render_imbalance_phasor()

    st.write("")
    _h4("Phase Loss — Two-Phase Operation")
    st.markdown(
        "Phase loss occurs when one conductor is interrupted — by blown fuse, contactor failure, "
        "or broken cable. The voltage of the affected phase is forced to zero, imposing the "
        "maximum possible supply unbalance:"
    )
    _eq(r"V_x = 0 \;\Rightarrow\; |\bar{V}_2| \approx |\bar{V}_1|")
    st.markdown(
        "With one phase suppressed, the machine operates in two-phase mode. "
        "The rotating field decomposes into two equal-amplitude components — "
        "positive sequence (weakened) and negative sequence (opposing motion) — "
        "producing pulsating torque and asymmetric heating. "
        "The operational consequences are:"
    )
    st.markdown(
        "- Current in the two active phases rises to approximately $\\sqrt{3}$ times the rated value.\n"
        "- Maximum available torque drops to approximately $50\\%$ of rated; loaded starting may become impossible.\n"
        "- A pulsating torque component at frequency $2f$ appears, generating vibration and audible noise.\n"
        "- Rotor and winding heating is severe — thermal protection must operate within seconds."
    )
    st.markdown(
        "The ratio of rotor losses under two-phase operation versus rated three-phase operation, "
        "at equivalent torque, is given by:"
    )
    _eq(r"P_{cu,2}^{\,\text{bif}} \approx 2\, P_{cu,2}^{\,\text{nom}}")
    st.markdown(
        "In the simulator, the phase-loss toggle forces $V_x = 0$ from "
        "$t_{imbalance}$ onward. It is recommended to limit $t_{max}$ to a few cycles after the event, "
        "as the model does not include thermal protection."
    )
    _div_warn(
        "Simultaneous simulation of two or more phase losses over extended periods "
        "should be avoided: without thermal protection in the model, currents tend to grow "
        "without bound."
    )

    st.write("")
    _h4("Unbalance Onset Instant — $t_{imbalance}$")
    st.markdown(
        "The parameter $t_{imbalance}$ separates two regimes in the simulation:"
    )
    st.markdown(
        "- $0 \\leq t < t_{imbalance}$: balanced grid — motor starts and accelerates normally.\n"
        "- $t \\geq t_{imbalance}$: unbalance and/or phase loss takes effect."
    )
    st.markdown(
        "This allows studying the **transient response to fault onset**: "
        "observe the speed disturbance, current peak, and new steady-state operating point "
        "(or divergence) immediately after $t_{imbalance}$."
    )
    _eq(r"V_x(t) = \begin{cases} V_{x,\,nom}(t) & t < t_{imbalance} \\ V_{x,\,imbalance}(t) & t \geq t_{imbalance} \end{cases}")
    st.markdown(
        "Setting $t_{imbalance} = 0$ places the asymmetry from the very start — "
        "useful for studying **starting under a pre-existing unbalanced grid**."
    )

    st.divider()
    st.markdown("### Digital Twin — Broken Bar Fault")

    _h4("Broken Bar Model — Severity $\\alpha$")
    st.markdown(
        "The broken bar fault is one of the most frequent occurrences in squirrel-cage "
        "induction motors. It arises from mechanical fatigue, repeated thermal cycles, "
        "or manufacturing defects — and manifests as a **rotor asymmetry** that produces "
        "characteristic oscillations in torque and current."
    )
    st.markdown(
        "The implemented model introduces a **periodic modulation of the rotor resistance** "
        "at the slip frequency $f_r = s \\cdot f_e$, simulating the effect "
        "of bars with elevated resistance:"
    )
    _eq(r"R_r(t) = R_{r,0}\,\bigl[1 + \alpha\,\sin(2\pi\,f_r\,t)\bigr], \quad f_r = s\,f_e")
    st.markdown(
        "where $\\alpha \\in [0,\\,0{,}5]$ is the **severity parameter** configurable in the simulator:"
    )
    st.markdown(
        "- $\\alpha = 0$: healthy motor — $R_r$ constant.\n"
        "- $\\alpha = 0{,}1$–$0{,}2$: incipient fault — subtle oscillations, difficult to detect without spectral analysis.\n"
        "- $\\alpha = 0{,}3$–$0{,}5$: severe fault — torque and current oscillations clearly visible in the plots."
    )
    st.markdown(
        "**Diagnostic spectral signature:** the broken bar fault produces sideband components "
        "in the stator current centered around the fundamental frequency:"
    )
    _eq(r"f_{sb} = f_e\,(1 \pm 2k\,s), \quad k = 1, 2, 3, \ldots")
    st.markdown(
        "The amplitude of these components grows with $\\alpha$ and with mechanical load. "
        "The diagnostic method based on these frequencies is called "
        "**MCSA** — *Motor Current Signature Analysis* — and is the most widely used "
        "predictive maintenance technique for induction motors."
    )
    _div_warn(
        "The $R_r$ modulation model is a first-order approximation. "
        "It correctly captures the oscillation frequency and the amplitude trend with severity, "
        "but does not reproduce all harmonics of the real signature of a physically fractured bar."
    )

    st.markdown("**Interactive MCSA simulator:** adjust the severity $\\alpha$ and observe the sidebands.")
    render_mcsa()
