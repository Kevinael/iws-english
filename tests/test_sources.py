# -*- coding: utf-8 -*-
"""Testes de core/sources.py — fontes de tensão/torque e build_fns."""
import numpy as np
import pytest
from core.mit_sources import (
    voltage_reduced_start, voltage_soft_starter, voltage_sag,
    torque_step, torque_pulse, build_fns,
)


# ── Fontes de tensão ───────────────────────────────────────────────────────

def test_voltage_reduced_before_switch():
    assert voltage_reduced_start(0.5, 220.0, 127.0, 1.0) == 127.0

def test_voltage_reduced_after_switch():
    assert voltage_reduced_start(1.5, 220.0, 127.0, 1.0) == 220.0

def test_voltage_reduced_at_switch():
    assert voltage_reduced_start(1.0, 220.0, 127.0, 1.0) == 220.0


def test_soft_starter_before_ramp():
    assert voltage_soft_starter(0.0, 220.0, 50.0, 0.5, 2.0) == 50.0

def test_soft_starter_during_ramp():
    v = voltage_soft_starter(1.25, 220.0, 50.0, 0.5, 2.0)
    # t=1.25 está no meio da rampa [0.5, 2.0] → 50% do percurso
    expected = 50.0 + (220.0 - 50.0) * (1.25 - 0.5) / (2.0 - 0.5)
    assert abs(v - expected) < 1e-10

def test_soft_starter_after_ramp():
    assert voltage_soft_starter(3.0, 220.0, 50.0, 0.5, 2.0) == 220.0

def test_soft_starter_monotone():
    """Tensão deve ser monotonamente crescente durante a rampa."""
    t_arr = np.linspace(0.5, 2.0, 50)
    v_arr = [voltage_soft_starter(t, 220.0, 50.0, 0.5, 2.0) for t in t_arr]
    diffs = np.diff(v_arr)
    assert np.all(diffs >= 0)


def test_voltage_sag_before():
    assert voltage_sag(0.5, 220.0, 0.7, 1.0, 1.5) == 220.0

def test_voltage_sag_during():
    assert abs(voltage_sag(1.2, 220.0, 0.7, 1.0, 1.5) - 220.0 * 0.7) < 1e-10

def test_voltage_sag_after():
    assert voltage_sag(1.6, 220.0, 0.7, 1.0, 1.5) == 220.0

def test_voltage_sag_at_end():
    """t == t_end deve retornar tensão nominal (intervalo semi-aberto)."""
    assert voltage_sag(1.5, 220.0, 0.7, 1.0, 1.5) == 220.0


# ── Fontes de torque ───────────────────────────────────────────────────────

def test_torque_step_before():
    assert torque_step(0.5, 0.0, 12.0, 1.5) == 0.0

def test_torque_step_after():
    assert torque_step(2.0, 0.0, 12.0, 1.5) == 12.0

def test_torque_pulse_inside():
    assert torque_pulse(1.5, 0.0, 50.0, 1.0, 2.0) == 50.0

def test_torque_pulse_outside():
    assert torque_pulse(0.5, 0.0, 50.0, 1.0, 2.0) == 0.0

def test_torque_pulse_at_end():
    assert torque_pulse(2.0, 0.0, 50.0, 1.0, 2.0) == 0.0


# ── build_fns ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("exp_type,config", [
    ("dol",         {"exp_type": "dol",         "Tl_final": 12.0, "t_carga": 1.5}),
    ("yd",          {"exp_type": "yd",           "Tl_final": 12.0, "t_carga": 2.0, "t_2": 1.0}),
    ("comp",        {"exp_type": "comp",         "Tl_final": 12.0, "t_carga": 2.0, "t_2": 1.0, "voltage_ratio": 0.65}),
    ("soft",        {"exp_type": "soft",         "Tl_final": 12.0, "t_carga": 3.0, "t_2": 0.5, "t_pico": 2.0, "voltage_ratio": 0.3}),
    ("dol_vazio",   {"exp_type": "dol",          "Tl_final": 12.0, "Tl_inicial": 0.0, "t_carga": 1.0}),
    ("pulso_carga", {"exp_type": "pulso_carga",  "Tl_final": 12.0, "t_carga": 1.0, "t_retirada": 2.0}),
    ("gerador",     {"exp_type": "gerador",      "Tl_mec": 10.0,   "t_2": 1.0}),
    ("shutdown",    {"exp_type": "shutdown",     "Tl_final": 12.0, "t_carga": 1.0, "t_cutoff": 2.0}),
    ("voltage_sag", {"exp_type": "voltage_sag",  "Tl_final": 12.0, "t_carga": 0.5,
                     "sag_magnitude": 0.7, "t_start_sag": 1.0, "t_duration_sag": 0.3}),
])
def test_build_fns_returns_callables(exp_type, config, mp_3hp):
    """build_fns deve retornar callables para qualquer exp_type suportado."""
    vfn, tfn, t_ev = build_fns(config, mp_3hp)
    assert callable(vfn)
    assert callable(tfn)
    assert isinstance(t_ev, list)
    # Funções devem retornar float
    assert isinstance(vfn(0.0), (int, float))
    assert isinstance(tfn(0.0), (int, float))


def test_build_fns_unknown_returns_defaults(mp_3hp):
    """exp_type desconhecido deve retornar Vl constante e torque zero."""
    vfn, tfn, _ = build_fns({"exp_type": "nao_existe"}, mp_3hp)
    assert vfn(0.0) == mp_3hp.Vl
    assert tfn(0.0) == 0.0


def test_build_fns_dol_vl_constant(mp_3hp):
    """DOL: tensão deve ser constante igual a Vl."""
    vfn, _, _ = build_fns({"exp_type": "dol", "Tl_final": 12.0, "t_carga": 1.5}, mp_3hp)
    t_arr = [0.0, 0.5, 1.0, 2.0]
    assert all(vfn(t) == mp_3hp.Vl for t in t_arr)


def test_build_fns_yd_voltage_step(mp_3hp):
    """YD: tensão reduzida antes de t_2, nominal depois."""
    config = {"exp_type": "yd", "Tl_final": 12.0, "t_carga": 2.0, "t_2": 1.0}
    vfn, _, _ = build_fns(config, mp_3hp)
    import math
    Vy = mp_3hp.Vl / math.sqrt(3.0)
    assert abs(vfn(0.5) - Vy) < 1e-6
    assert abs(vfn(1.5) - mp_3hp.Vl) < 1e-6
