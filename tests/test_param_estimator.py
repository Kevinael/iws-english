# -*- coding: utf-8 -*-
"""Testes de core/param_estimator.py — estimação por dados de placa."""
import pytest
from core.param_estimator import estimate_params


BASE = dict(Vl=220, f=60, p=4, Pn_kW=2.24, N_nom=1746,
            rend=0.84, fp=0.82, Ip_In=6.0, Tp_Tn=1.5, is_delta=False)


def test_estimate_returns_success():
    res = estimate_params(**BASE)
    assert res.get("success") is True


def test_estimate_Rs_positive():
    res = estimate_params(**BASE)
    assert res["Rs"] > 0.0


def test_estimate_Rr_positive():
    res = estimate_params(**BASE)
    assert res["Rr"] > 0.0


def test_estimate_Xm_positive():
    res = estimate_params(**BASE)
    assert res["Xm"] > 0.0


def test_estimate_Xls_positive():
    res = estimate_params(**BASE)
    assert res["Xls"] > 0.0


def test_estimate_Xlr_positive():
    res = estimate_params(**BASE)
    assert res["Xlr"] > 0.0


def test_estimate_Xm_greater_than_leakage():
    """Xm deve ser maior que as reatâncias de dispersão."""
    res = estimate_params(**BASE)
    assert res["Xm"] > res["Xls"]
    assert res["Xm"] > res["Xlr"]


def test_estimate_nema_b_ratio():
    """Distribuição NEMA B: Xls/Xlr ≈ 0.4/0.6 = 2/3."""
    res = estimate_params(**BASE)
    ratio = res["Xls"] / res["Xlr"]
    assert abs(ratio - 2.0/3.0) < 0.05


def test_estimate_delta_connection():
    """Ligação delta deve retornar sucesso e parâmetros coerentes."""
    params = {**BASE, "is_delta": True}
    res = estimate_params(**params)
    assert res.get("success") is True
    assert res["Rs"] > 0.0


def test_estimate_large_motor():
    """Motor de grande porte (2250 HP) deve convergir."""
    res = estimate_params(
        Vl=2300, f=60, p=4, Pn_kW=1678, N_nom=1786,
        rend=0.965, fp=0.89, Ip_In=5.5, Tp_Tn=1.3, is_delta=False,
    )
    assert res.get("success") is True
    assert res["Rs"] > 0.0
    assert res["Xm"] > res["Xls"]
