# -*- coding: utf-8 -*-
"""
dc_results.py
=============
Orchestrator for the four DC machine result sub-tabs: Overview, Dynamic Analysis,
Diagnostics & Faults, and Asset Management. Mirrors the modular structure of tim_results.

Responsibilities:
  - Build the four result tabs and delegate each to its dedicated sub-module.
  - Render the DCM PDF export block.

Relationships:
  Imported by : IWS_UI
  Imports     : core.dc.facade, ui.dc_results_overview, ui.dc_results_dynamics,
                ui.dc_results_diagnostics, ui.dc_results_asset

Extending:
  - To add a new DCM sub-tab, create ui/dc_results_<name>.py and wire it here,
    following the same pattern as tim_results.
"""

from __future__ import annotations

import streamlit as st

from core.dc.facade import DCMachineParams

from ui.dc_results_overview     import render_dc_tab_overview
from ui.dc_results_dynamics     import render_dc_tab_dynamic
from ui.dc_results_diagnostics  import render_dc_tab_diagnostics
from ui.dc_results_asset        import render_dc_tab_assets


# ─────────────────────────────────────────────────────────────────────────────
# PDF EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _render_dc_pdf_export(
    res: dict,
    mp: DCMachineParams,
    var_keys: list[str],
    var_labels: list[str],
    t_events: list,
    exp_label: str,
    exp_type: str,
    tmax: float,
    h: float,
    ref_list: list | None,
) -> None:
    from viz.pdf_dc import generate_dc  # noqa: E402

    st.markdown("---")
    st.markdown('<p class="slabel">Export Report</p>', unsafe_allow_html=True)

    if not st.session_state.get("pdf_bytes_dc"):
        if st.button("DC Machine Report (PDF)", key="btn_pdf_dc"):
            with st.spinner("Generating DC machine report..."):
                st.session_state["pdf_bytes_dc"] = generate_dc(
                    exp_label=exp_label,
                    mp=mp,
                    res=res,
                    var_keys=var_keys,
                    var_labels=var_labels,
                    t_events=t_events,
                    exp_type=exp_type,
                    tmax=tmax,
                    h=h,
                    exp_config=st.session_state.get("sim_result", {}).get("exp_config"),
                    input_mode=st.session_state.get("wi_dc_input_mode"),
                    ref_list=ref_list,
                )
            st.rerun()
    else:
        st.download_button(
            label="Download DC Machine Report (PDF)",
            data=st.session_state["pdf_bytes_dc"],
            file_name="report_iws_dcm.pdf",
            mime="application/pdf",
            key="btn_pdf_dc_download",
        )
        if st.button("Regenerate DCM", key="btn_pdf_dc_regen"):
            del st.session_state["pdf_bytes_dc"]
            st.rerun()

    if st.session_state.get("pdf_bytes_dc") and not st.session_state.get("pdf_bytes"):
        st.session_state["pdf_bytes"] = st.session_state["pdf_bytes_dc"]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def render_results_dc(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    mp: DCMachineParams,
    exp_label: str,
    exp_type: str,
    exp_config: dict,
    tmax: float,
    h: float,
    decimals: int = 3,
    ref_list: list | None = None,
    energy_tariff: float = 0.75,
    **kwargs,
) -> None:
    """Renders the 4 DC machine result sub-tabs."""
    d   = decimals
    exc = mp.excitation if mp else res.get("excitation", "sep_motor")
    is_gen = exc in ("sep_gen", "shunt_gen")

    _cache_key = hash(repr(res.get("ia", [])[:5]))

    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs(
        ["Overview", "Dynamic Analysis", "Diagnostics & Faults", "Asset Management"],
        key="results_tabs_dc",
    )

    with tab_visao:
        render_dc_tab_overview(res, mp, exc, is_gen, d, energy_tariff)

    with tab_dinamica:
        render_dc_tab_dynamic(res, var_keys, var_labels, dark, t_events, d, exp_type, mp, ref_list, exc, _cache_key)

    with tab_diag:
        render_dc_tab_diagnostics(res, mp, exc, d)

    with tab_ativos:
        render_dc_tab_assets(res, mp, exc, is_gen, d, h, energy_tariff)

    _render_dc_pdf_export(res, mp, var_keys, var_labels, t_events, exp_label, exp_type, tmax, h, ref_list)
