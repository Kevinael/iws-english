# -*- coding: utf-8 -*-
"""Testes de invariantes físicos — conservação de energia, balanço de torques, térmica."""
import numpy as np
import pytest
from core.IWS_PY import run_simulation, build_fns


# ── Balanço de torques em regime permanente ────────────────────────────────

@pytest.mark.parametrize("Tl", [6.0, 12.0, 18.0])
def test_torque_balance_3hp(mp_3hp, Tl):
    """Te_ss = TL + B*wr_ss — erro menor que 2%."""
    config = {"exp_type": "dol", "Tl_final": Tl, "t_carga": 1.5}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    Te_expected = Tl + mp_3hp.B * res["wr_ss"]
    err = abs(res["Te_ss"] - Te_expected) / max(Te_expected, 1.0)
    assert err < 0.02, f"Tl={Tl}: Te_ss={res['Te_ss']:.3f}, esperado={Te_expected:.3f}"


def test_torque_balance_50hp(mp_50hp):
    """50 HP com B=0: Te_ss deve ser exatamente TL (tolerância 1%)."""
    Tl = 197.0
    config = {"exp_type": "dol", "Tl_final": Tl, "t_carga": 2.0}
    vfn, tfn, _ = build_fns(config, mp_50hp)
    res = run_simulation(mp_50hp, tmax=5.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    err = abs(res["Te_ss"] - Tl) / Tl
    assert err < 0.01


# ── Conservação de potência ────────────────────────────────────────────────

def test_power_balance_dol(dol_result, mp_3hp):
    """P_in ≈ P_gap + P_cu_s + P_fe (tolerância 3%)."""
    res = dol_result
    P_in_check = res["P_gap"] + res["P_cu_s"] + res["P_fe"]
    err = abs(res["P_in"] - P_in_check) / max(res["P_in"], 1.0)
    assert err < 0.03


def test_power_gap_decomposition(dol_result):
    """P_gap = P_cu_r / s (tolerância 2%)."""
    res = dol_result
    if abs(res["s"]) > 0.001:
        P_gap_check = res["P_cu_r"] / res["s"]
        err = abs(res["P_gap"] - P_gap_check) / max(abs(res["P_gap"]), 1.0)
        assert err < 0.02


def test_efficiency_bounds(dol_result):
    """Rendimento deve estar entre 0 e 100%."""
    assert 0.0 <= dol_result["eta"] <= 100.0


def test_efficiency_reasonable(dol_result):
    """Motor 3HP em carga nominal deve ter η > 70%."""
    assert dol_result["eta"] > 70.0


# ── Sanidade numérica ──────────────────────────────────────────────────────

def test_no_nan_in_results(dol_result):
    """Nenhuma série temporal deve conter NaN."""
    keys = ["wr", "n", "Te", "ias", "ibs", "ics", "Va", "Temp"]
    for k in keys:
        assert not np.any(np.isnan(dol_result[k])), f"NaN encontrado em '{k}'"


def test_wr_non_negative(dol_result):
    """Velocidade angular mecânica não pode ser negativa em modo motor."""
    assert np.all(dol_result["wr"] >= 0.0)


def test_temp_above_ambient(dol_result, mp_3hp):
    """Temperatura deve ser sempre >= T_amb."""
    assert np.all(dol_result["Temp"] >= mp_3hp.T_amb - 0.01)


def test_wr_monotone_during_startup(dol_result):
    """wr deve ser monotonamente crescente durante a aceleração (antes de t_carga)."""
    res = dol_result
    t = res["t"]
    wr = res["wr"]
    mask = t < 1.4  # antes do degrau de carga em 1.5s
    wr_startup = wr[mask]
    diffs = np.diff(wr_startup)
    # Permite pequenas oscilações (< 0.5 rad/s de retrocesso)
    assert np.all(diffs >= -0.5)


# ── Modelo térmico ─────────────────────────────────────────────────────────

@pytest.mark.xfail(reason="modelo termico desativado em IWS_PY.py:107 (em revisao)", strict=True)
def test_temp_increases_under_load(dol_result, mp_3hp):
    """Temperatura final deve ser maior que T_amb (motor aqueceu)."""
    assert dol_result["Temp"][-1] > mp_3hp.T_amb


def test_temp_converges_direction(mp_3hp):
    """Em simulação longa, temperatura deve se aproximar de T_amb + Rth*P (sentido correto)."""
    config = {"exp_type": "dol", "Tl_final": 12.0, "t_carga": 1.0}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=5.0, h=5e-4, voltage_fn=vfn, torque_fn=tfn)
    # Temperatura ao final deve ser maior do que no início
    T_inicio = res["Temp"][len(res["Temp"])//4]
    T_fim = res["Temp"][-1]
    assert T_fim >= T_inicio


# ── Slip e velocidade ──────────────────────────────────────────────────────

def test_slip_positive_motor(dol_result):
    """Escorregamento deve ser positivo em modo motor."""
    assert dol_result["s"] > 0.0


def test_slip_less_than_one(dol_result):
    """Escorregamento nominal deve ser bem menor que 1."""
    assert dol_result["s"] < 0.15


def test_speed_below_sync(dol_result, mp_3hp):
    """Velocidade de regime deve ser menor que a síncrona."""
    ws_mec = mp_3hp.wb / (mp_3hp.p / 2.0)
    assert dol_result["wr_ss"] < ws_mec


# ── Experimentos ────────────────────────────────────────────────────────────

def test_yd_lower_startup_current(mp_3hp):
    """YD deve ter corrente de pico menor que DOL."""
    config_dol = {"exp_type": "dol",  "Tl_final": 0.0, "t_carga": 99.0}
    config_yd  = {"exp_type": "yd",   "Tl_final": 0.0, "t_carga": 99.0, "t_2": 1.0}
    vfn_d, tfn_d, _ = build_fns(config_dol, mp_3hp)
    vfn_y, tfn_y, _ = build_fns(config_yd,  mp_3hp)
    res_d = run_simulation(mp_3hp, tmax=0.5, h=1e-4, voltage_fn=vfn_d, torque_fn=tfn_d)
    res_y = run_simulation(mp_3hp, tmax=0.5, h=1e-4, voltage_fn=vfn_y, torque_fn=tfn_y)
    assert res_y["ias"].max() < res_d["ias"].max()


def test_shutdown_wr_reaches_zero(mp_3hp):
    """Após desligamento, wr deve chegar a zero."""
    config = {"exp_type": "shutdown", "Tl_final": 12.0, "t_carga": 0.5, "t_cutoff": 1.5}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=5.0, h=1e-4,
                         voltage_fn=vfn, torque_fn=tfn,
                         clamp_wr_at_zero=True, t_cutoff=1.5)
    assert res["wr"][-1] < 0.5  # praticamente zero


def test_voltage_sag_wr_recovers(mp_3hp):
    """Após afundamento de tensão, velocidade deve se recuperar."""
    config = {
        "exp_type": "voltage_sag",
        "Tl_final": 8.0, "t_carga": 0.5,
        "sag_magnitude": 0.7,
        "t_start_sag": 1.5, "t_duration_sag": 0.2,
    }
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    # wr pós-sag deve estar acima de 90% da síncrona
    ws = mp_3hp.wb / (mp_3hp.p / 2.0)
    assert res["wr"][-1] > 0.90 * ws


def test_gerador_negative_slip(mp_3hp):
    """Operação como gerador deve resultar em escorregamento negativo."""
    config = {"exp_type": "gerador", "Tl_mec": 15.0, "t_2": 1.0}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    res = run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
    assert res["s"] < 0.0
