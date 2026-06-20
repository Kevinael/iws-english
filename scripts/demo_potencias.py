# -*- coding: utf-8 -*-
"""
demo_potencias.py
=================
Demonstration script that runs a DOL simulation and prints steady-state
power metrics to stdout.

Responsibilities:
  - Instantiate a reference motor via MachineParams.
  - Run run_simulation with a DOL configuration.
  - Print RMS voltages, currents, and power flow (input, air-gap,
    mechanical, output, losses).

Relationships:
  Imported by : (standalone script — run directly)
  Imports     : core.IWS_PY

Extending:
  - To benchmark a different motor, replace the MachineParams block.
"""

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.tim.facade import MachineParams, run_simulation, build_fns

mp = MachineParams()
config = {"exp_type": "dol", "Tl_final": 80.0, "t_load": 1.5}
vfn, tfn, t_ev = build_fns(config, mp)

print("Running simulation...")
res = run_simulation(mp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
print(f"Done. N = {len(res['t'])} points.\n")

print("=== Steady-state RMS values ===")
print(f"  Va_rms  = {res['Va_rms']:.4f} V")
print(f"  Vb_rms  = {res['Vb_rms']:.4f} V")
print(f"  Vc_rms  = {res['Vc_rms']:.4f} V")
print(f"  ias_rms = {res['ias_rms']:.4f} A  (physical current)")
print(f"  ibs_rms = {res['ibs_rms']:.4f} A")
print(f"  ics_rms = {res['ics_rms']:.4f} A")
print(f"  Te      = {res['Te_ss']:.4f} N.m")
print(f"  wr      = {res['wr_ss']:.4f} rad/s   (mechanical)")
print(f"  n       = {res['n_ss']:.2f} RPM")
print(f"  s       = {res['s']*100:.3f} %")

print()
print("=== Power values ===")
print(f"  P_gap  = {res['P_gap']:.2f} W")
print(f"  P_cu_r = {res['P_cu_r']:.2f} W")
print(f"  P_cu_s = {res['P_cu_s']:.2f} W   (sum of 3 phases)")
print(f"  P_fe   = {res['P_fe']:.2f} W   (core losses)")
print(f"  P_in   = {res['P_in']:.2f} W")
print(f"  P_mec  = {res['P_mec']:.2f} W")
print(f"  P_out  = {res['P_out']:.2f} W")
print(f"  eta    = {res['eta']:.2f} %")
