# -*- coding: utf-8 -*-
"""
sim_results.py
==============
Renders the four induction-machine result sub-tabs: Overview (KPIs), Dynamic Analysis (waveforms), Diagnostics, and Asset Management.

Responsibilities:
  - Render KPI cards and health panel in the Overview sub-tab.
  - Build and cache Plotly waveform charts for the Dynamic Analysis sub-tab.
  - Display automated diagnostics and fault signatures in the Diagnostics sub-tab.
  - Generate and provide download buttons for academic and industrial PDF reports.

Relationships:
  Imported by : IWS_UI
  Imports     : core.IWS_PY, core.energy_analysis, core.harmonica_analysis,
                core.sim_diagnostics, viz.plotly_charts, viz.pdf_academico,
                viz.pdf_industrial, utils.text_utils, ui.theme

Extending:
  - To add a new result sub-tab, create a render_<tab>() function and append it to the st.tabs call.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.IWS_PY import MachineParams
from core.energy_analysis import compute_energy_metrics
from viz.plotly_charts import (
    build_fig_stacked, build_fig_sidebyside, build_fig_overlay, build_fig_torque_speed,
)
from viz.pdf_academico import generate_academico
from viz.pdf_industrial import generate_industrial
from core.harmonica_analysis import build_fig_fft
from core.sim_diagnostics import generate_insights
from utils.text_utils import _strip_latex
from ui.theme import REF_COLORS, REF_DASHES


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


_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "simulation_chart",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
}




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
        _thresh = 0.95 * _n_sync
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
                    _thresh_n = 0.95 * _n_sync
                    _above    = np.where(_n_arr >= _thresh_n)[0]
                    if len(_above) > 0:
                        _t_accel = float(_t_arr[int(_above[0])])
                        if _t_accel < 10.0:
                            _trip_class, _trip_fn = 10, st.success
                            _trip_msg = f"Class 10 — starting in **{_t_accel:.2f} s** (< 10 s)"
                        elif _t_accel < 20.0:
                            _trip_class, _trip_fn = 20, st.warning
                            _trip_msg = f"Class 20 — starting in **{_t_accel:.2f} s** (10–20 s)"
                        else:
                            _trip_class, _trip_fn = 30, st.error
                            _trip_msg = f"Class 30 — starting in **{_t_accel:.2f} s** (> 20 s)"

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
                            _mpcb_lo  = 0.80 * _In
                            _mpcb_hi  = 1.00 * _In
                            _mpcb_icu = _ias_pk * 1.25
                            _mpcb_fn  = st.success if _icp_ratio <= 8 else (st.warning if _icp_ratio <= 12 else st.error)
                            _mpcb_fn(
                                f"**Motor Protection Circuit Breaker (MPCB)** — thermal setting: "
                                f"{_mpcb_lo:.1f}–{_mpcb_hi:.1f} A; "
                                f"breaking capacity ≥ **{_mpcb_icu:.0f} A** "
                                f"(simulated peak × 1.25). (IEC 60947-2)"
                            )

                        if _In is not None:
                            _fus_lo = 2.0 * _In
                            _fus_hi = 2.5 * _In
                            st.info(
                                f"**Protection Fuse (gG/aM)** — "
                                f"recommended rated current: **{_fus_lo:.0f}–{_fus_hi:.0f} A** "
                                f"(2.0–2.5 × In = {_In:.1f} A). "
                                f"Class aM if coordinated with MPCB. (IEC 60269-1)"
                            )
                            _cont_rup = 6.0 * _In
                            st.info(
                                f"**AC-3 Contactor** — utilization current: ≥ **{_In:.1f} A**; "
                                f"breaking capacity: ≥ **{_cont_rup:.0f} A** (6 × In). "
                                f"(IEC 60947-4-1, cat. AC-3)"
                            )

                        if _Vn is not None:
                            _vn_ll = _Vn
                            if _vn_ll <= 230:
                                _uc, _up_max = 275, 1500
                            elif _vn_ll <= 400:
                                _uc, _up_max = 420, 2500
                            else:
                                _uc, _up_max = int(_vn_ll * 1.1), 4000
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
                            _class_F, _class_H = 155, 180
                            if _T_max < _class_F:
                                _prot_fn, _prot_iso = st.success, "F (155 °C)"
                            elif _T_max < _class_H:
                                _prot_fn, _prot_iso = st.warning, "H (180 °C)"
                            else:
                                _prot_fn, _prot_iso = st.error, "C (> 180 °C) — review insulation"
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
    t_window  = None
    if zoom_mode == "Steady State":
        t_window = (max(0.0, t_ss - max(0.05 * tmax_data, 0.02)), tmax_data)
    elif zoom_mode == "Starting":
        _cfg  = exp_config or {}
        _pad  = 0.1
        if exp_type == "dol":
            _ws_mec = 2.0 * np.pi * mp.f / (mp.p / 2.0)
            _wr     = np.asarray(res["wr"], dtype=float)
            _above  = np.where(_wr >= 0.95 * _ws_mec)[0]
            _t_acc  = float(res["t"][int(_above[0])]) if len(_above) > 0 else t_ss
            _tend   = _t_acc + _pad
        elif exp_type in ("yd", "comp"):
            _tc   = float(_cfg.get("t_carga", 0.0))
            _t2   = float(_cfg.get("t_2", 0.0))
            _tend = max(_tc, _t2) + _pad
        elif exp_type == "soft":
            _tp   = float(_cfg.get("t_pico", 0.0))
            _tc   = float(_cfg.get("t_carga", 0.0))
            _tend = max(_tp, _tc) + _pad
        elif exp_type == "voltage_sag":
            _ts   = float(_cfg.get("t_start_sag", 0.0))
            _dur  = float(_cfg.get("t_duration_sag", 0.1))
            _tend = _ts + _dur + _pad
        else:
            _tend = t_ss + _pad
        t_window = (0.0, min(_tend, tmax_data))
    elif zoom_mode == "Load Pulse":
        _dur     = max(_t_pulso_off - _t_pulso_on, 0.1)
        _pad     = max(0.2 * _dur, 0.1)
        t_window = (max(0.0, _t_pulso_on - _pad), min(tmax_data, _t_pulso_off + _pad))

    def _y_range(keys):
        if t_window is None:
            return {}
        t_arr = np.asarray(res["t"], dtype=float)
        mask  = (t_arr >= t_window[0]) & (t_arr <= t_window[1])
        ranges = {}
        for key in keys:
            if key not in res:
                continue
            vals = np.asarray(res[key], dtype=float)[mask]
            if tl_arr is not None and key == "Te":
                vals = np.concatenate([vals, np.asarray(tl_arr, dtype=float)[mask]])
            vals = vals[np.isfinite(vals)]
            if len(vals) == 0:
                continue
            ymin, ymax = float(vals.min()), float(vals.max())
            ymid     = (ymin + ymax) / 2.0
            min_span = max(abs(ymid) * 0.01, 0.1)
            if (ymax - ymin) < min_span:
                ymin, ymax = ymid - min_span / 2, ymid + min_span / 2
            pad = (ymax - ymin) * 0.12
            ranges[key] = (ymin - pad, ymax + pad)
        return ranges

    def _apply_zoom(fig, keys):
        if t_window is None:
            return fig
        x0, x1 = t_window
        fig.update_xaxes(range=[x0, x1], autorange=False)
        yr = _y_range(keys)
        if yr:
            ylo, yhi = next(iter(yr.values()))
            fig.update_layout(yaxis=dict(range=[ylo, yhi], autorange=False))
        return fig

    def _apply_zoom_overlay(fig, keys):
        if t_window is None:
            return fig
        x0, x1 = t_window
        fig.update_xaxes(range=[x0, x1], autorange=False)
        yr         = _y_range(keys)
        right_units = {"n", "wr"}
        left_keys  = [k for k in keys if k not in right_units]
        right_keys = [k for k in keys if k in right_units]
        if left_keys and any(k in yr for k in left_keys):
            all_v = np.concatenate([np.array(yr[k]) for k in left_keys if k in yr])
            fig.update_layout(yaxis=dict(range=[float(all_v.min()), float(all_v.max())], autorange=False))
        if right_keys and any(k in yr for k in right_keys):
            all_v = np.concatenate([np.array(yr[k]) for k in right_keys if k in yr])
            fig.update_layout(yaxis2=dict(range=[float(all_v.min()), float(all_v.max())], autorange=False))
        return fig

    # ── contextual notes per variable ──────────────────────────────────
    _bb_sev   = float(res.get("_broken_bar_severity", 0.0))
    _s_val    = float(res.get("s", 0.0))
    _deseq_on = any((exp_config or {}).get(k, 0) for k in
                    ("deseq_a", "deseq_b", "deseq_c", "falta_fase_a", "falta_fase_b", "falta_fase_c"))
    _is_yd    = (exp_type == "yd")
    _is_gen   = (exp_type == "gerador")
    _is_sd    = (exp_type == "shutdown")
    _is_soft  = (exp_type == "soft")
    _Tl_cfg   = float((exp_config or {}).get("Tl_final", 0.0))
    _Te_max   = float(np.max(res["Te"])) if "Te" in res else 0.0

    def _nota_apos(key: str) -> None:
        """Emits the appropriate contextual note for variable 'key', if any."""
        _cfg = exp_config or {}
        if key == "Te":
            if _bb_sev > 0:
                _f_osc = 2.0 * abs(_s_val) * mp.f
                st.caption(
                    f"**Broken bar (α={_bb_sev:.2f})** — $T_e$ oscillates at {_f_osc:.1f} Hz "
                    f"($2sf$). Load torque $T_L$ remains essentially constant: "
                    f"inertia $J$ damps speed oscillations, making $\\Delta T_L \\ll \\Delta T_e$. "
                    f"The spectral signature appears in current as sidebands at $(1\\pm2s)f_e$ Hz — "
                    f"see the **Diagnostics & Faults** tab."
                )
            elif _deseq_on:
                st.caption(
                    "**Voltage unbalance / Phase fault** — the negative-sequence component "
                    "establishes a rotating field opposing $\\omega_s$, with effective slip "
                    "$s^- = 2 - s^+$, generating pulsating braking torque at frequency $2f$ and reducing "
                    "mean $T_e$ relative to balanced operation."
                )
            elif _is_yd:
                st.caption(
                    "**Star-Delta Starting (Y-$\\Delta$)** — at switching, the phase voltage jumps "
                    "from $V_n/\\sqrt{3}$ to $V_n$, imposing an excitation step over the residual flux "
                    "in the air gap. The second $T_e$ peak decays with time constant $\\tau_s = L_s/R_s$ to "
                    "the new steady state $T_e = T_L + B\\,\\omega_r$."
                )
            elif exp_type == "autotrafo":
                _k = float(_cfg.get("voltage_ratio", 0.5))
                st.caption(
                    f"**Autotransformer Starting (tap $k$ = {_k:.0%})** — reduced voltage "
                    f"$V_s = k\\,V_n$ attenuates $T_e$ by factor $k^2 = {_k**2:.2f}$, reducing the "
                    f"inrush peak without eliminating transient oscillations. At switching to full "
                    f"voltage a second transient occurs analogous to Y-$\\Delta$ mode."
                )
            elif _is_soft:
                if _Te_max < _Tl_cfg * 1.05 and _Tl_cfg > 0:
                    st.caption(
                        "**Soft-starter** — maximum starting torque is close to load torque. "
                        "If $T_{e,\\max} < T_L$ the motor will not start. Consider increasing the initial "
                        "voltage or reducing load during acceleration."
                    )
                else:
                    st.caption(
                        "**Soft-starter** — the voltage ramp smooths $T_e$ growth, "
                        "eliminating the inrush peak of direct starting. Torque grows "
                        "approximately proportionally to $V_s^2(t)$ until reaching $T_e = T_L + B\\,\\omega_r$ "
                        "in steady state."
                    )
            elif exp_type == "pulso_carga":
                st.caption(
                    "**Load Pulse** — sudden insertion of $T_L$ causes transient drop in "
                    "$\\omega_r$ and increase in slip $s$. Electromagnetic torque $T_e$ "
                    "rises in response, with oscillations damped by time constant $\\tau_m = J/B$, "
                    "until equaling $T_L + B\\,\\omega_r$ at the new operating point."
                )
            elif _is_gen:
                st.caption(
                    "**Generator Mode** — negative $T_e$ indicates the machine absorbs mechanical torque "
                    "and injects active power into the grid (slip $s < 0$, rotor above "
                    "synchronous speed $\\omega_s$). Motor sign convention adopted: "
                    "positive = motor, negative = generator."
                )
            elif _is_sd:
                _tau_r = mp.Lr / mp.Rr if mp.Rr > 0 else 0.0
                st.caption(
                    f"**Shutdown** — after voltage cut, air-gap flux decays with "
                    f"time constant $\\tau_r = L_r/R_r$ = {_tau_r:.3f} s and $T_e$ rapidly drops to zero. "
                    f"The rotor continues spinning by inertia, decelerating under $T_L$ and viscous friction $B$."
                )
            elif exp_type == "voltage_sag":
                _sag = float(_cfg.get("sag_magnitude", 0.5))
                st.caption(
                    f"**Voltage Sag ($V_{{sag}}$ = {_sag:.0%}$V_n$)** — "
                    f"$T_e$ drops proportionally to $V_s^2$, reducing to $\\approx {_sag**2:.0%}$ "
                    f"of rated value during the disturbance. If $T_{{e,\\min}} < T_L$ the motor loses "
                    f"synchronism and may stall ($s \\to 1$)."
                )
            elif exp_type == "dol":
                st.caption(
                    "**Direct-On-Line Starting (DOL)** — at energization with $\\omega_r = 0$ and $s = 1$, "
                    "low circuit impedance imposes inrush current $I_s \\approx 5$–$8\\,I_n$. "
                    "Torque $T_e$ exhibits damped oscillations superimposed on a rising envelope, "
                    "arising from transient fluxes in the $d$-$q$ axes, until stabilizing at "
                    "$T_e = T_L + B\\,\\omega_r$."
                )

        elif key in ("ias", "ibs", "ics"):
            if _bb_sev > 0:
                _f_osc = 2.0 * abs(_s_val) * mp.f
                _f_lo  = (1.0 - 2.0 * abs(_s_val)) * mp.f
                _f_hi  = (1.0 + 2.0 * abs(_s_val)) * mp.f
                st.caption(
                    f"**Broken bar (α={_bb_sev:.2f})** — rotor circuit asymmetry "
                    f"induces amplitude modulation in stator current, generating sidebands "
                    f"at $(1\\pm2s)f_e$ = {_f_lo:.1f} Hz and {_f_hi:.1f} Hz visible in the MCSA spectrum "
                    f"— see the **Diagnostics & Faults** tab."
                )
            elif _deseq_on:
                st.caption(
                    "**Voltage unbalance / Phase fault** — asymmetric phase currents "
                    "indicate negative-sequence component $I_2$ circulating in the stator. "
                    "The phase with lower voltage tends to carry higher current, accelerating "
                    "insulation aging."
                )
            elif _is_yd:
                st.caption(
                    "**Star-Delta Starting (Y-$\\Delta$)** — in star mode, $I_s$ is "
                    "reduced to $1/3$ of the equivalent DOL value. At delta switching "
                    "a second current peak occurs, typically $1{.}5$–$2\\,I_n$, "
                    "decaying with $\\tau_s = L_s/R_s$."
                )
            elif exp_type == "autotrafo":
                _k = float(_cfg.get("voltage_ratio", 0.5))
                st.caption(
                    f"**Autotransformer (tap $k$ = {_k:.0%})** — stator inrush current "
                    f"is reduced by $k^2 = {_k**2:.2f}$ compared to direct starting, since "
                    f"$I_{{s,\\text{{inrush}}}} \\propto V_s = k\\,V_n$."
                )
            elif _is_soft:
                st.caption(
                    "**Soft-starter** — the voltage ramp eliminates the inrush peak; current "
                    "grows gradually from $I_s \\approx 0$ to $I_n$ in steady state, "
                    "reducing electrical and mechanical stress at starting."
                )
            elif exp_type == "dol":
                st.caption(
                    "**Direct-On-Line Starting (DOL)** — with $s = 1$, starting current reaches "
                    "$I_{{s,0}} \\approx V_n / Z_s$, typically $5$–$8\\,I_n$. "
                    "As $\\omega_r$ increases and $s$ decreases, $I_s$ reduces to $I_n$ "
                    "in steady state."
                )
            elif exp_type == "voltage_sag":
                st.caption(
                    "**Voltage Sag** — during the sag, $I_s$ may transiently rise "
                    "if the motor decelerates and slip $s$ increases, "
                    "typical behavior for loads with torque proportional to $\\omega_r^2$."
                )

        elif key in ("iar", "ibr", "icr"):
            if _bb_sev > 0:
                st.caption(
                    f"**Broken bar (α={_bb_sev:.2f})** — asymmetric rotor currents "
                    f"indicate that one or more bars have elevated resistance ($R_{{bar}} \\gg R_r$). "
                    f"Non-uniform distribution generates $T_e$ pulsation and localized heating."
                )
            elif _deseq_on:
                st.caption(
                    "**Voltage unbalance** — the negative-sequence component induces "
                    "rotor current at frequency $(2-s)f_e$, much larger than $sf_e$ of "
                    "balanced operation, increasing rotor Joule losses."
                )

        elif key in ("Va", "Vb", "Vc"):
            if exp_type == "voltage_sag":
                _sag = float(_cfg.get("sag_magnitude", 0.5))
                _t0  = float(_cfg.get("t_start_sag", 0.5))
                _dt  = float(_cfg.get("t_duration_sag", 0.1))
                st.caption(
                    f"**Voltage Sag** — voltage reduced to {_sag:.0%}$V_n$ during "
                    f"$\\Delta t_{{sag}}$ = {_dt:.3f} s (from $t$ = {_t0:.3f} s to "
                    f"$t$ = {_t0+_dt:.3f} s). Abrupt recovery after the sag may generate "
                    f"a re-excitation transient in stator flux."
                )
            elif _deseq_on:
                _falta = any(_cfg.get(k, 0) for k in ("falta_fase_a", "falta_fase_b", "falta_fase_c"))
                if _falta:
                    st.caption(
                        "**Phase fault** — the open-phase voltage drops to zero at the terminals; "
                        "the remaining phases maintain rated amplitude, imposing non-zero "
                        "negative-sequence voltage $V_2$ on the stator."
                    )
                else:
                    st.caption(
                        "**Voltage unbalance** — unequal phase amplitudes indicate "
                        "supply asymmetry. Decomposition into symmetric components "
                        "reveals $V_2/V_1$ proportional to the degree of unbalance."
                    )

        elif key in ("n", "wr"):
            _lbl_v = "$\\omega_r$" if key == "wr" else "$n$"
            _lbl_u = "rad/s" if key == "wr" else "rpm"
            if _is_gen:
                st.caption(
                    f"**Generator Mode** — {_lbl_v} above synchronous speed corresponds to "
                    f"$s < 0$. The machine operates as an induction generator, injecting active power "
                    f"into the grid without independent excitation (requires reactive power from the grid for magnetization)."
                )
            elif _is_sd:
                _ws    = 2.0 * np.pi * mp.f / (mp.p / 2.0)
                _t_cut = float(_cfg.get("t_cutoff", 0.0))
                import math as _math
                if mp.B > 0 and _Tl_cfg > 0:
                    _t_stop = _math.log(1.0 + mp.B * _ws / _Tl_cfg) * mp.J / mp.B
                elif _Tl_cfg > 0:
                    _t_stop = mp.J * _ws / _Tl_cfg
                else:
                    _t_stop = mp.J / mp.B if mp.B > 0 else 0.0
                st.caption(
                    f"**Shutdown** — after $t_{{off}}$ = {_t_cut:.2f} s the voltage is cut and "
                    f"the motor decelerates freely. Estimated stop time: **{_t_stop:.2f} s** "
                    f"($J/B \\cdot \\ln(1 + B\\omega_s/T_L)$)."
                )
            elif exp_type == "voltage_sag":
                st.caption(
                    f"**Voltage Sag** — the drop in $T_e \\propto V_s^2$ during the sag "
                    f"causes transient deceleration of {_lbl_v}. If the slip margin "
                    f"is sufficient, the motor recovers rated speed after voltage restoration; "
                    f"otherwise it stalls ($s \\to 1$)."
                )
            elif exp_type == "pulso_carga":
                st.caption(
                    f"**Load Pulse** — sudden insertion of $T_L$ causes transient drop "
                    f"in {_lbl_v}, increasing $s$ and consequently $T_e$. The system "
                    f"damps and converges to the new equilibrium point with mechanical "
                    f"time constant $\\tau_m \\approx J/B$."
                )
            elif _is_yd:
                st.caption(
                    f"**Star-Delta Starting (Y-$\\Delta$)** — {_lbl_v} grows monotonically "
                    f"during star phase. At switching, the $T_e$ transient causes "
                    f"a visible perturbation before stabilization in steady state."
                )
            elif exp_type == "autotrafo":
                st.caption(
                    f"**Autotransformer** — acceleration under reduced voltage is slower than "
                    f"in DOL (torque proportional to $k^2$). At switching to full voltage, "
                    f"{_lbl_v} exhibits a transient perturbation before reaching steady state."
                )
            elif _is_soft:
                st.caption(
                    f"**Soft-starter** — {_lbl_v} grows smoothly with the progressive increase "
                    f"of $V_s(t)$, without the mechanical shock of direct starting. Acceleration "
                    f"is monotonic, limited by the configured ramp profile."
                )
            elif exp_type == "dol":
                _ws_rpm = 60.0 * mp.f / (mp.p / 2.0)
                st.caption(
                    f"**Direct-On-Line Starting (DOL)** — {_lbl_v} starts from zero and accelerates to "
                    f"$\\approx (1-s_{{nom}})\\,\\omega_s$ ({_ws_rpm*(1-abs(_s_val)):.0f} {_lbl_u}). "
                    f"Acceleration is determined by excess torque $T_e - T_L$ divided "
                    f"by moment of inertia $J$."
                )

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
            P_nom_kw=max(_P_mec_ss / 1000.0, 0.5),
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
                if _thd > 5.0:
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
                    st.info("THD within the IEEE 519 recommended limit (< 5%).")

                if _fp < 0.85:
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
