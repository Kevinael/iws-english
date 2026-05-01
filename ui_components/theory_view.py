# -*- coding: utf-8 -*-
"""Aba Teoria — ponto de entrada para ui_components.

A lógica educacional completa vive em ui/theory.py.
Este módulo re-exporta render_theory_tab para manter a interface
uniforme dentro do pacote ui_components.
"""

from __future__ import annotations

from ui.theory import render_theory_tab  # noqa: F401  (re-export)

__all__ = ["render_theory_tab"]
