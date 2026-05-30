# -*- coding: utf-8 -*-
"""
pdf_industrial.py — Relatório Industrial do IWS Simulator.

Perfil: tomada de decisão, KPIs, diagnóstico de falhas, análise econômica.
Sem equacionamentos extensos. Todas as referências salvas incluídas.
Exporta: generate_industrial(exp_label, mp, res, ..., ref_list) -> bytes
"""

from __future__ import annotations
import datetime
import numpy as np

from core.IWS_PY import MachineParams
from viz.pdf_commons import (
    safe_text, fmt_power, embed_fig, build_circuit_bytes,
    cell_rich,
    compute_trip_class, compute_energy_metrics,
    compute_losses, compute_integrator_params, compute_broken_bar,
    make_chunks, build_abc_currents_fig, build_losses_bar_fig,
    build_curves_fig, fig_to_png_bytes, make_pdf_class,
)


# Paleta industrial
_BG_DARK  = (10, 30, 80)
_BG_CARD  = (240, 244, 255)
_ACCENT   = (29, 78, 216)
_TEXT_DRK = (15, 23, 42)
_TEXT_MID = (51, 65, 85)
_TEXT_LGT = (100, 116, 139)
_GREEN    = (22, 163, 74)
_RED      = (220, 38, 38)
_AMBER    = (217, 119, 6)


# ─────────────────────────────────────────────────────────────────────────────
# Primitivos de layout — industrial
# ─────────────────────────────────────────────────────────────────────────────

def _dash_title(pdf, title: str, subtitle: str = "") -> None:
    pdf.set_fill_color(*_BG_DARK)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, f"  {title}", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    if subtitle:
        pdf.set_fill_color(*_ACCENT)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, f"  {subtitle}", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _sec_bar(pdf, title: str) -> None:
    pdf.set_fill_color(*_ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, f"  {title}", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _kpi_row(pdf, items: list[tuple[str, str, str]]) -> None:
    n = len(items)
    if n == 0:
        return
    w = 170.0 / n
    x_start = pdf.get_x()
    y0 = pdf.get_y()
    for lbl, val, unit in items:
        x0 = pdf.get_x()
        pdf.set_fill_color(*_BG_CARD)
        pdf.cell(w, 14, "", border=0, fill=True)
        pdf.set_xy(x0 + 2, y0 + 1)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_TEXT_DRK)
        pdf.cell(w - 4, 6, val, border=0)
        pdf.set_xy(x0 + 2, y0 + 7)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_TEXT_MID)
        pdf.cell(w - 4, 5, f"{lbl} ({unit})", border=0)
        pdf.set_xy(x0 + w, y0)
    pdf.set_xy(x_start, y0 + 14)
    pdf.ln(2)


def _mini_table(pdf, rows: list[tuple], widths: list[float]) -> None:
    for idx, row in enumerate(rows):
        fill = (240, 244, 255) if idx % 2 == 0 else (255, 255, 255)
        x0, y0 = pdf.get_x(), pdf.get_y()
        for cell_val, w in zip(row, widths):
            cell_rich(pdf, f"  {str(cell_val)}", w, 6, main_size=9,
                      fill_rgb=fill, text_rgb=_TEXT_DRK)
        pdf.set_xy(x0, y0 + 6)
        pdf.ln(0)


