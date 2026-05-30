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
    "sep_motor":    ["campo_fraco_dc", "frenagem_dc", "gerador_dc", "resistencia_dc", "dol_dc", "pulso_dc"],
    "shunt_motor":  ["frenagem_dc", "resistencia_dc", "dol_dc", "pulso_dc"],
    "series_motor": ["frenagem_dc", "resistencia_dc", "dol_dc", "pulso_dc"],
    "sep_gen":      ["gerador_dc"],
    "shunt_gen":    ["gerador_dc"],
}

_MODE_LABELS: dict[str, str] = {
    "campo_fraco_dc": "Enfraquecimento de Campo",
    "frenagem_dc":    "Frenagem Elétrica",
    "gerador_dc":     "Gerador — Carga Resistiva",
    "resistencia_dc": "Partida com Resistência Série",
    "dol_dc":         "Partida Direta (DOL)",
    "pulso_dc":       "Pulso de Carga",
}

_BRAKE_LABELS: dict[str, str] = {
    "plugging":    "Reversão de Polaridade (Plugging)",
    "injecao_cc":  "Injeção de Corrente Contínua",
    "regenerativo":"Frenagem Regenerativa",
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

def render_dc_machine_params(dark: bool, experiment_mode: bool) -> tuple[DCMachineParams, int, float]:
    """Renderiza seletor de parâmetros MCC.

    Retorna (DCMachineParams, ref_code, energy_tariff).
    ref_code: hash inteiro para cache invalidation.
    energy_tariff: tarifa R$/kWh lida de Parâmetros Avançados.
    """
    from core.dc_estimator import estimate_dc_nameplate, estimate_dc_tests

    st.markdown('<p class="slabel">Parâmetros da Máquina</p>', unsafe_allow_html=True)

    # ── Carga automática do preset padrão na primeira abertura ───────────────
    if "wi_dc_Va" not in st.session_state:
        _default_preset = _PRESETS_BY_EXC["sep_motor"]["Motor Sep. 220 V — Sen Ex. 9.2"]
        for k, v in _default_preset.items():
            st.session_state[f"wi_dc_{k}"] = v
        st.session_state["wi_dc_excitation"] = "sep_motor"
        st.session_state["wi_dc_preset"]     = "Motor Sep. 220 V — Sen Ex. 9.2"
        st.rerun()

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
    _PARAM_SOURCE_LABELS_DC = [
        "Inserir parâmetros manualmente",
        "Estimar por dados de placa (Nameplate)",
        "Determinar por Ensaios IEEE 113",
    ]
    _wi("wi_dc_input_mode", _PARAM_SOURCE_LABELS_DC[0])
    input_mode = st.radio(
        "Fonte de dados", _PARAM_SOURCE_LABELS_DC,
        index=_PARAM_SOURCE_LABELS_DC.index(
            st.session_state.get("wi_dc_input_mode", _PARAM_SOURCE_LABELS_DC[0])
        ),
        horizontal=True, key="wi_dc_input_mode",
        disabled=experiment_mode,
    )

    if input_mode == "Estimar por dados de placa (Nameplate)" and not experiment_mode:
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

        with st.expander("Como esses parâmetros foram estimados? (NEMA heurístico)", expanded=False):
            is_sep_placa  = exc in ("sep_motor", "sep_gen")
            is_shunt_placa = exc == "shunt_motor"
            _wm_n = nn_rpm * (2 * 3.14159265 / 60)
            _In   = (Pn_kW * 1000) / (Vn_p * max(eta_p, 0.01))
            _Ea_n = Vn_p - est["Ra"] * _In
            st.info(
                f"**Método:** NEMA heurístico — estimação a partir de dados de placa.  \n"
                f"**Excitação:** {_EXC_LABELS.get(exc, exc)}  \n"
                f"**Premissas:** queda resistiva ≈ 5–10 % de $V_n$; "
                f"τ_a = L_a/R_a ≈ 0,8 s; τ_f = L_f/R_f ≈ 0,1 s."
            )
            _mp1, _mp2, _mp3, _mp4 = st.columns(4)
            _mp1.metric("Ra (Ω)",       f"{est['Ra']:.4f}")
            _mp2.metric("La (H)",       f"{est['La']:.4f}")
            _mp3.metric("kb (V·s/rad)", f"{est['kb']:.5f}")
            _mp4.metric("Va (V)",       f"{est['Va']:.2f}")
            if not (exc == "series_motor"):
                _mc1, _mc2, _mc3 = st.columns(3)
                _Vf_est = est.get("Vf", est["Va"])
                if is_shunt_placa:
                    _mc1.metric("Vf = Va (V)", f"{_Vf_est:.2f}")
                else:
                    _mc1.metric("Vf (V)",  f"{_Vf_est:.2f}")
                _mc2.metric("Rf (Ω)",  f"{est.get('Rf', 0):.4f}")
                _mc3.metric("Lf (H)",  f"{est.get('Lf', 0):.5f}")
            _mm1, _mm2 = st.columns(2)
            _mm1.metric("J (kg·m²)", f"{est.get('J', 0):.4f}")
            _mm2.metric("B (N·m·s)", f"{est.get('B', 0):.2e}")
            # Avisos de sanidade
            if est["Ra"] / max(est["Va"], 1e-6) < 0.005:
                st.warning("$R_a/V_a$ muito baixo — verifique resistência de armadura.")
            if est["kb"] <= 0:
                st.error("$k_b$ ≤ 0 — impossível. Revise Vn, nn ou η.")

    elif input_mode == "Determinar por Ensaios IEEE 113" and not experiment_mode:
        # Guia de procedimento (fechado por padrão)
        with st.expander("Como realizar os ensaios IEEE 113 (procedimento, fórmulas e dicas)", expanded=False):
            st.markdown("""
**Visão geral.** O método IEEE Std 113-1985 determina os parâmetros do circuito equivalente de
um motor CC por meio de **dois ensaios físicos complementares**:

| Ensaio | Seção IEEE 113 | Parâmetros extraídos |
|--------|--------------|---------------------|
| **[1a] CC Armadura** | Sec. 4.2.2.2 | $R_a$ |
| **[1b] CC Campo** | Sec. 4.2.2.1 | $R_f$ (excitação separada) |
| **[2] CA Armadura** | Sec. 7.5.1 | $L_a$ (rotor travado, campo curto-circuitado) |
| **[3] Degrau de Campo** | Sec. 7.5.3 | $L_f$ (constante de tempo $\tau_f$) |
| **[4] Vazio** | Sec. 5.6 | $k_b$, $E_{a,nl}$, $R_f$ (shunt via $V_a/I_f$) |

Os ensaios [2] e [3] são opcionais — se não realizados, $L_a$ e $L_f$ são estimados
por heurística ($L_a = R_a \\cdot 0{,}8$; $L_f = R_f \\cdot 0{,}1$).
            """)

            st.markdown("### [1a] Ensaio CC — Resistência da Armadura")
            st.markdown("""
**Objetivo.** Medir $R_a$ com o motor parado e desconectado da alimentação CC de operação.

**Equipamento.** Fonte CC ajustável, voltímetro CC, amperímetro CC.

**Procedimento (IEEE 113 Sec. 3):**
1. Garanta o motor **frio** (à temperatura ambiente) — a resistência varia ~0,4%/°C.
2. Conecte a fonte CC entre os **dois terminais de armadura** (A1–A2).
3. Eleve a tensão até a corrente atingir aproximadamente **25% de $I_n$**.
4. Aguarde **1 minuto** para estabilização térmica.
5. Anote $V_{dc,a}$ e $I_{dc,a}$ simultaneamente.

**Fórmula aplicada:**

$$R_a = \\frac{V_{dc,a}}{I_{dc,a}}$$

**Dicas práticas:**
- Não exceda 25% de $I_n$ — correntes maiores aquecem a armadura e falseiam $R_a$.
- Repita o ensaio em **3 posições distintas do comutador** e use a média — evita erros de contato de escova.
- Valor típico: 0,01–5 Ω, conforme a potência e tensão nominal do motor.
            """)

            st.markdown("### [1b] Ensaio CC — Resistência do Campo (excitação separada)")
            st.markdown("""
**Objetivo.** Medir $R_f$ com o circuito de campo isolado da armadura.

**Equipamento.** Fonte CC ajustável, voltímetro CC, amperímetro CC.

**Procedimento (IEEE 113 Sec. 3):**
1. Garanta o motor **frio** — desconecte a alimentação de armadura.
2. Conecte a fonte CC entre os **terminais de campo** (F1–F2).
3. Eleve a tensão até a corrente atingir aproximadamente **25% de $I_{f,n}$**.
4. Aguarde **1 minuto** para estabilização térmica.
5. Anote $V_{dc,f}$ e $I_{dc,f}$ simultaneamente.

**Fórmula aplicada:**

$$R_f = \\frac{V_{dc,f}}{I_{dc,f}}$$

**Nota:** Para excitação **shunt**, $R_f$ é calculado a partir do ensaio a vazio: $R_f = V_{a,nl}/I_{fd,nl}$.

**Dicas práticas:**
- Valor típico: 10–500 Ω para excitação separada (alta resistência, baixa corrente).
- Para motores shunt, o ensaio direto também é válido e mais preciso.
            """)

            st.markdown("### [2] Ensaio CA — Indutância de Armadura (Sec. 7.5.1)")
            st.markdown("""
**Objetivo.** Medir $L_a$ por impedância CA com o rotor travado mecanicamente.

**Equipamento.** Fonte CA monofásica ajustável (50 ou 60 Hz), voltímetro CA, amperímetro CA,
osciloscópio ou wattímetro (para medição do ângulo de fase).

**Procedimento (IEEE 113 Sec. 7.5.1):**
1. **Trave o rotor** mecanicamente — não pode girar durante o ensaio.
2. **Curto-circuite o enrolamento de campo** (shunt) para evitar sobretensões induzidas.
3. Aplique tensão CA monofásica entre os terminais de armadura (A1–A2).
4. Limite a corrente CA a **≤ 20% de $I_n$** para evitar superaquecimento das escovas.
5. Meça $V_{ac}$, $I_{ac}$ e o ângulo de fase $\\theta$ entre tensão e corrente.

**Fórmula aplicada (IEEE 113 Sec. 7.5.1):**

$$L_a = \\frac{V_{ac} \\cdot \\sin\\theta}{I_{ac} \\cdot 2\\pi f}$$

**Dicas práticas:**
- Use osciloscópio para observar a forma de onda e medir $\\theta$ com precisão.
- Alternativamente, use wattímetro: $\\cos\\theta = P/(V_{ac}\\cdot I_{ac})$, logo $\\sin\\theta = \\sqrt{1 - \\cos^2\\theta}$.
- Execute o ensaio rapidamente — corrente CA aquece escovas e comutador.
- Se o ângulo $\\theta = 0$, a indutância é desprezível — verifique o circuito.
            """)

            st.markdown("### [3] Ensaio de Degrau — Indutância de Campo (Sec. 7.5.3)")
            st.markdown("""
**Objetivo.** Medir $L_f$ a partir da constante de tempo de campo $\\tau_f$ (excitação separada).

**Equipamento.** Fonte CC ajustável, osciloscópio ou registrador, interruptor rápido.

**Procedimento (IEEE 113 Sec. 7.5.3):**
1. Acione o motor à velocidade nominal em pleno campo (armadura aberta ou em vazio).
2. Reduza a tensão de campo para ~50% do valor nominal.
3. **Abra o circuito de campo** e ajuste a fonte para o valor nominal $V_f$.
4. **Feche abruptamente** o circuito — aplique degrau de tensão ao campo.
5. Registre $i_f(t)$ com osciloscópio e determine $\\tau_f$ = tempo para atingir **63,2%** de $I_{f,final}$.

**Fórmula aplicada (IEEE 113 Sec. 7.5.3):**

$$L_f = R_f \\cdot \\tau_f$$

**Dicas práticas:**
- Ciclar o campo duas vezes entre 50% e 100% antes do ensaio para estabilizar a saturação.
- A norma define também $L_{f,ef}$ usando a tensão de armadura como indicador de fluxo — mais precisa em máquinas saturadas.
- Valor típico: $\\tau_f$ = 0,1–2 s para motores industriais de excitação separada.
            """)

            st.markdown("### [4] Ensaio a Vazio — Constante de Máquina")
            st.markdown("""
**Objetivo.** Determinar $k_b$ e $E_{a,nl}$ operando o motor **sem carga mecânica no eixo**
em tensão e velocidade nominais.

**Equipamento.** Fonte CC de armadura ajustável, fonte CC de campo (excitação separada),
voltímetro CC, amperímetro CC, tacômetro.

**Procedimento (IEEE 113 Sec. 4):**
1. **Desacople** qualquer carga mecânica do eixo (motor gira livre).
2. Aplique a tensão de armadura nominal $V_{a,nom}$ e a corrente de campo nominal $I_{fd,nom}$.
3. Deixe o motor estabilizar em velocidade (regime permanente).
4. Anote $V_{a,nl}$, $I_{a,nl}$, $I_{fd,nl}$ e $n_{nl}$ (RPM).

**Fórmulas aplicadas:**

$$E_{a,nl} = V_{a,nl} - R_a \\cdot I_{a,nl}$$

$$k_b = \\frac{E_{a,nl}}{I_{fd,nl} \\cdot \\omega_{nl}}, \\quad \\omega_{nl} = \\frac{2\\pi \\cdot n_{nl}}{60}$$

**Sobre a indutância $L_a$:**
- $L_a$ não é determinada diretamente por ensaio a vazio.
- O estimador adota a heurística IEEE 113: $\\tau_a = L_a/R_a \\approx 10\\text{–}50\\,\\text{ms}$ para máquinas industriais.
- Para medição direta, aplique degrau de tensão à armadura (motor travado) e meça a constante de tempo da corrente.

**Dicas práticas:**
- $I_{a,nl}$ típica: 5–15% de $I_n$ (perdas em vazio dominadas por atrito e ventilação).
- Motores com **saturação magnética** têm $k_b$ variável com $I_{fd}$ — o ensaio fornece o valor na região nominal.
- Para excitação **shunt**, $I_{fd} = V_a / R_f$ — verificar consistência com $R_f$ medido.
            """)

            st.markdown("---")
            st.markdown("""
**Referências bibliográficas:**
- IEEE Std 113-1985 — *Guide on Test Procedures for DC Machines*, Sec. 4.2 (resistência), Sec. 5.6 (vazio), Sec. 7.5 (indutância).
- Sen, P. C. — *Principles of Electric Machines and Power Electronics*, 3ª ed., §7.3 ("Testing of DC Machines").
- Chapman, S. J. — *Máquinas Elétricas*, 5ª ed., §8.5 ("Determinação dos Parâmetros do Motor CC").
            """)

        _pgroup("Ensaio de Resistência CC — Armadura (IEEE 113 Sec. 3)")
        e1, e2 = st.columns(2)
        _wi("wi_dc_V_dc_test", 1.0)
        _wi("wi_dc_I_dc_test", 0.1)
        V_dc_t = e1.number_input("$V_{dc,a}$ (V)", min_value=0.001, key="wi_dc_V_dc_test", format="%.3f")
        I_dc_t = e2.number_input("$I_{dc,a}$ (A)", min_value=0.001, key="wi_dc_I_dc_test", format="%.3f")
        _Ra_preview = V_dc_t / max(I_dc_t, 1e-9)
        st.caption(f"→ $R_a$ ≈ **{_Ra_preview:.4f} Ω**")

        # Ensaio CC de campo — só para excitação separada (IEEE 113 Sec. 3, terminais F1–F2)
        _is_sep_test = exc in ("sep_motor", "sep_gen")
        V_dc_f_t = 0.0
        I_dc_f_t = 0.0
        if _is_sep_test:
            _pgroup("Ensaio de Resistência CC — Campo (IEEE 113 Sec. 3)")
            f1, f2 = st.columns(2)
            _wi("wi_dc_V_dc_f_test", 1.0)
            _wi("wi_dc_I_dc_f_test", 0.1)
            V_dc_f_t = f1.number_input("$V_{dc,f}$ (V)", min_value=0.001, key="wi_dc_V_dc_f_test", format="%.3f")
            I_dc_f_t = f2.number_input("$I_{dc,f}$ (A)", min_value=0.001, key="wi_dc_I_dc_f_test", format="%.3f")
            _Rf_preview = V_dc_f_t / max(I_dc_f_t, 1e-9)
            st.caption(f"→ $R_f$ ≈ **{_Rf_preview:.4f} Ω**")

        # Ensaio CA de indutância de armadura (IEEE 113 Sec. 7.5.1)
        _pgroup("Ensaio CA — Indutância de Armadura (IEEE 113 Sec. 7.5.1)")
        h1, h2, h3, h4 = st.columns(4)
        _wi("wi_dc_V_ac_test",    0.0)
        _wi("wi_dc_I_ac_test",    0.0)
        _wi("wi_dc_theta_test",   0.0)
        _wi("wi_dc_f_ac_test",   60.0)
        V_ac_t     = h1.number_input("$V_{ac}$ (V)",   min_value=0.0, key="wi_dc_V_ac_test",  format="%.3f",
                                     help="Tensão CA aplicada à armadura (rotor travado, campo curto-circuitado). 0 = usar heurística.")
        I_ac_t     = h2.number_input("$I_{ac}$ (A)",   min_value=0.0, key="wi_dc_I_ac_test",  format="%.3f",
                                     help="Corrente CA medida (≤ 20% de I_n conforme IEEE 113).")
        theta_t    = h3.number_input("$\\theta$ (°)",  min_value=0.0, max_value=90.0, key="wi_dc_theta_test", format="%.1f",
                                     help="Ângulo de fase entre V e I medido por osciloscópio ou wattímetro.")
        f_ac_t     = h4.number_input("$f_{ac}$ (Hz)",  min_value=1.0, key="wi_dc_f_ac_test",  format="%.1f",
                                     help="Frequência da fonte CA (50 ou 60 Hz conforme IEEE 113).")
        if V_ac_t > 1e-9 and I_ac_t > 1e-9 and theta_t > 0.1:
            import math as _math
            _La_prev = V_ac_t * _math.sin(_math.radians(theta_t)) / (I_ac_t * 2 * _math.pi * max(f_ac_t, 1.0))
            st.caption(f"→ $L_a$ ≈ **{_La_prev*1000:.3f} mH**")
        else:
            st.caption("→ $L_a$: heurística ($R_a \\cdot 0{,}8$) — informe $V_{{ac}}$, $I_{{ac}}$, $\\theta$ para cálculo IEEE 113.")

        # Ensaio de degrau de campo — indutância de campo (IEEE 113 Sec. 7.5.3)
        if _is_sep_test:
            _pgroup("Ensaio de Degrau — Indutância de Campo (IEEE 113 Sec. 7.5.3)")
            _wi("wi_dc_tau_f_ms_test", 0.0)
            tau_f_t = st.number_input(
                "$\\tau_f$ medido (ms)", min_value=0.0, key="wi_dc_tau_f_ms_test", format="%.1f",
                help="Tempo para 63,2% da corrente de campo final após degrau de tensão. 0 = usar heurística (Rf·0,1).",
            )
            if tau_f_t > 1e-3:
                _Rf_prev = V_dc_f_t / max(I_dc_f_t, 1e-9)
                _Lf_prev = _Rf_prev * (tau_f_t / 1000.0)
                st.caption(f"→ $L_f$ ≈ **{_Lf_prev:.5f} H**  ($R_f \\cdot \\tau_f$ = {_Rf_prev:.4f}·{tau_f_t/1000:.4f})")
            else:
                st.caption("→ $L_f$: heurística ($R_f \\cdot 0{,}1$) — informe $\\tau_f$ para cálculo IEEE 113.")
        else:
            tau_f_t = 0.0

        _pgroup("Ensaio a Vazio (IEEE 113 Sec. 5.6)")
        g1, g2, g3, g4 = st.columns(4)
        _wi("wi_dc_V_nl_test",  24.0)
        _wi("wi_dc_I_nl_test",  0.05)
        _wi("wi_dc_If_nl_test", 8.4)
        _wi("wi_dc_n_nl_test",  6500.0)
        V_nl_t  = g1.number_input("$V_{a,nl}$ (V)",    min_value=0.01,  key="wi_dc_V_nl_test",  format="%.3f")
        I_nl_t  = g2.number_input("$I_{a,nl}$ (A)",    min_value=0.001, key="wi_dc_I_nl_test",  format="%.3f")
        If_nl_t = g3.number_input("$I_{fd,nl}$ (A)",   min_value=0.001, key="wi_dc_If_nl_test", format="%.3f")
        n_nl_t  = g4.number_input("$n_{nl}$ (RPM)",    min_value=1.0,   key="wi_dc_n_nl_test",  format="%.1f")
        est = estimate_dc_tests(
            V_dc_t, I_dc_t, V_nl_t, I_nl_t, If_nl_t, n_nl_t, exc,
            V_dc_f=V_dc_f_t, I_dc_f=I_dc_f_t,
            V_ac=V_ac_t, I_ac=I_ac_t, theta_deg=theta_t, f_ac=f_ac_t,
            tau_f_ms=tau_f_t,
        )
        for fld, wk in [("Ra","wi_dc_Ra"),("La","wi_dc_La"),("kb","wi_dc_kb"),
                        ("Lf","wi_dc_Lf"),("Rf","wi_dc_Rf")]:
            if fld in est:
                st.session_state[wk] = est[fld]

        # Expander de Detalhes do Cálculo
        with st.expander("Detalhes do Cálculo (IEEE Std 113-1985)", expanded=True):
            # Cabeçalho — método e configuração
            _exc_label_map = {
                "sep_motor": "Excitação separada (motor)",
                "sep_gen":   "Excitação separada (gerador)",
                "shunt":     "Shunt",
                "series_motor": "Série",
            }
            st.markdown(
                f"**Método:** IEEE Std 113-1985 — dois ensaios físicos. "
                f"**Configuração:** {_exc_label_map.get(exc, exc)}."
            )

            # ── Ensaios físicos: duas ou três colunas lado a lado ────
            st.markdown("##### Ensaios físicos")
            _has_rf = "Rf" in est
            _t1, _t2, *_t3 = st.columns(3 if _has_rf else 2)
            with _t1:
                st.markdown("**Ensaio CC — Armadura**")
                st.markdown(f"$R_a$ = **{est['Ra']:.4f} Ω**")
                st.caption(f"via $V_{{dc,a}}/I_{{dc,a}}$ = {V_dc_t / max(I_dc_t, 1e-9):.4f} Ω")
            if _has_rf and _t3:
                with _t3[0]:
                    st.markdown("**Ensaio CC — Campo**")
                    st.markdown(f"$R_f$ = **{est['Rf']:.4f} Ω**")
                    st.caption(f"via $V_{{dc,f}}/I_{{dc,f}}$ = {V_dc_f_t / max(I_dc_f_t, 1e-9):.4f} Ω")
            with _t2:
                st.markdown("**Ensaio a Vazio**")
                _wm_nl = n_nl_t * (2 * 3.14159265 / 60)
                st.markdown(
                    f"$E_{{a,nl}}$ = **{est['Ea_nl']:.3f} V**  \n"
                    f"$\\omega_{{nl}}$ = **{_wm_nl:.2f} rad/s**  \n"
                    f"$k_b$ = **{est['kb']:.5f} V·s/rad**"
                )
                st.caption(
                    f"via $E_{{a,nl}} = V_{{a,nl}} - R_a \\cdot I_{{a,nl}}$ "
                    f"= {V_nl_t:.3f} − {est['Ra']:.4f}·{I_nl_t:.3f}"
                )

            st.divider()

            # ── Indicadores intermediários ───────────────────────────
            st.markdown("##### Indicadores intermediários")
            _tau_a = est["La"] / max(est["Ra"], 1e-9)
            _im_c1, _im_c2, _im_c3, _im_c4 = st.columns(4)
            _im_c1.metric("Ea_nl (V)",        f"{est['Ea_nl']:.3f}")
            _im_c2.metric("ω_nl (rad/s)",     f"{_wm_nl:.2f}")
            _im_c3.metric("τ_a = La/Ra (ms)", f"{_tau_a * 1000:.2f}")
            if exc in ("sep_motor", "sep_gen"):
                _Lf_est = est.get("Lf", 0.0)
                _Rf_est = float(st.session_state.get("wi_dc_Rf", 1.0))
                _tau_f = _Lf_est / max(_Rf_est, 1e-9)
                _im_c4.metric("τ_f = Lf/Rf (ms)", f"{_tau_f * 1000:.2f}")

            # ── Parâmetros estimados ──────────────────────────────────
            st.markdown("##### Parâmetros estimados (circuito equivalente)")
            _p1 = st.columns(3)
            _p1[0].metric("Ra (Ω)",       f"{est['Ra']:.4f}")
            _p1[1].metric("La (H)",       f"{est['La']:.5f}")
            _p1[2].metric("kb (V·s/rad)", f"{est['kb']:.5f}")
            if exc in ("sep_motor", "sep_gen"):
                _p2 = st.columns(3)
                _p2[0].metric("Lf (H)",   f"{est.get('Lf', 0):.5f}")
                _p2[1].metric("Rf (Ω)",   f"{est.get('Rf', 0):.4f}" if "Rf" in est else "—")
                _p2[2].metric("If_nl (A)", f"{If_nl_t:.4f}")
            elif exc == "shunt_motor" and "Rf" in est:
                _p2 = st.columns(3)
                _p2[0].metric("Lf (H)",  f"{est.get('Lf', 0):.5f}")
                _p2[1].metric("Rf (Ω)",  f"{est['Rf']:.4f}")
                _p2[2].metric("If_nl (A)", f"{If_nl_t:.4f}")

            # Avisos de sanidade
            if est["kb"] <= 0:
                st.error("$k_b$ ≤ 0 — impossível. Verifique $V_{a,nl}$, $R_a$ e $I_{a,nl}$.")
            if est["Ra"] / max(V_nl_t, 1e-6) > 0.3:
                st.warning("$R_a/V_{a,nl}$ > 30 % — Ra parece elevado para esta tensão de operação.")

        if st.button(
            "✔ Usar estes parâmetros na simulação",
            key="btn_dc_use_tests",
            help="Copia os parâmetros estimados para o modo Manual, permitindo ajustes antes de simular.",
        ):
            for fld, wk in [("Ra","wi_dc_Ra"),("La","wi_dc_La"),("kb","wi_dc_kb"),("Lf","wi_dc_Lf")]:
                if fld in est:
                    st.session_state[wk] = est[fld]
            st.session_state["wi_dc_input_mode"] = "Inserir parâmetros manualmente"
            st.rerun()

    # ── Preset loader — só no modo manual (estimadores têm própria fonte de dados) ──
    if input_mode == "Inserir parâmetros manualmente":
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

    _wi("wi_dc_energy_tariff", 0.75)

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

        _is_manual    = (input_mode == "Inserir parâmetros manualmente")
        _is_nameplate = (input_mode == "Estimar por dados de placa (Nameplate)")
        _is_ieee      = (input_mode == "Determinar por Ensaios IEEE 113")

        if _is_manual:
            # ── Grupo armadura completo ──────────────────────────────
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

            # ── Grupo campo ──────────────────────────────────────────
            if not is_series:
                _pgroup("Dados de Campo")
                if is_sep:
                    vf = st.number_input(
                        "Tensão de campo — $V_f$ (V)",
                        min_value=0.0, key="wi_dc_Vf", format="%.3f",
                        help="Tensão da fonte independente de campo (excitação separada).",
                    )
                else:
                    vf = va
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

        else:
            # Ra, La, kb, Lf estimados em ambos os modos — ler silenciosamente
            ra = float(st.session_state.get("wi_dc_Ra", 0.013))
            la = float(st.session_state.get("wi_dc_La", 0.01))
            kb = float(st.session_state.get("wi_dc_kb", 0.004))
            lf = float(st.session_state.get("wi_dc_Lf", 0.167))

            if _is_nameplate:
                # Nameplate estima tudo elétrico — ler Va, Vf, Rf silenciosamente
                va = float(st.session_state.get("wi_dc_Va", 24.0))
                rf = float(st.session_state.get("wi_dc_Rf", 1.43))
                vf = float(st.session_state.get("wi_dc_Vf", va if not is_sep else 12.0))
            else:
                # IEEE 113: Va e Vf não estimados — editáveis; Rf estimado pelo ensaio CC campo
                _pgroup("Dados de Armadura")
                va = st.number_input(
                    "Tensão de armadura — $V_a$ (V)",
                    min_value=0.0, key="wi_dc_Va", format="%.3f",
                    help="Tensão CC aplicada ao enrolamento de armadura.",
                )
                st.markdown('</div>', unsafe_allow_html=True)

                if not is_series:
                    _pgroup("Dados de Campo")
                    if is_sep:
                        vf = st.number_input(
                            "Tensão de campo — $V_f$ (V)",
                            min_value=0.0, key="wi_dc_Vf", format="%.3f",
                            help="Tensão da fonte independente de campo (excitação separada).",
                        )
                        # Rf estimado pelo ensaio CC campo — ler silenciosamente
                        rf = float(st.session_state.get("wi_dc_Rf", 1.43))
                    else:
                        vf = va
                        st.caption("Shunt: $V_f = V_a$ (fixo — campo em paralelo com a armadura)")
                        # Rf estimado via V_nl/If_nl — ler silenciosamente
                        rf = float(st.session_state.get("wi_dc_Rf", 1.43))
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    _pgroup("Campo (série com armadura)")
                    rf = st.number_input(
                        "Resistência do campo série — $R_s$ (Ω)",
                        min_value=1e-6, key="wi_dc_Rf", format="%.4f",
                        help="Resistência do enrolamento de campo série (em série com a armadura).",
                    )
                    vf = 0.0
                    st.markdown('</div>', unsafe_allow_html=True)

        # Grupo carga elétrica (geradores) — não estimado, sempre visível
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

        # Grupo mecânico — Nameplate estima J e B; IEEE não estima nenhum
        if _is_nameplate:
            J     = float(st.session_state.get("wi_dc_J",     0.21))
            B     = float(st.session_state.get("wi_dc_B",     1.074e-6))
            Tload = float(st.session_state.get("wi_dc_Tload", 2.493))
        else:
            # Manual e Ensaios: J, B, Tload editáveis
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

        # Métricas derivadas
        _tau_a_ms = (la / max(ra, 1e-9)) * 1000
        _n0_rpm   = (va / max(kb, 1e-9)) * (60 / (2 * 3.14159265)) - (B * va / max(kb**2, 1e-9)) * (60 / (2 * 3.14159265))
        _d1, _d2, _d3 = st.columns(3)
        _d1.metric("τ_a (ms)",      f"{_tau_a_ms:.2f}",   help="Constante de tempo elétrica da armadura = La/Ra")
        if not is_series and lf > 0 and rf > 0:
            _tau_f_ms = (lf / max(rf, 1e-9)) * 1000
            _d2.metric("τ_f (ms)",  f"{_tau_f_ms:.2f}",   help="Constante de tempo do circuito de campo = Lf/Rf")
        else:
            _d2.metric("τ_f (ms)",  "—",                  help="Não aplicável para motor série")
        _d3.metric("n₀ est. (RPM)", f"{max(_n0_rpm, 0):.0f}", help="Velocidade estimada em vazio (regime)")

        # Parâmetros Avançados
        with st.expander("Parâmetros Avançados", expanded=False):
            _pgroup("Análise Econômica")
            _wi("wi_dc_energy_tariff", 0.75)
            st.number_input(
                "Tarifa de energia — R$/kWh",
                min_value=0.0001, max_value=5.0,
                step=0.01, format="%.4f",
                key="wi_dc_energy_tariff",
                help="Tarifa usada para calcular custo operacional anual na aba Gestão de Ativos.",
            )

    mp = DCMachineParams(
        Va=va, Ra=ra, La=la,
        Vf=vf, Rf=rf, Lf=lf,
        Rl=rl, Ll=ll,
        J=J, B=B, kb=kb,
        excitation=exc,
        Tload=Tload,
    )

    ref_code = hash((va, ra, la, vf, rf, lf, rl, ll, J, B, kb, exc, Tload))
    energy_tariff = float(st.session_state.get("wi_dc_energy_tariff", 0.75))
    return mp, ref_code, energy_tariff


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

    elif mode == "frenagem_dc":
        brake_labels = list(_BRAKE_LABELS.values())
        brake_keys   = list(_BRAKE_LABELS.keys())
        _wi("wi_dc_brake_method", brake_labels[0])
        brake_sel = st.selectbox(
            "Método de Frenagem", brake_labels,
            index=brake_labels.index(st.session_state.get("wi_dc_brake_method", brake_labels[0])),
            key="wi_dc_brake_method",
        )
        brake = brake_keys[brake_labels.index(brake_sel)]
        exp_config["brake_method"] = brake
        exp_config["Tl_final"]     = _Tl_ref

        _BRAKE_DESC_DC = {
            "plugging":    "Inverte a polaridade da tensão de armadura enquanto o motor ainda gira. "
                           "Produz torque contrário ao movimento — frenagem muito rápida, mas com alta "
                           "corrente de armadura e possível inversão de sentido se não houver chave de parada.",
            "injecao_cc":  "Corta a alimentação de operação e injeta tensão CC reduzida na armadura. "
                           "O fluxo de campo mantido produz torque de frenagem sem inverter o sentido. "
                           "Frenagem suave e controlada — corrente limitada pela resistência de armadura.",
            "regenerativo":"Reduz a tensão de armadura abaixo da fcem do motor. A corrente de armadura "
                           "inverte — o motor opera como gerador, devolvendo energia à fonte. Frenagem "
                           "suave; eficaz apenas em cargas com alta inércia ou velocidade elevada.",
        }
        st.info(_BRAKE_DESC_DC[brake])

        if brake == "plugging":
            _wi("wi_dc_t_freia", 3.0)
            exp_config["t_freia"] = st.number_input(
                "Instante de reversão — $t_{freia}$ (s)", min_value=0.1,
                key="wi_dc_t_freia", format="%.2f",
            )
            tmax_def = exp_config["t_freia"] * 2.5
            h_def    = 1e-3
            _ibox(
                f"<strong>t = 0 s</strong> — motor parte em sentido positivo com carga de {_Tl_ref:.3f} N·m.<br>"
                f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — polaridade de armadura invertida; "
                f"torque de frenagem opõe-se ao movimento; rotor desacelera e inverte o sentido."
            )

        elif brake == "injecao_cc":
            c1, c2 = st.columns(2)
            _wi("wi_dc_t_freia",   3.0)
            _wi("wi_dc_Vdc_inj",   mp.Va * 0.1)
            exp_config["t_freia"]  = c1.number_input(
                "Instante de corte — $t_{freia}$ (s)", min_value=0.1,
                key="wi_dc_t_freia", format="%.2f",
            )
            exp_config["Vdc_inj"]  = c2.number_input(
                "Tensão CC injetada — $V_{inj}$ (V)", min_value=0.0,
                key="wi_dc_Vdc_inj", format="%.2f",
                help="Tensão CC aplicada à armadura após corte da alimentação CA. Tipicamente 5–15% de Va.",
            )
            tmax_def = exp_config["t_freia"] * 2.5
            h_def    = 1e-3
            _ibox(
                f"<strong>t = 0 s</strong> — motor opera em regime com carga de {_Tl_ref:.3f} N·m.<br>"
                f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — alimentação cortada; "
                f"tensão CC de <strong>{exp_config['Vdc_inj']:.2f} V</strong> injetada na armadura; "
                f"corrente produz torque oposto ao movimento — frenagem controlada sem inversão."
            )

        elif brake == "regenerativo":
            c1, c2 = st.columns(2)
            _wi("wi_dc_t_freia",  3.0)
            _wi("wi_dc_Va_regen", mp.Va * 0.5)
            exp_config["t_freia"]   = c1.number_input(
                "Instante de frenagem — $t_{freia}$ (s)", min_value=0.1,
                key="wi_dc_t_freia", format="%.2f",
            )
            exp_config["Va_regen"]  = c2.number_input(
                "Tensão de armadura reduzida — $V_{a,regen}$ (V)", min_value=0.0,
                key="wi_dc_Va_regen", format="%.2f",
                help="Tensão abaixo da fcem — motor opera como gerador devolvendo energia.",
            )
            tmax_def = exp_config["t_freia"] * 2.5
            h_def    = 1e-3
            _ibox(
                f"<strong>t = 0 s</strong> — motor opera em regime com carga de {_Tl_ref:.3f} N·m.<br>"
                f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — tensão de armadura reduzida para "
                f"<strong>{exp_config['Va_regen']:.2f} V</strong> (abaixo da fcem); "
                f"corrente inverte — motor opera como gerador, devolvendo energia à fonte."
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
            elif mode == "frenagem_dc":
                _critical_dc = [("frenagem", "t_{freia}", exp_config.get("t_freia", 0))]
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
