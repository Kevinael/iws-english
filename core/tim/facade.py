# -*- coding: utf-8 -*-
"""
IWS_PY.py
=========
Public facade for the induction-machine simulator — exports MachineParams,
run_simulation, and build_fns with a backwards-compatible interface.

Responsibilities:
  - Re-export MachineParams from core.machine_model
  - Orchestrate run_simulation by calling the solver and post-processing
  - Expose build_fns from core.sources for experiment construction

Relationships:
  Imported by : ui_components.sim_config, ui_components.sim_runner,
                ui_components.sim_results, viz.pdf_commons, viz.pdf_report_v2,
                scripts.gen_figures, scripts.gen_resultados_web,
                scripts.demo_potencias, analysis.compare_dc_ac_dol,
                tests.conftest, tests.test_physics
  Imports     : core.machine_model, core.solver, core.sources,
                core.transforms, core.thermal

Extending:
  - Add a new simulation mode in core.sources and core.solver; expose it via
    run_simulation without breaking the existing public interface.
"""

from __future__ import annotations
import warnings
import numpy as np

from core.tim.machine_model import MachineParams, _make_rhs
from core.tim.sources import build_fns
from core.transforms import clarke_park_transform
from core.tim.fault import make_broken_bar_rr_fn
from core.tim.solver import (
    _solve, _voltages_vectorized, _reconstruct_currents, _compute_steady_state,
    SS_TOL, MIN_SS_CYCLES, NYQUIST_LIMIT, F_ROTOR_FLOOR,
    RTOL, ATOL, MAX_STEP_FACTOR,
)


def run_simulation(
    mp: MachineParams,
    tmax: float,
    h: float,
    voltage_fn,
    torque_fn,
    ref_code: int = 1,
    deseq_a: float = 0.0,
    deseq_b: float = 0.0,
    deseq_c: float = 0.0,
    falta_fase_a: bool = False,
    falta_fase_b: bool = False,
    falta_fase_c: bool = False,
    t_deseq: float = 0.0,
    df_a: float = 0.0,
    df_b: float = 0.0,
    df_c: float = 0.0,
    clamp_wr_at_zero: bool = False,
    t_cutoff: float | None = None,
    broken_bar_severity: float = 0.0,
    t_broken_bar: float = 0.0,
) -> dict:
    """Integrates the Krause model via solve_ivp and returns the time series.

    Outputs (backwards-compatible):
      arr["wr"]     — mechanical angular velocity (rad/s)
      arr["n"]      — mechanical speed (RPM)
      arr["Te"]     — electromagnetic torque (N.m)
      arr["Temp"]   — motor temperature (degrees C)
      arr["Te_ss"], arr["wr_ss"], arr["s"], arr["eta"], ... — steady state
    """
    if mp.f * h > NYQUIST_LIMIT:
        warnings.warn(
            f"h*f = {mp.f * h:.3f} > {NYQUIST_LIMIT} "
            f"(< {int(1 / NYQUIST_LIMIT)} samples/cycle) "
            "— RMS and steady-state detection may be inaccurate.",
            stacklevel=2,
        )

    t_values     = np.arange(0.0, tmax, h)
    deseq        = (deseq_a, deseq_b, deseq_c, falta_fase_a, falta_fase_b, falta_fase_c,
                    df_a, df_b, df_c)
    deseq_active = (deseq_a != 0.0 or deseq_b != 0.0 or deseq_c != 0.0
                    or falta_fase_a or falta_fase_b or falta_fase_c
                    or df_a != 0.0 or df_b != 0.0 or df_c != 0.0)

    rr_fn     = make_broken_bar_rr_fn(mp.Rr, broken_bar_severity, mp.wb, t_start=t_broken_bar)
    rhs       = _make_rhs(mp, voltage_fn, torque_fn, ref_code, deseq, t_deseq, deseq_active, rr_fn)
    y0        = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, mp.T_amb, 0.0]
    y_history = _solve(rhs, t_values, y0, mp, clamp_wr_at_zero, t_cutoff=t_cutoff)


    PSIqs, PSIds, PSIqr, PSIdr, wr_e, tetar, _unused_temp, _theta_slip_arr = y_history
    tetae = mp.wb * t_values

    Vl_arr = np.fromiter(
        (voltage_fn(tv) for tv in t_values), dtype=float, count=len(t_values)
    )
    Va, Vb, Vc = _voltages_vectorized(t_values, Vl_arr, mp, deseq, t_deseq, deseq_active)
    Vds, Vqs   = clarke_park_transform(Va, Vb, Vc, tetae)
    ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr = _reconstruct_currents(
        PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp
    )

    Te     = (3.0 / 2.0) * (mp.p / 2.0) * (1.0 / mp.wb) * (PSIds * iqs - PSIqs * ids)
    wr_mec = np.maximum(wr_e / (mp.p / 2.0), 0.0)
    n_rpm  = np.maximum(wr_e * 60.0 / (np.pi * mp.p), 0.0)

    # TEMP DISABLED: thermal model under revision — returns constant T_amb
    Temp_arr = np.full(len(t_values), mp.T_amb)

    arr = {
        "t":    t_values,
        "wr":   wr_mec,
        "n":    n_rpm,
        "Te":   Te,
        "ids":  ids,  "iqs": iqs,  "idr": idr, "iqr": iqr,
        "ias":  ias,  "ibs": ibs,  "ics": ics,
        "iar":  iar,  "ibr": ibr,  "icr": icr,
        "Va":   Va,   "Vb":  Vb,   "Vc":  Vc,
        "Vds":  Vds,  "Vqs": Vqs,
        "Temp": Temp_arr,
        "_broken_bar_severity": broken_bar_severity,
        "_t_broken_bar":        t_broken_bar,
    }
    arr.update(_compute_steady_state(arr, mp))
    return arr
