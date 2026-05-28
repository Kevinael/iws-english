# -*- coding: utf-8 -*-
"""Configuração de parâmetros e experimento para MCC.

Exporta:
    render_dc_machine_params        — col_params (seletor + inputs)
    render_experiment_config_dc     — col_circuit inferior (modo + variáveis)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from core.dc_machine_model import DCMachineParams


# ─────────────────────────────────────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────────────────────────────────────

_PRESETS_DC: dict[str, dict[str, Any]] = {
    "Motor Separado (dcmei)": {
        "excitation": "sep_motor",
        "Va": 24.0, "Ra": 0.013, "La": 0.01,
        "Vf": 12.0, "Rf": 1.43,  "Lf": 0.167,
        "kb": 0.004, "J": 0.21,  "B": 1.074e-6, "Tload": 2.493,
    },
    "Motor Shunt (dcmp)": {
        "excitation": "shunt_motor",
        "Va": 24.0, "Ra": 0.013, "La": 0.01,
        "Rf": 1.43, "Lf": 0.167,
        "kb": 0.004, "J": 0.21,  "B": 1.074e-6, "Tload": 2.493,
    },
    "Motor Série (dcms)": {
        "excitation": "series_motor",
        "Va": 24.0, "Ra": 0.013, "La": 0.01,
        "Rf": 0.026, "Lf": 0.167,
        "kb": 0.004, "J": 0.21,  "B": 1.074e-6, "Tload": 2.493,
    },
    "Gerador Separado (dgmei)": {
        "excitation": "sep_gen",
        "Va": 0.0,  "Ra": 0.013, "La": 0.01,
        "Vf": 48.0, "Rf": 1.43,  "Lf": 0.167,
        "Rl": 2.5,  "Ll": 1.5,
        "kb": 0.004, "J": 0.21,  "B": 1.074e-6, "Tload": 4.0,
    },
    "Gerador Shunt (dcgp)": {
        "excitation": "shunt_gen",
        "Va": 0.0,  "Ra": 0.013, "La": 0.01,
        "Rf": 1.43, "Lf": 0.167,
        "Rl": 2.5,  "Ll": 1.5,
        "kb": 0.004, "J": 0.21,  "B": 1.074e-6, "Tload": 4.0,
    },
}

# Variáveis disponíveis para plotar por tipo de grandeza
_VAR_OPTIONS: dict[str, str] = {
    "ia":  "Corrente de Armadura $i_a$ (A)",
    "ifd": "Corrente de Campo $i_{fd}$ (A)",
    "wm":  "Velocidade Angular $\\omega_m$ (rad/s)",
    "n":   "Velocidade $n$ (RPM)",
    "Te":  "Conjugado Eletromagnético $T_e$ (N·m)",
    "Ea":  "FEM $E_a$ (V)",
    "Vt":  "Tensão de Terminal $V_t$ (V)",
}

_DEFAULT_VARS: list[str] = ["ia", "wm", "Te"]

# Modos de operação disponíveis por configuração
_MODES_BY_EXC: dict[str, list[str]] = {
    "sep_motor":    ["dol_dc", "resistencia_dc", "plugging_dc", "pulso_dc", "campo_fraco_dc"],
    "shunt_motor":  ["dol_dc", "resistencia_dc", "plugging_dc", "pulso_dc"],
    "series_motor": ["dol_dc", "resistencia_dc", "plugging_dc", "pulso_dc"],
    "sep_gen":      ["gerador_dc"],
    "shunt_gen":    ["gerador_dc"],
}

_MODE_LABELS: dict[str, str] = {
    "dol_dc":         "Partida Direta (DOL)",
    "resistencia_dc": "Partida com Resistência Série",
    "plugging_dc":    "Reversão de Rotação (Plugging)",
    "pulso_dc":       "Pulso de Carga",
    "campo_fraco_dc": "Enfraquecimento de Campo",
    "gerador_dc":     "Gerador — Carga Resistiva",
}

_EXC_LABELS: dict[str, str] = {
    "sep_motor":    "Excitação Separada — Motor",
    "shunt_motor":  "Shunt (Paralelo) — Motor",
    "series_motor": "Série — Motor",
    "sep_gen":      "Excitação Separada — Gerador",
    "shunt_gen":    "Shunt (Paralelo) — Gerador",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _pgroup(title: str) -> None:
    st.markdown(f'<div class="pgroup-title">{title}</div>', unsafe_allow_html=True)


def _ibox(html: str) -> None:
    st.markdown(f'<div class="ibox">{html}</div>', unsafe_allow_html=True)


def _wi(key: str, default: Any) -> None:
    """Inicializa session_state se ausente."""
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — PARÂMETROS DA MÁQUINA (col_params)
# ─────────────────────────────────────────────────────────────────────────────

def render_dc_machine_params(dark: bool, experiment_mode: bool) -> tuple[DCMachineParams, int]:
    """Renderiza seletor de parâmetros MCC.

    Retorna (DCMachineParams, ref_code).
    ref_code: hash inteiro para cache invalidation.
    """
    from core.dc_estimator import estimate_dc_nameplate, estimate_dc_tests

    st.markdown('<p class="slabel">Parâmetros da Máquina</p>', unsafe_allow_html=True)

    # ── Configuração de excitação ────────────────────────────────────────────
    _wi("wi_dc_excitation", "sep_motor")
    exc_options = list(_EXC_LABELS.keys())
    exc_labels  = [_EXC_LABELS[k] for k in exc_options]
    exc_stored  = st.session_state.get("wi_dc_excitation", "sep_motor")
    exc_idx     = exc_options.index(exc_stored) if exc_stored in exc_options else 0

    exc_label_sel = st.selectbox(
        "Configuração", exc_labels, index=exc_idx,
        key="_dc_exc_sel", label_visibility="visible",
        disabled=experiment_mode,
    )
    exc = exc_options[exc_labels.index(exc_label_sel)]
    st.session_state["wi_dc_excitation"] = exc

    # ── Fonte de dados: Manual / Placa / Ensaios ─────────────────────────────
    _wi("wi_dc_input_mode", "Manual")
    input_mode = st.radio(
        "Fonte de dados", ["Manual", "Placa de Identificação", "Ensaios"],
        index=["Manual", "Placa de Identificação", "Ensaios"].index(
            st.session_state.get("wi_dc_input_mode", "Manual")
        ),
        horizontal=True, key="wi_dc_input_mode",
        disabled=experiment_mode,
    )

    if input_mode == "Placa de Identificação" and not experiment_mode:
        _pgroup("Dados da Placa (NEMA)")
        p1, p2, p3, p4 = st.columns(4)
        _wi("wi_dc_Pn_kW", 0.5)
        _wi("wi_dc_Vn_placa", 24.0)
        _wi("wi_dc_nn_rpm", 6500.0)
        _wi("wi_dc_eta_placa", 0.85)
        Pn_kW    = p1.number_input("$P_n$ (kW)",  min_value=0.001, key="wi_dc_Pn_kW",     format="%.3f")
        Vn_p     = p2.number_input("$V_n$ (V)",   min_value=1.0,   key="wi_dc_Vn_placa",  format="%.1f")
        nn_rpm   = p3.number_input("$n_n$ (RPM)", min_value=1.0,   key="wi_dc_nn_rpm",    format="%.0f")
        eta_p    = p4.number_input("$\\eta$",      min_value=0.01, max_value=1.0,
                                    key="wi_dc_eta_placa", format="%.3f")
        est = estimate_dc_nameplate(Pn_kW * 1000, Vn_p, nn_rpm, eta_p, exc)
        for fld, wk in [("Ra","wi_dc_Ra"),("La","wi_dc_La"),("kb","wi_dc_kb"),
                        ("Va","wi_dc_Va"),("Vf","wi_dc_Vf"),("Rf","wi_dc_Rf"),
                        ("Lf","wi_dc_Lf"),("J","wi_dc_J"),("B","wi_dc_B")]:
            if fld in est:
                st.session_state[wk] = est[fld]
        st.info(f"Estimado: $R_a$ = {est['Ra']:.4f} Ω | $k_b$ = {est['kb']:.5f} | "
                f"$V_a$ = {est['Va']:.1f} V")

    elif input_mode == "Ensaios" and not experiment_mode:
        _pgroup("Ensaio de Resistência CC")
        e1, e2 = st.columns(2)
        _wi("wi_dc_V_dc_test", 1.0)
        _wi("wi_dc_I_dc_test", 0.1)
        V_dc_t = e1.number_input("$V_{dc}$ (V)", min_value=0.001, key="wi_dc_V_dc_test", format="%.3f")
        I_dc_t = e2.number_input("$I_{dc}$ (A)", min_value=0.001, key="wi_dc_I_dc_test", format="%.3f")

        _pgroup("Ensaio a Vazio")
        g1, g2, g3, g4 = st.columns(4)
        _wi("wi_dc_V_nl_test",  24.0)
        _wi("wi_dc_I_nl_test",  0.05)
        _wi("wi_dc_If_nl_test", 8.4)
        _wi("wi_dc_n_nl_test",  6500.0)
        V_nl_t  = g1.number_input("$V_{a,nl}$ (V)",    min_value=0.01,  key="wi_dc_V_nl_test",  format="%.3f")
        I_nl_t  = g2.number_input("$I_{a,nl}$ (A)",    min_value=0.001, key="wi_dc_I_nl_test",  format="%.3f")
        If_nl_t = g3.number_input("$I_{fd,nl}$ (A)",   min_value=0.001, key="wi_dc_If_nl_test", format="%.3f")
        n_nl_t  = g4.number_input("$n_{nl}$ (RPM)",    min_value=1.0,   key="wi_dc_n_nl_test",  format="%.1f")
        est = estimate_dc_tests(V_dc_t, I_dc_t, V_nl_t, I_nl_t, If_nl_t, n_nl_t, exc)
        for fld, wk in [("Ra","wi_dc_Ra"),("La","wi_dc_La"),("kb","wi_dc_kb"),("Lf","wi_dc_Lf")]:
            if fld in est:
                st.session_state[wk] = est[fld]
        st.info(f"Estimado: $R_a$ = {est['Ra']:.4f} Ω | $k_b$ = {est['kb']:.5f} | "
                f"$E_{{a,nl}}$ = {est['Ea_nl']:.3f} V")

    # ── Preset loader ────────────────────────────────────────────────────────
    preset_names = ["— Selecionar preset —"] + list(_PRESETS_DC.keys())
    preset_sel = st.selectbox("Preset", preset_names, key="wi_dc_preset",
                               label_visibility="collapsed")
    if preset_sel != "— Selecionar preset —":
        ps = _PRESETS_DC[preset_sel]
        for k, v in ps.items():
            st.session_state[f"wi_dc_{k}"] = v
        st.session_state["wi_dc_preset"] = "— Selecionar preset —"
        st.rerun()

    is_gen    = exc in ("sep_gen", "shunt_gen")
    is_sep    = exc in ("sep_motor", "sep_gen")
    is_series = exc == "series_motor"

    if experiment_mode:
        # Modo travado: mostrar resumo
        _wi("wi_dc_Va",    220.0)
        _wi("wi_dc_Ra",    1.0)
        _wi("wi_dc_La",    0.05)
        _wi("wi_dc_kb",    1.2)
        _wi("wi_dc_J",     0.05)
        _wi("wi_dc_B",     0.01)
        _wi("wi_dc_Tload", 5.0)
        st.info("Parâmetros travados no modo experimento.")
        va    = float(st.session_state.get("wi_dc_Va",  220.0))
        ra    = float(st.session_state.get("wi_dc_Ra",  1.0))
        la    = float(st.session_state.get("wi_dc_La",  0.05))
        vf    = float(st.session_state.get("wi_dc_Vf",  va if not is_sep else 220.0))
        rf    = float(st.session_state.get("wi_dc_Rf",  150.0))
        lf    = float(st.session_state.get("wi_dc_Lf",  10.0))
        rl    = float(st.session_state.get("wi_dc_Rl",  0.0))
        ll    = float(st.session_state.get("wi_dc_Ll",  0.0))
        kb    = float(st.session_state.get("wi_dc_kb",  1.2))
        J     = float(st.session_state.get("wi_dc_J",   0.05))
        B     = float(st.session_state.get("wi_dc_B",   0.01))
        Tload = float(st.session_state.get("wi_dc_Tload", 5.0))
    else:
        # Inicializar defaults
        _wi("wi_dc_Va",    24.0)
        _wi("wi_dc_Ra",    0.013)
        _wi("wi_dc_La",    0.01)
        _wi("wi_dc_Vf",    12.0)
        _wi("wi_dc_Rf",    1.43)
        _wi("wi_dc_Lf",    0.167)
        _wi("wi_dc_Rl",    0.0)
        _wi("wi_dc_Ll",    0.0)
        _wi("wi_dc_kb",    0.004)
        _wi("wi_dc_J",     0.21)
        _wi("wi_dc_B",     1.074e-6)
        _wi("wi_dc_Tload", 2.493)

        # Grupo armadura
        _pgroup("Armadura")
        c1, c2 = st.columns(2)
        va = c1.number_input("$V_a$ (V)",  min_value=0.0, key="wi_dc_Va",  format="%.3f")
        ra = c2.number_input("$R_a$ (Ω)",  min_value=1e-6, key="wi_dc_Ra", format="%.4f")
        la = c1.number_input("$L_a$ (H)",  min_value=1e-6, key="wi_dc_La", format="%.4f")
        kb = c2.number_input("$k_b$ (V·s/rad)", min_value=1e-6, key="wi_dc_kb", format="%.4f")

        # Grupo campo (sep e shunt — não série)
        if not is_series:
            _pgroup("Campo")
            d1, d2 = st.columns(2)
            if is_sep:
                vf = d1.number_input("$V_f$ (V)",  min_value=0.0, key="wi_dc_Vf", format="%.3f")
            else:
                vf = va   # shunt: Vf = Va
                st.caption("Shunt: $V_f = V_a$ (fixo)")
            rf = d2.number_input("$R_f$ (Ω)",  min_value=1e-6, key="wi_dc_Rf", format="%.4f")
            lf = d1.number_input("$L_f$ (H)",  min_value=1e-6, key="wi_dc_Lf", format="%.4f")
        else:
            _pgroup("Campo (série com armadura)")
            e1, e2 = st.columns(2)
            rf = e1.number_input("$R_f$ (Ω)",  min_value=1e-6, key="wi_dc_Rf", format="%.4f")
            lf = e2.number_input("$L_f$ (H)",  min_value=1e-6, key="wi_dc_Lf", format="%.4f")
            vf = 0.0

        # Grupo carga elétrica (geradores)
        if is_gen:
            _pgroup("Carga Elétrica")
            f1, f2 = st.columns(2)
            rl = f1.number_input("$R_l$ (Ω)", min_value=1e-6, key="wi_dc_Rl", format="%.3f")
            ll = f2.number_input("$L_l$ (H)", min_value=0.0,  key="wi_dc_Ll", format="%.4f")
        else:
            rl = float(st.session_state.get("wi_dc_Rl", 0.0))
            ll = float(st.session_state.get("wi_dc_Ll", 0.0))

        # Grupo mecânico
        _pgroup("Mecânico")
        m1, m2, m3 = st.columns(3)
        J     = m1.number_input("$J$ (kg·m²)", min_value=1e-6, key="wi_dc_J",     format="%.4f")
        B     = m2.number_input("$B$ (N·m·s)",  min_value=0.0,  key="wi_dc_B",     format="%.2e")
        Tload = m3.number_input("$T_l$ (N·m)",  min_value=0.0,  key="wi_dc_Tload", format="%.4f")

    mp = DCMachineParams(
        Va=va, Ra=ra, La=la,
        Vf=vf, Rf=rf, Lf=lf,
        Rl=rl, Ll=ll,
        J=J, B=B, kb=kb,
        excitation=exc,
        Tload=Tload,
    )

    ref_code = hash((va, ra, la, vf, rf, lf, rl, ll, J, B, kb, exc, Tload))
    return mp, ref_code


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — EXPERIMENTO (col_circuit inferior)
# ─────────────────────────────────────────────────────────────────────────────

def render_experiment_config_dc(
    mp: DCMachineParams,
    _wk: Any = None,
) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    """Renderiza seletor de modo e parâmetros do experimento MCC.

    Retorna (exp_config, var_keys, var_labels, tmax, h).
    """
    st.markdown('<p class="slabel">Experimento</p>', unsafe_allow_html=True)

    exc = mp.excitation
    available_modes = _MODES_BY_EXC.get(exc, ["dol_dc"])
    mode_labels = [_MODE_LABELS[m] for m in available_modes]

    _wi("wi_dc_mode_idx", 0)
    mode_idx = st.selectbox(
        "Modo de Operação", mode_labels, index=0, key="_dc_mode_sel",
        label_visibility="visible",
    )
    mode_sel_label = st.session_state.get("_dc_mode_sel", mode_labels[0])
    mode = available_modes[mode_labels.index(mode_sel_label)] if mode_sel_label in mode_labels else available_modes[0]

    exp_config: dict[str, Any] = {"exp_type": mode, "exp_label": _MODE_LABELS[mode]}

    _pgroup("Parâmetros do Experimento")

    if mode == "dol_dc":
        tmax_def = 12.0
        h_def    = 1e-3

    elif mode == "resistencia_dc":
        c1, c2 = st.columns(2)
        _wi("wi_dc_R_ini", 5.0)
        _wi("wi_dc_t_ramp", 2.0)
        exp_config["R_ini"]  = c1.number_input("$R_{ini}$ (Ω)", min_value=0.0, key="wi_dc_R_ini",  format="%.2f")
        exp_config["t_ramp"] = c2.number_input("$t_{rampa}$ (s)", min_value=0.1, key="wi_dc_t_ramp", format="%.2f")
        tmax_def = exp_config["t_ramp"] + 8.0
        h_def    = 1e-3

    elif mode == "plugging_dc":
        _wi("wi_dc_t_freia", 3.0)
        exp_config["t_freia"] = st.number_input("$t_{freia}$ (s)", min_value=0.1, key="wi_dc_t_freia", format="%.2f")
        tmax_def = exp_config["t_freia"] * 2.5
        h_def    = 1e-3

    elif mode == "campo_fraco_dc":
        c1, c2, c3 = st.columns(3)
        _wi("wi_dc_Vf_fraco",  mp.Vf * 0.5)
        _wi("wi_dc_t_campo",   3.0)
        _wi("wi_dc_t_trans",   0.5)
        exp_config["Vf_fraco"] = c1.number_input("$V_f$ fraco (V)", min_value=0.0,
                                                   key="wi_dc_Vf_fraco", format="%.2f")
        exp_config["t_campo"]  = c2.number_input("$t_{campo}$ (s)", min_value=0.1,
                                                   key="wi_dc_t_campo", format="%.2f")
        exp_config["t_trans"]  = c3.number_input("$t_{trans}$ (s)", min_value=0.05,
                                                   key="wi_dc_t_trans", format="%.2f")
        tmax_def = exp_config["t_campo"] + 10.0
        h_def    = 1e-3

    elif mode == "pulso_dc":
        c1, c2 = st.columns(2)
        _wi("wi_dc_t_pulso",  4.0)
        _wi("wi_dc_Tl_extra", mp.Tload * 0.5)
        exp_config["t_pulso"]  = c1.number_input("$t_{pulso}$ (s)",     min_value=0.1, key="wi_dc_t_pulso",  format="%.2f")
        exp_config["Tl_extra"] = c2.number_input("$\\Delta T_l$ (N·m)", min_value=0.0, key="wi_dc_Tl_extra", format="%.3f")
        tmax_def = exp_config["t_pulso"] + 8.0
        h_def    = 1e-3

    elif mode == "gerador_dc":
        _wi("wi_dc_Tl_gen", abs(mp.Tload))
        exp_config["Tl_gen"] = st.number_input("$T_l$ gen (N·m)", min_value=0.0, key="wi_dc_Tl_gen", format="%.3f")
        tmax_def = 150.0
        h_def    = 5e-3
    else:
        tmax_def = 12.0
        h_def    = 1e-3

    # Tempo e passo
    _pgroup("Tempo de Simulação")
    tc1, tc2 = st.columns(2)
    _wi("wi_dc_tmax", tmax_def)
    _wi("wi_dc_h",    h_def)
    tmax = tc1.number_input("$t_{max}$ (s)",     min_value=0.1,  value=tmax_def, key="wi_dc_tmax", format="%.2f")
    h    = tc2.number_input("$h$ (s)",           min_value=1e-5, value=h_def,    key="wi_dc_h",    format="%.1e")

    # Variáveis a plotar
    st.markdown('<p class="slabel">Grandezas a Plotar</p>', unsafe_allow_html=True)
    _wi("wi_dc_vars", _DEFAULT_VARS)
    sel_labels = st.multiselect(
        "Grandezas",
        options=list(_VAR_OPTIONS.values()),
        default=[_VAR_OPTIONS[k] for k in _DEFAULT_VARS if k in _VAR_OPTIONS],
        key="wi_dc_vars_ms",
        label_visibility="collapsed",
    )
    label_to_key = {v: k for k, v in _VAR_OPTIONS.items()}
    var_keys   = [label_to_key[lb] for lb in sel_labels if lb in label_to_key]
    var_labels = [lb for lb in sel_labels if lb in label_to_key]

    if not var_keys:
        var_keys, var_labels = _DEFAULT_VARS, [_VAR_OPTIONS[k] for k in _DEFAULT_VARS]

    _ibox(f"<strong>Modo:</strong> {_MODE_LABELS[mode]} &nbsp;|&nbsp; "
          f"<strong>Excitação:</strong> {_EXC_LABELS.get(exc, exc)}")

    return exp_config, var_keys, var_labels, float(tmax), float(h)
