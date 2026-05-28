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

# Presets por excitação — fontes: Sen (2013), Fitzgerald/Umans (2014)
_PRESETS_BY_EXC: dict[str, dict[str, dict[str, Any]]] = {
    "sep_motor": {
        "Motor Sep. 220 V — Sen Ex. 9.2": {
            "Va": 220.0, "Ra": 0.5,   "La": 0.01,
            "Vf": 220.0, "Rf": 220.0, "Lf": 10.0,
            "kb": 1.05,  "J": 2.5,    "B": 0.05,   "Tload": 25.0,
        },
        "Motor Sep. 500 V 100 HP — Fitzgerald Ex. 10.2/10.3": {
            "Va": 500.0, "Ra": 0.084, "La": 0.01,
            "Vf": 300.0, "Rf": 109.0, "Lf": 5.0,
            "kb": 1.91,  "J": 17.5,   "B": 0.1,    "Tload": 286.0,
        },
    },
    "shunt_motor": {
        "Motor Shunt 100 V 12 kW — Sen Ex. 4.6": {
            "Va": 100.0, "Ra": 0.1,   "La": 0.01,
            "Rf": 101.0, "Lf": 5.0,
            "kb": 0.949, "J": 0.5,    "B": 0.054,  "Tload": 113.9,
        },
        "Motor Shunt 450 V 50 kW — Fitzgerald Ex. 7.4": {
            "Va": 450.0, "Ra": 0.242, "La": 0.02,
            "Rf": 167.0, "Lf": 8.0,
            "kb": 4.29,  "J": 5.0,    "B": 0.1,    "Tload": 497.0,
        },
    },
    "series_motor": {
        "Motor Série 220 V 7 HP — Sen Ex. 4.9": {
            "Va": 220.0, "Ra": 0.6,  "La": 0.02,
            "Rf": 0.4,   "Lf": 0.05,
            "kb": 6.2,   "J": 2.0,   "B": 0.05,   "Tload": 155.2,
        },
        "Motor Série 600 V Pesado — Sen Prob. 4.39": {
            "Va": 600.0, "Ra": 0.5,  "La": 0.05,
            "Rf": 0.5,   "Lf": 0.1,
            "kb": 10.02, "J": 10.0,  "B": 0.1,    "Tload": 751.5,
        },
    },
    "sep_gen": {
        "Gerador Sep. 200 V — Sen Ex. 9.1": {
            "Va": 200.0, "Ra": 0.25,  "La": 0.02,
            "Vf": 200.0, "Rf": 100.0, "Lf": 25.0,
            "kb": 1.91,  "J": 2.5,    "B": 0.1,    "Tload": -25.0,
            "Rl": 1.0,   "Ll": 0.15,
        },
        "Gerador Sep. 250 V 100 kW — Fitzgerald Ex. 7.1": {
            "Va": 250.0, "Ra": 0.025, "La": 0.005,
            "Vf": 250.0, "Rf": 100.0, "Lf": 5.0,
            "kb": 1.99,  "J": 10.0,   "B": 0.2,    "Tload": -800.0,
            "Rl": 0.625, "Ll": 0.05,
        },
    },
    "shunt_gen": {
        "Gerador Shunt 100 V 12 kW — Sen Ex. 4.2/4.3": {
            "Va": 100.0, "Ra": 0.1,   "La": 0.01,
            "Rf": 100.0, "Lf": 10.0,
            "kb": 0.95,  "J": 2.0,    "B": 0.05,   "Tload": -115.0,
            "Rl": 0.83,  "Ll": 0.01,
        },
        "Gerador Shunt 250 V 100 kW — Fitzgerald Ex. 7.7": {
            "Va": 250.0, "Ra": 0.025, "La": 0.005,
            "Rf": 100.0, "Lf": 5.0,
            "kb": 1.99,  "J": 10.0,   "B": 0.1,    "Tload": -800.0,
            "Rl": 0.625, "Ll": 0.05,
        },
    },
}

# Flat dict para compatibilidade legada (não usado na UI nova)
_PRESETS_DC: dict[str, dict[str, Any]] = {
    name: {**vals, "excitation": exc}
    for exc, presets in _PRESETS_BY_EXC.items()
    for name, vals in presets.items()
}

# Variáveis disponíveis para plotar por tipo de grandeza
_VAR_MECANICAS: dict[str, str] = {
    "Velocidade Angular  ωm  (rad/s)":       "wm",
    "Velocidade  n  (RPM)":                  "n",
    "Conjugado Eletromagnético  Tₑ  (N·m)":  "Te",
}

