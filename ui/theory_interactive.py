# -*- coding: utf-8 -*-
"""Componentes interativos Plotly para a aba Teoria.

Cada função é autocontida: lê parâmetros da máquina de st.session_state
(usando o resultado da última simulação, ou o motor Krause 3HP como fallback)
e renderiza um gráfico Plotly interativo via st.plotly_chart.

Exporta:
    render_boucherot            — Te×s com slider de R'₂ (Boucherot)
    render_zonas_operacao       — Te×n com zonas coloridas e diagrama vetorial
    render_comparativo_partidas — corrente×tempo: DOL, Y-D, Soft-Starter
    render_park_dinamico        — plano vetorial αβ/dq + séries temporais
    render_sankey_potencia      — Sankey de fluxo de potência com slider de s
    render_circuito_alternavel  — Circuito equivalente alternável (completo / IEEE)
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import io
import matplotlib
try:
    matplotlib.use("Agg")
except Exception:
    pass
import matplotlib.pyplot as plt

from viz.plotly_charts import _plot_theme
from viz.eqcircuit_plotter import build_figure
from core.curva_tn import _extract_params, _torque_array, calc_fluxo_potencia


# ─────────────────────────────────────────────────────────────────────────────
# PARÂMETROS FALLBACK — Motor Krause 3HP (NEMA, 60 Hz)
# ─────────────────────────────────────────────────────────────────────────────

class _FallbackMP:
    """Subconjunto mínimo de MachineParams para os componentes interativos."""
    Vl    = 220.0          # tensão de fase RMS (V)
    f     = 60.0           # frequência (Hz)
    Rs    = 0.435          # resistência do estator (Ω)
    Rr    = 0.816          # resistência do rotor (Ω)
    Xm    = 26.13          # reatância de magnetização (Ω)
    Xls   = 0.754          # reatância de dispersão do estator (Ω)
    Xlr   = 0.754          # reatância de dispersão do rotor (Ω)
    Rfe   = 500.0
    p     = 4              # número de polos
    J     = 0.089          # inércia (kg·m²)
    B     = 0.0

    @property
    def wb(self):
        return 2.0 * np.pi * self.f

    @property
    def Lm(self):
        return self.Xm / self.wb

    @property
    def Xls_a(self):
        return self.Xls

    @property
    def Xlr_a(self):
        return self.Xlr

    @property
    def n_sync(self):
        return 120.0 * self.f / self.p


_MP_DEFAULT = _FallbackMP()


def _get_mp():
    """Retorna MachineParams da última simulação ou o fallback."""
    res = st.session_state.get("sim_result")
    if res and "mp" in res:
        return res["mp"]
    return _MP_DEFAULT


def _dark() -> bool:
    return bool(st.session_state.get("dark_mode", False))


# ─────────────────────────────────────────────────────────────────────────────
# 1. BOUCHEROT INTERATIVO — Te×s com slider de R'₂
# ─────────────────────────────────────────────────────────────────────────────

def render_boucherot() -> None:
    """Gráfico Te×s com slider nativo Plotly (zero latência) — teorema de Boucherot.

    Pré-calcula N_STEPS curvas para o grid de R'₂ e empacota como frames Plotly.
    O slider JS move entre frames no cliente, sem rerun do Streamlit.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2_nom, X2, Xm, ws_mec, ns = _extract_params(mp)

    # Thevenin
    Zth  = (1j * Xm * (R1 + 1j * X1)) / (R1 + 1j * (X1 + Xm))
    Rth  = Zth.real
    Xth  = Zth.imag
    Vth  = abs(V1 * 1j * Xm / (R1 + 1j * (X1 + Xm)))
    Tmax = 3.0 * Vth**2 / (2.0 * ws_mec * (Rth + np.sqrt(Rth**2 + (Xth + X2)**2)))

    # Grid de R'₂ — 60 passos logarítmicos entre 0.2× e 5× o nominal
    N_STEPS = 60
    r2_grid = np.geomspace(R2_nom * 0.2, 3.0, N_STEPS)
    # Índice inicial: valor nominal mais próximo
    nom_idx = int(np.argmin(np.abs(r2_grid - R2_nom)))

    def _make_s_arr(scr: float) -> np.ndarray:
        """Grid de s adaptativo: densidade alta ao redor de s_cr."""
        wing = min(scr * 0.8, 0.15)
        return np.unique(np.concatenate([
            np.linspace(1e-4, max(1e-4, scr - wing), 200),
            np.linspace(max(1e-4, scr - wing), min(1.0, scr + wing), 300),
            np.linspace(min(1.0, scr + wing), 1.0, 100),
            np.linspace(1.001, 2.0, 60),
        ]))

    col_sel  = "#4f8ef7" if dark else "#1d4ed8"
    col_peak = "#f97316"
    col_scr  = "#a78bfa" if dark else "#7c3aed"

    # Curva inicial (frame nom_idx)
    r2_init   = r2_grid[nom_idx]
    scr_init  = r2_init / np.sqrt(Rth**2 + (Xth + X2)**2)
    s_arr_i   = _make_s_arr(scr_init)
    Te_init   = _torque_array(s_arr_i, V1, R1, X1, r2_init, X2, Xm, ws_mec)
    peak_idx  = int(np.argmax(Te_init))
    s_peak_i  = float(s_arr_i[peak_idx])
    Te_peak_i = float(Te_init[peak_idx])

    # s_arr fixo para calcular Te_max_plot (pior caso = R2 mínimo, scr menor)
    s_ref     = _make_s_arr(R2_nom * 0.2 / np.sqrt(Rth**2 + (Xth + X2)**2))

    Te_max_plot = float(Tmax) * 1.25

    # ── figura base ──────────────────────────────────────────────────────────
    fig = go.Figure()

    # Trace 0 — curva principal (variável por frame)
    fig.add_trace(go.Scatter(
        x=s_arr_i, y=Te_init,
        mode="lines",
        name=f"R'₂ = {r2_init:.3f} Ω",
        line=dict(color=col_sel, width=3),
    ))

    # Trace 1 — marcador no pico
    fig.add_trace(go.Scatter(
        x=[s_peak_i], y=[Te_peak_i],
        mode="markers+text",
        text=[f"T_max = {Te_peak_i:.1f} N·m"],
        textposition="top center",
        textfont=dict(color=col_peak, size=11),
        marker=dict(color=col_peak, size=12, symbol="circle",
                    line=dict(color=pt["paper_bg"], width=2)),
        showlegend=False,
    ))

    # Trace 2 — linha vertical pontilhada descendo do pico ao eixo X
    fig.add_trace(go.Scatter(
        x=[s_peak_i, s_peak_i], y=[0, Te_peak_i],
        mode="lines",
        line=dict(color=col_peak, width=1.5, dash="dot"),
        showlegend=False,
    ))

    # Trace 3 — marcador de s_cr no eixo (y=0) com rótulo
    fig.add_trace(go.Scatter(
        x=[s_peak_i], y=[0],
        mode="markers+text",
        text=[f"s_cr = {s_peak_i:.3f}"],
        textposition="top center",
        textfont=dict(color=col_scr, size=10),
        marker=dict(color=col_scr, size=8, symbol="triangle-up"),
        showlegend=False,
    ))

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    for i, r2 in enumerate(r2_grid):
        scr   = r2 / np.sqrt(Rth**2 + (Xth + X2)**2)
        s_f   = _make_s_arr(scr)
        Te    = _torque_array(s_f, V1, R1, X1, r2, X2, Xm, ws_mec)
        pidx  = int(np.argmax(Te))
        sp    = float(s_f[pidx])
        Tp    = float(Te[pidx])
        label = f"{r2:.3f}"
        frames.append(go.Frame(
            name=str(i),
            data=[
                go.Scatter(x=s_f.tolist(), y=Te.tolist(), name=f"R'₂ = {r2:.3f} Ω"),
                go.Scatter(x=[sp], y=[Tp],
                           text=[f"T_max = {Tp:.1f} N·m"],
                           textposition="top center"),
                go.Scatter(x=[sp, sp], y=[0, Tp]),
                go.Scatter(x=[sp], y=[0],
                           text=[f"s_cr = {sp:.3f}"]),
            ],
            traces=[0, 1, 2, 3],
        ))
        slider_steps.append(dict(
            method="animate",
            label=label,
            args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                 transition=dict(duration=0))],
        ))

    fig.frames = frames

    # ── layout com slider JS ─────────────────────────────────────────────────
    fig.update_layout(
        height=460,
        title=dict(text="Curva T×s — Teorema de Boucherot (T_max invariante com R'₂)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=130),
        xaxis=dict(title="Escorregamento s", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]), range=[0, 2.0],
                   zeroline=True, zerolinecolor=pt["grid"]),
        yaxis=dict(title="Torque (N·m)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"]),
                   range=[0, Te_max_plot]),
        showlegend=True,
        legend=dict(
            x=0.98, y=0.98, xanchor="right", yanchor="top",
            font=dict(size=10, color=pt["fg"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        sliders=[dict(
            active=nom_idx,
            currentvalue=dict(
                prefix="R'₂ = ",
                suffix=" Ω",
                visible=True,
                xanchor="center",
                font=dict(size=13, color=pt["fg"]),
            ),
            # y=0 ancora o slider na base do paper; pad empurra para baixo do eixo X
            y=0,
            pad=dict(t=55, b=10),
            len=0.92,
            x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"],
            bordercolor=pt["grid"],
            tickcolor=pt["fg"],
            font=dict(color=pt["fg"], size=9),
        )],
        # updatemenus oculto é necessário para o slider animate funcionar
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )

    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ─────────────────────────────────────────────────────────────────────────────
# 2. ZONAS DE OPERAÇÃO — Te×n com zonas coloridas e diagrama vetorial
# ─────────────────────────────────────────────────────────────────────────────

def render_zonas_operacao() -> None:
    """Gráfico Te×n com três zonas coloridas e diagrama vetorial de ωs/ωm."""
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)

    # Seleciona zona para o diagrama vetorial
    zona = st.radio(
        "Região de operação",
        options=["Motor (0 < s < 1)", "Gerador (s < 0)", "Frenagem (s > 1)"],
        horizontal=True,
        key="th_zona_radio",
    )

    # Arrays por região
    s_brake  = np.linspace(1.001, 2.0,  150)
    s_motor  = np.linspace(1e-4,  1.0,  400)
    s_gen    = np.linspace(-1.0, -1e-4, 150)

    Te_brake = _torque_array(s_brake, V1, R1, X1, R2, X2, Xm, ws_mec)
    Te_motor = _torque_array(s_motor, V1, R1, X1, R2, X2, Xm, ws_mec)
    Te_gen   = _torque_array(s_gen,   V1, R1, X1, R2, X2, Xm, ws_mec)

    n_brake = ns * (1.0 - s_brake)
    n_motor = ns * (1.0 - s_motor)
    n_gen   = ns * (1.0 - s_gen)

    alpha_zone = 0.18

    col_motor = "#4f8ef7" if dark else "#1d4ed8"
    col_gen   = "#34d399" if dark else "#059669"
    col_brake = "#f87171" if dark else "#dc2626"

    fig = go.Figure()

    # Faixas de fundo por zona
    fig.add_vrect(x0=float(n_brake.min()), x1=float(n_brake.max()),
                  fillcolor=col_brake, opacity=alpha_zone, layer="below", line_width=0)
    fig.add_vrect(x0=0.0, x1=float(ns),
                  fillcolor=col_motor, opacity=alpha_zone, layer="below", line_width=0)
    fig.add_vrect(x0=float(ns), x1=float(n_gen.max()),
                  fillcolor=col_gen, opacity=alpha_zone, layer="below", line_width=0)

    # Curvas
    fig.add_trace(go.Scatter(x=n_brake, y=Te_brake, mode="lines",
                             name="Frenagem", line=dict(color=col_brake, width=2.5)))
    fig.add_trace(go.Scatter(x=n_motor, y=Te_motor, mode="lines",
                             name="Motor", line=dict(color=col_motor, width=2.5)))
    fig.add_trace(go.Scatter(x=n_gen, y=Te_gen, mode="lines",
                             name="Gerador", line=dict(color=col_gen, width=2.5)))

    # Linha de velocidade síncrona
    fig.add_vline(x=float(ns), line_dash="dash", line_color=pt["fg"],
                  line_width=1.5, annotation_text=f"ns = {ns:.0f} RPM",
                  annotation_font_color=pt["fg"])

    fig.update_layout(
        height=340,
        title=dict(text="Curva T×n — Três Regiões de Operação",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=45),
        xaxis=dict(title="Velocidade (RPM)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(title="Torque (N·m)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    # Diagrama vetorial animado
    _render_diagrama_vetorial(zona, dark)


@st.cache_data(show_spinner="Gerando animação…")
def _build_gif_vetorial(zona: str, dark: bool) -> tuple[bytes, str]:
    """Gera os bytes do GIF animado para a zona e tema dados. Resultado cacheado."""
    import tempfile, os, base64
    from math import gcd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation

    if zona.startswith("Motor"):
        wr_frac   = 0.75
        col_rotor = "#4f8ef7" if dark else "#1d4ed8"
        titulo    = "Motor — ωm < ωs"
        desc      = "O campo girante puxa o rotor. Torque no mesmo sentido do movimento."
    elif zona.startswith("Gerador"):
        wr_frac   = 1.25
        col_rotor = "#34d399" if dark else "#059669"
        titulo    = "Gerador — ωm > ωs"
        desc      = "O rotor ultrapassa o campo. Torque opõe-se ao movimento — geração."
    else:
        wr_frac   = -0.50
        col_rotor = "#f87171" if dark else "#dc2626"
        titulo    = "Frenagem — ωm < 0 (sentido inverso)"
        desc      = "Rotor gira ao contrário do campo. Energia cinética + elétrica viram calor."

    bg_hex   = "#151a24" if dark else "#ffffff"
    fg_hex   = "#e5e7eb" if dark else "#111111"
    grid_hex = "#2a2a3a" if dark else "#dddddd"

    _STEPS_PER_REV = 48
    _MAX_REVS      = 12
    best_p, best_q = 1, 1
    best_err = abs(wr_frac - 1.0)
    for q in range(1, 21):
        p = round(wr_frac * q)
        if p == 0:
            continue
        err = abs(wr_frac - p / q)
        if err < best_err:
            best_err, best_p, best_q = err, abs(p), q
    g = gcd(best_p, best_q)
    n_revs_s = min(best_q // g, _MAX_REVS)

    N       = _STEPS_PER_REV * n_revs_s
    theta_s = np.linspace(0, 2 * np.pi * n_revs_s, N, endpoint=False)
    theta_m = theta_s * wr_frac

    fig_m, ax = plt.subplots(figsize=(3.2, 3.2))
    fig_m.patch.set_facecolor(bg_hex)
    ax.set_facecolor(bg_hex)
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")

    circ = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(circ), np.sin(circ), color=grid_hex, lw=1, ls="--")
    ax.set_title(titulo, color=fg_hex, fontsize=9, pad=6)
    ax.plot(0, 0, "o", color=fg_hex, ms=4, zorder=5)

    arr_s = ax.annotate("", xy=(1, 0), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=fg_hex,
                                        lw=2.0, mutation_scale=16))
    arr_m = ax.annotate("", xy=(1, 0), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=col_rotor,
                                        lw=2.0, linestyle="dashed",
                                        mutation_scale=16))
    ax.plot([], [], color=fg_hex,   lw=2,        label="ωs (campo)")
    ax.plot([], [], color=col_rotor, lw=2, ls="--", label="ωm (rotor)")
    ax.legend(loc="lower center", fontsize=7.5, framealpha=0,
              labelcolor=fg_hex, ncol=2)

    def _update(i):
        arr_s.set_position((0, 0)); arr_s.xy = (np.cos(theta_s[i]), np.sin(theta_s[i]))
        arr_m.set_position((0, 0)); arr_m.xy = (np.cos(theta_m[i]), np.sin(theta_m[i]))
        return arr_s, arr_m

    ani = animation.FuncAnimation(fig_m, _update, frames=N, interval=60, blit=True)

    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ani.save(tmp_path, writer="pillow", dpi=100)
        plt.close(fig_m)
        with open(tmp_path, "rb") as f:
            gif_bytes = f.read()
    finally:
        os.unlink(tmp_path)

    return gif_bytes, desc


def _render_diagrama_vetorial(zona: str, dark: bool) -> None:
    import base64
    gif_bytes, desc = _build_gif_vetorial(zona, dark)
    b64 = base64.b64encode(gif_bytes).decode()
    st.markdown(
        f'<img src="data:image/gif;base64,{b64}" width="300" style="display:block;margin:auto;">',
        unsafe_allow_html=True,
    )
    st.caption(desc)


# ─────────────────────────────────────────────────────────────────────────────
# 3. COMPARATIVO DE PARTIDAS — corrente×tempo
# ─────────────────────────────────────────────────────────────────────────────

def render_comparativo_partidas() -> None:
    """Curvas analíticas de corrente de fase vs. tempo para DOL, Y-D e Soft-Starter."""
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    V1, R1, X1, R2, X2, Xm, ws_mec, ns = _extract_params(mp)
    # Impedância a s=1 (partida)
    Z2_start  = R2 + 1j * X2
    Zeq_start = (1j * Xm * Z2_start) / (1j * Xm + Z2_start)
    Ztotal    = R1 + 1j * X1 + Zeq_start
    I_dol     = abs(V1 / Ztotal)           # pico de corrente DOL (A)
    # Corrente nominal: usa s ≈ 0.04
    Z2_nom   = (R2 / 0.04) + 1j * X2
    Zeq_nom  = (1j * Xm * Z2_nom) / (1j * Xm + Z2_nom)
    Zt_nom   = R1 + 1j * X1 + Zeq_nom
    I_nom    = abs(V1 / Zt_nom)

    # Constante de tempo elétrica aproximada
    tau_e  = (X1 + Xm * X2 / (Xm + X2)) / (2.0 * np.pi * mp.f * max(R1 + R2, 0.01))
    t_acc  = max(tau_e * 4.0, 0.3)        # tempo até regime
    t_max  = t_acc * 2.5

    t = np.linspace(0.0, t_max, 800)

    def _envelope(I_peak, tau):
        """Envelope de decaimento exponencial do transitório de corrente."""
        env = I_nom + (I_peak - I_nom) * np.exp(-t / max(tau, 1e-6))
        return np.maximum(env, I_nom)

    # DOL
    i_dol = _envelope(I_dol, tau_e)

    # Y-D: fase Y usa V/√3 → corrente reduzida a 1/3
    t_yd  = t_acc * 0.6          # instante de comutação Y→D
    i_yd  = np.where(
        t < t_yd,
        _envelope(I_dol / 3.0, tau_e),
        _envelope(I_dol * 0.7, tau_e * 0.5),   # pico menor no segundo transitório
    )

    # Soft-Starter: rampa de tensão de 0 → V em t_ramp
    t_ramp = t_acc * 0.8
    v_ramp = np.clip(t / t_ramp, 0.0, 1.0)
    i_ss   = _envelope(I_dol * v_ramp, tau_e * 0.4) * v_ramp
    i_ss   = np.maximum(i_ss, I_nom * v_ramp)

    # Seleção de métodos
    metodos = st.multiselect(
        "Métodos de partida",
        options=["DOL (Direta)", "Estrela-Triângulo (Y-D)", "Soft-Starter"],
        default=["DOL (Direta)", "Estrela-Triângulo (Y-D)", "Soft-Starter"],
        key="th_partidas_sel",
    )

    col_dol = "#f87171" if dark else "#dc2626"
    col_yd  = "#4f8ef7" if dark else "#1d4ed8"
    col_ss  = "#34d399" if dark else "#059669"

    fig = go.Figure()

    if "DOL (Direta)" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_dol, mode="lines", name="DOL",
                                 line=dict(color=col_dol, width=2.5)))
    if "Estrela-Triângulo (Y-D)" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_yd, mode="lines", name="Y-D",
                                 line=dict(color=col_yd, width=2.5, dash="dash")))
        fig.add_vline(x=t_yd, line_dash="dot", line_color=col_yd, line_width=1,
                      annotation_text="Y→D", annotation_font_color=col_yd)
    if "Soft-Starter" in metodos:
        fig.add_trace(go.Scatter(x=t, y=i_ss, mode="lines", name="Soft-Starter",
                                 line=dict(color=col_ss, width=2.5, dash="longdash")))

    # Linha de corrente nominal
    fig.add_hline(y=I_nom, line_dash="dot", line_color=pt["fg"], line_width=1.2,
                  annotation_text=f"I_nom ≈ {I_nom:.1f} A",
                  annotation_font_color=pt["fg"])

    fig.update_layout(
        height=340,
        title=dict(text="Comparativo de Partidas — Corrente de Fase (modelo analítico)",
                   x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"])),
        paper_bgcolor=pt["paper_bg"], plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=45),
        xaxis=dict(title="Tempo (s)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        yaxis=dict(title="Corrente de fase (A)", showgrid=True, gridcolor=pt["grid"],
                   tickfont=dict(size=10, color=pt["fg"])),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18,
                    font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ─────────────────────────────────────────────────────────────────────────────
# 4. TRANSFORMADA DE PARK DINÂMICA — plano vetorial + séries temporais
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Gerando animação…")
def _build_gif_park(ref: str, dark: bool) -> tuple[bytes, str]:
    """GIF animado da transformada de Clarke (αβ) ou Park (dq). Resultado cacheado."""
    import tempfile, os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    import matplotlib.gridspec as gridspec

    bg_hex   = "#151a24" if dark else "#ffffff"
    fg_hex   = "#e5e7eb" if dark else "#111111"
    grid_hex = "#2a2a3a" if dark else "#dddddd"
    col_a    = "#4f8ef7" if dark else "#1d4ed8"   # componente α ou d
    col_b    = "#f87171" if dark else "#dc2626"    # componente β ou q
    col_vec  = "#f97316"                            # vetor resultante

    # s didático para o referencial rotórico — grande o suficiente para completar
    # o loop em poucos ciclos: 1 volta do vetor = 1/s ciclos de ωe
    s_typ = 0.5   # → loop completo em 2 ciclos de ωe

    # Frames: para o rotórico cobrir exatamente 1 volta do vetor (= 1/s ciclos de ωe)
    # garantindo loop perfeito; os outros modos usam 1 ciclo de ωe.
    n_cycles = round(1.0 / s_typ) if ref == "rotor" else 1
    N    = 60 * n_cycles
    t    = np.linspace(0.0, float(n_cycles), N, endpoint=False)  # ciclos de ωe
    th_e = 2.0 * np.pi * t                                        # ângulo elétrico

    # Vetor de tensão no referencial fixo αβ — gira sempre a ωe
    Vs_a = np.cos(th_e)   # componente α
    Vs_b = np.sin(th_e)   # componente β

    if ref == "dq":
        # Eixos dq giram junto com o vetor → vetor parece parado no plano dq.
        # Mostramos: plano αβ com vetor girando + eixos dq girando junto.
        # Séries: Vqs = cte, Vds = 0.
        Vx = np.zeros(N)   # Vds
        Vz = np.ones(N)    # Vqs
        lbl_x_curto, lbl_z_curto = "Vds", "Vqs"
        lbl_x = "Vds  (eixo direto — alinhado com o fluxo)"
        lbl_z = "Vqs  (eixo em quadratura — 90° do fluxo)"
        lbl_ax_x = "α  (eixo estacionário horizontal)"
        lbl_ax_y = "β  (eixo estacionário vertical, 90° de α)"
        titulo = "Park — referencial dq (síncrono)"
        desc   = ("No referencial dq, os eixos d e q giram a ωe junto com o vetor de tensão (laranja). "
                  "Por isso Vqs = constante e Vds = 0 em regime — o vetor parece parado.")
        modo = "dq"
    elif ref == "rotor":
        # Eixos giram a ωr = (1−s)·ωe → vetor do estator oscila a s·ωe no plano rotórico.
        th_r = 2.0 * np.pi * s_typ * t
        Vx = np.cos(th_r)
        Vz = np.sin(th_r)
        lbl_x_curto, lbl_z_curto = "Vdr", "Vqr"
        lbl_x = "Vdr  (componente direta — solidária ao rotor)"
        lbl_z = "Vqr  (componente em quadratura — 90° de Vdr)"
        lbl_ax_x = "dr  (eixo direto — solidário ao rotor)"
        lbl_ax_y = "qr  (eixo em quadratura — 90° de dr)"
        titulo = f"Referencial rotórico — vetor do estator gira a s·ωe  (s={s_typ} ilustrativo)"
        desc   = (f"No referencial do rotor, os eixos giram a ωr = (1−s)·ωe. "
                  f"O vetor de tensão do estator (laranja) oscila à frequência de escorregamento fs = s·fe. "
                  f"Em motores reais s ≈ 0,02–0,08; s={s_typ} é usado aqui para tornar a animação visível.")
        modo = "rotor"
    else:
        # Referencial αβ fixo: vetor gira a ωe, eixos parados.
        Vx = Vs_a
        Vz = Vs_b
        lbl_x_curto, lbl_z_curto = "Vα", "Vβ"
        lbl_x = "Vα  (componente horizontal — eixo estacionário)"
        lbl_z = "Vβ  (componente vertical — 90° de Vα)"
        lbl_ax_x = "α  (eixo estacionário horizontal)"
        lbl_ax_y = "β  (eixo estacionário vertical, 90° de α)"
        titulo = "Clarke — referencial αβ (estacionário)"
        desc   = ("No referencial αβ, os eixos são fixos no espaço. "
                  "O vetor de tensão (laranja) gira a ωe: "
                  "Vα e Vβ são senoidais com 90° de defasagem entre si.")
        modo = "ab"

    fig_m = plt.figure(figsize=(11.0, 6.0), facecolor=bg_hex)
    gs    = gridspec.GridSpec(1, 2, width_ratios=[1, 1.3], wspace=0.4,
                              left=0.07, right=0.97, top=0.88, bottom=0.38)
    ax_v  = fig_m.add_subplot(gs[0])   # plano vetorial
    ax_t  = fig_m.add_subplot(gs[1])   # séries temporais

    # ── estilo base ───────────────────────────────────────────────────────────
    for ax in (ax_v, ax_t):
        ax.set_facecolor(bg_hex)
        for sp in ax.spines.values():
            sp.set_color(grid_hex)
        ax.tick_params(colors=fg_hex, labelsize=10)

    # ── plano vetorial ────────────────────────────────────────────────────────
    circ = np.linspace(0, 2 * np.pi, 200)
    ax_v.plot(np.cos(circ), np.sin(circ), color=grid_hex, lw=0.8, ls="--")
    ax_v.set_xlim(-1.5, 1.5); ax_v.set_ylim(-1.5, 1.5)
    ax_v.set_aspect("equal")
    ax_v.set_title(titulo, color=fg_hex, fontsize=11, pad=6)
    ax_v.plot(0, 0, "o", color=fg_hex, ms=3, zorder=5)

    ax_v.set_ylabel(lbl_ax_y, color=fg_hex, fontsize=10)
    # xlabel do plano vetorial omitido — informação está na legenda das projeções

    if modo == "dq":
        # Eixos fixos αβ em cinza claro, eixos dq girantes coloridos
        ax_v.axhline(0, color=grid_hex, lw=0.5)
        ax_v.axvline(0, color=grid_hex, lw=0.5)
        # Eixos dq girantes
        axd_line, = ax_v.plot([], [], color=col_a, lw=1.2, ls="-")
        axq_line, = ax_v.plot([], [], color=col_b, lw=1.2, ls="-")
        axd_lbl   = ax_v.text(0, 0, "d", color=col_a, fontsize=10, ha="center", va="center")
        axq_lbl   = ax_v.text(0, 0, "q", color=col_b, fontsize=10, ha="center", va="center")
    else:
        ax_v.axhline(0, color=grid_hex, lw=0.6)
        ax_v.axvline(0, color=grid_hex, lw=0.6)

    # Vetor principal (laranja) — sempre mostra o vetor no plano αβ ou rotórico
    vec_x = Vs_a if modo in ("dq", "ab") else Vx
    vec_z = Vs_b if modo in ("dq", "ab") else Vz
    arr = ax_v.annotate("", xy=(vec_x[0], vec_z[0]), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=col_vec,
                                        lw=2.2, mutation_scale=14))
    # Legenda manual para o vetor laranja e projeções
    ax_v.plot([], [], color=col_vec, lw=2, label="V (vetor de tensão)")
    if modo == "dq":
        ax_v.plot([], [], color=col_a, lw=1.2, label="eixo d")
        ax_v.plot([], [], color=col_b, lw=1.2, label="eixo q")
    ax_v.plot([], [], "o", color=col_a, ms=4, label=f"projeção em {lbl_x_curto}")
    ax_v.plot([], [], "o", color=col_b, ms=4, label=f"projeção em {lbl_z_curto}")
    ax_v.legend(fontsize=9, framealpha=0, labelcolor=fg_hex,
                loc="upper center", bbox_to_anchor=(0.5, -0.22),
                ncol=2, handlelength=1.2)

    dot_a, = ax_v.plot([], [], "o", color=col_a, ms=4, zorder=6)
    dot_b, = ax_v.plot([], [], "o", color=col_b, ms=4, zorder=6)

    # ── séries temporais ──────────────────────────────────────────────────────
    ax_t.set_xlim(0, float(n_cycles)); ax_t.set_ylim(-1.4, 1.4)
    ax_t.set_xlabel("Ciclos de ωe", color=fg_hex, fontsize=10)
    ax_t.set_ylabel("Amplitude (p.u.)", color=fg_hex, fontsize=10)
    ax_t.plot(t, Vx, color=col_a, lw=1.2, ls="--", alpha=0.35)
    ax_t.plot(t, Vz, color=col_b, lw=1.2, ls="--", alpha=0.35)
    ax_t.legend([lbl_x, lbl_z], fontsize=9, framealpha=0,
                labelcolor=fg_hex, loc="upper center",
                bbox_to_anchor=(0.5, -0.22), ncol=1, handlelength=1.2)

    line_a, = ax_t.plot([], [], color=col_a, lw=1.8)
    line_b, = ax_t.plot([], [], color=col_b, lw=1.8, ls="--")
    cur_a,  = ax_t.plot([], [], "o", color=col_a, ms=5)
    cur_b,  = ax_t.plot([], [], "o", color=col_b, ms=5)
    vline,  = ax_t.plot([], [], color=fg_hex, lw=0.8, ls=":")

    def _update(i):
        # Vetor laranja no plano vetorial
        arr.set_position((0, 0))
        arr.xy = (vec_x[i], vec_z[i])
        # Projeções nos eixos
        dot_a.set_data([vec_x[i]], [0])
        dot_b.set_data([0], [vec_z[i]])
        # Eixos dq girantes (só no modo dq)
        if modo == "dq":
            d_x, d_y = 1.3 * np.cos(th_e[i]), 1.3 * np.sin(th_e[i])
            q_x, q_y = 1.3 * np.cos(th_e[i] + np.pi/2), 1.3 * np.sin(th_e[i] + np.pi/2)
            axd_line.set_data([-d_x, d_x], [-d_y, d_y])
            axq_line.set_data([-q_x, q_x], [-q_y, q_y])
            axd_lbl.set_position((d_x * 0.85, d_y * 0.85))
            axq_lbl.set_position((q_x * 0.85, q_y * 0.85))
        # Séries temporais
        line_a.set_data(t[:i+1], Vx[:i+1])
        line_b.set_data(t[:i+1], Vz[:i+1])
        cur_a.set_data([t[i]], [Vx[i]])
        cur_b.set_data([t[i]], [Vz[i]])
        vline.set_data([t[i], t[i]], [-1.4, 1.4])
        if modo == "dq":
            return arr, dot_a, dot_b, axd_line, axq_line, axd_lbl, axq_lbl, line_a, line_b, cur_a, cur_b, vline
        return arr, dot_a, dot_b, line_a, line_b, cur_a, cur_b, vline

    ani = animation.FuncAnimation(fig_m, _update, frames=N, interval=50, blit=True)

    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ani.save(tmp_path, writer="pillow", dpi=100)
        plt.close(fig_m)
        with open(tmp_path, "rb") as f:
            gif_bytes = f.read()
    finally:
        os.unlink(tmp_path)

    return gif_bytes, desc


