# -*- coding: utf-8 -*-
"""
conftest.py
===========
Shared pytest fixtures defining three reference induction machine models
(3 HP, 50 HP, 2250 HP from Krause 1986).

Responsibilities:
  - Provide mp_3hp, mp_50hp, and mp_2250hp fixtures with Krause textbook
    parameters.
  - Make fixtures available to all tests without explicit import.

Relationships:
  Imported by : (pytest — auto-discovered)
  Imports     : core.machine_model, data.machines_mit

Extending:
  - To add a new reference motor fixture, add an entry to data/machines_mit.py
    and expose it here following the existing pattern.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.tim_machine_model import MachineParams
from data.machines_mit import KRAUSE_3HP, KRAUSE_50HP, KRAUSE_2250HP


@pytest.fixture
def mp_3hp():
    """Krause 3 HP — parâmetros de referência do livro."""
    return MachineParams(**KRAUSE_3HP)


@pytest.fixture
def mp_50hp():
    """Krause 50 HP."""
    return MachineParams(**KRAUSE_50HP)


@pytest.fixture
def mp_2250hp():
    """Krause 2250 HP."""
    return MachineParams(**KRAUSE_2250HP)


@pytest.fixture
def dol_result(mp_3hp):
    """Simulação DOL completa do 3HP para reuso entre testes."""
    from core.tim_facade import run_simulation, build_fns
    config = {"exp_type": "dol", "Tl_final": 12.0, "t_carga": 1.5}
    vfn, tfn, _ = build_fns(config, mp_3hp)
    return run_simulation(mp_3hp, tmax=3.0, h=1e-4, voltage_fn=vfn, torque_fn=tfn)
