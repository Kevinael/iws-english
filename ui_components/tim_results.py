# -*- coding: utf-8 -*-
"""
tim_results.py
==============
Renders the four induction-machine result sub-tabs: Overview (KPIs), Dynamic Analysis (waveforms), Diagnostics, and Asset Management.

Responsibilities:
  - Render KPI cards and health panel in the Overview sub-tab.
  - Build and cache Plotly waveform charts for the Dynamic Analysis sub-tab.
  - Display automated diagnostics and fault signatures in the Diagnostics sub-tab.
  - Generate and provide download buttons for academic and industrial PDF reports.

Relationships:
  Imported by : IWS_UI
  Imports     : core.tim.facade, core.tim.energy_analysis, core.tim.harmonic_analysis,
                core.tim.diagnostics, core.constants, viz.tim_charts, viz.plotly_config,
                viz.zoom_helpers, viz.pdf_academico, viz.pdf_industrial,
                utils.text_utils, ui.theme, ui_components.chart_notes

Extending:
  - To add a new result sub-tab, create a _render_tab_<name>() function and add it to render_results().
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.tim.facade import MachineParams
from core.tim.energy_analysis import compute_energy_metrics
from viz.tim_charts import (
    build_fig_stacked, build_fig_sidebyside, build_fig_overlay, build_fig_torque_speed,
)
from viz.pdf_academico import generate_academico
from viz.pdf_industrial import generate_industrial
from core.tim.harmonic_analysis import build_fig_fft
from core.tim.diagnostics import generate_insights
from utils.text_utils import _strip_latex
from ui.theme import REF_COLORS, REF_DASHES
from core.constants import (
    STARTING_SPEED_THRESHOLD,
    RELAY_CLASS_10_S,
    RELAY_CLASS_20_S,
    INSULATION_CLASS_F_C,
    INSULATION_CLASS_H_C,
    INSULATION_CLASS_C_C,
    MPCB_THERMAL_LO_RATIO,
    MPCB_THERMAL_HI_RATIO,
    MPCB_ICU_MULTIPLIER,
    MPCB_RATIO_CLASS_8,
    MPCB_RATIO_CLASS_12,
    FUSE_MULTIPLIER_MIN,
    FUSE_MULTIPLIER_MAX,
    CONTACTOR_RUPTURE_MULT,
    SPD_VN_LV, SPD_UC_LV, SPD_UP_LV,
    SPD_VN_MV, SPD_UC_MV, SPD_UP_MV,
    SPD_UC_HV_MULTIPLIER, SPD_UP_HV,
    THD_LIMIT_IEEE519,
    POWER_FACTOR_MIN,
    HOURS_PER_YEAR,
    W_TO_KW,
    P_NOM_MIN_KW,
)
from viz.plotly_config import MIT_PLOT_CFG as _PLOT_CFG
from ui_components.chart_notes import emit_mit_note, MITNoteCtx
from viz.zoom_helpers import ZoomCtx, compute_t_window, apply_zoom, apply_zoom_overlay


@st.cache_data(show_spinner=False)
def _cached_energy_metrics(res: dict, tariff: float) -> dict:
    return compute_energy_metrics(res, tariff)


@st.cache_data(show_spinner=False)
def _cached_fig_fft(res: dict, dark: bool, key: str, label: str, _cache_key: int = 0) -> go.Figure:
    return build_fig_fft(res, dark, key=key, label=label)


@st.cache_data(show_spinner=False)
def _cached_fig_stacked(
    res: dict,
    var_keys: tuple,
    var_labels: tuple,
    dark: bool,
    t_events: tuple,
    decimals: int,
    _cache_key: int = 0,  # external hash to invalidate cache when res changes
) -> go.Figure:
    return build_fig_stacked(res, list(var_keys), list(var_labels), dark, list(t_events), decimals)


@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed(
    P_nom_kw: float, f: float, p: int, dark: bool, _cache_key: int = 0,
    *, res: dict | None = None,
) -> go.Figure:
    return build_fig_torque_speed(res=res, P_nom_kw=P_nom_kw, f=f, p=p, dark=dark)






# ─────────────────────────────────────────────────────────────────────────────
# KPIs BY EXPERIMENT
# ─────────────────────────────────────────────────────────────────────────────

def _kpis_destaque(
    res: dict,
    exp_type: str,
    mp: MachineParams,
    decimals: int,
    t_events: list,
) -> list[tuple[str, str, str]]:
    """Return list of (label, value, unit) tuples for the Starting Transient expander."""
    d = decimals
    out: list[tuple[str, str, str]] = []

    def _pk(key: str) -> float:
        arr = res.get(key)
        if arr is None:
            return 0.0
        return float(np.max(np.abs(arr)))

    if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
        _ias_pk = _pk("ias")
        if _ias_pk > 0:
            out.append(("Peak Current $i_{as}$", f"{_ias_pk:.{d}f}", "A"))

        _Te_pk = _pk("Te")
        if _Te_pk > 0:
            out.append(("Peak Torque $T_e$", f"{_Te_pk:.{d}f}", "N·m"))

    if exp_type in ("dol", "yd", "comp", "soft"):
        _n_arr  = np.asarray(res.get("n", []), dtype=float)
        _t_arr  = np.asarray(res.get("t", []), dtype=float)
        _n_sync = mp.f / mp.p * 60.0
        _thresh = STARTING_SPEED_THRESHOLD * _n_sync
        _above  = np.where(_n_arr >= _thresh)[0]
        if len(_above) > 0:
            _t_acc = float(_t_arr[int(_above[0])])
            out.append(("Starting Time (95% ωs)", f"{_t_acc:.{d}f}", "s"))

    if exp_type == "yd":
        _ias = np.asarray(res.get("ias", []), dtype=float)
        _t   = np.asarray(res.get("t",   []), dtype=float)
        if len(t_events) >= 2:
            _t_sw = t_events[1]
            _idx  = np.searchsorted(_t, _t_sw)
            if _idx < len(_ias):
                _pk2 = float(np.max(np.abs(_ias[_idx:])))
                out.append(("2nd Current Peak (Δ)", f"{_pk2:.{d}f}", "A"))

    if exp_type == "comp":
        _ratio = float(getattr(mp, "_autotrafo_ratio", 0.0))
        if _ratio > 0:
            out.append(("Voltage Tap $k$", f"{_ratio:.2f}", "p.u."))

    if exp_type == "voltage_sag":
        _sag = float(res.get("_sag_magnitude", 0.0))
        if _sag > 0:
            out.append(("Sag Magnitude", f"{_sag*100:.1f}", "%Vn"))

    if exp_type == "pulso_carga":
        _n_pk_drop = res.get("_speed_drop_pct", None)
        if _n_pk_drop is not None:
            out.append(("Speed Drop", f"{float(_n_pk_drop):.{d}f}", "%"))

    if exp_type in ("shutdown", "plugging", "dc_inject"):
        _n_arr = np.asarray(res.get("n", []), dtype=float)
        _t_arr = np.asarray(res.get("t", []), dtype=float)
        _below = np.where(np.abs(_n_arr) < 1.0)[0]
        if len(_below) > 0:
            _t_stop = float(_t_arr[int(_below[0])])
            out.append(("Stop Time", f"{_t_stop:.{d}f}", "s"))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# REFERENCE PANEL
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_overview(
    res: dict,
    mp: MachineParams,
    exp_type: str,
    exp_config: dict | None,
    decimals: int,
    t_events: list,
    energy_tariff: float,
    insights: list,
    n_critico: int,
    n_alerta: int,
    em: dict,
) -> None:
    d = decimals

    def fmt_pot(val: float, decimals: int) -> tuple[str, str]:
        if abs(val) >= 1000:
            return "kW", f"{val/1000:.{decimals}f}"
        return "W", f"{val:.{decimals}f}"

    # ── BLOCK 1: Health Panel ─────────────────────────────────────────
    _eta_val   = res.get("eta", 0.0)
    _s_pct     = res.get("s", 0.0) * 100.0
    _n_ss_disp = res["n_ss"]

    if n_critico > 0:
        _saude_cor, _saude_ico, _saude_txt = "#dc3545", "🔴", "Anomaly Detected"
        _saude_fn = st.error
    elif n_alerta > 0:
        _saude_cor, _saude_ico, _saude_txt = "#fd7e14", "🟡", "Attention"
        _saude_fn = st.warning
    else:
        _saude_cor, _saude_ico, _saude_txt = "#198754", "🟢", "Normal Operation"
        _saude_fn = st.success

    _diag_suffix = ""
    if n_critico or n_alerta:
        _diag_suffix = f" — {n_critico} critical, {n_alerta} warning(s). See **Diagnostics & Faults** tab."

    if exp_type != "shutdown":
        _saude_fn(
            f"{_saude_ico} **{_saude_txt}** — "
            f"Slip: **{_s_pct:.2f}%** | "
            f"Efficiency: **{_eta_val:.1f}%** | "
            f"Speed: **{_n_ss_disp:.0f} RPM**"
            + _diag_suffix
        )
    else:
        _saude_fn(f"{_saude_ico} **{_saude_txt}**" + _diag_suffix)

    st.write("")

    # ── BLOCK 2: Operating Quantities ─────────────────────────────────
    if exp_type != "shutdown":
        st.markdown('<p class="slabel">Operating Quantities</p>', unsafe_allow_html=True)

        n_ss    = res["n_ss"]
        Te_ss   = res["Te_ss"]
        wr_ss   = res["wr_ss"]
        ias_rms = res["ias_rms"]
        s_val   = res.get("s", 0.0)
        gerador = s_val < 0

        u_in,  v_in  = fmt_pot(res.get("P_in",  0.0), d)
        u0,    v0    = fmt_pot(abs(res.get("P_gap",  0.0)), d)
        u1,    v1    = fmt_pot(abs(res.get("P_mec",  0.0)), d)
        u2,    v2    = fmt_pot(res.get("P_cu_r", 0.0), d)
        u_out, v_out = fmt_pot(res.get("P_out", 0.0), d)

        lbl_in  = f"Turbine Mech. Power ({u_in})"    if gerador else f"Input Power ({u_in})"
        lbl_gap = f"Generated Air-Gap Power ({u0})"  if gerador else f"Air-Gap Power ({u0})"
        lbl_mec = f"Mechanical Input Power ({u1})"   if gerador else f"Mechanical Power ({u1})"

        _op1 = st.columns(3)
        _op1[0].metric("Speed (RPM)",                   f"{n_ss:.{d}f}")
        _op1[1].metric("Steady-State Torque $T_e$ (N·m)", f"{Te_ss:.{d}f}")
        _op1[2].metric("RMS Current $i_{as}$ (A)",     f"{ias_rms:.{d}f}")

        _op2 = st.columns(3)
        if gerador:
            _op2[0].metric(f"Grid Generated Power ({u_out})", v_out)
        else:
            _op2[0].metric(lbl_mec, v1)
        _op2[1].metric("Efficiency (%)",   f"{res.get('eta', 0.0):.{d}f}")
        _op2[2].metric("Slip (%)",         f"{s_val * 100:.{d}f}")

        _op3 = st.columns(3)
        _op3[0].metric(lbl_in,                  f"{v_in}")
        _op3[1].metric(lbl_gap,                 f"{v0}")
        _op3[2].metric(f"Rotor Losses ({u2})",  v2)

    # ── BLOCK 3: Starting Transient ───────────────────────────────────
    destaques = _kpis_destaque(res, exp_type, mp, d, t_events)
    _prot_items_exist = exp_type in ("dol", "yd", "comp", "soft", "voltage_sag")
    if destaques or _prot_items_exist:
        st.write("")
        with st.expander("Starting Transient and Protection", expanded=False):
            if destaques:
                st.markdown('<p class="slabel">Starting Quantities</p>', unsafe_allow_html=True)
                _MAX_COLS = 4
                for i in range(0, len(destaques), _MAX_COLS):
                    chunk = destaques[i:i + _MAX_COLS]
                    cols = st.columns(_MAX_COLS)
                    for col, (lbl, val, unit) in zip(cols, chunk):
                        col.metric(f"{lbl} ({unit})", val)
                st.write("")

            if _prot_items_exist:
                try:
                    _n_arr    = np.asarray(res["n"], dtype=float)
                    _t_arr    = np.asarray(res["t"], dtype=float)
                    _n_sync   = mp.f / mp.p * 60.0
                    _thresh_n = STARTING_SPEED_THRESHOLD * _n_sync
                    _above    = np.where(_n_arr >= _thresh_n)[0]
                    if len(_above) > 0:
                        _t_accel = float(_t_arr[int(_above[0])])
                        if _t_accel < RELAY_CLASS_10_S:
                            _trip_class, _trip_fn = 10, st.success
                            _trip_msg = f"Class 10 — starting in **{_t_accel:.2f} s** (< {RELAY_CLASS_10_S:.0f} s)"
                        elif _t_accel < RELAY_CLASS_20_S:
                            _trip_class, _trip_fn = 20, st.warning
                            _trip_msg = f"Class 20 — starting in **{_t_accel:.2f} s** ({RELAY_CLASS_10_S:.0f}–{RELAY_CLASS_20_S:.0f} s)"
                        else:
                            _trip_class, _trip_fn = 30, st.error
                            _trip_msg = f"Class 30 — starting in **{_t_accel:.2f} s** (> {RELAY_CLASS_20_S:.0f} s)"

                        st.markdown('<p class="slabel">Protection Recommendations</p>', unsafe_allow_html=True)
                        _trip_fn(
                            f"**Class {_trip_class} Overload Relay** — "
                            f"{_trip_msg}. (IEC 60947-4-1 / NEMA ICS 2)"
                        )

                        _In      = getattr(mp, "In", None)
                        _Vn      = getattr(mp, "Vn", None)
                        _ias_pk  = float(np.max(np.abs(res["ias"]))) if "ias" in res else None

                        if _In is not None and _ias_pk is not None:
                            _icp_ratio = _ias_pk / _In if _In > 0 else 0.0
                            _mpcb_lo  = MPCB_THERMAL_LO_RATIO * _In
                            _mpcb_hi  = MPCB_THERMAL_HI_RATIO * _In
                            _mpcb_icu = _ias_pk * MPCB_ICU_MULTIPLIER
                            _mpcb_fn  = st.success if _icp_ratio <= MPCB_RATIO_CLASS_8 else (st.warning if _icp_ratio <= MPCB_RATIO_CLASS_12 else st.error)
                            _mpcb_fn(
                                f"**Motor Protection Circuit Breaker (MPCB)** — thermal setting: "
                                f"{_mpcb_lo:.1f}–{_mpcb_hi:.1f} A; "
                                f"breaking capacity ≥ **{_mpcb_icu:.0f} A** "
                                f"(simulated peak × 1.25). (IEC 60947-2)"
                            )

                        if _In is not None:
                            _fus_lo = FUSE_MULTIPLIER_MIN * _In
                            _fus_hi = FUSE_MULTIPLIER_MAX * _In
                            st.info(
                                f"**Protection Fuse (gG/aM)** — "
                                f"recommended rated current: **{_fus_lo:.0f}–{_fus_hi:.0f} A** "
                                f"({FUSE_MULTIPLIER_MIN:.1f}–{FUSE_MULTIPLIER_MAX:.1f} × In = {_In:.1f} A). "
                                f"Class aM if coordinated with MPCB. (IEC 60269-1)"
                            )
                            _cont_rup = CONTACTOR_RUPTURE_MULT * _In
                            st.info(
                                f"**AC-3 Contactor** — utilization current: ≥ **{_In:.1f} A**; "
                                f"breaking capacity: ≥ **{_cont_rup:.0f} A** ({CONTACTOR_RUPTURE_MULT:.0f} × In). "
                                f"(IEC 60947-4-1, cat. AC-3)"
                            )

                        if _Vn is not None:
                            _vn_ll = _Vn
                            if _vn_ll <= SPD_VN_LV:
                                _uc, _up_max = SPD_UC_LV, SPD_UP_LV
                            elif _vn_ll <= SPD_VN_MV:
                                _uc, _up_max = SPD_UC_MV, SPD_UP_MV
                            else:
                                _uc, _up_max = int(_vn_ll * SPD_UC_HV_MULTIPLIER), SPD_UP_HV
                            st.info(
                                f"**Class II SPD (Surge)** — Uc ≥ **{_uc} V**; "
                                f"protection level Up ≤ **{_up_max} V**. "
                                f"Install in control panel, between phase and earth. (IEC 61643-11)"
                            )

                        _T_max = None
                        for _k in ("T_s", "Ts", "T_stator", "theta_s", "theta_stator"):
                            if _k in res:
                                _T_max = float(np.max(res[_k]))
                                break
                        if _T_max is not None:
                            if _T_max < INSULATION_CLASS_F_C:
                                _prot_fn, _prot_iso = st.success, f"F ({INSULATION_CLASS_F_C} °C)"
                            elif _T_max < INSULATION_CLASS_H_C:
                                _prot_fn, _prot_iso = st.warning, f"H ({INSULATION_CLASS_H_C} °C)"
                            else:
                                _prot_fn, _prot_iso = st.error, f"C (> {INSULATION_CLASS_C_C} °C) — review insulation"
                            _prot_fn(
                                f"**PTC Thermistor / RTD** — maximum simulated temperature: "
                                f"**{_T_max:.1f} °C** → recommended insulation class: **{_prot_iso}**. "
                                f"(IEC 60085 / IEC 60034-1)"
                            )

                except Exception:
                    pass

    # ── BLOCK 4: Economic Summary ──────────────────────────────────────
    if em:
        st.write("")
        st.markdown('<p class="slabel">Economic Summary</p>', unsafe_allow_html=True)
        _re1, _re2, _re3 = st.columns(3)
        _re1.metric("Steady-State Efficiency", f"{em['eta_ss']:.2f} %")
        _re2.metric("Input Power (steady state)", f"{em['P_in_ss_kw']:.3f} kW")
        _re3.metric("Annual Operating Cost", f"$ {em['custo_ano_brl']:,.2f}",
                    help=(
                        f"Estimated as: P_in_steady × 8,760 h/year × tariff.\n"
                        f"Assumptions: continuous operation 24 h/day, 365 days/year, "
                        f"at steady-state power.\n"
                        f"Current tariff: $ {energy_tariff:.4f}/kWh "
                        f"(configurable in Advanced Parameters → Economic Analysis)."
                    ))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — DYNAMIC ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@st.fragment
def _render_tab_dynamic(
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

    _is_pulso    = (exp_type == "pulso_carga")
    _t_pulso_on  = float((exp_config or {}).get("t_carga",    0.0))
    _t_pulso_off = float((exp_config or {}).get("t_retirada", 0.0))
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
        t_pulso_on  = _t_pulso_on,
        t_pulso_off = _t_pulso_off,
        tl_arr      = tl_arr,
    )
    t_window = compute_t_window(zoom_mode, _zoom_ctx)

    def _apply_zoom(fig, keys):
        return apply_zoom(fig, keys, t_window, res, tl_arr)

    def _apply_zoom_overlay(fig, keys):
        return apply_zoom_overlay(fig, keys, t_window, res, tl_arr)

    # ── contextual notes per variable ──────────────────────────────────
    _cfg = exp_config or {}
    _note_ctx = MITNoteCtx(
        exp_type  = exp_type,
        exp_config= _cfg,
        bb_sev    = float(res.get("_broken_bar_severity", 0.0)),
        s_val     = float(res.get("s", 0.0)),
        deseq_on  = any(_cfg.get(k, 0) for k in
                        ("deseq_a", "deseq_b", "deseq_c", "falta_fase_a", "falta_fase_b", "falta_fase_c")),
        is_yd     = (exp_type == "yd"),
        is_gen    = (exp_type == "gerador"),
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — DIAGNOSTICS & FAULTS
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_diagnosis(
    res: dict,
    mp: MachineParams,
    var_keys: list[str],
    var_labels: list[str],
    insights: list,
    n_critico: int,
    n_alerta: int,
    em: dict,
    dark: bool,
    res_hash: int,
) -> None:
    # ── BLOCK 1: Diagnostics banner ────────────────────────────────────
    if n_critico > 0:
        _diag_banner_fn  = st.error
        _diag_banner_ico = "🔴"
    elif n_alerta > 0:
        _diag_banner_fn  = st.warning
        _diag_banner_ico = "🟡"
    else:
        _diag_banner_fn  = st.success
        _diag_banner_ico = "🟢"

    _total_insights = len(insights)
    _n_info = _total_insights - n_critico - n_alerta
    _diag_banner_fn(
        f"{_diag_banner_ico} **{_total_insights} insight(s)** — "
        f"{n_critico} critical · {n_alerta} warning(s) · {_n_info} informational"
    )

    # ── BLOCK 2: Insights ─────────────────────────────────────────────
    if not insights:
        st.info(
            "No insights available for this experiment type "
            "or steady-state data was not detected."
        )
    else:
        _ICONS    = {"info": "ℹ️", "warning": "⚠️", "error": "🔴"}
        _level_fn = {"info": st.info, "warning": st.warning, "error": st.error}
        for _ins in insights:
            _fn   = _level_fn.get(_ins.level, st.info)
            _icon = _ICONS.get(_ins.level, "")
            _fn(f"**{_icon} {_ins.title}**\n\n{_ins.body}")

    # ── BLOCK 3: Power Quality ─────────────────────────────────────────
    if em:
        _thd = em.get("thd_pct", 0.0)
        _fp  = em.get("fp", 0.0)
        if _thd > 0 or _fp > 0:
            with st.expander("Power Quality", expanded=False):
                _qe1, _qe2 = st.columns(2)
                _qe1.metric("Power Factor (PF)", f"{_fp:.3f}")
                _qe2.metric("Current THD $i_{{as}}$", f"{_thd:.2f} %")

                _sat_active = float(res.get("_broken_bar_severity", 0.0)) > 0 or getattr(mp, "sat_enable", False)
                if _thd > THD_LIMIT_IEEE519:
                    if _sat_active:
                        st.warning(
                            f"High THD ({_thd:.1f}%) — likely contribution from **magnetic saturation**. "
                            f"Consider passive or active filter."
                        )
                    else:
                        st.warning(
                            f"Current THD above 5% ({_thd:.1f}%). "
                            f"Check for supply voltage distortion or non-linear load."
                        )
                else:
                    st.info(f"THD within the IEEE 519 recommended limit (< {THD_LIMIT_IEEE519:.0f}%).")

                if _fp < POWER_FACTOR_MIN:
                    _Te_ss  = float(res.get("Te_ss",  res.get("Te",  [0])[-1]))
                    _T_nom  = float(getattr(mp, "T_nom", 0) or 0)
                    _fator_carga = (_Te_ss / _T_nom) if _T_nom > 0 else None
                    if _fator_carga is not None and _fator_carga < 0.5:
                        _causa = (
                            f"**Probable cause: motor operating underloaded** "
                            f"(shaft torque ≈ {_Te_ss:.1f} N·m = {_fator_carga*100:.0f}% of rated). "
                            f"Magnetizing current $I_m = E_1/X_m$ remains practically constant "
                            f"regardless of load — with low torque, active power $P$ is small "
                            f"while reactive power $Q$ (dominated by $I_m$) remains high, "
                            f"resulting in low PF = P/√(P²+Q²). "
                            f"Motor oversized for the applied load."
                        )
                    else:
                        _causa = (
                            f"Magnetizing current ($I_m = E_1/X_m$) consumes reactive power "
                            f"regardless of load, raising $Q$ relative to $P$."
                        )
                    st.warning(
                        f"**Low Power Factor** ({_fp:.3f} < 0.85).  \n"
                        f"{_causa}  \n"
                        f"Correction: parallel capacitor bank for reactive power compensation."
                    )
                st.caption(
                    "THD calculated via FFT of $i_{{as}}$ in the steady-state window. "
                    "PF = P_in / S_apparent, where S = 3 × Va_rms × Ias_rms."
                )

    # ── BLOCK 4: Current Signature / FFT ──────────────────────────────
    _ac_keys = [k for k in var_keys if k in ("ias", "ibs", "ics", "iar", "ibr", "icr")]
    with st.expander("Current Signature Analysis (FFT / MCSA)", expanded=False):
        if _ac_keys:
            _fft_var = st.selectbox(
                "Variable for spectral analysis",
                options=_ac_keys,
                format_func=lambda k: next((l for kk, l in zip(var_keys, var_labels) if kk == k), k),
                key="fft_var_select_results",
            )
            _fft_lbl = _strip_latex(
                next((l for kk, l in zip(var_keys, var_labels) if kk == _fft_var), _fft_var)
            )
            _dp = st.session_state.get("plot_dark_toggle", dark)
            fig_fft = _cached_fig_fft(res, _dp, _fft_var, _fft_lbl, _cache_key=res_hash)

            _alpha = float(res.get("_broken_bar_severity", 0.0))
            if _alpha > 0:
                _s_val  = float(res.get("s", 0.0))
                _f_fund = mp.f
                _sb_lo  = _f_fund * (1.0 - 2.0 * abs(_s_val))
                _sb_hi  = _f_fund * (1.0 + 2.0 * abs(_s_val))
                for _freq, _lbl_sb in [(_sb_lo, f"(1−2s)f={_sb_lo:.1f}Hz"), (_sb_hi, f"(1+2s)f={_sb_hi:.1f}Hz")]:
                    fig_fft.add_vline(
                        x=_freq, line_dash="dash", line_color="#f59e0b", line_width=1.5,
                        annotation_text=_lbl_sb,
                        annotation_font_color="#f59e0b",
                        annotation_font_size=9,
                    )
                st.caption(
                    f"Broken bar active (alpha={_alpha:.2f}) — "
                    f"sideband components at **(1±2s)f**: "
                    f"{_sb_lo:.1f} Hz and {_sb_hi:.1f} Hz (s={_s_val*100:.2f}%)."
                )
            else:
                st.caption("Red dashed lines: odd harmonics (1st, 3rd, 5th, 7th, 9th).")
            st.plotly_chart(fig_fft, width="stretch", config=_PLOT_CFG, key="ems-fft-results")
        else:
            st.info("Select phase currents (ias, ibs, ics...) in the configuration to enable spectral analysis.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ASSET MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_assets(
    em: dict,
    exp_type: str,
    energy_tariff: float,
) -> None:
    if em:
        st.markdown('<p class="slabel">Economic Analysis</p>', unsafe_allow_html=True)

        _ec1, _ec2, _ec3 = st.columns(3)
        _ec1.metric("Steady-State Efficiency",   f"{em['eta_ss']:.2f} %")
        _ec2.metric("Annual Operating Cost",     f"$ {em['custo_ano_brl']:,.2f}",
                    help=(
                        f"Estimated as: P_in_steady × 8,760 h/year × tariff.\n"
                        f"Assumptions: continuous operation 24 h/day, 365 days/year, "
                        f"at steady-state power.\n"
                        f"Current tariff: $ {energy_tariff:.4f}/kWh."
                    ))
        _ec3.metric("Input Power (steady state)", f"{em['P_in_ss_kw']:.3f} kW")

        with st.expander("Consumption Details", expanded=False):
            _ed1, _ed2, _ed3 = st.columns(3)
            _ed1.metric("Energy in Experiment",     f"{em['E_total_kwh']:.5f} kWh")
            _ed2.metric("Experiment Cost",          f"$ {em['custo_exp_brl']:.4f}")
            _ed3.metric("Projected Annual Energy",
                        f"{em['P_in_ss_kw'] * em['horas_op_ano']:,.1f} kWh/year",
                        help=(
                            f"Electrical energy the motor would consume in one year of "
                            f"continuous operation at steady-state power "
                            f"({em['P_in_ss_kw']:.3f} kW × 8,760 h/year)."
                        ))
            st.caption(
                f"Annual projection based on continuous operation (8,760 h/year) at tariff "
                f"$ {energy_tariff:.2f}/kWh."
            )
    else:
        st.info("Economic analysis not available for the shutdown experiment.")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT PANEL
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

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

    dark_plot = st.session_state.get("plot_dark_toggle", dark)

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
        _render_tab_overview(
            res=res, mp=mp, exp_type=exp_type, exp_config=exp_config,
            decimals=decimals, t_events=t_events, energy_tariff=energy_tariff,
            insights=_insights, n_critico=_n_critico, n_alerta=_n_alerta, em=_em,
        )

    with tab_dinamica:
        if not var_keys:
            st.info("No variable selected. Return to configuration and choose variables to plot.")
        else:
            _render_tab_dynamic(
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
        _render_tab_diagnosis(
            res=res, mp=mp, var_keys=var_keys, var_labels=var_labels,
            insights=_insights, n_critico=_n_critico, n_alerta=_n_alerta,
            em=_em, dark=dark, res_hash=_res_hash,
        )

    with tab_ativos:
        _render_tab_assets(em=_em, exp_type=exp_type, energy_tariff=energy_tariff)

    _render_export_panel(
        res=res, mp=mp, exp_label=exp_label, exp_type=exp_type,
        exp_config=exp_config,
        var_keys=var_keys, var_labels=var_labels, t_events=t_events,
        ref_list=ref_list, energy_tariff=energy_tariff,
    )
