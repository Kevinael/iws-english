# -*- coding: utf-8 -*-
"""
theory_view.py
==============
Thin re-export wrapper providing a uniform interface for the Theory tab within ui.

Responsibilities:
  - Re-export render_theory_tab from ui.theory.
  - Keep the ui package interface stable regardless of internal ui/ restructuring.

Relationships:
  Imported by : IWS_UI
  Imports     : ui.theory

Extending:
  - To route Theory to a different module, change the import source here without touching IWS_UI.
"""

from __future__ import annotations

from ui.theory import render_theory_tab  # noqa: F401  (re-export)

__all__ = ["render_theory_tab"]
