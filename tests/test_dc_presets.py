# -*- coding: utf-8 -*-
"""
test_dc_presets.py
==================
Smoke tests: all DC presets instantiate DCMachineParams without error
and complete a short simulation without crash.

Covers:
  - All 13 presets in DC_PRESETS_BY_EXC
  - DCMachineParams field types are numeric
  - Simulation returns success=True for every preset
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from core.dc_machine_model import DCMachineParams
from core.dc_solver import run_simulation_dc
from core.dc_sources import make_voltage_fn_dc, make_torque_fn_dc
from data.machines_dc import DC_PRESETS_BY_EXC


def _all_presets():
    """Yield (exc_type, name, dict) for all DC presets."""
    for exc, presets in DC_PRESETS_BY_EXC.items():
        for name, vals in presets.items():
            yield exc, name, vals


def _clean(vals: dict) -> dict:
    """Strip UI-only keys before passing to DCMachineParams."""
    return {k: v for k, v in vals.items() if not k.startswith("_") and k != "dol_vazio"}


# ─── Instantiation ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("exc,name,vals", list(_all_presets()),
                          ids=[f"{e}/{n}" for e, n, _ in _all_presets()])
def test_preset_instantiates(exc, name, vals):
    """Every preset must produce a valid DCMachineParams without raising."""
    p = DCMachineParams(**_clean(vals))
    assert p.Va > 0
    assert p.Ra > 0
    assert p.kb > 0
    assert p.J > 0


# ─── Numeric field types ──────────────────────────────────────────────────────

@pytest.mark.parametrize("exc,name,vals", list(_all_presets()),
                          ids=[f"{e}/{n}" for e, n, _ in _all_presets()])
def test_preset_fields_are_numeric(exc, name, vals):
    numeric_keys = ("Va", "Ra", "La", "kb", "J", "B", "Tload")
    for k in numeric_keys:
        if k in vals:
            assert isinstance(vals[k], (int, float)), \
                f"{name}: field '{k}' must be numeric, got {type(vals[k])}"


# ─── Simulation smoke test ────────────────────────────────────────────────────

@pytest.mark.parametrize("exc,name,vals", list(_all_presets()),
                          ids=[f"{e}/{n}" for e, n, _ in _all_presets()])
def test_preset_simulation_completes(exc, name, vals):
    """All presets must simulate 2 s without raising or returning success=False."""
    p = DCMachineParams(**_clean(vals))

    # generators use gerador_dc mode; motors use dol_dc
    mode = "gerador_dc" if "gen" in exc else "dol_dc"
    exp_config = {"Tl_nom": abs(p.Tload)}

    vfn = make_voltage_fn_dc(mode, p, exp_config)
    tfn = make_torque_fn_dc(mode, p, exp_config)

    res = run_simulation_dc(p, tmax=2.0, h=1e-3, voltage_fn=vfn, torque_fn=tfn)

    assert res["success"], f"{name}: simulation returned success=False"
    assert len(res["t"]) > 10, f"{name}: simulation produced too few time points"
