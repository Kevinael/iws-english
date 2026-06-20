# -*- coding: utf-8 -*-
"""
dc_results_shared.py
====================
Shared cache layer and contextual-note helper for the DC machine result sub-tabs.

Responsibilities:
  - Cache Plotly waveform/torque-speed figures (mirrors tim_results cache pattern).
  - Provide the per-variable technical note rendered below dynamic charts.

Relationships:
  Imported by : ui.dc_results, ui.dc_results_dynamics
  Imports     : core.dc.facade, viz.plotly_charts_dc, streamlit, plotly
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from core.dc.facade import DCMachineParams
from viz.plotly_charts_dc import (
    build_fig_stacked_dc,
    build_fig_torque_speed_dc,
)


# ─────────────────────────────────────────────────────────────────────────────
# CACHE LAYER (mirrors tim_results cache pattern)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_fig_stacked_dc(
    res: dict,
    var_keys: tuple,
    var_labels: tuple,
    dark: bool,
    t_events: tuple,
    decimals: int,
    _cache_key: int = 0,
) -> go.Figure:
    return build_fig_stacked_dc(res, list(var_keys), list(var_labels), dark, list(t_events), decimals)


@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed_dc(
    res: dict,
    exc: str,
    dark: bool,
    _cache_key: int = 0,
) -> go.Figure:
    return build_fig_torque_speed_dc(res, exc, dark)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _nota_apos_dc(key: str, mode: str, mp: DCMachineParams) -> None:
    """Displays contextual technical note below the chart, mirroring MIT tim_results."""
    _tau_a = mp.La / max(mp.Ra, 1e-9)
    exc = mp.excitation
    is_series = exc == "series_motor"

    notas: dict[str, str] = {
        "ia": (
            f"Armature current $i_a$ rises rapidly at switch-on ($\\tau_a = L_a/R_a = {_tau_a*1000:.2f}\\,\\text{{ms}}$) "
            f"and is limited as back-EMF $E_a = k_b \\cdot i_{{fd}} \\cdot \\omega_m$ grows. "
            f"Steady state satisfies $i_{{a,ss}} = (V_a - E_{{a,ss}}) / R_a$."
        ),
        "ifd": (
            f"Field current $i_{{fd}}$ determines magnetic flux and thus effective $k_b$. "
            f"Its dynamics are slower than the armature: $\\tau_f = L_f/R_f = {(mp.Lf/max(mp.Rf,1e-9))*1000:.2f}\\,\\text{{ms}}$."
        ) if not is_series else (
            "Series motor: $i_{fd} = i_a$ (field in series with armature). "
            "Torque is proportional to $i_a^2$, resulting in high starting torque."
        ),
        "wm": (
            f"Angular acceleration: $\\dot{{\\omega}}_m = (T_e - T_l - B\\,\\omega_m) / J$. "
            f"With $J = {mp.J:.4f}\\,\\text{{kg·m}}^2$, the typical mechanical time constant is "
            f"$\\tau_m = J \\cdot R_a / k_b^2 \\approx {(mp.J * mp.Ra / max(mp.kb**2, 1e-9)):.3f}\\,\\text{{s}}$."
        ),
        "n": (
            f"Speed in RPM. Steady state: $n_{{ss}} = 60 \\cdot \\omega_{{m,ss}} / (2\\pi)$. "
            f"Field weakening (↓$V_f$ or ↓$I_{{fd}}$) increases steady-state speed."
        ),
        "Te": (
            f"Electromagnetic torque: $T_e = k_b \\cdot i_{{fd}} \\cdot i_a$"
            if not is_series else
            f"Electromagnetic torque: $T_e = k_b \\cdot i_a^2$ (series — high starting torque)."
        ),
        "Ea": (
            f"Back-EMF: $E_a = k_b \\cdot i_{{fd}} \\cdot \\omega_m$. "
            f"In steady state, $E_a \\approx V_a - R_a \\cdot i_{{a,ss}}$."
        ),
        "Vt": (
            f"Terminal voltage. Motor: $V_t = V_a - R_a \\cdot i_a$ (resistive drop). "
            f"Generator: $V_t = E_a - R_a \\cdot i_a$ (below back-EMF)."
        ) if not exc.endswith("_gen") else (
            f"Generator terminal voltage: $V_t = E_a - R_a \\cdot i_a$. "
            f"In steady state, $V_t$ depends on load $R_l$."
        ),
    }

    nota = notas.get(key)
    if nota:
        st.caption(nota)
