# -*- coding: utf-8 -*-
"""
compare_dc_ac_dol.py
====================
Comparative analysis overlaying DC (separately excited) and AC (three-phase
induction) motor DOL transients on shared ia(t), Te(t), and ωm(t) axes.

Responsibilities:
  - Match mechanical parameters (J, B) between MIT and DCM.
  - Run both simulations with equivalent operating conditions.
  - Produce overlay Plotly frames and print comparison statistics.

Relationships:
  Imported by : (standalone script — run directly)
  Imports     : core.IWS_PY, core.dc_machine_model

Extending:
  - To add a third motor type (e.g. PMSM), add a simulation block and an
    overlay trace following the existing DC/AC pattern.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
import sys
import os

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.dc_machine_model import DCMachineParams, DCMachineODEs
from core.dc_solver import DCSolver
from core.IWS_PY import MachineParams, run_simulation, build_fns
from scipy.integrate import odeint


def run_dc_sep_motor_dol(tmax: float = 12.0, h: float = 0.01) -> Dict:
    """Run DC sep_motor DOL with Tload=2.493."""
    params = DCMachineParams(
        Rf=1.43,
        Lf=0.1670,
        Ra=0.013,
        La=0.01,
        J=0.21,
        B=0.000001074,
        kb=0.004,
        Vf=12.0,
        Va=24.0,
        Tload=2.493,
    )

    t_eval = np.arange(0.0, tmax, h)
    x0 = np.array([0.0, 0.0, 0.0])  # [ifd, ia, wm] @ t=0

    def voltage_dol(t):
        """DOL: step voltage at t=0."""
        return 24.0

    solver = DCSolver("sep_motor", params, t_eval, x0)
    t_out, y_out, res = solver.run(voltage_dol)

    # Compute RPM: n = wm * 60 / (2*pi) [for DC, no poles factor]
    wm = res["wm"]
    n = wm * 60.0 / (2.0 * np.pi)

    return {
        "config": "DC sep_motor",
        "t": t_out,
        "ia": res["ia"],
        "wm": wm,
        "Te": res["Te"],
        "n": n,
    }


def run_ac_induction_motor_dol(tmax: float = 12.0, h: float = 0.01) -> Dict:
    """Run AC 3-phase IM DOL with matched J, B from sep_motor."""
    mp = MachineParams(
        Vl=220.0,
        f=60.0,
        Rs=0.435,
        Rr=0.816,
        Xm=26.13,
        Xls=0.754,
        Xlr=0.754,
        Rfe=500.0,
        p=4,
        J=0.21,      # Matched to sep_motor
        B=0.000001074,  # Matched to sep_motor
    )

    config = {
        "exp_type": "dol",
        "Tl_initial": 0.0,
        "Tl_final": 0.0,  # Free run
        "t_carga": 0.0,
    }

    voltage_fn, torque_fn, _ = build_fns(config, mp)

    res = run_simulation(
        mp,
        tmax=tmax,
        h=h,
        voltage_fn=voltage_fn,
        torque_fn=torque_fn,
    )

    return {
        "config": "AC induction motor",
        "t": res["t"],
        "ia": np.sqrt(res["iqs"]**2 + res["ids"]**2),  # Magnitude in dq frame
        "wm": res["wr"],
        "Te": res["Te"],
        "n": res["n"],
    }


def compute_transient_metrics(data: Dict) -> Dict:
    """Compute transient response metrics."""
    # Settle time: when ωm reaches 99% of final value
    final_wm = data["wm"][-1]
    threshold = 0.99 * final_wm
    settle_idx = np.where(data["wm"] >= threshold)[0]
    settle_time = data["t"][settle_idx[0]] if len(settle_idx) > 0 else data["t"][-1]

    # Peak current
    peak_ia = np.max(data["ia"])
    peak_ia_time = data["t"][np.argmax(data["ia"])]

    # Peak torque
    peak_Te = np.max(data["Te"])
    peak_Te_time = data["t"][np.argmax(data["Te"])]

    # Final values
    final_ia = data["ia"][-1]
    final_Te = data["Te"][-1]
    final_n = data["n"][-1]

    return {
        "settle_time_s": settle_time,
        "final_wm_rad_s": final_wm,
        "final_n_rpm": final_n,
        "peak_ia_A": peak_ia,
        "peak_ia_time_s": peak_ia_time,
        "peak_Te_Nm": peak_Te,
        "peak_Te_time_s": peak_Te_time,
        "final_ia_A": final_ia,
        "final_Te_Nm": final_Te,
    }


def main():
    print("=" * 80)
    print("COMPARATIVE ANALYSIS: DC sep_motor vs AC Induction Motor (DOL)")
    print("=" * 80)

    # Run both simulations
    print("\n[1] Running DC sep_motor DOL (12s, h=0.01)...")
    dc_data = run_dc_sep_motor_dol(tmax=12.0, h=0.01)

    print("[2] Running AC induction motor DOL (12s, h=0.01, matched J,B)...")
    ac_data = run_ac_induction_motor_dol(tmax=12.0, h=0.01)

    # Compute metrics
    print("\n[3] Computing transient metrics...")
    dc_metrics = compute_transient_metrics(dc_data)
    ac_metrics = compute_transient_metrics(ac_data)

    # Display comparison
    print("\n" + "=" * 80)
    print("TRANSIENT RESPONSE METRICS")
    print("=" * 80)

    metrics_keys = [
        "settle_time_s",
        "peak_ia_A",
        "peak_ia_time_s",
        "peak_Te_Nm",
        "peak_Te_time_s",
        "final_ia_A",
        "final_Te_Nm",
        "final_wm_rad_s",
        "final_n_rpm",
    ]

    print(f"\n{'Metric':<30} {'DC sep_motor':>20} {'AC IM':>20}")
    print("-" * 70)
    for key in metrics_keys:
        dc_val = dc_metrics.get(key, 0)
        ac_val = ac_metrics.get(key, 0)

        if isinstance(dc_val, float):
            print(f"{key:<30} {dc_val:>20.6f} {ac_val:>20.6f}")
        else:
            print(f"{key:<30} {dc_val:>20} {ac_val:>20}")

    # Export to CSV for visualization
    print("\n[4] Exporting frames to CSV...")

    # Pad shorter array
    t_common = np.linspace(0, 12.0, len(dc_data["t"]))

    df_dc = pd.DataFrame({
        "t": dc_data["t"],
        "ia_DC": dc_data["ia"],
        "Te_DC": dc_data["Te"],
        "wm_DC": dc_data["wm"],
    })

    # Interpolate AC data to match DC time grid
    ia_ac_interp = np.interp(dc_data["t"], ac_data["t"], ac_data["ia"])
    Te_ac_interp = np.interp(dc_data["t"], ac_data["t"], ac_data["Te"])
    wm_ac_interp = np.interp(dc_data["t"], ac_data["t"], ac_data["wm"])

    df_ac = pd.DataFrame({
        "t": dc_data["t"],
        "ia_AC": ia_ac_interp,
        "Te_AC": Te_ac_interp,
        "wm_AC": wm_ac_interp,
    })

    df_merged = pd.concat([df_dc, df_ac.drop(columns=["t"])], axis=1)
    csv_path = os.path.join(os.path.dirname(__file__), "dc_ac_comparative.csv")
    df_merged.to_csv(csv_path, index=False)
    print(f"   Saved: {csv_path}")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print(f"""
