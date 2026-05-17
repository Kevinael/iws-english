from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


_LINE_COLORS_DARK  = ["#ffffff"] * 12
_LINE_COLORS_LIGHT = ["#000000"] * 12


def _colors(dark: bool) -> list:
    return _LINE_COLORS_DARK if dark else _LINE_COLORS_LIGHT


def _plot_theme(dark: bool) -> dict:
    if dark:
        return dict(
            plot_bg    = "#151a24",
            paper_bg   = "#0f1218",
            fg         = "#e5e7eb",
            grid       = "rgba(255,255,255,0.15)",
            event_line = "#f59e0b",
        )
    return dict(
        plot_bg    = "#ffffff",
        paper_bg   = "#ffffff",
        fg         = "#000000",
        grid       = "#B9ADAD",
        event_line = "#000000",
    )


_TL_COLOR = "#f59e0b"  # âmbar — distingue TL de Te nos gráficos


def build_fig_stacked(res, var_keys, var_labels, dark, t_events, decimals=2,
                      tl_arr=None) -> go.Figure:
    n = len(var_keys)
    pt = _plot_theme(dark)
    cols = _colors(dark)
    has_tl = tl_arr is not None and "Te" in var_keys

    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        vertical_spacing=max(0.05, 0.07/max(n,1)),
    )
    t = res["t"]
    for i, (key, lbl) in enumerate(zip(var_keys, var_labels), 1):
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=cols[(i-1) % len(cols)], width=1.9),
            hovertemplate=f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}}<extra></extra>",
        ), row=i, col=1)
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name="TL (N·m)",
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=f"<b>TL</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}} N·m<extra></extra>",
            ), row=i, col=1)
        for te in (t_events or []):
            fig.add_vline(x=te, line_dash="dot", line_color=pt["event_line"],
                          line_width=1.1, row=i, col=1)
        fig.update_yaxes(row=i, col=1,
                         title_text=lbl,
                         title_font=dict(size=12, color=pt["fg"]),
                         showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
                         zeroline=True, zerolinecolor=pt["grid"],
                         tickfont=dict(size=10, color=pt["fg"]),
                         exponentformat="none",
                         autorange=True,
                         rangemode="normal",
                         fixedrange=False)

    fig.update_xaxes(row=n, col=1, title_text="Tempo (s)",
                     showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
                     tickfont=dict(size=10, color=pt["fg"]))
    fig.update_layout(
        height=max(300, 280*n),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=55, r=20, t=45, b=40),
        hovermode="x unified",
        showlegend=has_tl,
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)") if has_tl else {},
    )
    return fig


def build_fig_sidebyside(res, var_keys, var_labels, dark, t_events, decimals=2,
                         ref_list=None, primary_color=None,
                         compact: bool = False, tl_arr=None) -> list[go.Figure]:
    # ref_list: list of {"res": dict, "color": str, "dash": str, "label": str}
    cols = _colors(dark)
    figs = []
    t    = res["t"]
    th   = _plot_theme(dark)
    has_tl = tl_arr is not None and "Te" in var_keys

    for i, (key, lbl) in enumerate(zip(var_keys, var_labels)):
        pcol = primary_color if primary_color else cols[i % len(cols)]
        fig  = go.Figure()
        for ref_item in (ref_list or []):
            res_ref   = ref_item.get("res")
            ref_color = ref_item.get("color", "#888888")
            ref_dash  = ref_item.get("dash", "dash")
            ref_label = ref_item.get("label", "Referência")
            if res_ref is not None and key in res_ref:
                fig.add_trace(go.Scatter(
                    x=res_ref["t"], y=res_ref[key], mode="lines", name=ref_label,
                    line=dict(color=ref_color, width=1.4, dash=ref_dash),
                    hovertemplate=f"<b>{ref_label}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}}<extra></extra>",
                ))
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=pcol, width=1.8),
            hovertemplate=f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}}<extra></extra>",
        ))
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name="TL (N·m)",
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=f"<b>TL</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}} N·m<extra></extra>",
            ))
        for te in (t_events or []):
            fig.add_vline(x=te, line_dash="dot", line_color=th["event_line"], line_width=1.1)
        _h   = 200 if compact else 230
        _m   = dict(l=28, r=8,  t=26, b=26) if compact else dict(l=45, r=12, t=36, b=36)
        _fsz = 9   if compact else 10
        fig.update_layout(
            title=dict(text=lbl, x=0.5, xanchor="center",
                       font=dict(size=11 if compact else 12, color=th["fg"])),
            height=_h,
            paper_bgcolor=th["paper_bg"], plot_bgcolor=th["plot_bg"],
            font=dict(family="Inter, system-ui", size=_fsz, color=th["fg"]),
            margin=_m,
            xaxis=dict(title="Tempo (s)", showgrid=True,
                       gridcolor=th["grid"], tickfont=dict(size=9, color=th["fg"])),
            yaxis=dict(showgrid=True, gridcolor=th["grid"],
                       zeroline=True, zerolinecolor=th["grid"],
                       tickfont=dict(size=9, color=th["fg"]),
                       exponentformat="none",
                       autorange=True, rangemode="normal", fixedrange=False),
            hovermode="x unified",
            showlegend=(key == "Te" and has_tl),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=9),
                        bgcolor="rgba(0,0,0,0)") if (key == "Te" and has_tl) else {},
        )
        figs.append(fig)
    return figs


