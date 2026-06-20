# -*- coding: utf-8 -*-
"""
theme.py
========
Defines the dark/light colour palette and applies global CSS styling to the Streamlit application.

Responsibilities:
  - Provide _palette(dark) returning a colour dict with surface, border, text, and accent keys.
  - Apply Streamlit-compatible CSS via apply_css(dark) for typography and component overrides.
  - Expose REF_COLORS and REF_DASHES constants for consistent chart theming across the project.

Relationships:
  Imported by : ui.sim_config, ui.sim_results, viz.pdf_commons,
                viz.pdf_report_v2, IWS_UI
  Imports     : streamlit

Extending:
  - To add a new theme variant, extend _palette with a new branch and update apply_css accordingly.
"""
from pathlib import Path

import streamlit as st

REF_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
REF_DASHES = ["dash", "dot", "solid", "dash", "dot"]

_CSS_PATH = Path(__file__).parent / "assets" / "theme.css"


def _palette(dark: bool) -> dict:
    if dark:
        return dict(
            bg="#0e0e0e", surface="#1a1a1a", surface2="#242424",
            border="#333333", accent="#ffffff", accent2="#ffffff",
            on_accent="#000000",
            text="#ffffff", muted="#b5b5b5",
            success="#22eb6c", danger="#ff4444", warning="#fd7e14",
            warn_bg="rgba(255,68,68,0.08)", input_bg="#111111",
            tag="#242424",
            # semantic: status
            info="#0dcaf0",
            # semantic: phases
            phase_a="#ef4444", phase_b="#22c55e", phase_c="#3b82f6",
            # semantic: energy flows (Sankey)
            energy_in="#3b82f6", energy_cu="#ef4444", energy_fe="#f59e0b",
            energy_fw="#a855f7", energy_mec="#22c55e", energy_out="#22c55e",
            # semantic: braking methods
            brake_plug="#ef4444", brake_dc="#3b82f6", brake_regen="#22c55e",
        )
    return dict(
        bg="#ffffff", surface="#ebebeb", surface2="#ebebeb",
        border="#d0d0d0", accent="#000000", accent2="#000000",
        on_accent="#ffffff",
        text="#000000", muted="#555555",
        success="#198754", danger="#dc3545", warning="#fd7e14",
        warn_bg="rgba(220,38,38,0.06)", input_bg="#ffffff",
        tag="#ffffff",
        # semantic: status
        info="#0d6efd",
        # semantic: phases
        phase_a="#dc3545", phase_b="#198754", phase_c="#0d6efd",
        # semantic: energy flows (Sankey)
        energy_in="#0d6efd", energy_cu="#dc3545", energy_fe="#fd7e14",
        energy_fw="#6f42c1", energy_mec="#198754", energy_out="#198754",
        # semantic: braking methods
        brake_plug="#dc3545", brake_dc="#0d6efd", brake_regen="#198754",
    )


def apply_css(dark: bool) -> None:
    """Lê o template CSS externo, formata com a paleta e injeta no Streamlit.

    O CSS reside em ``ui/assets/theme.css`` com placeholders no estilo
    ``str.format`` (``{nome}``); chaves CSS literais são escapadas como ``{{`` ``}}``.
    """
    css_template = _CSS_PATH.read_text(encoding="utf-8")
    css = css_template.format(**_palette(dark))
    st.markdown(css, unsafe_allow_html=True)

