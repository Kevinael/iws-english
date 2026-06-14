# -*- coding: utf-8 -*-
"""
gen_resultados_web.py
=====================
Generates web-ready article figures from a 50 Hz MIT simulation for the
Overleaf project.

Responsibilities:
  - Run simulation with European-system parameters (220 V / 50 Hz).
  - Save matplotlib figures to the configured output directory.

Relationships:
  Imported by : (standalone script — run directly)
  Imports     : core.IWS_PY

Extending:
  - To change motor parameters or output path, edit the configuration block
    at the top of the script.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['text.usetex'] = False
import matplotlib.pyplot as plt
from core.tim.facade import MachineParams, run_simulation
from core.tim.sources import build_fns

from pathlib import Path
OUT = str(Path(__file__).parent.parent / "overleaf" / "imagens" / "resultados_web.png")

mp = MachineParams(
    Vl=220.0, f=50.0, p=4,
    Rs=2.65, Rr=2.85,
    Xm=60.98, Xls=4.43, Xlr=5.69,
    Rfe=800.0, J=0.025, B=0.001,
)

cfg = {
    'exp_type': 'pulso_carga',
    'Tl_base': 0.0,
    'Tl_final': 10.0,
    't_carga': 0.6,
    't_retirada': 0.8,
}
vfn, tfn, _ = build_fns(cfg, mp)
res = run_simulation(mp, tmax=1.2, h=2e-4, voltage_fn=vfn, torque_fn=tfn)

t = res['t']
ias = res['ias']
Te = res['Te']
n = res['wr'] * 60 / (2 * np.pi)

GRAY = '0.2'
fig, axes = plt.subplots(3, 1, figsize=(3.5, 3.2), sharex=True)
fig.subplots_adjust(left=0.22, right=0.97, top=0.97, bottom=0.11, hspace=0.12)

for ax in axes:
    ax.axvline(0.6, color='k', lw=0.7, ls='--', alpha=0.6)
    ax.axvline(0.8, color='k', lw=0.7, ls=':', alpha=0.5)
    ax.set_xlim(0.5, 1.0)
    ax.tick_params(labelsize=6)
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)
    ax.tick_params(width=0.5)
    ax.set_facecolor('white')

win = (t >= 0.5) & (t <= 1.0)
pad = 0.15

axes[0].plot(t, ias, lw=0.55, color=GRAY)
axes[0].set_ylabel('ias (A)', fontsize=7, labelpad=2)
s = ias[win]; axes[0].set_ylim(s.min() - pad*abs(s).max(), s.max() + pad*abs(s).max())

axes[1].plot(t, Te, lw=0.65, color=GRAY)
axes[1].axhline(10.0, color='0.5', lw=0.6, ls=':', alpha=0.8)
axes[1].set_ylabel('Te (N.m)', fontsize=7, labelpad=2)
s = Te[win]; rng = max(s.max()-s.min(), 0.5); axes[1].set_ylim(s.min()-pad*rng, s.max()+pad*rng)

axes[2].plot(t, n, lw=0.65, color=GRAY)
axes[2].set_ylabel('n (rpm)', fontsize=7, labelpad=2)
axes[2].set_xlabel('Time (s)', fontsize=7)
s = n[win]; rng = max(s.max()-s.min(), 1.0); axes[2].set_ylim(s.min()-pad*rng, s.max()+pad*rng)

yl = axes[2].get_ylim()
axes[2].text(0.61, yl[0] + (yl[1] - yl[0]) * 0.88,
             'Pulse (0.6-0.8 s)', fontsize=5.5, color='0.15', va='top')

fig.savefig(OUT, dpi=300, bbox_inches='tight')
plt.close(fig)
print('saved:', OUT)
