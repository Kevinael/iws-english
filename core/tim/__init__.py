from core.tim.facade import MachineParams, run_simulation, build_fns
from core.tim.machine_model import _make_rhs
from core.tim.fault_model import abc_voltages_imbalance, make_broken_bar_rr_fn
from core.tim.param_estimator import estimate_params, estimate_params_ieee_tests
from core.tim.energy_analysis import compute_energy_metrics
from core.tim.harmonic_analysis import build_fig_fft
from core.tim.diagnostics import generate_insights
from core.tim.torque_speed import calc_curva_tn, calc_fluxo_potencia, _extract_params, _torque_array
from core.tim.thermal import dTemp_dt, estimate_rth_cth
from core.tim.sources import build_fns  # re-export

__all__ = [
    "MachineParams", "run_simulation", "build_fns",
    "_make_rhs",
    "abc_voltages_imbalance", "make_broken_bar_rr_fn",
    "estimate_params", "estimate_params_ieee_tests",
    "compute_energy_metrics", "build_fig_fft", "generate_insights",
    "calc_curva_tn", "calc_fluxo_potencia", "_extract_params", "_torque_array",
    "dTemp_dt", "estimate_rth_cth",
]
