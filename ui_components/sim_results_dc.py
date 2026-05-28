"""DC machine results visualization.

Exports:
  render_dc_results — KPIs + plots for DC simulation
"""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.dc_machine_model import DCMachineParams, DCMachineODEs


def render_dc_results(
    result: dict[str, Any],
    decimals: int = 3,
    dark: bool = False,
) -> None:
    """Render DC simulation results: KPIs + plots.

    Parameters:
      result: dict from execute_dc_simulation_flow
        Keys: 'config', 'exp_type', 't', 'x', 'y', 'var_keys', 'var_labels', 'params'
      decimals: decimal places for KPI display
      dark: dark mode flag
    """

    config = result.get("config", "sep_motor")
    params = result.get("params")
    t = result.get("t")
    y = result.get("y", {})
    var_keys = result.get("var_keys", [])
    var_labels = result.get("var_labels", [])

    st.divider()

    # ── KPI Row ──
    st.subheader("Valores Finais (Regime Permanente)")

    kpi_cols = st.columns(5)
    final_values = {
        "ia": y.get("ia", [0])[-1],
        "ifd": y.get("ifd", [0])[-1],
        "wm": y.get("wm", [0])[-1],
        "Te": y.get("Te", [0])[-1],
        "Ea": y.get("Ea", [0])[-1],
    }

    kpi_map = [
        ("ia (A)", final_values["ia"], f"{{:.{decimals}f}}"),
        ("ifd (A)", final_values["ifd"], f"{{:.{decimals}f}}"),
        ("ωm (rad/s)", final_values["wm"], f"{{:.{decimals}f}}"),
        ("Te (N·m)", final_values["Te"], f"{{:.{decimals}f}}"),
        ("Ea (V)", final_values["Ea"], f"{{:.{decimals}f}}"),
    ]

    for col, (label, val, fmt) in zip(kpi_cols, kpi_map):
        with col:
            st.metric(label, fmt.format(val))

    # ── Plots ──
    st.subheader("Gráficos")

    # Subset to selected vars
    plot_cols = []
    for key in var_keys:
        if key in y:
            plot_cols.append((key, var_labels[var_keys.index(key)]))

    if not plot_cols:
        st.info("Nenhuma variável selecionada para plotar.")
        return

    # Simple 2-column grid
    n_plots = len(plot_cols)
    for i in range(0, n_plots, 2):
        cols = st.columns(2)

        for j, col in enumerate(cols):
            if i + j < n_plots:
                key, label = plot_cols[i + j]
                with col:
                    _plot_dc_trace(t, y[key], label, dark)

    # ── Summary ──
    st.subheader("Sumário da Simulação")

    summary = f"""
**Configuração:** {config}
**Tempo Final:** {t[-1]:.2f} s
**Pontos:** {len(t)}

| Variável | Inicial | Final |
|---|---|---|
| ia | {y['ia'][0]:.{decimals}f} A | {y['ia'][-1]:.{decimals}f} A |
| ifd | {y['ifd'][0]:.{decimals}f} A | {y['ifd'][-1]:.{decimals}f} A |
| ωm | {y['wm'][0]:.{decimals}f} rad/s | {y['wm'][-1]:.{decimals}f} rad/s |
| Te | {y['Te'][0]:.{decimals}f} N·m | {y['Te'][-1]:.{decimals}f} N·m |
| Ea | {y['Ea'][0]:.{decimals}f} V | {y['Ea'][-1]:.{decimals}f} V |
"""

    st.markdown(summary)


def _plot_dc_trace(
    t: np.ndarray,
    y_data: np.ndarray,
    label: str,
    dark: bool,
) -> None:
    """Plot single trace (internal helper)."""

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=t,
            y=y_data,
            mode="lines",
            name=label,
            line=dict(color="#1f77b4" if not dark else "#80b1ff", width=2),
        )
    )

    fig.update_layout(
        title=label,
        xaxis_title="Tempo (s)",
        yaxis_title=label,
        template="plotly_dark" if dark else "plotly",
        height=350,
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True, config={"responsive": True})
