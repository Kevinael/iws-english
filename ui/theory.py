# -*- coding: utf-8 -*-
"""
theory.py
=========
Orchestrator for the induction-machine Theory tab — renders 8 pedagogical sub-tabs and delegates to interactive components.

Responsibilities:
  - Lay out 8 sub-tabs: dq0 model, steady state, unbalance, MCSA, braking, Krause, estimator, and manual.
  - Load static images via _b64 for embedding in Streamlit markdown.
  - Call render_* functions from theory_interactive for each interactive component.

Relationships:
  Imported by : ui_components.theory_view
  Imports     : ui.theory_interactive

Extending:
  - To add a new sub-tab, create a render_* function in theory_interactive.py and add a tab call here.
"""

from __future__ import annotations
import base64
import io
from pathlib import Path

import numpy as np
import matplotlib
from ui.theory_interactive import (
    render_boucherot,
    render_zonas_operacao,
    render_comparativo_partidas,
    render_park_dinamico,
    render_sankey_potencia,
    render_fasorial_desequilibrio,
    render_transitorios_sincronizados,
    render_mcsa,
    render_comparador_frenagem,
    render_blocos_krause,
)
matplotlib.use("Agg")
matplotlib.rcParams.update({"mathtext.fontset": "dejavusans", "text.usetex": False})
import matplotlib.pyplot as plt
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _b64(fname: str) -> str:
    for base in (Path(__file__).parent.parent, Path(__file__).parent):
        p = base / fname
        if p.exists():
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""


def _show_img(fname: str, width: str = "100%") -> None:
    b64 = _b64(fname)
    if not b64:
        st.caption(f"[{fname} not found]")
        return
    st.markdown(
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:{width};max-width:100%;display:block;'
        f'border-radius:6px;margin:.4rem auto;">',
        unsafe_allow_html=True,
    )


# ── figura matplotlib → bytes ─────────────────────────────────────────────────

def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── reference parameters for T×s curves ──────────────────────────────────────

_V1_REF, _f_REF, _p_REF = 220, 60, 4
_R1_REF, _X1_REF        = 0.50, 1.00
_R2_REF, _X2_REF        = 0.40, 1.00
_Xm_REF                 = 50.0
_ns_REF                 = 120 * _f_REF / _p_REF   # 1800 RPM


def _torque_ref(s: float) -> float:
    """Torque (N·m) for the reference motor used in the Theory tab."""
    if abs(s) < 1e-4:
        s = 1e-4
    Z2  = _R2_REF / s + 1j * _X2_REF
    Zeq = (1j * _Xm_REF * Z2) / (1j * _Xm_REF + Z2)
    Zt  = _R1_REF + 1j * _X1_REF + Zeq
    I1  = _V1_REF / Zt
    I2  = (I1 * Zeq) / Z2
    return 3 * abs(I2) ** 2 * (_R2_REF / s) / (2 * np.pi * _ns_REF / 60)


# ── rendering helpers ────────────────────────────────────────────────────────

def _h4(title: str) -> None:
    """Section subtitle — uses native markdown to support LaTeX and bold."""
    st.markdown(f"#### {title}")


def _eq(latex: str) -> None:
    """Centered equation via Streamlit's native KaTeX renderer."""
    st.markdown(f"$$\n{latex}\n$$")


def _p(text: str) -> None:
    st.markdown(text)


def _div_warn(text: str) -> None:
    st.warning(text)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — MODELING AND EQUIVALENT CIRCUITS
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_circuitos() -> None:
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — DYNAMIC BEHAVIOR AND TORQUE
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_dinamica() -> None:
    st.markdown(
        "The **slip** $s = (n_s - n_r)/n_s$ governs the machine's operating mode. "
        "Three physically distinct regions divide the $T_e \\times n$ curve, "
        "each with different dynamics and operational risks."
    )

    _h4("T×n Curve — Interactive Operating Zones")
    render_zonas_operacao()

    st.divider()

    # Boucherot
    _h4("Algebraic Formulation of $T_e(s)$ via Thévenin")
    st.markdown(
        "The torque–slip curve is obtained in closed form after reducing the "
        "stator and magnetizing branch by Thévenin, as seen from the rotor terminals "
        "(cf. Tab 1):"
    )
    _eq(r"\bar{V}_{th} = \bar{V}_1\,\frac{jX_m}{R_s + j(X_{ls} + X_m)}, \qquad \bar{Z}_{th} = R_{th} + jX_{th} = \frac{(R_s + jX_{ls})\,(jX_m)}{R_s + j(X_{ls} + X_m)}")
    st.markdown(
        "The power transferred across the air gap is "
        "$P_{ag} = 3\\,|I'_2|^2\\,(R'_2/s)$, and the electromagnetic torque is obtained by dividing "
        "by the mechanical synchronous speed $\\omega_s = (2/p)\\,\\omega_e$:"
    )
    _eq(r"T_e(s) = \frac{3}{\omega_s}\cdot\frac{V_{th}^2\,(R'_2/s)}{(R_{th} + R'_2/s)^2 + (X_{th} + X'_2)^2}")

    _h4("Maximum Torque and Critical Slip — Boucherot Theorem")
    st.markdown(
        "Differentiating $T_e(s)$ with respect to $s$ and setting it to zero yields the pair "
        "$(T_{max},\\, s_{cr})$:"
    )
    _eq(r"T_{max} = \frac{3\,V_{th}^2}{2\,\omega_s\!\left(R_{th} + \sqrt{R_{th}^2 + (X_{th}+X'_2)^2}\right)}")
    _eq(r"s_{cr} = \frac{R'_2}{\sqrt{R_{th}^2 + (X_{th}+X'_2)^2}}")
    st.markdown(
        "**Boucherot Theorem:** $T_{max}$ *does not depend on $R'_2$*. "
        "Varying $R'_2$ only **shifts** $s_{cr}$ without changing the peak magnitude. "
        "To obtain maximum starting torque ($T_{start} = T_{max}$), it suffices to impose $s_{cr} = 1$:"
    )
    _eq(r"R'_2\big|_{T_{start}=T_{max}} = \sqrt{R_{th}^2 + (X_{th}+X'_2)^2}")
    st.markdown(
        "In **wound-rotor motors**, external resistances are inserted "
        "in the slip rings only during starting and then short-circuited, exploiting this principle."
    )

    st.divider()
    _h4("Interactive Boucherot — Effect of R'₂ on the T×s Curve")
    render_boucherot()



# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — ENERGY BALANCE AND POWER FLOW
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_potencia() -> None:
    st.markdown(
        "Power flows in a **cascaded** manner, with each stage dissipating or converting "
        "a fraction determined by $s$, $R$, $X$ and $\\omega$. "
        "The operating mode (motor, generator, braking) reverses the flow direction."
    )

    st.divider()
    _h4("Fundamental Power Relations")
    st.markdown("The identities below hold in **steady state** for any $s$:")
    st.markdown(
        """
| Quantity | Expression | Note |
|---|---|---|
| **Input power** $P_{in}$ | $3\\,V_1\\,I_1\\cos\\varphi$ | Three-phase — stator terminals |
| **Stator copper losses** $P_{cu,1}$ | $3\\,I_1^2\\,R_s$ | Joule losses in stator windings |
| **Core losses** $P_{fe}$ | $3\\,V_\\phi^2/R_{fe}$ | Hysteresis + eddy currents in the core |
| **Air-gap power** $P_{ag}$ | $T_e\\,\\omega_s = P_{in} - P_{cu,1} - P_{fe}$ | $\\omega_s = 4\\pi f/p$ |
| **Rotor copper losses** $P_{cu,2}$ | $s\\,P_{ag} = 3\\,I_2'^2\\,R_r$ | Fraction of $P_{ag}$ dissipated in the rotor |
| **Mechanical power** $P_{mec}$ | $(1-s)\\,P_{ag} = T_e\\,\\omega_r$ | $\\omega_r = (1-s)\\,\\omega_s$ |
| **Output power** $P_{out}$ | $P_{mec} - P_{rot}$ | $P_{rot}$: friction + windage |
| **Efficiency** $\\eta$ | $P_{out}/P_{in}$ | Maximum when $P_{cu,1} \\approx P_{fe}+P_{rot}$ |
"""
    )

    st.divider()

    # Three modes side by side
    c1, c2, c3 = st.columns(3)
    with c1:
        _h4("Motor Mode")
        _show_img("imgs/fluxo_P_motor.png")
        _eq(r"P_{in} \xrightarrow{-P_{cu,1}} P_{ag} \xrightarrow{-P_{cu,2}} P_{mec} \xrightarrow{-P_{rot}} P_{out}")
        st.markdown(
            "Key relation: $P_{cu,2} = s\\,P_{ag}$ and $P_{mec} = (1-s)P_{ag}$. "
            "Efficiency is maximized at low rated slip."
        )
    with c2:
        _h4("Generator Mode")
        _show_img("imgs/fluxo_P_gerador.png")
        _eq(r"P_{in,mec} \xrightarrow{-P_{rot}} P_{mec} \xrightarrow{-P_{cu,2}} P_{ag} \xrightarrow{-P_{cu,1}} P_{out}")
        st.markdown(
            "Reversed direction: mechanical power enters via the shaft; "
            "electrical power exits through the stator terminals to the grid."
        )
    with c3:
        _h4("Braking Mode ($s > 1$)")
        _show_img("imgs/fluxo_P_frenagem.png")
        _eq(r"P_{ele} + P_{cin} \longrightarrow P_{cu,2}")
        st.markdown(
            "Electrical energy from the grid *and* kinetic energy from the shaft "
            "are **entirely converted to heat in the rotor**."
        )
        _div_warn("Brief operation only — rotor may burn within seconds. "
                  "$P_{cu,2} = s\\,P_{ag} > P_{ag}$ because $s > 1$.")

    st.divider()

    # Physical interpretation of slip
    _h4("Physical Interpretation of Slip")
    st.markdown(
        "Slip $s$ is the variable that **partitions** the air-gap power "
        "between losses and mechanical output:"
    )
    _eq(r"P_{ag} = \underbrace{s\,P_{ag}}_{P_{cu,2}\;\text{(heat)}} + \underbrace{(1-s)\,P_{ag}}_{P_{mec}\;\text{(work)}}")
    st.markdown(
        "A motor with $s = 0{,}05$ (5%) dissipates only 5% of the air-gap power in the rotor — "
        "the remaining 95% is converted to mechanical work. This is why **efficient motors "
        "operate at low slip**.\n\n"
        "In braking ($s > 1$), the equation above requires $P_{cu,2} > P_{ag}$, which is only possible "
        "because the **shaft kinetic energy** additionally feeds the rotor."
    )

    st.divider()
    _h4("Interactive Power Flow")
    render_sankey_potencia()


# ─────────────────────────────────────────────────────────────────────────────
# TAB — OPERATING DYNAMICS
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_dinamica_operacao() -> None:
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — PARAMETER SENSITIVITY GUIDE
# ─────────────────────────────────────────────────────────────────────────────

