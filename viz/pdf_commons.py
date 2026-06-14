# -*- coding: utf-8 -*-
"""
pdf_commons.py
==============
Shared utilities for PDF report generation — base class SimBlock and pure
helper functions used by all report generators.

Responsibilities:
  - Provide safe_text, fmt_power, embed_fig, build_circuit_bytes,
    cell_rich, and render_rich helper functions.
  - Expose compute_* metric helpers for KPI calculation.
  - Define the SimBlock base PDF class shared by all report styles.

Relationships:
  Imported by : viz.pdf_academico, viz.pdf_industrial, viz.pdf_dc
  Imports     : core.IWS_PY, viz.eqcircuit_plotter, ui.theme

Extending:
  - To add a new shared helper, add it here and import it in the consumer
    report modules (pdf_academico, pdf_industrial, pdf_dc).
"""

from __future__ import annotations
import io
import tempfile
import os
from contextlib import contextmanager

import numpy as np
from core.mit_facade import MachineParams
from viz.eqcircuit_plotter import build_figure as _build_circuit_figure
from ui.theme import _palette


# ─────────────────────────────────────────────────────────────────────────────
# Unicode → latin-1 map
# ─────────────────────────────────────────────────────────────────────────────

_LATIN1_MAP: dict[str, str] = {
    "—": "-", "–": "-", "−": "-",
    "Ω": "Ohm", "η": "eta", "α": "alfa", "ω": "w", "μ": "u",
    "·": ".", "²": "2", "³": "3", "¹": "1", "⁰": "0",
    "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-",
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "≥": ">=", "≤": "<=", "×": "x", "°": " deg", "≠": "!=", "≈": "~",
    "'": "'", "'": "'", "“": '"', "”": '"', "…": "...",
    "½": "1/2", "∞": "inf", "Δ": "Delta", "Φ": "Phi", "φ": "phi",
    "σ": "sigma", "λ": "lambda", "∂": "d", "∫": "int", "√": "sqrt", "±": "+/-",
    "µ": "u",
    "ₑ": "e", "ₐ": "a", "ₛ": "s", "ᵣ": "r",
}


def safe_text(text: str) -> str:
    for ch, repl in _LATIN1_MAP.items():
        text = text.replace(ch, repl)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def fmt_power(val: float) -> tuple[str, str]:
    if abs(val) >= 1000:
        return f"{val/1000:.3f}", "kW"
    return f"{val:.2f}", "W"


@contextmanager
def tempfile_ctx():
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        yield path
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def fig_to_png_bytes(mpl_fig, dpi: int = 180) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def embed_fig(pdf, png_bytes: bytes, width_mm: float = 170) -> None:
    with tempfile_ctx() as tmp:
        with open(tmp, "wb") as f:
            f.write(png_bytes)
        pdf.image(tmp, x=(210 - width_mm) / 2, w=width_mm)


def build_circuit_bytes(mp: MachineParams) -> bytes:
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
# Rich text: inline sub/superscripts  [sub]...[/sub]  [sup]...[/sup]
# ─────────────────────────────────────────────────────────────────────────────

def render_rich(pdf, text: str, main_size: int = 10, cell_h: float = 6.0,
                newline: bool = False) -> None:
    import re
    parts = re.split(r'(\[sub\].*?\[/sub\]|\[sup\].*?\[/sup\])', text)
    SUB_SIZE = max(6, main_size - 3)
    SUP_SIZE = max(6, main_size - 3)
    y0 = pdf.get_y()
    for part in parts:
        if not part:
            continue
        if part.startswith("[sub]"):
            inner = part[5:-6]
            pdf.set_font("Helvetica", "", SUB_SIZE)
            pdf.set_xy(pdf.get_x(), y0 + 2.0)
            pdf.cell(pdf.get_string_width(inner) + 0.4, cell_h, inner, border=0, fill=False)
            pdf.set_xy(pdf.get_x(), y0)
        elif part.startswith("[sup]"):
            inner = part[5:-6]
            pdf.set_font("Helvetica", "", SUP_SIZE)
            pdf.set_xy(pdf.get_x(), y0 - 2.0)
            pdf.cell(pdf.get_string_width(inner) + 0.4, cell_h, inner, border=0, fill=False)
            pdf.set_xy(pdf.get_x(), y0)
        else:
            pdf.set_font("Helvetica", "", main_size)
            pdf.cell(pdf.get_string_width(part), cell_h, part, border=0, fill=False)
    if newline:
        pdf.ln(cell_h)


