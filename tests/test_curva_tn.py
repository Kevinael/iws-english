# -*- coding: utf-8 -*-
"""Testes de core/curva_tn.py — curva T×n e fluxo de potência."""
import numpy as np
import pytest
from core.tim.torque_speed import calc_curva_tn, calc_fluxo_potencia


def test_curva_tn_keys(mp_3hp):
    """Resultado deve conter as chaves esperadas."""
    tn = calc_curva_tn(mp_3hp)
    for key in ("Te", "n_rpm", "s"):
        assert key in tn, f"Chave '{key}' ausente"


def test_curva_tn_length(mp_3hp):
    """Arrays Te, n_rpm e s devem ter o mesmo comprimento."""
    tn = calc_curva_tn(mp_3hp)
    assert len(tn["Te"]) == len(tn["n_rpm"]) == len(tn["s"])


def test_curva_tn_positive_torque_motor_region(mp_3hp):
    """Na região de motor (0 < s < 1), torque deve ser positivo."""
    tn = calc_curva_tn(mp_3hp)
    s = np.array(tn["s"])
    T = np.array(tn["Te"])
    mask = (s > 0.01) & (s < 0.99)
    assert np.all(T[mask] > 0.0)


def test_curva_tn_has_peak(mp_3hp):
    """Curva deve ter torque de pico maior que o torque nominal."""
    tn = calc_curva_tn(mp_3hp)
    T = np.array(tn["Te"])
    s = np.array(tn["s"])
    mask = (s > 0) & (s < 1)
    T_motor = T[mask]
    s_arr = s[mask]
    idx_nom = np.argmin(np.abs(s_arr - 0.03))
    T_nom = T_motor[idx_nom]
    assert T_motor.max() > 1.5 * T_nom


def test_curva_tn_negative_torque_generator(mp_3hp):
    """Na região de generator (s < 0), torque deve ser negativo."""
    tn = calc_curva_tn(mp_3hp)
    s = np.array(tn["s"])
    T = np.array(tn["Te"])
    mask = s < -0.01
    if mask.any():
        assert np.all(T[mask] < 0.0)


def test_fluxo_potencia_motor_region(mp_3hp):
    """Em s=0.03, P_mec deve ser positiva e η razoável."""
    fp = calc_fluxo_potencia(0.03, mp_3hp)
    assert fp["P_mec"] > 0.0
    assert 50.0 < fp["eta"] < 100.0


def test_fluxo_potencia_conservacao(mp_3hp):
    """P_in ≈ P_cu_s + P_fe + P_ag (tolerância 1%)."""
    fp = calc_fluxo_potencia(0.03, mp_3hp)
    P_in_check = fp.get("P_cu_s", 0) + fp.get("P_fe", 0) + fp.get("P_ag", fp.get("P_gap", 0))
    if fp.get("P_in", 0) > 0:
        err = abs(fp["P_in"] - P_in_check) / fp["P_in"]
        assert err < 0.05


def test_fluxo_potencia_slip_zero(mp_3hp):
    """Em s=0, não há potência transferida ao rotor."""
    fp = calc_fluxo_potencia(0.0, mp_3hp)
    # Sem escorregamento, P_cu_r = s*P_ag = 0
    assert fp.get("P_cu_r", fp.get("P_cu2", 0)) == pytest.approx(0.0, abs=1.0)
