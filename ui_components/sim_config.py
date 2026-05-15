# -*- coding: utf-8 -*-
"""Configuração e inputs da simulação — parâmetros da máquina e experimento.

Exporta:
    _WK                     — mapeamento campo lógico → key do widget
    VARIABLE_CATALOG        — catálogo completo de variáveis plotáveis
    VARIABLE_CATALOG_MECANICAS
    VARIABLE_CATALOG_ELETRICAS
    render_machine_selector — tela de seleção de equipamento
    render_machine_params   — coluna de parâmetros físicos
    render_experiment_config — configuração do experimento e variáveis
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import streamlit as st

from core.EMS_PY import MachineParams
from core.desequilibrio_falta import render_desequilibrio_ui, render_broken_bar_ui
from core.param_estimator import estimate_params, estimate_params_ieee_tests
from ui.theme import _palette
from ui_components.sim_runner import calc_tmax_auto


@st.cache_data(show_spinner=False)
def _cached_estimate_params(
    Vl: float, f: float, Pn_kW: float, N_nom: float,
    rend: float, fp: float, Ip_In: float, Tp_Tn: float, is_delta: bool,
) -> dict:
    return estimate_params(Vl, f, 0, Pn_kW, N_nom, rend, fp, Ip_In, Tp_Tn, is_delta=is_delta)


@st.cache_data(show_spinner=False)
def _cached_estimate_ieee(
    V_dc: float, I_dc: float, is_delta: bool,
    Vl_nl: float, I_nl: float, P_nl: float, f_nl: float,
    Vl_lr: float, I_lr: float, P_lr: float, f_lr: float,
    Pfw: float, split: str, Xls_frac: float,
) -> dict:
    return estimate_params_ieee_tests(
        V_dc, I_dc, is_delta, Vl_nl, I_nl, P_nl, f_nl,
        Vl_lr, I_lr, P_lr, f_lr, Pfw, split, Xls_frac,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGOS DE VARIÁVEIS
# ─────────────────────────────────────────────────────────────────────────────

VARIABLE_CATALOG_MECANICAS: dict[str, str] = {
    "Torque Eletromagnético  Tₑ  (N·m)":  "Te",
    "Velocidade do Rotor  n  (RPM)":       "n",
    "Velocidade Angular  ωᵣ  (rad/s)":     "wr",
}

VARIABLE_CATALOG_ELETRICAS: dict[str, str] = {
    "Corrente de Fase A — Estator  iₐₛ  (A)":  "ias",
    "Corrente de Fase B — Estator  ibₛ  (A)":  "ibs",
    "Corrente de Fase C — Estator  icₛ  (A)":  "ics",
    "Corrente de Fase A — Rotor  iₐᵣ  (A)":    "iar",
    "Corrente de Fase B — Rotor  ibᵣ  (A)":    "ibr",
    "Corrente de Fase C — Rotor  icᵣ  (A)":    "icr",
    "Componente d — Estator  idₛ  (A)":         "ids",
    "Componente q — Estator  iqₛ  (A)":         "iqs",
    "Componente d — Rotor  idᵣ  (A)":           "idr",
    "Componente q — Rotor  iqᵣ  (A)":           "iqr",
    "Tensão de Fase  Vₐ  (V)":                  "Va",
    "Tensão de Fase  Vb  (V)":                  "Vb",
    "Tensão de Fase  Vc  (V)":                  "Vc",
}

VARIABLE_CATALOG: dict[str, str] = {
    **VARIABLE_CATALOG_MECANICAS,
    **VARIABLE_CATALOG_ELETRICAS,
}


# ─────────────────────────────────────────────────────────────────────────────
# MAPEAMENTO CAMPO LÓGICO → KEY DO WIDGET
# ─────────────────────────────────────────────────────────────────────────────

_WK: dict[str, str] = {
    "Vl":           "wi_Vl",
    "f":            "wi_f",
    "Rs":           "wi_Rs",
    "Rr":           "wi_Rr",
    "input_mode":   "wi_input_mode",
    "f_ref":        "wi_f_ref",
    "Xm":           "wi_Xm",       # reatância (Ω) no modo X
    "Xls":          "wi_Xls",
    "Xlr":          "wi_Xlr",
    "Xm_L":         "wi_Xm_L",    # indutância (H) no modo L
    "Xls_L":        "wi_Xls_L",
    "Xlr_L":        "wi_Xlr_L",
    "Rfe":          "wi_Rfe",
    "p":            "wi_p",
    "J":            "wi_J",
    "B":            "wi_B",
    # experimento
    "exp_type":     "exp_select",
    "Tl_final":     "wi_Tl_final",
    "t_carga":      "wi_t_carga",
    "Tl_pulso":     "wi_Tl_pulso",
    "Tl_pulso_abs": "wi_Tl_pulso_abs",
    "t_pulso_on":   "wi_t_pulso_on",
    "t_pulso_off":  "wi_t_pulso_off",
    "Tl_mec":       "wi_Tl_mec",
    "t_2_gerador":  "wi_t_2_gerador",
    "tmax":         "wi_tmax",
    "h":            "wi_h",
    # modelos avançados
    "Rgrid":                "wi_Rgrid",
    "Lgrid":                "wi_Lgrid",
    # gêmeo digital e análise econômica
    "broken_bar_severity":  "wi_broken_bar_severity",
    "energy_tariff":        "wi_energy_tariff",
    # voltage sag
    "sag_magnitude":        "wi_sag_magnitude",
    "t_start_sag":          "wi_t_start_sag",
    "t_duration_sag":       "wi_t_duration_sag",
    "sag_Tl":               "wi_sag_Tl",
    # estimador de placa
    "param_source": "wi_param_source",
    "Pn_kW":    "wi_Pn_kW",
    "N_nom":    "wi_N_nom",
    "rend":     "wi_rend",
    "fp_placa": "wi_fp_placa",
    "Ip_In":    "wi_Ip_In",
    "Tp_Tn":    "wi_Tp_Tn",
    "is_delta": "wi_is_delta",
    # estimador IEEE 112 — ensaios físicos
    "ieee_split":    "wi_ieee_split",
    "ieee_Xls_frac": "wi_ieee_Xls_frac",
    "ieee_Pfw":      "wi_ieee_Pfw",
    "ieee_V_dc":     "wi_ieee_V_dc",
    "ieee_I_dc":     "wi_ieee_I_dc",
    "ieee_Vl_nl":    "wi_ieee_Vl_nl",
    "ieee_I_nl":     "wi_ieee_I_nl",
    "ieee_P_nl":     "wi_ieee_P_nl",
    "ieee_f_nl":     "wi_ieee_f_nl",
    "ieee_Vl_lr":    "wi_ieee_Vl_lr",
    "ieee_I_lr":     "wi_ieee_I_lr",
    "ieee_P_lr":     "wi_ieee_P_lr",
    "ieee_f_lr":     "wi_ieee_f_lr",
}


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULTS E PRESETS
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, float | int] = dict(
    Vl=220.0, f=60.0, Rs=0.435, Rr=0.816, Xm=26.13,
    Xls=0.754, Xlr=0.754, Rfe=500.0, p=4, J=0.089, B=0.005,
)

_INPUT_MODE_LABELS: list[str] = [
    "Reatâncias (Ω)  —  medidas em $f_{ref}$",
    "Indutâncias (H)  —  independentes de frequência",
]

_PARAM_SOURCE_LABELS: list[str] = [
    "Inserir parâmetros manualmente",
    "Estimar por dados de placa (Nameplate)",
    "Determinar por Ensaios IEEE 112",
]

_IEEE_SPLIT_LABELS: dict[str, str] = {
    "B":      "Classe B — 40% / 60% (padrão NEMA)",
    "A":      "Classe A — 50% / 50%",
    "C":      "Classe C — 30% / 70%",
    "D":      "Classe D — 50% / 50%",
    "WR":     "Rotor Bobinado — 50% / 50%",
    "custom": "Personalizada (definir fração Xls/Xk)",
}

_PRESETS: dict[str, dict[str, Any]] = {
    "Padrão — Krause 3 HP (2.2 kW / 12 N·m) 220 V/60 Hz": {
        # Krause (2002) — motor de indução 220 V / 60 Hz / 4 polos / ~3 cv
        # Rfe = 400 Ω: perdas no ferro ≈ 3×(127²/400) ≈ 121 W (~5.5% de potência nominal)
        # T_nom = P_nom / ω_r = 2200 / (1746×π/30) ≈ 12 N·m
        "Vl": 220.0, "f": 60.0, "Rs": 0.435, "Rr": 0.816,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 26.13, "Xls": 0.754, "Xlr": 0.754, "Rfe": 400.0,
        "p": 4, "J": 0.089, "B": 0.005,
        "exp_type": "Partida Direta (DOL)",
        "Tl_final": 12.0,
    },
    "Usta (2024) — 0.37 kW (2.4 N·m) 220 V/50 Hz": {
        # Motor de laboratório 220 V / 50 Hz / 4 polos / ~0.37 kW
        # Rfe = 800 Ω: motor pequeno com menor volume de ferro — perdas relativas menores
        # T_nom = 370 / (1455×π/30) ≈ 2.4 N·m
        "Vl": 220.0, "f": 50.0, "Rs": 2.65, "Rr": 2.85,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 50.0, "Xm": 60.98, "Xls": 4.43, "Xlr": 5.69, "Rfe": 800.0,
        "p": 4, "J": 0.025, "B": 0.001,
        "exp_type": "Pulso de Carga (aplica e retira)",
        "Tl_pulso": 0.0, "Tl_pulso_abs": 2.4, "t_pulso_on": 0.6, "t_pulso_off": 0.8,
        "tmax": 1.0,
        "Tl_final": 2.4,
    },
    "Krause 50 HP (37 kW / 202 N·m) — 460 V/60 Hz": {
        # Krause (2002) — motor industrial médio porte, 460 V / 60 Hz / 4 polos / 50 cv
        # Rfe = 150 Ω: núcleo maior, perdas absolutas maiores mas Rfe menor
        # T_nom = 37000 / (1746×π/30) ≈ 202 N·m
        "Vl": 460.0, "f": 60.0, "Rs": 0.087, "Rr": 0.228,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 13.08, "Xls": 0.302, "Xlr": 0.302, "Rfe": 150.0,
        "p": 4, "J": 1.662, "B": 0.0,
        "exp_type": "Partida Direta (DOL)",
        "Tl_final": 202.0,
    },
    "Krause 2250 HP (1678 kW / 9180 N·m) — 2300 V/60 Hz": {
        # Krause (2002) — motor de grande porte, média tensão, 2300 V / 60 Hz / 4 polos
        # Rfe = 80 Ω: núcleo de grande volume, alta corrente de excitação
        # T_nom = 1678000 / (1746×π/30) ≈ 9180 N·m
        # t_carga = 8 s: J = 63.87 kg·m² exige ~6–8 s para atingir 95% de n_s em DOL
        "Vl": 2300.0, "f": 60.0, "Rs": 0.029, "Rr": 0.022,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 13.04, "Xls": 0.226, "Xlr": 0.226, "Rfe": 80.0,
        "p": 4, "J": 63.87, "B": 0.05,
        "exp_type": "Partida Direta (DOL)",
        "Tl_final": 9180.0, "t_carga": 8.0,
    },
}

# Definição das máquinas disponíveis
MACHINES: list[dict[str, Any]] = [
    {"key": "mit",  "name": "Motor de Indução Trifásico",  "icon": "MIT", "tag": "Disponível",        "disabled": False},
    {"key": "sync", "name": "Gerador Sincrono",             "icon": "GS",  "tag": "Em desenvolvimento", "disabled": True},
    {"key": "dc",   "name": "Motor de Corrente Continua",  "icon": "MCC", "tag": "Em desenvolvimento", "disabled": True},
    {"key": "tr",   "name": "Transformador",                "icon": "TR",  "tag": "Em desenvolvimento", "disabled": True},
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE RENDERIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _pgroup(title: str) -> None:
    st.markdown(f'<div class="pgroup-title">{title}</div>', unsafe_allow_html=True)


def _ibox(html: str) -> None:
    st.markdown(f'<div class="ibox">{html}</div>', unsafe_allow_html=True)


def _Te_rotor_bloqueado(mp: MachineParams, voltage_ratio: float) -> float:
    """Torque eletromagnético em rotor bloqueado (s=1) para tensão reduzida.

    Usa o circuito equivalente em T sem Rfe (conservador — Rfe eleva Te ligeiramente).
    Te(s=1) = (3·p/2) / wb · Vf² · Rr / [(Rs+Rr)² + (Xls+Xlr)²]
    O fator k² de tensão reduzida é aplicado via Vf_red = k · Vf.
    """
    Vf   = mp.Vl / np.sqrt(3.0)
    Vf_r = Vf * voltage_ratio
    Zr2  = (mp.Rs + mp.Rr) ** 2 + (mp.Xls_a + mp.Xlr_a) ** 2
    if Zr2 == 0.0:
        return 0.0
    return (3.0 * (mp.p / 2) / mp.wb) * (Vf_r ** 2) * mp.Rr / Zr2


def _aviso_partida_reduzida(mp: MachineParams, voltage_ratio: float, Tl: float) -> None:
    """Exibe aviso de viabilidade de partida com tensão reduzida."""
    Te_bloq = _Te_rotor_bloqueado(mp, voltage_ratio)
    Te_nom  = _Te_rotor_bloqueado(mp, 1.0)
    if Tl <= 0.0:
        st.caption(
            f"Torque de partida estimado (rotor bloqueado): **{Te_bloq:.1f} N·m** "
            f"({voltage_ratio*100:.0f}% de tensão → {voltage_ratio**2*100:.0f}% de T_e,bloq nominal {Te_nom:.1f} N·m)."
        )
        return
    margem = (Te_bloq / Tl - 1.0) * 100.0
    if Te_bloq < Tl:
        st.error(
            f"Torque de partida estimado **{Te_bloq:.1f} N·m** < carga **{Tl:.1f} N·m** — "
            f"o motor **pode não partir** com esta tensão reduzida. "
            f"Aumente o tap/tensão inicial ou reduza a carga."
        )
    elif margem < 20.0:
        st.warning(
            f"Torque de partida estimado **{Te_bloq:.1f} N·m** — margem estreita de **+{margem:.0f}%** "
            f"sobre a carga de {Tl:.1f} N·m. A partida pode falhar com variações de rede ou atrito estático."
        )
    else:
        st.success(
            f"Partida viável — torque de partida estimado **{Te_bloq:.1f} N·m** "
            f"(margem de **+{margem:.0f}%** sobre a carga de {Tl:.1f} N·m)."
        )


def _validate_params(mp: MachineParams) -> None:
    """Emite avisos na UI quando parâmetros estão fora de faixas fisicamente plausíveis."""
    warns: list[str] = []
    rs_rr = mp.Rs / mp.Rr if mp.Rr else float("inf")
    if not (0.1 <= rs_rr <= 10):
        warns.append(f"Razão $R_s/R_r$ = {rs_rr:.2f} está fora da faixa típica [0.1, 10]. Verifique os valores.")
    xm_xls = mp.Xm / mp.Xls if mp.Xls else float("inf")
    if not (5 <= xm_xls <= 200):
        warns.append(f"Razão $X_m/X_{{ls}}$ = {xm_xls:.1f} está fora da faixa típica [5, 200]. Verifique os parâmetros magnéticos.")
    tau_e_ms = (mp.Lm / mp.Rr * 1000) if mp.Rr else float("inf")
    if tau_e_ms < 0.5:
        warns.append(f"Constante de tempo elétrica $\\tau_e$ ≈ {tau_e_ms:.2f} ms (< 0.5 ms). Passo $h$ muito pequeno pode ser necessário.")
    if mp.Xm > 0:
        _xls_ratio = mp.Xls_a / mp.Xm
        _xlr_ratio = mp.Xlr_a / mp.Xm
        if _xls_ratio < 0.01:
            warns.append(
                f"$X_{{ls}}$ = {mp.Xls:.5f} Ω parece muito pequeno "
                f"($X_{{ls}}/X_m$ = {_xls_ratio*100:.3f}%, típico: 2–15%). "
                "Verifique se inseriu indutância (H) em vez de reatância (Ω) — "
                "valores errados causam explosão de correntes e temperatura."
            )
        if _xlr_ratio < 0.01:
            warns.append(
                f"$X_{{lr}}$ = {mp.Xlr:.5f} Ω parece muito pequeno "
                f"($X_{{lr}}/X_m$ = {_xlr_ratio*100:.3f}%, típico: 2–15%). "
                "Verifique se inseriu indutância (H) em vez de reatância (Ω) — "
                "valores errados causam explosão de correntes e temperatura."
            )
    for w in warns:
        st.warning(w)


# ─────────────────────────────────────────────────────────────────────────────
# SELEÇÃO DE MÁQUINA
# ─────────────────────────────────────────────────────────────────────────────

def render_machine_selector(dark: bool) -> None:
    """Tela inicial de seleção de equipamento."""
    _palette(dark)
    ct_theme, _ = st.columns([1, 6])
    with ct_theme:
        st.toggle("Modo Escuro", value=dark, key="dark_mode")

    # apenas máquinas disponíveis são exibidas
    available = [m for m in MACHINES if not m["disabled"]]

    st.markdown('<p class="slabel">ElectraSim</p>', unsafe_allow_html=True)
    st.markdown("### Selecione o equipamento")
    st.write("")

    # grade centralizada: CSS "machine-grid-solo" para 1 card centrado
    cards_html = '<div class="machine-grid-solo">'
    for m in available:
        active  = st.session_state.get("selected_machine") == m["key"]
        cls     = "mcard mcard-solo" + (" active" if active else "")
        cards_html += (
            f'<div class="{cls}">'
            f'  <span class="mcard-icon">{m["icon"]}</span>'
            f'  <div class="mcard-name">{m["name"]}</div>'
            f'  <span class="mcard-tag">{m["tag"]}</span>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)
    st.write("")

    # botão centralizado
    _, btn_col, _ = st.columns([2, 1, 2])
    for m in available:
        with btn_col:
            if st.button("Iniciar Simulação", key=f"sel_{m['key']}", width="stretch"):
                st.session_state["selected_machine"] = m["key"]
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PARÂMETROS FÍSICOS DA MÁQUINA
# ─────────────────────────────────────────────────────────────────────────────

def render_machine_params(
    dark: bool,
    experiment_mode: bool,
    wk: dict[str, str] = _WK,
) -> tuple[MachineParams, int]:
    """Coluna esquerda: todos os campos de parâmetros. Retorna (mp, ref_code).

    Args:
        dark: tema escuro ativo.
        experiment_mode: quando True trava todos os inputs.
        wk: mapeamento campo lógico → key do widget (usa _WK por padrão).
    """
    st.markdown('<p class="slabel">Parâmetros Físicos da Máquina</p>', unsafe_allow_html=True)

    # Reset do selectbox de preset deve ocorrer ANTES de instanciar o widget
    if st.session_state.pop("_reset_preset_select", False):
        st.session_state["preset_select"] = "— Selecionar preset —"

    pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
    with pc1:
        preset_sel = st.selectbox(
            "Preset",
            ["— Selecionar preset —"] + list(_PRESETS.keys()),
            label_visibility="collapsed",
            key="preset_select",
        )
    with pc2:
        if st.button("Carregar", key="btn_load_preset", width="stretch",
                     disabled=(preset_sel == "— Selecionar preset —")):
            pdata = _PRESETS[preset_sel]
            _wk_preset = {
                "Vl": wk["Vl"], "f": wk["f"], "Rs": wk["Rs"], "Rr": wk["Rr"],
                "input_mode": wk["input_mode"], "f_ref": wk["f_ref"],
                "Xm": wk["Xm"], "Xls": wk["Xls"], "Xlr": wk["Xlr"],
                "Rfe": wk["Rfe"], "p": wk["p"], "J": wk["J"], "B": wk["B"],
                "exp_type": wk["exp_type"],
                "Tl_final": wk["Tl_final"],
                "Tl_pulso": wk["Tl_pulso"],
                "Tl_pulso_abs": wk["Tl_pulso_abs"],
                "t_pulso_on": wk["t_pulso_on"],
                "t_pulso_off": wk["t_pulso_off"],
                "t_carga": wk["t_carga"],
                "tmax": wk["tmax"],
            }
            for key, widget_key in _wk_preset.items():
                if key in pdata:
                    st.session_state[widget_key] = pdata[key]
            st.session_state[wk["param_source"]] = _PARAM_SOURCE_LABELS[0]
            st.session_state["_reset_preset_select"] = True
            st.rerun()

    if experiment_mode:
        _ibox("<strong>Parâmetros travados</strong> — desative o toggle para editar.")

    dis = experiment_mode

    # ── Seleção da fonte de parâmetros ────────────────────────────────────
    param_source_label = st.radio(
        "Fonte dos parâmetros do motor",
        _PARAM_SOURCE_LABELS,
        index=0,
        key=wk["param_source"],
        disabled=dis,
        horizontal=True,
    )
    use_placa = param_source_label.startswith("Estimar")
    use_ieee  = param_source_label.startswith("Determinar")
    if use_placa:
        input_mode_original = "PLACA"
    elif use_ieee:
        input_mode_original = "IEEE"
    else:
        input_mode_original = "MANUAL"

    if use_placa:
        # ══════════════════════════════════════════════════════════════════
        # MODO PLACA — todos os parâmetros deduzidos da nameplate
        # ══════════════════════════════════════════════════════════════════
        _pgroup("Dados de Rede")
        Vl = st.number_input("Tensão de linha RMS — $V_l$ (V)", min_value=50.0, max_value=15000.0, value=_DEFAULTS["Vl"], step=1.0, key=wk["Vl"], disabled=dis)
        f  = st.number_input("Frequência da rede — $f$ (Hz)",   min_value=1.0,  max_value=400.0,   value=_DEFAULTS["f"],  step=1.0, key=wk["f"],  disabled=dis)
        is_delta = st.checkbox(
            "Ligação em Triângulo (Δ) — desmarque para Estrela (Y)",
            value=False, key=wk["is_delta"], disabled=dis,
            help="Afeta a tensão de fase e a corrente de fase usadas no cálculo do circuito equivalente.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        _pgroup("Dados de Placa (Nameplate)")
        Pn_kW = st.number_input(
            "Potência nominal no eixo (kW)",
            min_value=0.01, max_value=10000.0, value=2.2, step=0.1, format="%.2f",
            key=wk["Pn_kW"], disabled=dis,
            help="Potência mecânica nominal na flange do motor (valor da placa).",
        )
        N_nom = st.number_input(
            "Velocidade nominal (RPM)",
            min_value=1.0, max_value=60000.0, value=1746.0, step=1.0, format="%.0f",
            key=wk["N_nom"], disabled=dis,
            help="Rotação em plena carga nominal. O número de polos é deduzido automaticamente.",
        )
        rend_placa = st.number_input(
            "Rendimento nominal η (ex: 0.91)",
            min_value=0.01, max_value=0.999, value=0.85, step=0.01, format="%.3f",
            key=wk["rend"], disabled=dis,
            help="Eficiência em plena carga — η = P_eixo / P_elétrica.",
        )
        fp_placa = st.number_input(
            "Fator de potência nominal cos(φ) (ex: 0.85)",
            min_value=0.01, max_value=0.999, value=0.85, step=0.01, format="%.3f",
            key=wk["fp_placa"], disabled=dis,
            help="cos(φ) em plena carga nominal.",
        )
        Ip_In = st.number_input(
            "Relação corrente de partida / nominal  (Ip/In)",
            min_value=1.0, max_value=15.0, value=6.0, step=0.1, format="%.1f",
            key=wk["Ip_In"], disabled=dis,
            help="Corrente de partida DOL em múltiplos da corrente nominal (tipicamente 5–8 para NEMA B).",
        )
        Tp_Tn = st.number_input(
            "Relação torque de partida / nominal  (Tp/Tn)",
            min_value=0.1, max_value=5.0, value=1.5, step=0.1, format="%.2f",
            key=wk["Tp_Tn"], disabled=dis,
            help="Torque de partida (s=1) em múltiplos do torque nominal (tipicamente 1.0–2.0 para NEMA B).",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        resultado = _cached_estimate_params(Vl, f, Pn_kW, N_nom, rend_placa, fp_placa, Ip_In, Tp_Tn, is_delta)

        if not resultado["success"]:
            st.error(f"Dados de placa inconsistentes: {resultado['error']}  Parâmetros padrão (Krause 3 HP) serão usados.")
            Rs, Rr, Xm, Xls, Xlr = 0.435, 0.816, 26.13, 0.754, 0.754
            Rfe = _DEFAULTS["Rfe"]
        else:
            Rs, Rr    = resultado["Rs"],  resultado["Rr"]
            Xm        = resultado["Xm"]
            Xls       = resultado["Xls"]
            Xlr       = resultado["Xlr"]
            Rfe       = resultado["Rfe"]
            ligacao = "Triângulo (Δ)" if is_delta else "Estrela (Y)"
            with st.expander("Como esses parâmetros foram estimados?", expanded=True):
                st.info(
                    f"**Método:** IEEE circuito equivalente em T — regime permanente.\n\n"
                    f"**Ligação assumida:** {ligacao}  "
                    f"| **Polos deduzidos da placa:** {resultado['p_est']}\n\n"
                    f"**Premissas elétricas:**\n"
                    f"- Distribuição NEMA B: $X_{{ls}}$ = 40% · $X_k$, $X_{{lr}}$ = 60% · $X_k$\n"
                    f"- Fator de potência na partida: cos(φₚ) = 0,20\n"
                    f"- Tensão no entreferro: $E_1 \\approx V_f - I_n \\cdot |Z_s|$ "
                    f"= {resultado['E1']:.2f} V (queda estatórica subtraída)\n"
                    f"- $R_{{fe}}$ estimado por heurística: perdas no ferro ≈ 20% das perdas totais "
                    f"({resultado['P_fe_total']:.1f} W) referidas a $E_1$ → $R_{{fe}}$ = {Rfe:.1f} Ω"
                )
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Vel. síncrona (Estimado)",       f"{resultado['n_s']:.1f} RPM")
                c2.metric("Escorregamento sₙ (Estimado)",   f"{resultado['s_n']*100:.2f}%")
                c3.metric("Corrente nominal Iₙ (Estimado)", f"{resultado['In_lin']:.2f} A")
                c4.metric("Torque nominal Tₙ (Estimado)",   f"{resultado['Tn']:.2f} N·m")
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Corrente partida Iₚ (Estimado)", f"{resultado['Ip_fase']:.2f} A")
                c6.metric("Torque partida Tₚ (Estimado)",   f"{resultado['Tp']:.2f} N·m")
                c7.metric("Zₖ (Estimado)",                  f"{resultado['Zk']:.4f} Ω")
                c8.metric("Xₖ (Estimado)",                  f"{resultado['Xk']:.4f} Ω")
                st.markdown("**Parâmetros do circuito equivalente estimados:**")
                p1, p2, p3, p4, p5, p6 = st.columns(6)
                p1.metric("Rₛ (Estimado)",  f"{Rs:.4f} Ω")
                p2.metric("Rᵣ (Estimado)",  f"{Rr:.4f} Ω")
                p3.metric("Xₘ (Estimado)",  f"{Xm:.4f} Ω")
                p4.metric("Xls (Estimado)", f"{Xls:.4f} Ω")
                p5.metric("Xlr (Estimado)", f"{Xlr:.4f} Ω")
                p6.metric("Rfe (Estimado)", f"{Rfe:.1f} Ω")

        # Parâmetros fixos para MachineParams no modo placa
        f_ref      = f
        input_mode = "X"

    elif use_ieee:
        # ══════════════════════════════════════════════════════════════════
        # MODO IEEE 112 — três ensaios físicos (CC + Vazio + Bloqueado)
        # ══════════════════════════════════════════════════════════════════
        _pgroup("Dados de Rede")
        Vl = st.number_input(
            "Tensão de linha RMS — $V_l$ (V)",
            min_value=50.0, max_value=15000.0, value=_DEFAULTS["Vl"], step=1.0,
            key=wk["Vl"], disabled=dis,
        )
        f  = st.number_input(
            "Frequência da rede — $f$ (Hz)",
            min_value=1.0, max_value=400.0, value=_DEFAULTS["f"], step=1.0,
            key=wk["f"], disabled=dis,
        )
        is_delta = st.checkbox(
            "Ligação em Triângulo (Δ) — desmarque para Estrela (Y)",
            value=False, key=wk["is_delta"], disabled=dis,
            help="Define o fator do ensaio CC: Y → Rs = (V_dc/I_dc)/2; Δ → Rs = (V_dc/I_dc)·1,5.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        _pgroup("[1] Ensaio CC — Resistência do Estator")
        c_dc1, c_dc2 = st.columns(2)
        V_dc = c_dc1.number_input(
            "Tensão CC aplicada — $V_{dc}$ (V)",
            min_value=0.01, max_value=1000.0, value=10.0, step=0.1, format="%.3f",
            key=wk["ieee_V_dc"], disabled=dis,
            help="Tensão CC aplicada entre dois terminais do motor (resistência a frio).",
        )
        I_dc = c_dc2.number_input(
            "Corrente CC medida — $I_{dc}$ (A)",
            min_value=0.001, max_value=10000.0, value=11.5, step=0.1, format="%.3f",
            key=wk["ieee_I_dc"], disabled=dis,
            help="Corrente CC estabilizada após o transitório térmico.",
        )
        # Preview do Rs em tempo real (sem chamar o estimador completo)
        if I_dc > 0:
            Rs_prev = (V_dc / I_dc) * (1.5 if is_delta else 0.5)
            st.caption(f"$R_s$ calculado (preview): **{Rs_prev:.4f} Ω**")
        st.markdown('</div>', unsafe_allow_html=True)

        _pgroup("[2] Ensaio em Vazio (No-Load)")
        c_nl1, c_nl2 = st.columns(2)
        Vl_nl = c_nl1.number_input(
            "Tensão de linha — $V_{l,NL}$ (V)",
            min_value=10.0, max_value=15000.0, value=float(Vl), step=1.0, format="%.1f",
            key=wk["ieee_Vl_nl"], disabled=dis,
            help="Tensão de linha aplicada durante o ensaio em vazio (tipicamente igual à nominal).",
        )
        I_nl = c_nl2.number_input(
            "Corrente de linha — $I_{NL}$ (A)",
            min_value=0.001, max_value=10000.0, value=4.5, step=0.1, format="%.3f",
            key=wk["ieee_I_nl"], disabled=dis,
            help="Corrente de linha em regime, motor desacoplado.",
        )
        c_nl3, c_nl4 = st.columns(2)
        P_nl = c_nl3.number_input(
            "Potência trifásica — $P_{NL}$ (W)",
            min_value=0.1, max_value=1e7, value=180.0, step=1.0, format="%.2f",
            key=wk["ieee_P_nl"], disabled=dis,
            help="Potência ativa trifásica total absorvida no ensaio em vazio.",
        )
        f_nl = c_nl4.number_input(
            "Frequência — $f_{NL}$ (Hz)",
            min_value=1.0, max_value=400.0, value=float(f), step=1.0, format="%.2f",
            key=wk["ieee_f_nl"], disabled=dis,
        )
        Pfw = st.number_input(
            "Perdas mecânicas — $P_{fw}$ (W) — 0 = estimar como 0,8% de $P_{NL}$",
            min_value=0.0, max_value=1e6, value=0.0, step=1.0, format="%.2f",
            key=wk["ieee_Pfw"], disabled=dis,
            help="Atrito + ventilação. Se deixado em 0, a heurística IEEE estima 0,8% de P_NL.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        _pgroup("[3] Ensaio de Rotor Bloqueado (Locked Rotor)")
        c_lr1, c_lr2 = st.columns(2)
        Vl_lr = c_lr1.number_input(
            "Tensão de linha — $V_{l,LR}$ (V)",
            min_value=0.1, max_value=15000.0, value=50.0, step=0.1, format="%.2f",
            key=wk["ieee_Vl_lr"], disabled=dis,
            help="Tensão reduzida aplicada com o rotor travado (cuidado: corrente nominal).",
        )
        I_lr = c_lr2.number_input(
            "Corrente de linha — $I_{LR}$ (A)",
            min_value=0.001, max_value=10000.0, value=14.0, step=0.1, format="%.3f",
            key=wk["ieee_I_lr"], disabled=dis,
            help="Corrente de linha medida com rotor bloqueado.",
        )
        c_lr3, c_lr4 = st.columns(2)
        P_lr = c_lr3.number_input(
            "Potência trifásica — $P_{LR}$ (W)",
            min_value=0.1, max_value=1e7, value=480.0, step=1.0, format="%.2f",
            key=wk["ieee_P_lr"], disabled=dis,
        )
        f_lr = c_lr4.number_input(
            "Frequência — $f_{LR}$ (Hz)",
            min_value=1.0, max_value=400.0, value=15.0, step=0.5, format="%.2f",
            key=wk["ieee_f_lr"], disabled=dis,
            help="IEEE Std 112 recomenda f_LR ≈ 25% de f nominal para minimizar saturação.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        _pgroup("Distribuição $X_{ls}$ / $X_{lr}$")
        split_label = st.selectbox(
            "Classe NEMA da distribuição",
            list(_IEEE_SPLIT_LABELS.values()),
            index=0,
            key=wk["ieee_split"], disabled=dis,
            help="IEEE Std 112-2017, Tabela 1 — fração de Xk atribuída a Xls.",
        )
        split_code = next(k for k, v in _IEEE_SPLIT_LABELS.items() if v == split_label)
        if split_code == "custom":
            Xls_frac = st.slider(
                "Fração $X_{ls} / X_k$",
                min_value=0.10, max_value=0.90, value=0.40, step=0.05,
                key=wk["ieee_Xls_frac"], disabled=dis,
            )
        else:
            Xls_frac = 0.4
        st.markdown('</div>', unsafe_allow_html=True)

        resultado = _cached_estimate_ieee(
            V_dc, I_dc, is_delta,
            Vl_nl, I_nl, P_nl, f_nl,
            Vl_lr, I_lr, P_lr, f_lr,
            Pfw, split_code, Xls_frac,
        )

        if not resultado["success"]:
            st.error(
                f"Ensaios IEEE inconsistentes: {resultado['error']}  "
                "Parâmetros padrão (Krause 3 HP) serão usados."
            )
            Rs, Rr, Xm, Xls, Xlr = 0.435, 0.816, 26.13, 0.754, 0.754
            Rfe = _DEFAULTS["Rfe"]
        else:
            Rs    = resultado["Rs"]
            Rr    = resultado["Rr"]
            Xm    = resultado["Xm"]
            Xls   = resultado["Xls"]
            Xlr   = resultado["Xlr"]
            Rfe   = resultado["Rfe"]
            ligacao = "Triângulo (Δ)" if is_delta else "Estrela (Y)"
            with st.expander("Detalhes do Cálculo (IEEE Std 112-2017)", expanded=True):
                st.info(
                    f"**Método:** IEEE Std 112-2017 — três ensaios físicos.\n\n"
                    f"**Ligação:** {ligacao}  "
                    f"| **Distribuição:** {_IEEE_SPLIT_LABELS[resultado['split_used']]} "
                    f"(fração $X_{{ls}}$/$X_k$ = {resultado['Xls_frac']:.2f})\n\n"
                    f"**Ensaio CC:** $R_s$ = {Rs:.4f} Ω  "
                    f"(via $V_{{dc}}$/$I_{{dc}}$ = {(V_dc/I_dc):.4f} Ω)\n\n"
                    f"**Ensaio em Vazio:** $E_{{1,NL}}$ = {resultado['E1_nl']:.2f} V  "
                    f"| $P_{{fe,3φ}}$ = {resultado['Pfe_3ph']:.2f} W  "
                    f"| $P_{{fw}}$ usado = {resultado['Pfw_used']:.2f} W "
                    f"({'medido' if Pfw > 0 else 'heurística 0,8% · P_NL'})\n\n"
                    f"**Ensaio Bloqueado:** $Z_k$ = {resultado['Zk']:.4f} Ω  "
                    f"| $R_k$ = {resultado['Rk']:.4f} Ω  "
                    f"| $X_{{k,LR}}$ = {resultado['Xk_lr']:.4f} Ω → "
                    f"$X_k$ @ {f_nl:.0f} Hz = {resultado['Xk']:.4f} Ω "
                    f"(corrigido por $f_{{NL}}/f_{{LR}}$ = {(f_nl/f_lr):.2f})"
                )
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("E₁_NL (Estimado)",  f"{resultado['E1_nl']:.2f} V")
                c2.metric("Iμ — magnetização", f"{resultado['I_mu']:.3f} A")
                c3.metric("Pfe trifásica",     f"{resultado['Pfe_3ph']:.1f} W")
                c4.metric("Pfw usado",         f"{resultado['Pfw_used']:.1f} W")
                st.markdown("**Parâmetros do circuito equivalente estimados:**")
                p1, p2, p3, p4, p5, p6 = st.columns(6)
                p1.metric("Rₛ (Estimado)",  f"{Rs:.4f} Ω")
                p2.metric("Rᵣ (Estimado)",  f"{Rr:.4f} Ω")
                p3.metric("Xₘ (Estimado)",  f"{Xm:.4f} Ω")
                p4.metric("Xls (Estimado)", f"{Xls:.4f} Ω")
                p5.metric("Xlr (Estimado)", f"{Xlr:.4f} Ω")
                p6.metric("Rfe (Estimado)", f"{Rfe:.1f} Ω")

            # Avisos de sanidade (apenas em caso de sucesso)
            if Xm < 5.0 * Xls:
                st.warning(
                    f"$X_m / X_{{ls}}$ = {Xm/Xls:.2f} < 5 — relação atípica. "
                    "Verifique os dados do ensaio em vazio."
                )
            if Rfe < 50.0:
                st.warning(
                    f"$R_{{fe}}$ = {Rfe:.1f} Ω muito baixo — verifique $P_{{NL}}$ "
                    "e a separação de perdas mecânicas (Pfw)."
                )

        # Parâmetros fixos para MachineParams no modo IEEE
        f_ref      = f
        input_mode = "X"

    else:
        # ══════════════════════════════════════════════════════════════════
        # MODO MANUAL — parâmetros inseridos diretamente pelo usuário
        # ══════════════════════════════════════════════════════════════════
        _pgroup("Dados Elétricos")
        Vl = st.number_input("Tensão de linha RMS — $V_l$ (V)",               min_value=50.0,   max_value=15000.0, value=_DEFAULTS["Vl"],  step=1.0,   key=wk["Vl"],  disabled=dis)
        f  = st.number_input("Frequência da rede — $f$ (Hz)",                 min_value=1.0,    max_value=400.0,   value=_DEFAULTS["f"],   step=1.0,   key=wk["f"],   disabled=dis)
        Rs = st.number_input("Resistência do estator — $R_s$ (Ω)",            min_value=0.0001, max_value=100.0,   value=_DEFAULTS["Rs"],  step=0.001, key=wk["Rs"],  format="%.3f", disabled=dis)
        Rr = st.number_input("Resistência do rotor — $R_r$ (Ω)",              min_value=0.0001, max_value=100.0,   value=_DEFAULTS["Rr"],  step=0.001, key=wk["Rr"],  format="%.3f", disabled=dis)

        input_mode_label = st.radio(
            "Formato dos parâmetros magnéticos",
            _INPUT_MODE_LABELS,
            index=0,
            key=wk["input_mode"],
            disabled=dis,
            horizontal=True,
        )
        input_mode = "X" if input_mode_label.startswith("Reatâncias") else "L"

        if input_mode == "X":
            f_ref = st.number_input(
                "Frequência de referência dos ensaios — $f_{ref}$ (Hz)",
                min_value=1.0, max_value=400.0, value=60.0, step=1.0,
                key=wk["f_ref"],
                help="Frequência em que $X_m$, $X_{ls}$ e $X_{lr}$ foram medidos (tipicamente 50 Hz ou 60 Hz).",
                disabled=dis,
            )
            Xm  = st.number_input("Reatância de magnetização — $X_m$ (Ω)",            min_value=0.0001, max_value=500.0, value=_DEFAULTS["Xm"],  step=0.01,  key=wk["Xm"],  format="%.2f", disabled=dis)
            Xls = st.number_input("Reatância de dispersão do estator — $X_{ls}$ (Ω)", min_value=0.0001, max_value=50.0,  value=_DEFAULTS["Xls"], step=0.001, key=wk["Xls"], format="%.3f", disabled=dis)
            Xlr = st.number_input("Reatância de dispersão do rotor — $X_{lr}$ (Ω)",   min_value=0.0001, max_value=50.0,  value=_DEFAULTS["Xlr"], step=0.001, key=wk["Xlr"], format="%.3f", disabled=dis)
        else:
            f_ref   = 60.0
            _wb_ref = 2.0 * 3.141592653589793 * 60.0
            Xm  = st.number_input("Indutância de magnetização — $L_m$ (H)",            min_value=1e-6, max_value=10.0, value=round(_DEFAULTS["Xm"]  / _wb_ref, 6), step=0.0001, key=wk["Xm_L"],  format="%.6f", disabled=dis)
            Xls = st.number_input("Indutância de dispersão do estator — $L_{ls}$ (H)", min_value=1e-6, max_value=1.0,  value=round(_DEFAULTS["Xls"] / _wb_ref, 6), step=0.0001, key=wk["Xls_L"], format="%.6f", disabled=dis)
            Xlr = st.number_input("Indutância de dispersão do rotor — $L_{lr}$ (H)",   min_value=1e-6, max_value=1.0,  value=round(_DEFAULTS["Xlr"] / _wb_ref, 6), step=0.0001, key=wk["Xlr_L"], format="%.6f", disabled=dis)

        Rfe = st.number_input("Resistência de perdas no ferro — $R_{fe}$ (Ω)", min_value=10.0, max_value=10000.0, value=_DEFAULTS["Rfe"], step=10.0, key=wk["Rfe"], format="%.1f", disabled=dis)
        st.caption("$R_{fe}$ afeta tanto a dinâmica do ODE (correntes de perda no ferro) quanto o balanço de potências em regime permanente.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Mecânicos ─────────────────────────────────────────────────────────
    _pgroup("Dados Mecânicos e Referencial")
    p = st.selectbox("Número de polos — $p$", options=[2, 4, 6, 8, 10, 12], index=1, key=wk["p"], disabled=dis)
    J = st.number_input("Momento de inércia — $J$ (kg·m²)",               min_value=0.0001, max_value=100.0, value=_DEFAULTS["J"], step=0.001, key=wk["J"], format="%.3f", disabled=dis)
    B = st.number_input("Coeficiente de atrito viscoso — $B$ (N·m·s/rad)", min_value=0.0,   max_value=10.0,  value=_DEFAULTS["B"], step=0.001, key=wk["B"], format="%.3f", disabled=dis)
    if B == 0.0:
        _T_nom_est = float(st.session_state.get("wi_Tl_final", 0.0))
        _wr_nom    = (1.0 - 0.03) * 120.0 * f / p * 3.14159265 / 30.0
        if _T_nom_est > 0.0 and _wr_nom > 0.0:
            _B_est = 0.01 * _T_nom_est / _wr_nom
            st.caption(
                f"B = 0 na referência bibliográfica — estimado por regra empírica "
                f"(0,01 × T_nom / ω_nom): **{_B_est:.4f} N·m·s/rad**. "
                "Edite manualmente se necessário."
            )
            B = _B_est
    ref_label = st.selectbox(
        "Referencial da Transformada de Park",
        ["Síncrono  (ω = ωₑ)", "Rotórico  (ω = ωᵣ)", "Estacionário  (ω = 0)"],
        disabled=dis,
    )
    ref_code = {"Síncrono  (ω = ωₑ)": 1,
                "Rotórico  (ω = ωᵣ)": 2,
                "Estacionário  (ω = 0)": 3}[ref_label]
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Parâmetros Avançados (IAS/Industrial) ────────────────────────────
    # Im_0: corrente de magnetização em vazio = Vfase / (wb·Lm)
    with st.expander("Parâmetros Avançados (IAS/Industrial)", expanded=False):
        # ── Impedância de Rede ───────────────────────────────────────────
        _pgroup("Impedância de Rede (Voltage Sag)")
        rg1, rg2 = st.columns(2)
        with rg1:
            Rgrid = st.number_input(
                "$R_{grid}$ (Ω/fase)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.01, format="%.4f",
                key=wk["Rgrid"],
                disabled=dis,
                help="Resistência da linha de alimentação por fase. 0 = sem queda resistiva.",
            )
        with rg2:
            Lgrid = st.number_input(
                "$L_{grid}$ (H/fase)",
                min_value=0.0, max_value=1.0, value=0.0, step=0.0001, format="%.4f",
                key=wk["Lgrid"],
                disabled=dis,
                help="Indutância da linha de alimentação por fase (H). 0 = sem queda indutiva.",
            )
        if Rgrid > 0 or Lgrid > 0:
            _wb = 2.0 * np.pi * f
            _Zgrid_mag = float(np.sqrt(Rgrid**2 + (_wb * Lgrid)**2))
            _ibox(
                f"Impedância de rede: $R_{{grid}}$ = {Rgrid:.4f} Ω  |  "
                f"$X_{{grid}}$ = {_wb*Lgrid:.4f} Ω  |  "
                f"$|Z_{{grid}}|$ = {_Zgrid_mag:.4f} Ω. "
                "A tensão no terminal do motor será menor que $V_l$."
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Análise Econômica ────────────────────────────────────────────
        _pgroup("Análise Econômica")
        energy_tariff = st.number_input(
            "Tarifa de energia elétrica (R$/kWh)",
            min_value=0.0001, max_value=5.0, value=0.75, step=0.01, format="%.2f",
            key=wk["energy_tariff"],
            disabled=dis,
            help=(
                "Tarifa média usada para projetar o custo operacional anual com base "
                "no perfil de carga simulado. Valor típico industrial: R$0,60–0,90/kWh."
            ),
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    mp = MachineParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe, p=p, J=J, B=B,
                       input_mode=input_mode, f_ref=f_ref,
                       Rgrid=Rgrid, Lgrid=Lgrid)
    _validate_params(mp)

    st.write("")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Velocidade Síncrona $n_s$", f"{mp.n_sync:.1f} RPM")
    mc2.metric("Velocidade Angular Base $\\omega_b$", f"{mp.wb/(mp.p/2):.2f} rad/s")
    mc3.metric("Reatância Mútua $X_{ml}$", f"{mp.Xml:.4f} Ω")
    if input_mode == "X":
        st.caption(f"Indutâncias calculadas a {f_ref:.0f} Hz → $L_m$ = {mp.Lm*1000:.4f} mH  |  $L_{{ls}}$ = {mp.Lls*1000:.4f} mH  |  $L_{{lr}}$ = {mp.Llr*1000:.4f} mH")

    return mp, ref_code, energy_tariff


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DO EXPERIMENTO
# ─────────────────────────────────────────────────────────────────────────────

def render_experiment_config(
    mp: MachineParams,
    wk: dict[str, str] = _WK,
) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    """Configuração do experimento, variáveis e parâmetros numéricos.

    Args:
        mp: parâmetros da máquina já construídos.
        wk: mapeamento campo lógico → key do widget (usa _WK por padrão).

    Returns:
        (config, var_keys, var_labels, tmax, h)
    """
    st.markdown('<p class="slabel">Experimento</p>', unsafe_allow_html=True)

    exp_options: dict[str, str] = {
        "Partida Direta (DOL)":                       "dol",
        "Partida Estrela-Triângulo (Y-D)":             "yd",
        "Partida com Autotransformador":               "comp",
        "Soft-Starter (Rampa de Tensão)":              "soft",
        "Pulso de Carga (aplica e retira)":            "pulso_carga",
        "Operação como Gerador":                       "gerador",
        "Desligamento (Corte de Alimentação)":         "shutdown",
        "Afundamento de Tensão (Voltage Sag)":         "voltage_sag",
    }
    exp_label = st.selectbox("Tipo de Experimento", list(exp_options.keys()), key=wk["exp_type"])
    exp_type  = exp_options[exp_label]
    config: dict[str, Any] = {"exp_type": exp_type, "exp_label": exp_label}

    _pgroup("Parâmetros de Carga e Tensão")

    # Torque de referência do preset carregado — usado como valor inicial em todos os experimentos.
    # Garante que ao comutar entre tipos de experimento o torque não retorne ao padrão fixo 80 N·m.
    _Tl_ref = float(st.session_state.get(wk["Tl_final"], 80.0))

    if exp_type == "dol":
        partir_em_vazio = st.checkbox(
            "Partir em vazio (aplicar carga após partida)",
            value=True,
            key="wi_dol_partir_vazio",
            help="Quando ativo, o motor parte sem carga e recebe o torque em t_carga. "
                 "Quando inativo, a carga já está presente desde o instante zero.",
        )
        config["partir_em_vazio"] = partir_em_vazio

        if partir_em_vazio:
            Tl_nom = st.number_input("Torque nominal de referência — $T_{nom}$ (N·m)", value=_Tl_ref, min_value=0.0001, key="wi_dol_Tl_nom")
            pct_fin = st.number_input(
                "Carga aplicada (%)", value=100.0,
                help="Torque de carga como percentual de T_nom. Aplicado em t_carga.",
                key="wi_dol_pct_fin",
            )
            config["Tl_inicial"] = 0.0
            config["Tl_final"]   = Tl_nom * pct_fin / 100.0
            config["t_carga"]    = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk["t_carga"])
            _ibox(
                f"<strong>t = 0 s</strong> — tensão nominal ({mp.Vl:.0f} V) aplicada; motor acelera em vazio (T<sub>l</sub> = 0).<br>"
                f"<strong>t = {config['t_carga']:.2f} s</strong> — carga de "
                f"<strong>{config['Tl_final']:.2f} N·m</strong> ({pct_fin:.1f}% de T<sub>nom</sub>) aplicada ao eixo; "
                f"motor acomoda-se ao novo ponto de operação em regime permanente."
            )
        else:
            config["Tl_inicial"] = None
            config["Tl_final"]   = st.number_input("Torque de carga — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk["Tl_final"])
            config["t_carga"]    = 0.0
            _ibox(
                f"<strong>t = 0 s</strong> — tensão nominal ({mp.Vl:.0f} V) e carga de "
                f"<strong>{config['Tl_final']:.2f} N·m</strong> aplicadas simultaneamente; "
                f"motor parte contra carga plena e acelera até o regime permanente."
            )


    elif exp_type == "yd":
        config["Tl_final"] = st.number_input("Torque de carga — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk["Tl_final"])
        config["t_2"]      = st.number_input("Instante de comutação Y → D — $t_2$ (s)", value=0.5, min_value=0.0001, key="wi_yd_t2")
        config["t_carga"]  = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk["t_carga"])
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte em estrela (Y) com tensão reduzida a "
            f"{mp.Vl/np.sqrt(3):.1f} V ({100/np.sqrt(3):.0f}% de V<sub>l</sub>); corrente e torque de partida reduzidos a ≈ 1/3.<br>"
            f"<strong>t = {config['t_2']:.2f} s</strong> — comutação Y → Δ: tensão sobe para {mp.Vl:.0f} V; "
            f"transitório de corrente de re-partida.<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — carga de <strong>{config['Tl_final']:.2f} N·m</strong> aplicada ao eixo."
        )
        _aviso_partida_reduzida(mp, 1.0 / np.sqrt(3.0), config["Tl_final"])

    elif exp_type == "comp":
        config["Tl_final"]      = st.number_input("Torque de carga — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk["Tl_final"])
        config["voltage_ratio"] = st.slider("Tap do autotransformador — $k$ (%)", 10, 95, 50, key="wi_comp_tap") / 100.0
        config["t_2"]           = st.number_input("Instante de comutação — $t_2$ (s)", value=0.5, min_value=0.0001, key="wi_comp_t2")
        config["t_carga"]       = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk["t_carga"])
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte com tensão reduzida a "
            f"{config['voltage_ratio']*100:.0f}% de V<sub>l</sub> "
            f"({mp.Vl * config['voltage_ratio']:.1f} V); torque de partida reduzido a "
            f"{config['voltage_ratio']**2 * 100:.0f}% do valor em tensão plena.<br>"
            f"<strong>t = {config['t_2']:.2f} s</strong> — comutação: autotransformador desconectado, "
            f"tensão nominal {mp.Vl:.0f} V aplicada diretamente; transitório de corrente de re-partida.<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — carga de <strong>{config['Tl_final']:.2f} N·m</strong> aplicada ao eixo."
        )
        _aviso_partida_reduzida(mp, config["voltage_ratio"], config["Tl_final"])

    elif exp_type == "soft":
        config["voltage_ratio"] = st.slider("Tensão inicial do Soft-Starter — $V_0$ (%)", 10, 90, 50, key="wi_soft_v0") / 100.0
        config["t_2"]           = st.number_input("Início da rampa de tensão — $t_2$ (s)", value=0.0, min_value=0.0, key="wi_soft_t2")
        config["t_pico"]        = st.number_input("Tempo para atingir tensão nominal — $t_{pico}$ (s)", value=5.0, min_value=0.0001, key="wi_soft_t_pico")
        config["Tl_final"]      = st.number_input("Torque de carga — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk["Tl_final"])
        config["t_carga"]       = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk["t_carga"])
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte com tensão inicial de "
            f"{config['voltage_ratio']*100:.0f}% de V<sub>l</sub> "
            f"({mp.Vl * config['voltage_ratio']:.1f} V); corrente e torque de partida limitados.<br>"
            f"<strong>t = {config['t_2']:.2f} s</strong> — rampa de tensão iniciada: tensão sobe linearmente até {mp.Vl:.0f} V.<br>"
            f"<strong>t = {config['t_pico']:.2f} s</strong> — tensão nominal atingida; Soft-Starter desconectado, "
            f"motor em operação direta (rampa de {config['t_pico'] - config['t_2']:.2f} s).<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — carga de <strong>{config['Tl_final']:.2f} N·m</strong> aplicada ao eixo."
        )
        _aviso_partida_reduzida(mp, config["voltage_ratio"], config["Tl_final"])

    elif exp_type == "pulso_carga":
        Tl_base = st.number_input("Torque de base — $T_{base}$ (N·m)", value=_Tl_ref * 0.5, min_value=0.0, key=wk["Tl_pulso"])
        st.caption("Carga já presente no eixo antes e após o pulso. Use 0 para partida em vazio.")
        if Tl_base == 0.0:
            Tl_pulso = st.number_input("Torque durante o pulso — $T_{pulso}$ (N·m)", value=_Tl_ref, min_value=0.0001, key=wk["Tl_pulso_abs"])
            st.caption("Torque aplicado no intervalo $[t_{on},\\, t_{off})$. Fora desse intervalo o motor opera em vazio.")
        else:
            pct      = st.number_input("Variação durante o pulso (%)", value=50.0, key="wi_pct_pulso")
            st.caption("Percentual de $T_{base}$ adicionado (positivo) ou subtraído (negativo) durante o pulso.")
            Tl_pulso = Tl_base * (1.0 + pct / 100.0)
        config["Tl_base"]  = Tl_base
        config["Tl_final"] = Tl_pulso
        t_on  = st.number_input("Instante de aplicação do pulso — $t_{on}$ (s)",  value=1.0, min_value=0.0, step=0.1, format="%.2f", key=wk["t_pulso_on"])
        t_off = st.number_input("Instante de retirada do pulso — $t_{off}$ (s)", value=1.5, min_value=0.0, step=0.1, format="%.2f", key=wk["t_pulso_off"])
        config["t_carga"]    = t_on
        config["t_retirada"] = t_off
        if t_off <= t_on:
            st.error(f"t_off ({t_off:.2f} s) deve ser maior que t_on ({t_on:.2f} s).")
            config["_invalid"] = True
        else:
            duracao = t_off - t_on
            if Tl_base == 0.0:
                _ibox(
                    f"<strong>t = 0 s</strong> — motor parte em vazio (T<sub>l</sub> = 0) com tensão nominal {mp.Vl:.0f} V.<br>"
                    f"<strong>t = {t_on:.2f} s</strong> — pulso de carga de <strong>{Tl_pulso:.2f} N·m</strong> aplicado; motor desacelera.<br>"
                    f"<strong>t = {t_off:.2f} s</strong> — pulso retirado (duração: {duracao:.2f} s); motor retorna ao vazio e recupera velocidade síncrona."
                )
            else:
                delta = Tl_pulso - Tl_base
                sinal = "aumento" if delta >= 0 else "redução"
                _ibox(
                    f"<strong>t = 0 s</strong> — motor parte com carga de base <strong>{Tl_base:.2f} N·m</strong> e tensão nominal {mp.Vl:.0f} V.<br>"
                    f"<strong>t = {t_on:.2f} s</strong> — {sinal} para <strong>{Tl_pulso:.2f} N·m</strong> "
                    f"({pct:+.1f}% de T<sub>base</sub>); transitório de velocidade e torque.<br>"
                    f"<strong>t = {t_off:.2f} s</strong> — retorno à base de {Tl_base:.2f} N·m (duração do pulso: {duracao:.2f} s)."
                )

    elif exp_type == "gerador":
        config["Tl_mec"] = st.number_input("Torque mecânico da turbina — $T_{mec}$ (N·m)", value=_Tl_ref, min_value=1.0, key=wk["Tl_mec"])
        config["t_2"]    = st.number_input("Instante de aplicação do torque — $t_2$ (s)", value=1.0, min_value=0.0, key=wk["t_2_gerador"])
        _ibox(
            f"<strong>t = 0 s</strong> — máquina conectada à rede ({mp.Vl:.0f} V) e acelerada pela inércia até próximo à velocidade síncrona.<br>"
            f"<strong>t = {config['t_2']:.2f} s</strong> — torque mecânico de <strong>{config['Tl_mec']:.2f} N·m</strong> aplicado pela turbina; "
            f"rotor ultrapassa a velocidade síncrona (s &lt; 0) e a máquina passa a injetar potência ativa na rede."
        )

    elif exp_type == "shutdown":
        config["Tl_final"]  = st.number_input("Torque de carga — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk["Tl_final"])
        config["t_carga"]   = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=0.3, min_value=0.0, key=wk["t_carga"])
        config["t_cutoff"]  = st.number_input("Instante de desligamento — $t_{des}$ (s)", value=1.5, min_value=0.0001, key="wi_sd_t_cutoff")
        if config["t_carga"] >= config["t_cutoff"]:
            st.error(f"t_carga ({config['t_carga']:.2f} s) deve ser menor que t_des ({config['t_cutoff']:.2f} s). Aplique a carga antes do desligamento.")
            config["_invalid"] = True
        _ws    = 2.0 * np.pi * mp.f / (mp.p / 2)
        _Tl_sd = config["Tl_final"]
        _B_sd  = mp.B
        _J_sd  = mp.J
        if _B_sd > 0 and _Tl_sd > 0:
            _t_stop_mec = (_J_sd / _B_sd) * np.log(1.0 + _B_sd * _ws / _Tl_sd)
        elif _Tl_sd > 0:
            _t_stop_mec = _J_sd * _ws / _Tl_sd
        else:
            _tau_m_fb   = _J_sd / _B_sd if _B_sd > 0 else 10.0
            _t_stop_mec = 5.0 * _tau_m_fb
        _t_end_sd = config["t_cutoff"] + _t_stop_mec * 1.2
        config["_t_end_shutdown"] = float(_t_end_sd)
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte com tensão nominal {mp.Vl:.0f} V e acelera em vazio.<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — carga de <strong>{config['Tl_final']:.2f} N·m</strong> aplicada; motor acomoda-se em regime permanente.<br>"
            f"<strong>t = {config['t_cutoff']:.2f} s</strong> — tensão cortada (abertura do contator); torque eletromagnético decai em milissegundos.<br>"
            f"<strong>Pós-corte</strong> — carga mecânica freia o rotor até parada completa "
            f"(t<sub>stop</sub> ≈ {_t_stop_mec:.2f} s, calculado por J/B·ln(1 + B·ω₀/T<sub>L</sub>)).<br>"
            f"<strong>t<sub>end</sub> automático: {_t_end_sd:.2f} s</strong> (t<sub>des</sub> + t<sub>stop</sub> × 1,2)."
        )

    elif exp_type == "voltage_sag":
        sg1, sg2 = st.columns(2)
        with sg1:
            sag_mag = st.slider(
                "Tensão durante o sag — $V_{sag}$ (% de $V_l$)",
                min_value=5, max_value=95, value=50, step=5,
                key=wk["sag_magnitude"],
                help="Percentual da tensão nominal durante o afundamento. 50% = sag de 0.5 pu.",
            ) / 100.0
        with sg2:
            config["Tl_final"] = st.number_input(
                "Torque de carga — $T_l$ (N·m)",
                value=_Tl_ref, min_value=0.0,
                key=wk["sag_Tl"],
                help="Carga mecânica aplicada desde o início da simulação.",
            )
            config["t_carga"] = 0.0
        t_start_sag    = st.number_input("Início do sag — $t_{sag}$ (s)",    value=0.5, min_value=0.0, step=0.05, format="%.3f", key=wk["t_start_sag"])
        t_duration_sag = st.number_input("Duração do sag — $\\Delta t_{sag}$ (s)", value=0.1, min_value=0.0001, max_value=5.0, step=0.01, format="%.3f", key=wk["t_duration_sag"])
        t_end_sag = t_start_sag + t_duration_sag
        config["sag_magnitude"]  = sag_mag
        config["t_start_sag"]    = t_start_sag
        config["t_duration_sag"] = t_duration_sag
        _Vsag_line = mp.Vl * sag_mag
        _ibox(
            f"<strong>t = 0 s</strong> — motor parte com tensão nominal {mp.Vl:.1f} V e carga de "
            f"<strong>{config['Tl_final']:.2f} N·m</strong>; atinge regime permanente antes do sag.<br>"
            f"<strong>t = {t_start_sag:.3f} s</strong> — afundamento de tensão: "
            f"{mp.Vl:.1f} V → <strong>{_Vsag_line:.1f} V ({sag_mag*100:.0f}%)</strong>; "
            f"torque eletromagnético reduz, rotor desacelera.<br>"
            f"<strong>t = {t_end_sag:.3f} s</strong> — tensão restaurada ({t_duration_sag*1000:.0f} ms de duração); "
            f"transitório de re-aceleração com pico de corrente — principal evento de interesse."
        )
        if t_duration_sag < 0.02:
            st.warning("Duração < 20 ms — sag sub-transitório; reduza o passo $h$ para capturar o transitório.")
        if sag_mag <= 0.1:
            st.warning("Sag profundo (≤ 10%) — o motor pode desacelerar significativamente e a corrente de re-partida pode superar a corrente de rotor bloqueado.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── seleção de variáveis ──────────────────────────────────────────────
    st.write("")
    st.markdown('<p class="slabel">Variáveis para Visualização</p>', unsafe_allow_html=True)
    _pgroup("Grandezas Mecânicas")
    sel_mec = st.multiselect(
        "Grandezas mecânicas",
        options=list(VARIABLE_CATALOG_MECANICAS.keys()),
        default=["Torque Eletromagnético  Tₑ  (N·m)", "Velocidade do Rotor  n  (RPM)"],
        label_visibility="collapsed",
    )
    _pgroup("Grandezas Elétricas")
    sel_ele = st.multiselect(
        "Grandezas elétricas",
        options=list(VARIABLE_CATALOG_ELETRICAS.keys()),
        default=["Corrente de Fase A — Estator  iₐₛ  (A)"],
        label_visibility="collapsed",
    )
    selected_labels = sel_mec + sel_ele
    var_keys   = [VARIABLE_CATALOG[v] for v in selected_labels]
    var_labels = list(selected_labels)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── tempo e passo ─────────────────────────────────────────────────────
    st.write("")
    st.markdown('<p class="slabel">Parâmetros Numéricos da Simulação</p>', unsafe_allow_html=True)
    _pgroup("Tempo Total e Passo de Integração")

    # para shutdown sincroniza wi_tmax com o t_end analítico apenas quando os
    # parâmetros que o determinam mudaram — preserva edições manuais do usuário
    if config.get("exp_type") == "shutdown" and "_t_end_shutdown" in config:
        _sd_hash = hashlib.md5(
            json.dumps([mp.J, mp.B, config.get("Tl_final"), config.get("t_cutoff")]).encode()
        ).hexdigest()
        if st.session_state.get("_sd_tmax_hash") != _sd_hash:
            st.session_state[wk["tmax"]] = round(float(config["_t_end_shutdown"]), 1)
            st.session_state["_sd_tmax_hash"] = _sd_hash

    tc1, tc2 = st.columns(2)
    with tc1:
        _tmax_auto = st.checkbox("Calcular tmax automaticamente (inércia do motor)", value=True, key="wi_tmax_auto")
        tmax = st.number_input("Tempo total — $t_{max}$ (s)", min_value=0.001, max_value=3600.0, value=2.0, step=0.1, format="%.1f", key=wk["tmax"], disabled=_tmax_auto)
        if _tmax_auto:
            tmax = 0.0  # sentinel: runner fará o cálculo real

        _etype = config.get("exp_type", "")
        if _etype == "shutdown":
            _tmax_sug = round(float(config.get("_t_end_shutdown", config.get("t_cutoff", 1.5))), 1)
            st.caption(f"Definido automaticamente: {_tmax_sug:.1f} s  (t_des + t_stop × 1,2 — analítico)")
            _tmax_auto_val = None
        else:
            _tmax_auto_val   = round(calc_tmax_auto(config, mp), 1)
            _t_acomo_preview = float(min(max(15.0 * mp.J, 2.0), 30.0))
            if _tmax_auto:
                st.caption(f"Automático: **{_tmax_auto_val:.1f} s**  (eventos + {_t_acomo_preview:.1f} s de acomodação mecânica, J={mp.J:.3f} kg·m²)")
            else:
                st.caption(f"Sugestão: ≥ {round(_tmax_auto_val - _t_acomo_preview + 0.5, 1):.1f} s  (último evento + 0,5 s para atingir regime)")

        h = st.number_input("Passo de integração — $h$ (s)", min_value=0.000001, max_value=0.1, value=0.0001, step=0.000001, format="%.6f", key=wk["h"])
        _tmax_display = _tmax_auto_val if (_tmax_auto and _tmax_auto_val is not None) else tmax
        n_steps = int(_tmax_display / h) if _tmax_display > 0 else 0
        st.caption(f"Total de passos: {n_steps:,}")
        if n_steps > 100_000:
            st.warning("Número elevado de passos. A simulação pode demorar vários segundos.")
        h_max_rec = 1.0 / (20.0 * mp.f)
        st.caption(f"h recomendado: ≤ {h_max_rec:.5f} s  (1/20 ciclo a {mp.f:.0f} Hz)")
        if h > h_max_rec:
            st.warning(
                f"Passo h={h:.5f} s excede o limite recomendado "
                f"({h_max_rec:.5f} s para {mp.f:.0f} Hz). "
                "Reduza h para evitar divergência numérica."
            )

        # verifica se tmax cobre todos os eventos do experimento
        _critical: list[tuple[str, str, float]] = []
        if _etype == "dol":
            _tc_dol = config.get("t_carga", 0)
            if _tc_dol > 0:
                _critical = [("aplicação da carga", r"t_{carga}", _tc_dol)]
        elif _etype == "yd":
            _critical = [("comutação Y→D",       r"t_2",       config.get("t_2", 0)),
                         ("aplicação da carga",  r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "comp":
            _critical = [("comutação do autotransformador", r"t_2",       config.get("t_2", 0)),
                         ("aplicação da carga",             r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "soft":
            _critical = [("início da rampa",         r"t_2",      config.get("t_2", 0)),
                         ("tensão nominal atingida", r"t_{pico}", config.get("t_pico", 0)),
                         ("aplicação da carga",      r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "pulso_carga":
            _critical = [("aplicação da carga", r"t_{on}",  config.get("t_carga", 0)),
                         ("retirada da carga",  r"t_{off}", config.get("t_retirada", 0))]
        elif _etype == "gerador":
            _critical = [("aplicação do torque da turbina", r"t_2", config.get("t_2", 0))]
        elif _etype == "shutdown":
            _critical = [("aplicação da carga", r"t_{carga}", config.get("t_carga", 0)),
                         ("desligamento",        r"t_{des}",   config.get("t_cutoff", 0))]
        if not _tmax_auto:
            for _lbl, _sym, _t in _critical:
                if _t >= tmax:
                    st.warning(
                        f"$t_{{max}}$ ({tmax:.2f} s) ≤ ${_sym}$ ({_t:.2f} s): "
                        f"o evento de **{_lbl}** não ocorrerá na simulação — aumente $t_{{max}}$."
                    )
    with tc2:
        _ibox(
            "<strong>t<sub>max</sub>:</strong> quanto maior, mais do transitório é capturado, porém maior o custo "
            "computacional.<br><br>"
            "<strong>h (passo):</strong> o limite de estabilidade é h ≤ 1/(20·f). "
            "Para f=60 Hz: h ≤ 0,00083 s. Para frequências maiores, reduza h proporcionalmente."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    render_desequilibrio_ui(config, tmax=tmax)
    render_broken_bar_ui(config, tmax=tmax, wk=wk)

    return config, var_keys, var_labels, tmax, h
