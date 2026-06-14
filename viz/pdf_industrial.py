# -*- coding: utf-8 -*-
"""
pdf_industrial.py
=================
Generates an industrial-style PDF report for induction-machine simulations
(KPIs, fault diagnostics, economic analysis).

Responsibilities:
  - Export generate_industrial(exp_label, mp, res, ..., ref_list) -> bytes.
  - Render KPI summary, fault signature table, and economic analysis.
  - Omit detailed equations to keep the report concise for decision-makers.

Relationships:
  Imported by : ui_components.sim_results
  Imports     : viz.pdf_commons

Extending:
  - To add a cost-of-downtime section, create _section_cost_downtime() and
    call it inside generate_industrial.
"""

from __future__ import annotations
import datetime
import numpy as np

from core.tim.facade import MachineParams
from viz.pdf_commons import (
    safe_text, fmt_power, embed_fig, build_circuit_bytes,
    cell_rich,
    compute_trip_class, compute_energy_metrics,
    compute_losses, compute_integrator_params, compute_broken_bar,
    make_chunks, build_abc_currents_fig, build_losses_bar_fig,
    build_curves_fig, fig_to_png_bytes, make_pdf_class,
)


# Industrial palette
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
# Layout primitives — industrial
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
# Simulation block — industrial
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

    # ── Executive cover ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_BG_DARK)
    pdf.rect(0, 0, 210, 58, style="F")
    pdf.set_xy(20, 12)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS SIMULATOR", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 28)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Industrial Simulation Report",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 38)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Experiment: {exp_label}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 47)
    pdf.set_font("Helvetica", "I", 8)
    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    pdf.cell(0, 6, f"Generated: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── Performance KPIs ──────────────────────────────────────────────────
    _dash_title(pdf, "PERFORMANCE", f"Steady State — {exp_type.upper()}")
    n_ss    = float(res.get("n_ss",    0.0))
    Te_ss   = float(res.get("Te_ss",   0.0))
    ias_rms = float(res.get("ias_rms", 0.0))
    eta     = float(res.get("eta",     0.0))
    s_val   = float(res.get("s",       0.0))
    P_in    = float(res.get("P_in",    0.0))
    v_pin, u_pin = fmt_power(P_in)
    _kpi_row(pdf, [
        ("Steady-State Speed",   f"{n_ss:.1f}",    "RPM"),
        ("Steady-State Torque Te", f"{Te_ss:.2f}", "N.m"),
        ("RMS Current Ias",      f"{ias_rms:.3f}", "A"),
        ("Efficiency eta",       f"{eta:.2f}",     "%"),
    ])
    _kpi_row(pdf, [
        ("Slip s",               f"{s_val*100:.3f}", "%"),
        ("Input Power",          v_pin,              u_pin),
        ("Number of Poles p",    str(mp.p),          "—"),
        ("Line Voltage Vl",      f"{mp.Vl:.1f}",     "V"),
    ])

    # ── Loss Balance ──────────────────────────────────────────────────────
    _sec_bar(pdf, "LOSS BALANCE")
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

    # ── Power Quality ──────────────────────────────────────────────────────
    if exp_type != "shutdown":
        em = compute_energy_metrics(res, mp, energy_tariff)
        _ensure_space(pdf, 55)
        _sec_bar(pdf, "POWER QUALITY")
        thd_ok = em["thd"] <= 5.0
        fp_ok  = em["fp"] >= 0.85
        _badge(pdf, thd_ok and fp_ok,
               f"PF = {em['fp']:.3f} ({'OK >= 0.85' if fp_ok else 'LOW'})   |   "
               f"THD = {em['thd']:.2f}% ({'OK < 5%' if thd_ok else 'HIGH > 5%'})")
        _mini_table(pdf, [
            ("Energy consumed in experiment",  f"{em['E_kwh']:.6f} kWh"),
            ("Experiment cost",                f"$ {em['custo_exp']:.4f}"),
            ("Steady-state input power",       f"{em['P_in_kw']:.3f} kW"),
            ("Steady-state efficiency",        f"{em['eta']:.2f} %"),
        ], [105, 65])
        pdf.ln(2)

        # ── Economic Analysis ──────────────────────────────────────────────
        _ensure_space(pdf, 45)
        _sec_bar(pdf, "ECONOMIC ANALYSIS")
        _mini_table(pdf, [
            ("Energy tariff",                      f"$ {energy_tariff:.2f}/kWh"),
            ("Annual operating cost (8760 h)",      f"$ {em['custo_ano']:,.2f}"),
            ("Estimated monthly cost (730 h)",      f"$ {em['P_in_kw'] * 730.0 * energy_tariff:,.2f}"),
        ], [105, 65])
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_TEXT_LGT)
        pdf.cell(0, 5, "  Projection based on continuous operation at steady-state power.",
                 border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ── Diagnostics — Broken Bar ──────────────────────────────────────────
    if broken_bar is not None:
        _ensure_space(pdf, 58)
        _sec_bar(pdf, "DIAGNOSTICS — BROKEN BAR (MCSA)")
        sev_ok = broken_bar["alpha"] < 0.2
        _badge(pdf, sev_ok,
               f"Severity: {broken_bar['severity_label']} "
               f"(alpha = {broken_bar['alpha']:.3f})",
               warn=0.2 <= broken_bar["alpha"] < 0.5)
        _mini_table(pdf, [
            ("Lower sideband frequency (1-2s)f",   f"{broken_bar['f_lo']:.2f} Hz"),
            ("Upper sideband frequency (1+2s)f",   f"{broken_bar['f_hi']:.2f} Hz"),
            ("Relative amplitude (1-2s)f / fund.", f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Relative amplitude (1+2s)f / fund.", f"{broken_bar['sb_ratio_hi']:.2f} %"),
            ("Slip (s)",                            f"{broken_bar['s_val']*100:.3f} %"),
        ], [115, 55])
        pdf.ln(2)

    # ── Protection — Trip Class ───────────────────────────────────────────
    if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
        tc = compute_trip_class(res, mp)
        if tc is not None:
            _ensure_space(pdf, 45)
            _sec_bar(pdf, "PROTECTION RECOMMENDATION — OVERLOAD RELAY")
            _badge(pdf, tc["class"] == 10,
                   f"Class {tc['class']} — t_acceleration = {tc['t_accel']:.2f} s "
                   f"(95% of {tc['n_sync']:.1f} RPM) — {tc['status']}",
                   warn=tc["class"] == 20)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*_TEXT_LGT)
            pdf.cell(0, 5,
                     "  Reference: IEC 60947-4-1 / NEMA ICS 2. "
                     "Class 10: t < 10 s | Class 20: 10-20 s | Class 30: > 20 s",
                     border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    # ── Automated Diagnostics ─────────────────────────────────────────────
    if insights:
        _ensure_space(pdf, 45)
        _sec_bar(pdf, "AUTOMATED DIAGNOSTICS")
        _COLORS = {"error": _RED, "warning": _AMBER, "info": _GREEN}
        _LABELS = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}
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

    # ── Numerical Integrator ──────────────────────────────────────────────
    _ensure_space(pdf, 52)
    _sec_bar(pdf, "NUMERICAL INTEGRATOR (LSODA)")
    ny_ok = integrator["nyquist_ok"]
    _badge(pdf, ny_ok,
           "Nyquist criterion: satisfied (>= 10 samples/cycle)"
           if ny_ok else
           "WARNING: Nyquist criterion not satisfied — RMS and FFT may be inaccurate")
    _mini_table(pdf, [
        ("Requested step (h)",               f"{integrator['h_req']:.6f} s"),
        ("Effective mean step",              f"{integrator['dt_eff']:.6f} s"),
        ("Samples per cycle",                f"{integrator['samples_per_cycle']:.1f}"),
        ("Total output points",              str(integrator["n_steps"])),
        ("Total simulated duration (tmax)",  f"{integrator['tmax']:.3f} s"),
    ], [105, 65])
    pdf.ln(2)

    # ── ABC Phase Currents ────────────────────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        _ensure_space(pdf, 78)
        _sec_bar(pdf, "ABC PHASE CURRENTS — STEADY STATE")
        embed_fig(pdf, fig_to_png_bytes(build_abc_currents_fig(res)), width_mm=170)
        pdf.ln(2)

    # ── Machine Parameters (compact) + Circuit ────────────────────────────
    _ensure_space(pdf, 120)
    _sec_bar(pdf, "MACHINE PARAMETERS")
    _mini_table(pdf, [
        ("R[sub]s[/sub]",  f"{mp.Rs:.4f} Ohm", "R[sub]r[/sub]",  f"{mp.Rr:.4f} Ohm"),
        ("X[sub]m[/sub]",  f"{mp.Xm:.4f} Ohm", "X[sub]ls[/sub]", f"{mp.Xls:.4f} Ohm"),
        ("X[sub]lr[/sub]", f"{mp.Xlr:.4f} Ohm", "J",              f"{mp.J:.4f} kg.m2"),
    ], [30, 45, 30, 45])
    pdf.ln(3)
    embed_fig(pdf, build_circuit_bytes(mp), width_mm=170)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_TEXT_LGT)
    pdf.multi_cell(0, 5, "Single-phase T equivalent circuit of the Three-Phase Induction Motor.",
                   border=0, align="C")
    pdf.ln(2)

    # ── Operating Mode Analysis ────────────────────────────────────────────
    if exp_config and is_main:
        import numpy as _np
        _mode = exp_config.get("exp_type", exp_type)
        if _mode == "frenagem":
            _ensure_space(pdf, 50)
            _sec_bar(pdf, "ELECTRIC BRAKING ANALYSIS")
            _brake = exp_config.get("brake_method", "plugging")
            _BRAKE_NAMES = {
                "plugging":    "Polarity Reversal (Plugging)",
                "injecao_cc":  "DC Injection Braking",
                "regenerativo":"Regenerative Braking",
            }
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_TEXT_MID)
            pdf.multi_cell(0, 5, f"  Method: {_BRAKE_NAMES.get(_brake, _brake)}")
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
                ("Braking instant",               f"{t_freia:.3f} s"),
                ("Speed before braking",          f"{_wm_b:.1f} RPM"),
                ("Post-braking peak current",     f"{_ia_pk:.3f} A"),
            ]
            if _t_stop is not None:
                _rows_b.append(("Estimated time to stop", f"{_t_stop:.3f} s"))
            _mini_table(pdf, _rows_b, [115, 55])

        elif _mode == "gerador":
            _ensure_space(pdf, 50)
            _sec_bar(pdf, "GENERATOR MODE ANALYSIS")
            _wr_ss = float(res.get("wr_ss", 0.0))
            _Te_ss = float(res.get("Te_ss", 0.0))
            _P_mec = abs(_Te_ss) * abs(_wr_ss)
            _P_ele = float(res.get("P_out", _P_mec * 0.9))
            _eta_g = _P_ele / _P_mec * 100 if _P_mec > 1e-3 else 0.0
            _rows_g = [
                ("Steady-state speed",          f"{_wr_ss * 60/(2*3.14159):.1f} RPM"),
                ("Input torque (Te,ss)",         f"{_Te_ss:.3f} N.m"),
                ("Input mechanical power",       f"{_P_mec:.2f} W"),
                ("Generated electrical power",   f"{_P_ele:.2f} W"),
                ("Estimated efficiency",         f"{_eta_g:.1f} %"),
            ]
            _mini_table(pdf, _rows_g, [115, 55])

    # ── Parameter Estimation ───────────────────────────────────────────────
    if input_mode and input_mode != "Enter parameters manually" and is_main:
        _ensure_space(pdf, 60)
        _sec_bar(pdf, "PARAMETER ESTIMATION")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_TEXT_MID)
        if "Nameplate" in input_mode:
            pdf.multi_cell(0, 5, "  Method: Nameplate (NEMA MG-1). Parameters estimated from nameplate data using heuristics.")
        else:
            pdf.multi_cell(0, 5, "  Method: IEEE Std 112-2017 Eq.(38)-(49). DC, no-load and locked-rotor tests.")
        pdf.ln(1)
        _rows_e = [
            ("Stator resistance (Rs)",          f"{mp.Rs:.5f} Ohm"),
            ("Rotor resistance (Rr)",            f"{mp.Rr:.5f} Ohm"),
            ("Magnetising reactance (Xm)",       f"{mp.Xm:.4f} Ohm"),
            ("Stator leakage reactance (Xls)",   f"{mp.Xls:.5f} Ohm"),
            ("Rotor leakage reactance (Xlr)",    f"{mp.Xlr:.5f} Ohm"),
            ("Iron-loss resistance (Rfe)",       f"{mp.Rfe:.1f} Ohm"),
        ]
        _mini_table(pdf, _rows_e, [115, 55])

    # ── Characteristic Curves ─────────────────────────────────────────────
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _dash_title(pdf, f"CHARACTERISTIC CURVES{sfx}", ", ".join(cl))
        curves = build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig(pdf, fig_to_png_bytes(curves), width_mm=170)


