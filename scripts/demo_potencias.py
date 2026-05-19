# -*- coding: utf-8 -*-
"""
calc_potencias.py — Imprime indicadores de regime e fluxo de potência.

Reusa run_simulation (que já entrega RMS, médias e potências corretamente
calculadas em janela de regime com inteiro de ciclos).
"""

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.IWS_PY import MachineParams, run_simulation, build_fns

mp = MachineParams()
config = {"exp_type": "dol", "Tl_final": 80.0, "t_carga": 1.5}
vfn, tfn, t_ev = build_fns(config, mp)

print("Rodando simulacao...")
res = run_simulation(mp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
print(f"Concluida. N = {len(res['t'])} pontos.\n")

print("=== Modulos em regime permanente ===")
print(f"  Va_rms  = {res['Va_rms']:.4f} V")
print(f"  Vb_rms  = {res['Vb_rms']:.4f} V")
print(f"  Vc_rms  = {res['Vc_rms']:.4f} V")
print(f"  ias_rms = {res['ias_rms']:.4f} A  (corrente fisica)")
print(f"  ibs_rms = {res['ibs_rms']:.4f} A")
print(f"  ics_rms = {res['ics_rms']:.4f} A")
print(f"  Te      = {res['Te_ss']:.4f} N.m")
print(f"  wr      = {res['wr_ss']:.4f} rad/s   (mecanica)")
print(f"  n       = {res['n_ss']:.2f} RPM")
print(f"  s       = {res['s']*100:.3f} %")

print()
print("=== Potencias ===")
print(f"  P_gap  = {res['P_gap']:.2f} W")
print(f"  P_cu_r = {res['P_cu_r']:.2f} W")
print(f"  P_cu_s = {res['P_cu_s']:.2f} W   (soma das 3 fases)")
print(f"  P_fe   = {res['P_fe']:.2f} W   (perdas no ferro)")
print(f"  P_in   = {res['P_in']:.2f} W")
print(f"  P_mec  = {res['P_mec']:.2f} W")
print(f"  P_out  = {res['P_out']:.2f} W")
print(f"  eta    = {res['eta']:.2f} %")
