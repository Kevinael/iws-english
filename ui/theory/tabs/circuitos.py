# -*- coding: utf-8 -*-
"""
ui/theory/tabs/circuitos.py
===========================
Theory Tab 1 — Modeling and Equivalent Circuits.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn, _show_img
from ui.theory_interactive import render_blocos_krause


def render_tab_circuitos() -> None:
    st.markdown(
        "The **single-phase equivalent circuit** transforms the three-phase electromagnetic "
        "problem into a steady-state electrical circuit. From it, the torque and power "
        "equations are derived and, by extension, the Krause $0dq$ model "
        "used for dynamic integration in the simulator."
    )

    st.divider()

    # 1a. Complete Circuit
    _h4("Complete Circuit — with $R_{fe}$")
    col_img, col_txt = st.columns([1, 1])
    with col_img:
        _show_img("imgs/ind_completo.png")
    with col_txt:
        st.markdown(
            "The *shunt* branch contains $R_{fe} \\parallel jX_m$, where $R_{fe}$ models "
            "core losses due to **hysteresis** and **eddy currents**. "
            "The excitation current decomposes as:"
        )
        _eq(r"I_\phi = I_c + jI_m = \frac{V_1}{R_{fe}} + \frac{V_1}{jX_m}")
        st.markdown("The element $R'_2/s$ concentrates two physical effects in series:")
        _eq(r"\frac{R'_2}{s} = R'_2 \;+\; R'_2\frac{1-s}{s}")
        st.markdown(
            "where $R'_2$ is the **actual rotor resistance** (Joule losses) and "
            "$R'_2(1-s)/s$ is the resistive equivalent of the **converted mechanical power**."
        )

    st.divider()

    # 1b. IEEE Circuit
    _h4("IEEE Circuit — Simplified Model (without $R_{fe}$)")
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown(
            "$R_{fe}$ is omitted — only $jX_m$ remains in the *shunt* branch. "
            "This simplification is valid because core losses typically represent "
            "$P_{fe} \\lesssim 2\\%\\,P_{nom}$; $R_{fe}$ is accounted for "
            "separately in the efficiency $\\eta$ calculation."
        )
        st.markdown("Stator mesh equation:")
        _eq(r"\bar{V}_1 = \bar{I}_1(R_s + jX_{ls}) + j X_m(\bar{I}_1 - \bar{I}'_2)")
        st.markdown(
            "This is the reference circuit for deriving the state equations "
            "of the Krause $0dq$ model implemented in the simulator."
        )
    with col_img:
        _show_img("imgs/ind_ieee.png")

    st.divider()

    # 1c. Thévenin
    _h4("Thévenin Equivalent — Rotor Loop Reduction")
    col_img, col_txt = st.columns([1, 1])
    with col_img:
        _show_img("imgs/ind_thevenin.png")
    with col_txt:
        st.markdown(
            "The stator and magnetizing branch are replaced by a source $V_{th}$ "
            "with impedance $Z_{th}$, yielding a **single loop for the rotor**:"
        )
        _eq(r"V_{th} \approx V_1 \frac{X_m}{X_1+X_m}, \quad R_{th} \approx R_1\!\left(\frac{X_m}{X_1+X_m}\right)^{\!2}, \quad X_{th} \approx X_1")
        st.markdown("Electromagnetic torque as a function of $s$:")
        _eq(r"T_e(s) = \frac{3\,V_{th}^2\,R'_2/s}{\omega_s\!\left[(R_{th}+R'_2/s)^2+(X_{th}+X'_2)^2\right]}")
        st.markdown(
            "This explicit expression for $T_e(s)$ is the basis of the **Boucherot Theorem** "
            "(Tab 2) and, when linearized in the $dq$ reference frame, yields the state equations "
            "of the **Krause model** integrated by the simulator."
        )

    st.divider()

    # 1d. Krause dq Model
    _h4("From the Equivalent Circuit to the Krause $0dq$ Model")
    st.markdown(
        "The simulator solves the differential equations in a **generic $dq$ reference frame**, "
        "selectable by the user: **synchronous** ($\\omega_{ref}=\\omega_e$), **rotor-fixed** "
        "($\\omega_{ref}=\\omega_r$), or **stationary** ($\\omega_{ref}=0$). The state variables "
        "are the **flux linkages** "
        "$\\psi_{qs},\\,\\psi_{ds},\\,\\psi_{qr}',\\,\\psi_{dr}'$ and the electrical rotor "
        "speed $\\omega_r$. The reference-frame slip is defined as "
        "$s_{ref} = (\\omega_{ref} - \\omega_r)/\\omega_b$, with $\\omega_b = 2\\pi f$."
    )

    st.markdown(
        "**Flux differential equations** "
        "(normalized form by $\\omega_b$ — cf. `core/machine_model.py:247–250`):"
    )
    _eq(r"\dot{\psi}_{qs} = \omega_b\!\left(v_{qs} - \tfrac{\omega_{ref}}{\omega_b}\,\psi_{ds} + \tfrac{R_s}{X_{ls,a}}(\psi_{mq}-\psi_{qs})\right)")
    _eq(r"\dot{\psi}_{ds} = \omega_b\!\left(v_{ds} + \tfrac{\omega_{ref}}{\omega_b}\,\psi_{qs} + \tfrac{R_s}{X_{ls,a}}(\psi_{md}-\psi_{ds})\right)")
    _eq(r"\dot{\psi}_{qr}' = \omega_b\!\left(-s_{ref}\,\psi_{dr}' + \tfrac{R_r'}{X_{lr,a}}(\psi_{mq}-\psi_{qr}')\right)")
    _eq(r"\dot{\psi}_{dr}' = \omega_b\!\left(\;\;s_{ref}\,\psi_{qr}' + \tfrac{R_r'}{X_{lr,a}}(\psi_{md}-\psi_{dr}')\right)")

    st.markdown(
        "**Algebraic relations** between mutual fluxes and state fluxes — "
        "eliminating currents from the dynamic system "
        "(cf. `core/machine_model.py:227–232`):"
    )
    _eq(r"\psi_{mq} = X_{ml}\!\left(\frac{\psi_{qs}}{X_{ls,a}} + \frac{\psi_{qr}'}{X_{lr,a}}\right), \qquad \psi_{md} = X_{ml}\!\left(\frac{\psi_{ds}}{X_{ls,a}} + \frac{\psi_{dr}'}{X_{lr,a}}\right)")
    _eq(r"X_{ml} = \left(\frac{1}{X_m} + \frac{1}{X_{ls,a}} + \frac{1}{X_{lr,a}}\right)^{\!-1}")

    st.markdown("**Currents** recovered after flux integration:")
    _eq(r"i_{qs} = \frac{\psi_{qs} - \psi_{mq}}{X_{ls,a}}, \quad i_{ds} = \frac{\psi_{ds} - \psi_{md}}{X_{ls,a}}, \quad i_{qr}' = \frac{\psi_{qr}' - \psi_{mq}}{X_{lr,a}}, \quad i_{dr}' = \frac{\psi_{dr}' - \psi_{md}}{X_{lr,a}}")

    st.markdown(
        "**Electromagnetic torque** "
        "(amplitude-invariant Clarke–Park convention, with factor $k=\\sqrt{2/3}$):"
    )
    _eq(r"T_e = \tfrac{3}{2}\cdot\tfrac{p}{2}\cdot\tfrac{1}{\omega_b}\,(\psi_{ds}\,i_{qs} - \psi_{qs}\,i_{ds})")

    st.markdown("**Mechanical equation** (Newton's second law for rotation):")
    _eq(r"J\,\dot{\omega}_m = T_e - T_L - B\,\omega_m, \qquad \omega_m = \tfrac{2}{p}\,\omega_r")

    st.markdown(
        "The $q$ and $d$ axes correspond, respectively, to the quadrature and in-phase "
        "projections of the supply voltage in the chosen reference frame. In **steady state** "
        "under the synchronous reference frame, all $dq$ components become **DC constants** — "
        "a property used as a numerical convergence test and which underpins vector control of machines."
    )

    st.markdown(
        "**$abc \\leftrightarrow dq$ transformation** — amplitude-invariant Clarke–Park "
        "(cf. `core/transforms.py:46–65`):"
    )
    _eq(r"\begin{pmatrix} v_{ds} \\ v_{qs} \end{pmatrix} = \sqrt{\tfrac{3}{2}}\,\begin{pmatrix} \cos\theta_e & \sin\theta_e \\ -\sin\theta_e & \cos\theta_e \end{pmatrix}\!\begin{pmatrix} v_a - \tfrac{1}{2}(v_b + v_c) \\ \tfrac{\sqrt{3}}{2}\,(v_b - v_c) \end{pmatrix}")

    st.markdown(
        "**Numerical solver:** integration via `scipy.integrate.solve_ivp` with LSODA method "
        "(cf. `core/solver.py:42–67`), tolerances $\\text{RTOL}=10^{-6}$, "
        "$\\text{ATOL}=10^{-9}$ and adaptive maximum step "
        "$\\Delta t_{max} = 1/(20\\,f)$, ensuring at least 20 samples per electrical cycle."
    )

    st.markdown("**Interactive Block Diagram:**")
    render_blocos_krause()

    st.divider()

    # 1e. Double Squirrel Cage
    _h4("Double Squirrel-Cage Circuit")
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown(
            "Two parallel rotor branches: **outer** cage "
            "($R_{2e}$ high, $X_{2e}$ low) and **inner** cage "
            "($R_{2i}$ low, $X_{2i}$ high). Equivalent impedance:"
        )
        _eq(r"Z'_{2,eq} = \frac{Z'_{2e}\,Z'_{2i}}{Z'_{2e}+Z'_{2i}}")
        st.markdown(
            "The **skin effect** redistributes current automatically "
            "with rotor frequency $f_r = s\\cdot f$:"
        )
        st.markdown(
            "- **Starting** ($s\\approx 1$, $f_r = f$): current concentrates "
            "in the outer cage $\\Rightarrow$ high $T_{start}$.\n"
            "- **Steady state** ($s\\approx 0{,}04$, $f_r \\approx 2$–$4\\;$Hz): "
            "current migrates to the inner cage $\\Rightarrow$ low $s_{nom}$, high $\\eta$."
        )
    with col_img:
        _show_img("imgs/ind_ieee_duplo.png")

    st.divider()

    _h4("Double Squirrel-Cage — Torque Composition")
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown("The resultant torque is the **superposition** of the torques from each cage:")
        _eq(r"T_e = T_{ext} + T_{int} = \frac{3}{\omega_s}\!\left(\frac{|V_{ag}|^2 R'_{2e}/s}{|Z'_{2e}|^2} + \frac{|V_{ag}|^2 R'_{2i}/s}{|Z'_{2i}|^2}\right)")
        st.markdown(
            "**At starting** ($s=1$, $f_r = f$): the **skin effect** "
            "forces current into the outer cage ($R'_{2e}$ high) "
            "$\\Rightarrow$ high $T_{start}$.\n\n"
            "**In steady state** ($s \\ll 1$, $f_r \\approx s\\,f$): "
            "$X'_{2i} \\to 0$ — inner cage ($R'_{2i}$ low) dominates "
            "$\\Rightarrow$ low $s_{nom}$, high $\\eta$.\n\n"
            "The result is an *automatic and continuous* variation of effective $R'_2$ "
            "during acceleration — without external components, owing to the "
            "**geometric profile of the rotor bars**."
        )
    with col_img:
        _show_img("imgs/SCdupla.png")
