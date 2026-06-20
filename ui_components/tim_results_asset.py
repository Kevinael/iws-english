# -*- coding: utf-8 -*-
"""
tim_results_asset.py
====================
Tab 4 — Asset Management: economic analysis, consumption details.

Responsibilities:
  - Render economic analysis metrics (efficiency, annual cost, input power).
  - Render consumption details expander.

Relationships:
  Imported by : ui_components.tim_results
  Imports     : streamlit
"""

from __future__ import annotations

import streamlit as st


def render_tab_assets(
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
