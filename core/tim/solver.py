# -*- coding: utf-8 -*-
"""
solver.py
=========
Integrates the induction-machine ODEs via LSODA (scipy), detects steady state,
and reconstructs physical quantities (currents, voltages, powers, temperature).

Responsibilities:
  - Run _solve with step-size control (h ≤ 1/(20f)) via LSODA
  - Detect steady-state onset from torque variation
  - Compute RMS values, powers, and power factor at steady state
  - Post-process the coupled thermal ODE

Relationships:
  Imported by : core.IWS_PY
  Imports     : core.tim.machine_model, core.transforms, core.tim.fault_model

Extending:
  - For a new starting mode, add logic in _solve; for new post-processing
    (e.g. harmonic loss analysis), create a helper and call it after _solve.
"""

from __future__ import annotations
import math
import warnings
import numpy as np
from scipy.integrate import solve_ivp

from core.tim.machine_model import MachineParams
from core.transforms import abc_voltages, clarke_park_transform, _SQRT3_2
from core.tim.power import compute_power_flow
from core.tim.fault_model import abc_voltages_imbalance
from core.constants import (
    SOLVER_SS_TOL as SS_TOL,
    SOLVER_MIN_SS_CYCLES as MIN_SS_CYCLES,
    SOLVER_NYQUIST_LIMIT as NYQUIST_LIMIT,
    SOLVER_F_ROTOR_FLOOR as F_ROTOR_FLOOR,
    SOLVER_RTOL as RTOL,
    SOLVER_ATOL as ATOL,
    SOLVER_MAX_STEP_FACTOR as MAX_STEP_FACTOR,
)


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATOR
# ═══════════════════════════════════════════════════════════════════════════

def _solve(rhs, t_values, y0, mp: MachineParams, clamp_wr_at_zero: bool, t_cutoff=None):
    """Integrates the ODE; supports restart at t_cutoff and wr=0 clamp on shutdown.

    Segmentation: t_cutoff forces integrator restart at the voltage discontinuity
    (shutdown). clamp_wr_at_zero adds a terminal event and a segment with dwr=0.
    See SME/2. Modulos/core/solver.md — section _solve and Code Reading Guide section 3.

    Returns:
        y_history shape (8, N).
    """
    tmax     = float(t_values[-1])
    max_step = 1.0 / (MAX_STEP_FACTOR * mp.f)
    N        = len(t_values)

    def _run(rhs_fn, t_span, y_init, t_eval):
        sol = solve_ivp(rhs_fn, t_span, y_init, t_eval=t_eval,
                        method='LSODA', rtol=RTOL, atol=ATOL, max_step=max_step)
        if not sol.success:
            warnings.warn(f"solve_ivp failed: {sol.message}")
        return sol

    def _fill(y_history, offset, sol):
        # writes directly into pre-allocated buffer; avoids array concatenation
        n = sol.y.shape[1]
        y_history[:, offset:offset + n] = sol.y
        return offset + n

    def _ffill(arr):
        # propagates the last finite value forward — correct for stopped motor
        # vectorized: indices of finite values accumulated per row
        for row in range(arr.shape[0]):
            r = arr[row]
            finite = np.isfinite(r)
            if not finite.any():
                continue
            idx = np.where(finite, np.arange(len(r)), 0)
            np.maximum.accumulate(idx, out=idx)
            arr[row] = r[idx]

    # NaN as sentinel: positions not filled by LSODA will be ffill'd later
    y_history = np.full((7, N), np.nan)

    if not clamp_wr_at_zero:
        if t_cutoff is not None and t_cutoff < tmax:
            mask_a = t_values <= t_cutoff
            mask_b = t_values >  t_cutoff
            t_a    = t_values[mask_a]
            t_b    = t_values[mask_b]
            sol_a  = _run(rhs, [t_values[0], t_cutoff], y0, t_a)
            off    = _fill(y_history, 0, sol_a)
            if t_b.size > 0:
                sol_b = _run(rhs, [t_cutoff, tmax], sol_a.y[:, -1], t_b)
                _fill(y_history, off, sol_b)
        else:
            sol = _run(rhs, [t_values[0], tmax], y0, t_values)
            y_history[:, :sol.y.shape[1]] = sol.y
        _ffill(y_history)
        return y_history

    # shutdown mode: clamp wr=0 after event
    # y[4] = electrical wr; threshold = 1% of synchronous speed
    # direction=-1: detects only downward crossing (avoids spurious trigger at startup)
    _ws        = mp.wb / (mp.p / 2.0)
    _threshold = 0.01 * _ws

    def event_wr_zero(t, y):
        return y[4] - _threshold
    event_wr_zero.terminal  = True
    event_wr_zero.direction = -1

    if t_cutoff is not None and t_cutoff < tmax:
        mask_a = t_values <= t_cutoff
        mask_b = t_values >  t_cutoff
        t_a    = t_values[mask_a]
        t_b    = t_values[mask_b]

        sol_a = _run(rhs, [t_values[0], t_cutoff], y0, t_a)
        off   = _fill(y_history, 0, sol_a)
        y_cut = sol_a.y[:, -1]

        if t_b.size > 0:
            sol_b = solve_ivp(rhs, [t_cutoff, tmax], y_cut, t_eval=t_b,
                              method='LSODA', rtol=RTOL, atol=ATOL,
                              max_step=max_step, events=event_wr_zero)
            n_b = sol_b.y.shape[1]
            y_history[:, off:off + n_b] = sol_b.y

            if sol_b.t_events[0].size > 0 and off + n_b < N:
                t_ev    = float(sol_b.t_events[0][0])
                y_ev    = sol_b.y_events[0][0].copy()
                y_ev[4] = 0.0

                # rhs_clamped: same RHS but forces dwr=0 — wr remains at zero
                # remaining states (fluxes, temperature) continue evolving
                def rhs_clamped(t, y):
                    d    = rhs(t, y)
                    d[4] = 0.0
                    return d

                t_rest = t_values[off + n_b:]
                sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
                n_c    = sol_c.y.shape[1]
                y_history[:, off + n_b:off + n_b + n_c] = sol_c.y
                if off + n_b + n_c < N:
                    # fills the remainder with the last state (motor stopped)
                    y_history[:, off + n_b + n_c:] = sol_c.y[:, -1:]
    else:
        sol_b = solve_ivp(rhs, [t_values[0], tmax], y0, t_eval=t_values,
                          method='LSODA', rtol=RTOL, atol=ATOL,
                          max_step=max_step, events=event_wr_zero)
        n_b = sol_b.y.shape[1]
        y_history[:, :n_b] = sol_b.y

        if sol_b.t_events[0].size > 0 and n_b < N:
            t_ev    = float(sol_b.t_events[0][0])
            y_ev    = sol_b.y_events[0][0].copy()
            y_ev[4] = 0.0

            def rhs_clamped(t, y):
                d    = rhs(t, y)
                d[4] = 0.0
                return d

            t_rest = t_values[n_b:]
            sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
            n_c    = sol_c.y.shape[1]
            y_history[:, n_b:n_b + n_c] = sol_c.y
            if n_b + n_c < N:
                y_history[:, n_b + n_c:] = sol_c.y[:, -1:]

    _ffill(y_history)
    return y_history


