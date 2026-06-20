# -*- coding: utf-8 -*-
"""
ui.theory
=========
Orchestrator for the induction-machine Theory tab — renders 8 pedagogical sub-tabs.

Responsibilities:
  - Lay out 8 sub-tabs and delegate rendering to ui.theory.tabs.* modules.
  - Expose render_theory_tab as the package public entry point.

Relationships:
  Imported by : ui.theory_view
  Imports     : ui.theory.tabs.*
"""

from __future__ import annotations
import streamlit as st

from ui.theory.tabs.circuits         import render_tab_circuits
from ui.theory.tabs.dynamics          import render_tab_dynamics
from ui.theory.tabs.power          import render_tab_power
from ui.theory.tabs.sensibilidade     import render_tab_sensibilidade
from ui.theory.tabs.dynamics_operation import render_tab_dynamics_operation
from ui.theory.tabs.manual            import render_tab_manual_de_uso
from ui.theory.tabs.estimators       import render_tab_estimators
from ui.theory.tabs.config            import render_tab_config
from ui.theory.tabs.experimentos      import render_tab_experimentos

__all__ = ["render_theory_tab"]


def render_theory_tab() -> None:
    st.markdown(
        "Physical foundations of the three-phase induction machine and simulator "
        "user manual — select a tab to explore the desired topic."
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "1 - Modeling and Circuits",
        "2 - Dynamic Behavior and Torque",
        "3 - Energy Balance",
        "4 - Parameter Sensitivity",
        "5 - Operating Dynamics",
        "6 - User Manual",
        "7 - Parameter Estimators",
        "8 - Settings and Experiments",
    ])

    with tab1:
        st.markdown("## Modeling and Equivalent Circuits")
        render_tab_circuits()

    with tab2:
        st.markdown("## Dynamic Behavior and Torque")
        render_tab_dynamics()

    with tab3:
        st.markdown("## Energy Balance and Power Flow")
        render_tab_power()

    with tab4:
        st.markdown("## Parameter Sensitivity Guide")
        render_tab_sensibilidade()

    with tab5:
        st.markdown("## Operating Dynamics")
        render_tab_dynamics_operation()

    with tab6:
        st.markdown("## Simulator User Manual")
        render_tab_manual_de_uso()

    with tab7:
        st.markdown("## Parameter Estimators")
        render_tab_estimators()

    with tab8:
        st.markdown("## Settings, Alerts, and Experiments")
        st.markdown("### Numerical Settings and Alerts")
        render_tab_config()
        st.divider()
        st.markdown("### Experiment Catalog")
        render_tab_experimentos()
