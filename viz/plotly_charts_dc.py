from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _plot_theme(dark: bool) -> dict:
    if dark:
        return dict(
            plot_bg    = "#151a24",
            paper_bg   = "#0f1218",
            fg         = "#e5e7eb",
            grid       = "rgba(255,255,255,0.15)",
        )
    return dict(
        plot_bg    = "#ffffff",
        paper_bg   = "#ffffff",
        fg         = "#000000",
        grid       = "#B9ADAD",
    )


_VAR_COLORS = {
    "ia":   "#1f77b4",  # azul
    "ifd":  "#ff7f0e",  # laranja
    "wm":   "#2ca02c",  # verde
    "Te":   "#d62728",  # vermelho
    "Ea":   "#9467bd",  # roxo
}


def _build_dc_frames(t: np.ndarray, state_dict: dict) -> list[go.Frame]:
    """
    Constrói frames para animação da resposta transiente DC.

    state_dict: {ifd, ia, wm, Te, Ea, [Vf]} — todas séries temporais
    Retorna: lista de go.Frame com dados truncados progressivamente
    """
    frames = []
    var_keys = ["ifd", "ia", "wm", "Te", "Ea"]

    for i in range(len(t)):
        traces = []
        for var_key in var_keys:
            y_data = state_dict[var_key]
            traces.append(go.Scatter(
                x=t[:i+1],
                y=y_data[:i+1],
                mode="lines",
                name=var_key.upper(),
                line=dict(color=_VAR_COLORS[var_key], width=2),
                hovertemplate=f"<b>{var_key.upper()}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.3f}}<extra></extra>",
            ))

        frame = go.Frame(data=traces, name=str(i))
        frames.append(frame)

    return frames


def build_dc_timeseries_fig(res: dict, dark: bool = False) -> go.Figure:
    """
    Constrói figura animada com 5 subplots (ia, ifd, wm, Te, Ea).

    res: {t, ifd, ia, wm, Te, Ea, [Vf]}
    Retorna: go.Figure com frames e controles de animação
    """
    pt = _plot_theme(dark)
    t = res["t"]
    var_keys = ["ifd", "ia", "wm", "Te", "Ea"]
    var_labels = ["ifd (A)", "ia (A)", "ωm (rad/s)", "Te (N·m)", "Ea (V)"]

    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        subplot_titles=var_labels,
        vertical_spacing=0.08,
    )

    # Adiciona traces iniciais (completos, ocultos — serão substituídos pela animação)
    for i, (var_key, var_label) in enumerate(zip(var_keys, var_labels), 1):
        fig.add_trace(go.Scatter(
            x=t, y=res[var_key],
            mode="lines",
            name=var_label,
            line=dict(color=_VAR_COLORS[var_key], width=2),
            hovertemplate=f"<b>{var_label}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.3f}}<extra></extra>",
        ), row=i, col=1)

        fig.update_yaxes(
            row=i, col=1,
            title_text=var_label,
            title_font=dict(size=11, color=pt["fg"]),
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
            zeroline=True, zerolinecolor=pt["grid"],
            tickfont=dict(size=9, color=pt["fg"]),
            exponentformat="none",
        )

    fig.update_xaxes(
        row=5, col=1,
        title_text="Tempo (s)",
        showgrid=True, gridcolor=pt["grid"], gridwidth=0.5,
        tickfont=dict(size=9, color=pt["fg"]),
    )

    # Constrói frames
    frames = _build_dc_frames(t, {k: res[k] for k in var_keys})
    fig.frames = frames

    # Controles de animação
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(label="▶ Play", method="animate",
                         args=[None, {"frame": {"duration": 50, "redraw": True},
                                     "fromcurrent": True}]),
                    dict(label="⏸ Pause", method="animate",
                         args=[[None], {"frame": {"duration": 0, "redraw": False},
                                       "mode": "immediate"}]),
                ],
                x=0.0, y=1.08, xanchor="left", yanchor="top",
            )
        ],
        height=900,
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=65, r=20, t=80, b=50),
        hovermode="x unified",
        title=dict(
            text="Resposta Transiente da Máquina CC",
            font=dict(size=14, color=pt["fg"]),
            x=0.5, xanchor="center",
        ),
    )

    return fig


def build_dc_param_sweep_fig(
    mp,
    config_dict: dict,
    param_name: str = "Vf",
    param_range: list | None = None,
    dark: bool = False,
) -> go.Figure:
    """
    Constrói figura com slider paramétrico (e.g., Vf varrido).

    Pré-computa família de trajectórias e constrói frames indexados por param_idx.

    mp: MachineParams (DC)
    config_dict: configuração base {t_end, solver, ...}
    param_name: "Vf", "ifd_ref", etc.
    param_range: [v_min, v_max, n_steps] ou None (auto: 5 passos)

    Retorna: go.Figure com slider e características Te×wm parametrizadas
    """
    pt = _plot_theme(dark)

    if param_range is None:
        if param_name == "Vf":
            param_range = [100, 200, 5]
        else:
            param_range = [0.5, 2.0, 5]

    v_min, v_max, n_steps = param_range
    param_vals = np.linspace(v_min, v_max, n_steps)

    # Dummy: cria frames para slider (em produção, rodar simulações para cada param_val)
    frames = []
    for idx, pv in enumerate(param_vals):
        # Placeholder: seria run_simulation(mp, {**config_dict, param_name: pv})
        traces = [
            go.Scatter(x=[0], y=[0], mode="lines", name="Te×wm (placeholder)")
        ]
        frame = go.Frame(data=traces, name=str(idx))
        frames.append(frame)

    fig = go.Figure(
        data=[go.Scatter(x=[0], y=[0], mode="lines", name="Te×wm")],
        frames=frames,
    )

    fig.update_layout(
        sliders=[
            dict(
                active=0,
                currentvalue=dict(
                    prefix=f"{param_name} = ",
                    visible=True,
                    xanchor="center",
                ),
                pad=dict(b=10, t=50),
                len=0.9,
                x=0.05,
                y=0,
                steps=[
                    dict(
                        args=[[str(i)], {"frame": {"duration": 300, "redraw": True},
                                        "mode": "immediate"}],
                        label=f"{pv:.2f}",
                        method="animate",
                    )
                    for i, pv in enumerate(param_vals)
                ],
            )
        ],
        height=500,
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10, color=pt["fg"]),
        margin=dict(l=60, r=20, t=50, b=80),
        hovermode="closest",
        title=dict(
            text=f"Característica Te×ωm parametrizada por {param_name}",
            font=dict(size=13, color=pt["fg"]),
            x=0.5, xanchor="center",
        ),
    )

    return fig