def _badge(pdf, ok: bool, msg: str, warn: bool = False) -> None:
    color = _GREEN if ok else (_AMBER if warn else _RED)
    pdf.set_fill_color(*color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, f"  {msg}", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _ensure_space(pdf, mm: float) -> None:
    if (pdf.h - pdf.b_margin) - pdf.get_y() < mm:
        pdf.add_page()


def _banner(pdf, text: str) -> None:
    _ensure_space(pdf, 20)
    pdf.set_fill_color(*_BG_DARK)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"  {text}", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


# ─────────────────────────────────────────────────────────────────────────────
# Bloco de simulação — industrial
# ─────────────────────────────────────────────────────────────────────────────

def _write_sim_block(
    pdf,
    res: dict, mp: MachineParams, exp_label: str, exp_type: str,
    t_events: list, var_keys: list, var_labels: list,
    energy_tariff: float, tmax: float, h: float,
    insights: list | None,
    exp_config: dict | None = None,
    input_mode: str | None = None,
    is_main: bool = False,
) -> None:
    losses     = compute_losses(res, mp)
    integrator = compute_integrator_params(res, mp, tmax, h)
    broken_bar = compute_broken_bar(res, mp)

    # ── Capa executiva ────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_BG_DARK)
    pdf.rect(0, 0, 210, 58, style="F")
    pdf.set_xy(20, 12)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS SIMULATOR", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 28)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Relatório Industrial de Simulação",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 38)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Experimento: {exp_label}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 47)
    pdf.set_font("Helvetica", "I", 8)
    ts = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M")
    pdf.cell(0, 6, f"Gerado em: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── KPIs de Desempenho ────────────────────────────────────────────────
    _dash_title(pdf, "DESEMPENHO", f"Regime Permanente — {exp_type.upper()}")
    n_ss    = float(res.get("n_ss",    0.0))
    Te_ss   = float(res.get("Te_ss",   0.0))
    ias_rms = float(res.get("ias_rms", 0.0))
    eta     = float(res.get("eta",     0.0))
    s_val   = float(res.get("s",       0.0))
    P_in    = float(res.get("P_in",    0.0))
    v_pin, u_pin = fmt_power(P_in)
    _kpi_row(pdf, [
        ("Velocidade de Regime",   f"{n_ss:.1f}",    "RPM"),
        ("Torque de Regime Te",    f"{Te_ss:.2f}",   "N.m"),
        ("Corrente Eficaz Ias",    f"{ias_rms:.3f}", "A"),
        ("Rendimento eta",         f"{eta:.2f}",     "%"),
    ])
    _kpi_row(pdf, [
        ("Escorregamento s",       f"{s_val*100:.3f}", "%"),
        ("Potência de Entrada",    v_pin,              u_pin),
        ("Número de Polos p",      str(mp.p),          "—"),
        ("Tensão de Linha Vl",     f"{mp.Vl:.1f}",     "V"),
    ])

    # ── Balanço de Perdas ─────────────────────────────────────────────────
    _sec_bar(pdf, "BALANÇO DE PERDAS")
    embed_fig(pdf, fig_to_png_bytes(build_losses_bar_fig(losses)), width_mm=170)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_TEXT_LGT)
    vcs, ucs   = fmt_power(losses["P_cu_s"])
    vcr_, ucr_ = fmt_power(losses["P_cu_r"])
    vfe, ufe   = fmt_power(losses["P_fe"])
    pdf.cell(0, 5,
             f"  Pcu,s = {vcs} {ucs} ({losses['pct_cu_s']:.1f}%)  |  "
             f"Pcu,r = {vcr_} {ucr_} ({losses['pct_cu_r']:.1f}%)  |  "
             f"Pfe = {vfe} {ufe} ({losses['pct_fe']:.1f}%)",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Qualidade de Energia ──────────────────────────────────────────────
    if exp_type != "shutdown":
        em = compute_energy_metrics(res, mp, energy_tariff)
        _ensure_space(pdf, 55)
        _sec_bar(pdf, "QUALIDADE DE ENERGIA")
        thd_ok = em["thd"] <= 5.0
        fp_ok  = em["fp"] >= 0.85
        _badge(pdf, thd_ok and fp_ok,
               f"FP = {em['fp']:.3f} ({'OK >= 0.85' if fp_ok else 'BAIXO'})   |   "
               f"THD = {em['thd']:.2f}% ({'OK < 5%' if thd_ok else 'ALTO > 5%'})")
        _mini_table(pdf, [
            ("Energia consumida no experimento",  f"{em['E_kwh']:.6f} kWh"),
            ("Custo do experimento",              f"R$ {em['custo_exp']:.4f}"),
            ("Potência de entrada em regime",     f"{em['P_in_kw']:.3f} kW"),
            ("Rendimento em regime",              f"{em['eta']:.2f} %"),
        ], [105, 65])
        pdf.ln(2)

        # ── Análise Econômica ─────────────────────────────────────────────
        _ensure_space(pdf, 45)
        _sec_bar(pdf, "ANÁLISE ECONÔMICA")
        _mini_table(pdf, [
            ("Tarifa de energia",                 f"R$ {energy_tariff:.2f}/kWh"),
            ("Custo operacional anual (8760 h)",  f"R$ {em['custo_ano']:,.2f}"),
            ("Custo mensal estimado (730 h)",     f"R$ {em['P_in_kw'] * 730.0 * energy_tariff:,.2f}"),
        ], [105, 65])
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_TEXT_LGT)
        pdf.cell(0, 5, "  Projeção baseada em operação contínua à potência de regime permanente.",
                 border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ── Diagnóstico — Barra Quebrada ──────────────────────────────────────
    if broken_bar is not None:
        _ensure_space(pdf, 58)
        _sec_bar(pdf, "DIAGNÓSTICO — BARRA QUEBRADA (MCSA)")
        sev_ok = broken_bar["alpha"] < 0.2
        _badge(pdf, sev_ok,
               f"Severidade: {broken_bar['severity_label']} "
               f"(alpha = {broken_bar['alpha']:.3f})",
               warn=0.2 <= broken_bar["alpha"] < 0.5)
        _mini_table(pdf, [
            ("Frequência lateral inferior (1-2s)f",   f"{broken_bar['f_lo']:.2f} Hz"),
            ("Frequência lateral superior (1+2s)f",   f"{broken_bar['f_hi']:.2f} Hz"),
            ("Amplitude relativa (1-2s)f / fund.",    f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Amplitude relativa (1+2s)f / fund.",    f"{broken_bar['sb_ratio_hi']:.2f} %"),
            ("Escorregamento (s)",                    f"{broken_bar['s_val']*100:.3f} %"),
        ], [115, 55])
        pdf.ln(2)

    # ── Proteção — Trip Class ─────────────────────────────────────────────
    if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
        tc = compute_trip_class(res, mp)
        if tc is not None:
            _ensure_space(pdf, 45)
            _sec_bar(pdf, "RECOMENDAÇÃO DE PROTEÇÃO — RELÉ DE SOBRECARGA")
            _badge(pdf, tc["class"] == 10,
                   f"Classe {tc['class']} — t_aceleracao = {tc['t_accel']:.2f} s "
                   f"(95% de {tc['n_sync']:.1f} RPM) — {tc['status']}",
                   warn=tc["class"] == 20)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*_TEXT_LGT)
            pdf.cell(0, 5,
                     "  Referência: IEC 60947-4-1 / NEMA ICS 2. "
                     "Classe 10: t < 10 s | Classe 20: 10-20 s | Classe 30: > 20 s",
                     border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    # ── Diagnóstico Automatizado ──────────────────────────────────────────
    if insights:
        _ensure_space(pdf, 45)
        _sec_bar(pdf, "DIAGNÓSTICO AUTOMATIZADO")
        _COLORS = {"error": _RED, "warning": _AMBER, "info": _GREEN}
        _LABELS = {"error": "ERRO", "warning": "ATENCAO", "info": "INFO"}
        for ins in insights:
            r_, g_, b_ = _COLORS.get(ins.level, (80, 80, 80))
            lbl_ = _LABELS.get(ins.level, ins.level.upper())
            pdf.set_fill_color(r_, g_, b_)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 7, f"  [{lbl_}]  {safe_text(ins.title)}", border=0, fill=True,
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*_TEXT_DRK)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"  {safe_text(ins.body)}", border=0)
            pdf.ln(2)
        pdf.ln(2)

    # ── Integrador Numérico ───────────────────────────────────────────────
    _ensure_space(pdf, 52)
    _sec_bar(pdf, "INTEGRADOR NUMÉRICO (LSODA)")
    ny_ok = integrator["nyquist_ok"]
    _badge(pdf, ny_ok,
           "Critério de Nyquist: satisfeito (>= 10 amostras/ciclo)"
           if ny_ok else
           "ATENCAO: critério de Nyquist não satisfeito — RMS e FFT podem ser imprecisos")
    _mini_table(pdf, [
        ("Passo solicitado (h)",              f"{integrator['h_req']:.6f} s"),
        ("Passo efetivo médio",               f"{integrator['dt_eff']:.6f} s"),
        ("Amostras por ciclo",                f"{integrator['samples_per_cycle']:.1f}"),
        ("Total de pontos de saída",          str(integrator["n_steps"])),
        ("Duração total simulada (tmax)",     f"{integrator['tmax']:.3f} s"),
    ], [105, 65])
    pdf.ln(2)

    # ── Correntes de Fase ABC ─────────────────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        _ensure_space(pdf, 78)
        _sec_bar(pdf, "CORRENTES DE FASE ABC — REGIME PERMANENTE")
        embed_fig(pdf, fig_to_png_bytes(build_abc_currents_fig(res)), width_mm=170)
        pdf.ln(2)

    # ── Parâmetros da Máquina (compacto) + Circuito ───────────────────────
    _ensure_space(pdf, 120)
    _sec_bar(pdf, "PARÂMETROS DA MÁQUINA")
    _mini_table(pdf, [
        ("R[sub]s[/sub]",  f"{mp.Rs:.4f} Ω", "R[sub]r[/sub]",  f"{mp.Rr:.4f} Ω"),
        ("X[sub]m[/sub]",  f"{mp.Xm:.4f} Ω", "X[sub]ls[/sub]", f"{mp.Xls:.4f} Ω"),
        ("X[sub]lr[/sub]", f"{mp.Xlr:.4f} Ω", "J",              f"{mp.J:.4f} kg·m²"),
    ], [30, 45, 30, 45])
    pdf.ln(3)
    embed_fig(pdf, build_circuit_bytes(mp), width_mm=170)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_TEXT_LGT)
    pdf.multi_cell(0, 5, "Circuito equivalente monofásico em T do Motor de Inducao Trifasico.",
                   border=0, align="C")
    pdf.ln(2)

    # ── Análise do Modo de Operação ────────────────────────────────────────
    if exp_config and is_main:
        import numpy as _np
        _mode = exp_config.get("exp_type", exp_type)
        if _mode == "frenagem":
            _ensure_space(pdf, 50)
            _sec_bar(pdf, "ANÁLISE DE FRENAGEM ELÉTRICA")
            _brake = exp_config.get("brake_method", "plugging")
            _BRAKE_NOMES = {
                "plugging":    "Reversão de Polaridade (Plugging)",
                "injecao_cc":  "Injeção de Corrente Contínua",
                "regenerativo":"Frenagem Regenerativa",
            }
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_TEXT_MID)
            pdf.multi_cell(0, 5, f"  Método: {_BRAKE_NOMES.get(_brake, _brake)}")
            pdf.ln(1)
            t_freia = exp_config.get("t_brake", exp_config.get("t_freia", 0.0))
            _wr_a = _np.asarray(res.get("wr", [0.0]))
            _t_a  = _np.asarray(res.get("t",  [0.0]))
            _ia_a = _np.asarray(res.get("ias", [0.0]))
            _idx_f = int(_np.searchsorted(_t_a, t_freia))
            _wm_b  = float(_wr_a[max(_idx_f-1, 0)]) * 60 / (2*3.14159) if len(_wr_a) > 0 else 0.0
            _ia_pk = float(_np.max(_np.abs(_ia_a[_idx_f:]))) if _idx_f < len(_ia_a) else 0.0
            _idx_stop = next((i for i in range(_idx_f, len(_wr_a)) if abs(_wr_a[i]) < 1.0), len(_wr_a)-1)
            _t_stop = float(_t_a[_idx_stop]) - t_freia if _idx_stop < len(_t_a) else None
            _rows_b = [
                ("Instante de frenagem",          f"{t_freia:.3f} s"),
                ("Velocidade antes da frenagem",   f"{_wm_b:.1f} RPM"),
                ("Corrente de pico pos-frenagem",  f"{_ia_pk:.3f} A"),
            ]
            if _t_stop is not None:
                _rows_b.append(("Tempo ate parada estimado", f"{_t_stop:.3f} s"))
            _mini_table(pdf, _rows_b, [115, 55])

        elif _mode == "gerador":
            _ensure_space(pdf, 50)
            _sec_bar(pdf, "ANÁLISE DO MODO GERADOR")
            _wr_ss = float(res.get("wr_ss", 0.0))
            _Te_ss = float(res.get("Te_ss", 0.0))
            _P_mec = abs(_Te_ss) * abs(_wr_ss)
            _P_ele = float(res.get("P_out", _P_mec * 0.9))
            _eta_g = _P_ele / _P_mec * 100 if _P_mec > 1e-3 else 0.0
            _rows_g = [
                ("Velocidade de regime",        f"{_wr_ss * 60/(2*3.14159):.1f} RPM"),
                ("Torque de entrada (Te,ss)",   f"{_Te_ss:.3f} N.m"),
                ("Potencia mecanica de entrada", f"{_P_mec:.2f} W"),
                ("Potencia eletrica gerada",    f"{_P_ele:.2f} W"),
                ("Rendimento estimado",         f"{_eta_g:.1f} %"),
            ]
            _mini_table(pdf, _rows_g, [115, 55])

    # ── Estimacao de Parametros ────────────────────────────────────────────
    if input_mode and input_mode != "Inserir parâmetros manualmente" and is_main:
        _ensure_space(pdf, 60)
        _sec_bar(pdf, "ESTIMAÇÃO DE PARÂMETROS")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_TEXT_MID)
        if "Nameplate" in input_mode:
            pdf.multi_cell(0, 5, "  Metodo: Nameplate (NEMA MG-1). Parametros estimados por heuristicas a partir da placa de identificacao.")
        else:
            pdf.multi_cell(0, 5, "  Metodo: IEEE Std 112-2017 Eq.(38)-(49). Ensaios CC, vazio e rotor bloqueado.")
        pdf.ln(1)
        _rows_e = [
            ("Resistencia do estator (Rs)",         f"{mp.Rs:.5f} Ohm"),
            ("Resistencia do rotor (Rr)",           f"{mp.Rr:.5f} Ohm"),
            ("Reatancia de magnetizacao (Xm)",      f"{mp.Xm:.4f} Ohm"),
            ("Reatancia de dispersao estator (Xls)", f"{mp.Xls:.5f} Ohm"),
            ("Reatancia de dispersao rotor (Xlr)",   f"{mp.Xlr:.5f} Ohm"),
            ("Resistencia de perdas no ferro (Rfe)", f"{mp.Rfe:.1f} Ohm"),
        ]
        _mini_table(pdf, _rows_e, [115, 55])

    # ── Curvas Características ────────────────────────────────────────────
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _dash_title(pdf, f"CURVAS CARACTERÍSTICAS{sfx}", ", ".join(cl))
        curves = build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig(pdf, fig_to_png_bytes(curves), width_mm=170)


