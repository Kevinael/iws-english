# -*- coding: utf-8 -*-
"""
pdf_dc.py
=========
Generates the technical PDF report for DC machine simulations, matching the
visual style of pdf_academico.py.

Responsibilities:
  - Export generate_dc(exp_label, mp, res, ...) -> bytes.
  - Render DC machine parameters, waveform figures, and diagnostic summary.

Relationships:
  Imported by : ui_components.sim_results_dc
  Imports     : core.dc_machine_model, viz.pdf_commons

Extending:
  - To add a new report section, create a _sec_<name>() helper and call it
    inside generate_dc.
"""

from __future__ import annotations
import datetime
import numpy as np

from core.dc.machine_model import DCMachineParams
from viz.pdf_commons import (
    safe_text, embed_fig,
    cell_rich, render_rich,
    build_curves_fig, fig_to_png_bytes, make_pdf_class,
    _sec, _subsec, _body, _caption, _th, _tr, _banner, _ensure_space,
)


_EXC_LABELS: dict[str, str] = {
    "sep_motor":    "Separately Excited — Motor",
    "shunt_motor":  "Shunt (Parallel) — Motor",
    "series_motor": "Series — Motor",
    "sep_gen":      "Separately Excited — Generator",
    "shunt_gen":    "Shunt (Parallel) — Generator",
}


# ─────────────────────────────────────────────────────────────────────────────
# DC loss bar chart
# ─────────────────────────────────────────────────────────────────────────────

