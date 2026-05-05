# -*- coding: utf-8 -*-
"""Fixtures compartilhadas entre os testes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.machine_model import MachineParams


@pytest.fixture
def mp_3hp():
    """Krause 3 HP — parâmetros de referência do livro."""
    return MachineParams(
        Vl=220, f=60, Rs=0.435, Rr=0.816,
        Xm=26.13, Xls=0.754, Xlr=0.754, Rfe=500,
        p=4, J=0.089, B=0.005,
    )


@pytest.fixture
def mp_50hp():
    """Krause 50 HP."""
    return MachineParams(
        Vl=460, f=60, Rs=0.087, Rr=0.228,
        Xm=13.08, Xls=0.302, Xlr=0.302, Rfe=500,
        p=4, J=1.662, B=0.0,
    )


@pytest.fixture
def mp_2250hp():
    """Krause 2250 HP."""
    return MachineParams(
        Vl=2300, f=60, Rs=0.262, Rr=0.187,
        Xm=13.08, Xls=1.206, Xlr=1.206, Rfe=500,
        p=4, J=63.87, B=0.05,
    )


@pytest.fixture
def dol_result(mp_3hp):
    """Simulação DOL completa do 3HP para reuso entre testes."""
    from core.EMS_PY import run_simulation, build_fns
    config = {"exp_type": "dol", "Tl_final": 12.0, "t_carga": 1.5}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    return run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
