# -*- coding: utf-8 -*-
"""
transforms.py — Transformadas de referencial para motores de inducao

Exporta:
  abc_voltages(t, Vl, f)              — tensoes trifasicas balanceadas (amplitude-invariante)
  clarke_park_transform(Va, Vb, Vc, tetae) — Clarke + Park: abc -> dq sincrono

Convencao amplitude-invariante (fator k = sqrt(2/3) na Clarke):
  - modulo das grandezas dq = modulo de fase no dominio abc
  - potencia: P = (3/2) * (Vqs*iqs + Vds*ids)

Documentacao detalhada de cada decisao de implementacao:
  SME/2. Modulos/core/transforms.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (secao 6)
  SME/1. Fundamentos/3 - Transformadas Clarke-Park.md
"""

from __future__ import annotations
import numpy as np


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
    Vbt = k * (np.sqrt(3.0) / 2.0 * Vb - np.sqrt(3.0) / 2.0 * Vc)
    # Park (alfabeta -> dq sincrono): convencao Krause — Vds e eixo d, Vqs e eixo q
    # (Vds, Vqs) — ordem d-antes-q: compativel com Krause (2013) Eq. 6.5-17
    Vds =  np.cos(tetae) * Vaf + np.sin(tetae) * Vbt
    Vqs = -np.sin(tetae) * Vaf + np.cos(tetae) * Vbt
    return Vds, Vqs
