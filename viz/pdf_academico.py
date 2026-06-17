# -*- coding: utf-8 -*-
"""
pdf_academico.py
================
Generates an academic-style PDF report for induction-machine simulations
(equations, all curves, saved references).

Responsibilities:
  - Export generate_academico(exp_label, mp, res, ..., ref_list) -> bytes.
  - Render equations, full waveform plots, and bibliography sections.

Relationships:
  Imported by : ui_components.sim_results
  Imports     : viz.pdf_commons

Extending:
  - To add a new report section, create a _section_<name>() helper and call
    it inside generate_academico.
"""

from __future__ import annotations
import datetime
import numpy as np

from core.tim.facade import MachineParams
from core.constants import GEN_EFFICIENCY_FALLBACK
from viz.pdf_commons import (
    safe_text, fmt_power, embed_fig, build_circuit_bytes,
    cell_rich, render_rich,
    compute_trip_class, compute_thd_harmonics, compute_energy_metrics,
    compute_losses, compute_integrator_params, compute_broken_bar,
    make_chunks, build_abc_currents_fig, build_losses_bar_fig,
    build_curves_fig, fig_to_png_bytes, make_pdf_class,
    _sec, _subsec, _body, _caption, _th, _tr, _banner, _ensure_space,
)


# ─────────────────────────────────────────────────────────────────────────────
# Section sub-renderers
# ─────────────────────────────────────────────────────────────────────────────

