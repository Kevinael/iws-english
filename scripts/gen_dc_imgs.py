# -*- coding: utf-8 -*-
"""
gen_dc_imgs.py
==============
Generates static PNG images used by ui/theory_dc.py.
Output: docs/bases para simulação/cc/imgs/

Run from project root:
    python scripts/gen_dc_imgs.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = Path(__file__).parent.parent / "docs" / "bases para simulação" / "cc" / "imgs"
OUT.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _save(fig, name: str) -> None:
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {path.name}")


def _circuit_png(excitation: str) -> None:
    from viz.eqcircuit_plotter_dc import _build_circuit_png_dc
    png_bytes = _build_circuit_png_dc(excitation, dark=False)
    dest = OUT / {
        "sep_motor":    "separate_motor.png",
        "shunt_motor":  "shunt_motor.png",
        "series_motor": "serie_motor.png",
        "sep_gen":      "separate_gerador.png",
        "shunt_gen":    "shunt_gerador.png",
    }[excitation]
    dest.write_bytes(png_bytes)
    print(f"  saved {dest.name}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Circuit PNGs (5 types)
# ─────────────────────────────────────────────────────────────────────────────

print("Generating circuit diagrams...")
for exc in ("sep_motor", "shunt_motor", "series_motor", "sep_gen", "shunt_gen"):
    _circuit_png(exc)


# ─────────────────────────────────────────────────────────────────────────────
# 2. wm_x_T.png — T×ωm for sep/shunt/series motor
# ─────────────────────────────────────────────────────────────────────────────

print("Generating wm_x_T.png...")

Va   = 24.0
Ra   = 0.013
Rf   = 1.43
kb   = 0.004
Tload = 2.493

wm = np.linspace(0, Va / (kb * 0.01) * 0.9, 600)

ifd_shunt = Va / Rf
ifd_sep   = (Va * 0.5) / Rf

def Te_lin(ifd, wm_arr):
    ia = (Va - kb * ifd * wm_arr) / Ra
    return np.maximum(kb * ifd * ia, 0)

Raf   = Ra + 0.026
ia_s  = Va / (Raf + kb * wm + 1e-9)
Te_serie = np.maximum(kb * ia_s**2, 0)

fig, ax = plt.subplots(figsize=(7, 4), facecolor="white")
ax.plot(wm, Te_lin(ifd_sep,   wm), color="#2563eb", lw=2, label="Separately Excited")
ax.plot(wm, Te_lin(ifd_shunt, wm), color="#16a34a", lw=2, label="Shunt")
ax.plot(wm, Te_serie,              color="#dc2626", lw=2, label="Series")
ax.axhline(Tload, color="#d97706", lw=1.4, ls="--", label=f"Load ({Tload} N·m)")
ax.set_xlabel("$\\omega_m$ (rad/s)", fontsize=12)
ax.set_ylabel("$T_e$ (N·m)",         fontsize=12)
ax.set_title("T×ωm — DC Machine Excitation Comparison", fontsize=13)
ax.legend(fontsize=10)
ax.set_xlim(0, wm[-1])
ax.set_ylim(0)
ax.grid(True, alpha=0.3)
fig.tight_layout()
_save(fig, "wm_x_T.png")


# ─────────────────────────────────────────────────────────────────────────────
# 3. gerador_comparativo.png — Vt×Ia for sep/shunt generator
# ─────────────────────────────────────────────────────────────────────────────

print("Generating gerador_comparativo.png...")

Ia = np.linspace(0, 30, 300)

# Sep gen: Vt = Ea - Ra*Ia  (Ea fixed by external excitation)
Ea_sep  = 28.0
Vt_sep  = np.maximum(Ea_sep - Ra * Ia, 0)

# Shunt gen: Vt = Ea - Ra*Ia; Ea depends on Vt via field (self-excited)
# simplified: Vt = Va_oc * (1 - Ia/(Isc)), drop-off due to armature reaction
Va_oc  = 26.0
Isc    = 35.0
Vt_shunt = np.maximum(Va_oc * (1 - Ia / Isc) - Ra * Ia * 0.5, 0)

fig, ax = plt.subplots(figsize=(7, 4), facecolor="white")
ax.plot(Ia, Vt_sep,   color="#2563eb", lw=2, label="Separately Excited")
ax.plot(Ia, Vt_shunt, color="#16a34a", lw=2, label="Shunt (self-excited)")
ax.set_xlabel("$I_a$ (A)",  fontsize=12)
ax.set_ylabel("$V_t$ (V)",  fontsize=12)
ax.set_title("Vt×Ia — DC Generator Comparison", fontsize=13)
ax.legend(fontsize=10)
ax.set_xlim(0, 30)
ax.set_ylim(0)
ax.grid(True, alpha=0.3)
fig.tight_layout()
_save(fig, "gerador_comparativo.png")


# ─────────────────────────────────────────────────────────────────────────────
# 4. curva_magnetizacao_simples_pb.png — magnetization curve (B&W)
# ─────────────────────────────────────────────────────────────────────────────

print("Generating curva_magnetizacao_simples_pb.png...")

If = np.linspace(0, 3.0, 300)
# Simplified saturation: Ea = Ea_sat * (1 - exp(-If/If0))
Ea_sat = 30.0
If0    = 0.6
Ea_mag = Ea_sat * (1 - np.exp(-If / If0))

# Air-gap line (linear part extrapolated)
slope  = (Ea_sat / If0)
Ea_ag  = slope * If

fig, ax = plt.subplots(figsize=(6, 4), facecolor="white")
ax.plot(If, Ea_mag, color="black", lw=2.2, label="Magnetization curve")
ax.plot(If, Ea_ag,  color="black", lw=1.2, ls="--", label="Air-gap line")
ax.set_xlabel("$I_f$ (A)",    fontsize=12)
ax.set_ylabel("$E_a$ (V)",    fontsize=12)
ax.set_title("DC Machine Magnetization Curve", fontsize=13)
ax.legend(fontsize=10)
ax.set_xlim(0, 3.0)
ax.set_ylim(0)
ax.grid(True, alpha=0.3)
fig.tight_layout()
_save(fig, "curva_magnetizacao_simples_pb.png")


print("Done. All images saved to:", OUT)