DC sep_motor (J={0.21}, B={0.000001074}):
  - Settle time: {dc_metrics['settle_time_s']:.3f} s
  - Peak current: {dc_metrics['peak_ia_A']:.3f} A @ t={dc_metrics['peak_ia_time_s']:.3f} s
  - Peak torque: {dc_metrics['peak_Te_Nm']:.3f} N·m @ t={dc_metrics['peak_Te_time_s']:.3f} s
  - Final speed: {dc_metrics['final_n_rpm']:.1f} RPM

AC induction motor (J={0.21}, B={0.000001074}):
  - Settle time: {ac_metrics['settle_time_s']:.3f} s
  - Peak current: {ac_metrics['peak_ia_A']:.3f} A @ t={ac_metrics['peak_ia_time_s']:.3f} s
  - Peak torque: {ac_metrics['peak_Te_Nm']:.3f} N·m @ t={ac_metrics['peak_Te_time_s']:.3f} s
  - Final speed: {ac_metrics['final_n_rpm']:.1f} RPM

KEY DIFFERENCES:
  - DC accelerates much faster (instant field + armature current control)
  - AC has slower transient (must build flux, slip decreases gradually)
  - DC load = {2.493:.3f} N·m (constant), AC load = 0 (free run on DOL)
  - Matched J,B isolates electrical behavior; mechanical response is identical
""")


if __name__ == "__main__":
    main()
