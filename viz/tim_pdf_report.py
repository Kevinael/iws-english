# -*- coding: utf-8 -*-
"""
pdf_report.py
=============
Legacy induction-machine PDF report generator — superseded by
pdf_academico.py and pdf_industrial.py; retained for backwards compatibility.

Responsibilities:
  - Provide the original single-style PDF generation function.
  - Serve as fallback if newer generators are unavailable.

Relationships:
  Imported by : (legacy — check usages before removing)
  Imports     : core.IWS_PY, viz.eqcircuit_plotter, ui.theme

Extending:
  - Do not extend; migrate callers to pdf_academico or pdf_industrial instead.
"""
from __future__ import annotations
import io
import numpy as np
from core.tim.facade import MachineParams
from core.constants import GEN_EFFICIENCY_FALLBACK
from viz.tim_eqcircuit import build_figure as _build_circuit_figure
from ui.theme import _palette


def _compute_trip_class(res: dict, mp) -> dict | None:
    """Computes Trip Class per IEC 60947-4-1 / NEMA ICS 2 from acceleration time."""
    try:
        import math
        n_arr   = np.asarray(res.get("n",  []), dtype=float)
        t_arr   = np.asarray(res.get("t",  []), dtype=float)
        n_sync  = mp.f / mp.p * 60.0
        thresh  = 0.95 * n_sync
        above   = np.where(n_arr >= thresh)[0]
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


def _compute_thd_harmonics(res: dict, mp) -> list[tuple]:
    """Returns list of (order, frequency, amplitude_rel%) for the first 9 harmonics."""
    rows = []
    try:
        ss_start = int(res.get("_ss_start", 0))
        ias_ss   = np.asarray(res["ias"][ss_start:], dtype=float)
        t_ss     = np.asarray(res["t"][ss_start:], dtype=float)
        if len(ias_ss) < 16:
            return rows
        dt   = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
        N    = len(ias_ss)
        spec = np.abs(np.fft.rfft(ias_ss)) * 2.0 / N
        freq = np.fft.rfftfreq(N, d=dt)

        # fundamental
        mask_f1 = (freq > 0.5 * mp.f) & (freq < 1.5 * mp.f)
        if not mask_f1.any():
            return rows
        A1 = float(spec[mask_f1].max())
        if A1 <= 0:
            return rows

        for k in range(1, 10):
            f_k   = mp.f * k
            mask  = (freq > f_k * 0.85) & (freq < f_k * 1.15)
            if not mask.any():
                continue
            Ak    = float(spec[mask].max())
            pct   = Ak / A1 * 100.0
            rows.append((k, f_k, Ak, pct))
    except Exception:
        pass
    return rows


def _compute_energy_pdf(res: dict, tarifa: float) -> dict:
    """Computes economic metrics, THD and PF for inclusion in the PDF."""
    t   = np.asarray(res["t"],   dtype=float)
    Vqs = np.asarray(res["Vqs"], dtype=float)
    Vds = np.asarray(res["Vds"], dtype=float)
    iqs = np.asarray(res["iqs"], dtype=float)
    ids = np.asarray(res["ids"], dtype=float)
    P_in_inst   = (3.0 / 2.0) * (Vqs * iqs + Vds * ids)
    E_j         = float(np.trapezoid(np.where(np.isfinite(P_in_inst), P_in_inst, 0.0), t))
    E_kwh       = E_j / 3_600_000.0
    custo_exp   = E_kwh * tarifa
    P_in_ss     = float(res.get("P_in", 0.0))
    P_in_ss_kw  = P_in_ss / 1000.0
    custo_ano   = P_in_ss_kw * 8_760.0 * tarifa

    # THD and PF in steady-state window
    thd_pct = 0.0
    fp      = 0.0
    try:
        ss_start = int(res.get("_ss_start", 0))
        ias_ss   = np.asarray(res["ias"][ss_start:], dtype=float)
        t_ss     = t[ss_start:]
        if len(ias_ss) >= 16:
            dt_ss = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
            N     = len(ias_ss)
            spec  = np.abs(np.fft.rfft(ias_ss)) / N
            freqs = np.fft.rfftfreq(N, d=dt_ss)
            f_fund = 60.0
            mask_fund = (freqs > 0.5 * f_fund) & (freqs < 1.5 * f_fund)
            if mask_fund.any():
                A1 = float(spec[mask_fund].max())
                mask_harm = freqs > 1.5 * f_fund
                A_harm    = spec[mask_harm]
                if A1 > 0 and len(A_harm) > 0:
                    thd_pct = float(np.sqrt(np.sum(A_harm ** 2)) / A1 * 100.0)
        Vqs_ss  = Vqs[ss_start:]
        Vds_ss  = Vds[ss_start:]
        Va_pk   = float(np.sqrt(np.mean(Vqs_ss ** 2 + Vds_ss ** 2)))
        Va_rms  = Va_pk / np.sqrt(2.0)
        ias_rms = float(res.get("ias_rms", 0.0))
        S_ap    = 3.0 * Va_rms * ias_rms
        if S_ap > 0 and np.isfinite(P_in_ss):
            fp = float(np.clip(abs(P_in_ss) / S_ap, 0.0, 1.0))
    except Exception:
        pass

    return {
        "E_kwh": E_kwh, "custo_exp": custo_exp,
        "P_in_ss_kw": P_in_ss_kw, "custo_ano": custo_ano,
        "eta": float(res.get("eta", 0.0)),
        "thd_pct": thd_pct, "fp": fp,
    }


