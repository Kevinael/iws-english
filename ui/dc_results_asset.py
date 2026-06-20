# -*- coding: utf-8 -*-
"""
dc_results_asset.py
===================
Tab 4 — Asset Management: efficiency/loss analysis, Sankey power flow, consumption details (DC machine).

Responsibilities:
  - Render efficiency, Joule/friction losses and utilization-factor metrics.
  - Render the power-flow Sankey diagram (motor mode).
  - Render experiment/annual consumption details.

Relationships:
  Imported by : ui.dc_results
  Imports     : core.dc.facade, core.dc.power, core.constants, viz.plotly_config, numpy, plotly, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.dc.facade import DCMachineParams
from core.dc.power import compute_losses_dc
from core.constants import (
    HOURS_PER_YEAR,
)
from viz.plotly_config import DC_PLOT_CFG as _PLOT_CFG


def render_dc_tab_assets(
    res: dict,
    mp: DCMachineParams,
    exc: str,
    is_gen: bool,
    d: int,
    h: float,
    energy_tariff: float,
) -> None:
    ia_ss  = res.get("ia_ss",  0.0)
    ifd_ss = res.get("ifd_ss", 0.0)
    Te_ss  = res.get("Te_ss",  0.0)
    wm_ss  = res.get("wm_ss",  0.0)

    st.markdown('<p class="slabel">Efficiency and Loss Analysis</p>', unsafe_allow_html=True)

    Va   = mp.Va if mp else 24.0

    losses    = compute_losses_dc(res, mp)
    P_Ra      = losses["P_Ra"]
    P_Rf      = losses["P_Rf"]
    P_mec     = losses["P_mec"]
    P_elec    = losses["P_elec"]
    P_mec_out = losses["P_mec_out"]
    eta       = losses["eta"]

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Efficiency η (%)",         f"{eta:.1f}")
    a2.metric("Joule Loss $R_a$ (W)",     f"{P_Ra:.3f}")
    a3.metric("Joule Loss $R_f$ (W)",     f"{P_Rf:.3f}")
    a4.metric("Friction Loss (W)",        f"{P_mec:.4f}")

    b1, b2 = st.columns(2)
    b1.metric("Electrical Power (W)",     f"{P_elec:.3f}")
    b2.metric("Mechanical Power (W)",     f"{P_mec_out:.3f}")

    Te_nom = mp.Tload if mp else 2.493
    util   = abs(Te_ss) / max(abs(Te_nom), 1e-9) * 100
    st.metric("Utilization Factor (%)",   f"{util:.1f}")

    with st.expander("Sankey Diagram (Power Flow)", expanded=False):
        try:
            if not is_gen and P_elec > 0:
                labels = ["Electrical Power", "Mechanical Power", "Joule Loss Ra", "Joule Loss Rf", "Friction Loss"]
                source = [0, 0, 0, 0]
                target = [1, 2, 3, 4]
                value  = [max(P_mec_out, 0), max(P_Ra, 0), max(P_Rf, 0), max(P_mec, 0)]
                fig_s  = go.Figure(go.Sankey(
                    node=dict(label=labels, pad=15, thickness=20),
                    link=dict(source=source, target=target, value=value),
                ))
                fig_s.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_s, use_container_width=True, config=_PLOT_CFG, key="dc-sankey")
            else:
                st.caption("Sankey available only in motor mode.")
        except Exception:
            st.caption("Sankey unavailable.")

    if energy_tariff > 0 and P_elec > 1e-3 and not is_gen:
        with st.expander("Consumption Details", expanded=False):
            try:
                _t_arr   = res["t"]
                _ia_arr  = res["ia"]
                _P_elec_arr = np.abs(Va) * np.abs(_ia_arr)
                _dt      = float(_t_arr[1] - _t_arr[0]) if len(_t_arr) > 1 else h
                _E_kWh   = float(np.sum(_P_elec_arr) * _dt / 3600)
                _custo_exp  = _E_kWh * energy_tariff
                _tmax_sim   = float(_t_arr[-1])
                _E_anual    = _E_kWh * (HOURS_PER_YEAR * 3600 / max(_tmax_sim, 1e-6))
                _custo_ano  = _E_anual * energy_tariff

                ec1, ec2 = st.columns(2)
                ec1.metric("Energy in experiment (kWh)",     f"{_E_kWh:.6f}")
                ec2.metric("Experiment cost ($)",            f"{_custo_exp:.6f}")
                ec3, ec4 = st.columns(2)
                ec3.metric("Projected annual energy (kWh/yr)", f"{_E_anual:,.1f}")
                ec4.metric("Projected annual cost ($/yr)",     f"{_custo_ano:,.2f}")
                st.caption(
                    f"Tariff: $ {energy_tariff:.4f}/kWh. "
                    f"Projection assumes continuous operation (8,760 h/year) with the same load profile."
                )
            except Exception:
                st.caption("Economic analysis unavailable.")
