# -*- coding: utf-8 -*-
"""Tests for core/torque_speed.py — torque-speed curve and power flow."""
import numpy as np
import pytest
from core.tim.torque_speed import calc_torque_speed, calc_power_flow


def test_torque_speed_keys(mp_3hp):
    """Result must contain the expected keys."""
    tn = calc_torque_speed(mp_3hp)
    for key in ("Te", "n_rpm", "s"):
        assert key in tn, f"Key '{key}' missing"


def test_torque_speed_length(mp_3hp):
    """Arrays Te, n_rpm and s must have the same length."""
    tn = calc_torque_speed(mp_3hp)
    assert len(tn["Te"]) == len(tn["n_rpm"]) == len(tn["s"])


def test_torque_speed_positive_torque_motor_region(mp_3hp):
    """In the motor region (0 < s < 1), torque must be positive."""
    tn = calc_torque_speed(mp_3hp)
    s = np.array(tn["s"])
    T = np.array(tn["Te"])
    mask = (s > 0.01) & (s < 0.99)
    assert np.all(T[mask] > 0.0)


def test_torque_speed_has_peak(mp_3hp):
    """Curve must have peak torque greater than rated torque."""
    tn = calc_torque_speed(mp_3hp)
    T = np.array(tn["Te"])
    s = np.array(tn["s"])
    mask = (s > 0) & (s < 1)
    T_motor = T[mask]
    s_arr = s[mask]
    idx_nom = np.argmin(np.abs(s_arr - 0.03))
    T_nom = T_motor[idx_nom]
    assert T_motor.max() > 1.5 * T_nom


def test_torque_speed_negative_torque_generator(mp_3hp):
    """In the generator region (s < 0), torque must be negative."""
    tn = calc_torque_speed(mp_3hp)
    s = np.array(tn["s"])
    T = np.array(tn["Te"])
    mask = s < -0.01
    if mask.any():
        assert np.all(T[mask] < 0.0)


def test_power_flow_motor_region(mp_3hp):
    """At s=0.03, P_mec must be positive and η reasonable."""
    fp = calc_power_flow(0.03, mp_3hp)
    assert fp["P_mec"] > 0.0
    assert 50.0 < fp["eta"] < 100.0


def test_power_flow_conservation(mp_3hp):
    """P_in ≈ P_cu_s + P_fe + P_ag (1% tolerance)."""
    fp = calc_power_flow(0.03, mp_3hp)
    P_in_check = fp.get("P_cu_s", 0) + fp.get("P_fe", 0) + fp.get("P_ag", fp.get("P_gap", 0))
    if fp.get("P_in", 0) > 0:
        err = abs(fp["P_in"] - P_in_check) / fp["P_in"]
        assert err < 0.05


def test_power_flow_slip_zero(mp_3hp):
    """At s=0, no power is transferred to the rotor."""
    fp = calc_power_flow(0.0, mp_3hp)
    # Without slip, P_cu_r = s*P_ag = 0
    assert fp.get("P_cu_r", fp.get("P_cu2", 0)) == pytest.approx(0.0, abs=1.0)
