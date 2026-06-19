# -*- coding: utf-8 -*-
"""
facade.py
=========
Public facade for the DC-machine simulator — exports DCMachineParams,
run_simulation_dc, build functions, and the parameter estimators.

Responsibilities:
  - Re-export DCMachineParams from core.dc.machine_model
  - Expose run_simulation_dc from core.dc.solver as the public entry point
  - Expose make_voltage_fn_dc / make_torque_fn_dc from core.dc.sources for
    experiment construction
  - Expose estimate_dc_nameplate / estimate_dc_tests from core.dc.estimator

Relationships:
  Imported by : ui_components.sim_runner_dc, ui_components.sim_config_dc,
                ui_components.sim_results_dc, ui.theory_dc_interactive,
                viz.pdf_dc, scripts.gen_dc_imgs, analysis.compare_dc_ac_dol,
                utils.gen_okoro_comparison, tests.*, core.dc.__init__
  Imports     : core.dc.machine_model, core.dc.solver, core.dc.sources,
                core.dc.estimator

Extending:
  - Add a new DC mode in core.dc.sources and core.dc.solver; expose it via
    run_simulation_dc without breaking the existing public interface.
  - Mirror of core.tim.facade: every consumer should import the DC public API
    from here, not from the submodules directly.
"""

from __future__ import annotations

from core.dc.machine_model import DCMachineParams, _make_rhs_dc, decode_shunt_gen
from core.dc.solver import run_simulation_dc
from core.dc.sources import make_voltage_fn_dc, make_torque_fn_dc
from core.dc.estimator import estimate_dc_nameplate, estimate_dc_tests

__all__ = [
    "DCMachineParams", "_make_rhs_dc", "decode_shunt_gen",
    "run_simulation_dc",
    "make_voltage_fn_dc", "make_torque_fn_dc",
    "estimate_dc_nameplate", "estimate_dc_tests",
]
