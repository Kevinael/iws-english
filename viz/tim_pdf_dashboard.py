# -*- coding: utf-8 -*-
"""
pdf_report_v2.py
================
Induction-machine PDF report v2 — supports two layout styles: IEEE-formal
(academic) and dashboard (KPI-focused).

Responsibilities:
  - Export generate_pdf_report_v2(style, ...) -> bytes; select layout via
    the style parameter ("academico" or "dashboard").
  - Provide _LATIN1_MAP for safe Unicode-to-latin-1 character substitution.

Relationships:
  Imported by : ui_components.sim_results (legacy path)
  Imports     : core.IWS_PY, viz.eqcircuit_plotter, ui.theme

Extending:
  - Prefer pdf_academico/pdf_industrial for new features; this module is a
    transitional version.
"""

from __future__ import annotations
import io
import numpy as np
from core.tim.facade import MachineParams
from viz.tim_eqcircuit import build_figure as _build_circuit_figure
from ui.theme import _palette
from viz.pdf_commons import (
    compute_trip_class,
    compute_thd_harmonics,
    compute_energy_metrics,
    tempfile_ctx,
    embed_fig,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────────────────────────────────────

# Substitution map: only characters outside latin-1 (code > 255).
# Portuguese accented characters (á, é, ã, ç, ó, etc.) are native latin-1 — NOT included here.
_LATIN1_MAP: dict[str, str] = {
    # dashes
    "—": "-",   # em dash
    "–": "-",   # en dash
    "−": "-",   # mathematical minus sign
    # omega / Greek letters
    "Ω": "Ohm",
    "η": "eta",
    "α": "alfa",
    "ω": "w",
    "μ": "u",
    # operators / mathematical symbols
    "·": ".",
    "²": "2",
    "³": "3",
    "¹": "1",
    "⁰": "0",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "⁻": "-",
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "≥": ">=",
    "≤": "<=",
    "×": "x",
    "°": " deg",
    "≠": "!=",
    "≈": "~",
    # others
    "'": "'",
    "'": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "½": "1/2",
    "∞": "inf",
    "Δ": "Delta",
    "Φ": "Phi",
    "φ": "phi",
    "σ": "sigma",
    "λ": "lambda",
    "∂": "d",
    "∫": "int",
    "√": "sqrt",
    "±": "+/-",
    "µ": "u",
    # literal Unicode sub/superscripts
    "ₑ": "e",
    "ₐ": "a",
    "ₛ": "s",
    "ᵣ": "r",
}


def _safe(text: str) -> str:
    """Converts text to latin-1-safe string for Helvetica (fpdf2 built-in).

    Preserves all accented characters (native latin-1).
    Substitutes only Unicode characters outside the latin-1 block (> U+00FF).
    """
    for ch, repl in _LATIN1_MAP.items():
        text = text.replace(ch, repl)
    # defensive encoding: any remaining non-latin-1 characters are discarded
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _fmt_power(val: float) -> tuple[str, str]:
    if abs(val) >= 1000:
        return f"{val/1000:.3f}", "kW"
    return f"{val:.2f}", "W"


def _fig_to_pdf_bytes(mpl_fig) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def _build_circuit_bytes(mp: MachineParams) -> bytes:
    """Generates the single-phase T equivalent circuit as PNG (bytes)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = _build_circuit_figure(mp, dark=False, palette_fn=_palette)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
# Inline sub/superscript text rendering
# Notation: "R[sub]s[/sub]" → R with 's' as subscript
#           "f[sup]2[/sup]" → f with '2' as superscript
# ─────────────────────────────────────────────────────────────────────────────

def _render_rich(pdf, text: str, main_size: int = 10, cell_h: float = 6.0,
                 fill: bool = False, align: str = "L", newline: bool = False) -> None:
    """Renders text with [sub]...[/sub] and [sup]...[/sup] markup.

    Advances cursor past the text; if newline=True, breaks line.
    """
    import re
    parts = re.split(r'(\[sub\].*?\[/sub\]|\[sup\].*?\[/sup\])', text)

    SUB_SIZE = max(6, main_size - 3)
    SUP_SIZE = max(6, main_size - 3)
    SUB_DY   =  2.0   # descent relative to baseline
    SUP_DY   = -2.0   # ascent relative to baseline

    x0 = pdf.get_x()
    y0 = pdf.get_y()

    for part in parts:
        if not part:
            continue
        if part.startswith("[sub]"):
            inner = part[5:-6]
            pdf.set_font("Helvetica", "", SUB_SIZE)
            pdf.set_xy(pdf.get_x(), y0 + SUB_DY)
            pdf.cell(pdf.get_string_width(inner) + 0.4, cell_h, inner,
                     border=0, fill=False)
            pdf.set_xy(pdf.get_x(), y0)
        elif part.startswith("[sup]"):
            inner = part[5:-6]
            pdf.set_font("Helvetica", "", SUP_SIZE)
            pdf.set_xy(pdf.get_x(), y0 + SUP_DY)
            pdf.cell(pdf.get_string_width(inner) + 0.4, cell_h, inner,
                     border=0, fill=False)
            pdf.set_xy(pdf.get_x(), y0)
        else:
            pdf.set_font("Helvetica", "", main_size)
            pdf.cell(pdf.get_string_width(part), cell_h, part,
                     border=0, fill=False)

    if newline:
        pdf.ln(cell_h)


def _cell_rich(pdf, text: str, w: float, h: float, main_size: int = 9,
               fill_rgb: tuple = (255, 255, 255), text_rgb: tuple = (40, 40, 40),
               align: str = "L") -> None:
    """Renders a fixed-width cell with sub/superscript support."""
    import re
    has_markup = bool(re.search(r'\[sub\]|\[sup\]', text))

    pdf.set_fill_color(*fill_rgb)
    x0, y0 = pdf.get_x(), pdf.get_y()

    # cell background
    pdf.cell(w, h, "", border=0, fill=True)
    pdf.set_xy(x0 + 2, y0)
    pdf.set_text_color(*text_rgb)

    if has_markup:
        _render_rich(pdf, text, main_size=main_size, cell_h=h)
    else:
        pdf.set_font("Helvetica", "", main_size)
        pdf.cell(w - 2, h, text, border=0, fill=False, align=align)

    pdf.set_xy(x0 + w, y0)


# ─────────────────────────────────────────────────────────────────────────────
# Extra-section computations
# ─────────────────────────────────────────────────────────────────────────────

def _compute_losses(res: dict, mp: MachineParams) -> dict:
    P_in   = float(res.get("P_in",    0.0))
    P_gap  = float(res.get("P_gap",   0.0))
    P_mec  = float(res.get("P_mec",   0.0))
    P_cu_r = float(res.get("P_cu_r",  0.0))

    iqs_ss = np.asarray(res["iqs"], dtype=float)
    ids_ss = np.asarray(res["ids"], dtype=float)
    ss     = int(res.get("_ss_start", max(0, len(iqs_ss) - 1)))
    iqs_m  = float(np.sqrt(np.mean(iqs_ss[ss:]**2))) if ss < len(iqs_ss) else 0.0
    ids_m  = float(np.sqrt(np.mean(ids_ss[ss:]**2))) if ss < len(ids_ss) else 0.0
    P_cu_s = (3.0 / 2.0) * mp.Rs * (iqs_m**2 + ids_m**2)

    Vqs_ss = np.asarray(res["Vqs"][ss:], dtype=float)
    Vds_ss = np.asarray(res["Vds"][ss:], dtype=float)
    if mp.Rfe > 0 and len(Vqs_ss) > 0:
        V_rms_sq = float(np.mean(Vqs_ss**2)) + float(np.mean(Vds_ss**2))
        P_fe = (3.0 / 2.0) * V_rms_sq / mp.Rfe
    else:
        P_fe = max(abs(P_in - P_gap - P_cu_s), 0.0) if P_in > 0 else 0.0

    P_loss_total = P_cu_s + P_cu_r + P_fe
    denom = P_in if abs(P_in) > 1.0 else 1.0

    return {
        "P_in":     P_in,   "P_mec":   P_mec,
        "P_cu_s":   P_cu_s, "P_cu_r":  P_cu_r,
        "P_fe":     P_fe,   "P_loss":  P_loss_total,
        "pct_cu_s": P_cu_s / denom * 100.0,
        "pct_cu_r": P_cu_r / denom * 100.0,
        "pct_fe":   P_fe   / denom * 100.0,
        "pct_mec":  P_mec  / denom * 100.0,
    }


def _compute_integrator_params(res: dict, mp: MachineParams, tmax: float, h: float) -> dict:
    t       = np.asarray(res["t"], dtype=float)
    n_steps = len(t)
    dt_eff  = float(t[-1] - t[0]) / max(n_steps - 1, 1) if n_steps > 1 else h
    nyquist_ok = mp.f * h <= 0.1
    return {
        "n_steps":          n_steps,
        "dt_eff":           dt_eff,
        "tmax":             tmax,
        "h_req":            h,
        "nyquist_ok":       nyquist_ok,
        "samples_per_cycle": 1.0 / (mp.f * dt_eff) if mp.f * dt_eff > 0 else 0.0,
    }


def _compute_broken_bar(res: dict, mp: MachineParams) -> dict | None:
    alpha = float(res.get("_broken_bar_severity", 0.0))
    if alpha <= 0:
        return None
    s_val  = float(res.get("s", 0.0))
    f_fund = mp.f
    f_lo   = f_fund * (1.0 - 2.0 * abs(s_val))
    f_hi   = f_fund * (1.0 + 2.0 * abs(s_val))

    ss    = int(res.get("_ss_start", 0))
    ias   = np.asarray(res.get("ias", []), dtype=float)[ss:]
    t_arr = np.asarray(res["t"][ss:], dtype=float)
    sb_ratio_lo = sb_ratio_hi = 0.0

    if len(ias) >= 16:
        dt   = float(t_arr[1] - t_arr[0]) if len(t_arr) > 1 else 1e-3
        N    = len(ias)
        spec = np.abs(np.fft.rfft(ias)) * 2.0 / N
        freq = np.fft.rfftfreq(N, d=dt)
        if (freq > 0).any():
            f1_idx = int(np.argmax(spec[freq > 0.1])) + np.searchsorted(freq, 0.1)
            A1     = float(spec[f1_idx]) if f1_idx < len(spec) else 1.0
            if A1 > 0:
                def _amp_near(f_target):
                    idx_f = int(np.argmin(np.abs(freq - f_target)))
                    lo, hi = max(0, idx_f - 2), min(len(spec), idx_f + 3)
                    return float(spec[lo:hi].max()) if lo < hi else 0.0
                sb_ratio_lo = _amp_near(f_lo) / A1 * 100.0
                sb_ratio_hi = _amp_near(f_hi) / A1 * 100.0

    severity_label = "Severe" if alpha >= 0.5 else ("Moderate" if alpha >= 0.2 else "Mild")
    return {
        "alpha": alpha, "s_val": s_val,
        "f_lo": f_lo, "f_hi": f_hi,
        "sb_ratio_lo": sb_ratio_lo, "sb_ratio_hi": sb_ratio_hi,
        "severity_label": severity_label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Matplotlib figures
# ─────────────────────────────────────────────────────────────────────────────

def _build_abc_currents_fig(res: dict) -> "matplotlib.figure.Figure":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ss     = int(res.get("_ss_start", 0))
    t      = np.asarray(res["t"][ss:], dtype=float)
    keys   = ["ias", "ibs", "ics"]
    colors = ["#1d4ed8", "#ea580c", "#16a34a"]
    labels = ["$i_{as}$ (A)", "$i_{bs}$ (A)", "$i_{cs}$ (A)"]

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.2), sharey=True)
    fig.patch.set_facecolor("white")

    for ax, key, color, lbl in zip(axes, keys, colors, labels):
        y = np.asarray(res.get(key, np.zeros_like(t)), dtype=float)[ss:]
        n = min(len(t), len(y))
        ax.plot(t[:n], y[:n], color=color, linewidth=1.1)
        rms_key = key + "_rms"
        y_rms = float(res.get(rms_key,
                      float(np.sqrt(np.mean(y[:n]**2))) if n > 0 else 0.0))
        ax.axhline( y_rms, color=color, linewidth=0.8, linestyle="--", alpha=0.65,
                    label=f"RMS = {y_rms:.3f} A")
        ax.axhline(-y_rms, color=color, linewidth=0.8, linestyle="--", alpha=0.65)
        ax.set_title(lbl, fontsize=9, fontweight="bold")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_facecolor("#f9fafc")
        ax.grid(True, color="#dde4f5", linewidth=0.4)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=7, framealpha=0.8)

    axes[0].set_ylabel("Current (A)", fontsize=8)
    fig.suptitle("ABC Phase Currents — Steady State", fontsize=10, fontweight="bold")
    fig.tight_layout()
    return fig


def _build_losses_bar_fig(losses: dict) -> "matplotlib.figure.Figure":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cats   = [
        "Stator copper\nlosses  $P_{cu,s}$",
        "Rotor copper\nlosses  $P_{cu,r}$",
        "Iron\nlosses  $P_{fe}$",
        "Mechanical\npower  $P_{mec}$",
    ]
    vals   = [losses["P_cu_s"], losses["P_cu_r"], losses["P_fe"],
              max(losses["P_mec"], 0.0)]
    colors = ["#1d4ed8", "#7c3aed", "#dc2626", "#16a34a"]
    pcts   = [losses["pct_cu_s"], losses["pct_cu_r"],
              losses["pct_fe"],   losses["pct_mec"]]

    fig, ax = plt.subplots(figsize=(10, 3.4))
    fig.patch.set_facecolor("white")
    bars = ax.barh(cats, vals, color=colors, alpha=0.85, height=0.5)
    max_val = max(vals) if any(v > 0 for v in vals) else 1.0
    for bar, pct, val in zip(bars, pcts, vals):
        v_str, u_str = _fmt_power(val)
        ax.text(bar.get_width() + max_val * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{v_str} {u_str}  ({pct:.1f}%)",
                va="center", fontsize=8, color="#1e293b")
    ax.set_xlabel("Power (W)", fontsize=8)
    ax.set_title("Loss Balance — Steady State", fontsize=9, fontweight="bold")
    ax.tick_params(labelsize=8)
    ax.set_facecolor("#f9fafc")
    ax.grid(True, axis="x", color="#dde4f5", linewidth=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def _build_curves_fig(res: dict, var_keys: list, var_labels: list,
                       t_events: list, color_offset: int = 0) -> "matplotlib.figure.Figure":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    COLORS = ["#1d4ed8", "#ea580c", "#16a34a", "#7c3aed",
              "#db2777", "#0d9488", "#d97706", "#4f46e5"]
    n   = max(1, len(var_keys))
    t   = res["t"]
    fig, axes = plt.subplots(n, 1, figsize=(11, 3.0 * n), sharex=True)
    if n == 1:
        axes = [axes]
    fig.patch.set_facecolor("white")

    for i, (key, lbl, ax) in enumerate(zip(var_keys, var_labels, axes)):
        color = COLORS[(i + color_offset) % len(COLORS)]
        y     = np.asarray(res.get(key, np.zeros_like(t)), dtype=float)
        ax.plot(t, y, color=color, linewidth=1.1, solid_capstyle="round")
        ax.set_ylabel(lbl, fontsize=9)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.tick_params(labelsize=8)
        ax.set_facecolor("#f9fafc")
        ax.grid(True, color="#dde4f5", linewidth=0.4)
        ax.spines[["top", "right"]].set_visible(False)
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
        for te in (t_events or []):
            ax.axvline(x=te, color="#94a3b8", linewidth=0.8, linestyle="--")
        pk_idx = int(np.argmax(np.abs(y)))
        ax.plot(float(t[pk_idx]), float(y[pk_idx]), "^",
                color="#dc2626", markersize=5, zorder=5,
                label=f"Peak: {float(np.abs(y[pk_idx])):.2f}")
        ss = int(res.get("_ss_start", len(y) - 1))
        if ss < len(y):
            ax.axvline(x=float(t[ss]), color="#16a34a",
                       linewidth=0.7, linestyle=":", alpha=0.6)
        ax.legend(fontsize=7, loc="upper right", framealpha=0.8)

    fig.subplots_adjust(left=0.10, right=0.96, top=0.96, bottom=0.06, hspace=0.65)
    return fig


AFFINITY_GROUPS = [
    ["Te", "n", "wr"],
    ["ias", "ibs", "ics"],
    ["iar", "ibr", "icr"],
    ["ids", "iqs"],
    ["idr", "iqr"],
    ["Va", "Vb", "Vc"],
]


def _make_chunks(keys, labels):
    key_to_lbl = dict(zip(keys, labels))
    chunks_out, assigned = [], set()
    for grp in AFFINITY_GROUPS:
        ck = [k for k in grp if k in key_to_lbl and k not in assigned]
        if ck:
            chunks_out.append((ck, [key_to_lbl[k] for k in ck]))
            assigned.update(ck)
    rest_k = [k for k in keys if k not in assigned]
    rest_l = [key_to_lbl[k] for k in rest_k]
    for i in range(0, len(rest_k), 4):
        chunks_out.append((rest_k[i:i+4], rest_l[i:i+4]))
    return chunks_out if chunks_out else [(keys, labels)]


# ─────────────────────────────────────────────────────────────────────────────
# BASE PDF CLASS — shared header, footer and primitives
# ─────────────────────────────────────────────────────────────────────────────

def _make_pdf_class(style: str):
    from fpdf import FPDF
    import datetime

    style_label = ("Structured Academic"
                   if style == "academico" else "Technical Dashboard")

    class EMS_PDF_V2(FPDF):
        def normalize_text(self, text: str) -> str:
            return super().normalize_text(_safe(text))

        def header(self):
            if self.page_no() == 1:
                return
            self.set_fill_color(235, 240, 255)
            self.rect(0, 0, 210, 16, style="F")
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(22, 54, 120)
            self.set_xy(20, 4)
            self.cell(100, 8,
                      f"IWS - Report V2 ({style_label})",
                      border=0)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 100, 100)
            self.set_xy(130, 4)
            ts = datetime.datetime.now().strftime("%Y-%m-%d")
            self.cell(60, 8, f"Generated: {ts}", border=0, align="R")
            self.ln(6)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8,
                      f"Page {self.page_no()} of {{nb}}",
                      align="C")

    return EMS_PDF_V2


# ─────────────────────────────────────────────────────────────────────────────
# ACADEMIC STYLE
# ─────────────────────────────────────────────────────────────────────────────

def _generate_academico(
    pdf, exp_label: str, mp: MachineParams, res: dict,
    var_keys: list, var_labels: list, t_events: list,
    exp_type: str, energy_tariff: float,
    losses: dict, integrator: dict, broken_bar: dict | None,
    insights: list | None = None, load_torque: float = 0.0,
) -> None:
    import datetime

    # ── local helpers ─────────────────────────────────────────────────────

    def sec(title: str, num: str = "") -> None:
        pdf.set_fill_color(22, 54, 120)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        label = f"  {num}  {title}" if num else f"  {title}"
        pdf.cell(0, 8, label, border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def subsec(title: str) -> None:
        pdf.set_fill_color(220, 228, 248)
        pdf.set_text_color(20, 30, 80)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"   {title}", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def body(text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5, text)
        pdf.ln(1)

    def caption(text: str) -> None:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, text, border=0, align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def th(cols: list[tuple[str, float]]) -> None:
        """Table header with sub/superscript support."""
        pdf.set_fill_color(200, 210, 245)
        pdf.set_text_color(20, 20, 80)
        x0, y0 = pdf.get_x(), pdf.get_y()
        for lbl, w in cols:
            _cell_rich(pdf, f"  {lbl}", w, 6, main_size=9,
                       fill_rgb=(200, 210, 245), text_rgb=(20, 20, 80))
        pdf.set_xy(x0, y0 + 6)
        pdf.ln(0)

    def tr(rows: list[tuple], widths: list[float], aligns: list[str]) -> None:
        """Table rows with zebra striping and sub/superscript support."""
        for idx, row in enumerate(rows):
            fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
            x0, y0 = pdf.get_x(), pdf.get_y()
            for cell, w, align in zip(row, widths, aligns):
                _cell_rich(pdf, f"  {str(cell)}", w, 6, main_size=9,
                           fill_rgb=fill, text_rgb=(40, 40, 40))
            pdf.set_xy(x0, y0 + 6)
            pdf.ln(0)

    # ── Cover ─────────────────────────────────────────────────────────────
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
    pdf.cell(0, 8, "Version 2 — Structured Academic Style",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 44)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Experiment: {exp_label}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 54)
    pdf.set_font("Helvetica", "I", 9)
    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    pdf.cell(0, 6, f"Generated: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── 1. Experiment Identification ──────────────────────────────────────
    sec("Experiment Identification", "1.")
    th([("Attribute", 90), ("Value", 80)])
    tr([
        ("Experiment",                         exp_label),
        ("Start-up / operation type",          exp_type.upper()),
        ("Synchronous speed",                  f"{mp.n_sync:.1f} RPM"),
        ("Rated frequency",                    f"{mp.f:.1f} Hz"),
        ("Number of poles",                    str(mp.p)),
        ("Line voltage (V[sub]l[/sub])",       f"{mp.Vl:.1f} V"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)

    # ── 2. Machine Parameters ─────────────────────────────────────────────
    sec("Machine Parameters", "2.")
    th([("Parameter", 100), ("Value", 45), ("Unit", 25)])
    tr([
        ("Stator resistance (R[sub]s[/sub])",                    f"{mp.Rs:.4f}",  "Ohm"),
        ("Rotor resistance (R[sub]r[/sub])",                     f"{mp.Rr:.4f}",  "Ohm"),
        ("Magnetising reactance (X[sub]m[/sub])",                f"{mp.Xm:.4f}",  "Ohm"),
        ("Stator leakage reactance (X[sub]ls[/sub])",            f"{mp.Xls:.4f}", "Ohm"),
        ("Rotor leakage reactance (X[sub]lr[/sub])",             f"{mp.Xlr:.4f}", "Ohm"),
        ("Iron-loss resistance (R[sub]fe[/sub])",                f"{mp.Rfe:.1f}", "Ohm"),
        ("Moment of inertia (J)",                                 f"{mp.J:.4f}",   "kg.m2"),
        ("Friction coefficient (B)",                              f"{mp.B:.4f}",   "N.m.s/rad"),
    ], [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)

    # ── 2.1 Single-Phase T Equivalent Circuit ─────────────────────────────
    CIRC_MIN = 85
    if (pdf.h - pdf.b_margin) - pdf.get_y() < CIRC_MIN:
        pdf.add_page()
    subsec("2.1  Single-Phase T Equivalent Circuit")
    pdf.ln(1)
    embed_fig(pdf, _build_circuit_bytes(mp), width_mm=160)
    caption(
        "Figure 2.1 — Single-phase T equivalent circuit of the Three-Phase Induction Motor. "
        "R[sub]s[/sub]: stator resistance; X[sub]ls[/sub]: stator leakage reactance; "
        "X[sub]m[/sub]: magnetising reactance; R[sub]fe[/sub]: iron-loss resistance; "
        "X[sub]lr[/sub]: rotor leakage reactance; R[sub]r[/sub]/s: rotor resistance referred to stator."
    )
    pdf.ln(3)

    # ── 3. Steady-State Indicators ────────────────────────────────────────
    pdf.add_page()
    sec("Steady-State Indicators", "3.")
    P_gap  = float(res.get("P_gap",  0.0))
    P_mec  = float(res.get("P_mec",  0.0))
    P_cu_r = float(res.get("P_cu_r", 0.0))
    P_in   = float(res.get("P_in",   0.0))
    s_val  = float(res.get("s",      0.0))
    eta    = float(res.get("eta",    0.0))
    vi, ui   = _fmt_power(P_in)
    vg, ug   = _fmt_power(P_gap)
    vm, um   = _fmt_power(P_mec)
    vcr, ucr = _fmt_power(P_cu_r)
    th([("Quantity", 105), ("Value", 45), ("Unit", 20)])
    tr([
        ("Steady-state speed",
         f"{res['n_ss']:.3f}",                                "RPM"),
        ("Rotor angular velocity (omega[sub]r[/sub])",
         f"{res['wr_ss']:.4f}",                               "rad/s"),
        ("Steady-state electromagnetic torque (T[sub]e[/sub])",
         f"{res['Te_ss']:.4f}",                               "N.m"),
        ("Maximum electromagnetic torque (T[sub]e,max[/sub])",
         f"{float(np.max(res['Te'])):.4f}",                   "N.m"),
        ("Slip (s)",
         f"{s_val*100:.3f}",                                  "%"),
        ("RMS line current (I[sub]as,rms[/sub])",
         f"{res['ias_rms']:.4f}",                              "A"),
        ("Peak current (I[sub]as,pk[/sub])",
         f"{float(np.max(np.abs(res['ias']))):.4f}",           "A"),
        ("Input power (P[sub]in[/sub])",                       vi,  ui),
        ("Air-gap power (P[sub]gap[/sub])",                    vg,  ug),
        ("Mechanical power (P[sub]mec[/sub])",                 vm,  um),
        ("Rotor copper losses (P[sub]cu,r[/sub])",             vcr, ucr),
        ("Efficiency (eta)",
         f"{eta:.3f}",                                         "%"),
    ], [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)

    # ── 4. Loss Balance ───────────────────────────────────────────────────
    LOSS_MIN = 100
    if (pdf.h - pdf.b_margin) - pdf.get_y() < LOSS_MIN:
        pdf.add_page()
    sec("Loss Balance (Steady State)", "4.")
    lf,  uf  = _fmt_power(losses["P_cu_s"])
    lg,  ug_ = _fmt_power(losses["P_cu_r"])
    lh,  uh  = _fmt_power(losses["P_fe"])
    li,  ui_ = _fmt_power(max(losses["P_mec"], 0.0))
    th([("Component", 100), ("Value", 38), ("Unit", 18), ("% of P[sub]in[/sub]", 24)])
    tr([
        ("Stator copper losses (P[sub]cu,s[/sub])",   lf,  uf,  f"{losses['pct_cu_s']:.1f}%"),
        ("Rotor copper losses (P[sub]cu,r[/sub])",    lg,  ug_, f"{losses['pct_cu_r']:.1f}%"),
        ("Iron losses (P[sub]fe[/sub])",              lh,  uh,  f"{losses['pct_fe']:.1f}%"),
        ("Useful mechanical power (P[sub]mec[/sub])", li,  ui_, f"{losses['pct_mec']:.1f}%"),
    ], [100, 38, 18, 24], ["L", "R", "L", "R"])
    pdf.ln(2)
    loss_fig = _build_losses_bar_fig(losses)
    embed_fig(pdf, _fig_to_pdf_bytes(loss_fig), width_mm=155)
    caption(
        "Figure 4.1 — Percentage distribution of steady-state losses "
        "relative to input power Pin."
    )
    pdf.ln(2)

    # ── 5. Numerical Integrator Parameters ───────────────────────────────
    INTEG_MIN = 55
    if (pdf.h - pdf.b_margin) - pdf.get_y() < INTEG_MIN:
        pdf.add_page()
    sec("Numerical Integrator Parameters (LSODA)", "5.")
    ny_status = ("Satisfied (>= 10 samples/cycle)"
                 if integrator["nyquist_ok"]
                 else "WARNING: insufficient — RMS and FFT may be inaccurate")
    th([("Parameter", 115), ("Value", 55)])
    tr([
        ("Requested sampling step (h)",                          f"{integrator['h_req']:.6f} s"),
        ("Effective mean step",                                   f"{integrator['dt_eff']:.6f} s"),
        ("Samples per cycle (f[sub]n[/sub] / h[sub]eff[/sub])", f"{integrator['samples_per_cycle']:.1f}"),
        ("Total output points",                                   str(integrator["n_steps"])),
        ("Total simulated duration (t[sub]max[/sub])",           f"{integrator['tmax']:.3f} s"),
        ("Nyquist criterion",                                     ny_status),
    ], [115, 55], ["L", "L"])
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5,
        "  Integrator: LSODA (scipy.integrate.solve_ivp), adaptive step control, "
        "RTOL = 1e-5, ATOL = 1e-6.")
    pdf.ln(3)

    # ── 6. Fault Indicators — Broken Bar (MCSA) ───────────────────────────
    if broken_bar is not None:
        BB_MIN = 60
        if (pdf.h - pdf.b_margin) - pdf.get_y() < BB_MIN:
            pdf.add_page()
        sec("Fault Indicators — Broken Bar (MCSA)", "6.")
        subsec("Current Spectral Analysis (Motor Current Signature Analysis)")
        th([("Indicator", 115), ("Value", 55)])
        tr([
            ("Severity (alpha)",                                    f"{broken_bar['alpha']:.3f}"),
            ("Severity classification",                             broken_bar["severity_label"]),
            ("Steady-state slip (s)",                               f"{broken_bar['s_val']*100:.3f} %"),
            ("Lower sideband frequency (1-2s)f",                   f"{broken_bar['f_lo']:.2f} Hz"),
            ("Upper sideband frequency (1+2s)f",                   f"{broken_bar['f_hi']:.2f} Hz"),
            ("Relative amplitude of (1-2s)f / fundamental",        f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Relative amplitude of (1+2s)f / fundamental",        f"{broken_bar['sb_ratio_hi']:.2f} %"),
        ], [115, 55], ["L", "L"])
        body(
            "Reference: IEEE 1159-2019 — Motor Current Signature Analysis (MCSA). "
            "Relative sideband amplitude above 3% of the fundamental indicates incipient fault; "
            "above 10% indicates severe fault."
        )
        pdf.ln(2)
        sec_num = "7."
    else:
        sec_num = "6."

    # ── Power Quality (THD + PF + Economic) ───────────────────────────────
    if exp_type != "shutdown":
        _em = compute_energy_metrics(res, mp, energy_tariff)
        QE_MIN = 60
        if (pdf.h - pdf.b_margin) - pdf.get_y() < QE_MIN:
            pdf.add_page()
        sec(f"Power Quality and Economic Analysis", sec_num)
        _thd_ok  = _em["thd"] <= 5.0
        _fp_ok   = _em["fp"] >= 0.85
        th([("Quantity", 110), ("Value", 40), ("Status / Unit", 20)])
        tr([
            ("Power Factor (PF)",                              f"{_em['fp']:.4f}",            "OK" if _fp_ok else "LOW"),
            ("Current THD (I[sub]as[/sub])",                   f"{_em['thd']:.2f} %",         "OK" if _thd_ok else "HIGH"),
            ("Energy consumed in experiment",                  f"{_em['E_kwh']:.6f}",          "kWh"),
            ("Experiment cost",                                f"$ {_em['custo_exp']:.4f}",    "$"),
            ("Steady-state input power",                       f"{_em['P_in_kw']:.3f}",        "kW"),
            ("Steady-state efficiency",                        f"{_em['eta']:.2f}",            "%"),
            ("Projected annual operating cost (8760 h)",       f"$ {_em['custo_ano']:,.2f}",   "$/yr"),
        ], [110, 40, 20], ["L", "R", "L"])
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, f"  Tariff: $ {energy_tariff:.2f}/kWh. THD and PF computed via FFT in the steady-state window.",
                 border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # harmonic spectrum by order
        _harm_rows = compute_thd_harmonics(res, mp)
        if _harm_rows:
            HARM_MIN = 40
            if (pdf.h - pdf.b_margin) - pdf.get_y() < HARM_MIN:
                pdf.add_page()
            subsec("Harmonic Spectrum of I[sub]as[/sub] — Orders 1 to 9")
            th([("Order", 25), ("Frequency (Hz)", 45), ("Amplitude (A)", 55), ("Relative (%)", 45)])
            tr([
                (f"{k}", f"{fk:.1f}", f"{Ak:.4f}", f"{pct:.2f}")
                for k, fk, Ak, pct in _harm_rows
            ], [25, 45, 55, 45], ["C", "R", "R", "R"])
            body("Relative amplitudes normalised by the fundamental. Reference: IEEE 519-2022.")
            pdf.ln(2)
        sec_num = str(int(sec_num[:-1]) + 1) + "."

    # ── Trip Class ────────────────────────────────────────────────────────
    if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
        _tc = compute_trip_class(res, mp)
        if _tc is not None:
            TC_MIN = 40
            if (pdf.h - pdf.b_margin) - pdf.get_y() < TC_MIN:
                pdf.add_page()
            sec("Protection Recommendation — Overload Relay", sec_num)
            _tc_color = {10: (22, 163, 74), 20: (217, 119, 6), 30: (220, 38, 38)}
            r_, g_, b__ = _tc_color.get(_tc["class"], (80, 80, 80))
            pdf.set_fill_color(r_, g_, b__)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 8,
                     f"  Class {_tc['class']} — t_acceleration = {_tc['t_accel']:.2f} s "
                     f"(95% of {_tc['n_sync']:.1f} RPM) — {_tc['status']}",
                     border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
            body("Reference: IEC 60947-4-1 / NEMA ICS 2. "
                 "Class 10: t < 10 s | Class 20: 10-20 s | Class 30: > 20 s.")
            pdf.ln(2)
            sec_num = str(int(sec_num[:-1]) + 1) + "."

    # ── Expert Diagnostics ────────────────────────────────────────────────
    if insights:
        DIAG_MIN = 40
        if (pdf.h - pdf.b_margin) - pdf.get_y() < DIAG_MIN:
            pdf.add_page()
        sec("Automated Diagnostics", sec_num)
        _COLORS = {"error": (220, 38, 38), "warning": (217, 119, 6), "info": (22, 163, 74)}
        _LABELS = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}
        for ins in insights:
            r_, g_, b__ = _COLORS.get(ins.level, (80, 80, 80))
            lbl_ = _LABELS.get(ins.level, ins.level.upper())
            pdf.set_fill_color(r_, g_, b__)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 7, f"  [{lbl_}]  {ins.title}", border=0, fill=True,
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"  {ins.body}", border=0)
            pdf.ln(2)
        sec_num = str(int(sec_num[:-1]) + 1) + "."

    # ── ABC Phase Currents ────────────────────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        ABC_MIN = 80
        if (pdf.h - pdf.b_margin) - pdf.get_y() < ABC_MIN:
            pdf.add_page()
        sec("ABC Phase Currents — Steady State", sec_num)
        abc_fig = _build_abc_currents_fig(res)
        embed_fig(pdf, _fig_to_pdf_bytes(abc_fig), width_mm=165)
        ias_rms = float(res.get("ias_rms", 0.0))
        caption(
            f"Figure {sec_num[:-1]}.1 - Phase currents ias, ibs, ics in steady state. "
            f"Dashed: +/- RMS (Ias,rms = {ias_rms:.3f} A). "
            "Balanced system: equal amplitudes, 120 deg phase shift."
        )
        pdf.ln(2)
        sec_num_curves = str(int(sec_num[:-1]) + 1) + "."
    else:
        sec_num_curves = sec_num

    # ── N. Characteristic Curves ──────────────────────────────────────────
    chunks = _make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        sec(f"Characteristic Curves{sfx}",
            f"{sec_num_curves[:-1]}." if pg == 0 else "")
        curves_fig = _build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig(pdf, _fig_to_pdf_bytes(curves_fig), width_mm=165)
        caption(", ".join(cl))


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL DASHBOARD STYLE
# ─────────────────────────────────────────────────────────────────────────────

def _generate_dashboard(
    pdf, exp_label: str, mp: MachineParams, res: dict,
    var_keys: list, var_labels: list, t_events: list,
    exp_type: str, energy_tariff: float,
    losses: dict, integrator: dict, broken_bar: dict | None,
    insights: list | None = None, load_torque: float = 0.0,
) -> None:
    import datetime

    BG_DARK  = (10, 30, 80)
    BG_CARD  = (240, 244, 255)
    ACCENT   = (29, 78, 216)
    TEXT_DRK = (15, 23, 42)
    TEXT_MID = (51, 65, 85)
    TEXT_LGT = (100, 116, 139)
    GREEN    = (22, 163, 74)
    RED      = (220, 38, 38)

    def dash_title(title: str, subtitle: str = "") -> None:
        pdf.set_fill_color(*BG_DARK)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, f"  {title}", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            pdf.set_fill_color(*ACCENT)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 6, f"  {subtitle}", border=0, fill=True,
                     new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    def kpi_row(items: list[tuple[str, str, str]]) -> None:
        n = len(items)
        if n == 0:
            return
        w = 170.0 / n
        x_start = pdf.get_x()
        y0 = pdf.get_y()
        for lbl, val, unit in items:
            x0 = pdf.get_x()
            pdf.set_fill_color(*BG_CARD)
            pdf.cell(w, 14, "", border=0, fill=True)
            pdf.set_xy(x0 + 2, y0 + 1)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*TEXT_DRK)
            pdf.cell(w - 4, 6, val, border=0)
            pdf.set_xy(x0 + 2, y0 + 7)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*TEXT_MID)
            pdf.cell(w - 4, 5, f"{lbl} ({unit})", border=0)
            pdf.set_xy(x0 + w, y0)
        pdf.set_xy(x_start, y0 + 14)
        pdf.ln(2)

    def sec_bar(title: str) -> None:
        pdf.set_fill_color(*ACCENT)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"  {title}", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def mini_table(rows: list[tuple], widths: list[float]) -> None:
        for idx, row in enumerate(rows):
            fill = (240, 244, 255) if idx % 2 == 0 else (255, 255, 255)
            x0, y0 = pdf.get_x(), pdf.get_y()
            for cell, w in zip(row, widths):
                _cell_rich(pdf, f"  {str(cell)}", w, 6, main_size=9,
                           fill_rgb=fill, text_rgb=TEXT_DRK)
            pdf.set_xy(x0, y0 + 6)
            pdf.ln(0)

    def status_badge(ok: bool, msg: str) -> None:
        pdf.set_fill_color(*(GREEN if ok else RED))
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, f"  {msg}", border=0, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── Dashboard Cover ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*BG_DARK)
    pdf.rect(0, 0, 210, 58, style="F")
    pdf.set_xy(20, 12)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "IWS SIMULATOR", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 28)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8,
             "Technical Simulation Dashboard — Version 2",
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
    dash_title("PERFORMANCE", f"Steady State — {exp_type.upper()}")
    n_ss    = float(res.get("n_ss",    0.0))
    Te_ss   = float(res.get("Te_ss",   0.0))
    ias_rms = float(res.get("ias_rms", 0.0))
    eta     = float(res.get("eta",     0.0))
    s_val   = float(res.get("s",       0.0))
    P_in    = float(res.get("P_in",    0.0))
    v_pin, u_pin = _fmt_power(P_in)
    kpi_row([
        ("Steady-State Speed",       f"{n_ss:.1f}",    "RPM"),
        ("Steady-State Torque Te",   f"{Te_ss:.2f}",   "N.m"),
        ("RMS Current Ias",          f"{ias_rms:.3f}", "A"),
        ("Efficiency eta",           f"{eta:.2f}",     "%"),
    ])
    kpi_row([
        ("Slip s",                   f"{s_val*100:.3f}",  "%"),
        ("Input Power",              v_pin,                u_pin),
        ("Number of Poles p",        str(mp.p),             "—"),
        ("Line Voltage Vl",          f"{mp.Vl:.1f}",        "V"),
    ])

    # ── Loss Balance ──────────────────────────────────────────────────────
    sec_bar("LOSS BALANCE")
    loss_fig = _build_losses_bar_fig(losses)
    embed_fig(pdf, _fig_to_pdf_bytes(loss_fig), width_mm=160)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*TEXT_LGT)
    vcs, ucs   = _fmt_power(losses["P_cu_s"])
    vcr_, ucr_ = _fmt_power(losses["P_cu_r"])
    vfe, ufe   = _fmt_power(losses["P_fe"])
    pdf.cell(0, 5,
             f"  Pcu,s = {vcs} {ucs} ({losses['pct_cu_s']:.1f}%)  |  "
             f"Pcu,r = {vcr_} {ucr_} ({losses['pct_cu_r']:.1f}%)  |  "
             f"Pfe = {vfe} {ufe} ({losses['pct_fe']:.1f}%)",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Numerical Integrator ──────────────────────────────────────────────
    INTEG_MIN = 52
    if (pdf.h - pdf.b_margin) - pdf.get_y() < INTEG_MIN:
        pdf.add_page()
    sec_bar("NUMERICAL INTEGRATOR (LSODA)")
    ny_ok = integrator["nyquist_ok"]
    status_badge(ny_ok,
                 "Nyquist criterion: satisfied (>= 10 samples/cycle)"
                 if ny_ok else
                 "WARNING: Nyquist criterion not satisfied — RMS and FFT may be inaccurate")
    mini_table([
        ("Requested step (h)",                      f"{integrator['h_req']:.6f} s"),
        ("Effective mean step",                      f"{integrator['dt_eff']:.6f} s"),
        ("Samples per cycle",                        f"{integrator['samples_per_cycle']:.1f}"),
        ("Total output points",                      str(integrator["n_steps"])),
        ("Total simulated duration (t[sub]max[/sub])", f"{integrator['tmax']:.3f} s"),
    ], [105, 65])
    pdf.ln(2)

    # ── Diagnostics — Broken Bar ──────────────────────────────────────────
    if broken_bar is not None:
        BB_MIN = 58
        if (pdf.h - pdf.b_margin) - pdf.get_y() < BB_MIN:
            pdf.add_page()
        sec_bar("DIAGNOSTICS — BROKEN BAR (MCSA)")
        sev_ok = broken_bar["alpha"] < 0.2
        status_badge(sev_ok,
                     f"Severity: {broken_bar['severity_label']} "
                     f"(alpha = {broken_bar['alpha']:.3f})")
        mini_table([
            ("Lower sideband frequency (1-2s)f",    f"{broken_bar['f_lo']:.2f} Hz"),
            ("Upper sideband frequency (1+2s)f",    f"{broken_bar['f_hi']:.2f} Hz"),
            ("Relative amplitude (1-2s)f / fund.",  f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Relative amplitude (1+2s)f / fund.",  f"{broken_bar['sb_ratio_hi']:.2f} %"),
            ("Slip (s)",                             f"{broken_bar['s_val']*100:.3f} %"),
        ], [115, 55])
        pdf.ln(2)

    # ── Power Quality ─────────────────────────────────────────────────────
    if exp_type != "shutdown":
        _em = compute_energy_metrics(res, mp, energy_tariff)
        QE_MIN = 55
        if (pdf.h - pdf.b_margin) - pdf.get_y() < QE_MIN:
            pdf.add_page()
        sec_bar("POWER QUALITY")
        _thd_status = "OK (< 5%)" if _em["thd"] <= 5.0 else "HIGH (> 5%)"
        _fp_status  = "OK (>= 0.85)" if _em["fp"] >= 0.85 else "LOW"
        status_badge(_em["fp"] >= 0.85 and _em["thd"] <= 5.0,
                     f"PF = {_em['fp']:.3f} ({_fp_status})   |   "
                     f"THD = {_em['thd']:.2f}% ({_thd_status})")
        mini_table([
            ("Energy consumed in experiment",   f"{_em['E_kwh']:.6f} kWh"),
            ("Experiment cost",                 f"$ {_em['custo_exp']:.4f}"),
            ("Steady-state input power",        f"{_em['P_in_kw']:.3f} kW"),
            ("Steady-state efficiency",         f"{_em['eta']:.2f} %"),
            ("Annual operating cost (8760 h)",  f"$ {_em['custo_ano']:,.2f}"),
        ], [105, 65])
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*TEXT_LGT)
        pdf.cell(0, 5, f"  Tariff: $ {energy_tariff:.2f}/kWh. Reference IEEE 519-2022.",
                 border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ── Trip Class ────────────────────────────────────────────────────────
    if exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
        _tc = compute_trip_class(res, mp)
        if _tc is not None:
            TC_MIN = 45
            if (pdf.h - pdf.b_margin) - pdf.get_y() < TC_MIN:
                pdf.add_page()
            sec_bar("PROTECTION RECOMMENDATION — OVERLOAD RELAY")
            _tc_ok = _tc["class"] == 10
            status_badge(_tc_ok,
                         f"Class {_tc['class']} — t_acceleration = {_tc['t_accel']:.2f} s "
                         f"(95% of {_tc['n_sync']:.1f} RPM) — {_tc['status']}")
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*TEXT_LGT)
            pdf.cell(0, 5,
                     "  Reference: IEC 60947-4-1 / NEMA ICS 2. "
                     "Class 10: t < 10 s | Class 20: 10-20 s | Class 30: > 20 s",
                     border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    # ── Expert Diagnostics ────────────────────────────────────────────────
    if insights:
        DIAG_MIN = 45
        if (pdf.h - pdf.b_margin) - pdf.get_y() < DIAG_MIN:
            pdf.add_page()
        sec_bar("AUTOMATED DIAGNOSTICS")
        _COLORS = {"error": RED, "warning": (217, 119, 6), "info": GREEN}
        _LABELS = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}
        for ins in insights:
            r_, g_, b__ = _COLORS.get(ins.level, (80, 80, 80))
            lbl_ = _LABELS.get(ins.level, ins.level.upper())
            pdf.set_fill_color(r_, g_, b__)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 7, f"  [{lbl_}]  {ins.title}", border=0, fill=True,
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*TEXT_DRK)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"  {ins.body}", border=0)
            pdf.ln(2)
        pdf.ln(2)

    # ── ABC Phase Currents ────────────────────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        ABC_MIN = 78
        if (pdf.h - pdf.b_margin) - pdf.get_y() < ABC_MIN:
            pdf.add_page()
        sec_bar("ABC PHASE CURRENTS — STEADY STATE")
        abc_fig = _build_abc_currents_fig(res)
        embed_fig(pdf, _fig_to_pdf_bytes(abc_fig), width_mm=165)
        pdf.ln(2)

    # ── Machine Parameters (compact) + Equivalent Circuit ────────────────
    PARAM_MIN = 120
    if (pdf.h - pdf.b_margin) - pdf.get_y() < PARAM_MIN:
        pdf.add_page()
    sec_bar("MACHINE PARAMETERS")
    mini_table([
        ("R[sub]s[/sub]",  f"{mp.Rs:.4f} Ohm",
         "R[sub]r[/sub]",  f"{mp.Rr:.4f} Ohm"),
        ("X[sub]m[/sub]",  f"{mp.Xm:.4f} Ohm",
         "X[sub]ls[/sub]", f"{mp.Xls:.4f} Ohm"),
        ("X[sub]lr[/sub]", f"{mp.Xlr:.4f} Ohm",
         "J",              f"{mp.J:.4f} kg.m2"),
    ], [30, 45, 30, 45])
    pdf.ln(3)
    embed_fig(pdf, _build_circuit_bytes(mp), width_mm=155)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*TEXT_LGT)
    pdf.cell(0, 5, "  Single-phase T equivalent circuit of the Three-Phase Induction Motor.",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Characteristic Curves ─────────────────────────────────────────────
    chunks = _make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        dash_title(f"CHARACTERISTIC CURVES{sfx}", ", ".join(cl))
        curves_fig = _build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        embed_fig(pdf, _fig_to_pdf_bytes(curves_fig), width_mm=165)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf_report_v2(
    style: str,
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
    """Generates PDF V2 report and returns as bytes.

    style: "academico" or "dashboard"
    All other parameters are equivalent to generate_pdf_report() V1.
    """
    if style not in ("academico", "dashboard"):
        raise ValueError(
            f"style must be 'academico' or 'dashboard', received: {style!r}"
        )

    var_labels = var_labels or var_keys
    t_events   = t_events   or []
    tmax_eff   = (tmax if tmax > 0
                  else float(res["t"][-1]) if len(res.get("t", [])) > 0
                  else 1.0)

    losses     = _compute_losses(res, mp)
    integrator = _compute_integrator_params(res, mp, tmax_eff, h)
    broken_bar = _compute_broken_bar(res, mp)

    PDF_CLS = _make_pdf_class(style)
    pdf = PDF_CLS()
    pdf.alias_nb_pages()
    pdf.set_margins(left=20, top=22, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)

    if style == "academico":
        _generate_academico(
            pdf, exp_label, mp, res,
            var_keys, var_labels, t_events,
            exp_type, energy_tariff,
            losses, integrator, broken_bar,
            insights=insights, load_torque=load_torque,
        )
    else:
        _generate_dashboard(
            pdf, exp_label, mp, res,
            var_keys, var_labels, t_events,
            exp_type, energy_tariff,
            losses, integrator, broken_bar,
            insights=insights, load_torque=load_torque,
        )

    return bytes(pdf.output())