# ─────────────────────────────────────────────────────────────────────────────
# KPI comparison table — all simulations
# ─────────────────────────────────────────────────────────────────────────────

def _write_kpi_comparison(pdf, current_sim: dict, ref_list: list) -> None:
    all_sims = [current_sim] + [r for r in ref_list if r.get("res") is not None]
    if len(all_sims) < 2:
        return

    pdf.add_page()
    _banner(pdf, "Comparative History — KPIs of All Simulations")
    _sec_bar(pdf, "PERFORMANCE AND POWER QUALITY COMPARISON")

    # Header
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
        ("Speed (RPM)",          "n_ss",    ".1f"),
        ("Torque Te (N.m)",      "Te_ss",   ".2f"),
        ("Ias RMS (A)",          "ias_rms", ".3f"),
        ("Efficiency (%)",       "eta",     ".2f"),
        ("Slip (%)",             "_s_pct",  ".3f"),
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
# Public interface
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
    """Generates industrial PDF report and returns as bytes.

    Iterates over current simulation + all references in ref_list.
    Includes KPI comparison table at the end.
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

    # ── Block: current simulation ─────────────────────────────────────────
    _banner(pdf, "Current Simulation")
    _write_sim_block(
        pdf, res, mp, exp_label, exp_type, t_events,
        var_keys, var_labels, energy_tariff, tmax_eff, h, insights,
        exp_config=exp_config, input_mode=input_mode, is_main=True,
    )

    # ── Block: each saved reference ───────────────────────────────────────
    for ref_i, ref in enumerate(ref_list):
        ref_res = ref.get("res")
        if ref_res is None:
            continue
        ref_mp        = ref.get("mp", mp)
        ref_label     = ref.get("exp_label", f"Reference {ref_i+1}")
        ref_exp_type  = ref.get("exp_type", "dol")
        ref_t_events  = ref.get("t_events", [])
        ref_var_keys  = ref.get("var_keys") or var_keys
        ref_var_labels = ref.get("var_labels") or var_labels
        ref_tariff    = ref.get("energy_tariff", energy_tariff)
        ref_tmax      = ref.get("tmax", tmax_eff)
        ref_h         = ref.get("h", h)
        _banner(pdf, f"Reference {ref_i+1} — {ref_label}")
        _write_sim_block(
            pdf, ref_res, ref_mp, ref_label, ref_exp_type, ref_t_events,
            ref_var_keys, ref_var_labels, ref_tariff, ref_tmax, ref_h,
            insights=None,
        )

    # ── KPI comparison table ──────────────────────────────────────────────
    if ref_list:
        _write_kpi_comparison(pdf, current_sim, ref_list)

    return bytes(pdf.output())
