# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
import io
import json
import re
from typing import Any
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from dataclasses import fields


def _strip_latex(s: str) -> str:
    """Converte notação LaTeX $...$ para texto simples (uso em labels do Plotly)."""
    _greek = {
        '\\omega': 'ω', '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ',
        '\\delta': 'δ', '\\theta': 'θ', '\\tau': 'τ', '\\phi': 'φ',
        '\\psi': 'ψ', '\\lambda': 'λ', '\\mu': 'μ', '\\sigma': 'σ',
        '\\pi': 'π', '\\eta': 'η',
    }
    def _convert(m: re.Match) -> str:
        inner = m.group(1)
        for cmd, uni in _greek.items():
            inner = inner.replace(cmd, uni)
        inner = inner.replace('{', '').replace('}', '').replace('_', '').replace('\\', '')
        return inner
    return re.sub(r'\$([^$]+)\$', _convert, s)

from core.EMS_PY import MachineParams, run_simulation, build_fns
from ui.theme import _palette, apply_css
from viz.plotly_charts import build_fig_stacked, build_fig_sidebyside, build_fig_overlay
from ui.theory import render_theory_tab
from viz.pdf_report import generate_pdf_report
from viz.eqcircuit_plotter import render_circuit as _render_circuit_eqcircuit_plotter
from ui.clean_view import render_clean_view
from core.desequilibrio_falta import render_desequilibrio_ui

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACAO DA PAGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador de Máquinas Elétricas",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# ═══════════════════════════════════════════════════════════════════════════
# BLOCO C — TELA INICIAL
# ═══════════════════════════════════════════════════════════════════════════

MACHINES = [
    {"key": "mit",  "name": "Motor de Indução Trifásico",  "icon": "MIT", "tag": "Disponível",       "disabled": False},
    {"key": "sync", "name": "Gerador Sincrono",             "icon": "GS",  "tag": "Em desenvolvimento","disabled": True},
    {"key": "dc",   "name": "Motor de Corrente Continua",  "icon": "MCC", "tag": "Em desenvolvimento","disabled": True},
    {"key": "tr",   "name": "Transformador",                "icon": "TR",  "tag": "Em desenvolvimento","disabled": True},
]


