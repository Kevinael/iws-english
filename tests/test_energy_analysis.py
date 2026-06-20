# -*- coding: utf-8 -*-
"""Tests for core/energy_analysis.py — compute_energy_metrics."""
import numpy as np
import pytest
from core.tim.energy_analysis import compute_energy_metrics


# ── local fixtures ───────────────────────────────────────────────────────────

def _make_res(n=2000, f=60.0, P_in=2500.0, eta=88.0, ias_rms=10.0):
    """Synthetic result with pure sinusoidal waveform (no harmonics)."""
    t   = np.linspace(0, 2.0, n)
    dt  = t[1] - t[0]
    w   = 2.0 * np.pi * f

    # voltage and current at steady state — arbitrary phase
    Vqs = np.full(n, np.sqrt(2.0) * 127.0)   # constant in synchronous ref. (approx.)
    Vds = np.zeros(n)
    iqs = np.full(n, np.sqrt(2.0) * ias_rms)
    ids = np.zeros(n)

    # pure sinusoidal ias → THD must be ≈ 0
    ias = np.sqrt(2.0) * ias_rms * np.sin(w * t)

    ss_start = n // 2   # steady state from the midpoint
    return {
        "t":        t,
        "Vqs":      Vqs,
        "Vds":      Vds,
        "iqs":      iqs,
        "ids":      ids,
        "ias":      ias,
        "_ss_start": ss_start,
        "eta":      eta,
        "P_in":     P_in,
        "ias_rms":  ias_rms,
        "_f_fund":  f,
    }


# ── return key tests ───────────────────────────────────────────────

def test_keys_present():
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    expected = {"E_total_kwh", "custo_exp_brl", "horas_op_ano",
                "custo_ano_brl", "eta_ss", "P_in_ss_kw", "thd_pct", "fp"}
    assert expected <= res.keys()


# ── physical value tests ─────────────────────────────────────────────────

def test_positive_energy():
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    assert res["E_total_kwh"] > 0


def test_custo_proporcional_tarifa():
    r1 = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.50)
    r2 = compute_energy_metrics(_make_res(), tarifa_brl_kwh=1.00)
    assert abs(r2["custo_exp_brl"] / r1["custo_exp_brl"] - 2.0) < 1e-6


def test_horas_op_ano_fixas():
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    assert res["horas_op_ano"] == pytest.approx(8760.0)


def test_custo_ano_proporcional_P_in():
    r1 = compute_energy_metrics(_make_res(P_in=1000.0), tarifa_brl_kwh=1.0)
    r2 = compute_energy_metrics(_make_res(P_in=2000.0), tarifa_brl_kwh=1.0)
    assert abs(r2["custo_ano_brl"] / r1["custo_ano_brl"] - 2.0) < 1e-4


def test_eta_ss_passthrough():
    res = compute_energy_metrics(_make_res(eta=92.5), tarifa_brl_kwh=0.75)
    assert res["eta_ss"] == pytest.approx(92.5)


def test_P_in_ss_kw_conversao():
    res = compute_energy_metrics(_make_res(P_in=3000.0), tarifa_brl_kwh=0.75)
    assert res["P_in_ss_kw"] == pytest.approx(3.0)


# ── THD and PF tests───────────────────────────────────────────────────────

def test_thd_senoidal_pura_baixo():
    """Pure sinusoidal signal must have THD close to zero."""
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    assert res["thd_pct"] < 5.0   # generous margin due to finite window


def test_fp_entre_zero_e_um():
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    assert 0.0 <= res["fp"] <= 1.0


def test_positive_pf_with_load():
    res = compute_energy_metrics(_make_res(P_in=2500.0, ias_rms=10.0), tarifa_brl_kwh=0.75)
    assert res["fp"] > 0.0


# ── robustness with short steady-state window──────────────────────────────────────

def test_janela_curta_nao_levanta_excecao():
    """Steady-state window < 16 samples: thd and fp stay at 0, without exception."""
    res = _make_res(n=20)
    res["_ss_start"] = 10   # only 10 samples at steady state
    out = compute_energy_metrics(res, tarifa_brl_kwh=0.75)
    assert out["thd_pct"] == 0.0
    assert out["fp"] == 0.0


def test_P_in_zero_custo_zero():
    """Without input power, annual cost must be zero."""
    res = compute_energy_metrics(_make_res(P_in=0.0), tarifa_brl_kwh=0.75)
    assert res["custo_ano_brl"] == pytest.approx(0.0)
