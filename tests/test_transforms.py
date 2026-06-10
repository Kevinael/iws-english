# -*- coding: utf-8 -*-
"""Testes de core/transforms.py — Clarke-Park e geração abc."""
import numpy as np
import pytest
from core.transforms import abc_voltages, clarke_park_transform


def test_abc_voltages_amplitude():
    """Amplitude de cada fase deve ser sqrt(2/3) * Vl."""
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 1/f, 1000, endpoint=False)
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    expected_amp = np.sqrt(2.0 / 3.0) * Vl
    assert abs(Va.max() - expected_amp) < 0.01


def test_abc_voltages_balance():
    """Soma instantânea Va + Vb + Vc deve ser zero (sistema equilibrado)."""
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 1/f, 1000, endpoint=False)
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    assert np.allclose(Va + Vb + Vc, 0.0, atol=1e-10)


def test_abc_voltages_phase_shift():
    """Vb deve estar defasado 120° de Va (atraso)."""
    Vl, f = 220.0, 60.0
    # Pico de Va em t=T/4, pico de Vb em t=T/4 + T/3
    T = 1.0 / f
    t_Va_peak = T / 4.0
    t_Vb_peak = T / 4.0 + T / 3.0
    Va_t, _, _ = abc_voltages(np.array([t_Va_peak]), Vl, f)
    _, Vb_t, _ = abc_voltages(np.array([t_Vb_peak]), Vl, f)
    assert abs(Va_t[0] - Vb_t[0]) < 0.01


def test_abc_voltages_scalar_vs_array():
    """Resultado escalar e vetorial devem ser idênticos."""
    Vl, f = 380.0, 50.0
    t_arr = np.array([0.0, 0.001, 0.005])
    Va_arr, Vb_arr, Vc_arr = abc_voltages(t_arr, Vl, f)
    for i, t in enumerate(t_arr):
        Va_s, Vb_s, Vc_s = abc_voltages(t, Vl, f)
        assert abs(float(Va_arr[i]) - float(Va_s)) < 1e-12
        assert abs(float(Vb_arr[i]) - float(Vb_s)) < 1e-12


def test_clarke_park_dc_in_sync_frame():
    """No referencial síncrono, Vds deve ser zero e Vqs constante (tensão DC).

    Isso confirma que Clarke-Park remove a componente oscilatória fundamental.
    """
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 5/f, 50000, endpoint=False)  # 5 ciclos
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    tetae = 2.0 * np.pi * f * t
    Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae)
    # Vds deve ser zero (tolerância numérica)
    assert abs(np.mean(Vds)) < 1e-6
    # Vqs deve ser constante (desvio padrão << média)
    assert Vqs.std() / abs(Vqs.mean()) < 1e-4


def test_clarke_park_magnitude():
    """Magnitude dq deve ser constante em regime estacionário."""
    Vl, f = 220.0, 60.0
    t = np.linspace(0, 1/f, 500, endpoint=False)
    Va, Vb, Vc = abc_voltages(t, Vl, f)
    tetae = 2.0 * np.pi * f * t
    Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae)
    magnitude = np.sqrt(Vds**2 + Vqs**2)
    # Magnitude deve ser constante (tensão DC no referencial síncrono)
    assert magnitude.std() / magnitude.mean() < 0.001