def _build_fft_fig(res: dict, key: str = "ias") -> "matplotlib.figure.Figure":
    """Amplitude spectrum (FFT) in matplotlib for inclusion in the PDF."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ss_start = int(res.get("_ss_start", 0))
    y = np.asarray(res.get(key, []), dtype=float)[ss_start:]
    t = np.asarray(res["t"][ss_start:], dtype=float)

    fig, ax = plt.subplots(figsize=(11, 3.0))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f9fafc")

    if len(y) < 4:
        ax.text(0.5, 0.5, "Insufficient data for FFT",
                transform=ax.transAxes, ha="center", va="center", fontsize=10)
        return fig

    dt   = float(t[1] - t[0]) if len(t) > 1 else 1e-3
    N    = len(y)
    yf   = np.abs(np.fft.rfft(y)) * 2.0 / N
    freq = np.fft.rfftfreq(N, d=dt)
    mask = freq <= 800
    freq, yf = freq[mask], yf[mask]

    ax.bar(freq, yf, width=freq[1] - freq[0] if len(freq) > 1 else 1.0,
           color="#1d4ed8", alpha=0.8, linewidth=0)

    # odd harmonics (red dotted)
    f1_idx = int(np.argmax(yf[freq > 0.1])) + np.searchsorted(freq, 0.1) if (freq > 0.1).any() else 0
    f1 = float(freq[f1_idx]) if f1_idx < len(freq) else 60.0
    for k in [1, 3, 5, 7, 9]:
        hf = f1 * k
        if hf <= freq[-1]:
            ax.axvline(hf, color="#dc2626", linewidth=0.9, linestyle=":", alpha=0.8)
            ax.text(hf, ax.get_ylim()[1] * 0.85, f"{hf:.0f}",
                    fontsize=6, color="#dc2626", ha="center")

    # broken bar sidebands (orange dashed)
    alpha = float(res.get("_broken_bar_severity", 0.0))
    s_val = float(res.get("s", 0.0))
    if alpha > 0:
        for sb_f, lbl in [
            (f1 * (1 - 2 * abs(s_val)), f"(1-2s)f\n{f1*(1-2*abs(s_val)):.1f}Hz"),
            (f1 * (1 + 2 * abs(s_val)), f"(1+2s)f\n{f1*(1+2*abs(s_val)):.1f}Hz"),
        ]:
            if 0 < sb_f <= freq[-1]:
                ax.axvline(sb_f, color="#d97706", linewidth=1.2, linestyle="--")
                ax.text(sb_f, ax.get_ylim()[1] * 0.65, lbl,
                        fontsize=6, color="#d97706", ha="center")

    ax.set_xlabel("Frequency (Hz)", fontsize=8)
    ax.set_ylabel("Amplitude", fontsize=8)
    ax.set_title(f"FFT Spectrum — {key} (steady state)", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(True, color="#dde4f5", linewidth=0.4, linestyle="-")
    ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.90, bottom=0.15)
    return fig


_DASH_MAP = {"dash": "--", "dot": ":", "solid": "-"}


def _build_pdf_page_fig(res: dict, var_keys: list, var_labels: list,
                         t_events: list, color_offset: int = 0,
                         ref_list=None, tl_arr=None) -> "matplotlib.figure.Figure":
    """Generates a matplotlib figure with up to N subplots for a PDF page.

    ref_list: list of {"res", "color", "dash", "label"} for overlay.
    When present, suppresses peak/steady-state annotations and shows legend.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    COLORS = ["#1d4ed8","#ea580c","#16a34a","#7c3aed",
              "#db2777","#0d9488","#d97706","#4f46e5",
              "#65a30d","#dc2626","#0891b2","#c026d3"]

    has_refs = bool(ref_list)
    n   = max(1, len(var_keys))
    t   = res["t"]
    fig, axes = plt.subplots(n, 1, figsize=(11, 3.2 * n), sharex=True)
    if n == 1:
        axes = [axes]

    fig.patch.set_facecolor("white")

    for i, (key, lbl, ax) in enumerate(zip(var_keys, var_labels, axes)):
        color = COLORS[(i + color_offset) % len(COLORS)]

        # ── reference curves (behind main curve) ─────────────────────────
        for ref_item in (ref_list or []):
            res_ref   = ref_item.get("res")
            ref_color = ref_item.get("color", "#888888")
            ref_dash  = ref_item.get("dash", "dash")
            ref_label = ref_item.get("label", "Reference")
            if res_ref is not None and key in res_ref and "t" in res_ref:
                ls = _DASH_MAP.get(ref_dash, "--")
                ax.plot(res_ref["t"], np.asarray(res_ref[key]),
                        color=ref_color, linewidth=0.9, linestyle=ls,
                        label=ref_label, alpha=0.85)

        # ── main curve ────────────────────────────────────────────────────
        y = np.asarray(res[key])
        ax.plot(t, y, color=color, linewidth=1.2, solid_capstyle="round",
                label="Current" if has_refs else "_nolegend_")

        # ── load torque overlay (TL) in Te subplot ─────────────────────
        if key == "Te" and tl_arr is not None:
            tl = np.asarray(tl_arr, dtype=float)
            n_common = min(len(t), len(tl))
            if n_common > 1:
                ax.plot(np.asarray(t[:n_common]), tl[:n_common],
                        color="#d97706", linewidth=1.0, linestyle="--",
                        label="T[sub]L[/sub] (N·m)", alpha=0.85)

        ax.set_ylabel(lbl, fontsize=9, labelpad=4)
        ax.tick_params(labelsize=8)
        ax.tick_params(axis="x", labelbottom=True)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_facecolor("#f9fafc")
        ax.grid(True, color="#dde4f5", linewidth=0.5, linestyle="-")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#c0cce0")
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
        for te in (t_events or []):
            ax.axvline(x=te, color="#94a3b8", linewidth=0.8, linestyle="--")

        if has_refs:
            # overlay mode: compact legend, no peak annotations
            ax.legend(fontsize=6, loc="upper right", framealpha=0.85,
                      ncol=min(len(ref_list) + 1, 3))
        else:
            # isolated mode: peak and steady-state annotations
            pk_idx = int(np.argmax(np.abs(y)))
            t_pk   = float(t[pk_idx])
            y_pk   = float(np.abs(y[pk_idx]))
            ax.plot(t_pk, y_pk, "^", color="#dc2626", markersize=6, zorder=5,
                    label=f"Peak: {y_pk:.2f}")
            rms_key  = key + "_rms"
            y_ss_rms = float(res[rms_key]) if rms_key in res else float(np.abs(y[-1]))
            ss_start = int(res.get("_ss_start", len(y) - 1))
            y_ss_mid = float(np.mean(y[ss_start:]))
            t_ss     = float(t[ss_start + (len(y) - ss_start) // 2])
            ax.axvline(x=float(t[ss_start]), color="#16a34a", linewidth=0.7,
                       linestyle=":", alpha=0.6)
            ax.plot(t_ss, y_ss_mid, "D", color="#16a34a", markersize=5, zorder=5,
                    label=f"Steady-state RMS: {y_ss_rms:.2f}")
            ax.legend(fontsize=7, loc="upper right", framealpha=0.8)

    fig.subplots_adjust(left=0.10, right=0.80, top=0.95, bottom=0.08,
                        hspace=0.75)
    for ax in axes:
        ax.tick_params(labelsize=14)
        ax.set_xlabel(ax.get_xlabel(), fontsize=14)
        ax.set_ylabel(ax.get_ylabel(), fontsize=14)
        legend = ax.get_legend()
        if legend is not None:
            legend.set_bbox_to_anchor((1.02, 1))
            legend.set_loc("upper left")
    return fig


def build_fig_matplotlib_pdf(res: dict, var_keys: list, var_labels: list,
                              t_events: list) -> "matplotlib.figure.Figure":
    """Compatibility wrapper: returns figure with all variables (used internally)."""
    return _build_pdf_page_fig(res, var_keys, var_labels, t_events, color_offset=0)

def generate_pdf_report(exp_label: str, mp: MachineParams, res: dict,
                        fig, var_keys: list,
                        var_labels: list | None = None,
                        t_events: list | None = None,
                        exp_type: str = "dol",
                        ref_list: list | None = None,
                        energy_tariff: float = 0.75,
                        insights: list | None = None,
                        load_torque: float = 0.0,
                        exp_config: dict | None = None,
                        input_mode: str | None = None) -> bytes:
    """Generates the technical PDF report and returns it as bytes (stream).

    Structure:
      - Complete block for the current simulation (Identification -> Curves)
      - Complete block for each saved reference (same structure)
      - Final section: all overlaid plots (current + references)
    """
    from fpdf import FPDF
    import datetime
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    var_labels = var_labels or var_keys
    t_events   = t_events   or []

    # ── Unicode → latin-1 substitution map ──────────────────────────────────
    _UNICODE_SAFE = {
        '—': '-',  '–': '-',
        'ₑ': 'e',  'ₐ': 'a',
        'ₛ': 's',  'ᵣ': 'r',
        '₀': '0',  '₁': '1',  '₂': '2',  '₃': '3',
        '₄': '4',  '₅': '5',  '₆': '6',  '₇': '7',
        '₈': '8',  '₉': '9',
        '·': '.',
        'ω': 'w',  'α': 'a',  'β': 'b',  'η': 'n',
        'σ': 's',  'φ': 'phi', 'λ': 'lambda',
    }

    def _safe(text: str) -> str:
        for ch, repl in _UNICODE_SAFE.items():
            text = text.replace(ch, repl)
        return text.encode('latin-1', errors='ignore').decode('latin-1')

    # ── Subclass with automatic header and footer ─────────────────────────
    class EMS_PDF(FPDF):
        def normalize_text(self, text: str) -> str:
            return super().normalize_text(_safe(text))

        def header(self):
            self.set_fill_color(230, 230, 230)
            self.rect(0, 0, 210, 18, style="F")
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(30, 30, 30)
            self.set_xy(20, 4)
            self.cell(120, 10, "IWS - TECHNICAL SIMULATION REPORT", border=0)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(80, 80, 80)
            ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
            self.set_xy(130, 4)
            self.cell(60, 5, f"Generated: {ts}", border=0, align="R")
            self.set_xy(130, 9)
            self.cell(60, 5, "Version 1.0 | IWS Simulator", border=0, align="R")
            self.ln(8)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, f"Page {self.page_no()} of {{nb}}", align="C")

    # ── Helper functions ───────────────────────────────────────────────────
    def section_title(pdf: EMS_PDF, title: str) -> None:
        """Section line with dark blue background and white text."""
        pdf.set_fill_color(25, 60, 140)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"  {title}", border=0, fill=True, ln=True)
        pdf.ln(2)

    def _render_cell_with_sub(pdf: EMS_PDF, text: str, w: float,
                               row_h: float, fill_rgb: tuple) -> None:
        """Renders a cell with subscript support via [sub] markup.
        Format: normal text[sub]subscript[/sub]normal text
        Ex: 'R[sub]fe[/sub]' -> R with 'fe' subscript.
        """
        import re
        parts = re.split(r'\[sub\](.*?)\[/sub\]', text)

        x0 = pdf.get_x() + 2
        y0 = pdf.get_y()

        # cell background with correct colour
        pdf.set_fill_color(*fill_rgb)
        pdf.cell(w, row_h, "", border=0, fill=True)

        pdf.set_xy(x0, y0)
        MAIN_SIZE = 10
        SUB_SIZE  = 7
        SUB_DY    = 2.2

        for i, part in enumerate(parts):
            if not part:
                continue
            if i % 2 == 1:
                # subscript
                pdf.set_font("Helvetica", "", SUB_SIZE)
                pdf.set_xy(pdf.get_x(), y0 + SUB_DY)
                pdf.cell(pdf.get_string_width(part) + 0.3, row_h - SUB_DY,
                         part, border=0, fill=False)
                pdf.set_xy(pdf.get_x(), y0)
            else:
                # normal text
                pdf.set_font("Helvetica", "", MAIN_SIZE)
                pdf.set_xy(pdf.get_x(), y0)
                pdf.cell(pdf.get_string_width(part), row_h,
                         part, border=0, fill=False)

        # reposition cursor to next cell in row
        pdf.set_xy(x0 - 2 + w, y0)

    def zebra_table(pdf: EMS_PDF, rows: list[tuple], col_widths: list[float],
                    col_aligns: list[str], row_h: float = 7) -> None:
        """Zebra-striped table. rows = list[(cell, ...)]
        The first column supports [sub]...[/sub] markup for subscripts.
        """
        for idx, row in enumerate(rows):
            fill_rgb = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill_rgb)
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "", 10)
            for col_i, (cell, w, align) in enumerate(zip(row, col_widths, col_aligns)):
                if col_i == 0 and '[sub]' in str(cell):
                    _render_cell_with_sub(pdf, str(cell), w, row_h, fill_rgb)
                else:
                    pdf.set_fill_color(*fill_rgb)
                    pdf.cell(w, row_h, f"  {cell}", border=0, fill=True, align=align)
            pdf.ln(row_h)

    def fmt_power(val: float) -> tuple[str, str]:
        """Returns (formatted_value, unit)."""
        if abs(val) >= 1000:
            return f"{val/1000:.3f}", "kW"
        return f"{val:.2f}", "W"

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

    def _mpl_to_pdf(mpl_fig, width_mm=170):
        buf = io.BytesIO()
        mpl_fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                        facecolor="white")
        plt.close(mpl_fig)
        buf.seek(0)
        with tempfile_ctx() as tmp:
            with open(tmp, "wb") as f_tmp:
                f_tmp.write(buf.read())
            pdf.image(tmp, x=(210 - width_mm) / 2, w=width_mm)

    # ── Block separator banner ─────────────────────────────────────────────
    def _block_banner(text: str) -> None:
        pdf.add_page()
        pdf.set_fill_color(15, 40, 100)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 14, f"  {text}", border=0, fill=True, ln=True)
        pdf.ln(4)

    # ══════════════════════════════════════════════════════════════════════
    # SIMULATION BLOCK — writes identification + values + circuit +
    #                    highlights + steady state + curves for one result
    # ══════════════════════════════════════════════════════════════════════
    def _write_block(b_res, b_mp, b_exp_label, b_exp_type, b_t_events,
                     b_var_keys, b_var_labels, b_tariff=0.75,
                     b_insights=None, b_load_torque=0.0, b_is_main=False):

        # ── Identification ─────────────────────────────────────────────────
        section_title(pdf, "Experiment Identification")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(50, 7, "  Experiment type:", border=0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, b_exp_label, border=0, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(50, 7, "  Synchronous speed:", border=0)
        pdf.cell(0, 7,
                 f"{b_mp.n_sync:.1f} RPM  |  {b_mp.wb/(b_mp.p/2.0):.3f} rad/s",
                 border=0, ln=True)
        pdf.cell(50, 7, "  Rated frequency:", border=0)
        pdf.cell(0, 7,
                 f"{b_mp.f:.1f} Hz",
                 border=0, ln=True)
        pdf.ln(5)

        # ── Rated Values ───────────────────────────────────────────────────
        section_title(pdf, "Machine Rated Values")
        pdf.set_fill_color(200, 210, 240)
        pdf.set_text_color(20, 20, 80)
        pdf.set_font("Helvetica", "B", 10)
        for lbl, w in [("  Parameter", 110), ("Value", 35), ("Unit", 25)]:
            pdf.cell(w, 7, lbl, border=0, fill=True)
        pdf.ln(7)
        zebra_table(pdf, [
            ("Line voltage (V[sub]l[/sub])",                        f"{b_mp.Vl:.1f}",  "V"),
            ("Frequency (f)",                                        f"{b_mp.f:.1f}",   "Hz"),
            ("Stator resistance (R[sub]s[/sub])",                   f"{b_mp.Rs:.4f}",  "Ohm"),
            ("Rotor resistance (R[sub]r[/sub])",                    f"{b_mp.Rr:.4f}",  "Ohm"),
            ("Magnetising reactance (X[sub]m[/sub])",               f"{b_mp.Xm:.4f}",  "Ohm"),
            ("Stator leakage reactance (X[sub]ls[/sub])",           f"{b_mp.Xls:.4f}", "Ohm"),
            ("Rotor leakage reactance (X[sub]lr[/sub])",            f"{b_mp.Xlr:.4f}", "Ohm"),
            ("Iron-loss resistance (R[sub]fe[/sub])",               f"{b_mp.Rfe:.1f}", "Ohm"),
            ("Number of poles (p)",                                  f"{b_mp.p}",       "-"),
            ("Moment of inertia (J)",                                f"{b_mp.J:.4f}",   "kg.m2"),
            ("Friction coefficient (B)",                             f"{b_mp.B:.4f}",   "N.m.s/rad"),
        ], col_widths=[110, 35, 25], col_aligns=["L", "R", "L"])
        pdf.ln(6)

        # ── Equivalent Circuit ─────────────────────────────────────────────
        # Keep circuit on the same page as identification and rated values.
        # Add page only if insufficient space remains.
        CIRCUIT_MIN_HEIGHT = 85  # estimated mm: title + image + caption
        space_left = (pdf.h - pdf.b_margin) - pdf.get_y()
        if space_left < CIRCUIT_MIN_HEIGHT:
            pdf.add_page()
        section_title(pdf, "Single-Phase T Equivalent Circuit")
        pdf.ln(2)
        circ_fig = _build_circuit_figure(b_mp, dark=False, palette_fn=_palette)
        circ_buf = io.BytesIO()
        circ_fig.savefig(circ_buf, format="png", dpi=200, bbox_inches="tight",
                         facecolor="white")
        plt.close(circ_fig)
        circ_buf.seek(0)
        with tempfile_ctx() as tmp_c:
            with open(tmp_c, "wb") as f_tmp:
                f_tmp.write(circ_buf.read())
            pdf.image(tmp_c, x=(210 - 170) / 2, w=170)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6, "Single-Phase T Equivalent Circuit of the Induction Motor",
                 border=0, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # ── Experiment Highlights ──────────────────────────────────────────
        pdf.add_page()
        section_title(pdf, "Experiment Highlights")

        def _kpis():
            ias_pk_  = b_res.get("ias_pk",  float(np.max(np.abs(b_res["ias"]))))
            Te_max_  = b_res.get("Te_max",  float(np.max(b_res["Te"])))
            n_ss_    = b_res["n_ss"]
            ias_rms_ = b_res["ias_rms"]
            s_val_   = b_res.get("s", 0.0)
            fator_   = b_res.get("fator_pk", ias_pk_ / ias_rms_ if ias_rms_ > 0 else 0.0)
            _dol_em_vazio_pdf = b_exp_type == "dol" and bool(b_t_events)
            if _dol_em_vazio_pdf:
                n_v_ = float(np.mean(b_res["n"][:max(1, len(b_res["n"])//5)]))
                iv_  = float(np.sqrt(np.mean(b_res["ias"][:max(1, len(b_res["ias"])//5)]**2)))
                rows_ = [
                    ("Peak current (i[sub]as,pk[/sub])",              f"{ias_pk_:.4f}",      "A"),
                    ("Maximum torque (T[sub]e,max[/sub])",             f"{Te_max_:.4f}",      "N.m"),
                    ("Speed before load",                              f"{n_v_:.3f}",          "RPM"),
                    ("Speed under load",                               f"{n_ss_:.3f}",         "RPM"),
                    ("Speed dip",                                      f"{n_v_-n_ss_:.3f}",    "RPM"),
                    ("RMS current variation",                          f"{ias_rms_-iv_:.4f}", "A"),
                ]
            elif b_exp_type in ("dol", "yd", "comp", "soft"):
                rows_ = [
                    ("Peak current (i[sub]as,pk[/sub])",                      f"{ias_pk_:.4f}",  "A"),
                    ("Peak factor (I[sub]pk[/sub]/I[sub]rms[/sub])",          f"{fator_:.4f}",   "-"),
                    ("Maximum torque (T[sub]e,max[/sub])",                     f"{Te_max_:.4f}",  "N.m"),
                    ("Final speed",                                             f"{n_ss_:.3f}",    "RPM"),
                ]
                if b_exp_type == "yd" and b_t_events:
                    t_ev_ = b_t_events[1] if len(b_t_events) > 1 else b_t_events[0]
                    idx_  = int(np.searchsorted(b_res["t"], t_ev_))
                    pk2_  = float(np.max(np.abs(b_res["ias"][idx_:]))) if idx_ < len(b_res["t"]) else 0.0
                    rows_.insert(1, ("Post Y-D peak current (i[sub]as,pk2[/sub])", f"{pk2_:.4f}", "A"))
            elif b_exp_type == "gerador":
                P_o_ = b_res.get("P_out", 0.0)
                e_g_ = b_res.get("eta", 0.0)
                u_p_ = "kW" if abs(P_o_) >= 1000 else "W"
                v_p_ = P_o_ / 1000 if abs(P_o_) >= 1000 else P_o_
                rows_ = [
                    ("Generated power (P[sub]out[/sub])",    f"{v_p_:.3f}",      u_p_),
                    ("Slip (s)",                              f"{s_val_*100:.3f}", "%"),
                    ("Efficiency (eta)",                      f"{e_g_:.3f}",      "%"),
                    ("RMS current (i[sub]as,rms[/sub])",      f"{ias_rms_:.4f}",  "A"),
                ]
            else:
                rows_ = []
            return rows_

        dest_rows = _kpis()
        if dest_rows:
            pdf.set_fill_color(200, 210, 240)
            pdf.set_text_color(20, 20, 80)
            pdf.set_font("Helvetica", "B", 10)
            for lbl, w in [("  Quantity", 110), ("Value", 35), ("Unit", 25)]:
                pdf.cell(w, 7, lbl, border=0, fill=True)
            pdf.ln(7)
            zebra_table(pdf, dest_rows, col_widths=[110, 35, 25], col_aligns=["L", "R", "L"])
            pdf.ln(6)

        # ── Trip Class (IEC 60947-4-1 / NEMA ICS 2) ───────────────────────
        if b_exp_type in ("dol", "yd", "comp", "soft", "voltage_sag"):
            _tc = _compute_trip_class(b_res, b_mp)
            if _tc is not None:
                TC_MIN = 35
                if (pdf.h - pdf.b_margin) - pdf.get_y() < TC_MIN:
                    pdf.add_page()
                section_title(pdf, "Protection Recommendation — Overload Relay")
                _tc_color = {10: (22, 163, 74), 20: (217, 119, 6), 30: (220, 38, 38)}
                r, g, b_ = _tc_color.get(_tc["class"], (80, 80, 80))
                pdf.set_fill_color(r, g, b_)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 8,
                         f"  Class {_tc['class']} — Acceleration time: {_tc['t_accel']:.2f} s "
                         f"(95% of {_tc['n_sync']:.1f} RPM) — Status: {_tc['status']}",
                         border=0, fill=True, ln=True)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5,
                         "  Reference: IEC 60947-4-1 / NEMA ICS 2 — "
                         "Class 10: t < 10 s | Class 20: 10-20 s | Class 30: > 20 s",
                         border=0, ln=True)
                pdf.ln(4)

        # ── Steady-State Indicators ────────────────────────────────────────
        section_title(pdf, "Steady-State Indicators")
        pdf.set_fill_color(200, 210, 240)
        pdf.set_text_color(20, 20, 80)
        pdf.set_font("Helvetica", "B", 10)
        for lbl, w in [("  Quantity", 110), ("Value", 35), ("Unit", 25)]:
            pdf.cell(w, 7, lbl, border=0, fill=True)
        pdf.ln(7)
        P_gap_  = b_res.get("P_gap",  0.0)
        P_mec_  = b_res.get("P_mec",  0.0)
        P_cu_r_ = b_res.get("P_cu_r", 0.0)
        eta_    = b_res.get("eta",    0.0)
        s_      = b_res.get("s",      0.0)
        P_in_   = b_res.get("P_in",   0.0)
        vi, ui   = fmt_power(P_in_)
        vg, ug   = fmt_power(P_gap_)
        vm, um   = fmt_power(P_mec_)
        vcr, ucr = fmt_power(P_cu_r_)
        zebra_table(pdf, [
            ("Steady-state speed",                                          f"{b_res['n_ss']:.3f}",                       "RPM"),
            ("Rotor angular velocity (ω[sub]r[/sub])",                     f"{b_res['wr_ss']:.4f}",                      "rad/s"),
            ("Steady-state electromagnetic torque (T[sub]e[/sub])",        f"{b_res['Te_ss']:.4f}",                      "N.m"),
            ("Maximum electromagnetic torque (T[sub]e,max[/sub])",         f"{float(np.max(b_res['Te'])):.4f}",          "N.m"),
            ("Slip (s)",                                                     f"{s_*100:.3f}",                              "%"),
            ("RMS line current (i[sub]as,rms[/sub])",                      f"{b_res['ias_rms']:.4f}",                    "A"),
            ("Peak current (i[sub]as,pk[/sub])",                           f"{float(np.max(np.abs(b_res['ias']))):.4f}", "A"),
            ("Input power (P[sub]in[/sub])",                               vi, ui),
            ("Air-gap power (P[sub]gap[/sub])",                            vg, ug),
            ("Mechanical power (P[sub]mec[/sub])",                         vm, um),
            ("Rotor copper losses (P[sub]cu,r[/sub])",                     vcr, ucr),
            ("Efficiency (eta)",                                            f"{eta_:.3f}", "%"),
        ], col_widths=[110, 35, 25], col_aligns=["L", "R", "L"])
        pdf.ln(6)

        # ── Economic Analysis ──────────────────────────────────────────────
        if b_exp_type != "shutdown":
            _em = _compute_energy_pdf(b_res, b_tariff)
            ECON_MIN_HEIGHT = 60
            if (pdf.h - pdf.b_margin) - pdf.get_y() < ECON_MIN_HEIGHT:
                pdf.add_page()
            section_title(pdf, "Economic Analysis (IAS Energy Conservation)")
            pdf.set_fill_color(200, 210, 240)
            pdf.set_text_color(20, 20, 80)
            pdf.set_font("Helvetica", "B", 10)
            for lbl, w in [("  Quantity", 110), ("Value", 40), ("Unit", 20)]:
                pdf.cell(w, 7, lbl, border=0, fill=True)
            pdf.ln(7)
            zebra_table(pdf, [
                ("Energy consumed in experiment",              f"{_em['E_kwh']:.6f}",           "kWh"),
                ("Experiment cost",                            f"$ {_em['custo_exp']:.4f}",      "-"),
                ("Steady-state input power",                   f"{_em['P_in_ss_kw']:.3f}",       "kW"),
                ("Steady-state efficiency",                    f"{_em['eta']:.2f}",              "%"),
                ("Projected annual energy (8,760 h/yr)",       f"{_em['P_in_ss_kw']*8760:.1f}", "kWh/yr"),
                ("Projected annual operating cost",            f"$ {_em['custo_ano']:,.2f}",     "-"),
            ], col_widths=[110, 40, 20], col_aligns=["L", "R", "L"])
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"  Tariff used: $ {b_tariff:.2f}/kWh  |  "
                           "Projection based on continuous operation at 8,760 h/yr.",
                     border=0, ln=True)
            pdf.ln(4)

            # ── Power Quality (THD + PF) ───────────────────────────────────
            _thd = _em.get("thd_pct", 0.0)
            _fp  = _em.get("fp", 0.0)
            if _thd > 0 or _fp > 0:
                QE_MIN_HEIGHT = 40
                if (pdf.h - pdf.b_margin) - pdf.get_y() < QE_MIN_HEIGHT:
                    pdf.add_page()
                section_title(pdf, "Power Quality")
                pdf.set_fill_color(200, 210, 240)
                pdf.set_text_color(20, 20, 80)
                pdf.set_font("Helvetica", "B", 10)
                for lbl, w in [("  Quantity", 110), ("Value", 40), ("Status", 20)]:
                    pdf.cell(w, 7, lbl, border=0, fill=True)
                pdf.ln(7)
                _thd_ok = _thd <= 5.0
                _fp_ok  = _fp >= 0.85
                zebra_table(pdf, [
                    ("Power Factor (PF)",                           f"{_fp:.4f}",         "OK" if _fp_ok else "LOW"),
                    ("Current THD (i[sub]as[/sub])",                f"{_thd:.2f} %",      "OK" if _thd_ok else "HIGH"),
                ], col_widths=[110, 40, 20], col_aligns=["L", "R", "L"])
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, "  THD via FFT of ias (steady state). PF = Pin / Sapparent.",
                         border=0, ln=True)
                pdf.ln(4)

                # ── Harmonic Spectrum ──────────────────────────────────────
                _harm_rows = _compute_thd_harmonics(b_res, b_mp)
                if _harm_rows:
                    HARM_MIN = 40
                    if (pdf.h - pdf.b_margin) - pdf.get_y() < HARM_MIN:
                        pdf.add_page()
                    section_title(pdf, "Harmonic Spectrum — i[sub]as[/sub] (Orders 1 to 9)")
                    pdf.set_fill_color(200, 210, 240)
                    pdf.set_text_color(20, 20, 80)
                    pdf.set_font("Helvetica", "B", 10)
                    for lbl, w in [("  Order", 30), ("Frequency (Hz)", 45), ("Amplitude (A)", 55), ("Relative (%)", 40)]:
                        pdf.cell(w, 7, lbl, border=0, fill=True)
                    pdf.ln(7)
                    harm_table = [
                        (f"{k}", f"{fk:.1f}", f"{Ak:.4f}", f"{pct:.2f}")
                        for k, fk, Ak, pct in _harm_rows
                    ]
                    zebra_table(pdf, harm_table, col_widths=[30, 45, 55, 40], col_aligns=["C", "R", "R", "R"])
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 5, "  Relative amplitudes normalised by the fundamental (1st harmonic). Reference: IEEE 519-2022.",
                             border=0, ln=True)
                    pdf.ln(4)

        # ── Current Signature (FFT) ────────────────────────────────────────
        _fft_key = next((k for k in ("ias", "ibs", "ics") if k in b_res), None)
        if _fft_key is not None and int(b_res.get("_ss_start", 0)) < len(b_res["t"]) - 4:
            _alpha = float(b_res.get("_broken_bar_severity", 0.0))
            FFT_MIN_HEIGHT = 75
            if (pdf.h - pdf.b_margin) - pdf.get_y() < FFT_MIN_HEIGHT:
                pdf.add_page()
            _fft_title = "Current Signature (FFT)"
            if _alpha > 0:
                _fft_title += f"  —  Broken bar active (alpha={_alpha:.2f})"
            section_title(pdf, _fft_title)
            pdf.ln(2)
            _mpl_to_pdf(_build_fft_fig(b_res, key=_fft_key), width_mm=170)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(80, 80, 80)
            _fft_caption = "Red lines: odd harmonics (1st, 3rd, 5th, 7th, 9th)."
            if _alpha > 0:
                _s = float(b_res.get("s", 0.0))
                _fft_caption += (
                    f"  Orange lines: broken-bar sidebands "
                    f"(1+/-2s)f = {b_mp.f*(1-2*abs(_s)):.1f} Hz / {b_mp.f*(1+2*abs(_s)):.1f} Hz  "
                    f"(s={_s*100:.2f}%)."
                )
            pdf.cell(0, 5, _fft_caption,
                     border=0, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # ── Expert Diagnostics ─────────────────────────────────────────────
        if b_insights:
            DIAG_MIN = 40
            if (pdf.h - pdf.b_margin) - pdf.get_y() < DIAG_MIN:
                pdf.add_page()
            section_title(pdf, "Automated Diagnostics")
            _LEVEL_COLORS = {
                "error":   (220, 38,  38),
                "warning": (217, 119, 6),
                "info":    (22,  163, 74),
            }
            _LEVEL_LABELS = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}
            for ins in b_insights:
                r, g, b_ = _LEVEL_COLORS.get(ins.level, (80, 80, 80))
                lbl = _LEVEL_LABELS.get(ins.level, ins.level.upper())
                # coloured insight header
                pdf.set_fill_color(r, g, b_)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 7, f"  [{lbl}]  {ins.title}", border=0, fill=True, ln=True)
                # body
                pdf.set_fill_color(245, 247, 255)
                pdf.set_text_color(40, 40, 40)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"  {ins.body}", border=0)
                pdf.ln(2)
            pdf.ln(2)

        # ── Operating Mode Analysis ────────────────────────────────────────
        if exp_config and b_is_main:
            _mode = exp_config.get("exp_type", exp_type)

            if _mode == "frenagem":
                if (pdf.h - pdf.b_margin) - pdf.get_y() < 50:
                    pdf.add_page()
                section_title(pdf, "Electric Braking Analysis")
                _brake = exp_config.get("brake_method", "plugging")
                _BRAKE_NAMES = {
                    "plugging":    "Polarity Reversal (Plugging)",
                    "injecao_cc":  "DC Injection Braking",
                    "regenerativo":"Regenerative Braking",
                }
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(22, 54, 120)
                pdf.cell(0, 6, f"  Method: {_BRAKE_NAMES.get(_brake, _brake)}", ln=True)
                pdf.set_text_color(40, 40, 40)
                t_freia = exp_config.get("t_brake", exp_config.get("t_freia", 0.0))
                _wm_arr = np.asarray(b_res.get("wr", b_res.get("wm", [0.0])))
                _t_arr  = np.asarray(b_res.get("t", [0.0]))
                _ia_arr = np.asarray(b_res.get("ias", b_res.get("ia", [0.0])))
                _idx_f  = int(np.searchsorted(_t_arr, t_freia))
                _wm_bef = float(_wm_arr[max(_idx_f-1, 0)]) if len(_wm_arr) > 0 else 0.0
                _ia_pk  = float(np.max(np.abs(_ia_arr[_idx_f:]))) if _idx_f < len(_ia_arr) else 0.0
                _idx_stop = next((i for i in range(_idx_f, len(_wm_arr)) if abs(_wm_arr[i]) < 1.0), len(_wm_arr)-1)
                _t_stop = float(_t_arr[_idx_stop]) - t_freia if _idx_stop < len(_t_arr) else None
                _rows_b = [
                    ("Braking instant",                f"{t_freia:.3f} s"),
                    ("Speed before braking",           f"{_wm_bef * 60/(2*3.14159):.1f} RPM"),
                    ("Post-braking peak current",      f"{_ia_pk:.3f} A"),
                ]
                if _t_stop is not None:
                    _rows_b.append(("Estimated time to stop", f"{_t_stop:.3f} s"))
                if _brake == "injecao_cc":
                    _rows_b.append(("Injected DC voltage", f"{exp_config.get('Vcc_inj', 0.0):.2f} V"))
                elif _brake == "regenerativo":
                    _rows_b.append(("Reduced voltage (%)", f"{exp_config.get('V_regen', 0):.0f}%"))
                pdf.set_fill_color(200, 210, 245)
                pdf.set_font("Helvetica", "B", 9)
                for lbl, val in [("Indicator", "Value")]:
                    pdf.cell(115, 6, f"  {lbl}", border=0, fill=True)
                    pdf.cell(55,  6, f"  {val}", border=0, fill=True, ln=True)
                for idx, (lbl, val) in enumerate(_rows_b):
                    _fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
                    pdf.set_fill_color(*_fill)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(40, 40, 40)
                    pdf.cell(115, 6, f"  {lbl}", border=0, fill=True)
                    pdf.cell(55,  6, f"  {val}", border=0, fill=True, ln=True)
                pdf.ln(3)

            elif _mode == "gerador":
                if (pdf.h - pdf.b_margin) - pdf.get_y() < 50:
                    pdf.add_page()
                section_title(pdf, "Generator Mode Analysis")
                _wr_ss = float(b_res.get("wr_ss", 0.0))
                _Te_ss = float(b_res.get("Te_ss", 0.0))
                _P_mec = abs(_Te_ss) * abs(_wr_ss)
                _P_ele = float(b_res.get("P_out_ss", _P_mec * GEN_EFFICIENCY_FALLBACK))
                _eta_g = _P_ele / _P_mec * 100 if _P_mec > 1e-3 else 0.0
                _rows_g = [
                    ("Steady-state speed",           f"{_wr_ss * 60/(2*3.14159):.1f} RPM"),
                    ("Input torque (T_e,ss)",         f"{_Te_ss:.3f} N.m"),
                    ("Input mechanical power",        f"{_P_mec:.2f} W"),
                    ("Generated electrical power",    f"{_P_ele:.2f} W"),
                    ("Estimated efficiency",          f"{_eta_g:.1f} %"),
                ]
                pdf.set_fill_color(200, 210, 245)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(115, 6, "  Indicator", border=0, fill=True)
                pdf.cell(55,  6, "  Value",     border=0, fill=True, ln=True)
                for idx, (lbl, val) in enumerate(_rows_g):
                    _fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
                    pdf.set_fill_color(*_fill)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(40, 40, 40)
                    pdf.cell(115, 6, f"  {lbl}", border=0, fill=True)
                    pdf.cell(55,  6, f"  {val}", border=0, fill=True, ln=True)
                pdf.ln(3)

            # Thermal evolution (if data available)
            _theta_s = b_res.get("theta_s") or b_res.get("Temp")
            _t_therm = b_res.get("t")
            if _theta_s is not None and _t_therm is not None:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                _ts = np.asarray(_theta_s)
                _tt = np.asarray(_t_therm)
                if len(_ts) == len(_tt) and len(_ts) > 2 and _ts.max() - _ts.min() > 0.1:
                    if (pdf.h - pdf.b_margin) - pdf.get_y() < 70:
                        pdf.add_page()
                    section_title(pdf, "Thermal Evolution")
                    _fig_th, _ax_th = plt.subplots(figsize=(9, 3))
                    _fig_th.patch.set_facecolor("white")
                    _ax_th.plot(_tt, _ts, color="#1d4ed8", linewidth=1.2, label="theta stator")
                    _theta_r = b_res.get("theta_r")
                    if _theta_r is not None:
                        _tr2 = np.asarray(_theta_r)
                        if len(_tr2) == len(_tt):
                            _ax_th.plot(_tt, _tr2, color="#dc2626", linewidth=1.2, label="theta rotor")
                    _ax_th.set_xlabel("Time (s)", fontsize=8)
                    _ax_th.set_ylabel("Temperature (degC)", fontsize=8)
                    _ax_th.legend(fontsize=8)
                    _ax_th.grid(True, color="#dde4f5", linewidth=0.4)
                    _ax_th.spines[["top", "right"]].set_visible(False)
                    _ax_th.tick_params(labelsize=8)
                    _fig_th.subplots_adjust(left=0.1, right=0.97, top=0.94, bottom=0.2)
                    embed_fig(pdf, _fig_th, w=175)
                    plt.close(_fig_th)
                    pdf.ln(2)

        # ── Parameter Estimation ───────────────────────────────────────────
        if input_mode and input_mode != "Enter parameters manually" and b_is_main:
            if (pdf.h - pdf.b_margin) - pdf.get_y() < 60:
                pdf.add_page()
            section_title(pdf, "Parameter Estimation")
            if "Nameplate" in input_mode:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(22, 54, 120)
                pdf.cell(0, 6, "  Method: Nameplate (NEMA MG-1 — Heuristic)", ln=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 5, "  Parameters estimated from the nameplate data "
                               "using NEMA MG-1 heuristics. Used directly in the simulation.")
            else:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(22, 54, 120)
                pdf.cell(0, 6, "  Method: IEEE Std 112-2017 — Physical Tests", ln=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 5, "  Parameters determined by the iterative procedure "
                               "IEEE Std 112-2017 Eq. (38)-(49): DC test (Rs), no-load test "
                               "(Xm, Rfe, Pfw) and locked-rotor test (Rr, Xls, Xlr).")
            pdf.ln(2)
            _est_rows = [
                ("Stator resistance (R_s)",              f"{mp.Rs:.5f} Ohm"),
                ("Rotor resistance (R_r)",               f"{mp.Rr:.5f} Ohm"),
                ("Magnetising reactance (X_m)",          f"{mp.Xm:.4f} Ohm"),
                ("Stator leakage reactance (X_ls)",      f"{mp.Xls:.5f} Ohm"),
                ("Rotor leakage reactance (X_lr)",       f"{mp.Xlr:.5f} Ohm"),
                ("Iron-loss resistance (R_fe)",          f"{mp.Rfe:.1f} Ohm"),
            ]
            pdf.set_fill_color(200, 210, 245)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(115, 6, "  Parameter", border=0, fill=True)
            pdf.cell(55,  6, "  Value",     border=0, fill=True, ln=True)
            for idx, (lbl, val) in enumerate(_est_rows):
                _fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*_fill)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(40, 40, 40)
                pdf.cell(115, 6, f"  {lbl}", border=0, fill=True)
                pdf.cell(55,  6, f"  {val}", border=0, fill=True, ln=True)
            pdf.ln(3)

        # ── Characteristic Curves ──────────────────────────────────────────
        b_chunks = _make_chunks(b_var_keys, b_var_labels)
        for pg, (ck, cl) in enumerate(b_chunks):
            pdf.add_page()
            sfx = f" ({pg+1}/{len(b_chunks)})" if len(b_chunks) > 1 else ""
            section_title(pdf, f"Characteristic Curves{sfx}")
            pdf.ln(2)
            _tl_overlay = b_res.get("TL") if "Te" in ck else None
            _mpl_to_pdf(_build_pdf_page_fig(b_res, ck, cl, b_t_events, color_offset=pg * 4,
                                            tl_arr=_tl_overlay))
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, ", ".join(cl),
                     border=0, align="C", new_x="LMARGIN", new_y="NEXT")

    # ══════════════════════════════════════════════════════════════════════
    # INITIALISE PDF
    # ══════════════════════════════════════════════════════════════════════
    pdf = EMS_PDF()
    pdf.alias_nb_pages()
    pdf.set_margins(left=20, top=24, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── Block: Current Simulation ──────────────────────────────────────────
    _block_banner("Current Simulation")
    _write_block(res, mp, exp_label, exp_type, t_events, var_keys, var_labels,
                 b_tariff=energy_tariff, b_insights=insights, b_load_torque=load_torque,
                 b_is_main=True)

    # ── Block: each Reference ──────────────────────────────────────────────
    for ref_i, r in enumerate(ref_list or []):
        ref_res = r.get("res")
        if ref_res is None:
            continue
        ref_mp         = r.get("mp", mp)
        ref_label      = r.get("exp_label", f"Reference {ref_i+1}")
        ref_exp_type   = r.get("exp_type", "dol")
        ref_t_events   = r.get("t_events", [])
        ref_var_keys   = r.get("var_keys") or var_keys
        ref_var_labels = r.get("var_labels") or var_labels
        ref_tariff     = r.get("energy_tariff", energy_tariff)
        _block_banner(f"Reference {ref_i+1} — {ref_label}")
        _write_block(ref_res, ref_mp, ref_label, ref_exp_type, ref_t_events,
                     ref_var_keys, ref_var_labels, b_tariff=ref_tariff)

    # ── Final Section: Overlaid Plots ──────────────────────────────────────
    if ref_list:
        chart_refs = [
            {
                "res":   r["res"],
                "color": r.get("color", "#888888"),
                "dash":  r.get("dash", "dash"),
                "label": r.get("exp_label", "Reference"),
            }
            for r in ref_list if r.get("res") is not None
        ]
        if chart_refs:
            main_chunks = _make_chunks(var_keys, var_labels)
            for pg, (ck, cl) in enumerate(main_chunks):
                valid_k = [k for k in ck if k in res]
                if not valid_k:
                    continue
                valid_l = [cl[ck.index(k)] for k in valid_k]
                pdf.add_page()
                sfx = f" ({pg+1}/{len(main_chunks)})" if len(main_chunks) > 1 else ""
                section_title(pdf, f"Comparative Curves — Overlaid{sfx}")
                pdf.ln(2)
                _mpl_to_pdf(_build_pdf_page_fig(
                    res, valid_k, valid_l, t_events,
                    color_offset=pg * 4, ref_list=chart_refs,
                ))
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(80, 80, 80)
                names = "Current vs. " + ", ".join(r["label"] for r in chart_refs)
                pdf.cell(0, 5, names,
                         border=0, align="C", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def tempfile_ctx():
    """Simple context manager for a temporary PNG file."""
    import tempfile, os
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            yield path
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
    return _ctx()


def embed_fig(pdf, fig_or_bytes, w: float = 170) -> None:
    import io as _io
    import tempfile, os
    from contextlib import contextmanager

    @contextmanager
    def _tmp():
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            yield path
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    if isinstance(fig_or_bytes, (bytes, bytearray)):
        png = fig_or_bytes
    else:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        buf = _io.BytesIO()
        fig_or_bytes.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white")
        plt.close(fig_or_bytes)
        buf.seek(0)
        png = buf.read()

    with _tmp() as tmp:
        with open(tmp, "wb") as f:
            f.write(png)
        pdf.image(tmp, x=(210 - w) / 2, w=w)
