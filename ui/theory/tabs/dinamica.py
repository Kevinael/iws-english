# -*- coding: utf-8 -*-
"""
ui/theory/tabs/dinamica.py
==========================
Theory Tab 2 — Dynamic Behavior and Torque.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq
from ui.theory_interactive import render_zonas_operacao, render_boucherot


def render_tab_dinamica() -> None:
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
