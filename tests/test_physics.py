# -*- coding: utf-8 -*-
"""Physical invariant tests — energy conservation, torque balance, thermal."""
import numpy as np
import pytest
from core.tim.facade import run_simulation, build_fns


# ── Torque balance in steady state ──────────────────────────────────────────

@pytest.mark.parametrize("Tl", [6.0, 12.0, 18.0])
def test_torque_balance_3hp(mp_3hp, Tl):
    """Te_ss = TL + B*wr_ss — error below 2%."""
    config = {"exp_type": "dol", "Tl_final": Tl, "t_load": 1.5}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    Te_expected = Tl + mp_3hp.B * res["wr_ss"]
    err = abs(res["Te_ss"] - Te_expected) / max(Te_expected, 1.0)
    assert err < 0.02, f"Tl={Tl}: Te_ss={res['Te_ss']:.3f}, expected={Te_expected:.3f}"


def test_torque_balance_50hp(mp_50hp):
    """50 HP with B=0: Te_ss must equal TL exactly (1% tolerance)."""
    Tl = 197.0
    config = {"exp_type": "dol", "Tl_final": Tl, "t_load": 2.0}
    vfn, tfn, _ = build_fns(config, mp_50hp)
    res = run_simulation(mp_50hp, tmax=5.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    err = abs(res["Te_ss"] - Tl) / Tl
    assert err < 0.01


# ── Power conservation ──────────────────────────────────────────────────────

def test_power_balance_dol(dol_result, mp_3hp):
    """P_in ≈ P_gap + P_cu_s + P_fe (3% tolerance)."""
    res = dol_result
    P_in_check = res["P_gap"] + res["P_cu_s"] + res["P_fe"]
    err = abs(res["P_in"] - P_in_check) / max(res["P_in"], 1.0)
    assert err < 0.03


def test_power_gap_decomposition(dol_result):
    """P_gap = P_cu_r / s (2% tolerance)."""
    res = dol_result
    if abs(res["s"]) > 0.001:
        P_gap_check = res["P_cu_r"] / res["s"]
        err = abs(res["P_gap"] - P_gap_check) / max(abs(res["P_gap"]), 1.0)
        assert err < 0.02


def test_efficiency_bounds(dol_result):
    """Efficiency must lie between 0 and 100%."""
    assert 0.0 <= dol_result["eta"] <= 100.0


def test_efficiency_reasonable(dol_result):
    """3HP motor at rated load must have η > 70%."""
    assert dol_result["eta"] > 70.0


# ── Numerical sanity ──────────────────────────────────────────────────────────

def test_no_nan_in_results(dol_result):
    """No time series may contain NaN."""
    keys = ["wr", "n", "Te", "ias", "ibs", "ics", "Va"]
    for k in keys:
        assert not np.any(np.isnan(dol_result[k])), f"NaN found in '{k}'"


def test_wr_non_negative(dol_result):
    """Mechanical angular speed cannot be negative in motor mode."""
    assert np.all(dol_result["wr"] >= 0.0)


def test_wr_monotone_during_startup(dol_result):
    """wr must increase monotonically during acceleration (before t_load)."""
    res = dol_result
    t = res["t"]
    wr = res["wr"]
    mask = t < 1.4  # before the load step at 1.5s
    wr_startup = wr[mask]
    diffs = np.diff(wr_startup)
    # Allow small oscillations (< 0.5 rad/s backward)
    assert np.all(diffs >= -0.5)


# ── Slip and speed ──────────────────────────────────────────────────────────

def test_slip_positive_motor(dol_result):
    """Slip must be positive in motor mode."""
    assert dol_result["s"] > 0.0


def test_slip_less_than_one(dol_result):
    """Rated slip must be well below 1."""
    assert dol_result["s"] < 0.15


def test_speed_below_sync(dol_result, mp_3hp):
    """Steady-state speed must be lower than synchronous."""
    ws_mec = mp_3hp.wb / (mp_3hp.p / 2.0)
    assert dol_result["wr_ss"] < ws_mec


# ── Experiments ───────────────────────────────────────────────────────────────

def test_yd_lower_startup_current(mp_3hp):
    """Y-D must have lower peak current than DOL."""
    config_dol = {"exp_type": "dol",  "Tl_final": 0.0, "t_load": 99.0}
    config_yd  = {"exp_type": "yd",   "Tl_final": 0.0, "t_load": 99.0, "t_2": 1.0}
    vfn_d, tfn_d, _ = build_fns(config_dol, mp_3hp)
    vfn_y, tfn_y, _ = build_fns(config_yd,  mp_3hp)
    res_d = run_simulation(mp_3hp, tmax=0.5, h=1e-4, voltage_fn=vfn_d, torque_fn=tfn_d)
    res_y = run_simulation(mp_3hp, tmax=0.5, h=1e-4, voltage_fn=vfn_y, torque_fn=tfn_y)
    assert res_y["ias"].max() < res_d["ias"].max()


def test_shutdown_wr_reaches_zero(mp_3hp):
    """After shutdown, wr must reach zero."""
    config = {"exp_type": "shutdown", "Tl_final": 12.0, "t_load": 0.5, "t_cutoff": 1.5}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=5.0, h=1e-4,
                         voltage_fn=vfn, torque_fn=tfn,
                         clamp_wr_at_zero=True, t_cutoff=1.5)
    assert res["wr"][-1] < 0.5  # practically zero


def test_voltage_sag_wr_recovers(mp_3hp):
    """After a voltage sag, speed must recover."""
    config = {
        "exp_type": "voltage_sag",
        "Tl_final": 8.0, "t_load": 0.5,
        "sag_magnitude": 0.7,
        "t_start_sag": 1.5, "t_duration_sag": 0.2,
    }
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    # post-sag wr must be above 90% of synchronous
    ws = mp_3hp.wb / (mp_3hp.p / 2.0)
    assert res["wr"][-1] > 0.90 * ws


def test_generator_negative_slip(mp_3hp):
    """Operation as generator must result in negative slip."""
    config = {"exp_type": "generator", "Tl_mec": 15.0, "t_2": 1.0}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    assert res["s"] < 0.0
