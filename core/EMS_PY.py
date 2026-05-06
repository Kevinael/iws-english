# -*- coding: utf-8 -*-
"""
EMS_PY.py — Fachada publica do simulador de maquinas de inducao (modelo Krause 0dq)

Exporta (interface retrocompativel):
  MachineParams  — core.machine_model
  run_simulation — integra o ODE e retorna dict com series temporais
  build_fns      — core.sources

Modulos internos:
  core.machine_model  — MachineParams, _make_rhs
  core.solver         — _solve, pos-processamento, deteccao de regime
  core.sources        — fontes de tensao/torque, build_fns
  core.transforms     — abc_voltages, clarke_park_transform
  core.thermal        — estimate_rth_cth, dTemp_dt

Documentacao detalhada da arquitetura e decisoes de implementacao:
  SME/2. Modulos/core/EMS_PY.md
  SME/Fluxo de Dados e Execucao.md
  SME/1. Fundamentos/6 - API Publica (run_simulation e build_fns).md
  SME/2. Modulos/Guia de Leitura do Codigo.md
"""

from __future__ import annotations
import warnings
import numpy as np

from core.machine_model import MachineParams, _make_rhs
from core.sources import build_fns
from core.transforms import clarke_park_transform
from core.desequilibrio_falta import make_broken_bar_rr_fn
from core.solver import (
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
    clamp_wr_at_zero: bool = False,
    t_cutoff: float | None = None,
    broken_bar_severity: float = 0.0,
) -> dict:
    """Integra o modelo Krause via solve_ivp e devolve as series temporais.

    Saidas (retrocompativeis):
      arr["wr"]     — velocidade angular mecanica (rad/s)
      arr["n"]      — rotacao mecanica (RPM)
      arr["Te"]     — torque eletromagnetico (N.m)
      arr["Temp"]   — temperatura do motor (graus C)
      arr["Te_ss"], arr["wr_ss"], arr["s"], arr["eta"], ... — regime permanente
    """
    if mp.f * h > NYQUIST_LIMIT:
        warnings.warn(
            f"h*f = {mp.f * h:.3f} > {NYQUIST_LIMIT} "
            f"(< {int(1 / NYQUIST_LIMIT)} amostras/ciclo) "
            "— RMS e deteccao de regime podem ser imprecisos.",
            stacklevel=2,
        )

    t_values     = np.arange(0.0, tmax, h)
    deseq        = (deseq_a, deseq_b, deseq_c, falta_fase_a, falta_fase_b, falta_fase_c)
    deseq_active = (deseq_a != 0.0 or deseq_b != 0.0 or deseq_c != 0.0
                    or falta_fase_a or falta_fase_b or falta_fase_c)

    rr_fn     = make_broken_bar_rr_fn(mp.Rr, broken_bar_severity, mp.wb)
    rhs       = _make_rhs(mp, voltage_fn, torque_fn, ref_code, deseq, t_deseq, deseq_active, rr_fn)
    y0        = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, mp.T_amb, 0.0]
    y_history = _solve(rhs, t_values, y0, mp, clamp_wr_at_zero, t_cutoff=t_cutoff)

    PSIqs, PSIds, PSIqr, PSIdr, wr_e, tetar, Temp_arr, _theta_slip_arr = y_history
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
        "Temp": np.where(np.isfinite(Temp_arr), Temp_arr, mp.T_amb),
        "_broken_bar_severity": broken_bar_severity,
    }
    arr.update(_compute_steady_state(arr, mp))
    return arr
