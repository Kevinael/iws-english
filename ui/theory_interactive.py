# -*- coding: utf-8 -*-
"""Re-exports all public render_* functions from ui.theory submodules."""

from ui.theory.boucherot import render_boucherot
from ui.theory.zonas_operacao import render_zonas_operacao
from ui.theory.comparativo_partidas import render_comparativo_partidas
from ui.theory.park_dinamico import render_park_dinamico
from ui.theory.sankey_potencia import render_sankey_potencia
from ui.theory.transitorios import render_transitorios_sincronizados
from ui.theory.fasorial import render_fasorial_desequilibrio
from ui.theory.circuito_alternavel import render_circuito_alternavel
from ui.theory.mcsa import render_mcsa
from ui.theory.braking import render_comparador_frenagem
from ui.theory.blocos_krause import render_blocos_krause

__all__ = [
    "render_boucherot",
    "render_zonas_operacao",
    "render_comparativo_partidas",
    "render_park_dinamico",
    "render_sankey_potencia",
    "render_transitorios_sincronizados",
    "render_fasorial_desequilibrio",
    "render_circuito_alternavel",
    "render_mcsa",
    "render_comparador_frenagem",
    "render_blocos_krause",
]
