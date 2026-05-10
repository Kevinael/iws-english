# -*- coding: utf-8 -*-
"""
pdf_report_v2.py — Relatório técnico V2 com dois estilos de layout.

Estilos disponíveis:
  "academico"  — IEEE/ABNT: seções numeradas, tipografia formal, subíndices reais
  "dashboard"  — Dashboard Técnico: KPI cards, barra de perdas colorida, leitura rápida

Exporta:
  generate_pdf_report_v2(style, exp_label, mp, res, var_keys, var_labels,
                         t_events, exp_type, ref_list, energy_tariff) -> bytes
"""

from __future__ import annotations
import io
import numpy as np
from core.EMS_PY import MachineParams
from viz.eqcircuit_plotter import build_figure as _build_circuit_figure
from ui.theme import _palette


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários compartilhados
# ─────────────────────────────────────────────────────────────────────────────

# Mapa de substituição: apenas caracteres fora do latin-1 (código > 255).
# Acentos portugueses (á, é, ã, ç, ó, etc.) são latin-1 nativos — NÃO entram aqui.
_LATIN1_MAP: dict[str, str] = {
    # traços
    "—": "-",   # —  em dash
    "–": "-",   # –  en dash
    "−": "-",   # −  sinal de menos matemático
    # omega / letras gregas
    "Ω": "Ohm", # Ω
    "η": "eta", # η
    "α": "alfa",# α
    "ω": "w",   # ω
    "μ": "u",   # µ (micro — já é latin-1 \xB5, mas Unicode é diferente)
    # operadores / símbolos matemáticos
    "·": ".",   # · ponto central
    "²": "2",   # ² sobrescrito 2
    "³": "3",   # ³ sobrescrito 3
    "¹": "1",   # ¹ sobrescrito 1
    "⁰": "0",   # ⁰
    "⁴": "4",   # ⁴
    "⁵": "5",   # ⁵
    "⁶": "6",   # ⁶
    "⁷": "7",   # ⁷
    "⁸": "8",   # ⁸
    "⁹": "9",   # ⁹
    "⁻": "-",   # ⁻
    "₀": "0",   # ₀
    "₁": "1",   # ₁
    "₂": "2",   # ₂
    "₃": "3",   # ₃
    "₄": "4",   # ₄
    "₅": "5",   # ₅
    "₆": "6",   # ₆
    "₇": "7",   # ₇
    "₈": "8",   # ₈
    "₉": "9",   # ₉
    "≥": ">=",  # ≥
    "≤": "<=",  # ≤
    "×": "x",   # ×
    "°": " graus",# °
    "≠": "!=",  # ≠
    "≈": "~",   # ≈
    # outros
    "’": "'",   # ' aspa direita
    "‘": "'",   # ' aspa esquerda
    "“": '"',   # " aspas
    "”": '"',   # "
    "…": "...", # …
    "½": "1/2", # ½
    "∞": "inf", # ∞
    "Δ": "Delta",# Δ
    "Φ": "Phi", # Φ
    "φ": "phi", # φ
    "σ": "sigma",# σ
    "λ": "lambda",# λ
    "∂": "d",   # ∂
    "∫": "int", # ∫
    "√": "sqrt",# √
    "±": "+/-", # ±
    "µ": "u",   # µ (latin-1 micro — redundância segura)
    # subscrito/sobrescrito Unicode literais (caso apareçam fora das marcações)
    "ₑ": "e",   # ₑ
    "ₐ": "a",   # ₐ
    "ₛ": "s",   # ₛ
    "ᵣ": "r",   # ᵣ
    # "," é vírgula ASCII normal — linha removida (era erro)
}


def _safe(text: str) -> str:
    """Converte texto para latin-1 seguro para Helvetica (fpdf2 built-in).

    Preserva todos os acentos portugueses (latin-1 nativos).
    Substitui apenas os caracteres Unicode fora do bloco latin-1 (> U+00FF).
    """
    for ch, repl in _LATIN1_MAP.items():
        text = text.replace(ch, repl)
    # codificação defensiva: qualquer remanescente fora do latin-1 é descartado
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _fmt_power(val: float) -> tuple[str, str]:
    if abs(val) >= 1000:
        return f"{val/1000:.3f}", "kW"
    return f"{val:.2f}", "W"


