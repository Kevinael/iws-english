# -*- coding: utf-8 -*-
"""
dc_results_dynamics.py
======================
Tab 2 — Dynamic Analysis: waveform charts (stacked / side-by-side / overlay) and torque-speed curve (DC machine).

Responsibilities:
  - Render view/zoom selectors and slice the result arrays accordingly.
  - Build the chosen waveform layout via cached/non-cached chart builders.
  - Render the torque × speed curve.

Relationships:
  Imported by : ui.dc_results
  Imports     : core.dc.facade, ui.dc_results_shared, viz.plotly_charts_dc, viz.plotly_config, numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.dc.facade import DCMachineParams
from viz.plotly_config import DC_PLOT_CFG as _PLOT_CFG
from viz.plotly_charts_dc import (
    build_fig_sidebyside_dc,
    build_fig_overlay_dc,
)
from ui.dc_results_shared import (
    _cached_fig_stacked_dc,
    _cached_fig_torque_speed_dc,
    _nota_apos_dc,
)


def render_dc_tab_dynamic(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    d: int,
    exp_type: str,
    mp: DCMachineParams,
    ref_list: list | None,
    exc: str,
    _cache_key: int,
) -> None:
    if ref_list:
        try:
            from ui.tim_results import render_ref_panel
            render_ref_panel(ref_list)
        except Exception:
            pass

    _cc1, _cc2, _cc3 = st.columns([2, 2, 1])
    with _cc1:
        viz_opts  = ["Stacked", "Side by Side", "Overlay"]
        plot_mode = st.radio("View", viz_opts, horizontal=True,
                             key="plot_mode_dc", label_visibility="visible")
    with _cc2:
        zoom_opts = ["Full", "Transient", "Steady State"]
        zoom_mode = st.radio("Zoom", zoom_opts, horizontal=True,
                             key="zoom_mode_dc", label_visibility="visible")
    with _cc3:
        dark_plot = st.toggle("Dark background", key="plot_dark_dc", value=dark)

    t_arr = res["t"]
    tmax_sim = float(t_arr[-1])
    if zoom_mode == "Transient":
        t_cut = tmax_sim * 0.3
        mask  = t_arr <= t_cut
    elif zoom_mode == "Steady State":
        t_cut = tmax_sim * 0.7
        mask  = t_arr >= t_cut
    else:
        mask = np.ones(len(t_arr), dtype=bool)

    res_zoom = {k: (v[mask] if isinstance(v, np.ndarray) and len(v) == len(t_arr) else v)
                for k, v in res.items()}

    tl_arr = res_zoom.get("Tl")

    if plot_mode == "Stacked":
        fig = _cached_fig_stacked_dc(
            res_zoom, tuple(var_keys), tuple(var_labels),
            dark_plot, tuple(t_events), d, _cache_key=_cache_key,
        )
        st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key="dc-stacked")
        for _vk in var_keys:
            _nota_apos_dc(_vk, exp_type, mp)

    elif plot_mode == "Side by Side":
        figs = build_fig_sidebyside_dc(
            res_zoom, var_keys, var_labels, dark_plot, list(t_events), d,
            ref_list=ref_list, tl_arr=tl_arr,
        )
        for i, f in enumerate(figs):
            st.plotly_chart(f, use_container_width=True, config=_PLOT_CFG, key=f"dc-side-{i}")

    else:  # Overlay
        fig = build_fig_overlay_dc(
            res_zoom, var_keys, var_labels, dark_plot, list(t_events), d,
            ref_list=ref_list, tl_arr=tl_arr,
        )
        st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key="dc-overlay")

    st.markdown('<p class="slabel">Torque × Speed Curve</p>', unsafe_allow_html=True)
    fig_tn = _cached_fig_torque_speed_dc(res, exc, dark_plot, _cache_key=_cache_key)
    st.plotly_chart(fig_tn, use_container_width=True, config=_PLOT_CFG, key="dc-torque-speed")