def render_machine_selector(dark: bool) -> None:
    c = _palette(dark)
    ct_theme, _ = st.columns([1, 6])
    with ct_theme:
        st.toggle("Modo Escuro", value=dark, key="dark_mode")
    st.markdown('<p class="slabel">Seleção de Equipamento</p>', unsafe_allow_html=True)
    st.markdown("### Escolha o equipamento para simular")
    st.write("")

    # grid HTML puro — todos os cards com a mesma altura garantida
    cards_html = '<div class="machine-grid">'
    for m in MACHINES:
        active   = st.session_state.get("selected_machine") == m["key"]
        disabled = m["disabled"]
        cls     = "mcard" + (" active" if active else "") + (" disabled" if disabled else "")
        tag_cls = "mcard-tag" + (" soon" if disabled else "")
        cards_html += (
            f'<div class="{cls}">'
            f'  <span class="mcard-icon">{m["icon"]}</span>'
            f'  <div class="mcard-name">{m["name"]}</div>'
            f'  <span class="{tag_cls}">{m["tag"]}</span>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    st.write("")

    # botões de seleção abaixo do grid, alinhados por colunas
    cols = st.columns(4, gap="medium")
    for i, m in enumerate(MACHINES):
        with cols[i]:
            if not m["disabled"]:
                if st.button("Selecionar", key=f"sel_{m['key']}", width='stretch'):
                    st.session_state["selected_machine"] = m["key"]
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO D — LAYOUT PRINCIPAL DO MIT
# ═══════════════════════════════════════════════════════════════════════════

VARIABLE_CATALOG_MECANICAS = {
    "Torque Eletromagnético  Tₑ  (N·m)":              "Te",
    "Velocidade do Rotor  n  (RPM)":                   "n",
    "Velocidade Angular  ωᵣ  (rad/s)":                 "wr",
}

VARIABLE_CATALOG_ELETRICAS = {
    "Corrente de Fase A — Estator  iₐₛ  (A)":         "ias",
    "Corrente de Fase B — Estator  ibₛ  (A)":         "ibs",
    "Corrente de Fase C — Estator  icₛ  (A)":         "ics",
    "Corrente de Fase A — Rotor  iₐᵣ  (A)":           "iar",
    "Corrente de Fase B — Rotor  ibᵣ  (A)":           "ibr",
    "Corrente de Fase C — Rotor  icᵣ  (A)":           "icr",
    "Componente d — Estator  idₛ  (A)":               "ids",
    "Componente q — Estator  iqₛ  (A)":               "iqs",
    "Componente d — Rotor  idᵣ  (A)":                 "idr",
    "Componente q — Rotor  iqᵣ  (A)":                 "iqr",
    "Tensão de Fase  Vₐ  (V)":                        "Va",
    "Tensão de Fase  Vb  (V)":                        "Vb",
    "Tensão de Fase  Vc  (V)":                        "Vc",
}

VARIABLE_CATALOG = {**VARIABLE_CATALOG_MECANICAS, **VARIABLE_CATALOG_ELETRICAS}


def _pgroup(title: str) -> None:
    st.markdown(f'<div class="pgroup-title">{title}</div>', unsafe_allow_html=True)


def _ibox(html: str) -> None:
    st.markdown(f'<div class="ibox">{html}</div>', unsafe_allow_html=True)


# Valores nominais padrao para o Modo Experimento
_DEFAULTS = dict(
    Vl=220.0, f=60.0, Rs=0.435, Rr=0.816, Xm=26.13,
    Xls=0.754, Xlr=0.754, Rfe=500.0, p=4, J=0.089, B=0.005,
)



# Mapeamento: campo lógico → key do widget no session_state
_WK = {
    "Vl":           "wi_Vl",
    "f":            "wi_f",
    "Rs":           "wi_Rs",
    "Rr":           "wi_Rr",
    "input_mode":   "wi_input_mode",
    "f_ref":        "wi_f_ref",
    "Xm":           "wi_Xm",    # reatância (Ω) no modo X
    "Xls":          "wi_Xls",
    "Xlr":          "wi_Xlr",
    "Xm_L":         "wi_Xm_L",  # indutância (H) no modo L
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
    "Tl_pulso":     "wi_Tl_pulso",     # pulso_carga: torque de base
    "Tl_pulso_abs": "wi_Tl_pulso_abs", # pulso_carga: torque absoluto do pulso (base=0)
    "t_pulso_on":   "wi_t_pulso_on",  # pulso_carga: instante de aplicação
    "t_pulso_off":  "wi_t_pulso_off", # pulso_carga: instante de retirada
    "Tl_mec":       "wi_Tl_mec",      # gerador: torque mecânico da turbina
    "t_2_gerador":  "wi_t_2_gerador", # gerador: instante de aplicação do torque
    "tmax":         "wi_tmax",
    "h":            "wi_h",
}

# ── Presets de motores catalogados ───────────────────────────────────────────
_PRESETS: dict[str, dict[str, Any]] = {
    "Padrão": {
        # Elétricos
        "Vl": 220.0, "f": 60.0, "Rs": 0.435, "Rr": 0.816,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 60.0, "Xm": 26.13, "Xls": 0.754, "Xlr": 0.754, "Rfe": 500.0,
        # Mecânicos
        "p": 4, "J": 0.089, "B": 0.005,
        # Experimento
        "exp_type": "Partida Direta (DOL)",
    },
    "Usta (2024)": {
        # Elétricos
        "Vl": 220.0, "f": 50.0, "Rs": 2.65, "Rr": 2.85,
        "input_mode": "Reatâncias (Ω)  —  medidas em $f_{ref}$",
        "f_ref": 50.0, "Xm": 60.98, "Xls": 4.43, "Xlr": 5.69, "Rfe": 500.0,
        # Mecânicos
        "p": 4, "J": 0.025, "B": 0.001,
        # Experimento
        "exp_type": "Pulso de Carga (aplica e retira)",
        "Tl_pulso": 0.0, "Tl_pulso_abs": 10.0, "t_pulso_on": 0.6, "t_pulso_off": 0.8,
        "tmax": 1.0,
    },
}

# Valores de radio como aparecem na UI
_INPUT_MODE_LABELS = [
    "Reatâncias (Ω)  —  medidas em $f_{ref}$",
    "Indutâncias (H)  —  independentes de frequência",
]


def _validate_params(mp) -> None:
    """Emite avisos na UI quando parâmetros estão fora de faixas fisicamente plausíveis."""
    warns = []
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


def render_machine_params(dark: bool, experiment_mode: bool) -> tuple[MachineParams, int]:
    """Coluna esquerda: todos os campos de parâmetros. Retorna (mp, ref_code)."""
    st.markdown('<p class="slabel">Parâmetros Físicos da Máquina</p>', unsafe_allow_html=True)

    # ── Presets ───────────────────────────────────────────────────────────────
    # Reset flag must be applied BEFORE the selectbox widget is instantiated
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
                "Vl": _WK["Vl"], "f": _WK["f"], "Rs": _WK["Rs"], "Rr": _WK["Rr"],
                "input_mode": _WK["input_mode"], "f_ref": _WK["f_ref"],
                "Xm": _WK["Xm"], "Xls": _WK["Xls"], "Xlr": _WK["Xlr"],
                "Rfe": _WK["Rfe"], "p": _WK["p"], "J": _WK["J"], "B": _WK["B"],
                "exp_type": _WK["exp_type"],
                "Tl_pulso": _WK["Tl_pulso"],
                "Tl_pulso_abs": _WK["Tl_pulso_abs"],
                "t_pulso_on": _WK["t_pulso_on"],
                "t_pulso_off": _WK["t_pulso_off"],
                "tmax": _WK["tmax"],
            }
            for key, wk in _wk_preset.items():
                if key in pdata:
                    st.session_state[wk] = pdata[key]
            st.session_state["_reset_preset_select"] = True
            st.rerun()

    if experiment_mode:
        _ibox("<strong>Parâmetros travados</strong> — desative o toggle para editar.")

    dis = experiment_mode   # alias curto

    # ── Eletricos ─────────────────────────────────────────────────────────
    _pgroup("Dados Elétricos")
    Vl  = st.number_input("Tensão de linha RMS — $V_l$ (V)",               min_value=50.0,  max_value=15000.0, value=_DEFAULTS["Vl"],  step=1.0,   key=_WK["Vl"],  disabled=dis)
    f   = st.number_input("Frequência da rede — $f$ (Hz)",                min_value=1.0,   max_value=400.0,   value=_DEFAULTS["f"],   step=1.0,   key=_WK["f"],   disabled=dis)
    Rs  = st.number_input("Resistência do estator — $R_s$ (Ω)",           min_value=0.001, max_value=100.0,   value=_DEFAULTS["Rs"],  step=0.001, key=_WK["Rs"],  format="%.3f", disabled=dis)
    Rr  = st.number_input("Resistência do rotor — $R_r$ (Ω)",             min_value=0.001, max_value=100.0,   value=_DEFAULTS["Rr"],  step=0.001, key=_WK["Rr"],  format="%.3f", disabled=dis)

    # ── Modo de entrada dos parâmetros magnéticos ──────────────────────────
    input_mode_label = st.radio(
        "Modo de entrada dos parâmetros magnéticos",
        _INPUT_MODE_LABELS,
        index=0,
        key=_WK["input_mode"],
        disabled=dis,
        horizontal=True,
    )
    input_mode = "X" if input_mode_label.startswith("Reatâncias") else "L"

    if input_mode == "X":
        f_ref = st.number_input(
            "Frequência de referência dos ensaios — $f_{ref}$ (Hz)",
            min_value=1.0, max_value=400.0, value=60.0, step=1.0,
            key=_WK["f_ref"],
            help="Frequência em que $X_m$, $X_{ls}$ e $X_{lr}$ foram medidos (tipicamente 50 Hz ou 60 Hz).",
            disabled=dis,
        )
        Xm  = st.number_input("Reatância de magnetização — $X_m$ (Ω)",            min_value=0.1,   max_value=500.0,   value=_DEFAULTS["Xm"],  step=0.01,  key=_WK["Xm"],  format="%.2f", disabled=dis)
        Xls = st.number_input("Reatância de dispersão do estator — $X_{ls}$ (Ω)", min_value=0.001, max_value=50.0,    value=_DEFAULTS["Xls"], step=0.001, key=_WK["Xls"], format="%.3f", disabled=dis)
        Xlr = st.number_input("Reatância de dispersão do rotor — $X_{lr}$ (Ω)",   min_value=0.001, max_value=50.0,    value=_DEFAULTS["Xlr"], step=0.001, key=_WK["Xlr"], format="%.3f", disabled=dis)
    else:
        f_ref = 60.0  # irrelevante no modo L, mas necessário para MachineParams
        _wb_ref = 2.0 * 3.141592653589793 * 60.0
        Xm  = st.number_input("Indutância de magnetização — $L_m$ (H)",            min_value=1e-6, max_value=10.0, value=round(_DEFAULTS["Xm"]  / _wb_ref, 6), step=0.0001, key=_WK["Xm_L"],  format="%.6f", disabled=dis)
        Xls = st.number_input("Indutância de dispersão do estator — $L_{ls}$ (H)", min_value=1e-6, max_value=1.0,  value=round(_DEFAULTS["Xls"] / _wb_ref, 6), step=0.0001, key=_WK["Xls_L"], format="%.6f", disabled=dis)
        Xlr = st.number_input("Indutância de dispersão do rotor — $L_{lr}$ (H)",   min_value=1e-6, max_value=1.0,  value=round(_DEFAULTS["Xlr"] / _wb_ref, 6), step=0.0001, key=_WK["Xlr_L"], format="%.6f", disabled=dis)

    Rfe = st.number_input("Resistência de perdas no ferro — $R_{fe}$ (Ω)",   min_value=10.0,  max_value=10000.0, value=_DEFAULTS["Rfe"], step=10.0, key=_WK["Rfe"], format="%.1f", disabled=dis)
    st.caption("$R_{fe}$ é usado apenas no cálculo de potências e rendimento em regime permanente — não afeta a dinâmica da simulação.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Mecanicos ─────────────────────────────────────────────────────────
    _pgroup("Dados Mecânicos e Referencial")
    p   = st.selectbox("Número de polos — $p$", options=[2, 4, 6, 8, 10, 12], index=1, key=_WK["p"], disabled=dis)
    J   = st.number_input("Momento de inércia — $J$ (kg·m²)",              min_value=0.001, max_value=100.0, value=_DEFAULTS["J"], step=0.001, key=_WK["J"], format="%.3f", disabled=dis)
    B   = st.number_input("Coeficiente de atrito viscoso — $B$ (N·m·s/rad)", min_value=0.0, max_value=10.0, value=_DEFAULTS["B"], step=0.001, key=_WK["B"], format="%.3f", disabled=dis)
    ref_label = st.selectbox(
        "Referencial da Transformada de Park",
        ["Síncrono  (ω = ωₑ)", "Rotórico  (ω = ωᵣ)", "Estacionário  (ω = 0)"],
        disabled=dis,
    )
    ref_code = {"Síncrono  (ω = ωₑ)": 1,
                "Rotórico  (ω = ωᵣ)": 2,
                "Estacionário  (ω = 0)": 3}[ref_label]
    st.markdown('</div>', unsafe_allow_html=True)

    mp = MachineParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe, p=p, J=J, B=B,
                       input_mode=input_mode, f_ref=f_ref)

    # validação física dos parâmetros
    _validate_params(mp)

    # grandezas derivadas
    st.write("")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Velocidade Síncrona $n_s$", f"{mp.n_sync:.1f} RPM")
    mc2.metric("Velocidade Angular Base $\\omega_b$", f"{mp.wb/(mp.p/2):.2f} rad/s")
    mc3.metric("Reatância Mútua $X_{ml}$", f"{mp.Xml:.4f} Ω")
    if input_mode == "X":
        st.caption(f"Indutâncias calculadas a {f_ref:.0f} Hz → $L_m$ = {mp.Lm*1000:.4f} mH  |  $L_{{ls}}$ = {mp.Lls*1000:.4f} mH  |  $L_{{lr}}$ = {mp.Llr*1000:.4f} mH")

    return mp, ref_code