# ─────────────────────────────────────────────────────────────────────────────
# Tabela comparativa de KPIs — todas as simulações
# ─────────────────────────────────────────────────────────────────────────────

def _write_kpi_comparison(pdf, current_sim: dict, ref_list: list) -> None:
    all_sims = [current_sim] + [r for r in ref_list if r.get("res") is not None]
    if len(all_sims) < 2:
        return

    pdf.add_page()
    _banner(pdf, "Histórico Comparativo — KPIs de Todas as Simulações")
    _sec_bar(pdf, "COMPARAÇÃO DE DESEMPENHO E QUALIDADE DE ENERGIA")

    # Cabeçalho
    col_w = min(170.0 / len(all_sims), 38.0)
    label_w = 170.0 - col_w * len(all_sims)
    label_w = max(label_w, 50.0)
    col_w = (170.0 - label_w) / len(all_sims)

    headers = [("KPI", label_w)] + [
        (safe_text(s.get("exp_label", f"Sim {i+1}")), col_w)
        for i, s in enumerate(all_sims)
    ]
    x0, y0 = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(22, 54, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for lbl, w in headers:
        pdf.cell(w, 7, f"  {lbl[:18]}", border=0, fill=True)
    pdf.ln(7)

    def _val(sim: dict, key: str, fmt: str = ".2f") -> str:
        r = sim.get("res") or sim
        v = r.get(key)
        if v is None:
            return "—"
        try:
            return f"{float(v):{fmt}}"
        except Exception:
            return str(v)

    kpi_rows = [
        ("Vel. regime (RPM)",    "n_ss",    ".1f"),
        ("Torque Te (N.m)",      "Te_ss",   ".2f"),
        ("Ias RMS (A)",          "ias_rms", ".3f"),
        ("Rendimento (%)",       "eta",     ".2f"),
        ("Escorregamento (%)",   "_s_pct",  ".3f"),
        ("P_in (kW)",            "_pin_kw", ".3f"),
    ]

    for idx, (lbl, key, fmt) in enumerate(kpi_rows):
        fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill)
        pdf.set_text_color(*_TEXT_DRK)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(label_w, 6, f"  {lbl}", border=0, fill=True)
        for sim in all_sims:
            r = sim.get("res") or sim
            if key == "_s_pct":
                val = f"{float(r.get('s', 0.0)) * 100:.3f}"
            elif key == "_pin_kw":
                val = f"{float(r.get('P_in', 0.0)) / 1000:.3f}"
            else:
                v = r.get(key)
                val = f"{float(v):{fmt}}" if v is not None else "—"
            pdf.cell(col_w, 6, f"  {val}", border=0, fill=True)
        pdf.ln(6)
    pdf.ln(4)


# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────

def generate_industrial(
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
    exp_config: dict | None = None,
    input_mode: str | None = None,
) -> bytes:
    """Gera relatório industrial em PDF e retorna como bytes.

    Itera sobre simulação atual + todas as referências em ref_list.
    Inclui tabela comparativa de KPIs ao final.
    """
    var_labels = var_labels or var_keys
    t_events   = t_events   or []
    ref_list   = ref_list   or []

    PDF_CLS = make_pdf_class("Industrial")
    pdf = PDF_CLS()
    pdf.alias_nb_pages()
    pdf.set_margins(left=20, top=22, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)

    tmax_eff = tmax if tmax > 0 else (float(res["t"][-1]) if len(res.get("t", [])) > 0 else 1.0)

    current_sim = {
        "res": res, "exp_label": exp_label, "exp_type": exp_type,
    }

    # ── Bloco: simulação atual ────────────────────────────────────────────
    _banner(pdf, "Simulação Atual")
    _write_sim_block(
        pdf, res, mp, exp_label, exp_type, t_events,
        var_keys, var_labels, energy_tariff, tmax_eff, h, insights,
        exp_config=exp_config, input_mode=input_mode, is_main=True,
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
        _banner(pdf, f"Referência {ref_i+1} — {ref_label}")
        _write_sim_block(
            pdf, ref_res, ref_mp, ref_label, ref_exp_type, ref_t_events,
            ref_var_keys, ref_var_labels, ref_tariff, ref_tmax, ref_h,
            insights=None,
        )

    # ── Tabela comparativa de KPIs ────────────────────────────────────────
    if ref_list:
        _write_kpi_comparison(pdf, current_sim, ref_list)

    return bytes(pdf.output())