def build_fig_overlay(res, var_keys, var_labels, dark, t_events, decimals=2,
                      ref_list=None, primary_color=None,
                      compact: bool = False, tl_arr=None) -> go.Figure:
    # ref_list: list of {"res": dict, "color": str, "dash": str, "label": str}
    pt   = _plot_theme(dark)
    cols = _colors(dark)
    t    = res["t"]

    right_units = {"n", "wr"}
    has_right   = any(k in right_units for k in var_keys)
    has_tl      = tl_arr is not None and "Te" in var_keys

    fig = go.Figure()
    for ref_item in (ref_list or []):
        res_ref   = ref_item.get("res")
        ref_color = ref_item.get("color", "#888888")
        ref_dash  = ref_item.get("dash", "dash")
        ref_label = ref_item.get("label", "Referência")
        if res_ref is not None:
            for key, lbl in zip(var_keys, var_labels):
                if key not in res_ref:
                    continue
                yaxis = "y2" if (key in right_units and has_right) else "y"
                fig.add_trace(go.Scatter(
                    x=res_ref["t"], y=res_ref[key], mode="lines",
                    name=f"{ref_label} — {lbl}", yaxis=yaxis,
                    line=dict(color=ref_color, width=1.4, dash=ref_dash),
                    hovertemplate=f"<b>{ref_label}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}}<extra></extra>",
                ))
    for i, (key, lbl) in enumerate(zip(var_keys, var_labels)):
        pcol  = primary_color if primary_color else cols[i % len(cols)]
        yaxis = "y2" if (key in right_units and has_right) else "y"
        fig.add_trace(go.Scatter(
            x=t, y=res[key], mode="lines", name=lbl,
            line=dict(color=pcol, width=1.9), yaxis=yaxis,
            hovertemplate=f"<b>{lbl}</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}}<extra></extra>",
        ))
        if key == "Te" and has_tl:
            fig.add_trace(go.Scatter(
                x=t, y=tl_arr, mode="lines", name="TL (N·m)",
                line=dict(color=_TL_COLOR, width=1.6, dash="dash"),
                hovertemplate=f"<b>TL</b><br>t = %{{x:.4f}} s<br>valor = %{{y:.{decimals}f}} N·m<extra></extra>",
            ))
    for te in (t_events or []):
        fig.add_vline(x=te, line_dash="dot", line_color=pt["event_line"], line_width=1.1)

    y2_cfg = dict(
        overlaying="y", side="right",
        showgrid=False, zeroline=False,
        tickfont=dict(size=10, color=pt["fg"]),
        exponentformat="none",
        autorange=True, rangemode="normal", fixedrange=False,
    ) if has_right else {}

    _r_val = (45 if has_right else 8)  if compact else (65 if has_right else 20)
    _ov_m  = dict(l=35, r=_r_val, t=32, b=28) if compact else dict(l=55, r=65 if has_right else 20, t=48, b=40)
    fig.update_layout(
        height=320 if compact else 380,
        title=dict(text="Curvas Sobrepostas", x=0.5, xanchor="center",
                   font=dict(size=11 if compact else 12, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=10 if compact else 11, color=pt["fg"]),
        margin=_ov_m,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(title="Tempo (s)", showgrid=True,
                   gridcolor=pt["grid"], gridwidth=0.4,
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(showgrid=True, gridcolor=pt["grid"],
                   zeroline=True, zerolinecolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   exponentformat="none",
                   autorange=True, rangemode="normal", fixedrange=False),
        yaxis2=y2_cfg if has_right else {},
    )
    return fig


def build_fig_torque_speed(
    res: dict,
    P_nom_kw: float,
    f: float,
    p: int,
    dark: bool = False,
) -> go.Figure:
    """Conjugado eletromagnético vs. velocidade do rotor.

    Traça a trajetória dinâmica completa da partida até o regime permanente e
    sobrepõe referências nominais de projeto (velocidade síncrona e torque nominal).

    Args:
        res: dicionário de resultados do solver (campos "n" em RPM, "Te" em N·m).
        P_nom_kw: potência mecânica nominal do motor em kW.
        f: frequência nominal em Hz.
        p: número de polos.
        dark: True para tema escuro.
    """
    pt = _plot_theme(dark)

    rpm_array = np.asarray(res["n"],  dtype=float)
    te_array  = np.asarray(res["Te"], dtype=float)

    # Descarta os primeiros 5 ciclos elétricos: nesse intervalo Te oscila
    # violentamente em torno de wr≈0 (inrush eletromagnético), poluindo a
    # trajetória T×n. Mesma janela usada por _compute_thermal.
    t_array = np.asarray(res.get("t", []), dtype=float)
    if len(t_array) > 1 and f > 0:
        h     = float(t_array[1] - t_array[0])
        n_skip = min(max(0, int(round(5.0 / (f * h)))), len(rpm_array) - 1)
    else:
        n_skip = 0
    rpm_plot = rpm_array[n_skip:]
    te_plot  = te_array[n_skip:]

    # Ponto de operação: última amostra válida (sobre o array já recortado)
    valid_mask   = np.isfinite(rpm_plot) & np.isfinite(te_plot)
    rpm_op       = float(rpm_plot[valid_mask][-1]) if valid_mask.any() else float(rpm_plot[-1])
    torque_op    = float(te_plot[valid_mask][-1])  if valid_mask.any() else float(te_plot[-1])

    # Referências nominais
    n_sync       = 120.0 * f / p                           # RPM síncrona
    n_nom        = n_sync * (1.0 - 0.03)                   # RPM nominal (s = 3%)
    omega_nom    = n_nom * 2.0 * np.pi / 60.0              # rad/s
    torque_nom   = (P_nom_kw * 1000.0) / omega_nom         # N·m

    col_traj  = "#60a5fa" if dark else "#1d4ed8"   # azul
    col_op    = "#f59e0b"                           # âmbar — destaque
    col_ref   = "#6b7280"                           # cinza — linhas de referência

    fig = go.Figure()

    # Trajetória dinâmica (sem o transitorio eletromagnetico inicial)
    fig.add_trace(go.Scatter(
        x=rpm_plot, y=te_plot,
        mode="lines",
        name="Trajetoria Dinamica",
        line=dict(color=col_traj, width=1.8),
        hovertemplate="<b>Trajetoria</b><br>n = %{x:.1f} RPM<br>Te = %{y:.2f} N·m<extra></extra>",
    ))

    # Ponto de operação em regime permanente
    fig.add_trace(go.Scatter(
        x=[rpm_op], y=[torque_op],
        mode="markers",
        name="Ponto de Operacao (Regime)",
        marker=dict(symbol="star", size=14, color=col_op,
                    line=dict(color=col_op, width=1)),
        hovertemplate=(
            "<b>Regime Permanente</b><br>"
            "n = %{x:.1f} RPM<br>"
            "Te = %{y:.2f} N·m<extra></extra>"
        ),
    ))

    # Linha de referência: torque nominal estimado
    fig.add_hline(
        y=torque_nom,
        line=dict(color=col_ref, width=1.2, dash="dash"),
        annotation_text=f"Torque Nominal Est. ({torque_nom:.1f} N·m)",
        annotation_position="top left",
        annotation_font=dict(size=10, color=col_ref),
    )

    # Linha de referência: velocidade síncrona
    fig.add_vline(
        x=n_sync,
        line=dict(color=col_ref, width=1.2, dash="dot"),
        annotation_text=f"Vel. Sincrona ({n_sync:.0f} RPM)",
        annotation_position="top right",
        annotation_font=dict(size=10, color=col_ref),
    )

    fig.update_layout(
        height=380,
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=40, b=50),
        hovermode="closest",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="right", x=1,
            font=dict(size=10), bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title="Velocidade do Rotor (RPM)",
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
            tickfont=dict(size=10, color=pt["fg"]),
            zeroline=False,
        ),
        yaxis=dict(
            title="Conjugado Eletromagnetico Te (N·m)",
            showgrid=True, gridcolor=pt["grid"], gridwidth=0.4,
            zeroline=True, zerolinecolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
            exponentformat="none", autorange=True,
        ),
        uirevision="ts-chart",
    )
    return fig