def _tempfile_ctx():
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


def _fig_to_pdf_bytes(mpl_fig) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def _embed_fig(pdf, png_bytes: bytes, width_mm: float = 165) -> None:
    with _tempfile_ctx() as tmp:
        with open(tmp, "wb") as f:
            f.write(png_bytes)
        pdf.image(tmp, x=(210 - width_mm) / 2, w=width_mm)


def _build_circuit_bytes(mp: MachineParams) -> bytes:
    """Gera o circuito equivalente monofásico em T como PNG (bytes)."""
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
# Renderização de texto com sub/sobrescritos inline
# Notação: "R[sub]s[/sub]" → R com 's' como subíndice
#          "f[sup]2[/sup]" → f com '2' como sobrescrição
# ─────────────────────────────────────────────────────────────────────────────

def _render_rich(pdf, text: str, main_size: int = 10, cell_h: float = 6.0,
                 fill: bool = False, align: str = "L", newline: bool = False) -> None:
    """Renderiza texto com marcações [sub]...[/sub] e [sup]...[/sup].

    Avança o cursor para após o texto; se newline=True, quebra linha.
    """
    import re
    parts = re.split(r'(\[sub\].*?\[/sub\]|\[sup\].*?\[/sup\])', text)

    SUB_SIZE = max(6, main_size - 3)
    SUP_SIZE = max(6, main_size - 3)
    SUB_DY   =  2.0   # descida relativa ao baseline
    SUP_DY   = -2.0   # subida relativa ao baseline

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
    """Renderiza uma célula de largura fixa com suporte a sub/sobrescritos."""
    import re
    has_markup = bool(re.search(r'\[sub\]|\[sup\]', text))

    pdf.set_fill_color(*fill_rgb)
    x0, y0 = pdf.get_x(), pdf.get_y()

    # fundo da célula
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
# Cálculos das seções extras
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

    severity_label = "Severa" if alpha >= 0.5 else ("Moderada" if alpha >= 0.2 else "Leve")
    return {
        "alpha": alpha, "s_val": s_val,
        "f_lo": f_lo, "f_hi": f_hi,
        "sb_ratio_lo": sb_ratio_lo, "sb_ratio_hi": sb_ratio_hi,
        "severity_label": severity_label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Figuras matplotlib
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
        ax.set_xlabel("Tempo (s)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_facecolor("#f9fafc")
        ax.grid(True, color="#dde4f5", linewidth=0.4)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=7, framealpha=0.8)

    axes[0].set_ylabel("Corrente (A)", fontsize=8)
    fig.suptitle("Correntes de Fase ABC — Regime Permanente", fontsize=10, fontweight="bold")
    fig.tight_layout()
    return fig


def _build_losses_bar_fig(losses: dict) -> "matplotlib.figure.Figure":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cats   = [
        "Perdas no cobre\ndo estator  $P_{cu,s}$",
        "Perdas no cobre\ndo rotor  $P_{cu,r}$",
        "Perdas no\nferro  $P_{fe}$",
        "Potência\nmecânica  $P_{mec}$",
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
    ax.set_xlabel("Potência (W)", fontsize=8)
    ax.set_title("Balanço de Perdas — Regime Permanente", fontsize=9, fontweight="bold")
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
        ax.set_xlabel("Tempo (s)", fontsize=8)
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
                label=f"Pico: {float(np.abs(y[pk_idx])):.2f}")
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
# CLASSE BASE PDF — cabeçalho, rodapé e primitivos compartilhados
# ─────────────────────────────────────────────────────────────────────────────

def _make_pdf_class(style: str):
    from fpdf import FPDF
    import datetime

    style_label = ("Acadêmico Estruturado"
                   if style == "academico" else "Dashboard Técnico")

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
                      f"EMS - Relatorio V2 ({style_label})",
                      border=0)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 100, 100)
            self.set_xy(130, 4)
            ts = datetime.datetime.now().strftime("%d/%m/%Y")
            self.cell(60, 8, f"Gerado em: {ts}", border=0, align="R")
            self.ln(6)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8,
                      f"Pagina {self.page_no()} de {{nb}}",
                      align="C")

    return EMS_PDF_V2


