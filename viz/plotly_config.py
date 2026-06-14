# -*- coding: utf-8 -*-
"""
plotly_config.py
================
Shared Plotly chart configuration dicts used by MIT and DC result modules.

Responsibilities:
  - Single source of truth for Plotly modebar/export settings.

Relationships:
  Imported by : ui_components.tim_results, ui_components.sim_results_dc
  Imports     : (none)
"""

from __future__ import annotations

from typing import Any

MIT_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "simulation_chart",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
}

DC_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "dcm_simulation",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
}