def _build_losses_bar_dc(losses: dict) -> object:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = []
    values = []
    pcts   = []

    labels.append("Joule loss R_a")
    values.append(losses.get("P_Ra", 0.0))
    pcts.append(losses.get("pct_Ra", 0.0))

    if losses.get("P_Rf", 0.0) > 0:
        labels.append("Joule loss R_f")
        values.append(losses["P_Rf"])
        pcts.append(losses.get("pct_Rf", 0.0))

    labels.append("Friction loss")
    values.append(losses.get("P_mec", 0.0))
    pcts.append(losses.get("pct_mec", 0.0))

    labels.append("Useful mechanical power")
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
    ax.set_xlabel("Power (W)", fontsize=8)
    ax.set_facecolor("#f9fafc")
    ax.grid(True, axis="x", color="#dde4f5", linewidth=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    fig.subplots_adjust(left=0.22, right=0.92, top=0.94, bottom=0.14)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# DC loss computation
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
# DC diagnostics block
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
            "CRITICAL",
            "Extreme overcurrent at start-up",
            f"Peak {ia_max:.1f} A = {ia_max/max(abs(ia_ss),1e-6):.0f}x steady state. "
            "Use series resistance or reduce Va.",
        ))

    if not res.get("success", True):
        anomalias.append((
            "CRITICAL",
            "Integrator numerical failure",
            "Reduce h to 1e-5 s or check parameters.",
        ))

    if exc not in ("series_motor",) and len(ifd_arr) > 10:
        ifd_std = float(np.std(ifd_arr[len(ifd_arr) // 2:]))
        if ifd_std > 0.05 * max(abs(ifd_ss), 1e-6):
            anomalias.append((
                "WARNING",
                "Field instability",
                f"sigma(ifd) = {ifd_std:.4f} A in steady state. "
                "Check Rf and Lf.",
            ))

    if len(wm_arr) > 10 and float(np.mean(wm_arr[-10:])) < 0.01 * abs(wm_ss) and abs(wm_ss) > 1:
        anomalias.append((
            "WARNING",
            "Steady state not reached",
            "omega_m still in transient at end of simulation. Increase tmax.",
        ))

    return anomalias


# ─────────────────────────────────────────────────────────────────────────────
# Section sub-renderers
# ─────────────────────────────────────────────────────────────────────────────

def _pdf_dc_cover(pdf, exp_label: str, exc: str) -> None:
    pdf.add_page()
    pdf.set_fill_color(15, 40, 100)
    pdf.rect(0, 0, 210, 65, style="F")
    pdf.set_xy(20, 14)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS - Technical Simulation Report",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 30)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Direct Current Machine (DC)",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 42)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Experiment: {safe_text(exp_label)}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 50)
    pdf.cell(0, 6, f"Configuration: {safe_text(_EXC_LABELS.get(exc, exc))}",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 57)
    pdf.set_font("Helvetica", "I", 9)
    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    pdf.cell(0, 6, f"Generated: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)


def _pdf_dc_section_identification(
    pdf, res: dict, mp: DCMachineParams,
    exp_label: str, exp_type: str, tmax: float,
    exc: str, sec_n: int,
) -> int:
    _sec(pdf, "Experiment Identification", f"{sec_n}.")
    _th(pdf, [("Attribute", 90), ("Value", 80)])
    _tr(pdf, [
        ("Experiment",                        safe_text(exp_label)),
        ("Operation type",                    exp_type.upper()),
        ("Excitation configuration",          safe_text(_EXC_LABELS.get(exc, exc))),
        ("Armature voltage (Va)",             f"{mp.Va:.1f} V"),
        ("Total simulated time",              f"{tmax:.3f} s"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)
    return sec_n + 1


def _pdf_dc_section_machine_params(pdf, mp: DCMachineParams, exc: str, sec_n: int) -> int:
    _sec(pdf, "Machine Parameters", f"{sec_n}.")
    rows_params = [
        ("Armature resistance (R[sub]a[/sub])",         f"{mp.Ra:.4f}", "Ohm"),
        ("Armature inductance (L[sub]a[/sub])",         f"{mp.La:.6f}", "H"),
        ("Electromechanical constant (k[sub]b[/sub])",  f"{mp.kb:.6f}", "V.s/rad"),
        ("Moment of inertia (J)",                        f"{mp.J:.4f}",  "kg.m2"),
        ("Friction coefficient (B)",                     f"{mp.B:.6f}",  "N.m.s/rad"),
        ("Rated load torque (T[sub]load[/sub])",         f"{mp.Tload:.4f}", "N.m"),
    ]
    if exc == "sep_motor":
        rows_params += [
            ("Field voltage (V[sub]f[/sub])",           f"{mp.Vf:.1f}",  "V"),
            ("Field resistance (R[sub]f[/sub])",        f"{mp.Rf:.4f}",  "Ohm"),
            ("Field inductance (L[sub]f[/sub])",        f"{mp.Lf:.6f}",  "H"),
        ]
    elif exc in ("shunt_motor", "shunt_gen"):
        rows_params += [
            ("Shunt field resistance (R[sub]f[/sub])",  f"{mp.Rf:.4f}", "Ohm"),
            ("Shunt field inductance (L[sub]f[/sub])",  f"{mp.Lf:.6f}", "H"),
            ("(V[sub]f[/sub] = V[sub]a[/sub] — parallel excitation)",
             f"{mp.Va:.1f}", "V"),
        ]
    elif exc == "series_motor":
        rows_params += [
            ("Series field resistance (R[sub]f[/sub])", f"{mp.Rf:.4f}", "Ohm"),
            ("Series field inductance (L[sub]f[/sub])", f"{mp.Lf:.6f}", "H"),
            ("(Field in series with armature)", "—", ""),
        ]
    elif exc == "sep_gen":
        rows_params += [
            ("Field voltage (V[sub]f[/sub])",           f"{mp.Vf:.1f}",  "V"),
            ("Field resistance (R[sub]f[/sub])",        f"{mp.Rf:.4f}",  "Ohm"),
            ("Field inductance (L[sub]f[/sub])",        f"{mp.Lf:.6f}",  "H"),
            ("Load resistance (R[sub]l[/sub])",         f"{mp.Rl:.4f}",  "Ohm"),
            ("Load inductance (L[sub]l[/sub])",         f"{mp.Ll:.6f}",  "H"),
        ]
    _th(pdf, [("Parameter", 100), ("Value", 45), ("Unit", 25)])
    _tr(pdf, rows_params, [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)

    try:
        from viz.eqcircuit_plotter_dc_v2 import build_circuit_png_dc
        _ensure_space(pdf, 90)
        _subsec(pdf, f"{sec_n}.1  Equivalent Circuit — {_EXC_LABELS.get(exc, exc)}")
        pdf.ln(1)
        circuit_bytes = build_circuit_png_dc(mp, dark=False)
        embed_fig(pdf, circuit_bytes, width_mm=170)
        _caption(pdf,
            f"Figure — Equivalent circuit of the DC machine with {_EXC_LABELS.get(exc, exc).lower()} excitation. "
            "Ra: armature resistance; La: armature inductance; "
            "Ea: back-EMF; kb: electromechanical constant.")
        pdf.ln(3)
    except Exception:
        pass

    return sec_n + 1


def _pdf_dc_section_steady_state(
    pdf, res: dict, mp: DCMachineParams, losses: dict, exc: str, sec_n: int,
) -> int:
    pdf.add_page()
    _sec(pdf, "Steady-State Indicators", f"{sec_n}.")
    n_ss   = float(res.get("n_ss",   0.0))
    wm_ss  = float(res.get("wm_ss",  0.0))
    Te_ss  = float(res.get("Te_ss",  0.0))
    ia_ss  = float(res.get("ia_ss",  0.0))
    ifd_ss = float(res.get("ifd_ss", 0.0))
    Ea_ss  = float(res.get("Ea_ss",  0.0))
    Vt_ss  = float(res.get("Vt_ss",  0.0))

    is_gen    = exc in ("sep_gen", "shunt_gen")
    P_elec    = losses["P_elec"]
    P_mec_out = losses["P_mec_out"]
    eta = (P_mec_out / max(P_elec, 1e-9) * 100) if not is_gen \
        else (P_elec / max(P_mec_out, 1e-9) * 100)

    rows_ss = [
        ("Steady-state speed (n)",                                f"{n_ss:.3f}",  "RPM"),
        ("Rotor angular velocity (omega[sub]m[/sub])",            f"{wm_ss:.4f}", "rad/s"),
        ("Steady-state electromagnetic torque (T[sub]e[/sub])",  f"{Te_ss:.4f}", "N.m"),
        ("Maximum electromagnetic torque",                       f"{float(np.max(res.get('Te', [Te_ss]))):.4f}", "N.m"),
        ("Steady-state armature current (i[sub]a[/sub])",        f"{ia_ss:.4f}", "A"),
        ("Peak armature current",                                f"{float(np.max(np.abs(res.get('ia', [ia_ss])))):.4f}", "A"),
        ("Back-EMF (E[sub]a[/sub])",                             f"{Ea_ss:.4f}", "V"),
        ("Terminal voltage (V[sub]t[/sub])",                     f"{Vt_ss:.4f}", "V"),
        ("Electrical power (P[sub]elec[/sub])",                  f"{P_elec:.3f}", "W"),
        ("Useful mechanical power (P[sub]mec[/sub])",            f"{P_mec_out:.3f}", "W"),
        ("Efficiency (eta)",                                     f"{eta:.2f}",   "%"),
    ]
    if exc not in ("series_motor",):
        rows_ss.insert(5, (
            "Steady-state field current (i[sub]fd[/sub])",
            f"{ifd_ss:.4f}", "A",
        ))
    _th(pdf, [("Quantity", 105), ("Value", 45), ("Unit", 20)])
    _tr(pdf, rows_ss, [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)
    return sec_n + 1


def _pdf_dc_section_loss_balance(pdf, losses: dict, sec_n: int) -> int:
    _ensure_space(pdf, 100)
    _sec(pdf, "Loss Balance (Steady State)", f"{sec_n}.")
    rows_loss = [
        ("Armature copper losses (P[sub]Ra[/sub])",
         f"{losses['P_Ra']:.4f}", "W", f"{losses['pct_Ra']:.1f}%"),
    ]
    if losses["P_Rf"] > 1e-9:
        rows_loss.append((
            "Field copper losses (P[sub]Rf[/sub])",
            f"{losses['P_Rf']:.4f}", "W", f"{losses['pct_Rf']:.1f}%",
        ))
    rows_loss += [
        ("Friction losses (P[sub]friction[/sub])",
         f"{losses['P_mec']:.4f}",     "W", f"{losses['pct_mec']:.1f}%"),
        ("Useful mechanical power (P[sub]mec[/sub])",
         f"{losses['P_mec_out']:.4f}", "W", f"{losses['pct_mec_out']:.1f}%"),
    ]
    _th(pdf, [("Component", 95), ("Value", 35), ("Unit", 18), ("% of P[sub]elec[/sub]", 22)])
    _tr(pdf, rows_loss, [95, 35, 18, 22], ["L", "R", "L", "R"])
    pdf.ln(2)
    embed_fig(pdf, fig_to_png_bytes(_build_losses_bar_dc(losses)), width_mm=170)
    _caption(pdf,
        "Percentage distribution of steady-state losses "
        "relative to input electrical power.")
    pdf.ln(2)
    return sec_n + 1


def _pdf_dc_section_curves(
    pdf, res: dict, t_events: list, var_keys: list, var_labels: list,
    exc: str, sec_n: int,
) -> int:
    dc_curve_keys   = ["ia", "wm", "Te"]
    dc_curve_labels = ["i_a (A)", "omega_m (rad/s)", "T_e (N.m)"]
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
        _sec(pdf, "Transient Curves", f"{sec_n}.")
        curves_fig = build_curves_fig(res, merged_keys, merged_labels, t_events or [])
        embed_fig(pdf, fig_to_png_bytes(curves_fig), width_mm=170)
        _caption(pdf,
            "Time evolution of electromechanical quantities during the simulation.")
        import matplotlib.pyplot as plt
        plt.close(curves_fig)
    return sec_n + 1


def _pdf_dc_section_diagnostics(
    pdf, res: dict, mp: DCMachineParams, sec_n: int,
) -> int:
    _ensure_space(pdf, 40)
    _sec(pdf, "Diagnostics and Observations", f"{sec_n}.")
    anomalias = _compute_anomalias_dc(res, mp)
    _COLORS_D = {"CRITICAL": (220, 38, 38), "WARNING": (217, 119, 6), "INFO": (22, 163, 74)}
    if not anomalias:
        pdf.set_fill_color(22, 163, 74)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, "  No anomalies detected.", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        _th(pdf, [("Severity", 30), ("Title", 85), ("Description", 55)])
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
    return sec_n + 1


def _pdf_dc_section_mode_analysis(
    pdf, res: dict, exp_type: str, exp_config: dict | None, sec_n: int,
) -> int:
    if not exp_config:
        return sec_n
    _ensure_space(pdf, 40)
    _sec(pdf, "Operating Mode Analysis", f"{sec_n}.")
    mode = exp_config.get("exp_type", exp_type)

    if mode == "frenagem_dc":
        brake = exp_config.get("brake_method", "plugging")
        _BRAKE_NAMES = {
            "plugging":    "Polarity Reversal (Plugging)",
            "injecao_cc":  "DC Injection Braking",
            "regenerativo":"Regenerative Braking",
        }
        _subsec(pdf, f"Electric Braking — {_BRAKE_NAMES.get(brake, brake)}")
        t_freia = exp_config.get("t_freia", 0.0)
        wm_arr  = np.asarray(res.get("wm", [0.0]))
        t_arr_m = np.asarray(res.get("t",  [0.0]))
        ia_arr  = np.asarray(res.get("ia",  [0.0]))
        idx_f   = int(np.searchsorted(t_arr_m, t_freia))
        wm_before = float(wm_arr[max(idx_f - 1, 0)]) if len(wm_arr) > 0 else 0.0
        ia_pk_brake = float(np.max(np.abs(ia_arr[idx_f:]))) if idx_f < len(ia_arr) else 0.0
        idx_stop = next((i for i in range(idx_f, len(wm_arr)) if abs(wm_arr[i]) < 1.0), len(wm_arr) - 1)
        t_stop = float(t_arr_m[idx_stop]) - t_freia if idx_stop < len(t_arr_m) else None
        rows_b = [
            ("Braking instant (t_brake)",       f"{t_freia:.3f} s"),
            ("Speed before braking",            f"{wm_before * 60 / (2*3.14159):.1f} RPM"),
            ("Post-braking peak current",       f"{ia_pk_brake:.3f} A"),
        ]
        if t_stop is not None:
            rows_b.append(("Estimated time to stop", f"{t_stop:.3f} s"))
        if brake == "injecao_cc":
            rows_b.append(("Injected DC voltage (V_inj)", f"{exp_config.get('Vdc_inj', 0.0):.2f} V"))
        elif brake == "regenerativo":
            rows_b.append(("Reduced voltage (V_a,regen)", f"{exp_config.get('Va_regen', 0.0):.2f} V"))
        _th(pdf, [("Indicator", 115), ("Value", 55)])
        _tr(pdf, rows_b, [115, 55], ["L", "L"])

    elif mode == "campo_fraco_dc":
        _subsec(pdf, "Field Weakening")
        t_campo = exp_config.get("t_campo", 0.0)
        Vf_fraco = exp_config.get("Vf_fraco", 0.0)
        wm_arr = np.asarray(res.get("wm", [0.0]))
        t_arr_m = np.asarray(res.get("t", [0.0]))
        idx_c = int(np.searchsorted(t_arr_m, t_campo))
        wm_before = float(wm_arr[max(idx_c - 1, 0)]) * 60 / (2*3.14159) if len(wm_arr) > 0 else 0.0
        wm_after  = float(wm_arr[-1]) * 60 / (2*3.14159) if len(wm_arr) > 0 else 0.0
        _th(pdf, [("Indicator", 115), ("Value", 55)])
        _tr(pdf, [
            ("Field weakening instant (t_campo)",      f"{t_campo:.3f} s"),
            ("Reduced field voltage (V_f,weak)",       f"{Vf_fraco:.2f} V"),
            ("Speed before field weakening",           f"{wm_before:.1f} RPM"),
            ("Speed after field weakening (steady)",   f"{wm_after:.1f} RPM"),
            ("Speed gain",                             f"{wm_after - wm_before:+.1f} RPM"),
        ], [115, 55], ["L", "L"])

    elif mode == "gerador_dc":
        _subsec(pdf, "Generator Mode — Power Analysis")
        ia_ss  = float(res.get("ia_ss",  0.0))
        wm_ss  = float(res.get("wm_ss",  0.0))
        Te_ss  = float(res.get("Te_ss",  0.0))
        Rl     = mp.Rl if hasattr(mp, "Rl") else 0.0
        Ea_ss  = float(res.get("Ea_ss",  0.0))
        Vt_ss  = float(res.get("Vt_ss",  0.0))
        P_mec_in  = abs(Te_ss) * abs(wm_ss)
        P_elec_out = Vt_ss ** 2 / Rl if Rl > 1e-6 else abs(ia_ss) * abs(Vt_ss)
        eta_gen = P_elec_out / P_mec_in * 100 if P_mec_in > 1e-3 else 0.0
        _th(pdf, [("Indicator", 115), ("Value", 55)])
        _tr(pdf, [
            ("Steady-state speed (n_ss)",            f"{wm_ss * 60 / (2*3.14159):.1f} RPM"),
            ("Terminal voltage (V_t,ss)",            f"{Vt_ss:.3f} V"),
            ("Armature current (I_a,ss)",            f"{ia_ss:.4f} A"),
            ("Back-EMF (E_a,ss)",                    f"{Ea_ss:.3f} V"),
            ("Input mechanical power",               f"{P_mec_in:.2f} W"),
            ("Generated electrical power",           f"{P_elec_out:.2f} W"),
            ("Estimated efficiency",                 f"{eta_gen:.1f} %"),
        ], [115, 55], ["L", "L"])

    return sec_n + 1


def _pdf_dc_section_param_estimation(
    pdf, mp: DCMachineParams, input_mode: str | None, sec_n: int,
) -> int:
    if not input_mode or input_mode == "Enter parameters manually":
        return sec_n
    _ensure_space(pdf, 50)
    _sec(pdf, "Parameter Estimation", f"{sec_n}.")
    if "Nameplate" in input_mode:
        _subsec(pdf, "Nameplate Method (NEMA — Heuristic)")
        _body(pdf, "  Parameters estimated from the machine nameplate data "
              "using NEMA heuristics. The values below were used in the simulation.")
    else:
        _subsec(pdf, "Test Method (IEEE Std 113-1985)")
        _body(pdf, "  Parameters determined from laboratory tests per "
              "IEEE Std 113-1985: armature DC test, field DC test, "
              "AC inductance test (Sec. 7.5.1) and no-load test (Sec. 5.6).")
    _th(pdf, [("Parameter", 85), ("Symbol", 30), ("Value", 55)])
    _tr(pdf, [
        ("Armature resistance",     "R_a",  f"{mp.Ra:.5f} Ohm"),
        ("Armature inductance",     "L_a",  f"{mp.La:.5f} H"),
        ("Back-EMF constant",       "k_b",  f"{mp.kb:.6f} V.s/rad"),
        ("Field resistance",        "R_f",  f"{mp.Rf:.4f} Ohm"),
        ("Field inductance",        "L_f",  f"{mp.Lf:.5f} H"),
        ("Moment of inertia",       "J",    f"{mp.J:.4f} kg.m2"),
        ("Viscous friction coeff.", "B",    f"{mp.B:.2e} N.m.s/rad"),
    ], [85, 30, 55], ["L", "C", "L"])
    return sec_n + 1


def _pdf_dc_section_integrator(
    pdf, res: dict, tmax: float, h: float, sec_n: int,
) -> int:
    _ensure_space(pdf, 55)
    _sec(pdf, "Numerical Integrator Parameters (LSODA)", f"{sec_n}.")
    t_arr  = np.asarray(res.get("t", [0.0, 1.0]))
    n_pts  = len(t_arr)
    dt_eff = float(t_arr[-1] - t_arr[0]) / max(n_pts - 1, 1)
    _th(pdf, [("Parameter", 115), ("Value", 55)])
    _tr(pdf, [
        ("Requested sampling step (h)",              f"{h:.6f} s"),
        ("Effective mean step",                       f"{dt_eff:.6f} s"),
        ("Total output points",                       str(n_pts)),
        ("Total simulated duration (t[sub]max[/sub])", f"{tmax:.3f} s"),
        ("Number of states",                          "4 (wm, ia, ifd/psi_f)"),
    ], [115, 55], ["L", "L"])
    _body(pdf,
          "  Integrator: LSODA (scipy.integrate.solve_ivp), adaptive step control, "
          "RTOL = 1e-5, ATOL = 1e-7.")
    pdf.ln(3)
    return sec_n + 1


# ─────────────────────────────────────────────────────────────────────────────
# Main simulation block — orchestrator
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
    exp_config: dict | None = None,
    input_mode: str | None = None,
) -> None:
    exc    = mp.excitation if mp else "sep_motor"
    losses = _compute_losses_dc(res, mp)

    _pdf_dc_cover(pdf, exp_label, exc)

    sec_n = 1
    sec_n = _pdf_dc_section_identification(pdf, res, mp, exp_label, exp_type, tmax, exc, sec_n)
    sec_n = _pdf_dc_section_machine_params(pdf, mp, exc, sec_n)
    sec_n = _pdf_dc_section_steady_state(pdf, res, mp, losses, exc, sec_n)
    sec_n = _pdf_dc_section_loss_balance(pdf, losses, sec_n)
    sec_n = _pdf_dc_section_curves(pdf, res, t_events, var_keys, var_labels, exc, sec_n)
    sec_n = _pdf_dc_section_diagnostics(pdf, res, mp, sec_n)
    sec_n = _pdf_dc_section_mode_analysis(pdf, res, exp_type, exp_config, sec_n)
    sec_n = _pdf_dc_section_param_estimation(pdf, mp, input_mode, sec_n)
    _pdf_dc_section_integrator(pdf, res, tmax, h, sec_n)


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
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
    exp_config: dict | None = None,
    input_mode: str | None = None,
    ref_list: list | None = None,
) -> bytes:
    """Generates DC machine technical PDF report and returns as bytes."""
    var_keys   = var_keys   or []
    var_labels = var_labels or []
    t_events   = t_events   or []
    ref_list   = ref_list   or []

    PDF = make_pdf_class("DC")
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_top_margin(20)

    # Main block
    _write_sim_block_dc(
        pdf, res, mp, exp_label, exp_type,
        t_events, var_keys, var_labels, tmax, h,
        exp_config=exp_config, input_mode=input_mode,
    )

    # Reference blocks (without extra mode/estimation sections)
    for ref_i, ref in enumerate(ref_list):
        ref_res = ref.get("res")
        if ref_res is None:
            continue
        ref_mp     = ref.get("mp", mp)
        ref_label  = ref.get("exp_label", f"Reference {ref_i+1}")
        ref_type   = ref.get("exp_type", exp_type)
        ref_tevs   = ref.get("t_events", [])
        ref_vkeys  = ref.get("var_keys") or var_keys
        ref_vlbls  = ref.get("var_labels") or var_labels
        ref_tmax   = ref.get("tmax", tmax)
        ref_h      = ref.get("h", h)
        _write_sim_block_dc(
            pdf, ref_res, ref_mp, ref_label, ref_type,
            ref_tevs, ref_vkeys, ref_vlbls, ref_tmax, ref_h,
        )

    return bytes(pdf.output())
