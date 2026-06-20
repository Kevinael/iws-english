# -*- coding: utf-8 -*-
"""Tests for core/machine_model.py — MachineParams and derived fields."""
import numpy as np
import pytest
from core.tim.machine_model import MachineParams


def test_post_init_wb(mp_3hp):
    """wb must be 2*pi*f."""
    assert abs(mp_3hp.wb - 2.0 * np.pi * 60.0) < 1e-10


def test_post_init_inductances(mp_3hp):
    """Lm = Xm / (2*pi*f_ref), consistent with mode X."""
    expected_Lm = 26.13 / (2.0 * np.pi * 60.0)
    assert abs(mp_3hp.Lm - expected_Lm) < 1e-10


def test_post_init_xls_a(mp_3hp):
    """Xls_a = wb * Lls."""
    expected = mp_3hp.wb * mp_3hp.Lls
    assert abs(mp_3hp.Xls_a - expected) < 1e-10


def test_post_init_xml_parallel(mp_3hp):
    """Xml must be the parallel of Xm_a // Xls_a_eff // Xlr_a."""
    Xm_a  = mp_3hp.wb * mp_3hp.Lm
    expected = 1.0 / (1.0/Xm_a + 1.0/mp_3hp.Xls_a_eff + 1.0/mp_3hp.Xlr_a)
    assert abs(mp_3hp.Xml - expected) < 1e-10


def test_n_sync(mp_3hp):
    """Synchronous speed: 120*f/p = 1800 RPM for 60 Hz, 4 poles."""
    assert abs(mp_3hp.n_sync - 1800.0) < 1e-6


def test_xls_a_eff_no_grid(mp_3hp):
    """Without grid (Lgrid=0), Xls_a_eff == Xls_a."""
    assert abs(mp_3hp.Xls_a_eff - mp_3hp.Xls_a) < 1e-10


def test_xls_a_eff_with_grid():
    """With Lgrid > 0, Xls_a_eff = Xls_a + Lgrid*wb."""
    Lgrid = 0.001
    mp = MachineParams(Lgrid=Lgrid)
    expected = mp.Xls_a + Lgrid * mp.wb
    assert abs(mp.Xls_a_eff - expected) < 1e-10


def test_mode_L():
    """Mode L: Lm, Lls, Llr used directly without division by wb_ref."""
    Lm_val = 0.1
    mp = MachineParams(Xm=Lm_val, Xls=0.005, Xlr=0.005, input_mode="L")
    assert abs(mp.Lm - Lm_val) < 1e-12
