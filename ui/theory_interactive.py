# -*- coding: utf-8 -*-
"""Re-exports all public render_* functions from ui.theory submodules."""

from ui.theory.boucherot import render_boucherot
from ui.theory.operating_zones import render_operating_zones
from ui.theory.startup_comparison import render_startup_comparison
from ui.theory.park_dinamico import render_park_dinamico
from ui.theory.sankey_power import render_sankey_power
from ui.theory.transients import render_synchronized_transients
from ui.theory.phasor import render_imbalance_phasor
from ui.theory.switchable_circuit import render_switchable_circuit
from ui.theory.mcsa import render_mcsa
from ui.theory.braking import render_braking_comparator
from ui.theory.krause_blocks import render_krause_blocks

__all__ = [
    "render_boucherot",
    "render_operating_zones",
    "render_startup_comparison",
    "render_park_dinamico",
    "render_sankey_power",
    "render_synchronized_transients",
    "render_imbalance_phasor",
    "render_switchable_circuit",
    "render_mcsa",
    "render_braking_comparator",
    "render_krause_blocks",
]