# ═══════════════════════════════════════════════════════════════════════════
# POST-PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def _voltages_vectorized(t_arr, Vl_arr, mp: MachineParams, imbalance, t_imbalance, imbalance_active):
    """Reconstructs Va/Vb/Vc for the full t vector (supports switch at t_imbalance)."""
    if not imbalance_active:
        return abc_voltages(t_arr, Vl_arr, mp.f)
    Va_b, Vb_b, Vc_b = abc_voltages(t_arr, Vl_arr, mp.f)
    Va_u, Vb_u, Vc_u = abc_voltages_imbalance(t_arr, Vl_arr, mp.f, *imbalance)
    mask = t_arr >= t_imbalance
    return (np.where(mask, Va_u, Va_b),
            np.where(mask, Vb_u, Vb_b),
            np.where(mask, Vc_u, Vc_b))


def _reconstruct_currents(PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp: MachineParams):
    """Vectorized reconstruction of dq and abc currents (stator and rotor).

    Operates on full arrays [N] — called once after integration.
    Sequence: fluxes -> dq currents -> inverse Park -> inverse Clarke -> abc.
    See SME/2. Modulos/core/solver.md — section _reconstruct_currents.
    """
    # mutual flux: Xml redistributes total flux between stator and rotor
    PSImq = mp.Xml * (PSIqs / mp.Xls_a_eff + PSIqr / mp.Xlr_a)
    PSImd = mp.Xml * (PSIds / mp.Xls_a_eff + PSIdr / mp.Xlr_a)
    # leakage current = (total flux - mutual flux) / leakage reactance
    ids = (PSIds - PSImd) / mp.Xls_a_eff
    iqs = (PSIqs - PSImq) / mp.Xls_a_eff
    idr = (PSIdr - PSImd) / mp.Xlr_a
    iqr = (PSIqr - PSImq) / mp.Xlr_a

    # inverse Park: P^{-1} = P^T (orthogonal matrix) — sign flip on sin
    cos_e, sin_e = np.cos(tetae), np.sin(tetae)
    cos_r, sin_r = np.cos(tetar), np.sin(tetar)
    iafs = ids * cos_e - iqs * sin_e   # stator alpha component (static frame)
    ibts = ids * sin_e + iqs * cos_e   # stator beta component
    iafr = idr * cos_r - iqr * sin_r   # rotor alpha component
    ibtr = idr * sin_r + iqr * cos_r   # rotor beta component

    # amplitude-invariant inverse Clarke: k = sqrt(3/2)
    k    = np.sqrt(3.0 / 2.0)
    sq32 = _SQRT3_2
    ias = k * iafs
    ibs = k * (-0.5 * iafs + sq32 * ibts)
    ics = k * (-0.5 * iafs - sq32 * ibts)
    iar = k * iafr
    ibr = k * (-0.5 * iafr + sq32 * ibtr)
    icr = k * (-0.5 * iafr - sq32 * ibtr)
    return ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr


def _detect_steady_state(t_arr, wr_arr, mp: MachineParams) -> int:
    """Detects the index of steady-state onset.

    Phase 1: finds the last point outside SS_TOL relative to wr_ref.
    Phase 2: aligns the window to a multiple of LCM(electrical_cycle, rotor_cycle)
             eliminating spectral bias in the RMS calculation.
    See SME/2. Modulos/core/solver.md — section _detect_steady_state.
    """
    N = len(t_arr)
    h = float(t_arr[1] - t_arr[0]) if N > 1 else 1e-4
    samples_per_cycle = max(1, int(round(1.0 / (mp.f * h))))
    min_ss            = MIN_SS_CYCLES * samples_per_cycle

    wr_arr = np.where(np.isfinite(wr_arr), wr_arr, 0.0)
    # reference = mean of last min_ss points (assumed in steady state)
    wr_ref = float(np.mean(wr_arr[-min_ss:])) if N >= min_ss else float(np.mean(wr_arr))

    if abs(wr_ref) < 1e-12:
        ss_start = 0
    else:
        rel_dev   = np.abs((wr_arr[:-min_ss] - wr_ref) / wr_ref)
        violators = np.where(rel_dev > SS_TOL)[0]
        # +1 because steady state begins at the point AFTER the last violator
        ss_start  = int(violators[-1]) + 1 if violators.size else 0

    # provisional slip estimate to compute f_rotor
    ss_len_tmp = max(N - ss_start, min_ss)
    wr_med_tmp = float(np.mean(wr_arr[max(0, N - ss_len_tmp):]))
    ws         = mp.wb / (mp.p / 2.0)
    s_tmp      = (ws - wr_med_tmp) / ws if ws != 0 else 0.0

    # F_ROTOR_FLOOR avoids astronomical lcm_samples when s≈0 (no-load operation)
    f_rotor = max(abs(s_tmp) * mp.f, F_ROTOR_FLOOR)
    samples_per_rotor_cycle = max(1, int(round(1.0 / (f_rotor * h))))

    # LCM-aligned window eliminates RMS bias from incomplete periods
    lcm_samples = math.lcm(samples_per_cycle, samples_per_rotor_cycle)
    lcm_samples = min(lcm_samples, N // 2)

    ss_len   = max(N - ss_start, min_ss)
    ss_len   = max(ss_len // lcm_samples, 1) * lcm_samples
    ss_start = max(0, N - ss_len)
    return ss_start


def _compute_steady_state(arr: dict, mp: MachineParams) -> dict:
    """Computes averages, RMS and power balance in the steady-state window.

    Balance: P_gap = Te_med * ws; P_cu_r = s*P_gap; P_mec = (1-s)*P_gap.
    Generator mode (s<0): reversed power flow — see SME/2. Modulos/core/solver.md.
    """
    t_arr  = arr["t"]
    wr_arr = arr["wr"]
    N      = len(t_arr)
    ss_start = _detect_steady_state(t_arr, wr_arr, mp)
    sl       = slice(ss_start, None)

    # replaces NaN with 0 before averages — NaN indicates isolated numerical failure
    def _safe_mean(a):
        return float(np.mean(np.where(np.isfinite(a), a, 0.0)))

    Te_med = _safe_mean(arr["Te"][sl])
    wr_med = _safe_mean(arr["wr"][sl])
    n_med  = _safe_mean(arr["n"][sl])

    ws     = mp.wb / (mp.p / 2.0)
    s      = (ws - wr_med) / ws if ws != 0 else 0.0
    P_gap  = Te_med * ws
    P_cu_r = s * P_gap
    P_mec  = (1.0 - s) * P_gap

    out: dict = {}
    rms_keys = ("ias", "ibs", "ics", "iar", "ibr", "icr",
                "ids", "iqs", "idr", "iqr",
                "Va",  "Vb",  "Vc",  "Vds", "Vqs")
    for k in rms_keys:
        vals = np.where(np.isfinite(arr[k][sl]), arr[k][sl], 0.0)
        out[f"{k}_rms"] = float(np.sqrt(np.mean(vals ** 2)))

    # Power balance via the canonical power layer (ABC formulas — single
    # source of truth shared with viz.pdf_commons).
    out.update({"P_gap": P_gap, "P_cu_r": P_cu_r, "P_mec": P_mec, "s": s})
    pf = compute_power_flow(out, mp)

    ias_pk  = float(np.max(np.abs(arr["ias"])))
    Te_max  = float(np.max(arr["Te"]))
    ias_rms = out.get("ias_rms", 1.0)
    fator_pk = ias_pk / ias_rms if ias_rms > 0 else 0.0

    out.update(pf)
    out.update({
        "n_ss": n_med,  "wr_ss": wr_med,  "Te_ss": Te_med,
        "_ss_start": ss_start,
        "ias_pk": ias_pk, "Te_max": Te_max, "fator_pk": fator_pk,
    })
    return out