def render_park_dinamico() -> None:
    """GIF animado da transformada de Clarke/Park — vetor girante + séries temporais."""
    dark = _dark()

    ref = st.radio(
        "Referencial",
        options=["dq (síncrono — Park)", "rotórico (ωref = ωr)", "αβ (estacionário — Clarke)"],
        horizontal=True,
        key="th_park_ref",
    )
    if ref.startswith("dq"):
        ref_key = "dq"
    elif ref.startswith("rot"):
        ref_key = "rotor"
    else:
        ref_key = "ab"

    import base64
    gif_bytes, desc = _build_gif_park(ref_key, dark)
    b64 = base64.b64encode(gif_bytes).decode()
    st.markdown(
        f'<img src="data:image/gif;base64,{b64}" '
        f'style="display:block;margin:auto;max-width:100%;">',
        unsafe_allow_html=True,
    )
    st.caption(desc)


# ─────────────────────────────────────────────────────────────────────────────
# 5. FLUXO DE POTÊNCIA — barras horizontais com slider Plotly (zero latência)
# ─────────────────────────────────────────────────────────────────────────────

def render_sankey_potencia() -> None:
    """Fluxo de potência com slider nativo Plotly (zero latência).

    go.Sankey não suporta frames Plotly; substituído por barras horizontais
    empilhadas (go.Bar) que representam o mesmo fluxo e animam normalmente.
    Pré-calcula N_STEPS valores de s; slider JS troca frames sem rerun.
    """
    mp   = _get_mp()
    dark = _dark()
    pt   = _plot_theme(dark)

    N_STEPS = 80
    s_grid  = np.linspace(-0.20, 2.00, N_STEPS)
    nom_idx = int(np.argmin(np.abs(s_grid - 0.05)))

    def _fmt(v: float) -> str:
        av = abs(v)
        return f"{v/1000:.2f} kW" if av >= 1000 else f"{v:.1f} W"

    COL_PIN  = "#4f8ef7"
    COL_CU1  = "#f87171"
    COL_AG   = "#a78bfa"
    COL_CU2  = "#fb923c"
    COL_MEC  = "#34d399"
    COL_OUT  = "#22c55e"

    LABELS = ["P_entrada", "P_cu1 (cobre est.)", "P_ag (entreferro)",
              "P_cu2 (cobre rot.)", "P_mec (conv.)", "P_saída"]

    def _make_frame_data(s: float):
        fp     = calc_fluxo_potencia(s, mp)
        P_in   = fp["P_in"]
        P_cu1  = fp["P_cu1"]
        P_ag   = fp["P_ag"]
        P_cu2  = fp["P_cu2"]
        P_mec  = fp["P_mec"]
        P_out  = fp["P_out"]
        region = fp["region"]
        eta    = fp["eta"]

        vals   = [abs(P_in), abs(P_cu1), abs(P_ag), abs(P_cu2), abs(P_mec), abs(P_out)]
        cols   = [COL_PIN, COL_CU1, COL_AG, COL_CU2, COL_MEC, COL_OUT]
        txts   = [_fmt(P_in), _fmt(P_cu1), _fmt(P_ag),
                  _fmt(P_cu2), _fmt(P_mec), _fmt(P_out)]

        traces = []
        for i, (lbl, val, col, txt) in enumerate(zip(LABELS, vals, cols, txts)):
            traces.append(go.Bar(
                name=lbl,
                x=[val],
                y=["Potência"],
                orientation="h",
                marker_color=col,
                text=[txt],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=11, color="#ffffff"),
                hovertemplate=f"{lbl}: {txt}<extra></extra>",
            ))

        # trace final: título dinâmico como anotação via scatter invisível
        traces.append(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(opacity=0),
            showlegend=False,
            hoverinfo="skip",
            name=f"{region} | η={eta:.1f}% | s={s:.3f}",
        ))
        return traces, region, eta

    # ── figura base ──────────────────────────────────────────────────────────
    init_traces, region_0, eta_0 = _make_frame_data(s_grid[nom_idx])
    fig = go.Figure(data=init_traces)

    # ── frames ───────────────────────────────────────────────────────────────
    frames = []
    slider_steps = []
    anim_args = dict(mode="immediate", frame=dict(duration=0, redraw=True),
                     transition=dict(duration=0))

    for i, s in enumerate(s_grid):
        trs, region, eta = _make_frame_data(s)
        frames.append(go.Frame(
            name=str(i),
            data=trs,
            traces=list(range(len(trs))),
        ))
        slider_steps.append(dict(
            method="animate",
            label=f"{s:.2f}",
            args=[[str(i)], anim_args],
        ))

    fig.frames = frames

    fig.update_layout(
        height=260,
        barmode="stack",
        title=dict(
            text=f"Fluxo de Potência — {region_0}  |  η = {eta_0:.1f}%  |  s = {s_grid[nom_idx]:.2f}",
            x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=20, r=20, t=55, b=110),
        xaxis=dict(
            title="Potência (W)", showgrid=True, gridcolor=pt["grid"],
            tickfont=dict(size=10, color=pt["fg"]),
        ),
        yaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=-0.28,
            font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        sliders=[dict(
            active=nom_idx,
            currentvalue=dict(
                prefix="Escorregamento  s = ",
                visible=True, xanchor="center",
                font=dict(size=13, color=pt["fg"]),
            ),
            y=0, pad=dict(t=45, b=5),
            len=0.92, x=0.04,
            steps=slider_steps,
            bgcolor=pt["paper_bg"], bordercolor=pt["grid"],
            tickcolor=pt["fg"], font=dict(color=pt["fg"], size=9),
        )],
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )

    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ─────────────────────────────────────────────────────────────────────────────