def cell_rich(pdf, text: str, w: float, h: float, main_size: int = 9,
              fill_rgb: tuple = (255, 255, 255), text_rgb: tuple = (40, 40, 40)) -> None:
    import re
    has_markup = bool(re.search(r'\[sub\]|\[sup\]', text))
    pdf.set_fill_color(*fill_rgb)
    x0, y0 = pdf.get_x(), pdf.get_y()
    pdf.cell(w, h, "", border=0, fill=True)
    pdf.set_xy(x0 + 2, y0)
    pdf.set_text_color(*text_rgb)
    if has_markup:
        render_rich(pdf, text, main_size=main_size, cell_h=h)
    else:
        pdf.set_font("Helvetica", "", main_size)
        pdf.cell(w - 2, h, text, border=0, fill=False)
    pdf.set_xy(x0 + w, y0)


# ─────────────────────────────────────────────────────────────────────────────
# Analytical computations
# ─────────────────────────────────────────────────────────────────────────────

def compute_trip_class(res: dict, mp: MachineParams) -> dict | None:
    try:
        n_arr  = np.asarray(res.get("n", []), dtype=float)
        t_arr  = np.asarray(res.get("t", []), dtype=float)
        n_sync = mp.f / mp.p * 60.0
        thresh = 0.95 * n_sync
        above  = np.where(n_arr >= thresh)[0]
        if len(above) == 0:
            return None
        t_accel = float(t_arr[int(above[0])])
        if t_accel < 10.0:
            cls, status = 10, "OK"
        elif t_accel < 20.0:
            cls, status = 20, "WARNING"
        else:
            cls, status = 30, "CRITICAL"
        return {"class": cls, "t_accel": t_accel, "status": status, "n_sync": n_sync}
    except Exception:
        return None


def compute_thd_harmonics(res: dict, mp: MachineParams) -> list[tuple]:
    rows = []
    try:
        ss   = int(res.get("_ss_start", 0))
        ias  = np.asarray(res["ias"][ss:], dtype=float)
        t_ss = np.asarray(res["t"][ss:], dtype=float)
        if len(ias) < 16:
            return rows
        dt   = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
        N    = len(ias)
        spec = np.abs(np.fft.rfft(ias)) * 2.0 / N
        freq = np.fft.rfftfreq(N, d=dt)
        mask_f1 = (freq > 0.5 * mp.f) & (freq < 1.5 * mp.f)
        if not mask_f1.any():
            return rows
        A1 = float(spec[mask_f1].max())
        if A1 <= 0:
            return rows
        for k in range(1, 10):
            f_k  = mp.f * k
            mask = (freq > f_k * 0.85) & (freq < f_k * 1.15)
            if not mask.any():
                continue
            Ak = float(spec[mask].max())
            rows.append((k, f_k, Ak, Ak / A1 * 100.0))
    except Exception:
        pass
    return rows


