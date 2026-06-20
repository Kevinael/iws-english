# -*- coding: utf-8 -*-
"""
gen_okoro_comparison.py
=======================
Generates comparison figures between IWS DC machine simulations and
Okoro et al. (2008) reference results for sep, shunt, and series
configurations.

Responsibilities:
  - Run three DC motor simulations with Okoro reference parameters.
  - Plot overlay figures comparing IWS output against published results.
  - Save PNGs to overleaf/imagens/.

Relationships:
  Imported by : (standalone script — run directly)
  Imports     : core.dc_machine_model

Extending:
  - To add a new reference comparison, add a simulation block and figure
    call following the existing per-configuration pattern.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.integrate import solve_ivp

from core.dc.facade import DCMachineParams, _make_rhs_dc

OUT_DIR = pathlib.Path(__file__).parent.parent / "overleaf" / "imagens"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family":    "serif",
    "font.size":      8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize":7,
    "ytick.labelsize":7,
    "legend.fontsize":7,
    "lines.linewidth":1.2,
    "axes.grid":      True,
    "grid.alpha":     0.35,
    "figure.dpi":     300,
})

# ---------------------------------------------------------------------------
# Parametros Okoro Tabela 1
# ---------------------------------------------------------------------------
COMMON = dict(Va=24.0, Ra=0.013, La=0.01, J=0.21, B=1.074e-6, kb=0.004, Tload=2.493)

CONFIGS = {
    "sep":    dict(**COMMON, Vf=12.0, Rf=1.43,  Lf=0.167, excitation="sep_motor"),
    "shunt":  dict(**COMMON,          Rf=1.43,  Lf=0.167, excitation="shunt_motor"),
    "series": dict(**COMMON,          Rf=0.026, Lf=0.167, excitation="series_motor"),
}

TMAX = {"sep": 15.0, "shunt": 15.0, "series": 60.0}
H    = 1e-4

TITLES = {
    "sep":    "Separately Excited DC Motor",
    "shunt":  "Shunt DC Motor",
    "series": "Series Wound DC Motor",
}

# Dados digitalizados das figuras do Okoro
OKORO = {
    "sep": {
        # Fig.7 — tmax=15s
        "t":   [0, 1, 2,    3,   5,   7,  10,  15],
        "ia":  [0, 900, 1300, 900, 400, 200, 130, 100],   # A
        "wm":  [0,  50, 150, 350, 520, 610, 660, 680],    # rad/s
        "Te":  [0,  10,  47,  32,  14,   7,   4,   3],    # N.m
        "ifd": [0, 7.5, 8.2, 8.4, 8.4, 8.4, 8.4, 8.4],   # A
    },
    "shunt": {
        # Fig.8 — tmax=15s
        "t":   [0,  1,    2,    3,    4,   5,   7,  10,  15],
        "ia":  [0, 700, 1000,  -200,  50, 100, 100, 100, 100],  # A
        "wm":  [0,  80,  300,  430,  360, 350, 350, 350, 350],  # rad/s
        "ifd": [0,  10,   17,   17,   17,  17,  17,  17,  17],  # A
    },
    "series": {
        # Fig.9 — tmax=60s
        "t":   [0,  1,   2,   5,  10,  20,  40,  60],
        "ia":  [0, 85,  60,  35,  27,  25,  25,  25],    # A
        "wm":  [0, -30,  30, 130, 190, 220, 230, 230],   # rad/s
    },
}

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def simulate(key, ifd0=0.0):
    cfg = CONFIGS[key]
    mp  = DCMachineParams(**cfg)
    Vf  = cfg.get("Vf", mp.Va)
    rhs = _make_rhs_dc(mp, lambda t: (mp.Va, Vf), lambda t: mp.Tload)

    tmax   = TMAX[key]
    t_eval = np.arange(0.0, tmax, H)
    t_eval = t_eval[t_eval < tmax]
    t_eval = np.append(t_eval, tmax)

    y0 = [0.0, ifd0, 0.0]
    sol = solve_ivp(rhs, [0.0, tmax], y0, method="LSODA",
                    t_eval=t_eval, max_step=1e-3, rtol=1e-6, atol=1e-8)

    t   = sol.t
    ia  = sol.y[0]
    ifd = sol.y[0] if cfg["excitation"] == "series_motor" else sol.y[1]
    wm  = sol.y[2]
    Te  = mp.kb * ia * ifd
    n_ss = int(max(1, len(t) * 0.05))
    print(f"[{key}] ia_ss={np.mean(ia[-n_ss:]):.1f}A  wm_ss={np.mean(wm[-n_ss:]):.1f}rad/s  success={sol.success}")
    return t, ia, ifd, wm, Te

# ---------------------------------------------------------------------------
# Sep motor — Fig.7: ia, ifd, wm, Te
# ---------------------------------------------------------------------------
def plot_sep():
    ifd0 = 12.0 / 1.43   # campo pre-estabelecido
    t, ia, ifd, wm, Te = simulate("sep", ifd0=ifd0)

    fig, axes = plt.subplots(2, 2, figsize=(6.8, 4.5))
    fig.suptitle(TITLES["sep"] + " — DOL Starting", fontsize=8)
    fig.subplots_adjust(hspace=0.45, wspace=0.35)

    ax = axes[0, 0]
    ax.plot(t, ia, "k-")
    ax.set_ylabel(r"$i_a$ (A)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["sep"])

    ax = axes[0, 1]
    ax.plot(t, ifd, "k-")
    ax.set_ylabel(r"$i_{fd}$ (A)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["sep"])

    ax = axes[1, 0]
    ax.plot(t, Te, "k-")
    ax.set_ylabel(r"$T_e$ (N·m)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["sep"])

    ax = axes[1, 1]
    ax.plot(t, wm, "k-")
    ax.set_ylabel(r"$\omega_m$ (rad/s)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["sep"])

    out = OUT_DIR / "resultados_okoro_sep.png"
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Saved -> {out.name}")

# ---------------------------------------------------------------------------
# Shunt motor — Fig.8: ia, ifd, wm
# ---------------------------------------------------------------------------
def plot_shunt():
    ifd0 = 24.0 / 1.43   # Vf=Va=24V
    t, ia, ifd, wm, Te = simulate("shunt", ifd0=ifd0)

    fig, axes = plt.subplots(2, 2, figsize=(6.8, 4.5))
    fig.suptitle(TITLES["shunt"] + " — DOL Starting", fontsize=8)
    fig.subplots_adjust(hspace=0.45, wspace=0.35)

    ax = axes[0, 0]
    ax.plot(t, ia, "k-")
    ax.set_ylabel(r"$i_a$ (A)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["shunt"])

    ax = axes[0, 1]
    ax.plot(t, ifd, "k-")
    ax.set_ylabel(r"$i_{fd}$ (A)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["shunt"])

    ax = axes[1, 0]
    ax.plot(t, Te, "k-")
    ax.set_ylabel(r"$T_e$ (N·m)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["shunt"])

    ax = axes[1, 1]
    ax.plot(t, wm, "k-")
    ax.set_ylabel(r"$\omega_m$ (rad/s)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["shunt"])

    out = OUT_DIR / "resultados_okoro_shunt.png"
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Saved -> {out.name}")

# ---------------------------------------------------------------------------
# Series motor — Fig.9: ia, wm
# ---------------------------------------------------------------------------
def plot_series():
    t, ia, ifd, wm, Te = simulate("series")

    # Curva estatica Te x wm para series
    cfg_s = CONFIGS["series"]
    mp_s  = DCMachineParams(**cfg_s)
    Raf   = mp_s.Ra + mp_s.Rf
    wm_range = np.linspace(130, 240, 300)
    ia_range = mp_s.Va / (Raf + mp_s.kb * wm_range)
    Te_range = mp_s.kb * ia_range ** 2

    fig, axes = plt.subplots(2, 2, figsize=(6.8, 4.5))
    fig.suptitle(TITLES["series"] + " — DOL Starting", fontsize=8)
    fig.subplots_adjust(hspace=0.45, wspace=0.35)

    ax = axes[0, 0]
    ax.plot(t, ia, "k-")
    ax.set_ylabel(r"$i_a$ (A)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["series"])

    ax = axes[0, 1]
    ax.plot(t, Te, "k-")
    ax.set_ylabel(r"$T_e$ (N·m)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["series"])

    ax = axes[1, 0]
    ax.plot(t, wm, "k-")
    ax.set_ylabel(r"$\omega_m$ (rad/s)"); ax.set_xlabel("Time (s)")
    ax.set_xlim(0, TMAX["series"])

    ax = axes[1, 1]
    ax.plot(wm_range, Te_range, "k-")
    ax.set_ylabel(r"$T_e$ (N·m)"); ax.set_xlabel(r"$\omega_m$ (rad/s)")

    out = OUT_DIR / "resultados_okoro_series.png"
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Saved -> {out.name}")

if __name__ == "__main__":
    plot_sep()
    plot_shunt()
    plot_series()
    print("Done.")
