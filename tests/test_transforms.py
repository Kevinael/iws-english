# -*- coding: utf-8 -*-
"""Tests for core/transforms.py — Clarke-Park and abc generation."""
import numpy as np
import pytest
from core.transforms import abc_voltages, clarke_park_transform


def test_abc_voltages_amplitude():
    """Amplitude of each phase must be sqrt(2/3) * Vl."""
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 1/f, 1000, endpoint=False)
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    expected_amp = np.sqrt(2.0 / 3.0) * Vl
    assert abs(Va.max() - expected_amp) < 0.01


def test_abc_voltages_balance():
    """Instantaneous sum Va + Vb + Vc must be zero (balanced system)."""
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 1/f, 1000, endpoint=False)
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    assert np.allclose(Va + Vb + Vc, 0.0, atol=1e-10)


def test_abc_voltages_phase_shift():
    """Vb must be phase-shifted 120° from Va (lag)."""
    Vl, f = 220.0, 60.0
    # Peak of Va at t=T/4, peak of Vb at t=T/4 + T/3
    T = 1.0 / f
    t_Va_peak = T / 4.0
    t_Vb_peak = T / 4.0 + T / 3.0
    Va_t, _, _ = abc_voltages(np.array([t_Va_peak]), Vl, f)
    _, Vb_t, _ = abc_voltages(np.array([t_Vb_peak]), Vl, f)
    assert abs(Va_t[0] - Vb_t[0]) < 0.01


def test_abc_voltages_scalar_vs_array():
    """Scalar and vector results must be identical."""
    Vl, f = 380.0, 50.0
    t_arr = np.array([0.0, 0.001, 0.005])
    Va_arr, Vb_arr, Vc_arr = abc_voltages(t_arr, Vl, f)
    for i, t in enumerate(t_arr):
        Va_s, Vb_s, Vc_s = abc_voltages(t, Vl, f)
        assert abs(float(Va_arr[i]) - float(Va_s)) < 1e-12
        assert abs(float(Vb_arr[i]) - float(Vb_s)) < 1e-12


def test_clarke_park_dc_in_sync_frame():
    """In the synchronous reference, Vds must be zero and Vqs constant (DC voltage).

    This confirms that Clarke-Park removes the fundamental oscillatory component.
    """
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 5/f, 50000, endpoint=False)  # 5 cycles
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    tetae = 2.0 * np.pi * f * t
    Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae)
    # Vds must be zero (numerical tolerance)
    assert abs(np.mean(Vds)) < 1e-6
    # Vqs must be constant (standard deviation << mean)
    assert Vqs.std() / abs(Vqs.mean()) < 1e-4


def test_clarke_park_magnitude():
    """dq magnitude must be constant at steady state."""
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 1/f, 500, endpoint=False)
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    tetae = 2.0 * np.pi * f * t
    Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae)
    magnitude = np.sqrt(Vds**2 + Vqs**2)
    # Magnitude must be constant (DC voltage in synchronous reference)
    assert magnitude.std() / magnitude.mean() < 0.001