_PARAMS_ELETRICOS = [
    {
        "nome": "$V_l$ — Line Voltage (RMS)",
        "desc": (
            "Defines the amplitude of the stator rotating magnetic field. "
            "Determines the air-gap flux: $\\Phi \\propto V_l/f$. "
            "This is the quantity with the greatest impact on available torque."
        ),
        "up": (
            "Maximum torque grows with $V_l^2$: $T_{max} \\propto V_{th}^2 \\propto V_l^2$. "
            "Starting current also increases significantly."
        ),
        "down": (
            "Starting torque decreases — may become insufficient to overcome load inertia, "
            "preventing starting (stall during acceleration)."
        ),
        "warn": (
            "Overvoltage ($> 110\\%\\,V_n$) causes **core saturation** and "
            "thermal degradation of insulation. "
            "Severe undervoltage ($< 85\\%\\,V_n$) may cause **stalling** under rated load."
        ),
    },
    {
        "nome": "$f$ — Grid Frequency",
        "desc": (
            "Determines synchronous speed: $n_s = 120\\,f/p\\;$(rpm). "
            "Reactances scale proportionally: $X = 2\\pi f L$."
        ),
        "up": (
            "Increases $n_s$, $X_m$, $X_{ls}$, $X_{lr}$. "
            "With constant $V_l$, the $V/f$ ratio falls, reducing flux and maximum torque."
        ),
        "down": (
            "Reduces operating speed. With constant $V_l$, the $V/f$ ratio rises, "
            "driving the core into **magnetic saturation**."
        ),
        "warn": (
            "Operating outside rated frequency without $V/f = $ const. control compromises "
            "flux, efficiency, and thermal integrity of the machine."
        ),
    },
    {
        "nome": "$R_s$ — Stator Resistance",
        "desc": (
            "Represents Joule losses in the stator windings: $P_{cu,1} = 3I_1^2 R_s$. "
            "Causes an internal voltage drop, reducing the effective voltage at the air gap."
        ),
        "up": (
            "Increases thermal dissipation and reduces $T_{max}$, "
            "since $R_{th} \\uparrow$ raises the denominator of the Boucherot expression."
        ),
        "down": (
            "Minimizes internal losses and improves efficiency. "
            "At extreme values, approximates an ideal transformer primary."
        ),
        "warn": (
            "Excessive $R_s$ (damaged or overheated windings) causes "
            "**progressive overheating**. "
            "Values near zero may cause **numerical instability** in the integrator."
        ),
    },
    {
        "nome": "$R_r$ — Rotor Resistance",
        "desc": (
            "Determining parameter of the torque curve. "
            "Defines critical slip: $s_{cr} = R_r / \\sqrt{R_{th}^2 + X_{eq}^2}$."
        ),
        "up": (
            "$s_{cr}$ increases — torque peak shifts to lower speeds. "
            "Starting torque grows up to the limit $T_{max}$ (when $s_{cr} = 1$)."
        ),
        "down": (
            "Improves efficiency ($s_{nom}$ decreases) and reduces steady-state slip. "
            "Starting torque decreases proportionally."
        ),
        "warn": (
            "Very high $R_r$ indicates **broken bars** — causes excessive slip and vibration. "
            "Zero values cause **mathematical singularity** in the rotor equations."
        ),
    },
    {
        "nome": "$X_m$ — Magnetizing Reactance",
        "desc": (
            "Represents the magnetizing (*shunt*) branch of the circuit: "
            "main flux path through the core. "
            "Related to mutual inductance: $X_m = 2\\pi f L_m$."
        ),
        "up": (
            "Reduces no-load magnetizing current $I_m = V_1/X_m$, "
            "improving power factor in steady state."
        ),
        "down": (
            "Increases $I_m$ — higher reactive current required to excite the core, "
            "degrading power factor."
        ),
        "warn": (
            "Low $X_m$ indicates poor-quality core or **magnetic saturation**. "
            "Excessively low values may cause **numerical divergence** in the integrator."
        ),
    },
    {
        "nome": "$R_{fe}$ — Core Loss Resistance",
        "desc": (
            "Models hysteresis and eddy currents in parallel with $X_m$. "
            "Core losses: $P_{fe} = 3\\,V_\\phi^2 / R_{fe}$. "
            "Typical values: $100$–$2000\\;\\Omega$ for medium-sized machines."
        ),
        "up": (
            "Lower $P_{fe}$. Motor operates with higher efficiency, "
            "especially at light load where core losses dominate."
        ),
        "down": (
            "Higher $P_{fe}$. Efficiency decreases, especially at no load. "
            "May indicate low-quality laminations or operation at elevated frequency."
        ),
        "warn": (
            "$R_{fe}$ is used **only in static power and efficiency calculations** — "
            "it does not influence the ODE or the simulated dynamics. "
            "Values $< 50\\;\\Omega$ indicate extremely poor-quality core."
        ),
    },
    {
        "nome": "$X_{ls}$ and $X_{lr}$ — Leakage Reactances",
        "desc": (
            "Model fluxes that do not link both windings (leakage). "
            "Define short-circuit reactance: $X_{cc} = X_{ls} + X_{lr}$, "
            "which limits maximum torque and starting current."
        ),
        "up": (
            "Increases $X_{cc}$, reducing $T_{max} \\propto 1/(X_{th}+X_{lr})$. "
            "Starting current decreases, facilitating protection."
        ),
        "down": (
            "$T_{max}$ increases and starting currents rise. "
            "Makes the motor more sensitive to load transients and voltage variations."
        ),
        "warn": (
            "Very low leakage results in **current peaks dangerous to the insulation**. "
            "Excessive leakage may **prevent starting** under rated load."
        ),
    },
]

