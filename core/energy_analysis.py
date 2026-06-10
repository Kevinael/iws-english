# -*- coding: utf-8 -*-
"""
energy_analysis.py
==================
Computes steady-state energy metrics — consumption, efficiency, cost, THD,
and power factor.

Responsibilities:
  - Extract steady-state quantities from the simulation results dict
  - Compute η, P_in, P_out, THD, power factor, and estimated annual cost

Relationships:
  Imported by : ui_components.sim_results
  Imports     : (numpy only)

Extending:
  - For time-of-use tariff bands, add a tariff-mode parameter to
    compute_energy_metrics.
"""

from __future__ import annotations
import numpy as np


def compute_energy_metrics(res: dict, tarifa_brl_kwh: float) -> dict:
    """Computes consumed energy, average efficiency, operating cost, THD and PF.

    Integrates P_in = (3/2)·(Vqs·iqs + Vds·ids) over the entire simulation interval.
    Efficiency is computed over the steady-state window.
    THD = sqrt(Σ Ak² k≥2) / A1 × 100% via FFT of ias in the steady-state window.
    PF = P_in_ss / S_apparent where S = 3 × Va_rms × ias_rms.

    Returns dict with:
        E_total_kwh   — total energy consumed in the experiment (kWh)
        custo_exp_brl — experiment cost (R$)
        horas_op_ano  — projected annual operating hours
        custo_ano_brl — projected annual operating cost (R$)
        eta_ss        — steady-state efficiency (%)
        P_in_ss_kw    — steady-state input power (kW)
        thd_pct       — THD of ias at steady state (%)
        fp            — Power Factor at steady state (dimensionless)
    """
    t   = np.asarray(res["t"],   dtype=float)
    Vqs = np.asarray(res["Vqs"], dtype=float)
    Vds = np.asarray(res["Vds"], dtype=float)
    iqs = np.asarray(res["iqs"], dtype=float)
    ids = np.asarray(res["ids"], dtype=float)

    # factor 3/2: amplitude-invariant convention (P = (3/2)*(Vqs*iqs + Vds*ids))
    P_in_inst   = (3.0 / 2.0) * (Vqs * iqs + Vds * ids)
    # np.trapezoid integrates numerically; NaN replaced by 0 (step with numerical failure)
    # 3_600_000 = 3.6e6 J/kWh — thousands separator for readability
    E_total_j   = float(np.trapezoid(np.where(np.isfinite(P_in_inst), P_in_inst, 0.0), t))
    E_total_kwh = E_total_j / 3_600_000.0
    custo_exp_brl = E_total_kwh * tarifa_brl_kwh

    ss_start   = int(res.get("_ss_start", 0))
    eta_ss     = float(res.get("eta", 0.0))
    P_in_ss    = float(res.get("P_in", 0.0))
    P_in_ss_kw = P_in_ss / 1000.0

    # annual cost extrapolated from P_in_ss (steady state), not from E_total (transient)
    # represents continuous operation — relevant scenario for sizing
    horas_op_ano  = 8_760.0
    E_ano_kwh     = P_in_ss_kw * horas_op_ano
    custo_ano_brl = E_ano_kwh * tarifa_brl_kwh

    thd_pct = 0.0
    fp      = 0.0
    try:
        ias_ss = np.asarray(res["ias"][ss_start:], dtype=float)
        t_ss   = t[ss_start:]
        # short window (< 16 samples): thd and fp remain neutral (0.0)
        if len(ias_ss) >= 16:
            dt_ss = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
            N     = len(ias_ss)
            spec  = np.abs(np.fft.rfft(ias_ss)) / N
            freqs = np.fft.rfftfreq(N, d=dt_ss)
            f_fund = float(res.get("_f_fund", 60.0)) if "_f_fund" in res else 60.0
            # window [0.5 fe, 1.5 fe]: robust to small period errors in the steady-state window
            mask_fund = (freqs > 0.5 * f_fund) & (freqs < 1.5 * f_fund)
            if mask_fund.any():
                A1        = float(spec[mask_fund].max())
                # harmonics: everything above 1.5 fe (avoids including the fundamental itself)
                mask_harm = freqs > 1.5 * f_fund
                A_harm    = spec[mask_harm]
                if A1 > 0 and len(A_harm) > 0:
                    thd_pct = float(np.sqrt(np.sum(A_harm ** 2)) / A1 * 100.0)

            Vqs_ss  = Vqs[ss_start:]
            Vds_ss  = Vds[ss_start:]
            # |Vdq| = sqrt(Vqs²+Vds²) is the peak amplitude of the phase voltage in the synchronous frame
            Va_pk   = float(np.sqrt(np.mean(Vqs_ss ** 2 + Vds_ss ** 2)))
            Va_rms  = Va_pk / np.sqrt(2.0)
            ias_rms = float(res.get("ias_rms", 0.0))
            S_ap    = 3.0 * Va_rms * ias_rms
            # np.clip ensures physically valid PF even with small numerical errors
            if S_ap > 0 and np.isfinite(P_in_ss):
                fp = float(np.clip(abs(P_in_ss) / S_ap, 0.0, 1.0))
    except Exception:
        # spectral analysis may fail due to short window, NaN or A1=0
        # returns thd=0 and fp=0 — neutral values without alarming the UI
        pass

    return {
        "E_total_kwh":   E_total_kwh,
        "custo_exp_brl": custo_exp_brl,
        "horas_op_ano":  horas_op_ano,
        "custo_ano_brl": custo_ano_brl,
        "eta_ss":        eta_ss,
        "P_in_ss_kw":    P_in_ss_kw,
        "thd_pct":       thd_pct,
        "fp":            fp,
    }