def render_experiment_config(mp: MachineParams) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    """Abaixo do circuito: configuracao do experimento."""
    st.markdown('<p class="slabel">Experimento</p>', unsafe_allow_html=True)

    exp_options = {
        "Partida Direta (DOL)":                       "dol",
        "Partida Estrela-Triângulo (Y-D)":             "yd",
        "Partida com Autotransformador":               "comp",
        "Soft-Starter (Rampa de Tensão)":              "soft",
        "Aplicação de Carga (partida em vazio)":      "carga",
        "Pulso de Carga (aplica e retira)":            "pulso_carga",
        "Operação como Gerador":                       "gerador",
        "Desligamento (Corte de Alimentação)":         "shutdown",
    }
    exp_label = st.selectbox("Tipo de Experimento", list(exp_options.keys()), key=_WK["exp_type"])
    exp_type  = exp_options[exp_label]
    config: dict[str, Any] = {"exp_type": exp_type, "exp_label": exp_label}

    _pgroup("Parâmetros de Carga e Tensão")

    if exp_type == "dol":
        config["Tl_final"] = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key=_WK["Tl_final"])
        config["t_carga"]  = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=_WK["t_carga"])

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

    elif exp_type == "pulso_carga":
        Tl_base = st.number_input("Torque de base — $T_{base}$ (N·m)", value=40.0, min_value=0.0, key=_WK["Tl_pulso"])
        st.caption("Carga já presente no eixo antes e após o pulso. Use 0 para partida em vazio.")
        if Tl_base == 0.0:
            Tl_pulso = st.number_input("Torque durante o pulso — $T_{pulso}$ (N·m)", value=80.0, min_value=0.01, key=_WK["Tl_pulso_abs"])
            st.caption("Torque aplicado no intervalo $[t_{on},\\, t_{off})$. Fora desse intervalo o motor opera em vazio.")
        else:
            pct      = st.number_input("Variação durante o pulso (%)", value=50.0, key="wi_pct_pulso")
            st.caption("Percentual de $T_{base}$ adicionado (positivo) ou subtraído (negativo) durante o pulso.")
            Tl_pulso = Tl_base * (1.0 + pct / 100.0)
        config["Tl_base"]  = Tl_base
        config["Tl_final"] = Tl_pulso
        t_on  = st.number_input("Instante de aplicação do pulso — $t_{on}$ (s)",  value=1.0, min_value=0.0, step=0.1, format="%.2f", key=_WK["t_pulso_on"])
        t_off = st.number_input("Instante de retirada do pulso — $t_{off}$ (s)", value=1.5, min_value=0.0, step=0.1, format="%.2f", key=_WK["t_pulso_off"])
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
        config["Tl_mec"] = st.number_input("Torque mecânico da turbina — $T_{mec}$ (N·m)", value=80.0, min_value=1.0, key=_WK["Tl_mec"])
        config["t_2"]    = st.number_input("Instante de aplicação do torque — $t_2$ (s)", value=1.0, min_value=0.0, key=_WK["t_2_gerador"])
        _ibox("O torque negativo impulsiona o rotor acima da velocidade síncrona, colocando a máquina em modo gerador.")

    elif exp_type == "shutdown":
        config["Tl_final"]  = st.number_input("Torque de carga — $T_l$ (N·m)", value=80.0, min_value=0.0, key="wi_sd_Tl_final")
        config["t_carga"]   = st.number_input("Instante de aplicação da carga — $t_{carga}$ (s)", value=0.3, min_value=0.0, key="wi_sd_t_carga")
        config["t_cutoff"]  = st.number_input("Instante de desligamento — $t_{des}$ (s)", value=1.5, min_value=0.1, key="wi_sd_t_cutoff")
        if config["t_carga"] >= config["t_cutoff"]:
            st.error(f"t_carga ({config['t_carga']:.2f} s) deve ser menor que t_des ({config['t_cutoff']:.2f} s). Aplique a carga antes do desligamento.")
            config["_invalid"] = True
        # ── tempo de parada analítico ─────────────────────────────────────
        # dω/dt = -(T_L + B·ω) / J  →  t_stop = (J/B)·ln(1 + B·ω₀/T_L)
        # ω₀ estimado como velocidade síncrona (pior caso: motor sem escorregamento)
        _ws      = 2.0 * np.pi * mp.f / (mp.p / 2)   # velocidade síncrona (rad/s)
        _Tl_sd   = config["Tl_final"]
        _B_sd    = mp.B
        _J_sd    = mp.J
        if _B_sd > 0 and _Tl_sd > 0:
            _t_stop_mec = (_J_sd / _B_sd) * np.log(1.0 + _B_sd * _ws / _Tl_sd)
        elif _Tl_sd > 0:
            # B ≈ 0: desaceleração linear → t_stop = J·ω₀/T_L
            _t_stop_mec = _J_sd * _ws / _Tl_sd
        else:
            # sem carga: usa 5·τ_m como fallback conservador
            _tau_m_fb   = _J_sd / _B_sd if _B_sd > 0 else 10.0
            _t_stop_mec = 5.0 * _tau_m_fb
        _t_end_sd = config["t_cutoff"] + _t_stop_mec * 1.2
        config["_t_end_shutdown"] = float(_t_end_sd)   # tmax dinâmico passado ao solver
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
    # para shutdown, sincroniza wi_tmax com o t_end analítico apenas quando os
    # parâmetros que o determinam mudaram — preserva edições manuais do usuário
    if config.get("exp_type") == "shutdown" and "_t_end_shutdown" in config:
        _sd_hash = hashlib.md5(
            json.dumps([mp.J, mp.B, config.get("Tl_final"), config.get("t_cutoff")]).encode()
        ).hexdigest()
        if st.session_state.get("_sd_tmax_hash") != _sd_hash:
            st.session_state[_WK["tmax"]] = round(float(config["_t_end_shutdown"]), 1)
            st.session_state["_sd_tmax_hash"] = _sd_hash
    tc1, tc2 = st.columns(2)
    with tc1:
        tmax = st.number_input("Tempo total — $t_{max}$ (s)", min_value=0.1, max_value=3600.0, value=2.0, step=0.1, format="%.1f", key=_WK["tmax"])

        # ── sugestão de tmax ─────────────────────────────────────────────
        _etype  = config.get("exp_type", "")
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

        h    = st.number_input("Passo de integração — $h$ (s)", min_value=0.000001, max_value=0.1, value=0.0001, step=0.000001, format="%.6f", key=_WK["h"])
        n_steps = int(tmax / h)
        t_est_s = n_steps * 1.0e-4          # ~0.1 ms/passo (odeint + overhead Python)
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

        # ── verificação: tmax cobre todos os eventos do experimento ──────
        # tuplas: (descrição, símbolo LaTeX, valor)
        _critical = []
        _etype = config.get("exp_type", "")
        if _etype == "dol":
            _critical = [("aplicação da carga", r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "yd":
            _critical = [("comutação Y→D",       r"t_2",      config.get("t_2", 0)),
                         ("aplicação da carga",  r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "comp":
            _critical = [("comutação do autotransformador", r"t_2",      config.get("t_2", 0)),
                         ("aplicação da carga",             r"t_{carga}", config.get("t_carga", 0))]
        elif _etype == "soft":
            _critical = [("início da rampa",          r"t_2",      config.get("t_2", 0)),
                         ("tensão nominal atingida",  r"t_{pico}", config.get("t_pico", 0)),
                         ("aplicação da carga",       r"t_{carga}", config.get("t_carga", 0))]
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
                    f"$t_{{max}}$ ({tmax:.2f} s) ≤ ${ _sym}$ ({_t:.2f} s): "
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


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO E — CIRCUITO EQUIVALENTE (delegado a eqcircuit_plotter.py)
# ═══════════════════════════════════════════════════════════════════════════

def render_circuit(mp: MachineParams, dark: bool) -> None:
    """Delega o desenho do circuito equivalente para eqcircuit_plotter.py."""
    _render_circuit_eqcircuit_plotter(mp, dark, _palette)


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO F — RESULTADOS
# ═══════════════════════════════════════════════════════════════════════════

def _kpis_destaque(res: dict, exp_type: str, mp: MachineParams, d: int, t_events: list | None = None) -> list[tuple]:
    """Retorna lista de (label, valor, unidade) com KPIs prioritarios por experimento."""
    ias_pk  = float(np.max(np.abs(res["ias"])))
    Te_max  = float(np.max(res["Te"]))
    n_ss    = res["n_ss"]
    ias_rms = res["ias_rms"]
    s_val   = res.get("s", 0.0)

    # corrente nominal estimada: Vl / (sqrt(3) * Rs) -- aprox a plena carga
    i_nom_est = (mp.Vl / np.sqrt(3.0)) / mp.Rs if mp.Rs > 0 else 1.0
    fator_pk  = ias_pk / ias_rms if ias_rms > 0 else 0.0

    if exp_type in ("dol", "yd", "comp", "soft"):
        # partidas: destaque de corrente de pico e torque maximo
        items = [
            ("Corrente de Pico $i_{as}$", f"{ias_pk:.{d}f}", "A"),
            ("Fator de Pico  ($I_{pk}$ / $I_{rms}$)", f"{fator_pk:.{d}f}", "—"),
            ("Torque Máximo $T_{e,max}$", f"{Te_max:.{d}f}", "N·m"),
            ("Velocidade Final", f"{n_ss:.{d}f}", "RPM"),
        ]
        if exp_type == "yd":
            # segundo pico: maximo apos o evento de comutacao
            _tevs = t_events or []
            t_ev = _tevs[1] if len(_tevs) > 1 else (_tevs[0] if _tevs else 0.0)
            t    = res["t"]
            idx  = int(np.searchsorted(t, t_ev))
            ias_pk2 = float(np.max(np.abs(res["ias"][idx:]))) if idx < len(t) else 0.0
            items.insert(1, ("Corrente de Pico pos-comutacao Y→D", f"{ias_pk2:.{d}f}", "A"))
        elif exp_type == "comp":
            _tevs = t_events or []
            t_ev_comp = _tevs[0] if _tevs else 0.0
            t_comp = res["t"]
            idx_comp = int(np.searchsorted(t_comp, t_ev_comp))
            ias_pk2_comp = float(np.max(np.abs(res["ias"][idx_comp:]))) if idx_comp < len(t_comp) else 0.0
            items.insert(1, ("Corrente de Pico pos-comutacao AT", f"{ias_pk2_comp:.{d}f}", "A"))

    elif exp_type == "carga":
        _tevs_c = t_events or []
        t_carga_ev = _tevs_c[0] if _tevs_c else 0.0
        idx_tc = max(int(np.searchsorted(res["t"], t_carga_ev)), 1)
        n_antes  = float(np.mean(res["n"][:idx_tc]))
        delta_n  = n_antes - n_ss
        delta_i  = ias_rms - float(np.sqrt(np.mean(res["ias"][:idx_tc]**2)))
        lbl_antes = "Velocidade Antes da Perturbação"
        lbl_delta = "Afundamento de Velocidade" if delta_n >= 0 else "Elevação de Velocidade"
        items = [
            (lbl_antes,              f"{n_antes:.{d}f}",       "RPM"),
            ("Velocidade após Perturbação", f"{n_ss:.{d}f}",   "RPM"),
            (lbl_delta,              f"{abs(delta_n):.{d}f}",  "RPM"),
            ("Variação de Corrente RMS",    f"{delta_i:.{d}f}", "A"),
        ]

    elif exp_type == "gerador":
        P_out = res.get("P_out", 0.0)
        eta   = res.get("eta",   0.0)
        lbl_p = "kW" if abs(P_out) >= 1000 else "W"
        val_p = P_out / 1000 if abs(P_out) >= 1000 else P_out
        items = [
            ("Potencia Gerada para a Rede", f"{val_p:.{d}f}", lbl_p),
            ("Escorregamento", f"{s_val*100:.{d}f}", "%"),
            ("Rendimento", f"{eta:.{d}f}", "%"),
            ("Corrente RMS de Geracao", f"{ias_rms:.{d}f}", "A"),
        ]

    elif exp_type == "shutdown":
        _tevs   = t_events or []
        t_cut   = _tevs[1] if len(_tevs) > 1 else (_tevs[0] if _tevs else 0.0)
        t_arr   = res["t"]
        idx_cut = int(np.searchsorted(t_arr, t_cut))
        # velocidade imediatamente antes do corte (média dos últimos 5% de amostras pré-corte)
        w0    = max(1, idx_cut - max(1, idx_cut // 20))
        n_pre = float(np.mean(res["n"][w0:idx_cut])) if idx_cut > 0 else 0.0
        n_final = float(np.mean(res["n"][-max(1, len(res["n"]) // 10):]))
        # tempo de parada estimado: primeiro índice pós-corte onde |n| < 1% de n_pre
        thresh   = 0.01 * n_pre if n_pre > 0 else 1.0
        stop_idx = int(np.searchsorted(np.abs(res["n"][idx_cut:]), thresh, side="right"))
        t_stop   = float(t_arr[idx_cut + stop_idx]) if stop_idx < len(t_arr) - idx_cut else float(t_arr[-1])
        items = [
            ("Velocidade pré-desligamento",  f"{n_pre:.{d}f}",   "RPM"),
            ("Velocidade final simulada",    f"{n_final:.{d}f}",  "RPM"),
            ("Instante do corte",            f"{t_cut:.{d}f}",    "s"),
            ("Tempo de parada estimado",     f"{t_stop:.{d}f}",   "s"),
            ("Corrente de pico (partida)",   f"{ias_pk:.{d}f}",   "A"),
        ]

    else:
        items = []

    return items


def render_results(res: dict[str, Any], var_keys: list[str], var_labels: list[str],
                   dark: bool, t_events: list, mp: MachineParams,
                   exp_label: str, exp_type: str = "dol", decimals: int = 3,
                   ref_list: list | None = None,
                   primary_color: str | None = None,
                   is_mobile: bool = False) -> None:
    """KPIs + graficos + botao PDF."""
    st.divider()

    # ── Destaques por experimento ─────────────────────────────────────────
    destaques = _kpis_destaque(res, exp_type, mp, decimals, t_events)
    if destaques:
        st.markdown('<p class="slabel">Destaques do Experimento</p>', unsafe_allow_html=True)
        cols = st.columns(len(destaques))
        for col, (lbl, val, unit) in zip(cols, destaques):
            col.metric(f"{lbl} ({unit})", val)
        st.write("")

    d = decimals  # alias curto

    # shutdown não tem regime permanente — omite toda a seção
    if exp_type != "shutdown":
        st.markdown('<p class="slabel">Indicadores de Regime Permanente</p>',
                    unsafe_allow_html=True)

        n_ss    = res["n_ss"]
        Te_ss   = res["Te_ss"]
        wr_ss   = res["wr_ss"]
        ias_rms = res["ias_rms"]
        Te_max  = float(np.max(res["Te"]))
        ias_pk  = float(np.max(np.abs(res["ias"])))

        def fmt_pot(val, d):
            if abs(val) >= 1000:
                return "kW", f"{val/1000:.{d}f}"
            return "W", f"{val:.{d}f}"

        # linha 1 — grandezas mecânicas/elétricas de regime
        # gerador: oculta Te_max (é artefato da partida, não do modo gerador)
        # carga/pulso_carga: oculta corrente de pico (pico é da partida em vazio)
        _show_Te_max = exp_type not in ("gerador",)
        _show_ias_pk = exp_type not in ("carga", "pulso_carga")

        _row1 = [
            ("Velocidade de Regime (RPM)",        f"{n_ss:.{d}f}"),
            ("Torque de Regime $T_e$ (N·m)",      f"{Te_ss:.{d}f}"),
        ]
        if _show_Te_max:
            _row1.append(("Torque Máximo $T_{e,max}$ (N·m)", f"{Te_max:.{d}f}"))
        if _show_ias_pk:
            _row1.append(("Corrente de Pico $i_{as}$ (A)",   f"{ias_pk:.{d}f}"))
        _row1 += [
            ("Corrente RMS $i_{as}$ (A)",         f"{ias_rms:.{d}f}"),
            ("Vel. Angular $\\omega_r$ (rad/s)",  f"{wr_ss:.{d}f}"),
        ]
        k = st.columns(len(_row1))
        for col, (lbl, val) in zip(k, _row1):
            col.metric(lbl, val)

        s_val   = res.get('s', 0.0)
        gerador = s_val < 0

        u_in, v_in = fmt_pot(res.get('P_in',  0.0), d)
        u0,   v0   = fmt_pot(abs(res.get('P_gap',  0.0)), d)
        u1,   v1   = fmt_pot(abs(res.get('P_mec',  0.0)), d)
        u2,   v2   = fmt_pot(res.get('P_cu_r', 0.0), d)

        lbl_in  = f"P. Mec. Turbina ({u_in})"    if gerador else f"P. Entrada ({u_in})"
        lbl_gap = f"P. Entreferro Gerada ({u0})"  if gerador else f"P. Entreferro ({u0})"
        lbl_mec = f"P. Mec. Entrada ({u1})"       if gerador else f"P. Mecanica ({u1})"

        u_out, v_out = fmt_pot(res.get('P_out', 0.0), d)

        k2 = st.columns(6)
        if gerador:
            k2[0].metric(lbl_in,                       v_in)
            k2[1].metric(lbl_gap,                      v0)
            k2[2].metric(f"P. Gerada Rede ({u_out})",  v_out)
            k2[3].metric(f"Perdas Rotor ({u2})",       v2)
        else:
            k2[0].metric(lbl_in,                       v_in)
            k2[1].metric(lbl_gap,                      v0)
            k2[2].metric(lbl_mec,                      v1)
            k2[3].metric(f"Perdas Rotor ({u2})",       v2)
        k2[4].metric("Rendimento (%)",      f"{res.get('eta', 0.0):.{d}f}")
        k2[5].metric("Escorregamento (%)",  f"{s_val*100:.{d}f}")

    st.write("")

    if not var_keys:
        st.info("Nenhuma grandeza selecionada. Retorne à configuração e escolha variáveis para plotar.")
        return

    # controles de visualizacao
    cv1, cv2, cv3 = st.columns([1.6, 1, 1.5])
    with cv1:
        _viz_opts = ["Empilhados", "Sobrepostos"] if is_mobile else ["Empilhados", "Lado a lado", "Sobrepostos"]
        # garante que o valor salvo ainda exista nas opções
        _cur_modo = st.session_state.get("plot_mode", _viz_opts[0])
        if _cur_modo not in _viz_opts:
            st.session_state["plot_mode"] = _viz_opts[0]
        modo = st.radio(
            "Modo de Visualização",
            _viz_opts,
            horizontal=True,
            key="plot_mode",
        )
    with cv2:
        dark_plot = st.toggle("Fundo escuro", value=dark, key="plot_dark_toggle")
    with cv3:
        zoom_mode = st.radio(
            "Zoom",
            ["Completo", "Partida", "Regime Permanente"],
            horizontal=True,
            key="zoom_mode",
        )

    st.write("")

    # ── Janela de zoom baseada na seleção do usuário ──────────────────────
    x_zoom    = None
    tmax_data = float(res["t"][-1])
    t_ss_idx  = int(res.get("_ss_start", 0))
    t_ss      = float(res["t"][t_ss_idx]) if t_ss_idx < len(res["t"]) else tmax_data

    if zoom_mode == "Regime Permanente":
        # do início do regime permanente até o fim, com pequena margem à esquerda
        x_zoom = [max(0.0, t_ss - max(0.05 * tmax_data, 0.02)), tmax_data]
    elif zoom_mode == "Partida":
        # do instante 0 até logo após o regime permanente ser atingido
        #x_zoom = [0.0, min(t_ss * 1.08 + 0.01, tmax_data)]
        x_zoom = [0.0, min(t_ss * 1.08 + 0.01, 0.2)]

    def _apply_zoom(fig: go.Figure) -> go.Figure:
        if x_zoom is None:
            return fig
        x0, x1 = x_zoom
        fig.update_xaxes(range=[x0, x1], autorange=False)
        # calcula range Y apenas com os pontos visíveis na janela X
        groups: dict = {}
        for trace in fig.data:
            xs = getattr(trace, "x", None)
            ys = getattr(trace, "y", None)
            if xs is None or ys is None:
                continue
            ya = getattr(trace, "yaxis", None) or "y"
            xs_a = np.asarray(xs, dtype=float)
            ys_a = np.asarray(ys, dtype=float)
            mask = (xs_a >= x0) & (xs_a <= x1) & np.isfinite(ys_a)
            if not mask.any():
                continue
            groups.setdefault(ya, []).append(ys_a[mask])
        for ya, arrays in groups.items():
            all_y = np.concatenate(arrays)
            ymin, ymax = float(all_y.min()), float(all_y.max())
            span = ymax - ymin
            pad  = span * 0.15 if span > 0 else (abs(ymax) * 0.10 if ymax != 0 else 0.1)
            axis_key = "yaxis" if ya == "y" else f"yaxis{ya[1:]}"
            ax = getattr(fig.layout, axis_key, None)
            if ax is not None:
                ax.range    = [ymin - pad, ymax + pad]
                ax.autorange = False
        return fig

    _PLOT_CFG = {
        "responsive": True,
        "scrollZoom": False,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": "grafico_simulador",
            "scale": 3,
            "height": 600,
            "width": 1200,
        },
    }

    def _render_plotly(fig: go.Figure, div_id: str = "ems-plot") -> None:
        st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key=div_id)

    # Constrói lista de referências para os gráficos
    chart_ref_list = [
        {
            "res":   r["res"],
            "color": r.get("color", "#888888"),
            "dash":  r.get("dash", "dash"),
            "label": r.get("exp_label", "Referência"),
        }
        for r in (ref_list or [])
        if r.get("res") is not None
    ]

    # Para os gráficos Plotly, usar labels sem marcação LaTeX
    var_labels_plot = [_strip_latex(l) for l in var_labels]

    # figura para o PDF usa labels limpos também
    fig_pdf = build_fig_stacked(res, var_keys, var_labels_plot, dark_plot, t_events, d)

    if modo == "Empilhados":
        for i, fig_single in enumerate(build_fig_sidebyside(
                res, var_keys, var_labels_plot, dark_plot, t_events, d,
                ref_list=chart_ref_list, primary_color=primary_color,
                compact=is_mobile)):
            _render_plotly(_apply_zoom(fig_single), div_id=f"ems-emp-{i}")
    elif modo == "Lado a lado":
        figs   = build_fig_sidebyside(
            res, var_keys, var_labels_plot, dark_plot, t_events, d,
            ref_list=chart_ref_list, primary_color=primary_color,
            compact=is_mobile)
        n_cols = min(len(figs), 3)
        rows   = [figs[i:i+n_cols] for i in range(0, len(figs), n_cols)]
        for ri, row in enumerate(rows):
            cols = st.columns(len(row), gap="small")
            for ci, (col, fig) in enumerate(zip(cols, row)):
                with col:
                    _render_plotly(_apply_zoom(fig), div_id=f"ems-side-{ri}-{ci}")
    else:
        fig_overlay = build_fig_overlay(
            res, var_keys, var_labels_plot, dark_plot, t_events, d,
            ref_list=chart_ref_list, primary_color=primary_color,
            compact=is_mobile)
        _render_plotly(_apply_zoom(fig_overlay), div_id="ems-overlay")

    st.write("")

    # ── Botao PDF ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="slabel">Exportar</p>', unsafe_allow_html=True)
    if st.button("Gerar Relatório Técnico (PDF)", key="btn_pdf"):
        with st.spinner("Gerando PDF..."):
            st.session_state["pdf_bytes"] = generate_pdf_report(
                exp_label, mp, res, fig_pdf,
                var_keys, var_labels, t_events,
                exp_type=exp_type,
                ref_list=ref_list,
            )
    if st.session_state.get("pdf_bytes"):
        st.download_button(
            label="Baixar Relatório PDF",
            data=st.session_state["pdf_bytes"],
            file_name="relatorio_ems.pdf",
            mime="application/pdf",
            key="btn_pdf_download",
        )


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO H — ORQUESTRADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    # inicializa estado de sessao
    if "dark_mode"        not in st.session_state: st.session_state["dark_mode"]        = False
    if "experiment_mode"  not in st.session_state: st.session_state["experiment_mode"]  = False
    if "selected_machine" not in st.session_state: st.session_state["selected_machine"] = None
    if "sim_result"       not in st.session_state: st.session_state["sim_result"]       = None
    if "ref_list"         not in st.session_state: st.session_state["ref_list"]         = []
    if "decimals"         not in st.session_state: st.session_state["decimals"]         = 3
    if "pdf_bytes"        not in st.session_state: st.session_state["pdf_bytes"]        = None

    # ── Detecção de largura de viewport (executa apenas uma vez) ─────────
    if "_vw" not in st.session_state:
        st.html(
            """<script>
            var vw = window.innerWidth;
            var p  = new URLSearchParams(window.parent.location.search);
            if (p.get('_vw') !== String(vw)) {
                p.set('_vw', String(vw));
                window.parent.history.replaceState({}, '', '?' + p.toString());
                window.parent.location.reload();
            }
            </script>"""
        )
        st.session_state["_vw"] = int(st.query_params.get("_vw", "1200"))

    _vw       = int(st.session_state.get("_vw", 1200))
    is_mobile = _vw < 600   # < 600 px: retrato estreito

    dark = st.session_state.get("dark_mode", False)
    apply_css(dark)

    # ── cabeçalho ────────────────────────────────────────────────────────
    st.markdown(
        '<div class="app-header">'
        '<div class="app-title">Simulador de Máquinas Elétricas</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── tela de seleção ───────────────────────────────────────────────────
    if not st.session_state["selected_machine"]:
        render_machine_selector(dark)
        return

    # ── navegacao: voltar ─────────────────────────────────────────────────
    col_back, col_title = st.columns([1, 9], vertical_alignment="center")
    with col_back:
        if st.button("Voltar", key="btn_back"):
            st.session_state["selected_machine"] = None
            st.session_state["sim_result"]        = None
            st.rerun()
    with col_title:
        machine_name = next(m["name"] for m in MACHINES
                            if m["key"] == st.session_state["selected_machine"])
        st.markdown(f"### {machine_name}")

    st.divider()

    # ── abas ──────────────────────────────────────────────────────────────
    tab_sim, tab_teoria, tab_clean = st.tabs(["Simulação", "Teoria", "Visualização para Artigo"])

    # ─── ABA SIMULACAO ────────────────────────────────────────────────────
    with tab_sim:
        # toggles no topo
        ct1, ct2, ct3, _ = st.columns([1, 1.6, 0.8, 4])
        with ct1:
            st.toggle("Modo Escuro", value=dark, key="dark_mode")
        with ct2:
            st.toggle("Travar Parâmetros", value=False, key="experiment_mode")
        with ct3:
            st.number_input("Casas decimais dos resultados", min_value=0, max_value=6,value = 3, step=1, key="decimals")

        experiment_mode = st.session_state.get("experiment_mode", False)
        dec = int(st.session_state.get("decimals", 3))

        st.write("")

        # Layout superior: parâmetros (esq) | circuito equivalente (dir)
        col_params, col_circuit = st.columns([1, 1], gap="large")

        with col_params:
            mp, ref_code = render_machine_params(dark, experiment_mode)

        with col_circuit:
            st.markdown('<p class="slabel">Circuito Equivalente Monofásico</p>',
                        unsafe_allow_html=True)
            render_circuit(mp, dark)

            st.write("")

            # Experimento na coluna direita, abaixo do circuito
            exp_config, var_keys, var_labels, tmax, h = render_experiment_config(mp)

        st.write("")

        # Botoes de acao
        bc1, bc2, bc3, bc4, bc5 = st.columns([1.5, 1.2, 1.2, 1.2, 1.5], vertical_alignment="bottom")
        with bc2:
            run_clicked = st.button("Executar Simulação", key="btn_run", width='stretch')
        with bc3:
            _can_save = (st.session_state["sim_result"] is not None
                         and len(st.session_state["ref_list"]) < 5)
            save_ref = st.button("Salvar Referência", key="btn_save_ref", width='stretch',
                                 disabled=not _can_save,
                                 help="Salva o resultado atual como referência (máx. 5)")
        with bc4:
            clear_ref = st.button("Limpar Referências", key="btn_clear_ref", width='stretch',
                                  disabled=not st.session_state["ref_list"],
                                  help="Remove todas as referências salvas")
        _REF_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
        _REF_DASHES = ["dash", "dot", "solid", "dash", "dot"]
        if save_ref and _can_save:
            new_ref = dict(st.session_state["sim_result"])
            _idx_new = len(st.session_state["ref_list"])
            new_ref["color"] = _REF_COLORS[_idx_new % len(_REF_COLORS)]
            new_ref["dash"]  = _REF_DASHES[_idx_new % len(_REF_DASHES)]
            st.session_state["ref_list"].append(new_ref)
            st.rerun()
        if clear_ref:
            st.session_state["ref_list"] = []
            st.rerun()

        # ── execucao ──────────────────────────────────────────────────────
        if run_clicked:
            if not var_keys:
                st.warning("Selecione ao menos uma grandeza para plotar antes de executar.")
            elif exp_config.get("_invalid"):
                st.error("Corrija os parâmetros do experimento antes de executar.")
            else:
                vfn, tfn, t_events = build_fns(exp_config, mp)
                # para shutdown, usa t_end analítico (t_cutoff + t_stop × 1,2)
                _tmax_run = float(exp_config.get("_t_end_shutdown", tmax)) \
                    if exp_config.get("exp_type") == "shutdown" else tmax
                _deseq_a      = exp_config.get("deseq_a", 0.0)
                _deseq_b      = exp_config.get("deseq_b", 0.0)
                _deseq_c      = exp_config.get("deseq_c", 0.0)
                _falta_fase_a = exp_config.get("falta_fase_a", False)
                _falta_fase_b = exp_config.get("falta_fase_b", False)
                _falta_fase_c = exp_config.get("falta_fase_c", False)
                _t_deseq      = exp_config.get("t_deseq", 0.0)
                if (_deseq_a != 0.0 or _deseq_b != 0.0 or _deseq_c != 0.0
                        or _falta_fase_a or _falta_fase_b or _falta_fase_c) and _t_deseq > 0.0:
                    t_events = t_events + [_t_deseq]
                with st.spinner("Executando integração numérica..."):
                    try:
                        res = run_simulation(
                            mp=mp, tmax=_tmax_run, h=h,
                            voltage_fn=vfn, torque_fn=tfn,
                            ref_code=ref_code,
                            deseq_a=_deseq_a, deseq_b=_deseq_b, deseq_c=_deseq_c,
                            falta_fase_a=_falta_fase_a, falta_fase_b=_falta_fase_b,
                            falta_fase_c=_falta_fase_c, t_deseq=_t_deseq,
                            clamp_wr_at_zero=(exp_config.get("exp_type") == "shutdown"),
                            t_cutoff=exp_config.get("t_cutoff") if exp_config.get("exp_type") == "shutdown" else None,
                        )
                        st.session_state["pdf_bytes"] = None
                        st.session_state["sim_result"] = dict(
                            res=res, var_keys=var_keys, var_labels=var_labels,
                            t_events=t_events, dark=dark, mp=mp,
                            exp_label=exp_config.get("exp_label", "Simulacao"),
                            exp_type=exp_config.get("exp_type", "dol"),
                            exp_config=exp_config,
                            tmax=tmax, h=h,
                        )
                        st.session_state["_sim_toast"] = (
                            f"Simulação concluída — "
                            f"n = {res['n'][-1]:.1f} RPM | "
                            f"Te = {res['Te'][-1]:.2f} N·m"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro na simulação: {e}")
                        st.info(
                            "Verifique os parâmetros. Passos de integração muito grandes "
                            "ou parâmetros fisicamente inválidos podem causar divergência numérica."
                        )

        # ── resultados (mesma aba, abaixo do botao) ───────────────────────
        _toast = st.session_state.pop("_sim_toast", None)
        if _toast:
            st.success(_toast)

        sr       = st.session_state.get("sim_result")
        ref_list = st.session_state["ref_list"]

        # ── painel de referências salvas ──────────────────────────────────
        if ref_list:
            st.markdown('<p class="slabel">Referências Salvas</p>', unsafe_allow_html=True)
            _dash_opts = {"Tracejado": "dash", "Pontilhado": "dot", "Sólido": "solid"}
            # cabeçalho das colunas
            _h1, _h2, _h3, _h4 = st.columns([5, 0.55, 1.5, 0.4])
            _h2.caption("Cor")
            _h3.caption("Linha")
            for _i, _ref in enumerate(ref_list):
                _c1, _c2, _c3, _c4 = st.columns([5, 0.55, 1.5, 0.4])
                with _c1:
                    st.markdown(
                        f'<div style="padding:0.38rem 0.75rem;border-radius:6px;'
                        f'background:rgba(128,128,128,0.08);font-size:0.88rem;'
                        f'border-left:3px solid {_ref.get("color","#888")};">'
                        f'<strong>{_ref.get("exp_label","Referência")}</strong></div>',
                        unsafe_allow_html=True,
                    )
                with _c2:
                    _ref["color"] = st.color_picker(
                        "Cor", value=_ref.get("color", "#888888"),
                        key=f"ref_color_{_i}", label_visibility="collapsed",
                    )
                with _c3:
                    _cur = _ref.get("dash", "dash")
                    _idx = list(_dash_opts.values()).index(_cur) if _cur in _dash_opts.values() else 0
                    _sel = st.selectbox(
                        "Linha", list(_dash_opts.keys()), index=_idx,
                        key=f"ref_dash_{_i}", label_visibility="collapsed",
                    )
                    _ref["dash"] = _dash_opts[_sel]
                with _c4:
                    if st.button("✕", key=f"ref_del_{_i}", help="Remover esta referência"):
                        st.session_state["ref_list"].pop(_i)
                        st.rerun()

        if sr is not None:
            # cor da simulação atual vem do tema (preto no claro, claro no escuro);
            # apenas referências salvas têm cor customizável
            _primary_color = None
            render_results(
                res=sr["res"],
                var_keys=var_keys if var_keys else sr["var_keys"],
                var_labels=var_labels if var_labels else sr["var_labels"],
                dark=sr["dark"],
                t_events=sr["t_events"],
                mp=sr["mp"],
                exp_label=sr.get("exp_label", "Simulacao"),
                exp_type=sr.get("exp_type", "dol"),
                decimals=dec,
                ref_list=ref_list,
                primary_color=_primary_color,
                is_mobile=is_mobile,
            )

    # ─── ABA TEORIA ───────────────────────────────────────────────────────
    with tab_teoria:
        render_theory_tab()

    # ─── ABA VISUALIZAÇÃO PARA ARTIGO ─────────────────────────────────────
    with tab_clean:
        render_clean_view()


if __name__ == "__main__":
    main()
