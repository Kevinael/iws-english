# -*- coding: utf-8 -*-
"""Execução da simulação MCC — orquestra DCSolver e persiste resultado.

Exporta:
    calc_tmax_dc_auto        — tmax automático por modo
    render_experiment_config_dc — UI de configuração de experimento DC
    execute_dc_simulation_flow  — botão Executar → session_state["dc_sim_result"]
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from core.dc_machine_model import DCMachineParams, DCMachineODEs
from core.dc_solver import DCSolver
from core.dc_sources import create_dc_source


# Chaves de widget para experimento DC
_WK_EXP = {
    "exp_type":      "wi_dc_exp_type",
    "t_carga":       "wi_dc_t_carga",
    "t_ramp":        "wi_dc_t_ramp",
    "t_switch":      "wi_dc_t_switch",
    "t_after_switch": "wi_dc_t_after_switch",
    "t_retirada":    "wi_dc_t_retirada",
    "t_weaken":      "wi_dc_t_weaken",
    "t_after_weaken": "wi_dc_t_after_weaken",
    "tmax":          "wi_dc_tmax",
    "h":             "wi_dc_h",
    "var_keys":      "wi_dc_var_keys",
}

_EXP_LABELS = {
    "dol_dc":        "DOL — Partida Direta",
    "resistencia_dc": "Partida por Resistência",
    "plugging_dc":   "Frenagem por Plugging",
    "pulso_dc":      "Pulso de Carga",
    "gerador_dc":    "Gerador",
    "campo_fraco_dc": "Campo Fraco",
}

_ALL_VAR_KEYS    = ["ia", "ifd", "wm", "Te", "Ea"]
_ALL_VAR_LABELS  = [
    "Corrente de Armadura (A)",
    "Corrente de Campo (A)",
    "Velocidade (rad/s)",
    "Torque (N·m)",
    "Tensão Induzida (V)",
]


# ─────────────────────────────────────────────────────────────────────────────
# TMAX AUTOMÁTICO
# ─────────────────────────────────────────────────────────────────────────────

def calc_tmax_dc_auto(exp_config: dict, params: DCMachineParams) -> float:
    """tmax automático: último evento + acomodação mecânica (heurística 10×J)."""
    exp_type = exp_config.get("exp_type", "dol_dc")

    if exp_type == "dol_dc":
        t_last = exp_config.get("t_carga", 1.0) or 1.0
    elif exp_type == "resistencia_dc":
        t_last = exp_config.get("t_ramp", 1.0) + exp_config.get("t_carga", 1.0)
    elif exp_type == "plugging_dc":
        t_last = exp_config.get("t_switch", 1.0) + exp_config.get("t_after_switch", 2.0)
    elif exp_type == "pulso_dc":
        t_last = exp_config.get("t_retirada", 2.0)
    elif exp_type == "gerador_dc":
        t_last = exp_config.get("t_carga", 1.0)
    elif exp_type == "campo_fraco_dc":
        t_last = exp_config.get("t_weaken", 1.0) + exp_config.get("t_after_weaken", 2.0)
    else:
        t_last = 1.0

    t_settle = float(min(max(10.0 * params.J, 1.0), 20.0))
    return t_last + t_settle


# ─────────────────────────────────────────────────────────────────────────────
# UI DE CONFIGURAÇÃO DE EXPERIMENTO
# ─────────────────────────────────────────────────────────────────────────────

def render_experiment_config_dc(
    params: DCMachineParams,
    config: str,
) -> tuple[dict, list[str], list[str], float, float]:
    """Renderiza seletores de experimento DC (modo, variáveis, tempo, passo).

    Retorna
    -------
    exp_config : dict  — configuração do experimento
    var_keys   : list  — variáveis selecionadas
    var_labels : list  — rótulos correspondentes
    tmax       : float — tempo total de simulação (s)
    h          : float — passo de integração (s)
    """
    st.markdown("---")
    st.markdown('<p class="slabel">Configuração do Experimento</p>', unsafe_allow_html=True)

    # ── Modo de operação ──────────────────────────────────────────────────
    # Filtra modos disponíveis por tipo de configuração
    if "gen" in config:
        modos_disp = {"gerador_dc": _EXP_LABELS["gerador_dc"]}
    else:
        modos_disp = {k: v for k, v in _EXP_LABELS.items() if k != "gerador_dc"}
        if config == "series_motor":
            del modos_disp["campo_fraco_dc"]

    modo_opts   = list(modos_disp.values())
    modo_keys   = list(modos_disp.keys())
    modo_idx    = 0
    cur_exp     = st.session_state.get(_WK_EXP["exp_type"], modo_keys[0])
    if cur_exp in modo_keys:
        modo_idx = modo_keys.index(cur_exp)

    exp_label = st.selectbox(
        "Modo de Operação",
        modo_opts,
        index=modo_idx,
        key=_WK_EXP["exp_type"] + "_sel",
    )
    exp_type = modo_keys[modo_opts.index(exp_label)]
    st.session_state[_WK_EXP["exp_type"]] = exp_type

    # ── Parâmetros por modo ───────────────────────────────────────────────
    exp_config: dict[str, Any] = {"exp_type": exp_type}

    col1, col2 = st.columns(2)

    if exp_type == "dol_dc":
        with col1:
            t_carga = st.number_input(
                "Instante de aplicação de carga (s)",
                min_value=0.1, value=float(st.session_state.get(_WK_EXP["t_carga"], 1.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_carga"],
                help="Tempo após o qual Tload é aplicado (0 = carga imediata).",
            )
        exp_config["t_carga"] = t_carga

    elif exp_type == "resistencia_dc":
        with col1:
            t_ramp = st.number_input(
                "Duração da rampa de tensão (s)",
                min_value=0.1, value=float(st.session_state.get(_WK_EXP["t_ramp"], 1.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_ramp"],
                help="Tempo para Va subir de 0 até Va nominal.",
            )
        with col2:
            t_carga = st.number_input(
                "Instante de carga após rampa (s)",
                min_value=0.0, value=float(st.session_state.get(_WK_EXP["t_carga"], 0.5)),
                step=0.1, format="%.2f", key=_WK_EXP["t_carga"],
            )
        exp_config.update({"t_ramp": t_ramp, "t_carga": t_carga})

    elif exp_type == "plugging_dc":
        with col1:
            t_switch = st.number_input(
                "Instante da comutação (s)",
                min_value=0.1, value=float(st.session_state.get(_WK_EXP["t_switch"], 1.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_switch"],
                help="Momento em que a polaridade de Va é invertida.",
            )
        with col2:
            t_after = st.number_input(
                "Tempo pós-comutação (s)",
                min_value=0.5, value=float(st.session_state.get(_WK_EXP["t_after_switch"], 2.0)),
                step=0.5, format="%.2f", key=_WK_EXP["t_after_switch"],
            )
        exp_config.update({"t_switch": t_switch, "t_after_switch": t_after})

    elif exp_type == "pulso_dc":
        with col1:
            t_carga = st.number_input(
                "Instante de aplicação do pulso (s)",
                min_value=0.1, value=float(st.session_state.get(_WK_EXP["t_carga"], 1.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_carga"],
            )
        with col2:
            t_retirada = st.number_input(
                "Instante de retirada do pulso (s)",
                min_value=0.2, value=float(st.session_state.get(_WK_EXP["t_retirada"], 3.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_retirada"],
            )
        exp_config.update({"t_carga": t_carga, "t_retirada": t_retirada})

    elif exp_type == "gerador_dc":
        with col1:
            t_carga = st.number_input(
                "Instante de conexão da carga (s)",
                min_value=0.1, value=float(st.session_state.get(_WK_EXP["t_carga"], 1.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_carga"],
            )
        exp_config["t_carga"] = t_carga

    elif exp_type == "campo_fraco_dc":
        with col1:
            t_weaken = st.number_input(
                "Instante do enfraquecimento (s)",
                min_value=0.1, value=float(st.session_state.get(_WK_EXP["t_weaken"], 1.0)),
                step=0.1, format="%.2f", key=_WK_EXP["t_weaken"],
                help="Momento em que Vf é reduzida para enfraquecer o campo.",
            )
        with col2:
            t_after = st.number_input(
                "Tempo pós-enfraquecimento (s)",
                min_value=0.5, value=float(st.session_state.get(_WK_EXP["t_after_weaken"], 3.0)),
                step=0.5, format="%.2f", key=_WK_EXP["t_after_weaken"],
            )
        exp_config.update({"t_weaken": t_weaken, "t_after_weaken": t_after})

    # ── Seleção de variáveis ──────────────────────────────────────────────
    st.write("")
    st.markdown("**Variáveis para plotar**")

    # Filtrar vars disponíveis por configuração
    if config == "series_motor":
        avail_keys   = ["ia", "wm", "Te", "Ea"]
        avail_labels = [_ALL_VAR_LABELS[i] for i, k in enumerate(_ALL_VAR_KEYS) if k in avail_keys]
    else:
        avail_keys   = _ALL_VAR_KEYS
        avail_labels = _ALL_VAR_LABELS

    default_sel = avail_keys  # todas por padrão
    saved_sel   = st.session_state.get(_WK_EXP["var_keys"], default_sel)
    saved_sel   = [k for k in saved_sel if k in avail_keys]
    if not saved_sel:
        saved_sel = default_sel

    # Checkboxes em linha
    var_cols  = st.columns(len(avail_keys))
    sel_keys  = []
    sel_labels = []
    for col, key, label in zip(var_cols, avail_keys, avail_labels):
        with col:
            checked = st.checkbox(
                label.split(" ")[0],  # abreviação: só o nome da variável
                value=(key in saved_sel),
                key=f"wi_dc_var_{key}",
                help=label,
            )
        if checked:
            sel_keys.append(key)
            sel_labels.append(label)

    st.session_state[_WK_EXP["var_keys"]] = sel_keys

    # ── Tempo e passo ─────────────────────────────────────────────────────
    st.write("")
    _tc1, _tc2, _tc3 = st.columns(3)
    with _tc1:
        use_auto = st.toggle(
            "tmax automático",
            value=st.session_state.get("wi_dc_tmax_auto", True),
            key="wi_dc_tmax_auto",
        )
    with _tc2:
        if use_auto:
            _tmax_prev = calc_tmax_dc_auto(exp_config, params)
            st.metric("tmax estimado (s)", f"{_tmax_prev:.2f}")
            tmax = _tmax_prev
        else:
            tmax = st.number_input(
                "tmax (s)",
                min_value=0.1,
                value=float(st.session_state.get(_WK_EXP["tmax"], 12.0)),
                step=0.5, format="%.2f", key=_WK_EXP["tmax"],
            )
    with _tc3:
        h = st.number_input(
            "Passo h (s)",
            min_value=1e-5, max_value=0.1,
            value=float(st.session_state.get(_WK_EXP["h"], 0.001)),
            step=0.001, format="%.4f", key=_WK_EXP["h"],
        )

    return exp_config, sel_keys, sel_labels, tmax, h


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTOR
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_dc_solve(
    config: str,
    params_tuple: tuple,
    exp_config_tuple: tuple,
    tmax: float,
    h: float,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Executa solver DC — cacheado por (config, params, exp_config, tmax, h)."""
    params_dict = dict(params_tuple)
    params      = DCMachineParams(**params_dict)
    exp_config  = dict(exp_config_tuple)
    exp_type    = exp_config.get("exp_type", "dol_dc")

    if config == "series_motor":
        x0 = np.array([0.0, 0.0])         # [ia, wm]
    else:
        x0 = np.array([0.0, 0.0, 0.0])    # [ifd, ia, wm]

    Va_nom = params.Va if exp_type != "gerador_dc" else 0.0

    if exp_type == "dol_dc":
        Va_func = create_dc_source("dol_dc", Va_nom=Va_nom)
    elif exp_type == "resistencia_dc":
        Va_func = create_dc_source("resistencia_dc", Va_nom=Va_nom,
                                   t_ramp=exp_config.get("t_ramp", 1.0))
    elif exp_type == "plugging_dc":
        Va_func = create_dc_source("plugging_dc", Va_nom=Va_nom,
                                   t_switch=exp_config.get("t_switch", 1.0))
    elif exp_type == "pulso_dc":
        Va_func = create_dc_source("pulso_dc", Va_nom=Va_nom)
    elif exp_type == "gerador_dc":
        Va_func = create_dc_source("gerador_dc")
    elif exp_type == "campo_fraco_dc":
        Va_func = create_dc_source("campo_fraco_dc", Va_nom=Va_nom)
    else:
        raise ValueError(f"exp_type desconhecido: {exp_type}")

    t_eval  = np.arange(0.0, tmax + h / 2.0, h)
    solver  = DCSolver(config, params, t_eval, x0)
    t, x, y = solver.run(Va_func)
    return t, x, y