_PARAMS_MECANICOS = [
    {
        "nome": "$p$ — Number of Poles",
        "desc": (
            "Defines synchronous speed: $n_s = 120\\,f/p\\;$(rpm), "
            "or equivalently $\\omega_s = 4\\pi f/p\\;$(rad/s)."
        ),
        "up": (
            "Reduces $n_s$. For the same power $P = T\\,\\omega$, "
            "rated torque must be proportionally larger."
        ),
        "down": (
            "Increases $n_s$ and $\\omega_s$. "
            "Rated torque decreases for the same output power."
        ),
        "warn": "$p$ must always be a positive even integer. Odd values invalidate the physical model.",
    },
    {
        "nome": "$J$ — Moment of Inertia",
        "desc": (
            "Governs acceleration dynamics via the mechanical equation: "
            "$J\\,\\dot{\\omega}_r = T_e - T_L - B\\,\\omega_r$. "
            "Includes the rotor and the load coupled to the shaft."
        ),
        "up": (
            "Slower acceleration — damped transients and longer starting time. "
            "Reduces sensitivity to sudden load changes."
        ),
        "down": (
            "Accelerated dynamic response — rotor reacts almost instantaneously to $T_e$ changes. "
            "Useful for servo drives, but requires protection against fast overloads."
        ),
        "warn": (
            "Very low $J$ may produce **noisy numerical oscillations** in the ODE. "
            "Very high $J$ may require very large $t_{max}$ to reach steady state."
        ),
    },
    {
        "nome": "$B$ — Viscous Friction Coefficient",
        "desc": (
            "Models mechanical losses proportional to speed: "
            "$T_{friction} = B\\,\\omega_r$ (bearings and ventilation)."
        ),
        "up": (
            "Increases system damping and mechanical dissipation. "
            "Steady-state equilibrium shifts to lower speed."
        ),
        "down": (
            "Reduces mechanical losses. "
            "If $B = 0$, damping depends exclusively on the external load $T_L$."
        ),
        "warn": (
            "High values simulate **catastrophic bearing failure** and "
            "may prevent the motor from reaching rated speed."
        ),
    },
]


