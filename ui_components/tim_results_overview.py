# -*- coding: utf-8 -*-
"""
tim_results_overview.py
=======================
Tab 1 — Overview: KPI cards, health panel, protection summary, economic summary.

Responsibilities:
  - Render health panel with slip/efficiency/speed.
  - Render operating quantity metrics.
  - Render starting transient and protection recommendations.
  - Render economic summary block.

Relationships:
  Imported by : ui_components.tim_results
  Imports     : core.tim.facade, core.constants, numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.tim.facade import MachineParams
from core.constants import (
    STARTING_SPEED_THRESHOLD,
    RELAY_CLASS_10_S,
    RELAY_CLASS_20_S,
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
)


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

    if exp_type == "load_pulse":
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


def _render_kpi_cards(
    res: dict,
    mp: MachineParams,
    exp_type: str,
    n_critico: int,
    n_alerta: int,
    decimals: int,
) -> None:
    d = decimals

    def fmt_pot(val: float, decimals: int) -> tuple[str, str]:
        if abs(val) >= 1000:
            return "kW", f"{val/1000:.{decimals}f}"
        return "W", f"{val:.{decimals}f}"

    # ── Health Panel ──────────────────────────────────────────────────
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

    # ── Operating Quantities ──────────────────────────────────────────
    if exp_type != "shutdown":
        st.markdown('<p class="slabel">Operating Quantities</p>', unsafe_allow_html=True)

        n_ss    = res["n_ss"]
        Te_ss   = res["Te_ss"]
        wr_ss   = res["wr_ss"]
        ias_rms = res["ias_rms"]
        s_val   = res.get("s", 0.0)
        generator = s_val < 0

        u_in,  v_in  = fmt_pot(res.get("P_in",  0.0), d)
        u0,    v0    = fmt_pot(abs(res.get("P_gap",  0.0)), d)
        u1,    v1    = fmt_pot(abs(res.get("P_mec",  0.0)), d)
        u2,    v2    = fmt_pot(res.get("P_cu_r", 0.0), d)
        u_out, v_out = fmt_pot(res.get("P_out", 0.0), d)

        lbl_in  = f"Turbine Mech. Power ({u_in})"    if generator else f"Input Power ({u_in})"
        lbl_gap = f"Generated Air-Gap Power ({u0})"  if generator else f"Air-Gap Power ({u0})"
        lbl_mec = f"Mechanical Input Power ({u1})"   if generator else f"Mechanical Power ({u1})"

        _op1 = st.columns(3)
        _op1[0].metric("Speed (RPM)",                   f"{n_ss:.{d}f}")
        _op1[1].metric("Steady-State Torque $T_e$ (N·m)", f"{Te_ss:.{d}f}")
        _op1[2].metric("RMS Current $i_{as}$ (A)",     f"{ias_rms:.{d}f}")

        _op2 = st.columns(3)
        if generator:
            _op2[0].metric(f"Grid Generated Power ({u_out})", v_out)
        else:
            _op2[0].metric(lbl_mec, v1)
        _op2[1].metric("Efficiency (%)",   f"{res.get('eta', 0.0):.{d}f}")
        _op2[2].metric("Slip (%)",         f"{s_val * 100:.{d}f}")

        _op3 = st.columns(3)
        _op3[0].metric(lbl_in,                  f"{v_in}")
        _op3[1].metric(lbl_gap,                 f"{v0}")
        _op3[2].metric(f"Rotor Losses ({u2})",  v2)


def _render_protection_summary(
    res: dict,
    mp: MachineParams,
    exp_type: str,
    decimals: int,
    t_events: list,
) -> None:
    destaques = _kpis_destaque(res, exp_type, mp, decimals, t_events)
    _prot_items_exist = exp_type in ("dol", "yd", "comp", "soft", "voltage_sag")
    if not destaques and not _prot_items_exist:
        return

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

            except Exception:
                pass


def render_tab_overview(
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
    _render_kpi_cards(res, mp, exp_type, n_critico, n_alerta, decimals)
    _render_protection_summary(res, mp, exp_type, decimals, t_events)

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