def compute_energy_metrics(res: dict, mp: MachineParams, tarifa: float) -> dict:
    t   = np.asarray(res.get("t",   []), dtype=float)
    Vqs = np.asarray(res.get("Vqs", []), dtype=float)
    Vds = np.asarray(res.get("Vds", []), dtype=float)
    iqs = np.asarray(res.get("iqs", []), dtype=float)
    ids = np.asarray(res.get("ids", []), dtype=float)
    P_in_inst = (3.0 / 2.0) * (Vqs * iqs + Vds * ids)
    E_j  = float(np.trapezoid(np.where(np.isfinite(P_in_inst), P_in_inst, 0.0), t)) if len(t) > 1 else 0.0
    E_kwh = E_j / 3_600_000.0
    P_in  = float(res.get("P_in", 0.0))
    thd = fp = 0.0
    try:
        ss   = int(res.get("_ss_start", 0))
        ias  = np.asarray(res["ias"][ss:], dtype=float)
        t_ss = t[ss:]
        if len(ias) >= 16:
            dt   = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
            N    = len(ias)
            spec = np.abs(np.fft.rfft(ias)) / N
            frq  = np.fft.rfftfreq(N, d=dt)
            mf1  = (frq > 0.5 * mp.f) & (frq < 1.5 * mp.f)
            if mf1.any():
                A1     = float(spec[mf1].max())
                A_harm = spec[frq > 1.5 * mp.f]
                if A1 > 0 and len(A_harm) > 0:
                    thd = float(np.sqrt(np.sum(A_harm**2)) / A1 * 100.0)
        Vqs_ss  = Vqs[ss:]; Vds_ss = Vds[ss:]
        Va_rms  = float(np.sqrt(np.mean(Vqs_ss**2 + Vds_ss**2))) / np.sqrt(2.0) if len(Vqs_ss) > 0 else 0.0
        ias_rms = float(res.get("ias_rms", 0.0))
        S_ap = 3.0 * Va_rms * ias_rms
        if S_ap > 0 and np.isfinite(P_in):
            fp = float(np.clip(abs(P_in) / S_ap, 0.0, 1.0))
    except Exception:
        pass
    return {
        "E_kwh": E_kwh, "custo_exp": E_kwh * tarifa,
        "P_in_kw": P_in / 1000.0,
        "custo_ano": (P_in / 1000.0) * 8_760.0 * tarifa,
        "eta": float(res.get("eta", 0.0)),
        "thd": thd, "fp": fp,
    }


def _mp_get(mp, key: str, default=0.0):
    """Accept both MachineParams object and plain dict."""
    if isinstance(mp, dict):
        return mp.get(key, default)
    return getattr(mp, key, default)


def compute_losses(res: dict, mp: dict) -> dict:
    P_in   = float(res.get("P_in",   0.0))
    P_gap  = float(res.get("P_gap",  0.0))
    P_mec  = float(res.get("P_mec",  0.0))
    P_cu_r = float(res.get("P_cu_r", 0.0))
    iqs_ss = np.asarray(res["iqs"], dtype=float)
    ids_ss = np.asarray(res["ids"], dtype=float)
    ss     = int(res.get("_ss_start", max(0, len(iqs_ss) - 1)))
    iqs_m  = float(np.sqrt(np.mean(iqs_ss[ss:]**2))) if ss < len(iqs_ss) else 0.0
    ids_m  = float(np.sqrt(np.mean(ids_ss[ss:]**2))) if ss < len(ids_ss) else 0.0
    P_cu_s = (3.0 / 2.0) * _mp_get(mp, "Rs", 0.435) * (iqs_m**2 + ids_m**2)
    Vqs_ss = np.asarray(res["Vqs"][ss:], dtype=float)
    Vds_ss = np.asarray(res["Vds"][ss:], dtype=float)
    if _mp_get(mp, "Rfe", 500.0) > 0 and len(Vqs_ss) > 0:
        V_rms_sq = float(np.mean(Vqs_ss**2)) + float(np.mean(Vds_ss**2))
        P_fe = (3.0 / 2.0) * V_rms_sq / _mp_get(mp, "Rfe", 500.0)
    else:
        P_fe = max(abs(P_in - P_gap - P_cu_s), 0.0) if P_in > 0 else 0.0
    P_loss = P_cu_s + P_cu_r + P_fe
    denom  = P_in if abs(P_in) > 1.0 else 1.0
    return {
        "P_in": P_in, "P_mec": P_mec,
        "P_cu_s": P_cu_s, "P_cu_r": P_cu_r, "P_fe": P_fe, "P_loss": P_loss,
        "pct_cu_s": P_cu_s / denom * 100.0,
        "pct_cu_r": P_cu_r / denom * 100.0,
        "pct_fe":   P_fe   / denom * 100.0,
        "pct_mec":  P_mec  / denom * 100.0,
    }