# ─────────────────────────────────────────────────────────────────────────────
# ESTILO ACADÊMICO
# ─────────────────────────────────────────────────────────────────────────────

def _generate_academico(
    pdf, exp_label: str, mp: MachineParams, res: dict,
    var_keys: list, var_labels: list, t_events: list,
    exp_type: str, energy_tariff: float,
    losses: dict, integrator: dict, broken_bar: dict | None,
) -> None:
    import datetime

    # ── helpers locais ────────────────────────────────────────────────────

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
        """Cabeçalho de tabela com suporte a sub/sobrescritos."""
        pdf.set_fill_color(200, 210, 245)
        pdf.set_text_color(20, 20, 80)
        x0, y0 = pdf.get_x(), pdf.get_y()
        for lbl, w in cols:
            _cell_rich(pdf, f"  {lbl}", w, 6, main_size=9,
                       fill_rgb=(200, 210, 245), text_rgb=(20, 20, 80))
        pdf.set_xy(x0, y0 + 6)
        pdf.ln(0)

    def tr(rows: list[tuple], widths: list[float], aligns: list[str]) -> None:
        """Linhas de tabela com zebra e suporte a sub/sobrescritos."""
        for idx, row in enumerate(rows):
            fill = (242, 245, 255) if idx % 2 == 0 else (255, 255, 255)
            x0, y0 = pdf.get_x(), pdf.get_y()
            for cell, w, align in zip(row, widths, aligns):
                _cell_rich(pdf, f"  {str(cell)}", w, 6, main_size=9,
                           fill_rgb=fill, text_rgb=(40, 40, 40))
            pdf.set_xy(x0, y0 + 6)
            pdf.ln(0)

    # ── Capa ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(15, 40, 100)
    pdf.rect(0, 0, 210, 65, style="F")
    pdf.set_xy(20, 14)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "EMS — Relatório Técnico de Simulação",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 30)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Versão 2 — Estilo Acadêmico Estruturado",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 44)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Experimento: {exp_label}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 54)
    pdf.set_font("Helvetica", "I", 9)
    ts = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M")
    pdf.cell(0, 6, f"Gerado em: {ts}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── 1. Identificação do Experimento ──────────────────────────────────
    sec("Identificação do Experimento", "1.")
    th([("Atributo", 90), ("Valor", 80)])
    tr([
        ("Experimento",                        exp_label),
        ("Tipo de partida/operação",            exp_type.upper()),
        ("Velocidade síncrona",                 f"{mp.n_sync:.1f} RPM"),
        ("Frequência nominal",                  f"{mp.f:.1f} Hz"),
        ("Número de polos",                     str(mp.p)),
        ("Tensão de linha (V[sub]l[/sub])",     f"{mp.Vl:.1f} V"),
    ], [90, 80], ["L", "L"])
    pdf.ln(4)

    # ── 2. Parâmetros da Máquina ─────────────────────────────────────────
    sec("Parâmetros da Máquina", "2.")
    th([("Parâmetro", 100), ("Valor", 45), ("Unidade", 25)])
    tr([
        ("Resistência do estator (R[sub]s[/sub])",          f"{mp.Rs:.4f}",  "Ω"),
        ("Resistência do rotor (R[sub]r[/sub])",            f"{mp.Rr:.4f}",  "Ω"),
        ("Reatância de magnetização (X[sub]m[/sub])",       f"{mp.Xm:.4f}",  "Ω"),
        ("Reatância de dispersão do estator (X[sub]ls[/sub])", f"{mp.Xls:.4f}", "Ω"),
        ("Reatância de dispersão do rotor (X[sub]lr[/sub])", f"{mp.Xlr:.4f}", "Ω"),
        ("Resistência de perdas no ferro (R[sub]fe[/sub])", f"{mp.Rfe:.1f}", "Ω"),
        ("Momento de inércia (J)",                           f"{mp.J:.4f}",   "kg·m²"),
        ("Coeficiente de atrito (B)",                        f"{mp.B:.4f}",   "N·m·s/rad"),
    ], [100, 45, 25], ["L", "R", "L"])
    pdf.ln(4)

    # ── 2.1 Circuito Equivalente Monofásico em T ──────────────────────────
    CIRC_MIN = 85
    if (pdf.h - pdf.b_margin) - pdf.get_y() < CIRC_MIN:
        pdf.add_page()
    subsec("2.1  Circuito Equivalente Monofásico em T")
    pdf.ln(1)
    _embed_fig(pdf, _build_circuit_bytes(mp), width_mm=160)
    caption(
        "Figura 2.1 — Circuito equivalente monofásico em T do Motor de Indução Trifásico. "
        "R[sub]s[/sub]: resistência do estator; X[sub]ls[/sub]: reatância de dispersão do estator; "
        "X[sub]m[/sub]: reatância de magnetização; R[sub]fe[/sub]: resistência de perdas no ferro; "
        "X[sub]lr[/sub]: reatância de dispersão do rotor; R[sub]r[/sub]/s: resistência do rotor referida ao estator."
    )
    pdf.ln(3)

    # ── 3. Indicadores de Regime Permanente ─────────────────────────────
    pdf.add_page()
    sec("Indicadores de Regime Permanente", "3.")
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
    th([("Grandeza", 105), ("Valor", 45), ("Unidade", 20)])
    tr([
        ("Velocidade de regime",
         f"{res['n_ss']:.3f}",                                "RPM"),
        ("Velocidade angular do rotor (ω[sub]r[/sub])",
         f"{res['wr_ss']:.4f}",                               "rad/s"),
        ("Torque eletromagnético de regime (T[sub]e[/sub])",
         f"{res['Te_ss']:.4f}",                               "N·m"),
        ("Torque eletromagnético máximo (T[sub]e,max[/sub])",
         f"{float(np.max(res['Te'])):.4f}",                   "N·m"),
        ("Escorregamento (s)",
         f"{s_val*100:.3f}",                                  "%"),
        ("Corrente de linha eficaz (I[sub]as,rms[/sub])",
         f"{res['ias_rms']:.4f}",                              "A"),
        ("Corrente de pico (I[sub]as,pk[/sub])",
         f"{float(np.max(np.abs(res['ias']))):.4f}",           "A"),
        ("Potência de entrada (P[sub]in[/sub])",               vi,  ui),
        ("Potência no entreferro (P[sub]gap[/sub])",           vg,  ug),
        ("Potência mecânica (P[sub]mec[/sub])",                vm,  um),
        ("Perdas no cobre do rotor (P[sub]cu,r[/sub])",        vcr, ucr),
        ("Rendimento (η)",
         f"{eta:.3f}",                                         "%"),
    ], [105, 45, 20], ["L", "R", "L"])
    pdf.ln(4)

    # ── 4. Balanço de Perdas ─────────────────────────────────────────────
    LOSS_MIN = 100
    if (pdf.h - pdf.b_margin) - pdf.get_y() < LOSS_MIN:
        pdf.add_page()
    sec("Balanço de Perdas (Regime Permanente)", "4.")
    lf,  uf  = _fmt_power(losses["P_cu_s"])
    lg,  ug_ = _fmt_power(losses["P_cu_r"])
    lh,  uh  = _fmt_power(losses["P_fe"])
    li,  ui_ = _fmt_power(max(losses["P_mec"], 0.0))
    th([("Componente", 100), ("Valor", 38), ("Unidade", 18), ("% de P[sub]in[/sub]", 24)])
    tr([
        ("Perdas no cobre do estator (P[sub]cu,s[/sub])",  lf,  uf,  f"{losses['pct_cu_s']:.1f}%"),
        ("Perdas no cobre do rotor (P[sub]cu,r[/sub])",    lg,  ug_, f"{losses['pct_cu_r']:.1f}%"),
        ("Perdas no ferro (P[sub]fe[/sub])",                lh,  uh,  f"{losses['pct_fe']:.1f}%"),
        ("Potência mecânica útil (P[sub]mec[/sub])",        li,  ui_, f"{losses['pct_mec']:.1f}%"),
    ], [100, 38, 18, 24], ["L", "R", "L", "R"])
    pdf.ln(2)
    loss_fig = _build_losses_bar_fig(losses)
    _embed_fig(pdf, _fig_to_pdf_bytes(loss_fig), width_mm=155)
    caption(
        "Figura 4.1 — Distribuição percentual das perdas em regime permanente "
        "em relação à potência de entrada Pₙₙ."
    )
    pdf.ln(2)

    # ── 5. Parâmetros do Integrador Numérico ─────────────────────────────
    INTEG_MIN = 55
    if (pdf.h - pdf.b_margin) - pdf.get_y() < INTEG_MIN:
        pdf.add_page()
    sec("Parâmetros do Integrador Numérico (LSODA)", "5.")
    ny_status = ("Satisfeito (≥ 10 amostras/ciclo)"
                 if integrator["nyquist_ok"]
                 else "ATENÇÃO: insuficiente — RMS e FFT podem ser imprecisos")
    th([("Parâmetro", 115), ("Valor", 55)])
    tr([
        ("Passo de amostragem solicitado (h)",                  f"{integrator['h_req']:.6f} s"),
        ("Passo efetivo médio",                                  f"{integrator['dt_eff']:.6f} s"),
        ("Amostras por ciclo (f[sub]n[/sub] / h[sub]ef[/sub])", f"{integrator['samples_per_cycle']:.1f}"),
        ("Total de pontos de saída",                             str(integrator["n_steps"])),
        ("Duração total simulada (t[sub]max[/sub])",            f"{integrator['tmax']:.3f} s"),
        ("Critério de Nyquist",                                  ny_status),
    ], [115, 55], ["L", "L"])
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5,
        "  Integrador: LSODA (scipy.integrate.solve_ivp), com controle adaptativo "
        "de passo e tolerâncias RTOL = 1×10⁻⁵, ATOL = 1×10⁻⁶.")
    pdf.ln(3)

    # ── 6. Indicadores de Falha — Barra Quebrada (MCSA) ──────────────────
    if broken_bar is not None:
        BB_MIN = 60
        if (pdf.h - pdf.b_margin) - pdf.get_y() < BB_MIN:
            pdf.add_page()
        sec("Indicadores de Falha — Barra Quebrada (MCSA)", "6.")
        subsec("Análise Espectral de Corrente (Motor Current Signature Analysis)")
        th([("Indicador", 115), ("Valor", 55)])
        tr([
            ("Severidade (α)",                              f"{broken_bar['alpha']:.3f}"),
            ("Classificação de severidade",                       broken_bar["severity_label"]),
            ("Escorregamento em regime (s)",                      f"{broken_bar['s_val']*100:.3f} %"),
            ("Frequência lateral inferior (1−2s)f",         f"{broken_bar['f_lo']:.2f} Hz"),
            ("Frequência lateral superior (1+2s)f",              f"{broken_bar['f_hi']:.2f} Hz"),
            ("Amplitude relativa de (1−2s)f / fundamental", f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Amplitude relativa de (1+2s)f / fundamental",      f"{broken_bar['sb_ratio_hi']:.2f} %"),
        ], [115, 55], ["L", "L"])
        body(
            "Referência: IEEE 1159-2019 — Motor Current Signature Analysis (MCSA). "
            "Amplitude relativa dos componentes laterais acima de 3% da fundamental indica "
            "falha incipiente; acima de 10% indica falha severa."
        )
        pdf.ln(2)
        sec_num = "7."
    else:
        sec_num = "6."

    # ── 7 (ou 6). Correntes de Fase ABC ──────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        ABC_MIN = 80
        if (pdf.h - pdf.b_margin) - pdf.get_y() < ABC_MIN:
            pdf.add_page()
        sec("Correntes de Fase ABC — Regime Permanente", sec_num)
        abc_fig = _build_abc_currents_fig(res)
        _embed_fig(pdf, _fig_to_pdf_bytes(abc_fig), width_mm=165)
        ias_rms = float(res.get("ias_rms", 0.0))
        caption(
            f"Figura {sec_num[:-1]}.1 — Correntes de fase i[sub]as[/sub], "
            f"i[sub]bs[/sub], i[sub]cs[/sub] em regime permanente. "
            f"Tracejado: ± RMS (I[sub]as,rms[/sub] = {ias_rms:.3f} A). "
            "Sistema equilibrado apresenta amplitudes iguais e defasagem de 120°."
        )
        pdf.ln(2)
        sec_num_curves = str(int(sec_num[:-1]) + 1) + "."
    else:
        sec_num_curves = sec_num

    # ── N. Curvas Características ─────────────────────────────────────────
    chunks = _make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        sec(f"Curvas Características{sfx}",
            f"{sec_num_curves[:-1]}." if pg == 0 else "")
        curves_fig = _build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        _embed_fig(pdf, _fig_to_pdf_bytes(curves_fig), width_mm=165)
        caption(", ".join(cl))


# ─────────────────────────────────────────────────────────────────────────────
# ESTILO DASHBOARD TÉCNICO
# ─────────────────────────────────────────────────────────────────────────────

def _generate_dashboard(
    pdf, exp_label: str, mp: MachineParams, res: dict,
    var_keys: list, var_labels: list, t_events: list,
    exp_type: str, energy_tariff: float,
    losses: dict, integrator: dict, broken_bar: dict | None,
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

    # ── Capa Dashboard ────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*BG_DARK)
    pdf.rect(0, 0, 210, 58, style="F")
    pdf.set_xy(20, 12)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "EMS SIMULATOR", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(20, 28)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8,
             "Dashboard Técnico de Simulação — Versão 2",
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
    dash_title("DESEMPENHO", f"Regime Permanente — {exp_type.upper()}")
    n_ss    = float(res.get("n_ss",    0.0))
    Te_ss   = float(res.get("Te_ss",   0.0))
    ias_rms = float(res.get("ias_rms", 0.0))
    eta     = float(res.get("eta",     0.0))
    s_val   = float(res.get("s",       0.0))
    P_in    = float(res.get("P_in",    0.0))
    v_pin, u_pin = _fmt_power(P_in)
    kpi_row([
        ("Velocidade de Regime",         f"{n_ss:.1f}",    "RPM"),
        ("Torque de Regime Tₑ",     f"{Te_ss:.2f}",   "N·m"),
        ("Corrente Eficaz Iₐₛ", f"{ias_rms:.3f}", "A"),
        ("Rendimento η",            f"{eta:.2f}",     "%"),
    ])
    kpi_row([
        ("Escorregamento s",     f"{s_val*100:.3f}",  "%"),
        ("Potência de Entrada",  v_pin,                u_pin),
        ("Número de Polos p",   str(mp.p),             "—"),
        ("Tensão de Linha Vₗ", f"{mp.Vl:.1f}",   "V"),
    ])

    # ── Balanço de Perdas ─────────────────────────────────────────────────
    sec_bar("BALANÇO DE PERDAS")
    loss_fig = _build_losses_bar_fig(losses)
    _embed_fig(pdf, _fig_to_pdf_bytes(loss_fig), width_mm=160)
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

    # ── Integrador Numérico ───────────────────────────────────────────────
    INTEG_MIN = 52
    if (pdf.h - pdf.b_margin) - pdf.get_y() < INTEG_MIN:
        pdf.add_page()
    sec_bar("INTEGRADOR NUMÉRICO (LSODA)")
    ny_ok = integrator["nyquist_ok"]
    status_badge(ny_ok,
                 "Critério de Nyquist: satisfeito (≥ 10 amostras/ciclo)"
                 if ny_ok else
                 "ATENÇÃO: critério de Nyquist não satisfeito — RMS e FFT podem ser imprecisos")
    mini_table([
        ("Passo solicitado (h)",               f"{integrator['h_req']:.6f} s"),
        ("Passo efetivo médio",                 f"{integrator['dt_eff']:.6f} s"),
        ("Amostras por ciclo",                  f"{integrator['samples_per_cycle']:.1f}"),
        ("Total de pontos de saída",            str(integrator["n_steps"])),
        ("Duração total simulada (t[sub]max[/sub])", f"{integrator['tmax']:.3f} s"),
    ], [105, 65])
    pdf.ln(2)

    # ── Diagnóstico — Barra Quebrada ──────────────────────────────────────
    if broken_bar is not None:
        BB_MIN = 58
        if (pdf.h - pdf.b_margin) - pdf.get_y() < BB_MIN:
            pdf.add_page()
        sec_bar("DIAGNÓSTICO — BARRA QUEBRADA (MCSA)")
        sev_ok = broken_bar["alpha"] < 0.2
        status_badge(sev_ok,
                     f"Severidade: {broken_bar['severity_label']} "
                     f"(α = {broken_bar['alpha']:.3f})")
        mini_table([
            ("Frequência lateral inferior (1−2s)f",  f"{broken_bar['f_lo']:.2f} Hz"),
            ("Frequência lateral superior (1+2s)f",        f"{broken_bar['f_hi']:.2f} Hz"),
            ("Amplitude relativa (1−2s)f / fund.",    f"{broken_bar['sb_ratio_lo']:.2f} %"),
            ("Amplitude relativa (1+2s)f / fund.",          f"{broken_bar['sb_ratio_hi']:.2f} %"),
            ("Escorregamento (s)",                          f"{broken_bar['s_val']*100:.3f} %"),
        ], [115, 55])
        pdf.ln(2)

    # ── Correntes de Fase ABC ─────────────────────────────────────────────
    if any(k in res for k in ("ias", "ibs", "ics")):
        ABC_MIN = 78
        if (pdf.h - pdf.b_margin) - pdf.get_y() < ABC_MIN:
            pdf.add_page()
        sec_bar("CORRENTES DE FASE ABC — REGIME PERMANENTE")
        abc_fig = _build_abc_currents_fig(res)
        _embed_fig(pdf, _fig_to_pdf_bytes(abc_fig), width_mm=165)
        pdf.ln(2)

    # ── Parâmetros da Máquina (compacto) + Circuito Equivalente ─────────
    PARAM_MIN = 120
    if (pdf.h - pdf.b_margin) - pdf.get_y() < PARAM_MIN:
        pdf.add_page()
    sec_bar("PARÂMETROS DA MÁQUINA")
    mini_table([
        ("R[sub]s[/sub]",  f"{mp.Rs:.4f} Ω",
         "R[sub]r[/sub]",  f"{mp.Rr:.4f} Ω"),
        ("X[sub]m[/sub]",  f"{mp.Xm:.4f} Ω",
         "X[sub]ls[/sub]", f"{mp.Xls:.4f} Ω"),
        ("X[sub]lr[/sub]", f"{mp.Xlr:.4f} Ω",
         "J",              f"{mp.J:.4f} kg·m²"),
    ], [30, 45, 30, 45])
    pdf.ln(3)
    _embed_fig(pdf, _build_circuit_bytes(mp), width_mm=155)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*TEXT_LGT)
    pdf.cell(0, 5, "  Circuito equivalente monofásico em T do Motor de Indução Trifásico.",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Curvas Características ────────────────────────────────────────────
    chunks = _make_chunks(var_keys, var_labels)
    for pg, (ck, cl) in enumerate(chunks):
        pdf.add_page()
        sfx = f" ({pg+1}/{len(chunks)})" if len(chunks) > 1 else ""
        dash_title(f"CURVAS CARACTERÍSTICAS{sfx}", ", ".join(cl))
        curves_fig = _build_curves_fig(res, ck, cl, t_events, color_offset=pg * 4)
        _embed_fig(pdf, _fig_to_pdf_bytes(curves_fig), width_mm=165)


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE PÚBLICA
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
) -> bytes:
    """Gera relatório PDF V2 e retorna como bytes.

    style: "academico" ou "dashboard"
    Todos os demais parâmetros são equivalentes ao generate_pdf_report() V1.
    """
    if style not in ("academico", "dashboard"):
        raise ValueError(
            f"style deve ser 'academico' ou 'dashboard', recebido: {style!r}"
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
        )
    else:
        _generate_dashboard(
            pdf, exp_label, mp, res,
            var_keys, var_labels, t_events,
            exp_type, energy_tariff,
            losses, integrator, broken_bar,
        )

    return bytes(pdf.output())
