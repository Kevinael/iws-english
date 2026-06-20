# -*- coding: utf-8 -*-
"""
dc_solver.py
============
Integrates the DC machine ODEs via LSODA and returns a results dict with keys
compatible with render_results_dc.

Responsibilities:
  - Run time integration via LSODA (scipy)
  - Reconstruct derived quantities (Ea, Pem, η)
  - Format output as a dict compatible with ui.sim_results_dc

Relationships:
  Imported by : ui.sim_runner_dc
  Imports     : core.dc_machine_model

Extending:
  - For DCM steady-state analysis, add a steady-state detection step similar
    to the MIT solver.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

from core.dc.machine_model import DCMachineParams, _make_rhs_dc, decode_shunt_gen
from core.constants import RAD_TO_RPM, DC_STEADY_STATE_CONV_THRESHOLD


def run_simulation_dc(
    params: DCMachineParams,
    tmax: float,
    h: float,
    voltage_fn: Callable[[float], tuple[float, float]],
    torque_fn: Callable[[float], float],
) -> dict:
    """Integra ODEs da MCC e retorna dict de resultados.

    Required keys (compatibility with render_ref_panel):
      t, ia, ifd, wm, Te, Tl, Ea, Vt, n
    """
    exc = params.excitation
    rhs = _make_rhs_dc(params, voltage_fn, torque_fn)

    # Initial conditions
    if exc == "shunt_gen":
        Llf = params.Ll + params.Lf
        Lla = params.Ll + params.La
        Leq = Lla * Llf - params.Ll * params.Ll
        ifd0 = 0.01
        ia0  = 0.1
        x1_0 = (Llf * ifd0 - params.Ll * ia0)
        x2_0 = (Lla * ia0  - params.Ll * ifd0)
        y0 = [x1_0, x2_0, 0.0]
    else:
        y0 = [0.0, 0.0, 0.0]

    t_eval = np.linspace(0.0, tmax, max(2, int(round(tmax / h)) + 1))
    sol = solve_ivp(
        rhs,
        [0.0, tmax],
        y0,
        method="LSODA",
        t_eval=t_eval,
        max_step=1e-4,
        rtol=1e-6,
        atol=1e-8,
    )

    t = sol.t

    if exc == "shunt_gen":
        ia_arr  = np.zeros(len(t))
        ifd_arr = np.zeros(len(t))
        for k in range(len(t)):
            ia_arr[k], ifd_arr[k] = decode_shunt_gen(sol.y[:, k], params)
        wm_arr = sol.y[2]
    else:
        ia_arr  = sol.y[0]
        ifd_arr = sol.y[0] if exc == "series_motor" else sol.y[1]
        wm_arr  = sol.y[2]

    # Vectorized post-processing
    Te_arr = params.kb * ia_arr * ifd_arr
    Ea_arr = params.kb * ifd_arr * wm_arr
    Tl_arr = np.array([torque_fn(ti) for ti in t])
    Va_arr = np.array([voltage_fn(ti)[0] for ti in t])
    n_arr  = wm_arr * RAD_TO_RPM              # RPM

    if exc in ("sep_gen", "shunt_gen"):
        Rla = params.Ra + params.Rl
        Vt_arr = params.Rl * ia_arr
    else:
        Vt_arr = Va_arr - params.Ra * ia_arr   # Vt = Va − Ra·ia

    # Steady state: average of last 10%; convergence check uses DC_STEADY_STATE_CONV_THRESHOLD
    n_ss = int(max(1, len(t) * 0.1))
    wm_ss_mean = float(np.mean(wm_arr[-n_ss:]))
    wm_ss_var  = float(np.std(wm_arr[-n_ss:]))
    converged  = (wm_ss_mean == 0.0) or (wm_ss_var / abs(wm_ss_mean) < DC_STEADY_STATE_CONV_THRESHOLD)

    def ss(arr: np.ndarray) -> float:
        return float(np.mean(arr[-n_ss:]))

    return {
        "t":      t,
        "ia":     ia_arr,
        "ifd":    ifd_arr,
        "wm":     wm_arr,
        "Te":     Te_arr,
        "Tl":     Tl_arr,
        "Ea":     Ea_arr,
        "Vt":     Vt_arr,
        "n":      n_arr,
        # steady-state scalars
        "ia_ss":  ss(ia_arr),
        "ifd_ss": ss(ifd_arr),
        "wm_ss":  ss(wm_arr),
        "n_ss":   ss(n_arr),
        "Te_ss":  ss(Te_arr),
        "Ea_ss":  ss(Ea_arr),
        "Vt_ss":  ss(Vt_arr),
        # metadata
        "excitation": exc,
        "tmax": tmax,
        "success": bool(sol.success),
        "converged": converged,
    }
