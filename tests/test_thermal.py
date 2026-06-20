# -*- coding: utf-8 -*-
"""Tests for core/thermal.py — dTemp_dt and estimate_rth_cth."""
import numpy as np
import pytest
from core.tim.thermal import dTemp_dt, estimate_rth_cth


def test_dTemp_dt_equilibrio():
    """At equilibrium (T = T_amb + Rth*P), dT/dt must be zero."""
    Rth, Cth, T_amb = 1.0, 5000.0, 25.0
    P = 100.0
    T_eq = T_amb + Rth * P
    result = dTemp_dt(T_eq, P, 0.0, Rth, Cth, T_amb)
    assert abs(result) < 1e-10


def test_dTemp_dt_aquecimento():
    """Starting from T_amb, dT/dt must be positive when there are losses."""
    result = dTemp_dt(25.0, 100.0, 0.0, 1.0, 5000.0, 25.0)
    assert result > 0.0


def test_dTemp_dt_resfriamento():
    """Without losses and T > T_amb, motor must cool down (dT/dt < 0)."""
    result = dTemp_dt(80.0, 0.0, 0.0, 1.0, 5000.0, 25.0)
    assert result < 0.0


def test_dTemp_dt_regime_convergencia():
    """Simple Euler integration must converge to T_amb + Rth*P."""
    Rth, Cth, T_amb = 0.5, 10000.0, 25.0
    P_total = 200.0
    T_target = T_amb + Rth * P_total
    T = T_amb
    dt = 1.0
    for _ in range(100_000):
        T += dTemp_dt(T, P_total, 0.0, Rth, Cth, T_amb) * dt
    assert abs(T - T_target) < 0.1


def test_estimate_rth_cth_positive():
    """Estimated Rth and Cth must be positive."""
    Xm_a = 2.0 * np.pi * 60.0 * (26.13 / (2.0 * np.pi * 60.0))
    Rth, Cth = estimate_rth_cth(
        Vl=220, Rs=0.435, Rr=0.816,
        Xls_a=0.754, Xlr_a=0.754, Xm_a=Xm_a,
    )
    assert Rth > 0.0
    assert Cth > 0.0


def test_estimate_rth_cth_delta_T():
    """Resulting steady-state T must be T_amb + 50 K (tolerance 1 K)."""
    import math
    wb = 2.0 * np.pi * 60.0
    Xm_a = wb * (26.13 / wb)
    Rs, Rr = 0.435, 0.816
    Xls_a, Xlr_a = 0.754, 0.754
    Vl = 220.0
    Rth, _ = estimate_rth_cth(Vl=Vl, Rs=Rs, Rr=Rr, Xls_a=Xls_a, Xlr_a=Xlr_a, Xm_a=Xm_a)
    s = 0.03
    Vfase = Vl / math.sqrt(3.0)
    Z_rot = complex(Rr / s, Xlr_a)
    Z_mag = complex(0, Xm_a)
    Z_par = Z_rot * Z_mag / (Z_rot + Z_mag)
    Z_tot = complex(Rs, Xls_a) + Z_par
    Is = Vfase / abs(Z_tot)
    Ir = Is * abs(Z_mag / (Z_rot + Z_mag))
    P_perdas = 3.0 * (Rs * Is**2 + Rr * Ir**2)
    delta_T = Rth * P_perdas
    assert abs(delta_T - 50.0) < 1.0


def test_estimate_rth_cth_maior_motor():
    """Larger motor (2250 HP) must have smaller Rth than smaller motor (3 HP)."""
    wb = 2.0 * np.pi * 60.0
    Rth_3hp, _ = estimate_rth_cth(
        Vl=220, Rs=0.435, Rr=0.816,
        Xls_a=0.754, Xlr_a=0.754, Xm_a=wb * (26.13 / wb),
    )
    Rth_2250hp, _ = estimate_rth_cth(
        Vl=2300, Rs=0.262, Rr=0.187,
        Xls_a=1.206, Xlr_a=1.206, Xm_a=wb * (13.08 / wb),
    )
    assert Rth_2250hp < Rth_3hp