# 6. CIRCUITO EQUIVALENTE ALTERNÁVEL — Completo (com Rfe) vs. IEEE (sem Rfe)
# ─────────────────────────────────────────────────────────────────────────────

def _palette_theory(dark: bool) -> dict[str, str]:
    if dark:
        return dict(muted="#8892b0", text="#e4e8f5", accent="#4f8ef7",
                    border="#2a3150", surface="#161b27")
    return dict(muted="#4b5563", text="#111827", accent="#2563eb",
                border="#d0d8f0", surface="#ffffff")


@st.cache_data(show_spinner="Gerando circuito…")
def _build_circuit_png(mp_key: tuple, dark: bool, simplified: bool) -> bytes:
    """Gera os bytes PNG do circuito equivalente (cacheável)."""
    # Reconstrói um objeto compatível com build_figure a partir da chave
    class _MP:
        pass
    mp_obj = _MP()
    (mp_obj.Vl, mp_obj.f, mp_obj.Rs, mp_obj.Rr,
     mp_obj.Xm, mp_obj.Xls, mp_obj.Xlr, rfe_real, mp_obj.p) = mp_key
    mp_obj.Rfe = 1e9 if simplified else rfe_real  # Rfe → ∞ remove o ramo shunt

    bg_hex = "#0d1117" if dark else "#ffffff"
    with matplotlib.rc_context({"mathtext.fontset": "dejavusans", "text.usetex": False}):
        fig = build_figure(mp_obj, dark, _palette_theory)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=bg_hex, bbox_inches="tight")
        plt.close(fig)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 7. DESEQUILÍBRIO DE TENSÃO — senoidais com slider δ (amplitude) + Δf (freq)
