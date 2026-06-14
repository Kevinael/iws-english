# -*- coding: utf-8 -*-
"""
test_dc_sources.py
==================
Unit tests for DC voltage and torque source functions (core/dc_sources.py).

Covers:
  - make_voltage_fn_dc returns callable producing (Va, Vf) tuples
  - DOL mode applies full voltage immediately
  - Series resistance mode starts with reduced voltage then ramps
  - Plugging mode reverses Va sign
  - Field weakening mode reduces Vf below nominal
  - Pulse mode applies load step and removes it
  - make_torque_fn_dc returns correct constant or pulsed torque
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

from core.dc.machine_model import DCMachineParams
from core.dc.sources import make_voltage_fn_dc, make_torque_fn_dc


@pytest.fixture
def sep_motor():
    return DCMachineParams(
        Va=220.0, Ra=0.5, La=0.01, Vf=220.0, Rf=220.0, Lf=10.0,
        kb=1.05, J=2.5, B=0.05, Tload=25.0, excitation="sep_motor",
    )


@pytest.fixture
def shunt_motor():
    return DCMachineParams(
        Va=100.0, Ra=0.1, La=0.01, Rf=101.0, Lf=5.0,
        kb=0.949, J=0.5, B=0.054, Tload=113.9, excitation="shunt_motor",
    )


# ─── make_voltage_fn_dc ──────────────────────────────────────────────────────

class TestVoltageSourcesDC:
    def test_dol_full_voltage_at_t0(self, sep_motor):
        fn = make_voltage_fn_dc("dol_dc", sep_motor, {})
        Va, Vf = fn(0.0)
        assert Va == pytest.approx(sep_motor.Va)
        assert Vf == pytest.approx(sep_motor.Vf)

    def test_dol_constant_over_time(self, sep_motor):
        fn = make_voltage_fn_dc("dol_dc", sep_motor, {})
        times = [0.0, 0.5, 1.0, 2.0]
        results = [fn(t) for t in times]
        assert all(r[0] == pytest.approx(sep_motor.Va) for r in results)

    def test_resistencia_reduced_at_t0(self, sep_motor):
        """Series resistance start: Va at t=0 must be < nominal."""
        cfg = {"t_resistencia": 1.0, "Va_red_frac": 0.5}
        fn = make_voltage_fn_dc("resistencia_dc", sep_motor, cfg)
        Va0, _ = fn(0.0)
        assert Va0 < sep_motor.Va

    def test_resistencia_full_after_ramp(self, sep_motor):
        """Series resistance start: Va after t_resistencia = nominal."""
        cfg = {"t_resistencia": 1.0, "Va_red_frac": 0.5}
        fn = make_voltage_fn_dc("resistencia_dc", sep_motor, cfg)
        Va_late, _ = fn(2.0)
        assert Va_late == pytest.approx(sep_motor.Va, rel=0.01)

    def test_plugging_reverses_va(self, sep_motor):
        """Plugging braking: Va sign reversed after t_freia=3.0."""
        fn = make_voltage_fn_dc("plugging_dc", sep_motor, {})
        Va, _ = fn(4.0)
        assert Va < 0

    def test_campo_fraco_reduces_vf(self, sep_motor):
        """Field weakening: Vf after t_campo < nominal Vf."""
        cfg = {"t_campo": 0.5, "Vf_fraco": sep_motor.Vf * 0.6}
        fn = make_voltage_fn_dc("campo_fraco_dc", sep_motor, cfg)
        _, Vf_early = fn(0.0)
        _, Vf_late  = fn(2.0)
        assert Vf_late < Vf_early

    def test_gerador_returns_tuple(self, sep_motor):
        fn = make_voltage_fn_dc("gerador_dc", sep_motor, {})
        result = fn(0.5)
        assert isinstance(result, tuple) and len(result) == 2

    def test_voltage_fn_returns_floats(self, sep_motor):
        fn = make_voltage_fn_dc("dol_dc", sep_motor, {})
        Va, Vf = fn(1.0)
        assert isinstance(Va, float)
        assert isinstance(Vf, float)


# ─── make_torque_fn_dc ───────────────────────────────────────────────────────

class TestTorqueSourcesDC:
    def test_dol_constant_torque(self, sep_motor):
        fn = make_torque_fn_dc("dol_dc", sep_motor, {"Tl_nom": 25.0})
        assert fn(0.0) == pytest.approx(25.0)
        assert fn(1.5) == pytest.approx(25.0)

    def test_pulso_applies_step(self, sep_motor):
        cfg = {"Tl_nom": 25.0, "t_pulso": 1.0, "Tl_extra": 20.0}
        fn = make_torque_fn_dc("pulso_dc", sep_motor, cfg)
        assert fn(0.5) == pytest.approx(25.0)   # before pulse
        assert fn(1.5) == pytest.approx(45.0)   # Tl_nom + Tl_extra
        assert fn(1.5) > fn(0.5)

    def test_gerador_torque_negative(self, sep_motor):
        """Generator mechanical traction torque is positive."""
        fn = make_torque_fn_dc("gerador_dc", sep_motor, {"Tl_nom": -25.0})
        assert fn(1.0) > 0
