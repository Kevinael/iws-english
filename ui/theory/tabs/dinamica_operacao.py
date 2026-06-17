# -*- coding: utf-8 -*-
"""
ui/theory/tabs/dinamica_operacao.py
====================================
Theory Tab 5 — Operating Dynamics.
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from ui.theory.tabs._shared import (
    _h4, _eq, _div_warn,
    _fig_to_bytes, _torque_ref,
    _ns_REF,
)
from ui.theory_interactive import (
    render_park_dinamico,
    render_transitorios_sincronizados,
    render_comparador_frenagem,
)


def render_tab_dinamica_operacao() -> None:
    st.markdown(
        "Understanding the operating dynamics of the three-phase induction motor requires "
        "analyzing each phase of the electromechanical cycle — from initial energization to "
        "complete standstill. This tab covers these states in chronological order, "
        "linking physical phenomena to the governing equations."
    )

    # ── Park Transform Reference Frame ──────────────────────────────────
    st.divider()
    _h4("Park Transform Reference Frame — Choice of Rotation Axis")
    st.markdown(
        "The Park transform projects three-phase $abc$ quantities onto two "
        "orthogonal $dq$ axes rotating at a reference angular speed $\\omega_{ref}$. "
        "The choice of $\\omega_{ref}$ defines the **reference frame** and changes the appearance of "
        "the waveforms — without altering the machine physics."
    )
    st.markdown("The three reference frames available in the simulator are:")

    col1, col2, col3 = st.columns(3)
    with col1:
        _h4("Synchronous ($\\omega_{ref} = \\omega_e$)")
        st.markdown(
            "The $d$ and $q$ axes rotate together with the stator rotating magnetic field "
            "at speed $\\omega_e$. Since the voltage vector also rotates at $\\omega_e$, "
            "it appears **stationary** in this frame. "
            "In steady state, all quantities — voltages, currents, and fluxes — "
            "become **DC values**."
        )
        st.markdown(
            "**In the animation:** the voltage vector (orange) rotates in the αβ plane, "
            "but the $d$ and $q$ axes rotate along with it — the vector appears **stationary** in the $dq$ plane.\n\n"
            "**What remains constant in steady state:** $V_{qs}$ and $V_{ds}$ — "
            "the voltage vector components in the $dq$ frame are DC values. "
            "The same applies to currents and fluxes: $I_{qs}$, $I_{ds}$, $\\psi_{qs}$, $\\psi_{ds}$."
        )
        _eq(r"V_{qs} = \text{const.},\quad V_{ds} = 0 \;\text{(steady state)}")
        _div_warn("Default simulator reference frame. Recommended for steady-state analysis and vector control.")
    with col2:
        _h4("Rotor-Fixed ($\\omega_{ref} = \\omega_r$)")
        st.markdown(
            "The axes rotate rigidly with the rotor at speed $\\omega_r = (1-s)\\,\\omega_e$. "
            "**Rotor** quantities become DC; **stator** quantities "
            "oscillate at the slip frequency $f_s = s \\cdot f_e$, "
            "since the stator field advances relative to the rotor."
        )
        st.markdown(
            "**In the animation:** the stator voltage vector (orange) rotates slowly "
            "in the $d_r q_r$ plane at frequency $s \\cdot f_e$ — the components $V_{dr}$ and $V_{qr}$ "
            "are low-frequency sinusoids.\n\n"
            "**What remains constant in steady state:** rotor quantities — "
            "$V_{dr}$, $V_{qr}$, $I_{dr}$, $I_{qr}$, $\\psi_{dr}$, $\\psi_{qr}$ — are DC in this frame.\n\n"
            "**What oscillates:** stator quantities as seen by the rotor oscillate at $s \\cdot f_e$, "
            "as shown in the animation."
        )
        _eq(r"\omega_{ref} = \omega_r = (1-s)\,\omega_e \;\Rightarrow\; f_{\text{stator}} = s\,f_e")
        _div_warn("Indicated for rotor fault studies and stator current spectral analysis.")
    with col3:
        _h4("Stationary ($\\omega_{ref} = 0$)")
        st.markdown(
            "The $\\alpha\\beta$ axes are fixed in space — they do not rotate. "
            "The voltage vector rotates at $\\omega_e$ in this frame. "
            "No quantity is DC: stator and rotor oscillate at their natural frequencies."
        )
        st.markdown(
            "**In the animation:** the voltage vector (orange) rotates at $\\omega_e$ in the fixed $\\alpha\\beta$ plane. "
            "The components $V_\\alpha$ and $V_\\beta$ — visible in the time series — "
            "are sinusoids with 90° phase shift between them.\n\n"
            "**What oscillates:** all quantities — $V_\\alpha$, $V_\\beta$, $I_\\alpha$, $I_\\beta$ "
            "oscillate at $f_e$; rotor quantities oscillate at $s \\cdot f_e$.\n\n"
            "**What remains constant:** nothing — no quantity is DC in this frame."
        )
        _eq(r"\omega_{ref} = 0 \;\Rightarrow\; V_\alpha = V\cos(\omega_e t),\; V_\beta = V\sin(\omega_e t)")
        _div_warn("Basis for sensorless control (encoder-free). Useful for visualizing currents in fixed coordinates.")

    st.markdown(
        "The model state equations change only in the cross-coupling terms "
        "(terms $\\omega_{ref}\\,\\psi$). The solution is mathematically equivalent "
        "in all three frames — the choice only affects the interpretation of the waveforms."
    )

    st.divider()
    _h4("Park Transform — Interactive Visualization")
    render_park_dinamico()

    # ── pre-compute T×n curve ────────────────────────────────────────────────
    s_mot  = np.linspace(0.002, 1.0, 600)
    T_mot  = np.array([_torque_ref(s) for s in s_mot])
    n_mot  = _ns_REF * (1 - s_mot)
    idx_pk = int(np.argmax(T_mot))
    T_load = T_mot[idx_pk] * 0.45
    idx_ss = next((i for i in range(idx_pk, len(T_mot) - 1)
                   if T_mot[i] >= T_load >= T_mot[i + 1]), len(T_mot) - 1)

    def _style_ax(a):
        a.set_facecolor("white")
        for sp in a.spines.values():
            sp.set_edgecolor("#cccccc")
        a.tick_params(colors="#333333")
        a.grid(True, alpha=0.35, linestyle=":", color="#bbbbbb")

    # ── CARD 1 — Starting, Acceleration and Steady State ────────────────────────────────
    st.divider()
    _h4("Starting, Acceleration and Steady State")
    st.markdown(
        "At the instant the stator is connected to the three-phase grid, the three currents "
        "mutually phase-shifted by 120° establish a **rotating magnetic field** "
        "that rotates at synchronous speed $n_s$:"
    )
    _eq(r"n_s = \frac{120\,f_e}{p} \quad \text{(RPM)}")
    st.markdown(
        "With the rotor at rest ($s = 1$), the rotor impedance is predominantly "
        "reactive, resulting in a starting current $I_p$ between 6 and 8 times the rated value "
        "and a relatively modest initial torque — explained by the low power "
        "factor imposed by the leakage reactance:"
    )
    _eq(r"I_p \approx (6 \text{ to } 8)\, I_n \quad (s = 1)")
    st.markdown(
        "As the rotor accelerates, slip $s$ decreases and the rotor current frequency "
        "$f_r = s \\cdot f_e$ falls. The reduction of rotor reactance "
        "improves the power factor and raises torque up to the **Maximum Torque** "
        "(pull-out) at critical slip $s_{cr}$. For $s < s_{cr}$, torque "
        "decreases until equilibrium with the load — the **steady state** "
        "— where necessarily $n < n_s$, since without slip there is no induction:"
    )
    _eq(r"s = \frac{n_s - n}{n_s} > 0 \quad \Longleftrightarrow \quad n < n_s")

    fig1, ax = plt.subplots(figsize=(8, 4.2))
    fig1.patch.set_facecolor("white")
    _style_ax(ax)
    ax.plot(n_mot, T_mot, color="#222222", linewidth=2.5, label=r"$T \times n$ Curve")
    ax.axhline(T_load, color="#555555", linestyle="--", linewidth=1.4, label="Load $T_L$")
    ax.axvline(_ns_REF, color="#aaaaaa", linestyle=":", linewidth=1)
    ax.text(_ns_REF + 10, T_mot.max() * 0.04, "$n_s$", color="#888", fontsize=9)
    ax.scatter([n_mot[-1]], [T_mot[-1]], color="#333333", s=90, zorder=5)
    ax.annotate("Starting  $s=1$\n$I_p \\approx 6\\!-\\!8\\,I_n$",
                xy=(n_mot[-1], T_mot[-1]),
                xytext=(n_mot[-1] - 370, T_mot[-1] + T_mot.max() * 0.09),
                color="#333333", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2))
    ax.scatter([n_mot[idx_pk]], [T_mot[idx_pk]], color="#555555", s=90, zorder=5)
    ax.annotate("Maximum Torque\n(Pull-out)",
                xy=(n_mot[idx_pk], T_mot[idx_pk]),
                xytext=(n_mot[idx_pk] - 400, T_mot[idx_pk] - T_mot.max() * 0.14),
                color="#555555", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.2))
    ax.scatter([n_mot[idx_ss]], [T_load], color="#111111", s=90, zorder=5)
    ax.annotate("Steady\nState",
                xy=(n_mot[idx_ss], T_load),
                xytext=(n_mot[idx_ss] + 35, T_load + T_mot.max() * 0.13),
                color="#111111", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#111111", lw=1.2))
    ax.annotate("", xy=(n_mot[idx_ss] - 25, T_load + 1),
                xytext=(n_mot[-1] - 10, T_mot[-1] + 1),
                arrowprops=dict(arrowstyle="->", color="#999999", lw=1.5,
                                connectionstyle="arc3,rad=-0.25"))
    ax.set_xlabel("Speed (rpm)", fontsize=10, fontweight="bold", color="#222")
    ax.set_ylabel("Torque (N·m)",     fontsize=10, fontweight="bold", color="#222")
    ax.set_title("Operating Trajectory — Starting to Steady State",
                 fontsize=11, fontweight="bold", color="#111")
    ax.legend(fontsize=9, facecolor="white", edgecolor="#cccccc")
    ax.set_xlim(0, _ns_REF * 1.04)
    ax.set_ylim(0, T_mot.max() * 1.2)
    fig1.tight_layout()
    st.image(_fig_to_bytes(fig1))

    # ── CARD 2 — Load Dynamics ───────────────────────────────────────────
    st.divider()
    _h4("Load Dynamics — Sudden Load Application and Removal")
    st.markdown(
        "When a load is suddenly applied to the shaft, the resistive torque momentarily exceeds "
        "$T_{em}$ and the rotor decelerates. The increase in slip "
        "raises $f_r = s \\cdot f_e$, the rotor current $I_2$, and, through "
        "magnetic coupling, the stator current $I_1$. Torque grows to a new equilibrium "
        "at a slightly lower speed, governed by the equation of motion:"
    )
    _eq(r"\frac{d\omega_r}{dt} = \frac{p}{2J}(T_{em} - T_{load}) - \frac{B}{J}\,\omega_r")
    st.markdown(
        "On load removal, the process reverses: $T_{em}$ exceeds the resistive torque, "
        "the rotor accelerates, and slip reduces to very small values "
        "($s \\approx 0{,}005$ to $0{,}02$), sufficient only to supply "
        "mechanical and core losses. The chart below illustrates the speed dip "
        "$\\Delta n$ and the transient torque peak upon load application:"
    )

    _t   = np.linspace(0.0, 5.0, 1000)
    t_on = 2.0
    n0, n1 = 1795.0, 1762.0
    tau_n  = 0.35
    Te0, Te1, Te_pk = 8.0, 42.0, 68.0
    tau_Te = 0.12
    _n  = np.where(_t < t_on, n0,
                   n1 + (n0 - n1) * np.exp(-(_t - t_on) / tau_n))
    _Te = np.where(_t < t_on, Te0,
                   Te1 + (Te_pk - Te1) * np.exp(-(_t - t_on) / tau_Te) *
                   np.sin(np.pi * (_t - t_on) / (3 * tau_Te)).clip(0))
    _Te = np.where(_t < t_on, Te0, _Te)

    fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.8), sharex=True)
    fig2.patch.set_facecolor("white")
    for a in (ax1, ax2):
        _style_ax(a)
        a.axvline(t_on, color="#555555", linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.plot(_t, _n, color="#222222", linewidth=2)
    ax1.set_ylabel("Speed (rpm)", fontsize=9, fontweight="bold", color="#222")
    ax1.annotate("Load\napplied", xy=(t_on, n0), xytext=(t_on + 0.35, n0 + 3),
                 color="#555555", fontsize=8,
                 arrowprops=dict(arrowstyle="->", color="#555555", lw=1.1))
    ax1.annotate(f"$\\Delta n$ = {n0 - n1:.0f} rpm",
                 xy=((t_on + 5) / 2, (n0 + n1) / 2), color="#555", fontsize=8, ha="center")
    ax2.plot(_t, _Te, color="#444444", linewidth=2)
    ax2.set_ylabel("Torque $T_e$ (N·m)", fontsize=9, fontweight="bold", color="#222")
    ax2.set_xlabel("Time (s)",           fontsize=9, fontweight="bold", color="#222")
    fig2.suptitle("Transient Response — Sudden Load Application",
                  fontsize=11, fontweight="bold", color="#111")
    fig2.tight_layout()
    st.image(_fig_to_bytes(fig2))

    st.divider()
    _h4("Synchronized Transients — Interactive Visualization")
    st.markdown(
        "The panel below displays three fundamental quantities — **speed** $n(t)$, "
        "**electromagnetic torque** $T_e(t)$, and **phase current** $i_{as}(t)$ — "
        "aligned on the same time axis for three typical transient scenarios. "
        "Observe how each electrical or mechanical event propagates simultaneously through "
        "all three quantities: current reacts first (electrical time constant $\\tau_e$), "
        "torque follows immediately, and speed responds last (mechanical inertia $J$)."
    )
    render_transitorios_sincronizados()

    # ── CARD 3 — Braking and Controlled Stop ───────────────────────────────────────────
    st.divider()
    _h4("Braking and Controlled Stop")
    st.markdown(
        "In many applications — cranes, presses, conveyor belts — "
        "coast-down stopping is unacceptable for safety or productivity reasons. "
        "Three active braking methods exist for induction motors, each with a distinct "
        "physical principle, stopping speed, and thermal cost."
    )
    st.markdown(
        "**1. Regenerative Braking** — "
        "occurs when the load drives the rotor above $n_s$, making $s$ negative. "
        "Power flow reverses: the machine converts shaft kinetic energy into "
        "electrical energy returned to the grid. This is the most efficient method, but requires "
        "the receiving system (inverter with regenerative bridge or braking resistor) to "
        "absorb the returned energy."
    )
    _eq(r"s < 0 \;\Rightarrow\; P_{ag} < 0 \;\Rightarrow\; \text{power returned to grid}")
    st.markdown(
        "**2. Plugging (Counter-current Braking)** — "
        "two of the three supply phases are reversed while the motor is running. "
        "The rotating field instantly reverses, producing slip $s \\approx 2$ "
        "and torque opposing the motion. Stopping is fastest, but currents "
        "exceed starting values and heat dissipated in the rotor is severe. The motor "
        "*must* be disconnected exactly at $n = 0$; otherwise it accelerates "
        "in the opposite direction."
    )
    _eq(r"s = \frac{n_s - n}{n_s} \approx 2 \quad (n_s \text{ reversed, } n \text{ positive})")
    st.markdown(
        "**3. DC Injection Braking** — "
        "the three-phase supply is disconnected and DC voltage is applied to two stator terminals. "
        "The resulting stationary field interacts with the moving rotor conductors, "
        "inducing currents that produce braking torque proportional "
        "to speed — which naturally vanishes at $n = 0$, eliminating the risk "
        "of reversal. Stopping is slower, but smooth and precise."
    )
    _eq(r"T_{brake} \propto \omega_r \;\xrightarrow{\;\omega_r \to 0\;}\; 0")
    st.markdown("The chart compares $n(t)$ for all three methods from the same rated operating point. "
                "The dashed line shows what happens if plugging is *not* interrupted at zero:")

    _tb   = np.linspace(0.0, 2.6, 900)
    n_nom = 1760.0
    t_plug_stop = 0.35
    _n_plug_motor = n_nom * (1.0 - _tb / t_plug_stop)
    tau_dc  = 1.05
    _n_dc   = n_nom * np.exp(-_tb / tau_dc)
    tau_reg = 0.55
    _n_reg  = n_nom * np.exp(-_tb / tau_reg)
    mask_plug = _tb <= t_plug_stop

    fig3, ax3 = plt.subplots(figsize=(8, 4.2))
    fig3.patch.set_facecolor("white")
    _style_ax(ax3)
    ax3.plot(_tb[mask_plug], _n_plug_motor[mask_plug],
             color="#111111", linewidth=2.3, label="Plugging (Counter-current)")
    ax3.plot(_tb[~mask_plug][: int(0.35 / (_tb[1] - _tb[0]))],
             _n_plug_motor[~mask_plug][: int(0.35 / (_tb[1] - _tb[0]))],
             color="#111111", linewidth=1.6, linestyle="--", alpha=0.55)
    ax3.plot(_tb, _n_reg, color="#555555", linewidth=2.3, linestyle="--",
             label="Regenerative")
    ax3.plot(_tb, _n_dc,  color="#888888", linewidth=2.3, linestyle=":",
             label="DC Injection")
    ax3.axhline(0, color="#aaaaaa", linewidth=0.9, linestyle="-")
    ax3.axhline(n_nom, color="#cccccc", linewidth=0.8, linestyle=":")
    ax3.annotate("Disconnect at\n$n = 0$ (plugging)",
                 xy=(t_plug_stop, 0),
                 xytext=(t_plug_stop + 0.25, n_nom * 0.18),
                 color="#333333", fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2))
    ax3.set_xlabel("Time since braking onset (s)",
                   fontsize=10, fontweight="bold", color="#222")
    ax3.set_ylabel("Speed (rpm)", fontsize=10, fontweight="bold", color="#222")
    ax3.set_title("Comparison of Braking Methods — $n(t)$",
                  fontsize=11, fontweight="bold", color="#111")
    ax3.legend(fontsize=9.5, facecolor="white", edgecolor="#cccccc")
    ax3.set_xlim(0, 2.6)
    ax3.set_ylim(-200, n_nom * 1.12)
    fig3.tight_layout()
    st.image(_fig_to_bytes(fig3))

    st.markdown("**Interactive comparator:** adjust the initial speed and intensity of each method.")
    render_comparador_frenagem()
