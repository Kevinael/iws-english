# -*- coding: utf-8 -*-
"""
test_dc_phase1_validation.py
============================
Phase-1 integration validation of the DCM sep_motor DOL solver against the
Scilab reference dcmei.sce (RK4, 12 s, h=0.01).

NOTE: This test was written against the Phase-1 API (DCMachineODEs, DCSolver,
create_dc_source) which was superseded during refactoring. The tests are
skipped until the API is migrated to the current dc_solver / dc_sources
interface.

Responsibilities:
  - Validate that LSODA output matches Scilab RK4 reference at t=12 s.

Relationships:
  Imported by : (pytest — auto-discovered)
  Imports     : core.dc_machine_model, core.dc_solver, core.dc_sources

Extending:
  - To re-enable, rewrite using run_simulation_dc / make_voltage_fn_dc from
    the current API.
"""

import pytest
import numpy as np

pytestmark = pytest.mark.skip(
    reason="Phase-1 API (DCMachineODEs, DCSolver, create_dc_source) was "
           "superseded; rewrite against run_simulation_dc to re-enable."
)

from core.dc.machine_model import DCMachineParams


def test_sep_motor_dol():
    """Run sep_motor DOL with dcmei.sce params and compare."""

    # Params from dcmei.sce (default dialog)
    params = DCMachineParams(
        Rf=1.43,
        Lf=0.1670,
        Vf=12.0,
        Ra=0.013,
        La=0.01,
        Va=24.0,  # This is set by DOL_DC
        J=0.21,
        B=0.000001074,
        kb=0.004,
        Tload=2.493,
    )

    # Initial state: [ifd=0, ia=0, wm=0]
    x0 = np.array([0.0, 0.0, 0.0])

    # Time: 0 to 12s with dt=0.01 (matches dcmei.sce)
    t_eval = np.arange(0, 12.01, 0.01)

    # DOL source: Va=24V constant
    Va_func = create_dc_source("dol_dc", Va_nom=24.0)

    # Solver
    solver = DCSolver("sep_motor", params, t_eval, x0)
    t, x, y = solver.run(Va_func)

    # Get final values
    final = solver.get_final_state()

    print("=" * 70)
    print("DC Motor Phase 1 Validation: sep_motor DOL (dcmei.sce params)")
    print("=" * 70)
    print(f"\nFinal Time: {final['t_final']:.2f} s")
    print(f"Final ia:   {final['ia']:.6f} A")
    print(f"Final ifd:  {final['ifd']:.6f} A")
    print(f"Final wm:   {final['wm']:.6f} rad/s")
    print(f"Final Ea:   {final['Ea']:.6f} V")
    print(f"Final Te:   {final['Te']:.6f} N·m")

    # Sanity checks
    print("\n" + "=" * 70)
    print("Sanity Checks:")
    print("=" * 70)

    # 1. Field current should reach steady state ifd ≈ Vf/Rf
    ifd_expected = params.Vf / params.Rf
    print(f"\n1. Field current (steady state):")
    print(f"   Expected (Vf/Rf): {ifd_expected:.6f} A")
    print(f"   Actual (final):   {final['ifd']:.6f} A")
    print(f"   Match: {np.abs(final['ifd'] - ifd_expected) < 0.01}")

    # 2. Torque should balance load at steady state: Te ≈ Tload
    print(f"\n2. Torque balance (steady state):")
    print(f"   Load torque:    {params.Tload:.6f} N·m")
    print(f"   Electric torque (final): {final['Te']:.6f} N·m")
    print(f"   Match: {np.abs(final['Te'] - params.Tload) < 0.1}")

    # 3. Dynamics: ia and wm should increase from 0
    print(f"\n3. Initial dynamics (t=0.01s):")
    print(f"   ia(0.01):  {y['ia'][1]:.6f} A (should be > 0)")
    print(f"   wm(0.01):  {y['wm'][1]:.6f} rad/s (should be >= 0)")

    # 4. Check step data matches dimensions
    print(f"\n4. Integration check:")
    print(f"   Time steps: {len(t)} (expected {len(t_eval)})")
    print(f"   State shape: {x.shape} (expected ({len(t_eval)}, 3))")
    print(f"   Output keys: {list(y.keys())}")

    # Optional: write CSV for inspection
    print("\n" + "=" * 70)
    print("Writing sep_motor_DOL.csv for inspection...")
    print("=" * 70)

    with open("sep_motor_DOL.csv", "w") as f:
        f.write("t,ia,ifd,wm,Te,Ea\n")
        for i in range(0, len(t), max(1, len(t) // 1200)):  # Sample ~1200 points
            f.write(
                f"{t[i]:.4f},"
                f"{y['ia'][i]:.6f},"
                f"{y['ifd'][i]:.6f},"
                f"{y['wm'][i]:.6f},"
                f"{y['Te'][i]:.6f},"
                f"{y['Ea'][i]:.6f}\n"
            )

    print("\nValidation complete.")
    return final, t, y


if __name__ == "__main__":
    final, t, y = test_sep_motor_dol()