def _pdf_cover(pdf, exp_label: str, banner_label: str) -> None:
    pdf.add_page()
    pdf.set_fill_color(15, 40, 100)
    pdf.rect(0, 0, 210, 65, style="F")
    pdf.set_xy(20, 14)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS — Technical Simulation Report",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 30)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Structured Academic Version",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 44)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Experiment: {exp_label}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 54)
    pdf.set_font("Helvetica", "I", 9)
    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    pdf.cell(0, 6, f"Generated: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    if banner_label:
        _banner(pdf, banner_label)


def _pdf_section_identification(
    pdf, res: dict, mp: MachineParams,
    exp_label: str, exp_type: str, sec_n: int,
) -> int:
    _sec(pdf, "Experiment Identification", f"{sec_n}.")
    _th(pdf, [("Attribute", 90), ("Value", 80)])
    _tr(pdf, [
        ("Experiment",                        exp_label),
        ("Start-up / operation type",         exp_type.upper()),
        ("Synchronous speed",                 f"{mp.n_sync:.1f} RPM"),
        ("Rated frequency",                   f"{mp.f:.1f} Hz"),
        ("Number of poles",                   str(mp.p)),
        ("Line voltage (V[sub]l[/sub])",      f"{mp.Vl:.1f} V"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)
    return sec_n + 1


def _pdf_section_machine_params(pdf, mp: MachineParams, sec_n: int) -> int:
    _sec(pdf, "Machine Parameters", f"{sec_n}.")
    _th(pdf, [("Parameter", 100), ("Value", 45), ("Unit", 25)])
    _tr(pdf, [
        ("Stator resistance (R[sub]s[/sub])",             f"{mp.Rs:.4f}", "Ohm"),
        ("Rotor resistance (R[sub]r[/sub])",              f"{mp.Rr:.4f}", "Ohm"),
        ("Magnetising reactance (X[sub]m[/sub])",         f"{mp.Xm:.4f}", "Ohm"),
        ("Stator leakage reactance (X[sub]ls[/sub])",     f"{mp.Xls:.4f}", "Ohm"),
        ("Rotor leakage reactance (X[sub]lr[/sub])",      f"{mp.Xlr:.4f}", "Ohm"),
        ("Iron-loss resistance (R[sub]fe[/sub])",         f"{mp.Rfe:.1f}", "Ohm"),
        ("Moment of inertia (J)",                          f"{mp.J:.4f}", "kg.m2"),
        ("Friction coefficient (B)",                       f"{mp.B:.4f}", "N.m.s/rad"),
    ], [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)
    _ensure_space(pdf, 85)
    _subsec(pdf, f"{sec_n}.1  Single-Phase T Equivalent Circuit")
    pdf.ln(1)
    embed_fig(pdf, build_circuit_bytes(mp), width_mm=170)
    _caption(pdf,
        "Figure — Single-phase T equivalent circuit of the Three-Phase Induction Motor. "
        "Rs: stator resistance; Xls: stator leakage reactance; "
        "Xm: magnetising reactance; Rfe: iron-loss resistance; "
        "Xlr: rotor leakage reactance; Rr/s: rotor resistance referred to stator."
    )
    pdf.ln(3)
    return sec_n + 1


def _pdf_section_steady_state(pdf, res: dict, sec_n: int) -> int:
    pdf.add_page()
    _sec(pdf, "Steady-State Indicators", f"{sec_n}.")
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
    _th(pdf, [("Quantity", 105), ("Value", 45), ("Unit", 20)])
    _tr(pdf, [
        ("Steady-state speed",                                      f"{res['n_ss']:.3f}",                     "RPM"),
        ("Rotor angular velocity (omega[sub]r[/sub])",              f"{res['wr_ss']:.4f}",                    "rad/s"),
        ("Steady-state electromagnetic torque (T[sub]e[/sub])",    f"{res['Te_ss']:.4f}",                    "N.m"),
        ("Maximum electromagnetic torque (T[sub]e,max[/sub])",     f"{float(np.max(res['Te'])):.4f}",        "N.m"),
        ("Slip (s)",                                                 f"{s_val*100:.3f}",                       "%"),
        ("RMS line current (I[sub]as,rms[/sub])",                  f"{res['ias_rms']:.4f}",                  "A"),
        ("Peak current (I[sub]as,pk[/sub])",                       f"{float(np.max(np.abs(res['ias']))):.4f}", "A"),
        ("Input power (P[sub]in[/sub])",                            vi, ui),
        ("Air-gap power (P[sub]gap[/sub])",                         vg, ug),
        ("Mechanical power (P[sub]mec[/sub])",                      vm, um),
        ("Rotor copper losses (P[sub]cu,r[/sub])",                 vcr, ucr),
        ("Efficiency (eta)",                                        f"{eta:.3f}",                             "%"),
    ], [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)
    return sec_n + 1


def _pdf_section_loss_balance(pdf, losses: dict, sec_n: int) -> int:
    _ensure_space(pdf, 100)
    _sec(pdf, "Loss Balance (Steady State)", f"{sec_n}.")
    lf, uf   = fmt_power(losses["P_cu_s"])
    lg, ug_  = fmt_power(losses["P_cu_r"])
    lh, uh   = fmt_power(losses["P_fe"])
    li, ui_  = fmt_power(max(losses["P_mec"], 0.0))
    _th(pdf, [("Component", 100), ("Value", 38), ("Unit", 18), ("% of P[sub]in[/sub]", 24)])
    _tr(pdf, [
        ("Stator copper losses (P[sub]cu,s[/sub])", lf,  uf,  f"{losses['pct_cu_s']:.1f}%"),
        ("Rotor copper losses (P[sub]cu,r[/sub])",  lg,  ug_, f"{losses['pct_cu_r']:.1f}%"),
        ("Iron losses (P[sub]fe[/sub])",             lh,  uh,  f"{losses['pct_fe']:.1f}%"),
        ("Useful mechanical power (P[sub]mec[/sub])", li, ui_, f"{losses['pct_mec']:.1f}%"),
    ], [100, 38, 18, 24], ["L", "R", "L", "R"])
    pdf.ln(2)
    embed_fig(pdf, fig_to_png_bytes(build_losses_bar_fig(losses)), width_mm=170)
    _caption(pdf, "Percentage distribution of steady-state losses relative to input power.")
    pdf.ln(2)
    return sec_n + 1


def _pdf_section_integrator(pdf, integrator: dict, sec_n: int) -> int:
    _ensure_space(pdf, 55)
    _sec(pdf, "Numerical Integrator Parameters (LSODA)", f"{sec_n}.")
    ny_ok = integrator["nyquist_ok"]
    ny_status = ("Satisfied (>= 10 samples/cycle)"
                 if ny_ok else "WARNING: insufficient — RMS and FFT may be inaccurate")
    _th(pdf, [("Parameter", 115), ("Value", 55)])
    _tr(pdf, [
        ("Requested sampling step (h)",        f"{integrator['h_req']:.6f} s"),
        ("Effective mean step",                 f"{integrator['dt_eff']:.6f} s"),
        ("Samples per cycle (fn / heff)",       f"{integrator['samples_per_cycle']:.1f}"),
        ("Total output points",                 str(integrator["n_steps"])),
        ("Total simulated duration (t[sub]max[/sub])", f"{integrator['tmax']:.3f} s"),
        ("Nyquist criterion",                   ny_status),
    ], [115, 55], ["L", "L"])
    _body(pdf,
        "  Integrator: LSODA (scipy.integrate.solve_ivp), adaptive step control, "
        "RTOL = 1e-5, ATOL = 1e-6.")
    pdf.ln(3)
    return sec_n + 1


def _pdf_section_broken_bar(pdf, broken_bar: dict | None, sec_n: int) -> int:
    if broken_bar is None:
        return sec_n
    _ensure_space(pdf, 60)
    _sec(pdf, "Fault Indicators — Broken Bar (MCSA)", f"{sec_n}.")
    _subsec(pdf, "Current Spectral Analysis (Motor Current Signature Analysis)")
    _th(pdf, [("Indicator", 115), ("Value", 55)])
    _tr(pdf, [
        ("Severity (alpha)",                           f"{broken_bar['alpha']:.3f}"),
        ("Severity classification",                    broken_bar["severity_label"]),
        ("Steady-state slip (s)",                      f"{broken_bar['s_val']*100:.3f} %"),
        ("Lower sideband frequency (1-2s)f",          f"{broken_bar['f_lo']:.2f} Hz"),
        ("Upper sideband frequency (1+2s)f",          f"{broken_bar['f_hi']:.2f} Hz"),
        ("Relative amplitude (1-2s)f / fundamental",  f"{broken_bar['sb_ratio_lo']:.2f} %"),
        ("Relative amplitude (1+2s)f / fundamental",  f"{broken_bar['sb_ratio_hi']:.2f} %"),
    ], [115, 55], ["L", "L"])
    _body(pdf,
        "Reference: IEEE 1159-2019 — MCSA. "
        "Relative amplitude > 3% indicates incipient fault; > 10% indicates severe fault.")
    pdf.ln(2)
    return sec_n + 1


def _pdf_section_power_quality(
    pdf, res: dict, mp: MachineParams,
    energy_tariff: float, exp_type: str, sec_n: int,
) -> int:
    if exp_type == "shutdown":
        return sec_n
    em = compute_energy_metrics(res, mp, energy_tariff)
    _ensure_space(pdf, 60)
    _sec(pdf, "Power Quality and Economic Analysis", f"{sec_n}.")
    thd_ok = em["thd"] <= 5.0
    fp_ok  = em["fp"] >= 0.85
    _th(pdf, [("Quantity", 110), ("Value", 40), ("Status / Unit", 20)])
    _tr(pdf, [
        ("Power Factor (PF)",                        f"{em['fp']:.4f}",           "OK" if fp_ok else "LOW"),
        ("Current THD (I[sub]as[/sub])",             f"{em['thd']:.2f} %",        "OK" if thd_ok else "HIGH"),
        ("Energy consumed in experiment",            f"{em['E_kwh']:.6f}",         "kWh"),
        ("Experiment cost",                          f"$ {em['custo_exp']:.4f}",  "$"),
        ("Steady-state input power",                 f"{em['P_in_kw']:.3f}",       "kW"),
        ("Steady-state efficiency",                  f"{em['eta']:.2f}",           "%"),
        ("Projected annual operating cost (8760h)", f"$ {em['custo_ano']:,.2f}",  "$/yr"),
    ], [110, 40, 20], ["L", "R", "L"])
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5,
             f"  Tariff: $ {energy_tariff:.2f}/kWh. THD and PF computed via FFT in the steady-state window.",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    harm_rows = compute_thd_harmonics(res, mp)
    if harm_rows:
        _ensure_space(pdf, 40)
        _subsec(pdf, "Harmonic Spectrum of I[sub]as[/sub] — Orders 1 to 9")
        _th(pdf, [("Order", 25), ("Frequency (Hz)", 45), ("Amplitude (A)", 55), ("Relative (%)", 45)])
        _tr(pdf, [
            (f"{k}", f"{fk:.1f}", f"{Ak:.4f}", f"{pct:.2f}")
            for k, fk, Ak, pct in harm_rows
        ], [25, 45, 55, 45], ["C", "R", "R", "R"])
        _body(pdf, "Relative amplitudes normalised by the fundamental. Reference: IEEE 519-2022.")
        pdf.ln(2)
    return sec_n + 1


def _pdf_section_trip_class(
    pdf, res: dict, mp: MachineParams, exp_type: str, sec_n: int,
) -> int:
    if exp_type not in ("dol", "yd", "comp", "soft", "voltage_sag"):
        return sec_n
    tc = compute_trip_class(res, mp)
    if tc is None:
        return sec_n
    _ensure_space(pdf, 40)
    _sec(pdf, "Protection Recommendation — Overload Relay", f"{sec_n}.")
    tc_color = {10: (22, 163, 74), 20: (217, 119, 6), 30: (220, 38, 38)}
    r_, g_, b_ = tc_color.get(tc["class"], (80, 80, 80))
    pdf.set_fill_color(r_, g_, b_)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8,
             f"  Class {tc['class']} — t_acceleration = {tc['t_accel']:.2f} s "
             f"(95% of {tc['n_sync']:.1f} RPM) — {tc['status']}",
             border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
    _body(pdf, "Reference: IEC 60947-4-1 / NEMA ICS 2. "
               "Class 10: t < 10 s | Class 20: 10-20 s | Class 30: > 20 s.")
    pdf.ln(2)
    return sec_n + 1


def _pdf_section_diagnostics(pdf, insights: list | None, sec_n: int) -> int:
    if not insights:
        return sec_n
    _ensure_space(pdf, 40)
    _sec(pdf, "Automated Diagnostics", f"{sec_n}.")
    _COLORS = {"error": (220, 38, 38), "warning": (217, 119, 6), "info": (22, 163, 74)}
    _LABELS = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}
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
    return sec_n + 1


def _pdf_section_abc_currents(pdf, res: dict, sec_n: int) -> int:
    if not any(k in res for k in ("ias", "ibs", "ics")):
        return sec_n
    _ensure_space(pdf, 80)
    _sec(pdf, "ABC Phase Currents — Steady State", f"{sec_n}.")
    embed_fig(pdf, fig_to_png_bytes(build_abc_currents_fig(res)), width_mm=170)
    ias_rms = float(res.get("ias_rms", 0.0))
    _caption(pdf,
        f"Phase currents ias, ibs, ics in steady state. "
        f"Dashed: +/- RMS (Ias,rms = {ias_rms:.3f} A). "
        "Balanced system: equal amplitudes, 120 deg phase shift.")
    pdf.ln(2)
    return sec_n + 1


def _pdf_section_mode_analysis(
    pdf, res: dict, mp: MachineParams,
    exp_type: str, exp_config: dict | None,
    energy_tariff: float, sec_n: int,
) -> int:
    if not exp_config:
        return sec_n
    import numpy as _np
    _mode = exp_config.get("exp_type", exp_type)
    if _mode == "frenagem":
        _ensure_space(pdf, 50)
        _sec(pdf, "Electric Braking Analysis", f"{sec_n}.")
        _brake = exp_config.get("brake_method", "plugging")
        _BRAKE_NAMES = {
            "plugging":    "Polarity Reversal (Plugging)",
            "injecao_cc":  "DC Injection Braking",
            "regenerativo":"Regenerative Braking",
        }
        _body(pdf, f"  Method: {_BRAKE_NAMES.get(_brake, _brake)}")
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
            ("Braking instant",              f"{t_freia:.3f} s"),
            ("Speed before braking",         f"{_wm_b:.1f} RPM"),
            ("Post-braking peak current",    f"{_ia_pk:.3f} A"),
        ]
        if _t_stop is not None:
            _rows_b.append(("Estimated time to stop", f"{_t_stop:.3f} s"))
        _th(pdf, [("Indicator", 115), ("Value", 55)])
        _tr(pdf, _rows_b, [115, 55], ["L", "L"])
        return sec_n + 1

    elif _mode == "gerador":
        _ensure_space(pdf, 50)
        _sec(pdf, "Generator Mode Analysis", f"{sec_n}.")
        _wr_ss = float(res.get("wr_ss", 0.0))
        _Te_ss = float(res.get("Te_ss", 0.0))
        _P_mec = abs(_Te_ss) * abs(_wr_ss)
        _P_ele = float(res.get("P_out", _P_mec * GEN_EFFICIENCY_FALLBACK))
        _eta_g = _P_ele / _P_mec * 100 if _P_mec > 1e-3 else 0.0
        _rows_g = [
            ("Steady-state speed",          f"{_wr_ss * 60/(2*3.14159):.1f} RPM"),
            ("Input torque (Te,ss)",         f"{_Te_ss:.3f} N.m"),
            ("Input mechanical power",       f"{_P_mec:.2f} W"),
            ("Generated electrical power",   f"{_P_ele:.2f} W"),
            ("Estimated efficiency",         f"{_eta_g:.1f} %"),
        ]
        _th(pdf, [("Indicator", 115), ("Value", 55)])
        _tr(pdf, _rows_g, [115, 55], ["L", "L"])
        return sec_n + 1

    return sec_n


def _pdf_section_param_estimation(
    pdf, mp: MachineParams, input_mode: str | None, sec_n: int,
) -> int:
    if not input_mode or input_mode == "Enter parameters manually":
        return sec_n
    _ensure_space(pdf, 60)
    _sec(pdf, "Parameter Estimation", f"{sec_n}.")
    if "Nameplate" in input_mode:
        _body(pdf, "  Method: Nameplate (NEMA MG-1). Parameters estimated from nameplate data using heuristics.")
    else:
        _body(pdf, "  Method: IEEE Std 112-2017 Eq.(38)-(49). DC, no-load and locked-rotor tests.")
    _rows_e = [
        ("Stator resistance (Rs)",              f"{mp.Rs:.5f} Ohm"),
        ("Rotor resistance (Rr)",               f"{mp.Rr:.5f} Ohm"),
        ("Magnetising reactance (Xm)",          f"{mp.Xm:.4f} Ohm"),
        ("Stator leakage reactance (Xls)",      f"{mp.Xls:.5f} Ohm"),
        ("Rotor leakage reactance (Xlr)",       f"{mp.Xlr:.5f} Ohm"),
        ("Iron-loss resistance (Rfe)",          f"{mp.Rfe:.1f} Ohm"),
    ]
    _th(pdf, [("Parameter", 115), ("Value", 55)])
    _tr(pdf, _rows_e, [115, 55], ["L", "L"])
    return sec_n + 1


def _pdf_section_curves(
    pdf, res: dict, t_events: list,
    var_keys: list, var_labels: list, sec_n: int,
) -> None:
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _sec(pdf, f"Characteristic Curves{sfx}",
             f"{sec_n}." if pg == 0 else "")
        curves = build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig(pdf, fig_to_png_bytes(curves), width_mm=170)
        _caption(pdf, ", ".join(cl))


# ─────────────────────────────────────────────────────────────────────────────
# Simulation block — orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def _write_sim_block(
    pdf,
    res: dict, mp: MachineParams, exp_label: str, exp_type: str,
    t_events: list, var_keys: list, var_labels: list,
    energy_tariff: float, tmax: float, h: float,
    insights: list | None, load_torque: float,
    banner_label: str = "",
    exp_config: dict | None = None,
    input_mode: str | None = None,
    is_main: bool = False,
) -> None:
    losses     = compute_losses(res, mp)
    integrator = compute_integrator_params(res, mp, tmax, h)
    broken_bar = compute_broken_bar(res, mp)

    _pdf_cover(pdf, exp_label, banner_label)

    sec_n = 1
    sec_n = _pdf_section_identification(pdf, res, mp, exp_label, exp_type, sec_n)
    sec_n = _pdf_section_machine_params(pdf, mp, sec_n)
    sec_n = _pdf_section_steady_state(pdf, res, sec_n)
    sec_n = _pdf_section_loss_balance(pdf, losses, sec_n)
    sec_n = _pdf_section_integrator(pdf, integrator, sec_n)
    sec_n = _pdf_section_broken_bar(pdf, broken_bar, sec_n)
    sec_n = _pdf_section_power_quality(pdf, res, mp, energy_tariff, exp_type, sec_n)
    sec_n = _pdf_section_trip_class(pdf, res, mp, exp_type, sec_n)
    sec_n = _pdf_section_diagnostics(pdf, insights, sec_n)
    sec_n = _pdf_section_abc_currents(pdf, res, sec_n)
    if is_main:
        sec_n = _pdf_section_mode_analysis(pdf, res, mp, exp_type, exp_config, energy_tariff, sec_n)
        sec_n = _pdf_section_param_estimation(pdf, mp, input_mode, sec_n)
    _pdf_section_curves(pdf, res, t_events, var_keys, var_labels, sec_n)


# ─────────────────────────────────────────────────────────────────────────────
# Comparative section — all references overlaid
# ─────────────────────────────────────────────────────────────────────────────

def _write_comparative_section(
    pdf, res: dict, var_keys: list, var_labels: list,
    t_events: list, ref_list: list,
) -> None:
    chart_refs = [
        {
            "res":   r["res"],
            "color": r.get("color", "#888888"),
            "label": r.get("exp_label", "Reference"),
        }
        for r in ref_list if r.get("res") is not None
    ]
    if not chart_refs:
        return
    pdf.add_page()
    _banner(pdf, "Comparative Curves — Current + References Overlaid")
    chunks = make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        valid_k = [k for k in ck if k in res]
        if not valid_k:
            continue
        valid_l = [cl[ck.index(k)] for k in valid_k]
        if pg > 0:
            pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        _sec(pdf, f"Comparative Curves{sfx}")
        fig = build_curves_fig(res, valid_k, valid_l, t_events,
                               color_offset=pg * 4, ref_list=chart_refs)
        embed_fig(pdf, fig_to_png_bytes(fig), width_mm=170)
        names = "Current vs. " + ", ".join(r["label"] for r in chart_refs)
        _caption(pdf, names)


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
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
    exp_config: dict | None = None,
    input_mode: str | None = None,
) -> bytes:
    """Generates academic PDF report and returns as bytes.

    Iterates over current simulation + all references in ref_list.
    """
    var_labels = var_labels or var_keys
    t_events   = t_events   or []
    ref_list   = ref_list   or []

    PDF_CLS = make_pdf_class("Academic")
    pdf = PDF_CLS()
    pdf.alias_nb_pages()
    pdf.set_margins(left=20, top=22, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)

    tmax_eff = tmax if tmax > 0 else (float(res["t"][-1]) if len(res.get("t", [])) > 0 else 1.0)

    # ── Block: current simulation ─────────────────────────────────────────
    _write_sim_block(
        pdf, res, mp, exp_label, exp_type, t_events,
        var_keys, var_labels, energy_tariff, tmax_eff, h, insights, load_torque,
        banner_label="Current Simulation",
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
        _write_sim_block(
            pdf, ref_res, ref_mp, ref_label, ref_exp_type, ref_t_events,
            ref_var_keys, ref_var_labels, ref_tariff, ref_tmax, ref_h,
            insights=None, load_torque=0.0,
            banner_label=f"Reference {ref_i+1} — {ref_label}",
        )

    # ── Final section: overlaid plots ─────────────────────────────────────
    if ref_list:
        _write_comparative_section(pdf, res, var_keys, var_labels, t_events, ref_list)

    return bytes(pdf.output())
