# -*- coding: utf-8 -*-
"""DC machine configuration UI and parameter handling.

Exports:
  DC_CONFIGS              — 5 configurations with default params
  render_dc_config_selector — select machine type (sep_motor, shunt_motor, etc.)
  render_dc_circuit       — exibe circuito equivalente estático por configuração
  render_dc_params        — input fields for DC parameters
  get_dc_params           — return DCMachineParams from session_state
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from core.dc_machine_model import DCMachineParams

# Localização dos PNGs pré-gerados (relativo ao diretório do projeto)
_CIRCUIT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "circuits_dc")

_CIRCUIT_FILES = {
    "sep_motor":   "sep_motor.png",
    "shunt_motor": "shunt_motor.png",
    "series_motor": "series_motor.png",
    "sep_gen":     "sep_gen.png",
    "shunt_gen":   "shunt_gen.png",
}

# Widget key prefixes for DC parameters
_WK_DC = {
    "dc_config": "wi_dc_config",  # sep_motor, shunt_motor, series_motor, sep_gen, shunt_gen
    "Rf": "wi_dc_Rf",
    "Lf": "wi_dc_Lf",
    "Vf": "wi_dc_Vf",
    "Ra": "wi_dc_Ra",
    "La": "wi_dc_La",
    "Va": "wi_dc_Va",
    "J": "wi_dc_J",
    "B": "wi_dc_B",
    "kb": "wi_dc_kb",
    "Tload": "wi_dc_Tload",
    "Rl": "wi_dc_Rl",
    "Ll": "wi_dc_Ll",
}

# Default DC machine parameters (small test machine — from dcmei.sce)
DC_CONFIGS = {
    "sep_motor": {
        "name": "Motor de Campo Independente",
        "Rf": 1.43,
        "Lf": 0.1670,
        "Vf": 12.0,
        "Ra": 0.013,
        "La": 0.01,
        "Va": 24.0,
        "J": 0.21,
        "B": 0.000001074,
        "kb": 0.004,
        "Tload": 2.493,
        "Rl": 0.0,
        "Ll": 0.0,
    },
    "shunt_motor": {
        "name": "Motor de Campo em Paralelo",
        "Rf": 1.43,
        "Lf": 0.1670,
        "Vf": 0.0,
        "Ra": 0.013,
        "La": 0.01,
        "Va": 24.0,
        "J": 0.21,
        "B": 0.000001074,
        "kb": 0.004,
        "Tload": 0.0,
        "Rl": 0.0,
        "Ll": 0.0,
    },
    "series_motor": {
        "name": "Motor de Campo em Série",
        "Rf": 0.026,
        "Lf": 0.1670,
        "Vf": 0.0,
        "Ra": 0.013,
        "La": 0.01,
        "Va": 24.0,
        "J": 0.21,
        "B": 0.000001074,
        "kb": 0.004,
        "Tload": 0.0,
        "Rl": 0.0,
        "Ll": 0.0,
    },
    "sep_gen": {
        "name": "Gerador de Campo Independente",
        "Rf": 1.43,
        "Lf": 0.1670,
        "Vf": 48.0,
        "Ra": 0.013,
        "La": 0.01,
        "Va": 0.0,
        "J": 0.21,
        "B": 0.000001074,
        "kb": 0.004,
        "Tload": 4.0,
        "Rl": 2.5,
        "Ll": 1.5,
    },
    "shunt_gen": {
        "name": "Gerador de Campo em Paralelo",
        "Rf": 1.43,
        "Lf": 0.1670,
        "Vf": 0.0,
        "Ra": 0.013,
        "La": 0.01,
        "Va": 0.0,
        "J": 0.21,
        "B": 0.000001074,
        "kb": 0.004,
        "Tload": 4.0,
        "Rl": 2.5,
        "Ll": 1.5,
    },
}


def render_dc_circuit(config: str) -> None:
    """Exibe circuito equivalente estático da configuração CC selecionada."""
    fname = _CIRCUIT_FILES.get(config)
    if fname is None:
        return

    path = os.path.normpath(os.path.join(_CIRCUIT_DIR, fname))
    if not os.path.isfile(path):
        st.caption(f"Circuito não encontrado: {fname}")
        return

    st.markdown('<p class="slabel">Circuito Equivalente</p>', unsafe_allow_html=True)
    st.image(path, use_container_width=True)


def render_dc_config_selector() -> str:
    """Render DC machine type selector. Returns config key."""
    st.subheader("Tipo de Máquina CC")

    col1, col2 = st.columns(2)
    with col1:
        mode = st.radio(
            "Modo de Operação",
            ["Motor", "Gerador"],
            key="wi_dc_mode",
            horizontal=False,
        )
    with col2:
        if mode == "Motor":
            excitation = st.radio(
                "Excitação",
                ["Campo Independente", "Campo em Paralelo", "Campo em Série"],
                key="wi_dc_excitation_motor",
                horizontal=False,
            )
            config_map = {
                "Campo Independente": "sep_motor",
                "Campo em Paralelo": "shunt_motor",
                "Campo em Série": "series_motor",
            }
        else:
            excitation = st.radio(
                "Excitação",
                ["Campo Independente", "Campo em Paralelo"],
                key="wi_dc_excitation_gen",
                horizontal=False,
            )
            config_map = {
                "Campo Independente": "sep_gen",
                "Campo em Paralelo": "shunt_gen",
            }

        config = config_map[excitation]

    return config


def render_dc_params() -> dict[str, float]:
    """Render DC parameter input fields. Returns dict of parameter values."""
    st.subheader("Parâmetros da Máquina CC")

    config = st.session_state.get(_WK_DC["dc_config"], "sep_motor")
    defaults = DC_CONFIGS.get(config, DC_CONFIGS["sep_motor"])

    params = {}

    # ── Circuito de Campo ──
    st.markdown("**Circuito de Campo**")
    col1, col2, col3 = st.columns(3)
    with col1:
        params["Rf"] = st.number_input(
            "Rf (Ω)", value=defaults["Rf"], min_value=0.001, format="%.4f",
            key=_WK_DC["Rf"],
        )
    with col2:
        params["Lf"] = st.number_input(
            "Lf (H)", value=defaults["Lf"], min_value=0.0001, format="%.6f",
            key=_WK_DC["Lf"],
        )
    with col3:
        params["Vf"] = st.number_input(
            "Vf (V)", value=defaults["Vf"], min_value=0.0, format="%.2f",
            key=_WK_DC["Vf"],
            help="Tensão de campo (apenas campo indep.)",
        )

    # ── Circuito de Armadura ──
    st.markdown("**Circuito de Armadura**")
    col1, col2, col3 = st.columns(3)
    with col1:
        params["Ra"] = st.number_input(
            "Ra (Ω)", value=defaults["Ra"], min_value=0.001, format="%.6f",
            key=_WK_DC["Ra"],
        )
    with col2:
        params["La"] = st.number_input(
            "La (H)", value=defaults["La"], min_value=0.0001, format="%.6f",
            key=_WK_DC["La"],
        )
    with col3:
        params["Va"] = st.number_input(
            "Va (V)", value=defaults["Va"], min_value=0.0, format="%.2f",
            key=_WK_DC["Va"],
            help="Tensão de armadura (motors only)",
        )

    # ── Parâmetros Mecânicos ──
    st.markdown("**Parâmetros Mecânicos**")
    col1, col2, col3 = st.columns(3)
    with col1:
        params["J"] = st.number_input(
            "J (kg·m²)", value=defaults["J"], min_value=1e-6, format="%.8f",
            key=_WK_DC["J"],
        )
    with col2:
        params["B"] = st.number_input(
            "B (N·m·s/rad)", value=defaults["B"], min_value=0.0, format="%.10f",
            key=_WK_DC["B"],
        )
    with col3:
        params["kb"] = st.number_input(
            "kb (V·s/rad)", value=defaults["kb"], min_value=0.0001, format="%.6f",
            key=_WK_DC["kb"],
        )

    # ── Carga e Gerador (Load para motores, Load+Source para geradores) ──
    st.markdown("**Torque de Carga**")
    col1, col2, col3 = st.columns(3)
    with col1:
        params["Tload"] = st.number_input(
            "Tload (N·m)", value=defaults["Tload"], min_value=0.0, format="%.4f",
            key=_WK_DC["Tload"],
            help="Torque de carga (motors) ou mec. (gerador)",
        )

    # ── Carga de Saída (para geradores) ──
    if "gen" in config:
        st.markdown("**Carga de Saída (Gerador)**")
        col1, col2 = st.columns(2)
        with col1:
            params["Rl"] = st.number_input(
                "Rl (Ω)", value=defaults["Rl"], min_value=0.001, format="%.4f",
                key=_WK_DC["Rl"],
                help="Resistência de carga",
            )
        with col2:
            params["Ll"] = st.number_input(
                "Ll (H)", value=defaults["Ll"], min_value=0.0, format="%.6f",
                key=_WK_DC["Ll"],
                help="Indutância de carga",
            )
    else:
        params["Rl"] = 0.0
        params["Ll"] = 0.0

    return params


def get_dc_params() -> DCMachineParams:
    """Retrieve DC machine parameters from session_state."""
    config = st.session_state.get(_WK_DC["dc_config"], "sep_motor")
    params = {
        "config": config,
        "Rf": st.session_state.get(_WK_DC["Rf"], DC_CONFIGS[config]["Rf"]),
        "Lf": st.session_state.get(_WK_DC["Lf"], DC_CONFIGS[config]["Lf"]),
        "Ra": st.session_state.get(_WK_DC["Ra"], DC_CONFIGS[config]["Ra"]),
        "La": st.session_state.get(_WK_DC["La"], DC_CONFIGS[config]["La"]),
        "J": st.session_state.get(_WK_DC["J"], DC_CONFIGS[config]["J"]),
        "B": st.session_state.get(_WK_DC["B"], DC_CONFIGS[config]["B"]),
        "kb": st.session_state.get(_WK_DC["kb"], DC_CONFIGS[config]["kb"]),
        "Vf": st.session_state.get(_WK_DC["Vf"], DC_CONFIGS[config]["Vf"]),
        "Va": st.session_state.get(_WK_DC["Va"], DC_CONFIGS[config]["Va"]),
        "Tload": st.session_state.get(_WK_DC["Tload"], DC_CONFIGS[config]["Tload"]),
        "Rl": st.session_state.get(_WK_DC["Rl"], DC_CONFIGS[config]["Rl"]),
        "Ll": st.session_state.get(_WK_DC["Ll"], DC_CONFIGS[config]["Ll"]),
    }
    return DCMachineParams(**{k: v for k, v in params.items() if k != "config"})
