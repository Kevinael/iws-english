# -*- coding: utf-8 -*-
"""
dc_results_overview.py
======================
Tab 1 — Overview: KPI cards, health panel, protection recommendations, economic summary (DC machine).

Responsibilities:
  - Render DCM health panel and operating-quantity metrics.
  - Render starting transient and IEC protection recommendations.
  - Render economic summary block.

Relationships:
  Imported by : ui.dc_results
  Imports     : core.dc.facade, core.constants, data.experiment_modes, numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.dc.facade import DCMachineParams
from data.experiment_modes import DC_EXC_LABELS
from core.constants import (
    DC_OVERCURRENT_WARN_RATIO,
    DC_RELAY_CLASS_10_RATIO,
    DC_RELAY_CLASS_20_RATIO,
    DC_FUSE_MULTIPLIER,
    DC_BREAKER_LO_MULTIPLIER,
    DC_BREAKER_HI_MULTIPLIER,
    HOURS_PER_YEAR,
    W_TO_KW,
)


def render_dc_tab_overview(
    res: dict,
    mp: DCMachineParams,
    exc: str,
    is_gen: bool,
    d: int,
    energy_tariff: float,
) -> None:
    n_ss   = res.get("n_ss",   0.0)
    Te_ss  = res.get("Te_ss",  0.0)
    ia_ss  = res.get("ia_ss",  0.0)
    ifd_ss = res.get("ifd_ss", 0.0)
    Ea_ss  = res.get("Ea_ss",  0.0)
    Vt_ss  = res.get("Vt_ss",  0.0)
    wm_ss  = res.get("wm_ss",  0.0)

    # ── Health Panel ──────────────────────────────────────────────────
    ia_peak = float(np.max(np.abs(res["ia"])))
    Va_nom  = mp.Va if mp else 24.0
    overcurrent = ia_peak > DC_OVERCURRENT_WARN_RATIO * abs(ia_ss) if abs(ia_ss) > 1e-6 else False

    if not res.get("success", True):
        st.error("🔴 **Numerical Failure** — integrator did not converge. Reduce $h$ or review parameters.")
    elif overcurrent:
        st.warning(f"🟡 **Attention** — peak $i_a$ = {ia_peak:.1f} A "
                   f"({ia_peak/max(abs(ia_ss),1e-6):.1f}× steady state). "
                   f"Steady-state speed: **{n_ss:.0f} RPM**")
    else:
        st.success(f"🟢 **Normal Operation** — $n$ = **{n_ss:.0f} RPM** | "
                   f"$T_e$ = **{Te_ss:.{d}f} N·m** | "
                   f"$i_a$ = **{ia_ss:.{d}f} A**")

    st.write("")

    # ── Operating KPIs ────────────────────────────────────────────────
    st.markdown('<p class="slabel">Operating Quantities</p>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Speed (RPM)",            f"{n_ss:.{d}f}")
    k2.metric("$T_e$ (N·m)",            f"{Te_ss:.{d}f}")
    k3.metric("$i_a$ (A)",              f"{ia_ss:.{d}f}")

    k4, k5, k6 = st.columns(3)
    k4.metric("$\\omega_m$ (rad/s)",    f"{wm_ss:.{d}f}")
    k5.metric("$E_a$ (V)",              f"{Ea_ss:.{d}f}")
    k6.metric("$V_t$ (V)",              f"{Vt_ss:.{d}f}")

    if exc not in ("series_motor",):
        k7, k8, _ = st.columns(3)
        k7.metric("$i_{fd}$ (A)",       f"{ifd_ss:.{d}f}")
        k8.metric("Excitation",         DC_EXC_LABELS.get(exc, exc))

    # ── Starting Transient ────────────────────────────────────────────
    with st.expander("Starting Transient", expanded=False):
        tc1, tc2 = st.columns(2)
        tc1.metric("Peak $i_a$ (A)",    f"{float(np.max(np.abs(res['ia']))):.{d}f}")
        tc2.metric("Peak $T_e$ (N·m)",  f"{float(np.max(res['Te'])):.{d}f}")

    # ── Protection Recommendations ────────────────────────────────────
    P_mec_out_nom = abs(Te_ss) * abs(wm_ss)
    if abs(Va_nom) > 1e-6 and P_mec_out_nom > 1e-6:
        _eta_nom = P_mec_out_nom / max(abs(Va_nom) * abs(ia_ss), 1e-9)
        Ia_nom = (P_mec_out_nom / max(abs(Va_nom) * _eta_nom, 1e-9))
    else:
        Ia_nom = abs(ia_ss)

    with st.expander("Protection Recommendations (IEC)", expanded=False):
        _pk_ratio = ia_peak / max(Ia_nom, 1e-6)
        _classe_rele = "Class 10" if _pk_ratio < DC_RELAY_CLASS_10_RATIO else ("Class 20" if _pk_ratio < DC_RELAY_CLASS_20_RATIO else "Class 30")
        _fusivel    = Ia_nom * DC_FUSE_MULTIPLIER
        _disjuntor  = f"{Ia_nom * DC_BREAKER_LO_MULTIPLIER:.1f} – {Ia_nom * DC_BREAKER_HI_MULTIPLIER:.1f}"

        pr1, pr2, pr3 = st.columns(3)
        pr1.metric("Overload Relay",           _classe_rele,
                   help="IEC 60947-4-1 — based on peak-to-rated current ratio")
        pr2.metric("Fuse ≥ (A)",               f"{_fusivel:.1f}",
                   help="IEC 60269-1 — minimum 2× rated current")
        pr3.metric("Motor Circuit Breaker (A)", _disjuntor,
                   help="IEC 60947-2 — range 1.0–1.25× rated current")
        if exc in ("sep_motor", "sep_gen"):
            st.warning(
                "**Open-field protection:** separately excited motors risk overspeed "
                "if the field circuit opens under load — "
                "use an open-field protection relay (IEC 60947-4-1)."
            )

    # ── Economic Summary ──────────────────────────────────────────────
    _P_elec_ss = abs(Va_nom) * abs(ia_ss)
    if energy_tariff > 0 and _P_elec_ss > 1e-3 and not is_gen:
        st.write("")
        _eta_pct   = P_mec_out_nom / max(_P_elec_ss, 1e-9) * 100
        _custo_ano = _P_elec_ss / W_TO_KW * HOURS_PER_YEAR * energy_tariff
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("Efficiency η (%)",         f"{_eta_pct:.1f}")
        ec2.metric("Annual Cost ($)",           f"{_custo_ano:,.2f}",
                   help=f"Tariff: $ {energy_tariff:.4f}/kWh — continuous operation")
        ec3.metric("Input power (kW)",          f"{_P_elec_ss/W_TO_KW:.3f}")