def _render_tab_sensibilidade() -> None:
    st.markdown(
        "**Simulator calibration guide**: how each parameter qualitatively affects "
        "machine behavior. Useful for diagnostics, model tuning, and fault studies."
    )

    st.divider()
    st.markdown("### Electrical Parameters")
    for item in _PARAMS_ELETRICOS:
        st.markdown(f"**{item['nome']}**")
        st.markdown(item["desc"])
        st.markdown(f"- **If increased:** {item['up']}")
        st.markdown(f"- **If decreased:** {item['down']}")
        _div_warn(f"**Caution — extreme calibrations:** {item['warn']}")
        st.write("")

    st.divider()
    st.markdown("### Mechanical Parameters")
    for item in _PARAMS_MECANICOS:
        st.markdown(f"**{item['nome']}**")
        st.markdown(item["desc"])
        st.markdown(f"- **If increased:** {item['up']}")
        st.markdown(f"- **If decreased:** {item['down']}")
        _div_warn(f"**Caution — extreme calibrations:** {item['warn']}")
        st.write("")

    st.divider()
    st.markdown("### Magnetic Parameter Input Mode — Reactances vs. Inductances")
    _h4("Reactances $X$ (Ω) vs. Inductances $L$ (H)")
    st.markdown(
        "The magnetic parameters $X_m$, $X_{ls}$, and $X_{lr}$ can be entered in two "
        "equivalent forms. The choice depends on the available data source."
    )

    col_x, col_l = st.columns(2)
    with col_x:
        _h4("Reactance Mode (Ω)")
        st.markdown(
            "Values are provided as reactances measured at a reference frequency "
            "$f_{ref}$. This is the standard format of test reports and manufacturer catalogs."
        )
        _eq(r"X = 2\pi\,f_{ref}\,L")
        st.markdown(
            "**$f_{ref}$** must be the frequency at which the parameters were measured — "
            "typically the machine's rated frequency (50 Hz or 60 Hz). "
            "The simulator converts internally to inductances:"
        )
        _eq(r"L = \frac{X}{2\pi\,f_{ref}}")
        _div_warn(
            "If $f_{ref}$ differs from the grid frequency $f$, the effective reactances in the simulation "
            "will be correctly recalculated — $L$ is invariant, $X$ scales with $f$."
        )
    with col_l:
        _h4("Inductance Mode (H)")
        st.markdown(
            "Values are provided directly as frequency-independent inductances. "
            "Indicated when parameters come from parametric identification, "
            "finite element simulation (FEM), or impedance bridge measurements."
        )
        _eq(r"X_m(f) = 2\pi\,f\,L_m")
        st.markdown(
            "Inductances are entered once and remain valid for any "
            "operating frequency — the simulator recalculates reactances automatically "
            "at each change of $f$."
        )
        _div_warn(
            "Prefer this mode when operating outside rated frequency or when comparing "
            "machines of different frequencies using the same parameter set."
        )

    st.divider()
    st.markdown("### Thermal Parameters")
    _h4("$R_{th}$ — Thermal Resistance (K/W)")
    st.markdown(
        "Represents the resistance to heat flow between the winding and the external environment. "
        "Defines steady-state temperature as a function of total losses:"
    )
    _eq(r"\Delta T_{steady} = R_{th}\,(P_{cu} + P_{fe})")
    st.markdown(
        "In automatic mode, $R_{th}$ is estimated from the electrical parameters by imposing "
        "a rated temperature rise $\\Delta T = 50\\;$K — a typical value for TEFC "
        "(Totally Enclosed Fan Cooled) motors at rated operation, corresponding to "
        "$T_{steady} \\approx 75\\;$°C with $T_{amb} = 25\\;$°C."
    )
    _div_warn(
        "Low $R_{th}$ values indicate a well-cooled motor (large frame, "
        "forced ventilation). High values indicate a small enclosed motor or "
        "one with compromised ventilation — higher steady-state temperature."
    )

    st.write("")
    _h4("$C_{th}$ — Thermal Capacitance (J/K)")
    st.markdown(
        "Represents the energy required to raise the motor temperature by 1 K. "
        "Governs the **heating rate** — the thermal time constant is:"
    )
    _eq(r"\tau_{th} = R_{th}\,C_{th}")
    st.markdown(
        "In automatic mode, thermal capacitance is estimated from the motor equivalent mass, "
        "assuming steel with specific heat $c_p = 460\\;$J/(kg·K) and an industrial rule of "
        "$15\\;$kg/kW of rated power:"
    )
    _eq(r"C_{th} \approx \underbrace{15\,P_{nom}}_{\text{estimated mass (kg)}} \times 460\;\frac{\text{J}}{\text{kg·K}}")
    _div_warn(
        "The thermal ODE integrated by the simulator is: "
        "$\\dot{T} = (P_{cu} + P_{fe})/C_{th} - (T - T_{amb})/(R_{th}\\,C_{th})$. "
        "In steady state, $\\dot{T} = 0$ and $T_{steady} = T_{amb} + R_{th}\\,(P_{cu}+P_{fe})$."
    )

    st.write("")
    _h4("$T_{amb}$ — Ambient Temperature (°C)")
    st.markdown(
        "External ambient temperature, used as the boundary condition of the thermal ODE "
        "and as the initial value of $T$ in the simulation. "
        "Motor temperature at any instant is:"
    )
    _eq(r"T(t) = T_{amb} + \Delta T(t), \quad \Delta T(t) = \Delta T_{steady}\!\left(1 - e^{-t/\tau_{th}}\right)")
    st.markdown(
        "Changing $T_{amb}$ shifts the entire temperature curve without modifying the dynamics — "
        "$\\tau_{th}$ and $\\Delta T_{steady}$ remain unchanged."
    )

    st.divider()
    st.markdown("### Grid Impedance")
    _h4("$R_{grid}$ and $L_{grid}$ — Supply Grid Impedance")
    st.markdown(
        "In a real installation, the motor is not fed directly by an ideal voltage source: "
        "there is a grid impedance between the point of delivery and the motor terminals, "
        "composed of the resistance and inductance of cables, transformers, and busbars. "
        "The simulator models this impedance as a series $R_{grid} + jX_{grid}$ "
        "inserted in each phase before the stator terminals:"
    )
    _eq(r"\bar{V}_{motor} = \bar{V}_{grid} - \bar{I}_s\,(R_{grid} + j\omega_e L_{grid})")
    st.markdown(
        "The effective voltage at the motor terminals drops with current — especially "
        "during starting, when $I_s$ is maximum. The effect is equivalent to a "
        "**current-proportional voltage sag** throughout the entire transient."
    )
    st.markdown(
        "- **$R_{grid}$:** causes resistive voltage drop and active power dissipation in the cable.\n"
        "- **$L_{grid}$:** causes reactive voltage drop and phase lag — more relevant in "
        "medium-voltage grids or with long cables."
    )
    _div_warn(
        "With $R_{grid} = L_{grid} = 0$ (default), the motor is fed by an ideal source — "
        "terminal voltage always equal to $V_l$. "
        "Typical values for low-voltage cables: $R_{grid} \\approx 0{,}01$–$0{,}1\\;\\Omega$, "
        "$L_{grid} \\approx 10$–$100\\;\\mu$H."
    )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 8a — SIMULATION SETTINGS AND ALERTS (rendered inside Tab 8)
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_config() -> None:
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — EXPERIMENTS AND GRID DISTURBANCES
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_experimentos() -> None:
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
    render_comparativo_partidas()

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

    render_fasorial_desequilibrio()

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
        "$t_{deseq}$ onward. It is recommended to limit $t_{max}$ to a few cycles after the event, "
        "as the model does not include thermal protection."
    )
    _div_warn(
        "Simultaneous simulation of two or more phase losses over extended periods "
        "should be avoided: without thermal protection in the model, currents tend to grow "
        "without bound."
    )

    st.write("")
    _h4("Unbalance Onset Instant — $t_{deseq}$")
    st.markdown(
        "The parameter $t_{deseq}$ separates two regimes in the simulation:"
    )
    st.markdown(
        "- $0 \\leq t < t_{deseq}$: balanced grid — motor starts and accelerates normally.\n"
        "- $t \\geq t_{deseq}$: unbalance and/or phase loss takes effect."
    )
    st.markdown(
        "This allows studying the **transient response to fault onset**: "
        "observe the speed disturbance, current peak, and new steady-state operating point "
        "(or divergence) immediately after $t_{deseq}$."
    )
    _eq(r"V_x(t) = \begin{cases} V_{x,\,nom}(t) & t < t_{deseq} \\ V_{x,\,deseq}(t) & t \geq t_{deseq} \end{cases}")
    st.markdown(
        "Setting $t_{deseq} = 0$ places the asymmetry from the very start — "
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



# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — SIMULATOR USER MANUAL
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_manual_de_uso() -> None:
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

    st.markdown("**Thermal parameters** (decoupled heating model):")
    st.markdown(
        "- $R_{th}$ — thermal resistance (°C/W).\n"
        "- $C_{th}$ — thermal capacitance (J/°C).\n"
        "- $T_{amb}$ — ambient temperature (°C).\n"
        "When left at zero, they are estimated automatically."
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — PARAMETER ESTIMATORS
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_estimadores() -> None:
    st.markdown(
        "This tab documents the **two parameter estimators** available in the "
        "simulator. Both are legitimate T-equivalent circuit methods in steady state, "
        "but apply to different use cases — the choice depends on the available data."
    )

    # ── Section 7.1: Nameplate ──────────────────────────────────────────────
    st.markdown("### Section 7.1 — Nameplate Estimator (nameplate data)")

    st.info(
        "**When to use:** only motor nameplate data available "
        "(manufacturer catalog, no physical tests). Indicated for initial studies, "
        "sensitivity analysis, and rapid simulation of NEMA class B motors."
    )

    _h4("Background — IEEE T-Equivalent with NEMA Assumptions")
    st.markdown(
        "When the equivalent circuit parameters "
        "($R_s, R_r', X_m, X_{ls}, X_{lr}'$) are not directly available, this "
        "method estimates them from the motor **nameplate** data. The formulation combines "
        "the IEEE Std 112 methodology with the statistical reactance distribution "
        "assumptions of NEMA MG-1. The implementation is in "
        "`core/param_estimator.py:22–179` (function `estimate_params`)."
    )

    st.markdown("**Required input data:**")
    st.markdown(
        "- Line voltage $V_l$ and frequency $f$.\n"
        "- Rated shaft power $P_n$ (kW).\n"
        "- Rated speed $n_{nom}$ (rpm) — used to derive the number of poles "
        "and $s_{nom}$.\n"
        "- Rated efficiency $\\eta$ and power factor $\\cos\\varphi$.\n"
        "- Starting-to-rated current ratio $I_p/I_n$.\n"
        "- Starting-to-rated torque ratio $T_p/T_n$."
    )

    st.markdown("**Calculation sequence:**")

    st.markdown("**1.** Derivation of slip and rated quantities:")
    _eq(r"s_{nom} = 1 - \frac{n_{nom}}{n_s}, \qquad n_s = \frac{120\,f}{p}")
    _eq(r"I_n = \frac{P_n}{\sqrt{3}\,V_l\,\eta\,\cos\varphi}, \qquad T_n = \frac{P_n}{\omega_{r,nom}}")

    st.markdown("**2.** Estimation of starting current and short-circuit impedance:")
    _eq(r"I_p = \left(\frac{I_p}{I_n}\right) I_n, \qquad Z_k = \frac{V_f}{I_p}, \qquad X_k = Z_k\,\sqrt{1 - \cos^2\!\varphi_p}")
    st.markdown(
        "where $\\cos\\varphi_p \\approx 0{,}20$ is the typical starting power factor "
        "(NEMA B assumption for single squirrel-cage motors)."
    )

    st.markdown("**3.** Leakage reactance distribution (NEMA B assumption):")
    _eq(r"X_{ls} = 0{,}4\,X_k, \qquad X_{lr}' = 0{,}6\,X_k")

    st.markdown(
        "**4.** Estimation of $R_s$ and $R_r'$ by rated power balance:"
    )
    _eq(r"P_{cu,s} = 3\,I_n^2\,R_s = P_{in} - P_{ag} - P_{fe}, \qquad P_{cu,r} = 3\,I_n^2\,R_r' = s_{nom}\,P_{ag}")

    st.markdown("**5.** Magnetizing reactance by subtraction:")
    _eq(r"X_m = X_{cc} - X_{ls}, \qquad X_{cc} = \frac{V_f}{I_{cc}}")

    _div_warn(
        "**Nameplate Estimator limitations:** the parameters obtained are approximations "
        "based on NEMA statistical assumptions — suitable for simulation and "
        "sensitivity analysis, but **do not replace physical identification tests** "
        "(no-load and locked-rotor tests per IEEE Std 112). For motors outside the "
        "NEMA B standard (double cage, wound rotor, high-efficiency IE4 motors), "
        "results may deviate significantly from real values."
    )

    st.divider()

    # ── Section 7.2: IEEE Std 112-2017 ──────────────────────────────────────
    st.markdown("### Section 7.2 — IEEE Std 112-2017 Estimator (three physical tests)")

    st.info(
        "**When to use:** physical test data available (DC, no-load, "
        "locked rotor). Indicated for high-precision parameters, dynamic model validation, "
        "commissioning, and comparison with nameplate data."
    )

    _h4("7.2.1 — Background")
    st.markdown(
        "The method identifies $R_s, R_r', X_m, X_{ls}, X_{lr}', R_{fe}$ from "
        "**three physical tests** described in IEEE Std 112-2017. The implementation "
        "is in `core/param_estimator.py:193–406` (function "
        "`estimate_params_ieee_tests`). Each test exploits a specific operating condition "
        "of the T-equivalent circuit, isolating a subset of the parameters."
    )

    _h4("7.2.2 — DC Test (IEEE 112 Cl. 6.4)")
    st.markdown(
        "DC voltage is applied between two terminals with the rotor at rest. Since "
        "$X = 0$ in DC steady state, only resistances are seen. The calculation of "
        "$R_s$ depends on the winding connection topology "
        "(cf. `core/param_estimator.py:263–266`):"
    )
    _eq(r"R_s\Big|_Y = \tfrac{1}{2}\,\frac{V_{dc}}{I_{dc}} \qquad\text{(star — two windings in series)}")
    _eq(r"R_s\Big|_\Delta = \tfrac{3}{2}\,\frac{V_{dc}}{I_{dc}} \qquad\text{(delta — two in parallel, one in series)}")
    st.markdown(
        "**Experimental precautions:** correct the measured value to operating temperature "
        "(IEEE 112 Cl. 5.4); wait for thermal stabilization before reading. "
        "Small errors in $R_s$ propagate to other parameters via "
        "$R_r' = R_k - R_s$."
    )

    _h4("7.2.3 — No-Load Test (IEEE 112 Cl. 6.5)")
    st.markdown(
        "The motor is run without a coupled load at rated voltage and frequency. "
        "$V_{l,NL}$, $I_{NL}$, $P_{NL}$, and $f_{NL}$ are measured. The test identifies $X_m$, "
        "$R_{fe}$, and the air-gap voltage $E_{1,NL}$. Loss separation follows:"
    )
    _eq(r"P_{NL} = 3\,R_s\,I_{NL}^{\,2} + P_{fe} + P_{fw}")
    st.markdown(
        "When $P_{fw}$ (friction and windage) is not measured by coast-down, the "
        "heuristic is used (cf. `core/param_estimator.py:278`):"
    )
    _eq(r"P_{fw} = 0{,}008\,P_{NL}")
    st.markdown(
        "**Double phasor iteration** to refine $E_{1,NL}$ "
        "(cf. `core/param_estimator.py:329–376`):"
    )
    st.markdown(
        "*Iteration 1* — initial approximation assuming $I_{NL}$ in phase with $V_{f,NL}$:"
    )
    _eq(r"E_{1,NL}^{(1)} = \sqrt{(V_{f,NL} - R_s\,I_{NL})^{\,2} + (X_{ls}\,I_{NL})^{\,2}}")
    st.markdown(
        "*Iteration 2* — correct decomposition of $I_{NL}$ into components $I_{fe}$ "
        "(in phase with $E_1$) and $I_\\mu$ (in quadrature):"
    )
    _eq(r"E_{1,NL}^{(2)} = \sqrt{(V_{f,NL} - R_s\,I_{fe} - X_{ls}\,I_\mu)^{\,2} + (X_{ls}\,I_{fe} - R_s\,I_\mu)^{\,2}}")
    st.markdown("**Final results of the no-load test:**")
    _eq(r"R_{fe} = \frac{3\,E_{1,NL}^{\,2}}{P_{fe}}, \qquad I_\mu = \sqrt{I_{NL}^{\,2} - I_{fe}^{\,2}}, \qquad X_m = \frac{E_{1,NL}}{I_\mu} - X_{ls}")

    _h4("7.2.4 — Locked-Rotor Test (IEEE 112 Cl. 6.6)")
    st.markdown(
        "The rotor is mechanically locked and reduced voltage is applied until rated current "
        "is reached. Testing at reduced frequency "
        "$f_{LR} \\approx 0{,}25\\,f_{nom}$ is recommended to minimize the skin effect. "
        "The measured quantities are $V_{l,LR}$, $I_{LR}$, $P_{LR}$, and $f_{LR}$ "
        "(cf. `core/param_estimator.py:296–327`):"
    )
    _eq(r"Z_k = \frac{V_{f,LR}}{I_{LR}}, \qquad R_k = \frac{P_{LR}}{3\,I_{LR}^{\,2}}, \qquad X_k\big|_{f_{LR}} = \sqrt{Z_k^{\,2} - R_k^{\,2}}")
    st.markdown(
        "**Linear frequency correction** to project $X_k$ to rated frequency "
        "(cf. `core/param_estimator.py:312`):"
    )
    _eq(r"X_k\big|_{f_{nom}} = X_k\big|_{f_{LR}}\cdot\frac{f_{NL}}{f_{LR}}")
    st.markdown("The referred rotor resistance is obtained by subtraction:")
    _eq(r"R_r' = R_k - R_s, \qquad \text{with validation } R_r' > 0")

    _h4("7.2.5 — $X_{ls}/X_k$ Distribution by NEMA Class")
    st.markdown(
        "The short-circuit reactance $X_k$ represents the sum $X_{ls} + X_{lr}'$ — no "
        "physical test can separate the two terms. IEEE 112 adopts a "
        "**tabulated fraction**, depending on the motor construction class "
        "(cf. table `_IEEE_SPLIT_TABLE` in `core/param_estimator.py:183–190`):"
    )
    st.markdown(
        "| NEMA Class | $X_{ls}/X_k$ | $X_{lr}'/X_k$ | Application |\n"
        "|---|---|---|---|\n"
        "| A | $0{,}50$ | $0{,}50$ | Motors above $45\\;\\text{kW}$, wound rotor |\n"
        "| **B (standard)** | **$0{,}40$** | **$0{,}60$** | Industrial NEMA $1$–$100\\;\\text{kW}$ |\n"
        "| C | $0{,}30$ | $0{,}70$ | High impedance, high slip |\n"
        "| D | $0{,}50$ | $0{,}50$ | High starting torque |\n"
        "| WR (wound rotor) | $0{,}50$ | $0{,}50$ | Slip rings |\n"
        "| Custom | $\\alpha$ | $1-\\alpha$ | User-defined |"
    )

    _h4("7.2.6 — Usage Instructions (step by step)")
    st.markdown(
        "The fields corresponding to this estimator are located in the simulator "
        "sidebar, under the **IEEE Std 112-2017** mode "
        "(cf. `ui_components/sim_config.py:763–862`)."
    )
    st.markdown("**DC Test** — three values:")
    st.markdown(
        "- $V_{dc}$ (V) — DC voltage applied between two terminals.\n"
        "- $I_{dc}$ (A) — DC current measured at thermal steady state.\n"
        "- **Connection** — choose between star ($Y$) or delta ($\\Delta$)."
    )
    st.markdown("**No-Load Test** — five values:")
    st.markdown(
        "- $V_{l,NL}$ (V) — line voltage applied at the terminals.\n"
        "- $I_{NL}$ (A) — no-load line current.\n"
        "- $P_{NL}$ (W) — three-phase active power absorbed at no load.\n"
        "- $f_{NL}$ (Hz) — source frequency during the test.\n"
        "- $P_{fw}$ (W) — mechanical losses measured by coast-down "
        "(optional; leave at zero to apply the $0{,}8\\%\\,P_{NL}$ heuristic)."
    )
    st.markdown("**Locked-Rotor Test** — four values:")
    st.markdown(
        "- $V_{l,LR}$ (V) — reduced line voltage.\n"
        "- $I_{LR}$ (A) — line current near rated value.\n"
        "- $P_{LR}$ (W) — three-phase active power.\n"
        "- $f_{LR}$ (Hz) — source frequency, ideally "
        "$f_{LR} \\approx 0{,}25\\,f_{nom}$."
    )
    st.markdown(
        "**$X_{ls}/X_k$ distribution** — select the motor NEMA class. For "
        "Custom, adjust the fraction $\\alpha$ slider."
    )

    _h4("7.2.7 — Result Interpretation and Physical Sanity Criteria")
    st.markdown(
        "After execution, the estimator automatically validates each output against "
        "physical criteria. Warnings displayed in the **Calculation Details** panel "
        "(cf. `ui_components/sim_config.py:886`) indicate violations:"
    )
    st.markdown(
        "| Criterion | Physical meaning | Implementation |\n"
        "|---|---|---|\n"
        "| $R_s, R_r' > 0$ | Physically positive resistances | `param_estimator.py:269, 316` |\n"
        "| $P_{fe} > 0$ | $P_{NL}$ exceeds Joule losses plus $P_{fw}$ | L:283–291 |\n"
        "| $I_\\mu^{\\,2} > 0$ | No-load test $\\cos\\varphi$ is consistent | L:366–372 |\n"
        "| $R_k < Z_k$ | Power factor $\\le 1$ in locked-rotor test | L:301–307 |\n"
        "| $X_m / X_{ls} \\ge 5$ | Typical ratio for industrial motor | warning in `sim_config.py:947–950` |\n"
        "| $R_{fe} \\ge 50\\;\\Omega$ | $P_{fe}$ in realistic range | warning in `sim_config.py:952–955` |"
    )
    st.markdown(
        "**Connection to `MachineParams`:** the dictionary returned by the estimator is "
        "written to the fields $R_s$, $R_r'$, $X_m$, $X_{ls}$, $X_{lr}'$, $R_{fe}$ of the "
        "dataclass (cf. `core/machine_model.py:40–51`). The reference frequency "
        "$f_{ref}$ is set to $f_{NL}$ (cf. `core/machine_model.py:88–101`) and the "
        "resulting mutual reactance $X_{ml}$ is recalculated in `_xml_from_lm` "
        "(cf. `core/machine_model.py:158–163`)."
    )

    _div_warn(
        "**Cross-check recommendation:** even when using the IEEE 112 estimator, "
        "it is recommended to run the Nameplate estimator as a cross-check. "
        "Discrepancies greater than $\\pm 20\\%$ between the two methods indicate problems "
        "in the tests (unstable measurements, off-nominal temperature, harmonic distortion in "
        "the source) or that the motor under test deviates from the NEMA B standard assumed by the Nameplate method."
    )


# ─────────────────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def render_theory_tab() -> None:
    st.markdown(
        "Physical foundations of the three-phase induction machine and simulator "
        "user manual — select a tab to explore the desired topic."
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "1 - Modeling and Circuits",
        "2 - Dynamic Behavior and Torque",
        "3 - Energy Balance",
        "4 - Parameter Sensitivity",
        "5 - Operating Dynamics",
        "6 - User Manual",
        "7 - Parameter Estimators",
        "8 - Settings and Experiments",
    ])

    with tab1:
        st.markdown("## Modeling and Equivalent Circuits")
        _render_tab_circuitos()

    with tab2:
        st.markdown("## Dynamic Behavior and Torque")
        _render_tab_dinamica()

    with tab3:
        st.markdown("## Energy Balance and Power Flow")
        _render_tab_potencia()

    with tab4:
        st.markdown("## Parameter Sensitivity Guide")
        _render_tab_sensibilidade()

    with tab5:
        st.markdown("## Operating Dynamics")
        _render_tab_dinamica_operacao()

    with tab6:
        st.markdown("## Simulator User Manual")
        _render_tab_manual_de_uso()

    with tab7:
        st.markdown("## Parameter Estimators")
        _render_tab_estimadores()

    with tab8:
        st.markdown("## Settings, Alerts, and Experiments")
        st.markdown("### Numerical Settings and Alerts")
        _render_tab_config()
        st.divider()
        st.markdown("### Experiment Catalog")
        _render_tab_experimentos()
