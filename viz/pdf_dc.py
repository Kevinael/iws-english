# -*- coding: utf-8 -*-
"""
pdf_dc.py — Relatório Técnico MCC do IWS Simulator.

Perfil: mesmo estilo visual de pdf_academico.py, adaptado para MCC.
Exporta: generate_dc(exp_label, mp, res, ...) -> bytes
"""

from __future__ import annotations
import datetime
import numpy as np

from core.dc_machine_model import DCMachineParams
from viz.pdf_commons import (
    safe_text, embed_fig,
    cell_rich, render_rich,
    build_curves_fig, fig_to_png_bytes, make_pdf_class,
)


_EXC_LABELS: dict[str, str] = {
    "sep_motor":    "Excitação Separada — Motor",
    "shunt_motor":  "Shunt (Paralelo) — Motor",
    "series_motor": "Série — Motor",
    "sep_gen":      "Excitação Separada — Gerador",
    "shunt_gen":    "Shunt (Paralelo) — Gerador",
}


# ─────────────────────────────────────────────────────────────────────────────
# Primitivos de layout (espelham pdf_academico.py)
# ─────────────────────────────────────────────────────────────────────────────

def _sec(pdf, title: str, num: str = "") -> None:
    pdf.set_fill_color(22, 54, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    label = f"  {num}  {title}" if num else f"  {title}"
    pdf.cell(0, 8, label, border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _subsec(pdf, title: str) -> None:
    pdf.set_fill_color(220, 228, 248)
    pdf.set_text_color(20, 30, 80)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"   {title}", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _body(pdf, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, text)
    pdf.ln(1)


def _caption(pdf, text: str) -> None:
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, text, border=0, align="C")
    pdf.ln(2)


def _th(pdf, cols: list[tuple[str, float]]) -> None:
    pdf.set_fill_color(200, 210, 245)
    pdf.set_text_color(20, 20, 80)
    x0, y0 = pdf.get_x(), pdf.get_y()
    for lbl, w in cols:
        cell_rich(pdf, f"  {lbl}", w, 6, main_size=9,
                  fill_rgb=(200, 210, 245), text_rgb=(20, 20, 80))
    pdf.set_xy(x0, y0 + 6)
    pdf.ln(0)


def _tr(pdf, rows: list[tuple], widths: list[float], aligns: list[str]) -> None:
    for idx, row in enumerate(rows):
        fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
        x0, y0 = pdf.get_x(), pdf.get_y()
        for cell, w in zip(row, widths):
            cell_rich(pdf, f"  {str(cell)}", w, 6, main_size=9,
                      fill_rgb=fill, text_rgb=(40, 40, 40))
        pdf.set_xy(x0, y0 + 6)
        pdf.ln(0)


def _banner(pdf, text: str) -> None:
    _ensure_space(pdf, 20)
    pdf.set_fill_color(15, 40, 100)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"  {text}", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _ensure_space(pdf, mm: float) -> None:
    if (pdf.h - pdf.b_margin) - pdf.get_y() < mm:
        pdf.add_page()


# ─────────────────────────────────────────────────────────────────────────────
# Gráfico de barras de perdas DC
# ─────────────────────────────────────────────────────────────────────────────

def _build_losses_bar_dc(losses: dict) -> object:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = []
    values = []
    pcts   = []

    labels.append("P. Joule R_a")
    values.append(losses.get("P_Ra", 0.0))
    pcts.append(losses.get("pct_Ra", 0.0))

    if losses.get("P_Rf", 0.0) > 0:
        labels.append("P. Joule R_f")
        values.append(losses["P_Rf"])
        pcts.append(losses.get("pct_Rf", 0.0))

    labels.append("P. Atrito")
    values.append(losses.get("P_mec", 0.0))
    pcts.append(losses.get("pct_mec", 0.0))

    labels.append("P. Mecânica útil")
    values.append(losses.get("P_mec_out", 0.0))
    pcts.append(losses.get("pct_mec_out", 0.0))

    COLORS = ["#1d4ed8", "#ea580c", "#16a34a", "#7c3aed"]
    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.7 * len(labels))))
    fig.patch.set_facecolor("white")
    bars = ax.barh(labels, values, color=COLORS[:len(labels)], height=0.55)
    for bar, pct in zip(bars, pcts):
        w = bar.get_width()
        ax.text(w * 1.01, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%", va="center", fontsize=8, color="#374151")
    ax.set_xlabel("Potência (W)", fontsize=8)
    ax.set_facecolor("#f9fafc")
    ax.grid(True, axis="x", color="#dde4f5", linewidth=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    fig.subplots_adjust(left=0.22, right=0.92, top=0.94, bottom=0.14)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo de perdas DC
# ─────────────────────────────────────────────────────────────────────────────

def _compute_losses_dc(res: dict, mp: DCMachineParams) -> dict:
    ia_ss  = float(res.get("ia_ss",  0.0))
    ifd_ss = float(res.get("ifd_ss", 0.0))
    wm_ss  = float(res.get("wm_ss",  0.0))
    Te_ss  = float(res.get("Te_ss",  0.0))
    Va     = mp.Va if mp else 0.0
    Ra     = mp.Ra if mp else 0.0
    Rf     = mp.Rf if mp else 0.0
    B      = mp.B  if mp else 0.0
    exc    = mp.excitation if mp else "sep_motor"

    P_Ra      = ia_ss ** 2 * Ra
    P_Rf      = ifd_ss ** 2 * Rf if exc not in ("series_motor",) else 0.0
    P_mec     = B * wm_ss ** 2
    P_mec_out = abs(Te_ss) * abs(wm_ss)
    P_elec    = abs(Va) * abs(ia_ss)

    total = max(P_elec, 1e-9)
    return {
        "P_Ra":        P_Ra,
        "P_Rf":        P_Rf,
        "P_mec":       P_mec,
        "P_mec_out":   P_mec_out,
        "P_elec":      P_elec,
        "pct_Ra":      P_Ra      / total * 100,
        "pct_Rf":      P_Rf      / total * 100,
        "pct_mec":     P_mec     / total * 100,
        "pct_mec_out": P_mec_out / total * 100,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bloco de diagnóstico DC
# ─────────────────────────────────────────────────────────────────────────────

def _compute_anomalias_dc(res: dict, mp: DCMachineParams) -> list[tuple[str, str, str]]:
    ia_arr  = np.asarray(res.get("ia",  [0.0]))
    wm_arr  = np.asarray(res.get("wm",  [0.0]))
    ifd_arr = np.asarray(res.get("ifd", [0.0]))
    ia_ss   = float(res.get("ia_ss",  0.0))
    ifd_ss  = float(res.get("ifd_ss", 0.0))
    wm_ss   = float(res.get("wm_ss",  0.0))
    exc     = mp.excitation if mp else "sep_motor"
    anomalias: list[tuple[str, str, str]] = []

    ia_max = float(np.max(np.abs(ia_arr)))
    if ia_max > 15.0 * max(abs(ia_ss), 1e-6):
        anomalias.append((
            "CRÍTICO",
            "Sobrecorrente extrema na partida",
            f"Pico {ia_max:.1f} A = {ia_max/max(abs(ia_ss),1e-6):.0f}x regime. "
            "Use resistência série ou reduza Va.",
        ))

    if not res.get("success", True):
        anomalias.append((
            "CRÍTICO",
            "Falha numérica do integrador",
            "Reduza h para 1e-5 s ou verifique parâmetros.",
        ))

    if exc not in ("series_motor",) and len(ifd_arr) > 10:
        ifd_std = float(np.std(ifd_arr[len(ifd_arr) // 2:]))
        if ifd_std > 0.05 * max(abs(ifd_ss), 1e-6):
            anomalias.append((
                "ALERTA",
                "Instabilidade de campo",
                f"σ(ifd) = {ifd_std:.4f} A em regime. "
                "Verifique Rf e Lf.",
            ))

    if len(wm_arr) > 10 and float(np.mean(wm_arr[-10:])) < 0.01 * abs(wm_ss) and abs(wm_ss) > 1:
        anomalias.append((
            "ALERTA",
            "Regime não atingido",
            "ωm ainda em transitório ao fim da simulação. Aumente tmax.",
        ))

    return anomalias


# ─────────────────────────────────────────────────────────────────────────────
# Bloco principal de simulação
# ─────────────────────────────────────────────────────────────────────────────

def _write_sim_block_dc(
    pdf,
    res: dict,
    mp: DCMachineParams,
    exp_label: str,
    exp_type: str,
    t_events: list,
    var_keys: list,
    var_labels: list,
    tmax: float,
    h: float,
) -> None:
    exc    = mp.excitation if mp else "sep_motor"
    is_gen = exc in ("sep_gen", "shunt_gen")
    losses = _compute_losses_dc(res, mp)
    sec_n  = 1

    # ── Capa ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(15, 40, 100)
    pdf.rect(0, 0, 210, 65, style="F")
    pdf.set_xy(20, 14)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS - Relatorio Tecnico de Simulacao",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 30)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Motor de Corrente Continua (MCC)",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 42)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Experimento: {safe_text(exp_label)}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 50)
    pdf.cell(0, 6, f"Configuracao: {safe_text(_EXC_LABELS.get(exc, exc))}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 57)
    pdf.set_font("Helvetica", "I", 9)
    ts = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M")
    pdf.cell(0, 6, f"Gerado em: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── 1. Identificação ──────────────────────────────────────────────────
    _sec(pdf, "Identificação do Experimento", f"{sec_n}.")
    _th(pdf, [("Atributo", 90), ("Valor", 80)])
    _tr(pdf, [
        ("Experimento",                       safe_text(exp_label)),
        ("Tipo de operação",                  exp_type.upper()),
        ("Configuração de excitação",         safe_text(_EXC_LABELS.get(exc, exc))),
        ("Tensão de armadura (Va)",           f"{mp.Va:.1f} V"),
        ("Tempo total simulado",              f"{tmax:.3f} s"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 2. Parâmetros da Máquina ──────────────────────────────────────────
    _sec(pdf, "Parâmetros da Máquina", f"{sec_n}.")
    rows_params = [
        ("Resistência de armadura (R[sub]a[/sub])",    f"{mp.Ra:.4f}", "Ω"),
        ("Indutância de armadura (L[sub]a[/sub])",     f"{mp.La:.6f}", "H"),
        ("Constante eletromecânica (k[sub]b[/sub])",   f"{mp.kb:.6f}", "V·s/rad"),
        ("Momento de inércia (J)",                      f"{mp.J:.4f}",  "kg·m²"),
        ("Coeficiente de atrito (B)",                   f"{mp.B:.6f}",  "N·m·s/rad"),
        ("Torque de carga nominal (T[sub]load[/sub])",  f"{mp.Tload:.4f}", "N·m"),
    ]
    if exc == "sep_motor":
        rows_params += [
            ("Tensão de campo (V[sub]f[/sub])",         f"{mp.Vf:.1f}",  "V"),
            ("Resistência de campo (R[sub]f[/sub])",    f"{mp.Rf:.4f}",  "Ω"),
            ("Indutância de campo (L[sub]f[/sub])",     f"{mp.Lf:.6f}",  "H"),
        ]
    elif exc in ("shunt_motor", "shunt_gen"):
        rows_params += [
            ("Resistência de campo shunt (R[sub]f[/sub])", f"{mp.Rf:.4f}", "Ω"),
            ("Indutância de campo shunt (L[sub]f[/sub])",  f"{mp.Lf:.6f}", "H"),
            ("(V[sub]f[/sub] = V[sub]a[/sub] — excitação paralela)",
             f"{mp.Va:.1f}", "V"),
        ]
    elif exc == "series_motor":
        rows_params += [
            ("Resistência de campo série (R[sub]f[/sub])", f"{mp.Rf:.4f}", "Ω"),
            ("Indutância de campo série (L[sub]f[/sub])",  f"{mp.Lf:.6f}", "H"),
            ("(Campo em série com a armadura)", "—", ""),
        ]
    elif exc == "sep_gen":
        rows_params += [
            ("Tensão de campo (V[sub]f[/sub])",         f"{mp.Vf:.1f}",  "V"),
            ("Resistência de campo (R[sub]f[/sub])",    f"{mp.Rf:.4f}",  "Ω"),
            ("Indutância de campo (L[sub]f[/sub])",     f"{mp.Lf:.6f}",  "H"),
            ("Resistência de carga (R[sub]l[/sub])",    f"{mp.Rl:.4f}",  "Ω"),
            ("Indutância de carga (L[sub]l[/sub])",     f"{mp.Ll:.6f}",  "H"),
        ]
    _th(pdf, [("Parâmetro", 100), ("Valor", 45), ("Unidade", 25)])
    _tr(pdf, rows_params, [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)

    # ── 2.1 Circuito Equivalente ──────────────────────────────────────────
    try:
        from viz.eqcircuit_plotter_dc_v2 import build_circuit_png_dc
        _ensure_space(pdf, 90)
        _subsec(pdf, f"{sec_n}.1  Circuito Equivalente — {_EXC_LABELS.get(exc, exc)}")
        pdf.ln(1)
        circuit_bytes = build_circuit_png_dc(mp, dark=False)
        embed_fig(pdf, circuit_bytes, width_mm=170)
        _caption(pdf,
            f"Figura — Circuito equivalente do MCC com excitação {_EXC_LABELS.get(exc, exc).lower()}. "
            "Ra: resistência de armadura; La: indutância de armadura; "
            "Ea: força contra-eletromotriz; kb: constante eletromecânica.")
        pdf.ln(3)
    except Exception:
        pass

    sec_n += 1

    # ── 3. Indicadores de Regime Permanente ──────────────────────────────
    pdf.add_page()
    _sec(pdf, "Indicadores de Regime Permanente", f"{sec_n}.")
    n_ss   = float(res.get("n_ss",   0.0))
    wm_ss  = float(res.get("wm_ss",  0.0))
    Te_ss  = float(res.get("Te_ss",  0.0))
    ia_ss  = float(res.get("ia_ss",  0.0))
    ifd_ss = float(res.get("ifd_ss", 0.0))
    Ea_ss  = float(res.get("Ea_ss",  0.0))
    Vt_ss  = float(res.get("Vt_ss",  0.0))

    P_elec    = losses["P_elec"]
    P_mec_out = losses["P_mec_out"]
    eta = (P_mec_out / max(P_elec, 1e-9) * 100) if not is_gen \
        else (P_elec / max(P_mec_out, 1e-9) * 100)

    rows_ss = [
        ("Velocidade de regime (n)",                              f"{n_ss:.3f}",  "RPM"),
        ("Velocidade angular do rotor (ω[sub]m[/sub])",          f"{wm_ss:.4f}", "rad/s"),
        ("Torque eletromagnético de regime (T[sub]e[/sub])",     f"{Te_ss:.4f}", "N·m"),
        ("Torque eletromagnético máximo",                        f"{float(np.max(res.get('Te', [Te_ss]))):.4f}", "N·m"),
        ("Corrente de armadura de regime (i[sub]a[/sub])",       f"{ia_ss:.4f}", "A"),
        ("Corrente de armadura de pico",                         f"{float(np.max(np.abs(res.get('ia', [ia_ss])))):.4f}", "A"),
        ("Força contra-eletromotriz (E[sub]a[/sub])",            f"{Ea_ss:.4f}", "V"),
        ("Tensão de terminal (V[sub]t[/sub])",                   f"{Vt_ss:.4f}", "V"),
        ("Potência elétrica (P[sub]elec[/sub])",                 f"{P_elec:.3f}", "W"),
        ("Potência mecânica útil (P[sub]mec[/sub])",             f"{P_mec_out:.3f}", "W"),
        ("Rendimento (η)",                                       f"{eta:.2f}",   "%"),
    ]
    if exc not in ("series_motor",):
        rows_ss.insert(5, (
            "Corrente de campo de regime (i[sub]fd[/sub])",
            f"{ifd_ss:.4f}", "A",
        ))
    _th(pdf, [("Grandeza", 105), ("Valor", 45), ("Unidade", 20)])
    _tr(pdf, rows_ss, [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 4. Balanço de Perdas ──────────────────────────────────────────────
    _ensure_space(pdf, 100)
    _sec(pdf, "Balanço de Perdas (Regime Permanente)", f"{sec_n}.")
    rows_loss = [
        ("Perdas no cobre da armadura (P[sub]Ra[/sub])",
         f"{losses['P_Ra']:.4f}", "W", f"{losses['pct_Ra']:.1f}%"),
    ]
    if losses["P_Rf"] > 1e-9:
        rows_loss.append((
            "Perdas no cobre de campo (P[sub]Rf[/sub])",
            f"{losses['P_Rf']:.4f}", "W", f"{losses['pct_Rf']:.1f}%",
        ))
    rows_loss += [
        ("Perdas por atrito (P[sub]atrito[/sub])",
         f"{losses['P_mec']:.4f}",     "W", f"{losses['pct_mec']:.1f}%"),
        ("Potência mecânica útil (P[sub]mec[/sub])",
         f"{losses['P_mec_out']:.4f}", "W", f"{losses['pct_mec_out']:.1f}%"),
    ]
    _th(pdf, [("Componente", 95), ("Valor", 35), ("Unidade", 18), ("% de P[sub]elec[/sub]", 22)])
    _tr(pdf, rows_loss, [95, 35, 18, 22], ["L", "R", "L", "R"])
    pdf.ln(2)
    embed_fig(pdf, fig_to_png_bytes(_build_losses_bar_dc(losses)), width_mm=170)
    _caption(pdf,
        "Distribuição percentual das perdas em regime permanente "
        "em relação à potência elétrica de entrada.")
    pdf.ln(2)
    sec_n += 1

    # ── 5. Curvas Transientes ─────────────────────────────────────────────
    dc_curve_keys   = ["ia", "wm", "Te"]
    dc_curve_labels = ["i_a (A)", "ω_m (rad/s)", "T_e (N·m)"]
    if exc not in ("series_motor",) and "ifd" in res:
        dc_curve_keys.append("ifd")
        dc_curve_labels.append("i_fd (A)")

    if var_keys:
        merged_keys   = [k for k in dc_curve_keys if k in var_keys or k in res]
        merged_labels = [dc_curve_labels[dc_curve_keys.index(k)]
                         if k in dc_curve_keys else k
                         for k in merged_keys]
    else:
        merged_keys   = dc_curve_keys
        merged_labels = dc_curve_labels

    if merged_keys:
        pdf.add_page()
        _sec(pdf, "Curvas Transientes", f"{sec_n}.")
        curves_fig = build_curves_fig(res, merged_keys, merged_labels, t_events or [])
        embed_fig(pdf, fig_to_png_bytes(curves_fig), width_mm=170)
        _caption(pdf,
            "Evolução temporal das grandezas eletromecânicas durante a simulação.")
        import matplotlib.pyplot as plt
        plt.close(curves_fig)
    sec_n += 1

    # ── 6. Diagnóstico e Observações ─────────────────────────────────────
    _ensure_space(pdf, 40)
    _sec(pdf, "Diagnóstico e Observações", f"{sec_n}.")
    anomalias = _compute_anomalias_dc(res, mp)
    _COLORS_D = {"CRÍTICO": (220, 38, 38), "ALERTA": (217, 119, 6), "INFO": (22, 163, 74)}
    if not anomalias:
        pdf.set_fill_color(22, 163, 74)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, "  Nenhuma anomalia detectada.", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        _th(pdf, [("Severidade", 30), ("Título", 85), ("Descrição", 55)])
        for sev, titulo, desc in anomalias:
            r_, g_, b_ = _COLORS_D.get(sev, (80, 80, 80))
            fill = (242, 245, 255) if anomalias.index((sev, titulo, desc)) % 2 == 0 else (255, 255, 255)
            cell_rich(pdf, f"  {safe_text(sev)}", 30, 6, main_size=9,
                      fill_rgb=(r_, g_, b_), text_rgb=(255, 255, 255))
            cell_rich(pdf, f"  {safe_text(titulo)}", 85, 6, main_size=9,
                      fill_rgb=fill, text_rgb=(40, 40, 40))
            cell_rich(pdf, f"  {safe_text(desc)}", 55, 6, main_size=9,
                      fill_rgb=fill, text_rgb=(40, 40, 40))
            pdf.ln(0)
            x0 = pdf.get_x()
            pdf.set_xy(x0, pdf.get_y() + 6)
    sec_n += 1

    # ── 7. Parâmetros do Integrador ───────────────────────────────────────
    _ensure_space(pdf, 55)
    _sec(pdf, "Parâmetros do Integrador Numérico (LSODA)", f"{sec_n}.")
    t_arr  = np.asarray(res.get("t", [0.0, 1.0]))
    n_pts  = len(t_arr)
    dt_eff = float(t_arr[-1] - t_arr[0]) / max(n_pts - 1, 1)
    _th(pdf, [("Parâmetro", 115), ("Valor", 55)])
    _tr(pdf, [
        ("Passo de amostragem solicitado (h)",       f"{h:.6f} s"),
        ("Passo efetivo médio",                      f"{dt_eff:.6f} s"),
        ("Total de pontos de saída",                 str(n_pts)),
        ("Duração total simulada (t[sub]max[/sub])", f"{tmax:.3f} s"),
        ("Número de estados",                        "4 (ωm, ia, ifd/ψf)"),
    ], [115, 55], ["L", "L"])
    _body(pdf,
          "  Integrador: LSODA (scipy.integrate.solve_ivp), controle adaptativo "
          "de passo, RTOL = 1e-5, ATOL = 1e-7.")
    pdf.ln(3)


# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────

def generate_dc(
    exp_label: str,
    mp: DCMachineParams,
    res: dict,
    var_keys: list[str] | None = None,
    var_labels: list[str] | None = None,
    t_events: list | None = None,
    exp_type: str = "dol",
    tmax: float = 0.0,
    h: float = 1e-4,
) -> bytes:
    """Gera relatório técnico MCC em PDF e retorna como bytes."""
    var_keys   = var_keys   or []
    var_labels = var_labels or []
    t_events   = t_events   or []

    PDF = make_pdf_class("MCC")
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_top_margin(20)

    _write_sim_block_dc(
        pdf, res, mp, exp_label, exp_type,
        t_events, var_keys, var_labels, tmax, h,
    )

    return bytes(pdf.output())
