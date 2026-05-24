# -*- coding: utf-8 -*-
"""
pdf_academico.py — Relatório Acadêmico do IWS Simulator.

Perfil: rigor científico, equacionamento, curvas completas, todas as referências salvas.
Exporta: generate_academico(exp_label, mp, res, ..., ref_list) -> bytes
"""

from __future__ import annotations
import datetime
import numpy as np

from core.IWS_PY import MachineParams
from viz.pdf_commons import (
    safe_text, fmt_power, embed_fig, build_circuit_bytes,
    cell_rich, render_rich,
    compute_trip_class, compute_thd_harmonics, compute_energy_metrics,
    compute_losses, compute_integrator_params, compute_broken_bar,
    make_chunks, build_abc_currents_fig, build_losses_bar_fig,
    build_curves_fig, fig_to_png_bytes, make_pdf_class,
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
# Bloco de simulação — escreve todas as seções para um resultado
# ─────────────────────────────────────────────────────────────────────────────

def _write_sim_block(
    pdf,
    res: dict, mp: MachineParams, exp_label: str, exp_type: str,
    t_events: list, var_keys: list, var_labels: list,
    energy_tariff: float, tmax: float, h: float,
    insights: list | None, load_torque: float,
    banner_label: str = "",
) -> None:
    losses     = compute_losses(res, mp)
    integrator = compute_integrator_params(res, mp, tmax, h)
    broken_bar = compute_broken_bar(res, mp)
    sec_n = 1

    # ── Capa do bloco ─────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(15, 40, 100)
    pdf.rect(0, 0, 210, 65, style="F")
    pdf.set_xy(20, 14)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS — Relatorio Tecnico de Simulacao",
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
    _tr(pdf, [
        ("Experimento",                       exp_label),
        ("Tipo de partida/operação",           exp_type.upper()),
        ("Velocidade síncrona",                f"{mp.n_sync:.1f} RPM"),
        ("Frequência nominal",                 f"{mp.f:.1f} Hz"),
        ("Número de polos",                    str(mp.p)),
        ("Tensão de linha (V[sub]l[/sub])",    f"{mp.Vl:.1f} V"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 2. Parâmetros da Máquina ──────────────────────────────────────────
    _sec(pdf, "Parâmetros da Máquina", f"{sec_n}.")
    _th(pdf, [("Parâmetro", 100), ("Valor", 45), ("Unidade", 25)])
    _tr(pdf, [
        ("Resistência do estator (R[sub]s[/sub])",             f"{mp.Rs:.4f}", "Ohm"),
        ("Resistência do rotor (R[sub]r[/sub])",               f"{mp.Rr:.4f}", "Ohm"),
        ("Reatância de magnetização (X[sub]m[/sub])",          f"{mp.Xm:.4f}", "Ohm"),
        ("Reatância de dispersão do estator (X[sub]ls[/sub])", f"{mp.Xls:.4f}", "Ohm"),
        ("Reatância de dispersão do rotor (X[sub]lr[/sub])",   f"{mp.Xlr:.4f}", "Ohm"),
        ("Resistência de perdas no ferro (R[sub]fe[/sub])",    f"{mp.Rfe:.1f}", "Ohm"),
        ("Momento de inércia (J)",                              f"{mp.J:.4f}", "kg.m2"),
        ("Coeficiente de atrito (B)",                           f"{mp.B:.4f}", "N.m.s/rad"),
    ], [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)

    _ensure_space(pdf, 85)
    _subsec(pdf, f"{sec_n}.1  Circuito Equivalente Monofásico em T")
    pdf.ln(1)
    embed_fig(pdf, build_circuit_bytes(mp), width_mm=170)
    _caption(pdf,
        "Figura — Circuito equivalente monofásico em T do Motor de Indução Trifásico. "
        "Rs: resistência do estator; Xls: reatância de dispersão do estator; "
        "Xm: reatância de magnetização; Rfe: resistência de perdas no ferro; "
        "Xlr: reatância de dispersão do rotor; Rr/s: resistência do rotor referida ao estator."
    )
    pdf.ln(3)
    sec_n += 1

    # ── 3. Indicadores de Regime Permanente ──────────────────────────────
    pdf.add_page()
    _sec(pdf, "Indicadores de Regime Permanente", f"{sec_n}.")
    P_gap  = float(res.get("P_gap",  0.0))
    P_mec  = float(res.get("P_mec",  0.0))
    P_cu_r = float(res.get("P_cu_r", 0.0))
    P_in   = float(res.get("P_in",   0.0))
    s_val  = float(res.get("s",      0.0))
    eta    = float(res.get("eta",    0.0))
    vi, ui   = fmt_power(P_in)
    vg, ug   = fmt_power(P_gap)
    vm, um   = fmt_power(P_mec)
    vcr, ucr = fmt_power(P_cu_r)
    _th(pdf, [("Grandeza", 105), ("Valor", 45), ("Unidade", 20)])
    _tr(pdf, [
        ("Velocidade de regime",                                   f"{res['n_ss']:.3f}",                     "RPM"),
        ("Velocidade angular do rotor (ω[sub]r[/sub])",           f"{res['wr_ss']:.4f}",                    "rad/s"),
        ("Torque eletromagnético de regime (T[sub]e[/sub])",      f"{res['Te_ss']:.4f}",                    "N.m"),
        ("Torque eletromagnético máximo (T[sub]e,max[/sub])",     f"{float(np.max(res['Te'])):.4f}",        "N.m"),
        ("Escorregamento (s)",                                     f"{s_val*100:.3f}",                       "%"),
        ("Corrente de linha eficaz (I[sub]as,rms[/sub])",         f"{res['ias_rms']:.4f}",                  "A"),
        ("Corrente de pico (I[sub]as,pk[/sub])",                  f"{float(np.max(np.abs(res['ias']))):.4f}", "A"),
        ("Potência de entrada (P[sub]in[/sub])",                   vi, ui),
        ("Potência no entreferro (P[sub]gap[/sub])",               vg, ug),
        ("Potência mecânica (P[sub]mec[/sub])",                    vm, um),
        ("Perdas no cobre do rotor (P[sub]cu,r[/sub])",           vcr, ucr),
        ("Rendimento (eta)",                                       f"{eta:.3f}",                             "%"),
    ], [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)
    sec_n += 1

    # ── 5. Balanço de Perdas ──────────────────────────────────────────────
    _ensure_space(pdf, 100)
    _sec(pdf, "Balanço de Perdas (Regime Permanente)", f"{sec_n}.")
    lf, uf   = fmt_power(losses["P_cu_s"])
    lg, ug_  = fmt_power(losses["P_cu_r"])
    lh, uh   = fmt_power(losses["P_fe"])
    li, ui_  = fmt_power(max(losses["P_mec"], 0.0))
    _th(pdf, [("Componente", 100), ("Valor", 38), ("Unidade", 18), ("% de P[sub]in[/sub]", 24)])
    _tr(pdf, [
        ("Perdas no cobre do estator (P[sub]cu,s[/sub])", lf,  uf,  f"{losses['pct_cu_s']:.1f}%"),
        ("Perdas no cobre do rotor (P[sub]cu,r[/sub])",   lg,  ug_, f"{losses['pct_cu_r']:.1f}%"),
        ("Perdas no ferro (P[sub]fe[/sub])",               lh,  uh,  f"{losses['pct_fe']:.1f}%"),
        ("Potência mecânica útil (P[sub]mec[/sub])",       li,  ui_, f"{losses['pct_mec']:.1f}%"),
    ], [100, 38, 18, 24], ["L", "R", "L", "R"])
    pdf.ln(2)
    embed_fig(pdf, fig_to_png_bytes(build_losses_bar_fig(losses)), width_mm=170)
    _caption(pdf, "Distribuição percentual das perdas em regime permanente em relação à potência de entrada.")
    pdf.ln(2)
    sec_n += 1

    # ── 6. Integrador Numérico ────────────────────────────────────────────
    _ensure_space(pdf, 55)
    _sec(pdf, "Parâmetros do Integrador Numérico (LSODA)", f"{sec_n}.")
    ny_ok = integrator["nyquist_ok"]
    ny_status = ("Satisfeito (>= 10 amostras/ciclo)"
                 if ny_ok else "ATENCAO: insuficiente — RMS e FFT podem ser imprecisos")
    _th(pdf, [("Parâmetro", 115), ("Valor", 55)])
    _tr(pdf, [
        ("Passo de amostragem solicitado (h)",                  f"{integrator['h_req']:.6f} s"),
        ("Passo efetivo médio",                                  f"{integrator['dt_eff']:.6f} s"),
        ("Amostras por ciclo (fn / hef)",                        f"{integrator['samples_per_cycle']:.1f}"),
        ("Total de pontos de saída",                             str(integrator["n_steps"])),
        ("Duração total simulada (t[sub]max[/sub])",            f"{integrator['tmax']:.3f} s"),
        ("Critério de Nyquist",                                  ny_status),
    ], [115, 55], ["L", "L"])
    _body(pdf,
        "  Integrador: LSODA (scipy.integrate.solve_ivp), controle adaptativo "
        "de passo, RTOL = 1e-5, ATOL = 1e-6.")
    pdf.ln(3)
    sec_n += 1

    # ── 7. MCSA — Barra Quebrada ──────────────────────────────────────────
    if broken_bar is not None:
        _ensure_space(pdf, 60)
        _sec(pdf, "Indicadores de Falha — Barra Quebrada (MCSA)", f"{sec_n}.")
        _subsec(pdf, "Análise Espectral de Corrente (Motor Current Signature Analysis)")
        _th(pdf, [("Indicador", 115), ("Valor", 55)])
        _tr(pdf, [
            ("Severidade (alpha)",                              f"{broken_bar['alpha']:.3f}"),
            ("Classificação de severidade",                     broken_bar["severity_label"]),
            ("Escorregamento em regime (s)",                    f"{broken_bar['s_val']*100:.3f} %"),
            ("Frequência lateral inferior (1-2s)f",            f"{broken_bar['f_lo']:.2f} Hz"),
            ("Frequência lateral superior (1+2s)f",            f"{broken_bar['f_hi']:.2f} Hz"),
            ("Amplitude relativa (1-2s)f / fundamental",       f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Amplitude relativa (1+2s)f / fundamental",       f"{broken_bar['sb_ratio_hi']:.2f} %"),
        ], [115, 55], ["L", "L"])
        _body(pdf,
            "Referência: IEEE 1159-2019 — MCSA. "
            "Amplitude relativa > 3% indica falha incipiente; > 10% indica falha severa.")
        pdf.ln(2)
        sec_n += 1

    # ── 8. Qualidade de Energia e Análise Econômica ───────────────────────
    if exp_type != "shutdown":
        em = compute_energy_metrics(res, mp, energy_tariff)
        _ensure_space(pdf, 60)
        _sec(pdf, "Qualidade de Energia e Análise Econômica", f"{sec_n}.")
        thd_ok = em["thd"] <= 5.0
        fp_ok  = em["fp"] >= 0.85
        _th(pdf, [("Grandeza", 110), ("Valor", 40), ("Status / Unidade", 20)])
        _tr(pdf, [
            ("Fator de Potência (FP)",                    f"{em['fp']:.4f}",           "OK" if fp_ok else "BAIXO"),
            ("THD de corrente (I[sub]as[/sub])",          f"{em['thd']:.2f} %",        "OK" if thd_ok else "ALTO"),
            ("Energia consumida no experimento",          f"{em['E_kwh']:.6f}",         "kWh"),
            ("Custo do experimento",                      f"R$ {em['custo_exp']:.4f}", "R$"),
            ("Potência de entrada em regime",             f"{em['P_in_kw']:.3f}",       "kW"),
            ("Rendimento em regime permanente",           f"{em['eta']:.2f}",           "%"),
            ("Custo operacional anual projetado (8760h)", f"R$ {em['custo_ano']:,.2f}", "R$/ano"),
        ], [110, 40, 20], ["L", "R", "L"])
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5,
                 f"  Tarifa: R$ {energy_tariff:.2f}/kWh. THD e FP calculados via FFT na janela de regime permanente.",
                 border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        harm_rows = compute_thd_harmonics(res, mp)
        if harm_rows:
            _ensure_space(pdf, 40)
            _subsec(pdf, "Espectro Harmônico de I[sub]as[/sub] — Ordens 1 a 9")
            _th(pdf, [("Ordem", 25), ("Frequência (Hz)", 45), ("Amplitude (A)", 55), ("Relativa (%)", 45)])
            _tr(pdf, [
                (f"{k}a", f"{fk:.1f}", f"{Ak:.4f}", f"{pct:.2f}")
                for k, fk, Ak, pct in harm_rows
            ], [25, 45, 55, 45], ["C", "R", "R", "R"])
            _body(pdf, "Amplitudes relativas normalizadas pela fundamental. Referência: IEEE 519-2022.")
            pdf.ln(2)
        sec_n += 1

    # ── 9. Trip Class ─────────────────────────────────────────────────────
    if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
        tc = compute_trip_class(res, mp)
        if tc is not None:
            _ensure_space(pdf, 40)
            _sec(pdf, "Recomendação de Proteção — Relé de Sobrecarga", f"{sec_n}.")
            tc_color = {10: (22, 163, 74), 20: (217, 119, 6), 30: (220, 38, 38)}
            r_, g_, b_ = tc_color.get(tc["class"], (80, 80, 80))
            pdf.set_fill_color(r_, g_, b_)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 8,
                     f"  Classe {tc['class']} — t_aceleracao = {tc['t_accel']:.2f} s "
                     f"(95% de {tc['n_sync']:.1f} RPM) — {tc['status']}",
                     border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
            _body(pdf, "Referência: IEC 60947-4-1 / NEMA ICS 2. "
                       "Classe 10: t < 10 s | Classe 20: 10-20 s | Classe 30: > 20 s.")
            pdf.ln(2)
            sec_n += 1

    # ── 10. Diagnóstico Automatizado ──────────────────────────────────────
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

    # ── 11. Correntes de Fase ABC ─────────────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        _ensure_space(pdf, 80)
        _sec(pdf, "Correntes de Fase ABC — Regime Permanente", f"{sec_n}.")
        embed_fig(pdf, fig_to_png_bytes(build_abc_currents_fig(res)), width_mm=170)
        ias_rms = float(res.get("ias_rms", 0.0))
        _caption(pdf,
            f"Correntes de fase ias, ibs, ics em regime permanente. "
            f"Tracejado: +/- RMS (Ias,rms = {ias_rms:.3f} A). "
            "Sistema equilibrado: amplitudes iguais, defasagem de 120 graus.")
        pdf.ln(2)
        sec_n += 1

    # ── 12. Curvas Características ────────────────────────────────────────
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _sec(pdf, f"Curvas Características{sfx}",
             f"{sec_n}." if pg == 0 else "")
        curves = build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig(pdf, fig_to_png_bytes(curves), width_mm=170)
        _caption(pdf, ", ".join(cl))


# ─────────────────────────────────────────────────────────────────────────────
# Seção comparativa — todas as referências sobrepostas
# ─────────────────────────────────────────────────────────────────────────────

def _write_comparative_section(
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
        embed_fig(pdf, fig_to_png_bytes(fig), width_mm=170)
        names = "Atual vs. " + ", ".join(r["label"] for r in chart_refs)
        _caption(pdf, names)


# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────

def generate_academico(
    exp_label: str,
    mp: MachineParams,
    res: dict,
    var_keys: list,
    var_labels: list | None = None,
    t_events: list | None = None,
    exp_type: str = "dol",
    ref_list: list | None = None,
    energy_tariff: float = 0.75,
    tmax: float = 0.0,
    h: float = 1e-3,
    insights: list | None = None,
    load_torque: float = 0.0,
) -> bytes:
    """Gera relatório acadêmico em PDF e retorna como bytes.

    Itera sobre simulação atual + todas as referências em ref_list.
    """
    var_labels = var_labels or var_keys
    t_events   = t_events   or []
    ref_list   = ref_list   or []

    PDF_CLS = make_pdf_class("Acadêmico")
    pdf = PDF_CLS()
    pdf.alias_nb_pages()
    pdf.set_margins(left=20, top=22, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)

    tmax_eff = tmax if tmax > 0 else (float(res["t"][-1]) if len(res.get("t", [])) > 0 else 1.0)

    # ── Bloco: simulação atual ────────────────────────────────────────────
    _write_sim_block(
        pdf, res, mp, exp_label, exp_type, t_events,
        var_keys, var_labels, energy_tariff, tmax_eff, h, insights, load_torque,
        banner_label="Simulação Atual",
    )

    # ── Bloco: cada referência salva ─────────────────────────────────────
    for ref_i, ref in enumerate(ref_list):
        ref_res = ref.get("res")
        if ref_res is None:
            continue
        ref_mp        = ref.get("mp", mp)
        ref_label     = ref.get("exp_label", f"Referência {ref_i+1}")
        ref_exp_type  = ref.get("exp_type", "dol")
        ref_t_events  = ref.get("t_events", [])
        ref_var_keys  = ref.get("var_keys") or var_keys
        ref_var_labels = ref.get("var_labels") or var_labels
        ref_tariff    = ref.get("energy_tariff", energy_tariff)
        ref_tmax      = ref.get("tmax", tmax_eff)
        ref_h         = ref.get("h", h)
        _write_sim_block(
            pdf, ref_res, ref_mp, ref_label, ref_exp_type, ref_t_events,
            ref_var_keys, ref_var_labels, ref_tariff, ref_tmax, ref_h,
            insights=None, load_torque=0.0,
            banner_label=f"Referência {ref_i+1} — {ref_label}",
        )

    # ── Seção final: gráficos sobrepostos ─────────────────────────────────
    if ref_list:
        _write_comparative_section(pdf, res, var_keys, var_labels, t_events, ref_list)

    return bytes(pdf.output())
