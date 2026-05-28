# -*- coding: utf-8 -*-
"""Gráficos Plotly para simulação MCC (Motor de Corrente Contínua).

Exporta:
    build_dc_stacked    — subplots empilhados (padrão MIT build_fig_stacked)
    build_dc_sidebyside — grade 2×N lado a lado
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ─────────────────────────────────────────────────────────────────────────────
# TEMA
# ─────────────────────────────────────────────────────────────────────────────

def _plot_theme(dark: bool) -> dict:
    if dark:
        return dict(
            plot_bg  = "#151a24",
            paper_bg = "#0f1218",
            fg       = "#e5e7eb",
            grid     = "rgba(255,255,255,0.15)",
        )
    return dict(
        plot_bg  = "#ffffff",
        paper_bg = "#ffffff",
        fg       = "#000000",
        grid     = "#B9ADAD",
    )


_VAR_COLORS = {
    "ia":  "#1f77b4",   # azul
    "ifd": "#ff7f0e",   # laranja
    "wm":  "#2ca02c",   # verde
    "Te":  "#d62728",   # vermelho
    "Ea":  "#9467bd",   # roxo
}

_DEFAULT_COLOR = "#636efa"


# ─────────────────────────────────────────────────────────────────────────────
# BUILDERS PRINCIPAIS
# ─────────────────────────────────────────────────────────────────────────────

def build_dc_stacked(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool = False,
) -> go.Figure:
    """Subplots empilhados — um painel por variável, eixo X compartilhado.

    Parâmetros
    ----------
    res : dict
        Deve conter chave 't' + uma chave por variável em var_keys.
    var_keys : list[str]
        Variáveis a plotar (e.g. ['ia', 'wm', 'Te']).
    var_labels : list[str]
        Rótulos de eixo Y correspondentes.
    dark : bool
        Tema escuro.
    """
    pt = _plot_theme(dark)
    t  = np.asarray(res["t"])

    # Filtrar vars disponíveis
    pairs = [(k, l) for k, l in zip(var_keys, var_labels) if k in res]
    if not pairs:
        fig = go.Figure()
        fig.update_layout(
            title="Nenhuma variável disponível",
            paper_bgcolor=pt["paper_bg"],
        )
        return fig

    n = len(pairs)
    fig = make_subplots(
        rows=n,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06 if n <= 3 else 0.04,
    )

    for i, (key, label) in enumerate(pairs, 1):
        y_data = np.asarray(res[key])
        color  = _VAR_COLORS.get(key, _DEFAULT_COLOR)

        fig.add_trace(
            go.Scatter(
                x=t,
                y=y_data,
                mode="lines",
                name=label,
                line=dict(color=color, width=2),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "t = %{x:.4f} s<br>"
                    "valor = %{y:.4f}<extra></extra>"
                ),
            ),
            row=i,
            col=1,
        )

        fig.update_yaxes(
            row=i, col=1,
            title_text=label,
            title_font=dict(size=11, color=pt["fg"]),
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
            zeroline=True, zerolinecolor=pt["grid"],
            tickfont=dict(size=9, color=pt["fg"]),
            exponentformat="none",
        )

    fig.update_xaxes(
        row=n, col=1,
        title_text="Tempo (s)",
        title_font=dict(size=11, color=pt["fg"]),
        showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
        tickfont=dict(size=9, color=pt["fg"]),
    )

    # Eixos intermediários: mostrar ticks mas sem título
    for i in range(1, n):
        fig.update_xaxes(
            row=i, col=1,
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
            tickfont=dict(size=9, color=pt["fg"]),
        )

    altura = max(250 * n, 400)
    fig.update_layout(
        height=altura,
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=65, r=20, t=40, b=50),
        hovermode="x unified",
        showlegend=False,
        title=dict(
            text="Resposta Transiente — Máquina CC",
            font=dict(size=14, color=pt["fg"]),
            x=0.5, xanchor="center",
        ),
    )

    return fig


def build_dc_sidebyside(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool = False,
) -> go.Figure:
    """Grade 2×N — pares de variáveis lado a lado.

    Parâmetros iguais a build_dc_stacked. Variáveis ímpares ocupam coluna da esquerda,
    pares a da direita (última linha pode ter apenas 1 gráfico).
    """
    pt = _plot_theme(dark)
    t  = np.asarray(res["t"])

    pairs = [(k, l) for k, l in zip(var_keys, var_labels) if k in res]
    if not pairs:
        fig = go.Figure()
        fig.update_layout(
            title="Nenhuma variável disponível",
            paper_bgcolor=pt["paper_bg"],
        )
        return fig

    n_rows = (len(pairs) + 1) // 2

    specs = [[{"type": "xy"}, {"type": "xy"}]] * n_rows

    fig = make_subplots(
        rows=n_rows,
        cols=2,
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
        specs=specs,
    )

    for idx, (key, label) in enumerate(pairs):
        row = idx // 2 + 1
        col = idx % 2 + 1
        y_data = np.asarray(res[key])
        color  = _VAR_COLORS.get(key, _DEFAULT_COLOR)

        fig.add_trace(
            go.Scatter(
                x=t,
                y=y_data,
                mode="lines",
                name=label,
                line=dict(color=color, width=2),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "t = %{x:.4f} s<br>"
                    "valor = %{y:.4f}<extra></extra>"
                ),
            ),
            row=row,
            col=col,
        )

        fig.update_yaxes(
            row=row, col=col,
            title_text=label,
            title_font=dict(size=10, color=pt["fg"]),
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
            zeroline=True, zerolinecolor=pt["grid"],
            tickfont=dict(size=9, color=pt["fg"]),
            exponentformat="none",
        )
        fig.update_xaxes(
            row=row, col=col,
            title_text="Tempo (s)",
            title_font=dict(size=10, color=pt["fg"]),
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
            tickfont=dict(size=9, color=pt["fg"]),
        )

    altura = max(300 * n_rows, 400)
    fig.update_layout(
        height=altura,
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=60, r=20, t=40, b=50),
        hovermode="closest",
        showlegend=False,
        title=dict(
            text="Resposta Transiente — Máquina CC",
            font=dict(size=14, color=pt["fg"]),
            x=0.5, xanchor="center",
        ),
    )

    return fig
