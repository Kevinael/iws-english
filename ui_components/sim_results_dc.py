"""DC machine results visualization.

Exports:
  render_dc_results — KPIs + plots for DC simulation
"""

from __future__ import annotations

import time
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

    st.divider()
    st.subheader("Exportar Relatório")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📄 Gerar PDF Acadêmico", use_container_width=True):
            try:
                from viz.pdf_dc import generate_dc_academico

                # Extract params
                exp_label = f"{result.get('config_type', 'DC_SIM')}_{int(time.time() % 10000)}"
                mp = {
                    'Rf': result.get('Rf', 'N/A'), 'Lf': result.get('Lf', 'N/A'),
                    'Ra': result.get('Ra', 'N/A'), 'La': result.get('La', 'N/A'),
                    'kb': result.get('kb', 'N/A'), 'J': result.get('J', 'N/A'),
                    'B': result.get('B', 'N/A'),
                }
                var_keys = ['ia', 'ifd', 'wm', 'Te', 'Ea']
                var_labels = ['Corrente de Armadura (A)', 'Corrente de Campo (A)',
                              'Velocidade Mecânica (rad/s)', 'Torque (N·m)', 'Força Contra-Eletromotriz (V)']

                pdf_bytes = generate_dc_academico(
                    exp_label=exp_label,
                    mp=mp,
                    res=result,
                    var_keys=var_keys,
                    var_labels=var_labels,
                    exp_type=result.get('config_type', 'sep_motor_dol'),
                    energy_tariff=0.75,
                    tmax=result['t'][-1] if 't' in result else 1.0,
                    h=1e-3,
                )
                st.download_button(
                    label="⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"{exp_label}_relatorio.pdf",
                    mime="application/pdf",
                )
                st.success("PDF gerado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {str(e)}")


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
