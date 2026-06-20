# -*- coding: utf-8 -*-
"""
tim_results_dynamics.py
=======================
Tab 2 — Dynamic Analysis: waveform charts (Stacked/Side-by-side/Overlay), zoom controls, T×n.

Responsibilities:
  - Render view-mode and zoom-mode radio buttons.
  - Build and display Plotly waveform charts with zoom.
  - Render Torque × Speed expander.

Relationships:
  Imported by : ui.tim_results
  Imports     : viz.tim_charts, viz.zoom_helpers, viz.plotly_config,
                ui.chart_notes, core.tim.facade, numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.tim.facade import MachineParams
from core.constants import W_TO_KW, P_NOM_MIN_KW
from viz.tim_charts import (
    build_fig_stacked, build_fig_sidebyside, build_fig_overlay, build_fig_torque_speed,
)
from viz.plotly_config import MIT_PLOT_CFG as _PLOT_CFG
from viz.zoom_helpers import ZoomCtx, compute_t_window, apply_zoom, apply_zoom_overlay
from ui.chart_notes import emit_mit_note, MITNoteCtx


@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed(
    P_nom_kw: float, f: float, p: int, dark: bool, _cache_key: int = 0,
    *, res: dict | None = None,
) -> go.Figure:
    return build_fig_torque_speed(res=res, P_nom_kw=P_nom_kw, f=f, p=p, dark=dark)


@st.fragment
def render_tab_dynamic(
    res: dict,
    var_keys: list[str],
    var_labels_plot: list[str],
    dark: bool,
    t_events: list,
    decimals: int,
    exp_type: str,
    exp_config: dict | None,
    mp: MachineParams,
    is_mobile: bool,
    chart_ref_list: list,
    primary_color: str | None,
    tl_arr,
    res_hash: int,
) -> None:
    _PLOT_CFG_F: dict = {
        "responsive": True, "scrollZoom": False, "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {"format": "png", "filename": "simulation_chart",
                                 "scale": 3, "height": 600, "width": 1200},
    }

    _viz_opts = ["Stacked", "Overlay"] if is_mobile else ["Stacked", "Side by side", "Overlay"]
    _cur_modo = st.session_state.get("plot_mode", _viz_opts[0])
    if _cur_modo not in _viz_opts:
        st.session_state["plot_mode"] = _viz_opts[0]

    _is_pulso    = (exp_type == "load_pulse")
    _t_pulso_on  = float((exp_config or {}).get("t_load",    0.0))
    _t_pulso_off = float((exp_config or {}).get("t_removal", 0.0))
    _zoom_opts   = ["Full"]
    if _is_pulso:
        _zoom_opts.append("Load Pulse")
    else:
        _zoom_opts.append("Starting")
    _zoom_opts.append("Steady State")
    _zoom_default = "Load Pulse" if _is_pulso else _zoom_opts[0]
    _saved_zoom   = st.session_state.get("zoom_mode", _zoom_default)
    _zoom_idx     = _zoom_opts.index(_saved_zoom) if _saved_zoom in _zoom_opts else _zoom_opts.index(_zoom_default)

    _cc1, _cc2, _cc3 = st.columns([2, 2, 1])
    with _cc1:
        modo = st.radio("View", _viz_opts, horizontal=True, key="plot_mode")
    with _cc2:
        zoom_mode = st.radio(
            "Zoom", _zoom_opts, index=_zoom_idx,
            horizontal=True, key="zoom_mode",
        )
    with _cc3:
        dark_plot = st.toggle("Dark background", value=dark, key="plot_dark_toggle")

    st.write("")

    tmax_data = float(res["t"][-1])
    t_ss_idx  = int(res.get("_ss_start", 0))
    t_ss      = float(res["t"][t_ss_idx]) if t_ss_idx < len(res["t"]) else tmax_data

    _zoom_ctx = ZoomCtx(
        res         = res,
        exp_type    = exp_type,
        exp_config  = exp_config or {},
        mp_f        = mp.f,
        mp_p        = mp.p,
        t_ss        = t_ss,
        tmax_data   = tmax_data,
        t_pulse_on  = _t_pulso_on,
        t_pulse_off = _t_pulso_off,
        tl_arr      = tl_arr,
    )
    t_window = compute_t_window(zoom_mode, _zoom_ctx)

    def _apply_zoom(fig, keys):
        return apply_zoom(fig, keys, t_window, res, tl_arr)

    def _apply_zoom_overlay(fig, keys):
        return apply_zoom_overlay(fig, keys, t_window, res, tl_arr)

    _cfg = exp_config or {}
    _note_ctx = MITNoteCtx(
        exp_type  = exp_type,
        exp_config= _cfg,
        bb_sev    = float(res.get("_broken_bar_severity", 0.0)),
        s_val     = float(res.get("s", 0.0)),
        imbalance_on  = any(_cfg.get(k, 0) for k in
                        ("imbalance_a", "imbalance_b", "imbalance_c", "phase_loss_a", "phase_loss_b", "phase_loss_c")),
        is_yd     = (exp_type == "yd"),
        is_gen    = (exp_type == "generator"),
        is_sd     = (exp_type == "shutdown"),
        is_soft   = (exp_type == "soft"),
        Tl_cfg    = float(_cfg.get("Tl_final", 0.0)),
        Te_max    = float(np.max(res["Te"])) if "Te" in res else 0.0,
        mp        = mp,
    )

    def _nota_apos(key: str) -> None:
        emit_mit_note(key, _note_ctx)

    if modo == "Stacked":
        for i, (fig_single, key) in enumerate(zip(
                build_fig_sidebyside(
                    res, var_keys, var_labels_plot, dark_plot, t_events, decimals,
                    ref_list=chart_ref_list, primary_color=primary_color,
                    compact=is_mobile, tl_arr=tl_arr),
                var_keys)):
            st.plotly_chart(_apply_zoom(fig_single, [key]),
                            width="stretch", config=_PLOT_CFG_F, key=f"ems-emp-{i}")
            _nota_apos(key)
    elif modo == "Side by side":
        figs   = build_fig_sidebyside(
            res, var_keys, var_labels_plot, dark_plot, t_events, decimals,
            ref_list=chart_ref_list, primary_color=primary_color,
            compact=is_mobile, tl_arr=tl_arr)
        n_cols = min(len(figs), 3)
        rows   = [list(zip(figs, var_keys))[i:i+n_cols] for i in range(0, len(figs), n_cols)]
        for ri, row in enumerate(rows):
            cols = st.columns(len(row), gap="small")
            for ci, (col, (fig, key)) in enumerate(zip(cols, row)):
                with col:
                    st.plotly_chart(_apply_zoom(fig, [key]),
                                    width="stretch", config=_PLOT_CFG_F,
                                    key=f"ems-side-{ri}-{ci}")
                    _nota_apos(key)
    else:
        fig_overlay = build_fig_overlay(
            res, var_keys, var_labels_plot, dark_plot, t_events, decimals,
            ref_list=chart_ref_list, primary_color=primary_color,
            compact=is_mobile, tl_arr=tl_arr)
        st.plotly_chart(_apply_zoom_overlay(fig_overlay, var_keys),
                        width="stretch", config=_PLOT_CFG_F, key="ems-overlay")
        for key in var_keys:
            _nota_apos(key)

    with st.expander("Torque × Speed", expanded=False):
        _P_mec_ss = float(res.get("P_mec", 0.0))
        _fig_ts = _cached_fig_torque_speed(
            P_nom_kw=max(_P_mec_ss / W_TO_KW, P_NOM_MIN_KW),
            f=mp.f, p=mp.p, dark=dark_plot,
            _cache_key=res_hash, res=res,
        )
        st.plotly_chart(_fig_ts, width="stretch")
