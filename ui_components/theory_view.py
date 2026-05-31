# -*- coding: utf-8 -*-
"""Theory Tab — entry point for ui_components.

The complete educational logic lives in ui/theory.py.
This module re-exports render_theory_tab to maintain a uniform
interface within the ui_components package.
"""

from __future__ import annotations

from ui.theory import render_theory_tab  # noqa: F401  (re-export)

__all__ = ["render_theory_tab"]