# ─────────────────────────────────────────────────────────────────────────────

def render_fasorial_desequilibrio() -> None:
    """Formas de onda Va/Vb/Vc com desequilíbrio de amplitude e frequência.

    Grid 2D de N_D × N_F frames Plotly pré-calculados (zero latência).
    Slider 1 — δ: desequilíbrio de amplitude em Va (+δ) e Vc (−δ).
    Slider 2 — Δf: desvio de frequência em Vc (Hz), Vb permanece nominal.
    VUF calculado via Fortescue nos fasores em t=0, exibido como anotação.
    """
    dark = _dark()
    pt   = _plot_theme(dark)
    mp   = _get_mp()
    f0   = float(mp.f)   # frequência nominal (Hz)

    N_D = 31   # passos de δ: −30% → +30%
    N_F = 21   # passos de Δf: −10 Hz → +10 Hz

    delta_grid = np.linspace(-0.30, 0.30, N_D)
    df_grid    = np.linspace(-10.0, 10.0, N_F)
    nom_d_idx  = N_D // 2  # δ = 0 no centro
    nom_f_idx  = N_F // 2  # Δf = 0 no centro

    # eixo de tempo: 2 ciclos nominais, 400 pontos
    T0  = 1.0 / f0
    t   = np.linspace(0.0, 2 * T0, 400)

    col_Va = "#f97316"
    col_Vb = "#4f8ef7" if dark else "#1d4ed8"
    col_Vc = "#34d399" if dark else "#059669"
    col_vuf = "#f87171"

    a_rot = np.exp(1j * 2 * np.pi / 3)
    F_mat = np.array([
        [1, 1,        1       ],
        [1, a_rot,    a_rot**2],
        [1, a_rot**2, a_rot**4],
    ]) / 3.0

    def _make_traces(delta: float, df: float):
        fc = f0 + df
        Va_t = (1.0 + delta) * np.sin(2 * np.pi * f0 * t)
        Vb_t =                  np.sin(2 * np.pi * f0 * t - 2 * np.pi / 3)
        Vc_t = (1.0 - delta) * np.sin(2 * np.pi * fc * t + 2 * np.pi / 3)

        # VUF via fasores em t=0 (pico normalizado)
        Va_f = complex(1.0 + delta, 0.0)
        Vb_f = a_rot**2
        Vc_f = (1.0 - delta) * np.exp(1j * (4 * np.pi / 3))
        _, V1s, V2s = F_mat @ np.array([Va_f, Vb_f, Vc_f])
        vuf = abs(V2s) / abs(V1s) * 100 if abs(V1s) > 1e-9 else 0.0

        t_ms = (t * 1000).tolist()
        return [
            go.Scatter(x=t_ms, y=Va_t.tolist(), mode="lines",
                       name="Va", line=dict(color=col_Va, width=2.5)),
            go.Scatter(x=t_ms, y=Vb_t.tolist(), mode="lines",
                       name="Vb", line=dict(color=col_Vb, width=2.5)),
            go.Scatter(x=t_ms, y=Vc_t.tolist(), mode="lines",
                       name=f"Vc  (f = {fc:.1f} Hz)", line=dict(color=col_Vc, width=2.5)),
            go.Scatter(
                x=[t_ms[-1] * 0.72], y=[1.25],
                mode="text",
                text=[f"VUF = {vuf:.1f}%"],
                textfont=dict(size=14, color=col_vuf),
                showlegend=False,
            ),
        ]

    # ── figura base ──────────────────────────────────────────────────────────
    fig = go.Figure(data=_make_traces(0.0, 0.0))

    # ── frames 2D ────────────────────────────────────────────────────────────
    frames = []
    anim_args = dict(mode="immediate", frame=dict(duration=0, redraw=True),
                     transition=dict(duration=0))

    for i_d, delta in enumerate(delta_grid):
        for i_f, df in enumerate(df_grid):
            frames.append(go.Frame(
                name=str(i_d * N_F + i_f),
                data=_make_traces(delta, df),
                traces=[0, 1, 2, 3],
            ))
    fig.frames = frames

    # slider δ — percorre amplitude, Δf fixo em 0
    steps_delta = [
        dict(method="animate", label=f"{d*100:+.0f}",
             args=[[str(i_d * N_F + nom_f_idx)], anim_args])
        for i_d, d in enumerate(delta_grid)
    ]

    # slider Δf — percorre frequência, δ fixo em 0
    steps_df = [
        dict(method="animate", label=f"{df:+.0f}",
             args=[[str(nom_d_idx * N_F + i_f)], anim_args])
        for i_f, df in enumerate(df_grid)
    ]

    slider_base = dict(
        len=0.88, x=0.06,
        bgcolor=pt["paper_bg"], bordercolor=pt["grid"], tickcolor=pt["fg"],
        font=dict(color=pt["fg"], size=9),
    )

    y_max = (1.0 + max(abs(delta_grid[0]), abs(delta_grid[-1]))) * 1.15

    fig.update_layout(
        height=560,
        title=dict(
            text="Desequilíbrio de Tensão — Formas de Onda Va / Vb / Vc",
            x=0.5, xanchor="center", font=dict(size=13, color=pt["fg"]),
        ),
        paper_bgcolor=pt["paper_bg"],
        plot_bgcolor=pt["plot_bg"],
        font=dict(family="Inter, system-ui", size=11, color=pt["fg"]),
        margin=dict(l=60, r=20, t=55, b=20),
        xaxis=dict(
            title="Tempo (ms)", showgrid=True, gridcolor=pt["grid"],
            zeroline=False, tickfont=dict(size=10, color=pt["fg"]),
            domain=[0, 1],
        ),
        yaxis=dict(
            title="Tensão (p.u.)", showgrid=True, gridcolor=pt["grid"],
            zeroline=True, zerolinecolor=pt["grid"],
            range=[-y_max, y_max],
            tickfont=dict(size=10, color=pt["fg"]),
            domain=[0.44, 1.0],
        ),
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=0.36,
            font=dict(size=10, color=pt["fg"]), bgcolor="rgba(0,0,0,0)",
        ),
        sliders=[
            dict(**slider_base,
                 active=nom_d_idx,
                 y=0.22,
                 pad=dict(t=20, b=0),
                 currentvalue=dict(
                     prefix="Desequilíbrio de amplitude  δ = ", suffix="%",
                     visible=True, xanchor="center",
                     font=dict(size=12, color=pt["fg"]),
                 ),
                 steps=steps_delta),
            dict(**slider_base,
                 active=nom_f_idx,
                 y=0.06,
                 pad=dict(t=20, b=0),
                 currentvalue=dict(
                     prefix="Desvio de frequência em Vc  Δf = ", suffix=" Hz",
                     visible=True, xanchor="center",
                     font=dict(size=12, color=pt["fg"]),
                 ),
                 steps=steps_df),
        ],
        updatemenus=[dict(
            type="buttons", visible=False,
            buttons=[dict(method="animate", args=[None])],
        )],
    )

    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def render_circuito_alternavel() -> None:
    """Circuito equivalente alternável: Completo (com Rfe) ↔ Simplificado IEEE (sem Rfe)."""
    mp   = _get_mp()
    dark = _dark()

    modo = st.radio(
        "Modelo de circuito",
        options=["Completo — com $R_{fe}$", "Simplificado IEEE — sem $R_{fe}$"],
        horizontal=True,
        key="th_circ_modo",
    )
    simplified = "IEEE" in modo

    mp_key = (
        float(mp.Vl), float(mp.f), float(mp.Rs), float(mp.Rr),
        float(mp.Xm), float(mp.Xls), float(mp.Xlr),
        float(getattr(mp, "Rfe", 500.0)), int(mp.p),
    )
    png_bytes = _build_circuit_png(mp_key, dark, simplified)
    st.image(png_bytes, use_container_width=True)

    if simplified:
        st.markdown(
            r"**Equação de malha** — ramo $R_{fe}$ removido ($R_{fe} \to \infty$, circuito aberto):"
        )
        st.latex(
            r"Z_{total} = R_s + jX_{ls} + jX_m \,\Big\|\,"
            r"\!\left(jX_{lr} + \tfrac{R_r}{s}\right)"
        )
        st.markdown(
            "Simplificação válida quando $P_{fe} \\lesssim 2\\%\\,P_{nom}$. "
            "O rendimento é calculado separadamente sem perder precisão."
        )
    else:
        st.markdown(r"**Equação de malha** — modelo completo com perdas no ferro:")
        st.latex(
            r"Z_{total} = R_s + jX_{ls} + "
            r"\left(jX_m \,\Big\|\, R_{fe}\right) \,\Big\|\,"
            r"\!\left(jX_{lr} + \tfrac{R_r}{s}\right)"
        )
