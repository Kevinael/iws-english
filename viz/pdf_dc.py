# -*- coding: utf-8 -*-
"""
pdf_dc.py — Relatório Acadêmico do DC Machine Simulator.

Perfil: rigor científico, equacionamento, curvas completas, todas as referências salvas.
Exporta: generate_dc_academico(exp_label, mp, res, ..., ref_list) -> bytes
"""

from __future__ import annotations
import datetime
import numpy as np

from viz.pdf_commons import (
    safe_text, fmt_power,
    cell_rich, fig_to_png_bytes,
    compute_energy_metrics, compute_losses, compute_integrator_params,
    make_chunks, build_losses_bar_fig, build_curves_fig, make_pdf_class,
)


# ─────────────────────────────────────────────────────────────────────────────
# Primitivos de layout — acadêmico
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
# Bloco de simulação — escreve todas as seções para um resultado DC
# ─────────────────────────────────────────────────────────────────────────────

def _write_dc_sim_block(
    pdf,
    res: dict, mp: dict, exp_label: str, exp_type: str,
    t_events: list, var_keys: list, var_labels: list,
    energy_tariff: float, tmax: float, h: float,
    insights: list | None,
    banner_label: str = "",
) -> None:
    losses     = compute_losses(res, mp)
    integrator = compute_integrator_params(res, mp, tmax, h)
    sec_n = 1

    # ── Capa do bloco ─────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(15, 40, 100)
    pdf.rect(0, 0, 210, 65, style="F")
    pdf.set_xy(20, 14)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "DC Machine — Relatório Técnico de Simulação",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 30)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Versao Academica Estruturada",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 44)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Experimento: {exp_label}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 54)
    pdf.set_font("Helvetica", "I", 9)
    ts = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M")
    pdf.cell(0, 6, f"Gerado em: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    if banner_label:
        _banner(pdf, banner_label)

    # ── 1. Identificação ──────────────────────────────────────────────────
    _sec(pdf, "Identificação do Experimento", f"{sec_n}.")
    _th(pdf, [("Atributo", 90), ("Valor", 80)])
    config_label = mp.get("config", "sep_motor").upper()
    _tr(pdf, [
        ("Experimento",                       exp_label),
        ("Tipo de configuração",              config_label),
        ("Modo de operação",                  exp_type.upper()),
        ("Tensão de armadura (V[sub]a[/sub])", f"{float(mp.get('Va', 0)):.1f} V"),
        ("Tensão de campo (V[sub]f[/sub])",   f"{float(mp.get('Vf', 0)):.1f} V"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 2. Parâmetros da Máquina ──────────────────────────────────────────
    _sec(pdf, "Parâmetros da Máquina", f"{sec_n}.")
    _th(pdf, [("Parâmetro", 100), ("Valor", 45), ("Unidade", 25)])
    _tr(pdf, [
        ("Resistência do campo (R[sub]f[/sub])",      f"{float(mp.get('Rf', 0)):.4f}", "Ohm"),
        ("Indutância do campo (L[sub]f[/sub])",       f"{float(mp.get('Lf', 0)):.6f}", "H"),
        ("Resistência da armadura (R[sub]a[/sub])",   f"{float(mp.get('Ra', 0)):.4f}", "Ohm"),
        ("Indutância da armadura (L[sub]a[/sub])",    f"{float(mp.get('La', 0)):.6f}", "H"),
        ("Constante de EMF reversa (k[sub]b[/sub])",  f"{float(mp.get('kb', 0)):.4f}", "V·s/rad"),
        ("Momento de inércia (J)",                      f"{float(mp.get('J', 0)):.4f}", "kg.m2"),
        ("Coeficiente de atrito (B)",                   f"{float(mp.get('B', 0)):.4f}", "N.m.s/rad"),
    ], [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 3. Indicadores de Regime Permanente ──────────────────────────────
    _ensure_space(pdf, 80)
    _sec(pdf, "Indicadores de Regime Permanente", f"{sec_n}.")
    P_in   = float(res.get("P_in", 0.0))
    P_mec  = float(res.get("P_mec", 0.0))
    eta    = float(res.get("eta", 0.0))
    vi, ui = fmt_power(P_in)
    vm, um = fmt_power(P_mec)
    _th(pdf, [("Grandeza", 105), ("Valor", 45), ("Unidade", 20)])
    _tr(pdf, [
        ("Velocidade de regime (n)",                        f"{res.get('n_ss', 0):.3f}",                    "RPM"),
        ("Velocidade angular do rotor (ω[sub]r[/sub])",    f"{res.get('wr_ss', 0):.4f}",                   "rad/s"),
        ("Torque eletromagnético de regime (T[sub]e[/sub])", f"{res.get('Te_ss', 0):.4f}",                  "N.m"),
        ("Torque eletromagnético máximo (T[sub]e,max[/sub])", f"{float(np.max(res.get('Te', [0]))):.4f}",  "N.m"),
        ("Corrente de armadura (I[sub]a,rms[/sub])",       f"{res.get('ia_rms', 0):.4f}",                   "A"),
        ("Corrente de campo (I[sub]f,rms[/sub])",          f"{res.get('ifd_rms', 0):.4f}",                  "A"),
        ("Potência de entrada (P[sub]in[/sub])",            vi, ui),
        ("Potência mecânica (P[sub]mec[/sub])",             vm, um),
        ("Rendimento (eta)",                                 f"{eta:.3f}",                                  "%"),
    ], [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 4. Balanço de Perdas ──────────────────────────────────────────────
    _ensure_space(pdf, 100)
    _sec(pdf, "Balanço de Perdas (Regime Permanente)", f"{sec_n}.")
    lf, uf   = fmt_power(losses["P_cu_s"])
    lg, ug_  = fmt_power(losses["P_cu_r"])
    li, ui_  = fmt_power(max(losses["P_mec"], 0.0))
    _th(pdf, [("Componente", 100), ("Valor", 38), ("Unidade", 18), ("% de P[sub]in[/sub]", 24)])
    _tr(pdf, [
        ("Perdas no cobre da armadura (P[sub]cu,a[/sub])", lf,  uf,  f"{losses['pct_cu_s']:.1f}%"),
        ("Perdas no cobre do campo (P[sub]cu,f[/sub])",    lg,  ug_, f"{losses['pct_cu_r']:.1f}%"),
        ("Potência mecânica útil (P[sub]mec[/sub])",       li,  ui_, f"{losses['pct_mec']:.1f}%"),
    ], [100, 38, 18, 24], ["L", "R", "L", "R"])
    pdf.ln(2)
    embed_fig_dc(pdf, fig_to_png_bytes(build_losses_bar_fig(losses)), width_mm=170)
    _caption(pdf, "Distribuição percentual das perdas em regime permanente em relação à potência de entrada.")
    pdf.ln(2)
    sec_n += 1

    # ── 5. Integrador Numérico ────────────────────────────────────────────
    _ensure_space(pdf, 55)
    _sec(pdf, "Parâmetros do Integrador Numérico (LSODA)", f"{sec_n}.")
    ny_ok = integrator["nyquist_ok"]
    ny_status = ("Satisfeito" if ny_ok else "ATENCAO: insuficiente")
    _th(pdf, [("Parâmetro", 115), ("Valor", 55)])
    _tr(pdf, [
        ("Passo de amostragem solicitado (h)",          f"{integrator['h_req']:.6f} s"),
        ("Passo efetivo médio",                          f"{integrator['dt_eff']:.6f} s"),
        ("Total de pontos de saída",                     str(integrator["n_steps"])),
        ("Duração total simulada (t[sub]max[/sub])",    f"{integrator['tmax']:.3f} s"),
        ("Critério de Nyquist",                          ny_status),
    ], [115, 55], ["L", "L"])
    _body(pdf,
        "  Integrador: LSODA (scipy.integrate.solve_ivp), controle adaptativo "
        "de passo, RTOL = 1e-5, ATOL = 1e-6.")
    pdf.ln(3)
    sec_n += 1

    # ── 6. Análise Energética ─────────────────────────────────────────────
    if exp_type != "shutdown":
        em = compute_energy_metrics(res, mp, energy_tariff)
        _ensure_space(pdf, 60)
        _sec(pdf, "Análise Energética", f"{sec_n}.")
        _th(pdf, [("Grandeza", 110), ("Valor", 40), ("Unidade", 20)])
        _tr(pdf, [
            ("Energia consumida no experimento",          f"{em['E_kwh']:.6f}",         "kWh"),
            ("Custo do experimento",                      f"R$ {em['custo_exp']:.4f}", "R$"),
            ("Potência de entrada em regime",             f"{em['P_in_kw']:.3f}",       "kW"),
            ("Rendimento em regime permanente",           f"{em['eta']:.2f}",           "%"),
            ("Custo operacional anual projetado (8760h)", f"R$ {em['custo_ano']:,.2f}", "R$/ano"),
        ], [110, 40, 20], ["L", "R", "L"])
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5,
                 f"  Tarifa: R$ {energy_tariff:.2f}/kWh.",
                 border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        sec_n += 1

    # ── 7. Diagnóstico Automatizado ──────────────────────────────────────
    if insights:
        _ensure_space(pdf, 40)
        _sec(pdf, "Diagnóstico Automatizado", f"{sec_n}.")
        _COLORS = {"error": (220, 38, 38), "warning": (217, 119, 6), "info": (22, 163, 74)}
        _LABELS = {"error": "ERRO", "warning": "ATENCAO", "info": "INFO"}
        for ins in insights:
            r_, g_, b_ = _COLORS.get(ins.level, (80, 80, 80))
            lbl_ = _LABELS.get(ins.level, ins.level.upper())
            pdf.set_fill_color(r_, g_, b_)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 7, f"  [{lbl_}]  {safe_text(ins.title)}", border=0, fill=True,
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"  {safe_text(ins.body)}", border=0)
            pdf.ln(2)
        sec_n += 1

    # ── 8. Curvas Características ────────────────────────────────────────
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _sec(pdf, f"Curvas Características{sfx}",
             f"{sec_n}." if pg == 0 else "")
        curves = build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig_dc(pdf, fig_to_png_bytes(curves), width_mm=170)
        _caption(pdf, ", ".join(cl))


# ─────────────────────────────────────────────────────────────────────────────
# Seção comparativa — todas as referências sobrepostas
# ─────────────────────────────────────────────────────────────────────────────

def _write_dc_comparative_section(
    pdf, res: dict, var_keys: list, var_labels: list,
    t_events: list, ref_list: list,
) -> None:
    chart_refs = [
        {
            "res":   r["res"],
            "color": r.get("color", "#888888"),
            "label": r.get("exp_label", "Referência"),
        }
        for r in ref_list if r.get("res") is not None
    ]
    if not chart_refs:
        return
    pdf.add_page()
    _banner(pdf, "Curvas Comparativas — Sobreposição Atual + Referências")
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        valid_k = [k for k in ck if k in res]
        if not valid_k:
            continue
        valid_l = [cl[ck.index(k)] for k in valid_k]
        if pg > 0:
            pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _sec(pdf, f"Curvas Comparativas{sfx}")
        fig = build_curves_fig(res, valid_k, valid_l, t_events,
                               color_offset=pg * 4, ref_list=chart_refs)
        embed_fig_dc(pdf, fig_to_png_bytes(fig), width_mm=170)
        names = "Atual vs. " + ", ".join(r["label"] for r in chart_refs)
        _caption(pdf, names)


# ─────────────────────────────────────────────────────────────────────────────
# Embutir figura (DC version)
# ─────────────────────────────────────────────────────────────────────────────

def embed_fig_dc(pdf, png_bytes: bytes, width_mm: float = 170) -> None:
    import tempfile
    import os
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        with open(tmp, "wb") as f:
            f.write(png_bytes)
        pdf.image(tmp, x=(210 - width_mm) / 2, w=width_mm)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────

def generate_dc_academico(
    exp_label: str,
    mp: dict,
    res: dict,
    var_keys: list,
    var_labels: list | None = None,
    t_events: list | None = None,
    exp_type: str = "sep_motor_dol",
    ref_list: list | None = None,
    energy_tariff: float = 0.75,
    tmax: float = 0.0,
    h: float = 1e-3,
    insights: list | None = None,
) -> bytes:
    """Gera relatório acadêmico para DC machine em PDF e retorna como bytes.

    Itera sobre simulação atual + todas as referências em ref_list.
    """
    var_labels = var_labels or var_keys
    t_events   = t_events   or []
    ref_list   = ref_list   or []

    PDF_CLS = make_pdf_class("DC Machine")
    pdf = PDF_CLS()
    pdf.alias_nb_pages()
    pdf.set_margins(left=20, top=22, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)

    tmax_eff = tmax if tmax > 0 else (float(res["t"][-1]) if len(res.get("t", [])) > 0 else 1.0)

    # ── Bloco: simulação atual ────────────────────────────────────────────
    _write_dc_sim_block(
        pdf, res, mp, exp_label, exp_type, t_events,
        var_keys, var_labels, energy_tariff, tmax_eff, h, insights,
        banner_label="Simulação Atual",
    )

    # ── Bloco: cada referência salva ─────────────────────────────────────
    for ref_i, ref in enumerate(ref_list):
        ref_res = ref.get("res")
        if ref_res is None:
            continue
        ref_mp        = ref.get("mp", mp)
        ref_label     = ref.get("exp_label", f"Referência {ref_i+1}")
        ref_exp_type  = ref.get("exp_type", "sep_motor_dol")
        ref_t_events  = ref.get("t_events", [])
        ref_var_keys  = ref.get("var_keys") or var_keys
        ref_var_labels = ref.get("var_labels") or var_labels
        ref_tariff    = ref.get("energy_tariff", energy_tariff)
        ref_tmax      = ref.get("tmax", tmax_eff)
        ref_h         = ref.get("h", h)
        _write_dc_sim_block(
            pdf, ref_res, ref_mp, ref_label, ref_exp_type, ref_t_events,
            ref_var_keys, ref_var_labels, ref_tariff, ref_tmax, ref_h,
            insights=None,
            banner_label=f"Referência {ref_i+1} — {ref_label}",
        )

    # ── Seção final: gráficos sobrepostos ─────────────────────────────────
    if ref_list:
        _write_dc_comparative_section(pdf, res, var_keys, var_labels, t_events, ref_list)

    return bytes(pdf.output())
