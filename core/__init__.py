# Compatibility shims — import from subpackages
from core.tim import (
    MachineParams, run_simulation, build_fns, _make_rhs,
    abc_voltages_deseq, make_broken_bar_rr_fn,
    render_desequilibrio_ui, render_broken_bar_ui,
    estimate_params, estimate_params_ieee_tests,
    compute_energy_metrics, build_fig_fft, generate_insights,
    calc_curva_tn, calc_fluxo_potencia, _extract_params, _torque_array,
    dTemp_dt, estimate_rth_cth,
)
from core.dc import (
    DCMachineParams, _make_rhs_dc, decode_shunt_gen,
    run_simulation_dc,
    make_voltage_fn_dc, make_torque_fn_dc,
    estimate_dc_nameplate, estimate_dc_tests,
)
