# -*- coding: utf-8 -*-
"""
transforms.py
=============
Implements amplitude-invariant Clarke and Park transforms for abc → dq
conversion in the synchronous reference frame.

Responsibilities:
  - Generate balanced three-phase voltages (abc_voltages)
  - Apply the Clarke-Park transform (clarke_park_transform)
  - Provide the _SQRT3_2 constant for internal use

Relationships:
  Imported by : core.machine_model, core.solver, core.desequilibrio_falta
  Imports     : (numpy only)

Extending:
  - For a stationary reference frame (αβ), add a separate clarke_transform
    without the Park rotation step.
"""

from __future__ import annotations
import numpy as np

_SQRT3_2 = np.sqrt(3.0) / 2.0  # sqrt(3)/2 — fator da transformada Clarke


def abc_voltages(t, Vl: float, f: float):
    """Tensoes abc balanceadas (amplitude-invariante).

    Args:
        t:   instante(s) em segundos — escalar ou array NumPy.
        Vl:  tensao de linha pico-a-pico (V).
        f:   frequencia (Hz).

    Returns:
        (Va, Vb, Vc) — tensoes de fase, mesma forma que t.
    """
    tetae = 2.0 * np.pi * f * t
    # k = sqrt(2/3): convencao amplitude-invariante — |Va| = |Vqs| apos Clarke-Park
    # Ver SME/1. Fundamentos/3 - Transformadas Clarke-Park.md — secao 'Fator k'
    k = np.sqrt(2.0 / 3.0)
    Va = k * Vl * np.sin(tetae)
    Vb = k * Vl * np.sin(tetae - 2.0 * np.pi / 3.0)
    Vc = k * Vl * np.sin(tetae + 2.0 * np.pi / 3.0)
    return Va, Vb, Vc


def clarke_park_transform(Va, Vb, Vc, tetae):
    """Clarke (amplitude-invariante, k = sqrt(3/2)) + Park: abc -> dq sincrono.

    Args:
        Va, Vb, Vc: tensoes de fase (escalar ou array).
        tetae:      angulo eletrico do referencial sincrono (rad).

    Returns:
        (Vds, Vqs) — componentes no referencial dq sincrono.
    """
    # k = sqrt(3/2): inverso do k da geracao abc — garante que |Vdq| = |Vabc_pico|
    k   = np.sqrt(3.0 / 2.0)
    # Clarke (abc -> alfabeta): fusao com Park — sem array intermediario alfabeta
    Vaf = k * (Va - 0.5 * Vb - 0.5 * Vc)
    Vbt = k * _SQRT3_2 * (Vb - Vc)
    # Park (alfabeta -> dq sincrono): convencao Krause — Vds e eixo d, Vqs e eixo q
    # (Vds, Vqs) — ordem d-antes-q: compativel com Krause (2013) Eq. 6.5-17
    Vds =  np.cos(tetae) * Vaf + np.sin(tetae) * Vbt
    Vqs = -np.sin(tetae) * Vaf + np.cos(tetae) * Vbt
    return Vds, Vqs