_VAR_ELETRICAS: dict[str, str] = {
    "Corrente de Armadura  iₐ  (A)":         "ia",
    "Corrente de Campo  i_fd  (A)":          "ifd",
    "FEM  Eₐ  (V)":                          "Ea",
    "Tensão de Terminal  Vt  (V)":           "Vt",
}

_VAR_OPTIONS: dict[str, str] = {**_VAR_MECANICAS, **_VAR_ELETRICAS}

_DEFAULT_VARS_MEC: list[str] = ["Conjugado Eletromagnético  Tₑ  (N·m)", "Velocidade  n  (RPM)"]
_DEFAULT_VARS_ELE: list[str] = ["Corrente de Armadura  iₐ  (A)"]
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

    # ── Preset loader — filtrado por excitação ───────────────────────────────
    if st.session_state.pop("_dc_reset_preset", False):
        st.session_state["wi_dc_preset"] = "— Selecionar preset —"

    _presets_exc = _PRESETS_BY_EXC.get(exc, {})
    _preset_names = ["— Selecionar preset —"] + list(_presets_exc.keys())
    pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
    with pc1:
        preset_sel = st.selectbox(
            "Preset", _preset_names, key="wi_dc_preset",
            label_visibility="collapsed",
            disabled=experiment_mode,
        )
    with pc2:
        if st.button("Carregar", key="btn_dc_load_preset", width="stretch",
                     disabled=(preset_sel == "— Selecionar preset —" or experiment_mode)):
            ps = _presets_exc[preset_sel]
            for k, v in ps.items():
                st.session_state[f"wi_dc_{k}"] = v
            st.session_state["_dc_reset_preset"] = True
            st.rerun()

    is_gen    = exc in ("sep_gen", "shunt_gen")
    is_sep    = exc in ("sep_motor", "sep_gen")
    is_series = exc == "series_motor"

    if experiment_mode:
        # Modo travado: resumo compacto com st.metric (igual padrão MIT)
        va    = float(st.session_state.get("wi_dc_Va",    24.0))
        ra    = float(st.session_state.get("wi_dc_Ra",    0.013))
        la    = float(st.session_state.get("wi_dc_La",    0.01))
        vf    = float(st.session_state.get("wi_dc_Vf",    va if not is_sep else 12.0))
        rf    = float(st.session_state.get("wi_dc_Rf",    1.43))
        lf    = float(st.session_state.get("wi_dc_Lf",    0.167))
        rl    = float(st.session_state.get("wi_dc_Rl",    0.0))
        ll    = float(st.session_state.get("wi_dc_Ll",    0.0))
        kb    = float(st.session_state.get("wi_dc_kb",    0.004))
        J     = float(st.session_state.get("wi_dc_J",     0.21))
        B     = float(st.session_state.get("wi_dc_B",     1.074e-6))
        Tload = float(st.session_state.get("wi_dc_Tload", 2.493))

        st.info(
            "**Parâmetros travados** — desative o toggle no topo da página para editar.  "
            "Variações no experimento (carga, tensão) não afetarão a máquina."
        )

        st.markdown('<p class="slabel">Parâmetros de Armadura</p>', unsafe_allow_html=True)
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Va (V)",       f"{va:.3f}")
        e2.metric("Ra (Ω)",       f"{ra:.4f}")
        e3.metric("La (H)",       f"{la:.4f}")
        e4.metric("kb (V·s/rad)", f"{kb:.4f}")

        if not is_series:
            st.markdown('<p class="slabel">Parâmetros de Campo</p>', unsafe_allow_html=True)
            f1, f2, f3 = st.columns(3)
            if is_sep:
                f1.metric("Vf (V)", f"{vf:.3f}")
            else:
                f1.metric("Vf = Va (V)", f"{va:.3f}")
            f2.metric("Rf (Ω)", f"{rf:.4f}")
            f3.metric("Lf (H)", f"{lf:.4f}")
        else:
            st.markdown('<p class="slabel">Campo (série)</p>', unsafe_allow_html=True)
            s1, s2 = st.columns(2)
            s1.metric("Rf_s (Ω)", f"{rf:.4f}")
            s2.metric("Lf_s (H)", f"{lf:.4f}")

        if is_gen:
            st.markdown('<p class="slabel">Carga Elétrica</p>', unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            g1.metric("Rl (Ω)", f"{rl:.3f}")
            g2.metric("Ll (H)", f"{ll:.4f}")

        st.markdown('<p class="slabel">Parâmetros Mecânicos</p>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("J (kg·m²)",   f"{J:.4f}")
        m2.metric("B (N·m·s)",   f"{B:.2e}")
        m3.metric("Tl (N·m)",    f"{Tload:.4f}")
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
        _pgroup("Dados de Armadura")
        va = st.number_input(
            "Tensão de armadura — $V_a$ (V)",
            min_value=0.0, key="wi_dc_Va", format="%.3f",
            help="Tensão CC aplicada ao enrolamento de armadura.",
        )
        ra = st.number_input(
            "Resistência de armadura — $R_a$ (Ω)",
            min_value=1e-6, key="wi_dc_Ra", format="%.4f",
            help="Resistência do enrolamento de armadura (inclui escovas). Afeta perdas Joule e corrente de partida.",
        )
        la = st.number_input(
            "Indutância de armadura — $L_a$ (H)",
            min_value=1e-6, key="wi_dc_La", format="%.4f",
            help="Indutância do circuito de armadura. Determina a constante de tempo elétrica τ_a = L_a / R_a.",
        )
        kb = st.number_input(
            "Constante de fcem — $k_b$ (V·s/rad)",
            min_value=1e-6, key="wi_dc_kb", format="%.4f",
            help="Relaciona fcem (Ea) e velocidade angular: Ea = kb · ωm. Também igual à constante de torque kt.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Grupo campo (sep e shunt — não série)
        if not is_series:
            _pgroup("Dados de Campo")
            if is_sep:
                vf = st.number_input(
                    "Tensão de campo — $V_f$ (V)",
                    min_value=0.0, key="wi_dc_Vf", format="%.3f",
                    help="Tensão da fonte independente de campo (excitação separada).",
                )
            else:
                vf = va   # shunt: Vf = Va
                st.caption("Shunt: $V_f = V_a$ (fixo — campo em paralelo com a armadura)")
            rf = st.number_input(
                "Resistência de campo — $R_f$ (Ω)",
                min_value=1e-6, key="wi_dc_Rf", format="%.4f",
                help="Resistência total do circuito de campo (enrolamento + reostato de campo).",
            )
            lf = st.number_input(
                "Indutância de campo — $L_f$ (H)",
                min_value=1e-6, key="wi_dc_Lf", format="%.4f",
                help="Indutância do enrolamento de campo. Determina τ_f = L_f / R_f.",
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            _pgroup("Campo (série com armadura)")
            rf = st.number_input(
                "Resistência do campo série — $R_s$ (Ω)",
                min_value=1e-6, key="wi_dc_Rf", format="%.4f",
                help="Resistência do enrolamento de campo série (em série com a armadura).",
            )
            lf = st.number_input(
                "Indutância do campo série — $L_s$ (H)",
                min_value=1e-6, key="wi_dc_Lf", format="%.4f",
                help="Indutância do enrolamento de campo série.",
            )
            vf = 0.0
            st.markdown('</div>', unsafe_allow_html=True)

        # Grupo carga elétrica (geradores)
        if is_gen:
            _pgroup("Carga Elétrica")
            rl = st.number_input(
                "Resistência de carga — $R_l$ (Ω)",
                min_value=1e-6, key="wi_dc_Rl", format="%.3f",
                help="Resistência da carga conectada ao gerador.",
            )
            ll = st.number_input(
                "Indutância de carga — $L_l$ (H)",
                min_value=0.0, key="wi_dc_Ll", format="%.4f",
                help="Indutância da carga conectada ao gerador (0 para carga puramente resistiva).",
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            rl = float(st.session_state.get("wi_dc_Rl", 0.0))
            ll = float(st.session_state.get("wi_dc_Ll", 0.0))

        # Grupo mecânico
        _pgroup("Dados Mecânicos")
        J = st.number_input(
            "Momento de inércia — $J$ (kg·m²)",
            min_value=1e-6, key="wi_dc_J", format="%.4f",
            help="Inércia total do conjunto motor + carga. Determina τ_m = J·Ra / kb².",
        )
        B = st.number_input(
            "Coef. de atrito viscoso — $B$ (N·m·s/rad)",
            min_value=0.0, key="wi_dc_B", format="%.2e",
            help="Coeficiente de atrito viscoso (friccional). Tipicamente muito pequeno.",
        )
        Tload = st.number_input(
            "Torque de carga — $T_l$ (N·m)",
            min_value=0.0, key="wi_dc_Tload", format="%.4f",
            help="Torque resistente de regime permanente aplicado ao eixo.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

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

def _tl_sugerido_dc(mp: DCMachineParams) -> float:
    """Torque nominal estimado: kb·ia_nominal, onde ia_nominal = (Va-kb·wm_nom)/Ra."""
    try:
        wm_nom = mp.Tload if mp.Tload > 0 else mp.Va / mp.kb if mp.kb > 0 else 100.0
        ia_nom = (mp.Va - mp.kb * wm_nom) / mp.Ra if mp.Ra > 0 else mp.Va / mp.Ra
        return float(max(abs(mp.kb * ia_nom), 0.01))
    except Exception:
        return float(abs(mp.Tload)) if mp.Tload else 1.0


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

    mode_sel_label = st.selectbox(
        "Tipo de Experimento", mode_labels, index=0, key="_dc_mode_sel",
        label_visibility="visible",
    )
    mode_sel_label = st.session_state.get("_dc_mode_sel", mode_labels[0])
    mode = available_modes[mode_labels.index(mode_sel_label)] if mode_sel_label in mode_labels else available_modes[0]

    exp_config: dict[str, Any] = {"exp_type": mode, "exp_label": _MODE_LABELS[mode]}

    _pgroup("Parâmetros de Carga e Tensão")

    _Tl_ref = float(st.session_state.get("wi_dc_Tload", mp.Tload))
    _tl_sug = _tl_sugerido_dc(mp)
    st.caption(f"Torque de carga configurado: **{_Tl_ref:.3f} N·m** | τ_a = L_a/R_a = {mp.La/mp.Ra:.4f} s")

    if mode == "dol_dc":
        tmax_def = 12.0
        h_def    = 1e-3
        partir_em_vazio = st.checkbox(
            "Partir em vazio (aplicar carga após partida)",
            value=True, key="wi_dc_dol_vazio",
            help="Quando ativo, o motor parte sem carga e recebe o torque em t_carga. "
                 "Quando inativo, a carga já está presente desde o instante zero.",
        )
        exp_config["partir_em_vazio"] = partir_em_vazio
        if partir_em_vazio:
            _wi("wi_dc_dol_t_carga", 2.0)
            exp_config["t_carga"] = st.number_input(
                "Instante de aplicação da carga — $t_{carga}$ (s)",
                min_value=0.0, key="wi_dc_dol_t_carga", format="%.2f",
            )
            exp_config["Tl_inicial"] = 0.0
            exp_config["Tl_final"]   = _Tl_ref
            tmax_def = max(exp_config["t_carga"] + 8.0, 12.0)
            _ibox(
                f"<strong>t = 0 s</strong> — tensão nominal ({mp.Va:.1f} V) aplicada; "
                f"motor acelera em vazio (T<sub>l</sub> = 0).<br>"
                f"<strong>t = {exp_config['t_carga']:.2f} s</strong> — carga de "
                f"<strong>{_Tl_ref:.3f} N·m</strong> aplicada ao eixo; "
                f"motor acomoda-se ao novo ponto de operação em regime permanente."
            )
        else:
            exp_config["Tl_inicial"] = None
            exp_config["Tl_final"]   = _Tl_ref
            exp_config["t_carga"]    = 0.0
            _ibox(
                f"<strong>t = 0 s</strong> — tensão nominal ({mp.Va:.1f} V) e carga de "
                f"<strong>{_Tl_ref:.3f} N·m</strong> aplicadas simultaneamente; "
                f"motor parte contra carga plena e acelera até o regime permanente."
            )

    elif mode == "resistencia_dc":
        c1, c2 = st.columns(2)
        _wi("wi_dc_R_ini", 5.0)
        _wi("wi_dc_t_ramp", 2.0)
        exp_config["R_ini"]  = c1.number_input("$R_{ini}$ (Ω)", min_value=0.0, key="wi_dc_R_ini",  format="%.2f")
        exp_config["t_ramp"] = c2.number_input("$t_{rampa}$ (s)", min_value=0.1, key="wi_dc_t_ramp", format="%.2f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_ramp"] + 8.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte com resistência série de "
            f"<strong>{exp_config['R_ini']:.2f} Ω</strong> limitando a corrente de partida.<br>"
            f"<strong>t = {exp_config['t_ramp']:.2f} s</strong> — resistência removida (curto-circuitada); "
            f"motor acelera até o regime permanente com carga de {_Tl_ref:.3f} N·m."
        )

    elif mode == "plugging_dc":
        _wi("wi_dc_t_freia", 3.0)
        exp_config["t_freia"]  = st.number_input("Instante de reversão — $t_{freia}$ (s)", min_value=0.1, key="wi_dc_t_freia", format="%.2f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_freia"] * 2.5
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte em sentido positivo com carga de {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — polaridade de armadura invertida (plugging); "
            f"torque de frenagem somado à carga; rotor desacelera e inverte o sentido de rotação."
        )

    elif mode == "campo_fraco_dc":
        c1, c2, c3 = st.columns(3)
        _wi("wi_dc_Vf_fraco",  mp.Vf * 0.5 if mp.Vf > 0 else mp.Va * 0.5)
        _wi("wi_dc_t_campo",   3.0)
        _wi("wi_dc_t_trans",   0.5)
        exp_config["Vf_fraco"] = c1.number_input("$V_f$ fraco (V)", min_value=0.0,
                                                   key="wi_dc_Vf_fraco", format="%.2f")
        exp_config["t_campo"]  = c2.number_input("$t_{campo}$ (s)", min_value=0.1,
                                                   key="wi_dc_t_campo", format="%.2f")
        exp_config["t_trans"]  = c3.number_input("$t_{trans}$ (s)", min_value=0.05,
                                                   key="wi_dc_t_trans", format="%.2f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_campo"] + 10.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor opera em campo nominal; carga de {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {exp_config['t_campo']:.2f} s</strong> — tensão de campo reduzida para "
            f"<strong>{exp_config['Vf_fraco']:.2f} V</strong> (enfraquecimento de campo); "
            f"fluxo cai, velocidade aumenta para manter a potência — transitório de {exp_config['t_trans']:.2f} s."
        )

    elif mode == "pulso_dc":
        c1, c2 = st.columns(2)
        _wi("wi_dc_t_pulso",  4.0)
        _wi("wi_dc_Tl_extra", _Tl_ref * 0.5)
        exp_config["t_pulso"]  = c1.number_input("Instante do pulso — $t_{pulso}$ (s)", min_value=0.1, key="wi_dc_t_pulso",  format="%.2f")
        exp_config["Tl_extra"] = c2.number_input("$\\Delta T_l$ adicional (N·m)", min_value=0.0, key="wi_dc_Tl_extra", format="%.3f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_pulso"] + 8.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor opera em regime com carga de {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {exp_config['t_pulso']:.2f} s</strong> — pulso de carga adicional de "
            f"<strong>{exp_config['Tl_extra']:.3f} N·m</strong> aplicado; motor desacelera e acomoda-se.<br>"
            f"<strong>t = {exp_config['t_pulso']*2:.2f} s</strong> — pulso retirado; motor recupera velocidade de regime."
        )

    elif mode == "gerador_dc":
        _wi("wi_dc_Tl_gen", abs(mp.Tload))
        exp_config["Tl_gen"] = st.number_input("Torque mecânico da primomotriz — $T_{mec}$ (N·m)", min_value=0.0, key="wi_dc_Tl_gen", format="%.3f")
        tmax_def = 15.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — máquina acelerada pela primomotriz com torque de "
            f"<strong>{exp_config['Tl_gen']:.3f} N·m</strong>; campo excitado.<br>"
            f"<strong>Regime</strong> — tensão de terminal $V_t$ se estabiliza; carga resistiva $R_L$ recebe potência gerada."
        )
    else:
        tmax_def = 12.0
        h_def    = 1e-3

    st.markdown('</div>', unsafe_allow_html=True)

    # Variáveis para visualização — separadas em Mecânicas / Elétricas (igual MIT)
    st.write("")
    st.markdown('<p class="slabel">Variáveis para Visualização</p>', unsafe_allow_html=True)
    _pgroup("Grandezas Mecânicas")
    sel_mec = st.multiselect(
        "Grandezas mecânicas",
        options=list(_VAR_MECANICAS.keys()),
        default=_DEFAULT_VARS_MEC,
        label_visibility="collapsed",
        key="wi_dc_vars_mec",
    )
    _pgroup("Grandezas Elétricas")
    sel_ele = st.multiselect(
        "Grandezas elétricas",
        options=list(_VAR_ELETRICAS.keys()),
        default=_DEFAULT_VARS_ELE,
        label_visibility="collapsed",
        key="wi_dc_vars_ele",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    selected_labels = sel_mec + sel_ele
    var_keys   = [_VAR_OPTIONS[v] for v in selected_labels if v in _VAR_OPTIONS]
    var_labels = [v for v in selected_labels if v in _VAR_OPTIONS]
    if not var_keys:
        var_keys   = _DEFAULT_VARS
        var_labels = [k for k, v in _VAR_OPTIONS.items() if v in _DEFAULT_VARS]

    # Parâmetros numéricos da simulação
    st.write("")
    st.markdown('<p class="slabel">Parâmetros Numéricos da Simulação</p>', unsafe_allow_html=True)
    _pgroup("Tempo Total e Passo de Integração")

    _t_acomo = float(min(max(15.0 * mp.J, 2.0), 30.0))
    _tmax_auto_val = round(tmax_def + _t_acomo, 1)

    tc1, tc2 = st.columns(2)
    with tc1:
        _tmax_auto = st.checkbox("Calcular tmax automaticamente (inércia do motor)", value=True, key="wi_dc_tmax_auto")
        _wi("wi_dc_tmax", tmax_def)
        tmax = st.number_input("Tempo total — $t_{max}$ (s)", min_value=0.001, max_value=3600.0,
                                value=tmax_def, step=0.1, format="%.1f",
                                key="wi_dc_tmax", disabled=_tmax_auto)
        if _tmax_auto:
            tmax = 0.0  # sentinel: runner resolve
            st.caption(f"Automático: **{_tmax_auto_val:.1f} s**  (modo + {_t_acomo:.1f} s de acomodação mecânica, J={mp.J:.4f} kg·m²)")
        else:
            st.caption(f"Sugestão: ≥ {round(tmax_def + 0.5, 1):.1f} s  (último evento + 0,5 s para atingir regime)")

        _wi("wi_dc_h", h_def)
        h = st.number_input("Passo de integração — $h$ (s)", min_value=1e-6, max_value=0.1,
                             value=h_def, step=1e-4, format="%.6f", key="wi_dc_h")

        _tmax_display = _tmax_auto_val if _tmax_auto else tmax
        n_steps = int(_tmax_display / h) if (_tmax_display > 0 and h > 0) else 0
        st.caption(f"Total de passos: {n_steps:,}")
        if n_steps > 500_000:
            st.warning("Número elevado de passos. A simulação pode demorar vários segundos.")

        # Validação: evento crítico não coberto por tmax
        if not _tmax_auto:
            _tmax_check = tmax
            _critical_dc: list[tuple[str, str, float]] = []
            if mode == "dol_dc" and exp_config.get("partir_em_vazio"):
                _critical_dc = [("aplicação da carga", "t_{carga}", exp_config.get("t_carga", 0))]
            elif mode == "resistencia_dc":
                _critical_dc = [("remoção da resistência", "t_{rampa}", exp_config.get("t_ramp", 0))]
            elif mode == "plugging_dc":
                _critical_dc = [("reversão de polaridade", "t_{freia}", exp_config.get("t_freia", 0))]
            elif mode == "campo_fraco_dc":
                _critical_dc = [("enfraquecimento de campo", "t_{campo}", exp_config.get("t_campo", 0))]
            elif mode == "pulso_dc":
                _critical_dc = [("pulso de carga", "t_{pulso}", exp_config.get("t_pulso", 0))]
            for _lbl, _sym, _t in _critical_dc:
                if _t >= _tmax_check:
                    st.warning(
                        f"$t_{{max}}$ ({_tmax_check:.2f} s) ≤ ${_sym}$ ({_t:.2f} s): "
                        f"o evento de **{_lbl}** não ocorrerá na simulação — aumente $t_{{max}}$."
                    )

    with tc2:
        _ibox(
            "<strong>t<sub>max</sub>:</strong> quanto maior, mais do transitório é capturado, "
            "porém maior o custo computacional.<br><br>"
            "<strong>h (passo):</strong> para MCC, recomenda-se h ≤ τ<sub>a</sub>/10, "
            "onde τ<sub>a</sub> = L<sub>a</sub>/R<sub>a</sub> é a constante de tempo elétrica da armadura."
        )

    exp_config["_tmax_auto_val"] = _tmax_auto_val

    _ibox(f"<strong>Modo:</strong> {_MODE_LABELS[mode]} &nbsp;|&nbsp; "
          f"<strong>Excitação:</strong> {_EXC_LABELS.get(exc, exc)}")

    return exp_config, var_keys, var_labels, float(tmax), float(h)
