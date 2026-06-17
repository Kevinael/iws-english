# -*- coding: utf-8 -*-
"""
ui/theory/tabs/potencia.py
==========================
Theory Tab 3 — Energy Balance and Power Flow.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn, _show_img
from ui.theory_interactive import render_sankey_potencia


def render_tab_potencia() -> None:
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
