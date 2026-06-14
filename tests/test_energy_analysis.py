# -*- coding: utf-8 -*-
"""Testes para core/energy_analysis.py — compute_energy_metrics."""
import numpy as np
import pytest
from core.mit_energy_analysis import compute_energy_metrics


# ── fixtures locais ───────────────────────────────────────────────────────────

def _make_res(n=2000, f=60.0, P_in=2500.0, eta=88.0, ias_rms=10.0):
    """Resultado sintético com forma de onda senoidal pura (sem harmônicas)."""
    t   = np.linspace(0, 2.0, n)
    dt  = t[1] - t[0]
    w   = 2.0 * np.pi * f

    # tensão e corrente em regime permanente — fase arbitrária
    Vqs = np.full(n, np.sqrt(2.0) * 127.0)   # constante no ref. síncrono (aprox.)
    Vds = np.zeros(n)
    iqs = np.full(n, np.sqrt(2.0) * ias_rms)
    ids = np.zeros(n)

    # ias senoidal pura → THD deve ser ≈ 0
    ias = np.sqrt(2.0) * ias_rms * np.sin(w * t)

    ss_start = n // 2   # regime a partir da metade
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


# ── testes de chaves do retorno ───────────────────────────────────────────────

def test_keys_present():
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    expected = {"E_total_kwh", "custo_exp_brl", "horas_op_ano",
                "custo_ano_brl", "eta_ss", "P_in_ss_kw", "thd_pct", "fp"}
    assert expected <= res.keys()


# ── testes de valores físicos ─────────────────────────────────────────────────

def test_energia_positiva():
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


# ── testes de THD e FP ───────────────────────────────────────────────────────

def test_thd_senoidal_pura_baixo():
    """Sinal senoidal puro deve ter THD próximo de zero."""
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    assert res["thd_pct"] < 5.0   # margem generosa por janela finita


def test_fp_entre_zero_e_um():
    res = compute_energy_metrics(_make_res(), tarifa_brl_kwh=0.75)
    assert 0.0 <= res["fp"] <= 1.0


def test_fp_positivo_com_carga():
    res = compute_energy_metrics(_make_res(P_in=2500.0, ias_rms=10.0), tarifa_brl_kwh=0.75)
    assert res["fp"] > 0.0


# ── robustez com janela de regime curta ──────────────────────────────────────

def test_janela_curta_nao_levanta_excecao():
    """Janela de regime < 16 amostras: thd e fp ficam em 0, sem exceção."""
    res = _make_res(n=20)
    res["_ss_start"] = 10   # apenas 10 amostras em regime
    out = compute_energy_metrics(res, tarifa_brl_kwh=0.75)
    assert out["thd_pct"] == 0.0
    assert out["fp"] == 0.0


def test_P_in_zero_custo_zero():
    """Sem potência de entrada, custo anual deve ser zero."""
    res = compute_energy_metrics(_make_res(P_in=0.0), tarifa_brl_kwh=0.75)
    assert res["custo_ano_brl"] == pytest.approx(0.0)
