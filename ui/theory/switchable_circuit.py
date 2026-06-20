# -*- coding: utf-8 -*-
"""
switchable_circuit.py
======================
Switchable equivalent circuit: Full (with Rfe) vs IEEE simplified (without Rfe).

Responsibilities:
  - Render radio selector and PNG image of the equivalent circuit.
  - Display LaTeX loop equation for the selected model.

Relationships:
  Imported by : ui.theory_interactive (re-export)
  Imports     : ui.theory._shared, ui.theory.transients (_build_circuit_png,
                _palette_theory)
"""

from __future__ import annotations

import streamlit as st

from ui.theory._shared import _get_mp, _dark
from ui.theory.transients import _build_circuit_png


def render_switchable_circuit() -> None:
    """Switchable equivalent circuit: Full (with Rfe) ↔ IEEE simplified (without Rfe)."""
    mp   = _get_mp()
    dark = _dark()

    modo = st.radio(
        "Circuit model",
        options=["Full — with $R_{fe}$", "IEEE simplified — without $R_{fe}$"],
        horizontal=True,
        key="th_circ_modo",
    )
    simplified = "IEEE" in modo

    mp_key = (
        float(mp.Vl), float(mp.f), float(mp.Rs), float(mp.Rr),
        float(mp.Xm), float(mp.Xls), float(mp.Xlr),
        float(getattr(mp, "Rfe", 500.0)), int(mp.p),
    )
    png_bytes = _build_circuit_png(mp_key, dark, simplified)
    st.image(png_bytes, width="stretch")

    if simplified:
        st.markdown(
            r"**Loop equation** — $R_{fe}$ branch removed ($R_{fe} \to \infty$, open circuit):"
        )
        st.latex(
            r"Z_{total} = R_s + jX_{ls} + jX_m \,\Big\|\,"
            r"\!\left(jX_{lr} + \tfrac{R_r}{s}\right)"
        )
        st.markdown(
            "Simplification valid when $P_{fe} \\lesssim 2\\%\\,P_{nom}$. "
            "Efficiency is calculated separately without loss of accuracy."
        )
    else:
        st.markdown(r"**Loop equation** — full model with core losses:")
        st.latex(
            r"Z_{total} = R_s + jX_{ls} + "
            r"\left(jX_m \,\Big\|\, R_{fe}\right) \,\Big\|\,"
            r"\!\left(jX_{lr} + \tfrac{R_r}{s}\right)"
        )
