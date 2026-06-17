# -*- coding: utf-8 -*-
"""
blocos_krause.py
================
Block diagram of the Krause 0dq model with expandable equation cards.

Responsibilities:
  - Render 6 CSS cards (voltage → flux, rotor flux, magnetising flux, currents,
    torque, mechanical equation).
  - Provide expandable expanders with full equations and physical meaning.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, viz.tim_charts
"""

from __future__ import annotations

import streamlit as st

from viz.tim_charts import _plot_theme

from ui.theory._shared import _dark


def render_blocos_krause() -> None:
    """Block diagram of the Krause 0dq model, with expandable cards per equation.

    Layout: 6 main cards (Vqs/Vds → ψqs/ψds, ψqr/ψdr, ψmq/ψmd, iqs/ids,
    Te, ωr). Each card shows the simplified equation; the user can expand
    to see the full version and its physical meaning.
    """
    dark = _dark()
    pt   = _plot_theme(dark)

    col_bg     = pt["paper_bg"]
    col_fg     = pt["fg"]
    col_border = pt["grid"]
    col_accent = "#4f8ef7" if dark else "#1d4ed8"

    # Card CSS (reuses project pgroup aesthetics)
    st.markdown(
        f"""
        <style>
        .krause-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.9rem;
            margin: 0.5rem 0 0.8rem 0;
        }}
        .krause-card {{
            background: {col_bg};
            border: 1px solid {col_border};
            border-left: 3px solid {col_accent};
            border-radius: 10px;
            padding: 0.8rem 1.0rem 0.6rem 1.0rem;
        }}
        .krause-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: {col_fg};
            margin-bottom: 0.3rem;
        }}
        .krause-subtitle {{
            font-size: 0.78rem;
            color: {col_fg};
            opacity: 0.7;
            margin-bottom: 0.4rem;
        }}
        @media (max-width: 768px) {{
            .krause-grid {{ grid-template-columns: 1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── 2-column layout (side by side) ───────────────────────────────────────
    blocos = [
        {
            "titulo": "1. Voltages → Stator Flux Linkages",
            "sub":   "Integration of applied voltages",
            "eq_simples": r"\dot{\psi}_{qs},\,\dot{\psi}_{ds} = f(V_{qs},\,V_{ds},\,\omega_e,\,\psi_{mq},\,\psi_{md})",
            "eq_full":    [
                r"\dot{\psi}_{qs} = \omega_b\!\left(V_{qs} - \tfrac{\omega_e}{\omega_b}\psi_{ds} + \tfrac{R_s}{X_{ls}}(\psi_{mq}-\psi_{qs})\right)",
                r"\dot{\psi}_{ds} = \omega_b\!\left(V_{ds} + \tfrac{\omega_e}{\omega_b}\psi_{qs} + \tfrac{R_s}{X_{ls}}(\psi_{md}-\psi_{ds})\right)",
            ],
            "fisica": (
                "The voltages $V_{qs}$ and $V_{ds}$ (synchronous reference frame) impose the derivative of "
                "the stator flux linkages. The cross-coupling via $\\omega_e$ represents "
                "the reference frame rotation, and the $R_s/X_{ls}$ term is the resistive voltage drop."
            ),
        },
        {
            "titulo": "2. Rotor Flux Linkages",
            "sub":   "Short-circuited squirrel-cage rotor",
            "eq_simples": r"\dot{\psi}_{qr},\,\dot{\psi}_{dr} = f(\omega_e-\omega_r,\,\psi_{mq},\,\psi_{md})",
            "eq_full":    [
                r"\dot{\psi}_{qr} = \omega_b\!\left(-\tfrac{\omega_e-\omega_r}{\omega_b}\psi_{dr} + \tfrac{R_r}{X_{lr}}(\psi_{mq}-\psi_{qr})\right)",
                r"\dot{\psi}_{dr} = \omega_b\!\left(\tfrac{\omega_e-\omega_r}{\omega_b}\psi_{qr} + \tfrac{R_r}{X_{lr}}(\psi_{md}-\psi_{dr})\right)",
            ],
            "fisica": (
                "Since the rotor is short-circuited ($V_{qr} = V_{dr} = 0$), only the internal "
                "resistive drop term and the cross-coupling through the relative speed "
                "$\\omega_e - \\omega_r$ govern the evolution of the rotor flux linkages."
            ),
        },
        {
            "titulo": "3. Magnetising Flux Linkages",
            "sub":   "Air-gap coupling",
            "eq_simples": r"\psi_{mq},\,\psi_{md} = \text{weighted average of }\psi_s,\,\psi_r",
            "eq_full":    [
                r"\psi_{mq} = X_{ml}\!\left(\tfrac{\psi_{qs}}{X_{ls}} + \tfrac{\psi_{qr}}{X_{lr}}\right)",
                r"\psi_{md} = X_{ml}\!\left(\tfrac{\psi_{ds}}{X_{ls}} + \tfrac{\psi_{dr}}{X_{lr}}\right)",
                r"\tfrac{1}{X_{ml}} = \tfrac{1}{X_m} + \tfrac{1}{X_{ls}} + \tfrac{1}{X_{lr}}",
            ],
            "fisica": (
                "The air-gap fluxes are a weighted combination of stator and rotor flux linkages "
                "through the resultant mutual reactance $X_{ml}$. This is the point at which "
                "stator and rotor are magnetically coupled."
            ),
        },
        {
            "titulo": "4. Stator Currents",
            "sub":   "Magnetic Ohm's law",
            "eq_simples": r"i_{qs},\,i_{ds} = \tfrac{\psi_{qs}-\psi_{mq}}{X_{ls}},\;\tfrac{\psi_{ds}-\psi_{md}}{X_{ls}}",
            "eq_full":    [
                r"i_{qs} = \tfrac{\psi_{qs} - \psi_{mq}}{X_{ls}}",
                r"i_{ds} = \tfrac{\psi_{ds} - \psi_{md}}{X_{ls}}",
            ],
            "fisica": (
                "The currents are obtained directly from the difference between total flux linkage and "
                "magnetising flux linkage, divided by the leakage reactance. In steady state, the current "
                "is in phase with the resistive drop $R_s \\cdot i$ across the stator."
            ),
        },
        {
            "titulo": "5. Electromagnetic Torque",
            "sub":   "Cross product of flux linkages and currents",
            "eq_simples": r"T_e = \tfrac{3}{2}\cdot\tfrac{p}{2}\cdot\tfrac{1}{\omega_b}(\psi_{ds}\,i_{qs}-\psi_{qs}\,i_{ds})",
            "eq_full":    [
                r"T_e = \tfrac{3}{2}\cdot\tfrac{p}{2}\cdot\tfrac{1}{\omega_b}\,(\psi_{ds}\,i_{qs} - \psi_{qs}\,i_{ds})",
            ],
            "fisica": (
                "The cross product of stator flux linkage and stator current produces the torque. "
                "This is the dq analogue of the classical expression $T \\propto \\vec{\\psi}\\times\\vec{i}$. "
                "The $3/2$ factor arises from the power-invariant transformation; $p/2$ converts "
                "magnetic poles to mechanical pole pairs."
            ),
        },
        {
            "titulo": "6. Mechanical Equation",
            "sub":   "Shaft dynamics",
            "eq_simples": r"\dot{\omega}_r = \tfrac{p}{2J}(T_e - T_L) - \tfrac{B}{J}\,\omega_r",
            "eq_full":    [
                r"\dot{\omega}_r = \tfrac{p}{2J}\,(T_e - T_L) - \tfrac{B}{J}\,\omega_r",
            ],
            "fisica": (
                "Newton's second law for rotation: net torque ($T_e - T_L$) divided by "
                "inertia $J$ determines the angular acceleration. The $B\\,\\omega_r/J$ term models "
                "viscous friction. The mechanical time constant is typically 10–100× the electrical one."
            ),
        },
    ]

    # Render card grid (summary)
    cards_html = '<div class="krause-grid">'
    for b in blocos:
        cards_html += (
            f'<div class="krause-card">'
            f'  <div class="krause-title">{b["titulo"]}</div>'
            f'  <div class="krause-subtitle">{b["sub"]}</div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # Detailed expanders per block
    st.caption("Expand each block to view the complete equation and its physical meaning.")
    for b in blocos:
        with st.expander(b["titulo"], expanded=False):
            st.markdown(f"_{b['sub']}_")
            for eq in b["eq_full"]:
                st.latex(eq)
            st.markdown(b["fisica"])

    # Flow diagram between blocks (compact text)
    st.markdown("---")
    st.markdown(
        "**Solver computational flow:** "
        "$V_{qs},V_{ds}$ → (1) → $\\psi_s$ ⇄ (3) ⇄ $\\psi_r$ ← (2) ← $\\omega_e-\\omega_r$ ; "
        "$\\psi_s,\\psi_m$ → (4) → $i_s$ ; $\\psi_s,i_s$ → (5) → $T_e$ → (6) → $\\omega_r$ "
        "(feeds back into 2)."
    )
