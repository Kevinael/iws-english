# -*- coding: utf-8 -*-
"""
tim_results.py
==============
Orchestrator for the four MIT result sub-tabs: Overview, Dynamic Analysis,
Diagnostics & Faults, and Asset Management.

Responsibilities:
  - Compute shared pre-requisites (energy metrics, insights, res_hash).
  - Create the four st.tabs and delegate rendering to sub-modules.
  - Render export panel (PDF academic + industrial).

Relationships:
  Imported by : IWS_UI
  Imports     : ui_components.tim_results_overview, tim_results_dynamics,
                tim_results_diagnostics, tim_results_asset,
                core.tim.facade, core.tim.energy_analysis, core.tim.diagnostics,
                viz.pdf_academico, viz.pdf_industrial, utils.text_utils, ui.theme,
                numpy, streamlit
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from core.tim.facade import MachineParams
from core.tim import compute_energy_metrics, generate_insights
from viz.pdf_academico import generate_academico
from viz.pdf_industrial import generate_industrial
from utils.text_utils import _strip_latex
from ui.theme import REF_COLORS, REF_DASHES

from ui_components.tim_results_overview     import render_tab_overview
from ui_components.tim_results_dynamics     import render_tab_dynamic
from ui_components.tim_results_diagnostics  import render_tab_diagnosis
from ui_components.tim_results_asset        import render_tab_assets


@st.cache_data(show_spinner=False)
def _cached_energy_metrics(res: dict, tariff: float) -> dict:
    return compute_energy_metrics(res, tariff)


def render_ref_panel(ref_list: list | None) -> None:
    """Sidebar widget for managing reference simulation overlays."""
    if not ref_list:
        return
    st.markdown("**Reference simulations**")
    for i, r in enumerate(ref_list):
        lbl   = r.get("exp_label", f"Ref {i+1}")
        color = r.get("color", REF_COLORS[i % len(REF_COLORS)])
        dash  = r.get("dash",  REF_DASHES[i % len(REF_DASHES)])
        st.markdown(
            f'<span style="color:{color}; font-style:italic;">▬▬ {lbl}</span>',
            unsafe_allow_html=True,
        )


def _render_export_panel(
    res: dict,
    mp: MachineParams,
    exp_label: str,
    exp_type: str,
    exp_config: dict | None,
    var_keys: list[str],
    var_labels: list[str],
    t_events: list,
    ref_list: list | None,
    energy_tariff: float,
) -> None:
    st.write("")
    st.divider()
    st.markdown('<p class="slabel">Export</p>', unsafe_allow_html=True)

    _tmax_exp = float(res["t"][-1]) if len(res.get("t", [])) > 0 else 1.0
    _h_exp    = float(res["t"][1] - res["t"][0]) if len(res.get("t", [])) > 1 else 1e-3

    _pdf_load_torque = float((exp_config or {}).get("Tl_final", 0.0))
    try:
        _pdf_insights = generate_insights(
            res=res, mp=mp,
            load_torque=_pdf_load_torque,
            tmax=_tmax_exp, exp_type=exp_type,
        )
    except Exception:
        _pdf_insights = []

    _ecol1, _ecol2 = st.columns(2)

    with _ecol1:
        if not st.session_state.get("pdf_bytes_academico"):
            if st.button("Academic Report", key="btn_pdf_academico"):
                with st.spinner("Generating Academic Report..."):
                    st.session_state["pdf_bytes_academico"] = generate_academico(
                        exp_label=exp_label, mp=mp, res=res,
                        var_keys=var_keys, var_labels=var_labels, t_events=t_events,
                        exp_type=exp_type, ref_list=ref_list,
                        energy_tariff=energy_tariff,
                        tmax=_tmax_exp, h=_h_exp,
                        insights=_pdf_insights,
                        load_torque=_pdf_load_torque,
                        exp_config=st.session_state.get("sim_result", {}).get("exp_config"),
                        input_mode=["Enter parameters manually",
                                    "Estimate from nameplate data",
                                    "Determine from IEEE 112 tests"][
                                       st.session_state.get("_param_source_idx", 0)],
                    )
                st.rerun()
        else:
            st.download_button(
                label="Download Academic Report (PDF)",
                data=st.session_state["pdf_bytes_academico"],
                file_name="report_iws_academic.pdf",
                mime="application/pdf",
                key="btn_pdf_academico_download",
            )
            if st.button("Regenerate Academic", key="btn_pdf_academico_regen"):
                del st.session_state["pdf_bytes_academico"]
                st.rerun()

    with _ecol2:
        if not st.session_state.get("pdf_bytes_industrial"):
            if st.button("Industrial Report", key="btn_pdf_industrial"):
                with st.spinner("Generating Industrial Report..."):
                    st.session_state["pdf_bytes_industrial"] = generate_industrial(
                        exp_label=exp_label, mp=mp, res=res,
                        var_keys=var_keys, var_labels=var_labels, t_events=t_events,
                        exp_type=exp_type, ref_list=ref_list,
                        energy_tariff=energy_tariff,
                        tmax=_tmax_exp, h=_h_exp,
                        insights=_pdf_insights,
                        load_torque=_pdf_load_torque,
                        exp_config=st.session_state.get("sim_result", {}).get("exp_config"),
                        input_mode=["Enter parameters manually",
                                    "Estimate from nameplate data",
                                    "Determine from IEEE 112 tests"][
                                       st.session_state.get("_param_source_idx", 0)],
                    )
                st.rerun()
        else:
            st.download_button(
                label="Download Industrial Report (PDF)",
                data=st.session_state["pdf_bytes_industrial"],
                file_name="report_iws_industrial.pdf",
                mime="application/pdf",
                key="btn_pdf_industrial_download",
            )
            if st.button("Regenerate Industrial", key="btn_pdf_industrial_regen"):
                del st.session_state["pdf_bytes_industrial"]
                st.rerun()

    if st.session_state.get("pdf_bytes_academico") and not st.session_state.get("pdf_bytes"):
        st.session_state["pdf_bytes"] = st.session_state["pdf_bytes_academico"]


def render_results(
    res: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    mp: MachineParams,
    exp_label: str,
    exp_type: str = "dol",
    decimals: int = 3,
    ref_list: list | None = None,
    primary_color: str | None = None,
    is_mobile: bool = False,
    energy_tariff: float = 0.75,
    exp_config: dict | None = None,
    torque_fn=None,
) -> None:
    """KPIs + charts + economic analysis + FFT + PDF button."""
    st.divider()

    var_labels_plot = [_strip_latex(lbl) for lbl in var_labels]

    _tl_arr = None
    if "Te" in var_keys and torque_fn is not None:
        try:
            if "TL" not in res:
                res["TL"] = np.fromiter((torque_fn(t) for t in res["t"]), dtype=float, count=len(res["t"]))
            _tl_arr = res["TL"]
        except Exception:
            pass

    _res_hash = int(hash((res["Te"][-1], res["Te"].std(), res["t"][-1], res.get("_broken_bar_severity", 0))))

    if st.session_state.get("_last_exp_for_zoom") != exp_type:
        st.session_state.pop("zoom_mode", None)
        st.session_state["_last_exp_for_zoom"] = exp_type

    chart_ref_list = [
        {
            "res":   r["res"],
            "color": r.get("color", "#888888"),
            "dash":  r.get("dash", "dash"),
            "label": r.get("exp_label", "Reference"),
        }
        for r in (ref_list or [])
        if r.get("res") is not None
    ]

    _em = _cached_energy_metrics(res, energy_tariff) if exp_type != "shutdown" else {}

    _load_torque = float((exp_config or {}).get("Tl_final", 0.0))
    _tmax_val    = float(res["t"][-1])
    _insights    = generate_insights(res, mp, _load_torque, _tmax_val, exp_type=exp_type, exp_config=exp_config)
    _n_critico   = sum(1 for i in _insights if i.level == "error")
    _n_alerta    = sum(1 for i in _insights if i.level == "warning")

    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs(
        ["Overview", "Dynamic Analysis", "Diagnostics & Faults", "Asset Management"],
        key="results_tabs",
    )

    with tab_visao:
        render_tab_overview(
            res=res, mp=mp, exp_type=exp_type, exp_config=exp_config,
            decimals=decimals, t_events=t_events, energy_tariff=energy_tariff,
            insights=_insights, n_critico=_n_critico, n_alerta=_n_alerta, em=_em,
        )

    with tab_dinamica:
        if not var_keys:
            st.info("No variable selected. Return to configuration and choose variables to plot.")
        else:
            render_tab_dynamic(
                res=res,
                var_keys=list(var_keys),
                var_labels_plot=list(var_labels_plot),
                dark=dark,
                t_events=t_events,
                decimals=decimals,
                exp_type=exp_type,
                exp_config=exp_config,
                mp=mp,
                is_mobile=is_mobile,
                chart_ref_list=chart_ref_list,
                primary_color=primary_color,
                tl_arr=_tl_arr,
                res_hash=_res_hash,
            )

    with tab_diag:
        render_tab_diagnosis(
            res=res, mp=mp, var_keys=var_keys, var_labels=var_labels,
            insights=_insights, n_critico=_n_critico, n_alerta=_n_alerta,
            em=_em, dark=dark, res_hash=_res_hash,
        )

    with tab_ativos:
        render_tab_assets(em=_em, exp_type=exp_type, energy_tariff=energy_tariff)

    _render_export_panel(
        res=res, mp=mp, exp_label=exp_label, exp_type=exp_type,
        exp_config=exp_config,
        var_keys=var_keys, var_labels=var_labels, t_events=t_events,
        ref_list=ref_list, energy_tariff=energy_tariff,
    )
