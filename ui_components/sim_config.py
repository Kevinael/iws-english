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
from core.desequilibrio_falta import render_desequilibrio_ui
from ui.theme import _palette


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
    "sat_enable":           "wi_sat_enable",
    "Im_sat":               "wi_Im_sat",
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
    # modelo térmico
    "th_override":          "wi_th_override",
    "Rth":                  "wi_Rth",
    "Cth":                  "wi_Cth",
    "T_amb":                "wi_T_amb",
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

_PRESETS: dict[str, dict[str, Any]] = {
    "Padrão — Krause 3 HP (2.2 kW) 220 V/60 Hz": {
        # Krause (2002) — motor de indução 220 V / 60 Hz / 4 polos / ~3 cv
        # Im0 ≈ 4.86 A  →  Im_sat = 2×Im0 ≈ 9.7 A (saturação moderada em partida)
        # Rfe = 400 Ω: perdas no ferro ≈ 3×(127²/400) ≈ 121 W (~5.5% de potência nominal)
        "Vl": 220.0, "f": 60.0, "Rs": 0.435, "Rr": 0.816,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 26.13, "Xls": 0.754, "Xlr": 0.754, "Rfe": 400.0,
        "p": 4, "J": 0.089, "B": 0.005,
        "sat_enable": True, "Im_sat": 9.7,
        "exp_type": "Partida Direta (DOL)",
    },
    "Usta (2024) — 0.37 kW 220 V/50 Hz": {
        # Motor de laboratório 220 V / 50 Hz / 4 polos / ~0.37 kW
        # Im0 = (220/√3) / Xm = 127/60.98 ≈ 2.08 A  →  Im_sat = 2×Im0 ≈ 4.2 A
        # Rfe = 800 Ω: motor pequeno com menor volume de ferro — perdas relativas menores
        "Vl": 220.0, "f": 50.0, "Rs": 2.65, "Rr": 2.85,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 50.0, "Xm": 60.98, "Xls": 4.43, "Xlr": 5.69, "Rfe": 800.0,
        "p": 4, "J": 0.025, "B": 0.001,
        "sat_enable": False, "Im_sat": 4.2,
        "exp_type": "Pulso de Carga (aplica e retira)",
        "Tl_pulso": 0.0, "Tl_pulso_abs": 10.0, "t_pulso_on": 0.6, "t_pulso_off": 0.8,
        "tmax": 1.0,
    },
    "Krause 50 HP (37 kW) — 460 V/60 Hz": {
        # Krause (2002) — motor industrial médio porte, 460 V / 60 Hz / 4 polos / 50 cv
        # Im0 = (460/√3) / Xm = 265.6/13.08 ≈ 20.3 A  →  Im_sat = 2×Im0 ≈ 14.5 A (ajustado)
        # Rfe = 150 Ω: núcleo maior, perdas absolutas maiores mas Rfe menor
        "Vl": 460.0, "f": 60.0, "Rs": 0.087, "Rr": 0.228,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 13.08, "Xls": 0.302, "Xlr": 0.302, "Rfe": 150.0,
        "p": 4, "J": 1.662, "B": 0.0,
        "sat_enable": True, "Im_sat": 14.5,
        "exp_type": "Partida Direta (DOL)",
    },
    "Krause 2250 HP (1678 kW) — 2300 V/60 Hz": {
        # Krause (2002) — motor de grande porte, média tensão, 2300 V / 60 Hz / 4 polos
        # Im0 = (2300/√3) / Xm = 1328/13.04 ≈ 101.8 A  →  Im_sat ≈ 75 A (saturação moderada)
        # Rfe = 80 Ω: núcleo de grande volume, alta corrente de excitação
        "Vl": 2300.0, "f": 60.0, "Rs": 0.029, "Rr": 0.022,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 13.04, "Xls": 0.226, "Xlr": 0.226, "Rfe": 80.0,
        "p": 4, "J": 63.87, "B": 0.0,
        "sat_enable": True, "Im_sat": 75.0,
        "exp_type": "Partida Direta (DOL)",
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

    st.markdown('<p class="slabel">Simulador de Máquinas Elétricas</p>', unsafe_allow_html=True)
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
            if st.button("Iniciar Simulação", key=f"sel_{m['key']}", use_container_width=True):
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
                "sat_enable": wk["sat_enable"], "Im_sat": wk["Im_sat"],
                "exp_type": wk["exp_type"],
                "Tl_pulso": wk["Tl_pulso"],
                "Tl_pulso_abs": wk["Tl_pulso_abs"],
                "t_pulso_on": wk["t_pulso_on"],
                "t_pulso_off": wk["t_pulso_off"],
                "tmax": wk["tmax"],
            }
            for key, widget_key in _wk_preset.items():
                if key in pdata:
                    st.session_state[widget_key] = pdata[key]
            st.session_state["_reset_preset_select"] = True
            st.rerun()

    if experiment_mode:
        _ibox("<strong>Parâmetros travados</strong> — desative o toggle para editar.")

    dis = experiment_mode

    # ── Elétricos ─────────────────────────────────────────────────────────
    _pgroup("Dados Elétricos")
    Vl = st.number_input("Tensão de linha RMS — $V_l$ (V)",               min_value=50.0,  max_value=15000.0, value=_DEFAULTS["Vl"],  step=1.0,   key=wk["Vl"],  disabled=dis)
    f  = st.number_input("Frequência da rede — $f$ (Hz)",                min_value=1.0,   max_value=400.0,   value=_DEFAULTS["f"],   step=1.0,   key=wk["f"],   disabled=dis)
    Rs = st.number_input("Resistência do estator — $R_s$ (Ω)",           min_value=0.001, max_value=100.0,   value=_DEFAULTS["Rs"],  step=0.001, key=wk["Rs"],  format="%.3f", disabled=dis)
    Rr = st.number_input("Resistência do rotor — $R_r$ (Ω)",             min_value=0.001, max_value=100.0,   value=_DEFAULTS["Rr"],  step=0.001, key=wk["Rr"],  format="%.3f", disabled=dis)

    input_mode_label = st.radio(
        "Modo de entrada dos parâmetros magnéticos",
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
        Xm  = st.number_input("Reatância de magnetização — $X_m$ (Ω)",            min_value=0.1,   max_value=500.0,   value=_DEFAULTS["Xm"],  step=0.01,  key=wk["Xm"],  format="%.2f", disabled=dis)
        Xls = st.number_input("Reatância de dispersão do estator — $X_{ls}$ (Ω)", min_value=0.001, max_value=50.0,    value=_DEFAULTS["Xls"], step=0.001, key=wk["Xls"], format="%.3f", disabled=dis)
        Xlr = st.number_input("Reatância de dispersão do rotor — $X_{lr}$ (Ω)",   min_value=0.001, max_value=50.0,    value=_DEFAULTS["Xlr"], step=0.001, key=wk["Xlr"], format="%.3f", disabled=dis)
    else:
        f_ref  = 60.0
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
    J = st.number_input("Momento de inércia — $J$ (kg·m²)",               min_value=0.001, max_value=100.0, value=_DEFAULTS["J"], step=0.001, key=wk["J"], format="%.3f", disabled=dis)
    B = st.number_input("Coeficiente de atrito viscoso — $B$ (N·m·s/rad)", min_value=0.0,   max_value=10.0,  value=_DEFAULTS["B"], step=0.001, key=wk["B"], format="%.3f", disabled=dis)
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
    _Vfase_sat      = Vl / np.sqrt(3.0)
    _wb_sat         = 2.0 * np.pi * f
    _Lm_sat         = Xm / (2.0 * np.pi * (f_ref if input_mode == "X" else f))
    _Im0_sat        = round(_Vfase_sat / (_wb_sat * _Lm_sat), 2) if _Lm_sat > 0 else 5.0
    _Im_sat_default = round(2.0 * _Im0_sat, 1)

    with st.expander("⚙️ Parâmetros Avançados (IAS/Industrial)", expanded=False):
        # ── Saturação Magnética ──────────────────────────────────────────
        _pgroup("Saturação Magnética")
        sat_enable = st.checkbox(
            "Ativar modelo de saturação (Froelich)",
            value=False,
            key=wk["sat_enable"],
            disabled=dis,
            help=(
                "Substitui $L_m$ constante por $L_m(i_m) = L_{m0}/(1 + |i_m|/I_{sat})$. "
                "Reduz a superestimação do torque de partida. "
                "Desativado por padrão — use apenas com dados de ensaio de circuito aberto."
            ),
        )
        Im_sat = st.number_input(
            "Corrente de semi-saturação — $I_{sat}$ (A)",
            min_value=0.1, max_value=500.0,
            value=_Im_sat_default,
            step=0.1, format="%.1f",
            key=wk["Im_sat"],
            disabled=dis or not sat_enable,
            help=(
                f"Corrente de magnetização em que $L_m$ cai à metade de $L_{{m0}}$. "
                f"$I_{{m0}}$ estimada = {_Im0_sat:.2f} A  |  "
                f"Default = 2×$I_{{m0}}$ = {_Im_sat_default:.1f} A (saturação moderada). "
                "Reduza para saturação mais intensa."
            ),
        )
        if sat_enable:
            _lm_ratio = 1.0 / (1.0 + _Im0_sat / Im_sat) if Im_sat > 0 else 1.0
            st.caption(
                f"$I_{{m0}}$ ≈ {_Im0_sat:.2f} A  ·  "
                f"$L_m$ em regime ≈ {_lm_ratio * 100:.0f}% de $L_{{m0}}$  ·  "
                f"$t_{{max}}$ sugerido: ≥ {round(2.0 / _lm_ratio, 1):.1f} s"
            )
            if _lm_ratio < 0.7:
                st.warning(
                    f"Saturação intensa ($L_m$ cai para {_lm_ratio*100:.0f}%). "
                    f"Use $t_{{max}}$ ≥ {round(2.0 / _lm_ratio, 1):.1f} s para capturar o regime permanente."
                )
        st.markdown('</div>', unsafe_allow_html=True)

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
            _Zgrid_mag = float(np.sqrt(Rgrid**2 + (_wb_sat * Lgrid)**2))
            _ibox(
                f"Impedância de rede: $R_{{grid}}$ = {Rgrid:.4f} Ω  |  "
                f"$X_{{grid}}$ = {_wb_sat*Lgrid:.4f} Ω  |  "
                f"$|Z_{{grid}}|$ = {_Zgrid_mag:.4f} Ω. "
                "A tensão no terminal do motor será menor que $V_l$."
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Análise Econômica ────────────────────────────────────────────
        _pgroup("Análise Econômica")
        energy_tariff = st.number_input(
            "Tarifa de energia elétrica (R$/kWh)",
            min_value=0.01, max_value=5.0, value=0.75, step=0.01, format="%.2f",
            key=wk["energy_tariff"],
            disabled=dis,
            help=(
                "Tarifa média usada para projetar o custo operacional anual com base "
                "no perfil de carga simulado. Valor típico industrial: R$0,60–0,90/kWh."
            ),
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Modelagem Térmica ────────────────────────────────────────────
        _pgroup("🌡 Modelagem Térmica")
        _ibox(
            "Modelo de 1ª ordem: "
            "<i>dT/dt = (P<sub>joule</sub> + P<sub>fe</sub>) / C<sub>th</sub> "
            "− (T − T<sub>amb</sub>) / (R<sub>th</sub> · C<sub>th</sub>)</i>. "
            "Por padrão R<sub>th</sub> e C<sub>th</sub> são calculados automaticamente "
            "para ΔT = 105 K (Classe B) e τ = 300 s."
        )
        _th_override = st.checkbox(
            "Sobrescrever parâmetros térmicos manualmente",
            value=False,
            key=wk["th_override"],
            disabled=dis,
            help=(
                "Quando desmarcado, Rth e Cth são estimados automaticamente "
                "a partir dos parâmetros elétricos do motor. "
                "Marque apenas se você tiver valores medidos por ensaio térmico."
            ),
        )
        # Preview dos valores auto-calculados (sempre visível)
        _mp_preview = MachineParams(
            Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe,
            p=p, J=J, B=B, input_mode=input_mode, f_ref=f_ref,
            sat_enable=sat_enable, Im_sat=Im_sat,
            Rgrid=Rgrid, Lgrid=Lgrid,
            Rth=0.0, Cth=0.0,
        )
        if not _th_override:
            st.caption(
                f"Auto: **Rth ≈ {_mp_preview.Rth:.4f} K/W**  |  "
                f"**Cth ≈ {_mp_preview.Cth:.1f} J/K**  |  "
                f"τ = {_mp_preview.Rth * _mp_preview.Cth:.0f} s  |  "
                f"T_regime ≈ {_mp_preview.T_amb + _mp_preview.Rth * max(_mp_preview.Cth / _mp_preview.Rth * 0.01, 1.0):.0f} °C (estimativa)"
            )
        _th1, _th2 = st.columns(2)
        with _th1:
            Rth = st.number_input(
                "$R_{th}$ (K/W)",
                min_value=0.01, max_value=100.0,
                value=round(_mp_preview.Rth, 4) if not _th_override else 1.5,
                step=0.01, format="%.4f",
                key=wk["Rth"],
                disabled=dis or not _th_override,
                help=(
                    "Resistência térmica total motor→ambiente. "
                    "Motores fechados (TEFC) ~1–3 K/W; abertos (DRIP) ~0.5–1.5 K/W."
                ),
            )
        with _th2:
            Cth = st.number_input(
                "$C_{th}$ (J/K)",
                min_value=1.0, max_value=50000.0,
                value=round(_mp_preview.Cth, 1) if not _th_override else 200.0,
                step=10.0, format="%.1f",
                key=wk["Cth"],
                disabled=dis or not _th_override,
                help=(
                    "Capacitância térmica do conjunto estator+rotor. "
                    "~100–500 J/K para motores de 1–10 cv."
                ),
            )
        T_amb = st.number_input(
            "Temperatura ambiente $T_{amb}$ (°C)",
            min_value=-20.0, max_value=60.0, value=25.0, step=1.0, format="%.1f",
            key=wk["T_amb"],
            disabled=dis,
            help="Temperatura inicial do motor = temperatura do ambiente. Padrão IEC: 40°C.",
        )
        _tau_th = Rth * Cth
        st.caption(
            f"Constante de tempo térmica: τ = R·C = **{_tau_th:.0f} s** "
            f"({_tau_th/60:.1f} min)."
        )
        if _tau_th < 30:
            st.warning("τ < 30 s — motor aquece muito rapidamente. Verifique Rth e Cth.")
        # Quando não há override, passa 0.0 → __post_init__ calcula automaticamente
        _Rth_mp = Rth if _th_override else 0.0
        _Cth_mp = Cth if _th_override else 0.0
        st.markdown('</div>', unsafe_allow_html=True)

    mp = MachineParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe, p=p, J=J, B=B,
                       input_mode=input_mode, f_ref=f_ref,
                       sat_enable=sat_enable, Im_sat=Im_sat,
                       Rgrid=Rgrid, Lgrid=Lgrid,
                       Rth=_Rth_mp, Cth=_Cth_mp, T_amb=T_amb)
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
        "Aplicação de Carga (partida em vazio)":      "carga",
        "Pulso de Carga (aplica e retira)":            "pulso_carga",
        "Operação como Gerador":                       "gerador",
        "Desligamento (Corte de Alimentação)":         "shutdown",
        "Afundamento de Tensão (Voltage Sag)":         "voltage_sag",
    }
    exp_label = st.selectbox("Tipo de Experimento", list(exp_options.keys()), key=wk["exp_type"])
    exp_type  = exp_options[exp_label]
    config: dict[str, Any] = {"exp_type": exp_type, "exp_label": exp_label}

    _pgroup("Parâmetros de Carga e Tensão")

    if exp_type == "dol":
        config["Tl_final"] = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key=wk["Tl_final"])
        config["t_carga"]  = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk["t_carga"])

    elif exp_type == "yd":
        config["Tl_final"] = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key="wi_yd_Tl_final")
        config["t_2"]      = st.number_input("Instante de comutação Y → D — $t_2$ (s)", value=0.5, min_value=0.01, key="wi_yd_t2")
        config["t_carga"]  = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key="wi_yd_t_carga")
        _ibox("A tensão em estrela é reduzida a V<sub>l</sub>&thinsp;/&thinsp;√3. A comutação para triângulo ocorre no instante t<sub>2</sub>.")

    elif exp_type == "comp":
        config["Tl_final"]      = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key="wi_comp_Tl_final")
        config["voltage_ratio"] = st.slider("Tap do autotransformador — $k$ (%)", 10, 95, 50, key="wi_comp_tap") / 100.0
        config["t_2"]           = st.number_input("Instante de comutação — $t_2$ (s)", value=0.5, min_value=0.01, key="wi_comp_t2")
        config["t_carga"]       = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key="wi_comp_t_carga")
        _ibox(f"Tensão inicial = {config['voltage_ratio']*100:.0f}% de V<sub>l</sub> nominal.")

    elif exp_type == "soft":
        config["voltage_ratio"] = st.slider("Tensão inicial do Soft-Starter — $V_0$ (%)", 10, 90, 50, key="wi_soft_v0") / 100.0
        config["t_2"]           = st.number_input("Início da rampa de tensão — $t_2$ (s)", value=0.9, min_value=0.0, key="wi_soft_t2")
        config["t_pico"]        = st.number_input("Tempo para atingir tensão nominal — $t_{pico}$ (s)", value=5.0, min_value=0.1, key="wi_soft_t_pico")
        config["Tl_final"]      = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key="wi_soft_Tl_final")
        config["t_carga"]       = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key="wi_soft_t_carga")

    elif exp_type == "carga":
        Tl_nom = st.number_input("Torque nominal de referência — $T_{nom}$ (N·m)", value=80.0, min_value=0.1, key="wi_carga_Tl_nom")
        c_ini, c_fin = st.columns(2)
        with c_ini:
            pct_ini = st.number_input("Carga inicial (%)", value=0.0, min_value=0.0,
                                      help="Torque já presente no eixo antes da perturbação. 0% = partida em vazio.",
                                      key="wi_carga_pct_ini")
        with c_fin:
            pct_fin = st.number_input("Carga após perturbação (%)", value=100.0,
                                      help="Pode ser maior (sobrecarga), menor (alívio) ou negativo (torque motor externo).",
                                      key="wi_carga_pct_fin")
        config["Tl_inicial"] = Tl_nom * pct_ini / 100.0
        config["Tl_final"]   = Tl_nom * pct_fin / 100.0
        config["t_carga"]    = st.number_input("Instante da perturbação — $t_{carga}$ (s)", value=1.0, min_value=0.0, key="wi_carga_t_carga")
        delta = config["Tl_final"] - config["Tl_inicial"]
        sinal = "aumento" if delta > 0 else ("redução" if delta < 0 else "sem variação")
        _ibox(
            f"Motor parte com <strong>{config['Tl_inicial']:.2f} N·m</strong> ({pct_ini:.1f}%) "
            f"e em $t_{{carga}}$ o torque muda para <strong>{config['Tl_final']:.2f} N·m</strong> "
            f"({pct_fin:.1f}%) — <strong>{sinal} de {abs(delta):.2f} N·m</strong>."
        )
        # ── Gêmeo Digital: Barra Quebrada ─────────────────────────────
        st.write("")
        with st.expander("🔩 Gêmeo Digital — Falha de Barra Quebrada", expanded=False):
            _ibox(
                "Modela a falha introduzindo oscilação em $R_r$ à freq. de escorregamento: "
                "$R_r(t) = R_r \\cdot (1 + \\alpha \\cdot \\cos(2s\\omega_b t))$. "
                "A assinatura espectral da corrente exibirá componentes laterais em $(1 \\pm 2s)f$."
            )
            broken_bar_severity = st.slider(
                "Severidade da falha — $\\alpha$",
                min_value=0.0, max_value=0.5, value=0.0, step=0.01,
                format="%.2f",
                key=wk["broken_bar_severity"],
                help="0 = motor saudável. 0.1 = 10% de variação em Rr (≈1 barra quebrada). 0.3+ = falha grave.",
            )
            if broken_bar_severity > 0:
                st.caption(
                    f"α = {broken_bar_severity:.2f} — componentes laterais esperados em "
                    f"$(1 \\pm 2s)f$ Hz. Use a análise FFT para verificar a assinatura."
                )
                if broken_bar_severity >= 0.3:
                    st.warning("Severidade elevada (α ≥ 0.3) — pode causar oscilações visíveis no torque.")
            config["broken_bar_severity"] = broken_bar_severity

    elif exp_type == "pulso_carga":
        Tl_base = st.number_input("Torque de base — $T_{base}$ (N·m)", value=40.0, min_value=0.0, key=wk["Tl_pulso"])
        st.caption("Carga já presente no eixo antes e após o pulso. Use 0 para partida em vazio.")
        if Tl_base == 0.0:
            Tl_pulso = st.number_input("Torque durante o pulso — $T_{pulso}$ (N·m)", value=80.0, min_value=0.01, key=wk["Tl_pulso_abs"])
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
                    f"Motor parte em vazio. "
                    f"Pulso de <strong>{Tl_pulso:.2f} N·m</strong> de {t_on:.2f} s a {t_off:.2f} s "
                    f"(duração: {duracao:.2f} s). Após o pulso retorna ao vazio."
                )
            else:
                delta = Tl_pulso - Tl_base
                sinal = "aumento" if delta >= 0 else "redução"
                _ibox(
                    f"Base: <strong>{Tl_base:.2f} N·m</strong> contínua. "
                    f"Pulso de {t_on:.2f} s a {t_off:.2f} s ({duracao:.2f} s): "
                    f"{sinal} para <strong>{Tl_pulso:.2f} N·m</strong> "
                    f"({pct:+.1f}% de $T_{{base}}$)."
                )

    elif exp_type == "gerador":
        config["Tl_mec"] = st.number_input("Torque mecânico da turbina — $T_{mec}$ (N·m)", value=80.0, min_value=1.0, key=wk["Tl_mec"])
        config["t_2"]    = st.number_input("Instante de aplicação do torque — $t_2$ (s)", value=1.0, min_value=0.0, key=wk["t_2_gerador"])
        _ibox("O torque negativo impulsiona o rotor acima da velocidade síncrona, colocando a máquina em modo gerador.")

    elif exp_type == "shutdown":
        config["Tl_final"]  = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key="wi_sd_Tl_final")
        config["t_carga"]   = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=0.3, min_value=0.0, key="wi_sd_t_carga")
        config["t_cutoff"]  = st.number_input("Instante de desligamento — $t_{des}$ (s)", value=1.5, min_value=0.1, key="wi_sd_t_cutoff")
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
            "A tensão cai a zero em <i>t<sub>des</sub></i>, simulando abertura do contator ou falta de rede. "
            "A carga mecânica permanece ativa e freia o rotor até a parada completa (ω<sub>r</sub> travado em 0).<br><br>"
            f"⏱ <strong>Tempo de parada analítico (pós-corte): {_t_stop_mec:.2f} s</strong>"
            f" &nbsp;— calculado por "
            f"t<sub>stop</sub> = (J/B)·ln(1 + B·ω₀/T<sub>L</sub>)<br>"
            f"⏱ <strong>t<sub>end</sub> automático: {_t_end_sd:.2f} s</strong>"
            f" &nbsp;(t<sub>des</sub> + t<sub>stop</sub> × 1,2 — 20% de margem)<br>"
            "O torque eletromagnético decai em milissegundos (transitório elétrico); "
            "a velocidade segue a equação mecânica acima."
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
                value=80.0, min_value=0.0,
                key=wk["sag_Tl"],
                help="Carga mecânica aplicada desde o início da simulação.",
            )
            config["t_carga"] = 0.0
        t_start_sag    = st.number_input("Início do sag — $t_{sag}$ (s)",    value=0.5, min_value=0.0, step=0.05, format="%.3f", key=wk["t_start_sag"])
        t_duration_sag = st.number_input("Duração do sag — $\\Delta t_{sag}$ (s)", value=0.1, min_value=0.01, max_value=5.0, step=0.01, format="%.3f", key=wk["t_duration_sag"])
        t_end_sag = t_start_sag + t_duration_sag
        config["sag_magnitude"]  = sag_mag
        config["t_start_sag"]    = t_start_sag
        config["t_duration_sag"] = t_duration_sag
        _Vsag_line = mp.Vl * sag_mag
        _ibox(
            f"Tensão cai de <strong>{mp.Vl:.1f} V</strong> para "
            f"<strong>{_Vsag_line:.1f} V ({sag_mag*100:.0f}%)</strong> "
            f"em <i>t</i> = {t_start_sag:.3f} s durante {t_duration_sag*1000:.0f} ms "
            f"(retorno em {t_end_sag:.3f} s). "
            "O transitório de re-partida pós-sag é o principal evento de interesse."
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
        tmax = st.number_input("Tempo total — $t_{max}$ (s)", min_value=0.1, max_value=3600.0, value=2.0, step=0.1, format="%.1f", key=wk["tmax"])

        _etype = config.get("exp_type", "")
        if _etype == "dol":
            _t_last = config.get("t_carga", 1.0)
        elif _etype in ("yd", "comp"):
            _t_last = max(config.get("t_2", 0.5), config.get("t_carga", 1.0))
        elif _etype == "soft":
            _t_last = max(config.get("t_pico", 5.0), config.get("t_carga", 1.0))
        elif _etype == "carga":
            _t_last = config.get("t_carga", 1.0)
        elif _etype == "pulso_carga":
            _t_last = config.get("t_retirada", 1.5)
        elif _etype == "gerador":
            _t_last = config.get("t_2", 1.0)
        elif _etype == "shutdown":
            _tmax_sug = round(float(config.get("_t_end_shutdown", config.get("t_cutoff", 1.5))), 1)
            st.caption(f"Definido automaticamente: {_tmax_sug:.1f} s  (t_des + t_stop × 1,2 — analítico)")
            _t_last = None
        else:
            _t_last = 1.0
        if _t_last is not None:
            _tmax_sug = round(_t_last + 0.5, 1)
            st.caption(f"Sugestão: ≥ {_tmax_sug:.1f} s  (último evento + 0,5 s para atingir regime)")

        h = st.number_input("Passo de integração — $h$ (s)", min_value=0.000001, max_value=0.1, value=0.0001, step=0.000001, format="%.6f", key=wk["h"])
        n_steps = int(tmax / h)
        t_est_s = n_steps * 1.0e-4
        if t_est_s < 1:
            est_str = "< 1 s"
        elif t_est_s < 60:
            est_str = f"~{t_est_s:.0f} s"
        else:
            est_str = f"~{t_est_s/60:.1f} min"
        st.caption(f"Total de passos: {n_steps:,}  ·  Tempo estimado: {est_str}")
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
            _critical = [("aplicação da carga", r"t_{carga}", config.get("t_carga", 0))]
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
        elif _etype == "carga":
            _critical = [("aplicação da carga", r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "pulso_carga":
            _critical = [("aplicação da carga", r"t_{on}",  config.get("t_carga", 0)),
                         ("retirada da carga",  r"t_{off}", config.get("t_retirada", 0))]
        elif _etype == "gerador":
            _critical = [("aplicação do torque da turbina", r"t_2", config.get("t_2", 0))]
        elif _etype == "shutdown":
            _critical = [("aplicação da carga", r"t_{carga}", config.get("t_carga", 0)),
                         ("desligamento",        r"t_{des}",   config.get("t_cutoff", 0))]
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

    return config, var_keys, var_labels, tmax, h
