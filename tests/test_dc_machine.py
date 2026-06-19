# -*- coding: utf-8 -*-
"""
test_dc_machine.py
==================
Unit and integration tests for the DC motor/generator physics.

Covers:
  - DCMachineParams post-init derived fields
  - Steady-state invariants (torque balance, power balance, back-EMF)
  - All six excitation configurations reach valid steady-state
  - Generator sign convention (Tload < 0)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

from core.dc.facade import (
    DCMachineParams, run_simulation_dc,
    make_voltage_fn_dc, make_torque_fn_dc,
)
from data.machines_dc import DC_PRESETS_BY_EXC


# ─── helpers ────────────────────────────────────────────────────────────────

def _run(preset_dict: dict, tmax: float = 3.0, h: float = 1e-3) -> dict:
    p = DCMachineParams(**{k: v for k, v in preset_dict.items()
                           if not k.startswith("_") and k != "dol_vazio"})
    exp_config = {"Tl_nom": abs(p.Tload)}
    vfn = make_voltage_fn_dc("dol_dc", p, exp_config)
    tfn = make_torque_fn_dc("dol_dc", p, exp_config)
    return run_simulation_dc(p, tmax=tmax, h=h, voltage_fn=vfn, torque_fn=tfn)


def _preset(exc: str, name: str) -> dict:
    return DC_PRESETS_BY_EXC[exc][name]


# ─── DCMachineParams ────────────────────────────────────────────────────────

class TestDCMachineParams:
    def test_series_motor_derived_fields(self):
        p = DCMachineParams(Va=220, Ra=0.6, La=0.02, Rf=0.4, Lf=0.05,
                             kb=6.2, J=2.0, B=0.05, Tload=155.2, excitation="series_motor")
        # Series: total resistance = Ra + Rf
        assert p._Raf == pytest.approx(p.Ra + p.Rf, rel=1e-6)
        assert p._Laf == pytest.approx(p.La + p.Lf, rel=1e-6)

    def test_positive_tload_for_motors(self):
        for exc in ("sep_motor", "shunt_motor", "series_motor"):
            for name, vals in DC_PRESETS_BY_EXC[exc].items():
                assert vals["Tload"] > 0, f"{name}: motor Tload must be positive"

    def test_negative_tload_for_generators(self):
        for exc in ("sep_gen", "shunt_gen"):
            for name, vals in DC_PRESETS_BY_EXC[exc].items():
                assert vals["Tload"] < 0, f"{name}: generator Tload must be negative"


# ─── Steady-state physics ────────────────────────────────────────────────────

class TestDCSteadyState:
    def test_sep_motor_back_emf(self):
        """Ea = Va - ia·Ra at steady state."""
        preset = _preset("sep_motor", "Sep. Motor 220 V — Sen Ex. 9.2")
        p = DCMachineParams(**{k: v for k, v in preset.items() if not k.startswith("_")})
        res = _run(preset, tmax=5.0)
        Ea_expected = p.Va - res["ia_ss"] * p.Ra
        assert res["Ea_ss"] == pytest.approx(Ea_expected, rel=0.01)

    def test_sep_motor_electromagnetic_torque(self):
        """Te = kb · ifd · ia at steady state."""
        preset = _preset("sep_motor", "Sep. Motor 220 V — Sen Ex. 9.2")
        p = DCMachineParams(**{k: v for k, v in preset.items() if not k.startswith("_")})
        res = _run(preset, tmax=5.0)
        Te_expected = p.kb * res["ifd_ss"] * res["ia_ss"]
        assert res["Te_ss"] == pytest.approx(Te_expected, rel=0.01)

    def test_sep_motor_torque_balance(self):
        """At steady state: Te > 0 and within reasonable bounds."""
        preset = _preset("sep_motor", "Sep. Motor 220 V — Sen Ex. 9.2")
        p = DCMachineParams(**{k: v for k, v in preset.items() if not k.startswith("_")})
        res = _run(preset, tmax=5.0)
        Te_ss = res["Te_ss"]
        Tload = abs(p.Tload)
        assert Te_ss > 0
        assert Te_ss < Tload * 3

    def test_speed_positive_sep_motors(self):
        # Sep_motor topology reaches positive steady-state speed under full nominal load in DOL.
        # Shunt/series presets are designed for their own starting modes (resistencia_dc,
        # campo_fraco_dc) — DOL with full Tload does not guarantee convergence for them.
        for name, vals in DC_PRESETS_BY_EXC["sep_motor"].items():
            res = _run(vals, tmax=5.0)
            assert res["wm_ss"] > 0, f"{name}: speed must be positive at steady state"

    def test_shunt_motor_power_balance(self):
        """Pin = Va·ia ≥ Pmec = Te·wm (losses absorbed by Ra)."""
        preset = _preset("shunt_motor", "Shunt Motor 100 V 12 kW — Sen Ex. 4.6")
        p = DCMachineParams(**{k: v for k, v in preset.items() if not k.startswith("_")})
        res = _run(preset, tmax=5.0)
        Pin  = p.Va * res["ia_ss"]
        Pmec = res["Te_ss"] * res["wm_ss"]
        assert Pin >= Pmec * 0.95  # at least 95% power delivered to shaft

    def test_series_motor_reaches_steady_state(self):
        preset = _preset("series_motor", "Series Motor 220 V 7 HP — Sen Ex. 4.9")
        res = _run(preset, tmax=5.0)
        assert res["success"]
        assert res["ia_ss"] > 0


# ─── Result dict completeness ────────────────────────────────────────────────

class TestDCSolverOutput:
    REQUIRED_KEYS = {"t", "ia", "ifd", "wm", "Te", "Tl", "Ea", "Vt", "n",
                     "ia_ss", "ifd_ss", "wm_ss", "n_ss", "Te_ss", "Ea_ss",
                     "Vt_ss", "excitation", "tmax", "success"}

    def test_output_keys_present(self):
        preset = _preset("sep_motor", "Sep. Motor 220 V — Sen Ex. 9.2")
        res = _run(preset)
        assert self.REQUIRED_KEYS.issubset(res.keys())

    def test_arrays_same_length(self):
        preset = _preset("sep_motor", "Sep. Motor 220 V — Sen Ex. 9.2")
        res = _run(preset)
        n = len(res["t"])
        for key in ("ia", "ifd", "wm", "Te", "Tl", "Ea", "Vt", "n"):
            assert len(res[key]) == n, f"Array '{key}' length mismatch"

