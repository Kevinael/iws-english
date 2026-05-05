# -*- coding: utf-8 -*-
"""Testes de core/machine_model.py — MachineParams e campos derivados."""
import numpy as np
import pytest
from core.machine_model import MachineParams


def test_post_init_wb(mp_3hp):
    """wb deve ser 2*pi*f."""
    assert abs(mp_3hp.wb - 2.0 * np.pi * 60.0) < 1e-10


def test_post_init_inductances(mp_3hp):
    """Lm = Xm / (2*pi*f_ref), consistente com modo X."""
    expected_Lm = 26.13 / (2.0 * np.pi * 60.0)
    assert abs(mp_3hp.Lm - expected_Lm) < 1e-10


def test_post_init_xls_a(mp_3hp):
    """Xls_a = wb * Lls."""
    expected = mp_3hp.wb * mp_3hp.Lls
    assert abs(mp_3hp.Xls_a - expected) < 1e-10


def test_post_init_xml_parallel(mp_3hp):
    """Xml deve ser o paralelo de Xm_a // Xls_a_eff // Xlr_a."""
    Xm_a  = mp_3hp.wb * mp_3hp.Lm
    expected = 1.0 / (1.0/Xm_a + 1.0/mp_3hp.Xls_a_eff + 1.0/mp_3hp.Xlr_a)
    assert abs(mp_3hp.Xml - expected) < 1e-10


def test_n_sync(mp_3hp):
    """Velocidade síncrona: 120*f/p = 1800 RPM para 60 Hz, 4 polos."""
    assert abs(mp_3hp.n_sync - 1800.0) < 1e-6


def test_xls_a_eff_no_grid(mp_3hp):
    """Sem rede (Lgrid=0), Xls_a_eff == Xls_a."""
    assert abs(mp_3hp.Xls_a_eff - mp_3hp.Xls_a) < 1e-10


def test_xls_a_eff_with_grid():
    """Com Lgrid > 0, Xls_a_eff = Xls_a + Lgrid*wb."""
    Lgrid = 0.001
    mp = MachineParams(Lgrid=Lgrid)
    expected = mp.Xls_a + Lgrid * mp.wb
    assert abs(mp.Xls_a_eff - expected) < 1e-10


def test_mode_L():
    """Modo L: Lm, Lls, Llr usados diretamente sem divisão por wb_ref."""
    Lm_val = 0.1
    mp = MachineParams(Xm=Lm_val, Xls=0.005, Xlr=0.005, input_mode="L")
    assert abs(mp.Lm - Lm_val) < 1e-12


def test_rth_auto_positive(mp_3hp):
    """Rth automático deve ser positivo."""
    assert mp_3hp.Rth > 0.0


def test_cth_auto_positive(mp_3hp):
    """Cth automático deve ser positivo."""
    assert mp_3hp.Cth > 0.0


def test_thermal_regime_temperature(mp_3hp):
    """T_regime = T_amb + 50 K por construção do Rth automático (tolerância 5 K)."""
    # Rth foi calibrado para delta_T = 50 K com as perdas do circuito T em s=3%
    # A temperatura de regime exata depende de P_perdas real — tolerância 10 K
    # (a heurística de massa introduz variação)
    import math
    Vfase = mp_3hp.Vl / math.sqrt(3.0)
    s = 0.03
    Xm_a = mp_3hp.wb * mp_3hp.Lm
    Z_rot = complex(mp_3hp.Rr / s, mp_3hp.Xlr_a)
    Z_mag = complex(0, Xm_a)
    Z_par = Z_rot * Z_mag / (Z_rot + Z_mag)
    Z_tot = complex(mp_3hp.Rs, mp_3hp.Xls_a) + Z_par
    Is = Vfase / abs(Z_tot)
    Ir = Is * abs(Z_mag / (Z_rot + Z_mag))
    P_perdas = 3.0 * (mp_3hp.Rs * Is**2 + mp_3hp.Rr * Ir**2)
    T_regime = mp_3hp.T_amb + mp_3hp.Rth * P_perdas
    assert abs(T_regime - (mp_3hp.T_amb + 50.0)) < 1.0


def test_rth_manual_override():
    """Rth manual deve prevalecer sobre o auto."""
    mp = MachineParams(Rth=2.5)
    assert abs(mp.Rth - 2.5) < 1e-10


def test_cth_manual_override():
    """Cth manual deve prevalecer sobre o auto."""
    mp = MachineParams(Cth=50000.0)
    assert abs(mp.Cth - 50000.0) < 1e-10
