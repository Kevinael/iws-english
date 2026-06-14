# -*- coding: utf-8 -*-
"""
gen_figures.py
==============
Generates article figures for the Overleaf project from a specific MIT
simulation (220 V / 60 Hz / DOL with load ramp).

Responsibilities:
  - Run simulation with hardcoded motor parameters.
  - Save matplotlib figures to the configured output directory.

Relationships:
  Imported by : (standalone script — run directly)
  Imports     : core.IWS_PY

Extending:
  - To generate figures for a different motor, edit the MachineParams block
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
OUT = str(Path(__file__).parent.parent / "overleaf" / "imagens")

mp = MachineParams(
    Vl=220.0, f=60.0, p=4,
    Rs=0.435, Rr=0.816, Xm=26.13,
    Xls=0.754, Xlr=0.754,
    Rfe=400.0, J=0.089, B=0.005,
)
cfg = {'exp_type': 'dol', 'Tl_final': 12.0, 'Tl_inicial': 0.0, 't_carga': 0.0}
vfn, tfn, _ = build_fns(cfg, mp)

GRAY = '0.2'

# ── Simulations ──────────────────────────────────────────────────────────────
res_bb = run_simulation(mp, tmax=3.0, h=5e-4, voltage_fn=vfn, torque_fn=tfn,
                        broken_bar_severity=0.7, t_broken_bar=1.5)
res_as = run_simulation(mp, tmax=3.0, h=5e-4, voltage_fn=vfn, torque_fn=tfn,
                        deseq_a=0.20, t_deseq=1.5)
res_fft = run_simulation(mp, tmax=3.0, h=5e-4, voltage_fn=vfn, torque_fn=tfn,
                         broken_bar_severity=0.9, t_broken_bar=0.5,
                         deseq_a=0.30, t_deseq=0.5)

# ── Figure 1: side-by-side 3-row panels (broken bar | phase asym) ─────────
fig, axes = plt.subplots(3, 2, figsize=(3.5, 3.2), sharex=True)
fig.subplots_adjust(left=0.16, right=0.97, top=0.93, bottom=0.11,
                    hspace=0.10, wspace=0.55)

col_titles = ['(a) Broken bar', '(b) Phase asym.']
sims = [res_bb, res_as]
ylabels = ['ias (A)', 'Te (N.m)', 'n (rpm)']

for col, (res, title) in enumerate(zip(sims, col_titles)):
    t = res['t']
    signals = [res['ias'], res['Te'], res['wr'] * 60 / (2 * np.pi)]
    axes[0, col].set_title(title, fontsize=6.5, pad=2)
    for row, (sig, ylabel) in enumerate(zip(signals, ylabels)):
        ax = axes[row, col]
        ax.axvline(1.5, color='k', lw=0.7, ls='--', alpha=0.7)
        ax.axvspan(1.5, 3.0, color='0.88', alpha=1.0, zorder=0)
        ax.plot(t, sig, lw=0.5, color=GRAY)
        ax.tick_params(labelsize=5.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.4)
        ax.tick_params(width=0.4)
        ax.set_facecolor('white')
        if col == 0:
            ax.set_ylabel(ylabel, fontsize=6.5, labelpad=2)
        if row == 1 and col == 0:
            ax.axhline(12.0, color='0.5', lw=0.5, ls=':', alpha=0.8)
    axes[2, col].set_xlabel('Time (s)', fontsize=6.5)

path = os.path.join(OUT, 'faults_dol.png')
fig.savefig(path, dpi=300, bbox_inches='tight')
plt.close(fig)
print('saved:', path)

# ── Figure 2: MCSA spectrum (dBc) ────────────────────────────────────────
t_full = np.asarray(res_fft['t'])
ss_idx = int(np.searchsorted(t_full, 1.0))
y = np.asarray(res_fft['ias'][ss_idx:])
dt = float(t_full[1] - t_full[0])
N = len(y)
yf = np.abs(np.fft.rfft(y)) * 2.0 / N
freq = np.fft.rfftfreq(N, d=dt)
mask = (freq > 0) & (freq <= 400.0)
freq_p = freq[mask]; yf_p = yf[mask]
A1 = float(yf_p[np.searchsorted(freq_p, 55):np.searchsorted(freq_p, 65)].max())
yf_db = 20 * np.log10(np.maximum(yf_p, 1e-6) / A1)

fig, ax = plt.subplots(figsize=(3.5, 2.0))
fig.subplots_adjust(left=0.18, right=0.97, top=0.88, bottom=0.21)
ax.plot(freq_p, yf_db, lw=0.5, color=GRAY)
ax.set_xlabel('Frequency (Hz)', fontsize=7)
ax.set_ylabel('Amplitude (dBc)', fontsize=7, labelpad=2)
ax.set_ylim(-80, 5)
ax.set_xlim(0, 400)
ax.tick_params(labelsize=6)
for spine in ax.spines.values():
    spine.set_linewidth(0.5)
ax.tick_params(width=0.5)
ax.grid(axis='y', lw=0.3, color='0.8', ls=':')
ax.set_title('MCSA -- broken bar + phase asym. (alpha=0.90, dVa=30%)', fontsize=6.0)

for label, hf in [('f1', 60), ('3f1', 180)]:
    lo = np.searchsorted(freq_p, hf - 8)
    hi = np.searchsorted(freq_p, hf + 8)
    if hi > lo:
        pk_idx = lo + int(np.argmax(yf_db[lo:hi]))
        if yf_db[pk_idx] > -65:
            ax.annotate(label,
                        xy=(freq_p[pk_idx], yf_db[pk_idx]),
                        xytext=(freq_p[pk_idx] + 18, yf_db[pk_idx] - 10),
                        fontsize=6, color='0.15',
                        arrowprops=dict(arrowstyle='->', lw=0.5, color='0.3'))

path = os.path.join(OUT, 'fft_broken_bar.png')
fig.savefig(path, dpi=300, bbox_inches='tight')
plt.close(fig)
print('saved:', path)