def execute_dc_simulation_flow(
    config: str,
    params: DCMachineParams,
    exp_config: dict[str, Any],
    var_keys: list[str],
    var_labels: list[str],
    tmax: float,
    h: float,
    dark: bool,
) -> None:
    """Executa simulação DC e armazena resultado em session_state["dc_sim_result"].

    Usa cache @st.cache_data para evitar re-integração quando parâmetros não mudam.
    """
    if not var_keys:
        st.warning("Selecione ao menos uma variável para plotar.")
        return

    exp_type = exp_config.get("exp_type", "dol_dc")

    if tmax <= 0.0:
        tmax = calc_tmax_dc_auto(exp_config, params)

    # Serializa params e exp_config para chave de cache
    params_tuple = tuple(sorted({
        "Rf": params.Rf, "Lf": params.Lf,
        "Ra": params.Ra, "La": params.La,
        "J":  params.J,  "B":  params.B,
        "kb": params.kb, "Vf": params.Vf,
        "Va": params.Va, "Tload": params.Tload,
        "Rl": params.Rl, "Ll": params.Ll,
    }.items()))
    exp_config_tuple = tuple(sorted(exp_config.items()))

    try:
        with st.spinner("Integrando ODE do Motor CC..."):
            t, x, y = _cached_dc_solve(
                config, params_tuple, exp_config_tuple, tmax, h
            )

        result = {
            "config":    config,
            "exp_type":  exp_type,
            "t":         t,
            "x":         x,
            "y":         y,
            "var_keys":  var_keys,
            "var_labels": var_labels,
            "params":    params,
            "tmax":      tmax,
            "h":         h,
            "dark_mode": dark,
        }

        st.session_state["dc_sim_result"] = result
        st.session_state.pop("pdf_bytes_dc_academico", None)  # invalida PDF anterior
        st.success(f"Simulação DC concluída: {len(t)} pontos, {t[-1]:.2f}s")

    except Exception as exc:
        st.error(f"Erro na integração DC: {exc}")
        import traceback
        st.code(traceback.format_exc())