def compute_integrator_params(res: dict, mp: dict, tmax: float, h: float) -> dict:
    t       = np.asarray(res["t"], dtype=float)
    n_steps = len(t)
    dt_eff  = float(t[-1] - t[0]) / max(n_steps - 1, 1) if n_steps > 1 else h
    nyquist_ok = _mp_get(mp, "f", 60.0) * h <= 0.1
    return {
        "n_steps": n_steps, "dt_eff": dt_eff, "tmax": tmax, "h_req": h,
        "nyquist_ok": nyquist_ok,
        "samples_per_cycle": 1.0 / (_mp_get(mp, "f", 60.0) * dt_eff) if _mp_get(mp, "f", 60.0) * dt_eff > 0 else 0.0,
    }


def compute_broken_bar(res: dict, mp: MachineParams) -> dict | None:
    alpha = float(res.get("_broken_bar_severity", 0.0))
    if alpha <= 0:
        return None
    s_val  = float(res.get("s", 0.0))
    f_fund = mp.f
    f_lo   = f_fund * (1.0 - 2.0 * abs(s_val))
    f_hi   = f_fund * (1.0 + 2.0 * abs(s_val))
    ss     = int(res.get("_ss_start", 0))
    ias    = np.asarray(res.get("ias", []), dtype=float)[ss:]
    t_arr  = np.asarray(res["t"][ss:], dtype=float)
    sb_lo = sb_hi = 0.0
    if len(ias) >= 16:
        dt   = float(t_arr[1] - t_arr[0]) if len(t_arr) > 1 else 1e-3
        N    = len(ias)
        spec = np.abs(np.fft.rfft(ias)) * 2.0 / N
        freq = np.fft.rfftfreq(N, d=dt)
        if (freq > 0).any():
            f1_idx = int(np.argmax(spec[freq > 0.1])) + np.searchsorted(freq, 0.1)
            A1 = float(spec[f1_idx]) if f1_idx < len(spec) else 1.0
            if A1 > 0:
                def _amp(f_t):
                    idx = int(np.argmin(np.abs(freq - f_t)))
                    lo, hi = max(0, idx - 2), min(len(spec), idx + 3)
                    return float(spec[lo:hi].max()) if lo < hi else 0.0
                sb_lo = _amp(f_lo) / A1 * 100.0
                sb_hi = _amp(f_hi) / A1 * 100.0
    label = "Severe" if alpha >= 0.5 else ("Moderate" if alpha >= 0.2 else "Mild")
    return {
        "alpha": alpha, "s_val": s_val,
        "f_lo": f_lo, "f_hi": f_hi,
        "sb_ratio_lo": sb_lo, "sb_ratio_hi": sb_hi,
        "severity_label": label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Matplotlib figures
# ─────────────────────────────────────────────────────────────────────────────

AFFINITY_GROUPS = [
    ["Te", "n", "wr"],
    ["ias", "ibs", "ics"],
    ["iar", "ibr", "icr"],
    ["ids", "iqs"],
    ["idr", "iqr"],
    ["Va", "Vb", "Vc"],
]


def make_chunks(keys: list, labels: list) -> list[tuple]:
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


def build_abc_currents_fig(res: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ss     = int(res.get("_ss_start", 0))
    t      = np.asarray(res["t"][ss:], dtype=float)
    keys   = ["ias", "ibs", "ics"]
    colors = ["#1d4ed8", "#ea580c", "#16a34a"]
    labels = ["ias (A)", "ibs (A)", "ics (A)"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.2), sharey=True)
    fig.patch.set_facecolor("white")
    for ax, key, color, lbl in zip(axes, keys, colors, labels):
        y = np.asarray(res.get(key, np.zeros_like(t)), dtype=float)[ss:]
        n = min(len(t), len(y))
        ax.plot(t[:n], y[:n], color=color, linewidth=1.1)
        y_rms = float(res.get(key + "_rms",
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


def build_losses_bar_fig(losses: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cats   = [
        "Stator copper\nlosses  Pcu,s",
        "Rotor copper\nlosses  Pcu,r",
        "Iron\nlosses  Pfe",
        "Mechanical\npower  Pmec",
    ]
    vals   = [losses["P_cu_s"], losses["P_cu_r"], losses["P_fe"], max(losses["P_mec"], 0.0)]
    colors = ["#1d4ed8", "#7c3aed", "#dc2626", "#16a34a"]
    pcts   = [losses["pct_cu_s"], losses["pct_cu_r"], losses["pct_fe"], losses["pct_mec"]]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    fig.patch.set_facecolor("white")
    bars = ax.barh(cats, vals, color=colors, alpha=0.85, height=0.5)
    max_val = max(vals) if any(v > 0 for v in vals) else 1.0
    for bar, pct, val in zip(bars, pcts, vals):
        v_str, u_str = fmt_power(val)
        ax.text(bar.get_width() + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v_str} {u_str}  ({pct:.1f}%)", va="center", fontsize=8, color="#1e293b")
    ax.set_xlabel("Power (W)", fontsize=8)
    ax.set_title("Loss Balance — Steady State", fontsize=9, fontweight="bold")
    ax.tick_params(labelsize=8)
    ax.set_facecolor("#f9fafc")
    ax.grid(True, axis="x", color="#dde4f5", linewidth=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def build_curves_fig(res: dict, var_keys: list, var_labels: list,
                     t_events: list, color_offset: int = 0,
                     ref_list: list | None = None):
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
        ax.plot(t, y, color=color, linewidth=1.1, solid_capstyle="round",
                label="Current", zorder=3)
        if ref_list:
            for ref_i, ref in enumerate(ref_list):
                r_res = ref.get("res", {})
                if key not in r_res:
                    continue
                yr = np.asarray(r_res[key], dtype=float)
                tr = np.asarray(r_res.get("t", t), dtype=float)
                n_pts = min(len(tr), len(yr))
                ax.plot(tr[:n_pts], yr[:n_pts],
                        color=ref.get("color", "#888888"),
                        linewidth=0.9, linestyle="--", alpha=0.75,
                        label=ref.get("label", f"Ref {ref_i+1}"), zorder=2)
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
        if ref_list or True:
            ax.legend(fontsize=7, loc="upper right", framealpha=0.8)
    fig.subplots_adjust(left=0.10, right=0.96, top=0.96, bottom=0.06, hspace=0.65)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Base FPDF class with parametric header/footer
# ─────────────────────────────────────────────────────────────────────────────

def make_pdf_class(style_label: str):
    from fpdf import FPDF
    import datetime

    class _BasePDF(FPDF):
        def normalize_text(self, text: str) -> str:
            return super().normalize_text(safe_text(text))

        def header(self):
            if self.page_no() == 1:
                return
            self.set_fill_color(235, 240, 255)
            self.rect(0, 0, 210, 16, style="F")
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(22, 54, 120)
            self.set_xy(20, 4)
            self.cell(100, 8, f"IWS — Report ({style_label})", border=0)
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
            self.cell(0, 8, f"Page {self.page_no()} of {{nb}}", align="C")

    return _BasePDF
