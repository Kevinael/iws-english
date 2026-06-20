# -*- coding: utf-8 -*-
"""
tim_results_diagnostics.py
==========================
Tab 3 — Diagnostics & Faults: insights banner, power quality, FFT/MCSA.

Responsibilities:
  - Render diagnostics banner with insight counts.
  - Render power quality block (THD, PF).
  - Render Current Signature Analysis (FFT / MCSA) expander.

Relationships:
  Imported by : ui_components.tim_results
  Imports     : core.tim.harmonic_analysis, core.constants, utils.text_utils,
                viz.plotly_config, core.tim.facade, numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.tim.facade import MachineParams
from core.tim import build_fig_fft
from core.constants import THD_LIMIT_IEEE519, POWER_FACTOR_MIN
from utils.text_utils import _strip_latex
from viz.plotly_config import MIT_PLOT_CFG as _PLOT_CFG


@st.cache_data(show_spinner=False)
def _cached_fig_fft(res: dict, dark: bool, key: str, label: str, _cache_key: int = 0) -> go.Figure:
    return build_fig_fft(res, dark, key=key, label=label)


def render_tab_diagnosis(
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
