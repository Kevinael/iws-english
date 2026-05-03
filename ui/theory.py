# -*- coding: utf-8 -*-
"""Aba Teoria — conteúdo educacional do simulador de máquinas de indução."""

from __future__ import annotations
import base64
import io
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams.update({"mathtext.fontset": "dejavusans", "text.usetex": False})
import matplotlib.pyplot as plt
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────────────────────────────────────

def _b64(fname: str) -> str:
    for base in (Path(__file__).parent.parent, Path(__file__).parent):
        p = base / fname
        if p.exists():
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""


def _show_img(fname: str, width: str = "100%") -> None:
    b64 = _b64(fname)
    if not b64:
        st.caption(f"[{fname} não encontrada]")
        return
    st.markdown(
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:{width};max-width:100%;display:block;'
        f'border-radius:6px;margin:.4rem auto;">',
        unsafe_allow_html=True,
    )


# ── figura matplotlib → bytes ─────────────────────────────────────────────────

def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── parâmetros de referência para curvas T×s ──────────────────────────────────

_V1_REF, _f_REF, _p_REF = 220, 60, 4
_R1_REF, _X1_REF        = 0.50, 1.00
_R2_REF, _X2_REF        = 0.40, 1.00
_Xm_REF                 = 50.0
_ns_REF                 = 120 * _f_REF / _p_REF   # 1800 RPM


def _torque_ref(s: float) -> float:
    """Torque (N·m) para o motor de referência da aba teoria."""
    if abs(s) < 1e-4:
        s = 1e-4
    Z2  = _R2_REF / s + 1j * _X2_REF
    Zeq = (1j * _Xm_REF * Z2) / (1j * _Xm_REF + Z2)
    Zt  = _R1_REF + 1j * _X1_REF + Zeq
    I1  = _V1_REF / Zt
    I2  = (I1 * Zeq) / Z2
    return 3 * abs(I2) ** 2 * (_R2_REF / s) / (2 * np.pi * _ns_REF / 60)


# ── helpers de renderização ───────────────────────────────────────────────────

def _h4(title: str) -> None:
    """Subtítulo de seção, sem cor azul."""
    st.markdown(
        f'<h4 style="font-size:1.05rem;font-weight:700;'
        f'margin:.6rem 0 .4rem;color:#111;">{title}</h4>',
        unsafe_allow_html=True,
    )


def _eq(latex: str) -> None:
    """Equação centralizada via KaTeX nativo do Streamlit."""
    st.markdown(f"$$\n{latex}\n$$")


def _p(text: str) -> None:
    st.markdown(text)


def _div_warn(text: str) -> None:
    st.markdown(
        f'<div style="background:#f3f3f3;border-left:4px solid #555;'
        f'padding:.5rem .8rem;border-radius:4px;margin:.5rem 0;'
        f'font-size:.88rem;color:#222;">{text}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ABA 1 — MODELAGEM E CIRCUITOS EQUIVALENTES
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_circuitos() -> None:
    st.markdown(
        "O **circuito equivalente monofásico** transforma o problema eletromagnético "
        "trifásico em um circuito elétrico de regime permanente. A partir dele derivam-se "
        "as equações de torque, potência e, por extensão, o modelo $0dq$ de Krause "
        "utilizado na integração dinâmica do simulador."
    )

    st.divider()

    # 1a. Circuito Completo
    _h4("Circuito Completo — com $R_{fe}$")
    col_img, col_txt = st.columns([1, 1])
    with col_img:
        _show_img("imgs/ind_completo.png")
    with col_txt:
        st.markdown(
            "O ramo *shunt* contém $R_{fe} \\parallel jX_m$, onde $R_{fe}$ modela "
            "as perdas no ferro por **histerese** e **correntes de Foucault**. "
            "A corrente de excitação se decompõe em:"
        )
        _eq(r"I_\phi = I_c + jI_m = \frac{V_1}{R_{fe}} + \frac{V_1}{jX_m}")
        st.markdown("O elemento $R'_2/s$ concentra dois efeitos físicos em série:")
        _eq(r"\frac{R'_2}{s} = R'_2 \;+\; R'_2\frac{1-s}{s}")
        st.markdown(
            "onde $R'_2$ é a **resistência real do rotor** (perdas Joule) e "
            "$R'_2(1-s)/s$ é o equivalente resistivo da **potência mecânica convertida**."
        )

    st.divider()

    # 1b. Circuito IEEE
    _h4("Circuito IEEE — Modelo Simplificado (sem $R_{fe}$)")
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown(
            "$R_{fe}$ é omitido — apenas $jX_m$ permanece no ramo *shunt*. "
            "Simplificação válida porque as perdas no ferro representam tipicamente "
            "$P_{fe} \\lesssim 2\\%\\,P_{nom}$; $R_{fe}$ é contabilizado "
            "separadamente no cálculo de rendimento $\\eta$."
        )
        st.markdown("Equação de malha do estator:")
        _eq(r"\bar{V}_1 = \bar{I}_1(R_s + jX_{ls}) + j X_m(\bar{I}_1 - \bar{I}'_2)")
        st.markdown(
            "Este é o circuito de referência para derivação das equações de estado "
            "do modelo $0dq$ de Krause implementado no simulador."
        )
    with col_img:
        _show_img("imgs/ind_ieee.png")

    st.divider()

    # 1c. Thévenin
    _h4("Equivalente de Thévenin — Redução da Malha do Rotor")
    col_img, col_txt = st.columns([1, 1])
    with col_img:
        _show_img("imgs/ind_thevenin.png")
    with col_txt:
        st.markdown(
            "O estator e o ramo de magnetização são substituídos por uma fonte $V_{th}$ "
            "com impedância $Z_{th}$, produzindo uma **malha única para o rotor**:"
        )
        _eq(r"V_{th} \approx V_1 \frac{X_m}{X_1+X_m}, \quad R_{th} \approx R_1\!\left(\frac{X_m}{X_1+X_m}\right)^{\!2}, \quad X_{th} \approx X_1")
        st.markdown("Torque eletromagnético em função de $s$:")
        _eq(r"T_e(s) = \frac{3\,V_{th}^2\,R'_2/s}{\omega_s\!\left[(R_{th}+R'_2/s)^2+(X_{th}+X'_2)^2\right]}")
        st.markdown(
            "Esta expressão explícita de $T_e(s)$ é a base do **Teorema de Boucherot** "
            "(Aba 2) e, ao ser linearizada no referencial $dq$, origina as equações de estado "
            "do **modelo de Krause** integradas pelo simulador."
        )

    st.divider()

    # 1d. Modelo dq de Krause
    _h4("Do Circuito Equivalente ao Modelo $0dq$ de Krause")
    st.markdown(
        "O simulador resolve as equações diferenciais no **referencial $dq$ síncrono** "
        "($\\omega_{ref} = \\omega_e$), usando os **fluxos concatenados** "
        "$\\psi_{qs},\\,\\psi_{ds},\\,\\psi_{qr},\\,\\psi_{dr}$ como variáveis de estado, "
        "junto com a velocidade rotórica $\\omega_r$."
    )
    st.markdown("Equações de estado (referencial síncrono):")
    _eq(r"\dot{\psi}_{qs} = \omega_b\!\left(V_{qs} - \tfrac{\omega_e}{\omega_b}\psi_{ds} + \tfrac{R_s}{X_{ls}}(\psi_{mq}-\psi_{qs})\right)")
    _eq(r"\dot{\psi}_{qr} = \omega_b\!\left(-\tfrac{\omega_e-\omega_r}{\omega_b}\psi_{dr} + \tfrac{R_r}{X_{lr}}(\psi_{mq}-\psi_{qr})\right)")
    _eq(r"T_e = \tfrac{3}{2}\cdot\tfrac{p}{2}\cdot\tfrac{1}{\omega_b}(\psi_{ds}\,i_{qs}-\psi_{qs}\,i_{ds})")
    _eq(r"\dot{\omega}_r = \tfrac{p}{2J}(T_e - T_L) - \tfrac{B}{J}\,\omega_r")
    st.markdown(
        "Os eixos $q$ e $d$ correspondem, respectivamente, às projeções em quadratura "
        "e em fase da tensão de alimentação no referencial síncrono. O acoplamento entre "
        "eles replica, em tempo real, o comportamento previsto pelo circuito equivalente em "
        "regime permanente."
    )

    st.divider()

    # 1e. Gaiola Dupla
    _h4("Circuito com Gaiola de Esquilo Dupla")
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown(
            "Dois ramos de rotor em paralelo: gaiola **externa** "
            "($R_{2e}$ alto, $X_{2e}$ baixo) e **interna** "
            "($R_{2i}$ baixo, $X_{2i}$ alto). Impedância equivalente:"
        )
        _eq(r"Z'_{2,eq} = \frac{Z'_{2e}\,Z'_{2i}}{Z'_{2e}+Z'_{2i}}")
        st.markdown(
            "O **efeito pelicular** redistribui a corrente automaticamente "
            "com a frequência rotórica $f_r = s\\cdot f$:"
        )
        st.markdown(
            "- **Partida** ($s\\approx 1$, $f_r = f$): corrente concentra-se "
            "na gaiola externa $\\Rightarrow$ alto $T_{part}$.\n"
            "- **Regime** ($s\\approx 0{,}04$, $f_r \\approx 2$–$4\\;$Hz): "
            "corrente migra para a gaiola interna $\\Rightarrow$ baixo $s_{nom}$, alto $\\eta$."
        )
    with col_img:
        _show_img("imgs/ind_ieee_duplo.png")


# ─────────────────────────────────────────────────────────────────────────────
# ABA 2 — COMPORTAMENTO DINÂMICO E TORQUE
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_dinamica() -> None:
    st.markdown(
        "O **escorregamento** $s = (n_s - n_r)/n_s$ governa o modo de operação da máquina. "
        "Três regiões fisicamente distintas dividem a curva $T_e \\times n$, "
        "com dinâmicas e riscos operacionais diferentes."
    )

    # Curva completa
    _show_img("imgs/T_x_s.png", width="88%")

    st.divider()

    # Três regiões
    col1, col2, col3 = st.columns(3)
    with col1:
        _h4("Região 1 — Frenagem ($s > 1$)")
        st.markdown(
            "O rotor gira em sentido oposto ao campo girante. "
            "$T_e < 0$: a máquina age como **freio eletromagnético** oposto ao movimento."
        )
        _eq(r"P_{cu,2} = s\,P_{ag} > P_{ag} \quad (s>1)")
        st.markdown(
            "O rotor absorve mais energia do que a fornecida pela rede — "
            "a diferença provém da **energia cinética da carga**."
        )
        _div_warn("Aplicação: *plugging* (inversão de fase para parada forçada). "
                  "Risco severo de sobreaquecimento — operação limitada a segundos.")
    with col2:
        _h4("Região 2 — Motor ($0 < s < 1$)")
        st.markdown("Operação nominal. Potência elétrica convertida em mecânica:")
        _eq(r"P_{mec} = (1-s)\,P_{ag} = T_e\,\omega_r")
        st.markdown(
            "**Região estável:** $n_{max} < n < n_s$ — perturbações são "
            "autorreguladas pelo aumento de $T_e$ quando $n$ cai.  \n"
            "**Região instável:** $0 < n < n_{max}$ — risco de "
            "*travamento (stall)* sob carga.  \n"
            "Escorregamento nominal típico: $s_n \\approx 0{,}02$–$0{,}06$."
        )
    with col3:
        _h4("Região 3 — Gerador ($s < 0$)")
        st.markdown(
            "Rotor acelerado acima de $n_s$ por fonte motriz externa. "
            "$T_e$ inverte sentido: a máquina entrega potência elétrica à rede."
        )
        _eq(r"P_{ag} = T_e\,\omega_s < 0 \;\Rightarrow\; P_{out,ele} > 0")
        st.markdown(
            "$P_{cu,2} = s\\,P_{ag} < 0$: o rotor absorve potência mecânica "
            "e a transfere ao entreferro."
        )
        _div_warn("Aplicações: geração eólica de indução, freio regenerativo em acionamentos.")

    st.divider()

    # Boucherot
    _h4("Torque Máximo e Escorregamento Crítico — Teorema de Boucherot")
    st.markdown(
        "Derivando $T_e(s)$ em relação a $s$ e igualando a zero, obtém-se o par "
        "$(T_{max},\\, s_{cr})$:"
    )
    _eq(r"T_{max} = \frac{3\,V_{th}^2}{2\,\omega_s\!\left(R_{th} + \sqrt{R_{th}^2 + (X_{th}+X'_2)^2}\right)}")
    _eq(r"s_{cr} = \frac{R'_2}{\sqrt{R_{th}^2 + (X_{th}+X'_2)^2}}")
    st.markdown(
        "**Teorema de Boucherot:** $T_{max}$ *não depende de $R'_2$*. "
        "Variar $R'_2$ apenas **desloca** $s_{cr}$ sem alterar a amplitude do pico. "
        "Para obter torque de partida máximo ($T_{part} = T_{max}$), basta impor $s_{cr} = 1$:"
    )
    _eq(r"R'_2\big|_{T_{part}=T_{max}} = \sqrt{R_{th}^2 + (X_{th}+X'_2)^2}")
    st.markdown(
        "Em **motores de rotor bobinado**, resistências externas são inseridas "
        "nos anéis coletores apenas na partida e depois curto-circuitadas, explorando este princípio."
    )

    st.divider()

    # Efeito de R'₂ na curva
    _h4("Curvas $T_e \\times n$ — Variação de $R'_2$ (Boucherot na prática)")
    col_img, col_txt = st.columns([1, 1])
    with col_img:
        _show_img("imgs/TR2.png")
    with col_txt:
        st.markdown(
            "$T_{max}$ é **invariante** com $R'_2$. "
            "O que muda é o escorregamento crítico: $s_{cr} \\propto R'_2$."
        )
        st.markdown(
            "- $R'_2 \\downarrow$: $s_{cr} \\downarrow$ — pico próximo a $n_s$ "
            "$\\Rightarrow$ alta eficiência em regime, baixo torque de partida.\n"
            "- $R'_2 \\uparrow$: $s_{cr} \\uparrow$ — pico a baixa rotação "
            "$\\Rightarrow$ alto torque de partida, alto $s_{nom}$ e perdas em regime."
        )
        _eq(r"T_{part} = T_{max} \;\Leftrightarrow\; R'_2 = \sqrt{R_{th}^2 + (X_{th}+X'_2)^2}")

    st.divider()

    # Gaiola dupla — torque
    _h4("Gaiola de Esquilo Dupla — Composição do Torque")
    col_txt, col_img = st.columns([1, 1])
    with col_txt:
        st.markdown("O torque resultante é a **superposição** dos torques de cada gaiola:")
        _eq(r"T_e = T_{ext} + T_{int} = \frac{3}{\omega_s}\!\left(\frac{|V_{ag}|^2 R'_{2e}/s}{|Z'_{2e}|^2} + \frac{|V_{ag}|^2 R'_{2i}/s}{|Z'_{2i}|^2}\right)")
        st.markdown(
            "**Na partida** ($s=1$, $f_r = f$): o **efeito pelicular** "
            "força a corrente para a gaiola externa ($R'_{2e}$ alto) "
            "$\\Rightarrow$ alto $T_{part}$.\n\n"
            "**Em regime** ($s \\ll 1$, $f_r \\approx s\\,f$): "
            "$X'_{2i} \\to 0$ — gaiola interna ($R'_{2i}$ baixo) domina "
            "$\\Rightarrow$ baixo $s_{nom}$, alto $\\eta$.\n\n"
            "O resultado é uma variação *automática e contínua* de $R'_2$ efetivo "
            "durante a aceleração — sem componentes externos, graças ao "
            "**perfil geométrico das barras do rotor**."
        )
    with col_img:
        _show_img("imgs/SCdupla.png")


# ─────────────────────────────────────────────────────────────────────────────
# ABA 3 — BALANÇO ENERGÉTICO E FLUXO DE POTÊNCIA
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_potencia() -> None:
    st.markdown(
        "As potências fluem de forma **encadeada**, com cada estágio dissipando ou convertendo "
        "uma fração determinada por $s$, $R$, $X$ e $\\omega$. "
        "O modo de operação (motor, gerador, frenagem) inverte o sentido do fluxo."
    )

    st.divider()
    _h4("Relações Fundamentais de Potência")
    st.markdown("As identidades abaixo valem em **regime permanente** para qualquer $s$:")
    st.markdown(
        """
| Grandeza | Expressão | Nota |
|---|---|---|
| **Potência de entrada** $P_{in}$ | $3\\,V_1\\,I_1\\cos\\varphi$ | Trifásico — terminais do estator |
| **Perdas no estator** $P_{cu,1}$ | $3\\,I_1^2\\,R_s$ | Joule nos enrolamentos estatóricos |
| **Perdas no ferro** $P_{fe}$ | $3\\,V_\\phi^2/R_{fe}$ | Histerese + Foucault no núcleo |
| **Potência no entreferro** $P_{ag}$ | $T_e\\,\\omega_s = P_{in} - P_{cu,1} - P_{fe}$ | $\\omega_s = 4\\pi f/p$ |
| **Perdas no rotor** $P_{cu,2}$ | $s\\,P_{ag} = 3\\,I_2'^2\\,R_r$ | Fração de $P_{ag}$ dissipada no rotor |
| **Potência mecânica** $P_{mec}$ | $(1-s)\\,P_{ag} = T_e\\,\\omega_r$ | $\\omega_r = (1-s)\\,\\omega_s$ |
| **Potência útil** $P_{out}$ | $P_{mec} - P_{rot}$ | $P_{rot}$: atrito + ventilação |
| **Rendimento** $\\eta$ | $P_{out}/P_{in}$ | Máximo quando $P_{cu,1} \\approx P_{fe}+P_{rot}$ |
"""
    )

    st.divider()

    # Três modos lado a lado
    c1, c2, c3 = st.columns(3)
    with c1:
        _h4("Modo Motor")
        _show_img("imgs/fluxo_P_motor.png")
        _eq(r"P_{in} \xrightarrow{-P_{cu,1}} P_{ag} \xrightarrow{-P_{cu,2}} P_{mec} \xrightarrow{-P_{rot}} P_{out}")
        st.markdown(
            "Relação-chave: $P_{cu,2} = s\\,P_{ag}$ e $P_{mec} = (1-s)P_{ag}$. "
            "A eficiência é maximizada com baixo escorregamento nominal."
        )
    with c2:
        _h4("Modo Gerador")
        _show_img("imgs/fluxo_P_gerador.png")
        _eq(r"P_{in,mec} \xrightarrow{-P_{rot}} P_{mec} \xrightarrow{-P_{cu,2}} P_{ag} \xrightarrow{-P_{cu,1}} P_{out}")
        st.markdown(
            "Sentido invertido: potência mecânica entra pelo eixo, "
            "potência elétrica sai pelos terminais do estator para a rede."
        )
    with c3:
        _h4("Modo Frenagem ($s > 1$)")
        _show_img("imgs/fluxo_P_frenagem.png")
        _eq(r"P_{ele} + P_{cin} \longrightarrow P_{cu,2}")
        st.markdown(
            "Energia elétrica da rede *e* energia cinética do eixo "
            "convertem-se **integralmente em calor no rotor**."
        )
        _div_warn("Operação breve — o rotor pode queimar em segundos. "
                  "$P_{cu,2} = s\\,P_{ag} > P_{ag}$ porque $s > 1$.")

    st.divider()

    # Insight qualitativo sobre s
    _h4("Interpretação Física do Escorregamento")
    st.markdown(
        "O escorregamento $s$ é a variável que **particiona** a potência do entreferro "
        "entre perdas e produção mecânica:"
    )
    _eq(r"P_{ag} = \underbrace{s\,P_{ag}}_{P_{cu,2}\;\text{(calor)}} + \underbrace{(1-s)\,P_{ag}}_{P_{mec}\;\text{(trabalho)}}")
    st.markdown(
        "Um motor com $s = 0{,}05$ (5%) dissipa apenas 5% da potência do entreferro no rotor — "
        "o restante 95% é convertido em trabalho mecânico. Por isso **motores eficientes "
        "operam com baixo escorregamento**.\n\n"
        "Na frenagem ($s > 1$), a equação acima exige $P_{cu,2} > P_{ag}$, o que só é possível "
        "porque a **energia cinética do eixo** alimenta adicionalmente o rotor."
    )


# ─────────────────────────────────────────────────────────────────────────────
# ABA DINÂMICA DE OPERAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_dinamica_operacao() -> None:
    st.markdown(
        "A compreensão da dinâmica de operação do motor de indução trifásico exige "
        "a análise de cada fase do ciclo eletromecânico — da energização inicial até "
        "a parada completa. Esta aba percorre esses estados em ordem cronológica, "
        "relacionando os fenômenos físicos às equações que os governam."
    )

    # ── pré-calcula curva T×n ─────────────────────────────────────────────────
    s_mot  = np.linspace(0.002, 1.0, 600)
    T_mot  = np.array([_torque_ref(s) for s in s_mot])
    n_mot  = _ns_REF * (1 - s_mot)
    idx_pk = int(np.argmax(T_mot))
    T_load = T_mot[idx_pk] * 0.45
    idx_ss = next((i for i in range(idx_pk, len(T_mot) - 1)
                   if T_mot[i] >= T_load >= T_mot[i + 1]), len(T_mot) - 1)

    def _style_ax(a):
        a.set_facecolor("white")
        for sp in a.spines.values():
            sp.set_edgecolor("#cccccc")
        a.tick_params(colors="#333333")
        a.grid(True, alpha=0.35, linestyle=":", color="#bbbbbb")

    # ── CARD 1 — Partida, Aceleração e Regime ────────────────────────────────
    st.divider()
    _h4("Partida, Aceleração e Regime Permanente")
    st.markdown(
        "No instante em que o estator é conectado à rede trifásica, as três correntes "
        "defasadas de 120° entre si estabelecem um **campo magnético girante** "
        "que rotaciona à velocidade síncrona $n_s$:"
    )
    _eq(r"n_s = \frac{120\,f_e}{p} \quad \text{(RPM)}")
    st.markdown(
        "Com o rotor em repouso ($s = 1$), a impedância rotórica é predominantemente "
        "reativa, resultando em uma corrente de partida $I_p$ entre 6 e 8 vezes a nominal "
        "e em um torque inicial relativamente modesto — explicado pelo baixo fator de "
        "potência imposto pela reatância de dispersão:"
    )
    _eq(r"I_p \approx (6 \text{ a } 8)\, I_n \quad (s = 1)")
    st.markdown(
        "À medida que o rotor acelera, o escorregamento $s$ diminui e a frequência das "
        "correntes rotóricas $f_r = s \\cdot f_e$ cai. A redução da reatância rotórica "
        "melhora o fator de potência e eleva o torque até o **Torque Máximo** "
        "(Pull-out) no escorregamento crítico $s_{cr}$. Para $s < s_{cr}$, o torque "
        "decresce até o ponto de equilíbrio com a carga — o **regime permanente** "
        "— onde obrigatoriamente $n < n_s$, pois sem escorregamento não há indução:"
    )
    _eq(r"s = \frac{n_s - n}{n_s} > 0 \quad \Longleftrightarrow \quad n < n_s")

    fig1, ax = plt.subplots(figsize=(8, 4.2))
    fig1.patch.set_facecolor("white")
    _style_ax(ax)
    ax.plot(n_mot, T_mot, color="#222222", linewidth=2.5, label=r"Curva $T \times n$")
    ax.axhline(T_load, color="#555555", linestyle="--", linewidth=1.4, label="Carga $T_L$")
    ax.axvline(_ns_REF, color="#aaaaaa", linestyle=":", linewidth=1)
    ax.text(_ns_REF + 10, T_mot.max() * 0.04, "$n_s$", color="#888", fontsize=9)
    ax.scatter([n_mot[-1]], [T_mot[-1]], color="#333333", s=90, zorder=5)
    ax.annotate("Partida  $s=1$\n$I_p \\approx 6\\!-\\!8\\,I_n$",
                xy=(n_mot[-1], T_mot[-1]),
                xytext=(n_mot[-1] - 370, T_mot[-1] + T_mot.max() * 0.09),
                color="#333333", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2))
    ax.scatter([n_mot[idx_pk]], [T_mot[idx_pk]], color="#555555", s=90, zorder=5)
    ax.annotate("Torque Máximo\n(Pull-out)",
                xy=(n_mot[idx_pk], T_mot[idx_pk]),
                xytext=(n_mot[idx_pk] - 400, T_mot[idx_pk] - T_mot.max() * 0.14),
                color="#555555", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.2))
    ax.scatter([n_mot[idx_ss]], [T_load], color="#111111", s=90, zorder=5)
    ax.annotate("Regime\nPermanente",
                xy=(n_mot[idx_ss], T_load),
                xytext=(n_mot[idx_ss] + 35, T_load + T_mot.max() * 0.13),
                color="#111111", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#111111", lw=1.2))
    ax.annotate("", xy=(n_mot[idx_ss] - 25, T_load + 1),
                xytext=(n_mot[-1] - 10, T_mot[-1] + 1),
                arrowprops=dict(arrowstyle="->", color="#999999", lw=1.5,
                                connectionstyle="arc3,rad=-0.25"))
    ax.set_xlabel("Velocidade (rpm)", fontsize=10, fontweight="bold", color="#222")
    ax.set_ylabel("Torque (N·m)",     fontsize=10, fontweight="bold", color="#222")
    ax.set_title("Trajetória de Operação — Partida até Regime Permanente",
                 fontsize=11, fontweight="bold", color="#111")
    ax.legend(fontsize=9, facecolor="white", edgecolor="#cccccc")
    ax.set_xlim(0, _ns_REF * 1.04)
    ax.set_ylim(0, T_mot.max() * 1.2)
    fig1.tight_layout()
    st.image(_fig_to_bytes(fig1))

    # ── CARD 2 — Dinâmica de Carga ───────────────────────────────────────────
    st.divider()
    _h4("Dinâmica de Carga — Aplicação e Alívio Bruscos")
    st.markdown(
        "Quando uma carga é aplicada bruscamente ao eixo, o torque resistente supera "
        "momentaneamente $T_{em}$ e o rotor desacelera. O aumento do escorregamento "
        "eleva $f_r = s \\cdot f_e$, a corrente rotórica $I_2$ e, por acoplamento "
        "magnético, a corrente estatórica $I_1$. O torque cresce até um novo equilíbrio "
        "em velocidade ligeiramente menor, governado pela equação de movimento:"
    )
    _eq(r"\frac{d\omega_r}{dt} = \frac{p}{2J}(T_{em} - T_{load}) - \frac{B}{J}\,\omega_r")
    st.markdown(
        "No alívio de carga, o processo se inverte: $T_{em}$ supera o resistente, "
        "o rotor acelera e o escorregamento reduz-se a valores muito pequenos "
        "($s \\approx 0{,}005$ a $0{,}02$), suficientes apenas para suprir as "
        "perdas mecânicas e no ferro. O gráfico abaixo ilustra o afundamento de "
        "velocidade $\\Delta n$ e o pico transitório de torque ao aplicar carga:"
    )

    _t   = np.linspace(0.0, 5.0, 1000)
    t_on = 2.0
    n0, n1 = 1795.0, 1762.0
    tau_n  = 0.35
    Te0, Te1, Te_pk = 8.0, 42.0, 68.0
    tau_Te = 0.12
    _n  = np.where(_t < t_on, n0,
                   n1 + (n0 - n1) * np.exp(-(_t - t_on) / tau_n))
    _Te = np.where(_t < t_on, Te0,
                   Te1 + (Te_pk - Te1) * np.exp(-(_t - t_on) / tau_Te) *
                   np.sin(np.pi * (_t - t_on) / (3 * tau_Te)).clip(0))
    _Te = np.where(_t < t_on, Te0, _Te)

    fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.8), sharex=True)
    fig2.patch.set_facecolor("white")
    for a in (ax1, ax2):
        _style_ax(a)
        a.axvline(t_on, color="#555555", linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.plot(_t, _n, color="#222222", linewidth=2)
    ax1.set_ylabel("Velocidade (rpm)", fontsize=9, fontweight="bold", color="#222")
    ax1.annotate("Carga\naplicada", xy=(t_on, n0), xytext=(t_on + 0.35, n0 + 3),
                 color="#555555", fontsize=8,
                 arrowprops=dict(arrowstyle="->", color="#555555", lw=1.1))
    ax1.annotate(f"$\\Delta n$ = {n0 - n1:.0f} rpm",
                 xy=((t_on + 5) / 2, (n0 + n1) / 2), color="#555", fontsize=8, ha="center")
    ax2.plot(_t, _Te, color="#444444", linewidth=2)
    ax2.set_ylabel("Torque $T_e$ (N·m)", fontsize=9, fontweight="bold", color="#222")
    ax2.set_xlabel("Tempo (s)",           fontsize=9, fontweight="bold", color="#222")
    fig2.suptitle("Resposta Transitória — Aplicação Brusca de Carga",
                  fontsize=11, fontweight="bold", color="#111")
    fig2.tight_layout()
    st.image(_fig_to_bytes(fig2))

    # ── CARD 3 — Frenagem e Parada ───────────────────────────────────────────
    st.divider()
    _h4("Frenagem e Parada Controlada")
    st.markdown(
        "Em diversas aplicações — guindastes, prensas, correias transportadoras — "
        "a parada por inércia é inaceitável por razões de segurança ou produtividade. "
        "Existem três métodos de frenagem ativa para motores de indução, cada um com "
        "princípio físico, velocidade de parada e custo térmico distintos."
    )
    st.markdown(
        "**1. Frenagem Regenerativa** — "
        "ocorre quando a carga impulsiona o rotor acima de $n_s$, tornando $s$ negativo. "
        "O fluxo de potência se inverte: a máquina converte energia cinética do eixo em "
        "energia elétrica devolvida à rede. É o método mais eficiente, mas exige que o "
        "sistema receptor (inversor com ponte regenerativa ou resistor de frenagem) consiga "
        "absorver o retorno de energia."
    )
    _eq(r"s < 0 \;\Rightarrow\; P_{ag} < 0 \;\Rightarrow\; \text{potência devolvida à rede}")
    st.markdown(
        "**2. Contracorrente (Plugging)** — "
        "duas das três fases da alimentação são invertidas com o motor em movimento. "
        "O campo girante reverte instantaneamente, produzindo escorregamento $s \\approx 2$ "
        "e torque contrário ao movimento. A parada é a mais rápida, porém as correntes "
        "ultrapassam as de partida e o calor dissipado no rotor é severo. O motor "
        "*deve* ser desconectado exatamente em $n = 0$; caso contrário acelera "
        "no sentido oposto."
    )
    _eq(r"s = \frac{n_s - n}{n_s} \approx 2 \quad (n_s \text{ invertida, } n \text{ positiva})")
    st.markdown(
        "**3. Injeção de Corrente Contínua (CC)** — "
        "a alimentação trifásica é desconectada e aplica-se tensão CC a dois terminais "
        "do estator. O campo fixo resultante interage com os condutores do rotor em "
        "movimento, induzindo correntes que produzem torque de frenagem proporcional "
        "à velocidade — que se anula naturalmente em $n = 0$, eliminando o risco "
        "de inversão. A parada é mais lenta, porém suave e precisa."
    )
    _eq(r"T_{brake} \propto \omega_r \;\xrightarrow{\;\omega_r \to 0\;}\; 0")
    st.markdown("O gráfico compara $n(t)$ para os três métodos a partir do mesmo ponto nominal. "
                "A linha tracejada indica o que ocorre se o plugging *não* for interrompido no zero:")

    _tb   = np.linspace(0.0, 2.6, 900)
    n_nom = 1760.0
    t_plug_stop = 0.35
    _n_plug_motor = n_nom * (1.0 - _tb / t_plug_stop)
    tau_dc  = 1.05
    _n_dc   = n_nom * np.exp(-_tb / tau_dc)
    tau_reg = 0.55
    _n_reg  = n_nom * np.exp(-_tb / tau_reg)
    mask_plug = _tb <= t_plug_stop

    fig3, ax3 = plt.subplots(figsize=(8, 4.2))
    fig3.patch.set_facecolor("white")
    _style_ax(ax3)
    ax3.plot(_tb[mask_plug], _n_plug_motor[mask_plug],
             color="#111111", linewidth=2.3, label="Contracorrente (Plugging)")
    ax3.plot(_tb[~mask_plug][: int(0.35 / (_tb[1] - _tb[0]))],
             _n_plug_motor[~mask_plug][: int(0.35 / (_tb[1] - _tb[0]))],
             color="#111111", linewidth=1.6, linestyle="--", alpha=0.55)
    ax3.plot(_tb, _n_reg, color="#555555", linewidth=2.3, linestyle="--",
             label="Regenerativa")
    ax3.plot(_tb, _n_dc,  color="#888888", linewidth=2.3, linestyle=":",
             label="Injeção de CC")
    ax3.axhline(0, color="#aaaaaa", linewidth=0.9, linestyle="-")
    ax3.axhline(n_nom, color="#cccccc", linewidth=0.8, linestyle=":")
    ax3.annotate("Desconectar em\n$n = 0$ (plugging)",
                 xy=(t_plug_stop, 0),
                 xytext=(t_plug_stop + 0.25, n_nom * 0.18),
                 color="#333333", fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2))
    ax3.set_xlabel("Tempo desde o início da frenagem (s)",
                   fontsize=10, fontweight="bold", color="#222")
    ax3.set_ylabel("Velocidade (rpm)", fontsize=10, fontweight="bold", color="#222")
    ax3.set_title("Comparação dos Métodos de Frenagem — $n(t)$",
                  fontsize=11, fontweight="bold", color="#111")
    ax3.legend(fontsize=9.5, facecolor="white", edgecolor="#cccccc")
    ax3.set_xlim(0, 2.6)
    ax3.set_ylim(-200, n_nom * 1.12)
    fig3.tight_layout()
    st.image(_fig_to_bytes(fig3))


# ─────────────────────────────────────────────────────────────────────────────
# ABA 4 — GUIA DE SENSIBILIDADE DE PARÂMETROS
# ─────────────────────────────────────────────────────────────────────────────

_PARAMS_ELETRICOS = [
    {
        "nome": "$V_l$ — Tensão de Linha (RMS)",
        "desc": (
            "Define a amplitude do campo magnético girante no estator. "
            "Determina o fluxo no entreferro: $\\Phi \\propto V_l/f$. "
            "É a grandeza com maior impacto no torque disponível."
        ),
        "up": (
            "O torque máximo cresce com $V_l^2$: $T_{max} \\propto V_{th}^2 \\propto V_l^2$. "
            "A corrente de partida também aumenta significativamente."
        ),
        "down": (
            "O torque de partida cai — pode tornar-se insuficiente para vencer a inércia da carga, "
            "impedindo a partida (stall na aceleração)."
        ),
        "warn": (
            "Sobretensão ($> 110\\%\\,V_n$) provoca **saturação do núcleo** e "
            "degradação térmica do isolamento. "
            "Subtensão severa ($< 85\\%\\,V_n$) pode causar **travamento (stall)** sob carga nominal."
        ),
    },
    {
        "nome": "$f$ — Frequência da Rede",
        "desc": (
            "Determina a velocidade síncrona: $n_s = 120\\,f/p\\;$(rpm). "
            "As reatâncias escalam proporcionalmente: $X = 2\\pi f L$."
        ),
        "up": (
            "Aumenta $n_s$, $X_m$, $X_{ls}$, $X_{lr}$. "
            "Com $V_l$ constante a relação $V/f$ cai, reduzindo o fluxo e o torque máximo."
        ),
        "down": (
            "Reduz a velocidade de operação. Com $V_l$ constante a relação $V/f$ cresce, "
            "levando o núcleo à **saturação magnética**."
        ),
        "warn": (
            "Operar fora da frequência nominal sem controle $V/f = $ const. compromete "
            "o fluxo, a eficiência e a integridade térmica da máquina."
        ),
    },
    {
        "nome": "$R_s$ — Resistência do Estator",
        "desc": (
            "Representa as perdas Joule nos enrolamentos estatóricos: $P_{cu,1} = 3I_1^2 R_s$. "
            "Provoca queda de tensão interna, reduzindo a tensão efetiva no entreferro."
        ),
        "up": (
            "Aumenta a dissipação térmica e reduz $T_{max}$, "
            "pois $R_{th} \\uparrow$ eleva o denominador da expressão de Boucherot."
        ),
        "down": (
            "Minimiza perdas internas e melhora o rendimento. "
            "Em valores extremos, aproxima o modelo de um transformador ideal no primário."
        ),
        "warn": (
            "$R_s$ excessivo (enrolamentos danificados ou sobreaquecidos) causa "
            "**sobreaquecimento progressivo**. "
            "Valores muito próximos de zero podem gerar **instabilidade numérica** no integrador."
        ),
    },
    {
        "nome": "$R_r$ — Resistência do Rotor",
        "desc": (
            "Parâmetro determinante da curva de torque. "
            "Define o escorregamento crítico: $s_{cr} = R_r / \\sqrt{R_{th}^2 + X_{eq}^2}$."
        ),
        "up": (
            "$s_{cr}$ aumenta — pico de torque desloca-se para rotações menores. "
            "O torque de partida cresce até o limite $T_{max}$ (quando $s_{cr} = 1$)."
        ),
        "down": (
            "Melhora a eficiência ($s_{nom}$ cai) e reduz o escorregamento em regime. "
            "O torque de partida diminui proporcionalmente."
        ),
        "warn": (
            "$R_r$ muito alto indica **barras fraturadas** — provoca escorregamento excessivo e vibração. "
            "Valores nulos causam **singularidade matemática** nas equações do rotor."
        ),
    },
    {
        "nome": "$X_m$ — Reatância de Magnetização",
        "desc": (
            "Representa o ramo de magnetização (*shunt*) do circuito: "
            "caminho do fluxo principal pelo núcleo. "
            "Relaciona-se com a indutância mútua: $X_m = 2\\pi f L_m$."
        ),
        "up": (
            "Reduz a corrente de magnetização em vazio $I_m = V_1/X_m$, "
            "melhorando o fator de potência em regime."
        ),
        "down": (
            "Aumenta $I_m$ — maior corrente reativa necessária para excitar o núcleo, "
            "piorando o fator de potência."
        ),
        "warn": (
            "$X_m$ baixo indica núcleo de má qualidade ou em **saturação magnética**. "
            "Valores excessivamente baixos podem causar **divergência numérica** no integrador."
        ),
    },
    {
        "nome": "$R_{fe}$ — Resistência de Perdas no Ferro",
        "desc": (
            "Modela histerese e correntes de Foucault em paralelo com $X_m$. "
            "Perdas no ferro: $P_{fe} = 3\\,V_\\phi^2 / R_{fe}$. "
            "Valores típicos: $100$–$2000\\;\\Omega$ para máquinas de médio porte."
        ),
        "up": (
            "$P_{fe}$ menor. O motor opera com maior eficiência, "
            "especialmente em regimes de baixa carga onde as perdas no núcleo dominam."
        ),
        "down": (
            "$P_{fe}$ maior. O rendimento cai, especialmente em operação a vazio. "
            "Pode indicar lâminas de baixa qualidade ou operação a frequência elevada."
        ),
        "warn": (
            "$R_{fe}$ é usado **apenas no cálculo estático** de potências e rendimento — "
            "não influencia o ODE nem a dinâmica simulada. "
            "Valores $< 50\\;\\Omega$ indicam núcleo de baixíssima qualidade."
        ),
    },
    {
        "nome": "$X_{ls}$ e $X_{lr}$ — Reatâncias de Dispersão",
        "desc": (
            "Modelam fluxos que não enlaçam ambos os enrolamentos (dispersão). "
            "Definem a reatância de curtocircuito: $X_{cc} = X_{ls} + X_{lr}$, "
            "que limita o torque máximo e a corrente de partida."
        ),
        "up": (
            "Aumenta $X_{cc}$, reduzindo $T_{max} \\propto 1/(X_{th}+X_{lr})$. "
            "Corrente de partida cai, facilitando a proteção."
        ),
        "down": (
            "$T_{max}$ sobe e correntes de partida aumentam. "
            "Torna o motor mais sensível a transitórios de carga e variações de tensão."
        ),
        "warn": (
            "Dispersão muito baixa resulta em **picos de corrente perigosos ao isolamento**. "
            "Dispersão excessiva pode **impedir a partida** sob carga nominal."
        ),
    },
]

_PARAMS_MECANICOS = [
    {
        "nome": "$p$ — Número de Polos",
        "desc": (
            "Define a velocidade síncrona: $n_s = 120\\,f/p\\;$(rpm), "
            "ou equivalentemente $\\omega_s = 4\\pi f/p\\;$(rad/s)."
        ),
        "up": (
            "Reduz $n_s$. Para a mesma potência $P = T\\,\\omega$, "
            "o torque nominal deve ser proporcionalmente maior."
        ),
        "down": (
            "Aumenta $n_s$ e $\\omega_s$. "
            "O torque nominal diminui para a mesma potência de saída."
        ),
        "warn": "$p$ deve ser sempre inteiro par. Valores ímpares invalidam o modelo físico.",
    },
    {
        "nome": "$J$ — Momento de Inércia",
        "desc": (
            "Governa a dinâmica de aceleração via equação mecânica: "
            "$J\\,\\dot{\\omega}_r = T_e - T_L - B\\,\\omega_r$. "
            "Inclui o rotor e a carga acoplada ao eixo."
        ),
        "up": (
            "Aceleração mais lenta — transitórios amortecidos e tempo de partida maior. "
            "Reduz a sensibilidade a variações abruptas de carga."
        ),
        "down": (
            "Resposta dinâmica acelerada — o rotor reage quase instantaneamente a variações de $T_e$. "
            "Útil para servoacionamentos, mas exige proteção contra sobrecargas rápidas."
        ),
        "warn": (
            "$J$ muito baixo pode gerar **oscilações numéricas ruidosas** no ODE. "
            "$J$ muito alto pode exigir $t_{max}$ muito grande para atingir o regime permanente."
        ),
    },
    {
        "nome": "$B$ — Coeficiente de Atrito Viscoso",
        "desc": (
            "Modela perdas mecânicas proporcionais à velocidade: "
            "$T_{atrito} = B\\,\\omega_r$ (mancais e ventilação)."
        ),
        "up": (
            "Aumenta o amortecimento do sistema e a dissipação mecânica. "
            "O ponto de equilíbrio em regime é deslocado para menor rotação."
        ),
        "down": (
            "Reduz perdas mecânicas. "
            "Se $B = 0$, o amortecimento depende exclusivamente da carga externa $T_L$."
        ),
        "warn": (
            "Valores elevados simulam **falha catastrófica em rolamentos** e "
            "podem impedir que o motor atinja a rotação nominal."
        ),
    },
]


def _render_tab_sensibilidade() -> None:
    st.markdown(
        "**Manual de calibração** do simulador: como cada parâmetro afeta qualitativamente "
        "o comportamento da máquina. Útil para diagnóstico, ajuste de modelo e estudo de falhas."
    )

    st.divider()
    st.markdown("### Parâmetros Elétricos")
    for item in _PARAMS_ELETRICOS:
        st.markdown(f"**{item['nome']}**")
        st.markdown(item["desc"])
        st.markdown(f"- **Se aumentar:** {item['up']}")
        st.markdown(f"- **Se diminuir:** {item['down']}")
        _div_warn(f"**Atenção — calibrações extremas:** {item['warn']}")
        st.write("")

    st.divider()
    st.markdown("### Parâmetros Mecânicos")
    for item in _PARAMS_MECANICOS:
        st.markdown(f"**{item['nome']}**")
        st.markdown(item["desc"])
        st.markdown(f"- **Se aumentar:** {item['up']}")
        st.markdown(f"- **Se diminuir:** {item['down']}")
        _div_warn(f"**Atenção — calibrações extremas:** {item['warn']}")
        st.write("")


# ─────────────────────────────────────────────────────────────────────────────
# ABA 5 — CONFIGURAÇÕES DE SIMULAÇÃO E ALERTAS
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_config() -> None:
    st.markdown(
        "Diretrizes para escolha do **tempo de simulação** $t_{max}$ e do "
        "**passo de integração** $h$, com critérios de estabilidade numérica "
        "e alertas para cenários que podem comprometer a simulação."
    )

    st.divider()
    _h4("Tempo de Simulação — $t_{max}$")
    st.markdown(
        "Define o horizonte temporal da integração numérica. "
        "Deve ser suficiente para conter o **transitório completo de partida** "
        "e, se necessário, a estabilização em regime permanente."
    )
    st.markdown("**Referência prática:**")
    st.markdown(
        "- Transitório de partida típico: $t_{part} \\approx 3$–$5 \\times \\tau_m$, "
        "onde $\\tau_m = J\\,\\omega_s / T_{e,nom}$.\n"
        "- Regime permanente: observar pelo menos $5$–$10$ ciclos elétricos após "
        "$t_{part}$ para calcular valores RMS confiáveis.\n"
        "- Experimentos com pulso de carga: incluir margem após $t_{off}$ "
        "para visualizar o retorno ao regime."
    )
    st.markdown(
        "- **$t_{max}$ maior:** Permite observar fenômenos de longo prazo e verificar estabilidade. "
        "Aumenta o custo computacional linearmente.\n"
        "- **$t_{max}$ menor:** Processamento rápido, mas arrisca truncar a análise antes da estabilização "
        "— os valores RMS e o torque médio ficam incorretos."
    )
    _div_warn(
        "**Atenção:** $t_{max}$ muito grande combinado com $h$ muito pequeno "
        "pode causar **estouro de memória** no navegador. "
        "Verifique: $N = t_{max}/h$ pontos armazenados."
    )

    st.divider()
    _h4("Passo de Integração — $h$")
    st.markdown(
        "Discretização temporal para o solver (**LSODA / scipy.odeint**). "
        "O passo controla precisão numérica e estabilidade da integração."
    )
    st.markdown("**Critério de estabilidade numérica:**")
    _eq(r"h \;\leq\; \frac{1}{20\,f}")
    st.markdown(
        "Este critério garante pelo menos **20 pontos por ciclo elétrico**, "
        "suficientes para integrar a frequência fundamental sem aliasing numérico."
    )
    st.markdown(
        """
| Frequência $f$ | $h_{max}$ recomendado | Pontos/ciclo |
|---|---|---|
| 50 Hz | $1{,}00\\;$ms | 20 |
| 60 Hz | $0{,}83\\;$ms | 20 |
| 60 Hz (alta fidelidade) | $0{,}20\\;$ms | 83 |
"""
    )
    st.markdown(
        "- **$h$ maior (passo grosso):** Simulação rápida, mas com risco de imprecisão nas correntes de partida "
        "e possível divergência numérica.\n"
        "- **$h$ menor (passo fino):** Alta fidelidade e estabilidade — indicado para análise de harmônicos "
        "e comparação com dados experimentais."
    )
    _div_warn(
        "**Atenção:** para $f = 60\\;$Hz, passos $h > 1\\;$ms costumam "
        "causar **divergência do integrador** — as correntes crescem "
        "indefinidamente nos primeiros ciclos de partida."
    )

    st.divider()
    _h4("Alertas de Calibração — Cenários Críticos")
    st.markdown(
        "As combinações de parâmetros abaixo podem comprometer a validade física "
        "da simulação ou causar falha numérica:"
    )
    st.markdown(
        """
| Cenário | Condição | Risco |
|---|---|---|
| **Saturação magnética** | $V_l/f \\gg (V_l/f)_{nom}$ ou $X_m$ muito baixo | Fluxo sai da região linear — $L_m$ cai, modelo dq deixa de ser válido. Sintoma: corrente de magnetização excessiva. |
| **Travamento (Stall)** | $T_L > T_{max}$ ou $V_l < 85\\%\\,V_n$ | Motor não acelera — fica preso na região instável da curva $T_e \\times n$. Corrente permanece elevada e o rotor superaquece. |
| **Divergência numérica** | $h > 1/(20f)$, $R_s \\approx 0$ ou $X_m \\approx 0$ | Correntes crescem sem limite nos primeiros ciclos. O simulador exibe valores absurdos (NaN, $\\infty$). |
| **Estouro de memória** | $N = t_{max}/h > 5 \\times 10^6$ pontos | Alocação excessiva de arrays NumPy — lentidão extrema ou travamento do navegador. |
| **Regime não atingido** | $t_{max} < 3\\,\\tau_m$ | Os valores RMS e de torque médio são calculados sobre dados transitórios — resultados de regime incorretos sem aviso explícito. |
"""
    )

    st.divider()
    _h4("Guia Rápido de Configuração")
    st.markdown("**Passo a passo para uma simulação confiável:**")
    st.markdown(
        "1. Calcule $\\tau_m \\approx J\\,\\omega_s / T_{e,nom}$ e defina $t_{max} \\geq 5\\,\\tau_m$.\n"
        "2. Escolha $h \\leq 1/(20f)$ — para 60 Hz use $h = 0{,}5\\;$ms como padrão seguro.\n"
        "3. Verifique que $T_L < T_{max}$ antes de simular (evita stall).\n"
        "4. Confirme $V_l/f$ próximo ao valor nominal (evita saturação).\n"
        "5. Se a simulação divergir, reduza $h$ pela metade e repita.\n"
        "6. Se o regime não aparecer nos gráficos, duplique $t_{max}$."
    )


# ─────────────────────────────────────────────────────────────────────────────
# ABA 7 — EXPERIMENTOS E PERTURBAÇÕES DE REDE
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_experimentos() -> None:
    st.markdown(
        "Cada experimento do simulador corresponde a um cenário físico distinto — "
        "partida, carga, geração ou falha de rede. "
        "Esta aba descreve o princípio de cada ensaio, as equações que o governam "
        "e os fenômenos observáveis nos gráficos."
    )

    st.divider()
    st.markdown("### Métodos de Partida")

    _h4("Partida Direta — DOL *(Direct On-Line)*")
    st.markdown(
        "O estator é conectado diretamente à rede em plena tensão $V_l$ no instante $t=0$. "
        "É o método mais simples, porém o mais agressivo: a corrente de partida atinge "
        "tipicamente 6 a 8 vezes a corrente nominal, gerando pico de torque e afundamento "
        "de tensão na rede."
    )
    _eq(r"I_{part} \approx (6\text{ a }8)\,I_n \quad (s=1,\; V = V_{nom})")
    st.markdown(
        "No simulador, a carga $T_l$ é aplicada em $t_{carga}$ (após a partida em vazio), "
        "permitindo observar o afundamento de velocidade e o transitório de corrente "
        "ao conectar a carga."
    )
    st.markdown(
        "- **Observar:** pico de corrente na partida, torque máximo (pull-out), tempo de aceleração.\n"
        "- **Risco:** sobrecarga térmica se $T_l > T_{max}$ — o motor trava (stall)."
    )

    st.write("")
    _h4("Partida Estrela-Triângulo — Y-D")
    st.markdown(
        "Na fase estrela ($0 < t < t_2$), cada enrolamento recebe $V_l/\\sqrt{3}$, "
        "reduzindo a corrente de partida e o torque a $1/3$ dos valores em triângulo:"
    )
    _eq(r"I_{part,Y} = \frac{1}{3}\,I_{part,\Delta}, \quad T_{part,Y} = \frac{1}{3}\,T_{part,\Delta}")
    st.markdown(
        "Em $t_2$, a chave comuta para triângulo: a tensão salta para $V_l$ e ocorre "
        "um **segundo pico de corrente** — muitas vezes ignorado na prática, "
        "mas visível no simulador. A carga $T_l$ é aplicada em $t_{carga} > t_2$."
    )
    st.markdown(
        "- **Observar:** dois picos de corrente (partida Y e comutação Y→D), redução de torque de partida.\n"
        "- **Limitação:** só aplicável a motores projetados para ligação em triângulo na tensão de linha."
    )

    st.write("")
    _h4("Partida com Autotransformador")
    st.markdown(
        "Um autotransformador com tap $k$ ($0 < k < 1$) aplica $k\\,V_l$ ao motor durante "
        "a partida. A corrente absorvida da rede é reduzida pelo fator $k^2$:"
    )
    _eq(r"I_{rede} = k^2\,I_{part,\,V_{nom}}, \quad T_{part} = k^2\,T_{part,\,V_{nom}}")
    st.markdown(
        "Em $t_2$ ocorre a comutação para tensão plena. O simulador permite escolher o tap "
        "$k$ via slider e observar o compromisso entre redução de corrente e torque de partida disponível."
    )
    st.markdown(
        "- **Observar:** corrente de rede reduzida na partida, pico na comutação, torque de partida limitado.\n"
        "- **Vantagem sobre Y-D:** tap ajustável permite otimizar o compromisso corrente × torque."
    )

    st.write("")
    _h4("Soft-Starter — Rampa de Tensão")
    st.markdown(
        "Um conversor eletrônico aplica uma tensão crescente de $V_0 = k\\,V_l$ até $V_l$ "
        "ao longo da rampa $[t_2,\\, t_{pico}]$:"
    )
    _eq(r"V(t) = V_0 + (V_l - V_0)\,\frac{t - t_2}{t_{pico} - t_2}, \quad t_2 \leq t \leq t_{pico}")
    st.markdown(
        "A corrente e o torque crescem suavemente, eliminando o pico abrupto das partidas "
        "comutadas. Em $t > t_{pico}$ o motor opera em plena tensão; a carga $T_l$ é "
        "aplicada em $t_{carga}$."
    )
    st.markdown(
        "- **Observar:** ausência de pico de corrente, aceleração mais lenta, corrente quase constante durante a rampa.\n"
        "- **Risco:** rampa muito longa eleva perdas Joule no rotor durante a aceleração ($P_{cu,2} = s\\,P_{ag}$)."
    )

    st.divider()
    st.markdown("### Ensaios de Carga")

    _h4("Aplicação de Carga — Partida em Vazio")
    st.markdown(
        "O motor parte em vazio ($T_l = 0$) e, em $t_{carga}$, recebe o torque resistente "
        "$T_l$ em degrau. É o ensaio de referência para medir o **afundamento de "
        "velocidade** $\\Delta n$ e o aumento de corrente ao conectar a carga:"
    )
    _eq(r"\Delta n = n_{vazio} - n_{carga} = n_s\,(s_{carga} - s_{vazio})")
    st.markdown(
        "O percentual de carga pode ser ajustado: 100% = carga nominal, acima = sobrecarga, "
        "abaixo = carga parcial."
    )
    st.markdown(
        "- **Observar:** afundamento de velocidade, aumento de corrente RMS, novo ponto de regime.\n"
        "- **Risco:** $T_l > T_{max}$ provoca stall — o motor não retorna ao regime estável."
    )

    st.write("")
    _h4("Pulso de Carga — Aplica e Retira")
    st.markdown(
        "A carga é aplicada em $t_{on}$ e retirada em $t_{off}$, simulando uma perturbação "
        "temporária (ex: impacto de carga em prensas, compressores alternativos). "
        "A equação de movimento governa a resposta:"
    )
    _eq(r"\frac{d\omega_r}{dt} = \frac{p}{2J}(T_e - T_l) - \frac{B}{J}\,\omega_r")
    st.markdown(
        "Após $t_{off}$, o motor retorna ao regime de vazio com transitório de velocidade "
        "e corrente observável."
    )
    st.markdown(
        "- **Observar:** queda e recuperação de velocidade, picos de corrente nos dois instantes de comutação.\n"
        "- **Parâmetro chave:** $J$ — inércia elevada amorece a queda de velocidade; baixa inércia amplifica o transitório."
    )

    st.divider()
    st.markdown("### Operação como Gerador")

    _h4("Operação como Gerador de Indução")
    st.markdown(
        "O motor parte normalmente ($0 < t < t_2$, $s > 0$). Em $t_2$, uma turbina "
        "ou fonte motriz externa aplica torque mecânico $T_{mec}$ no sentido do movimento, "
        "acelerando o rotor **acima de $n_s$**. O escorregamento torna-se negativo "
        "e o sentido do fluxo de potência no entreferro inverte:"
    )
    _eq(r"s < 0 \;\Rightarrow\; P_{ag} = T_e\,\omega_s < 0 \;\Rightarrow\; \text{potência entregue à rede}")
    st.markdown(
        "A tensão de rede permanece constante — o gerador de indução necessita da rede "
        "para excitar o campo magnético (não é autônomo). A potência gerada é:"
    )
    _eq(r"P_{out} = |P_{ag}| - P_{cu,s} - P_{fe} - P_{rot}")
    st.markdown(
        "- **Observar:** velocidade acima de $n_s$, torque eletromagnético negativo, escorregamento negativo nos KPIs.\n"
        "- **Aplicações:** geração eólica de pequeno porte, freio regenerativo em acionamentos de velocidade variável."
    )

    st.divider()
    st.markdown("### Desligamento")

    _h4("Desligamento — Corte de Alimentação")
    st.markdown(
        "Em $t_{des}$, a tensão de alimentação é zerada, simulando abertura de contator "
        "ou falta total de rede. O campo girante desaparece em microssegundos (transitório "
        "elétrico); a velocidade decai dominada pela constante mecânica:"
    )
    _eq(r"\tau_m = \frac{J}{B} \quad \Rightarrow \quad \omega_r(t) \approx \omega_r(t_{des})\,e^{-(t-t_{des})/\tau_m}")
    st.markdown(
        "A carga mecânica $T_l$ permanece ativa, acelerando a parada. Se $B \\approx 0$ "
        "e $T_l = 0$, o rotor para apenas por atrito — tempo longo."
    )
    st.markdown(
        "- **Observar:** extinção abrupta da corrente, decaimento exponencial de velocidade, tempo de parada.\n"
        "- **t_max recomendado:** $t_{des} + 5\\,\\tau_m$ para capturar a parada completa."
    )

    st.divider()
    st.markdown("### Desequilíbrio de Tensão e Falta de Fase")

    _h4("Desequilíbrio de Tensão — Componentes Simétricas")
    st.markdown(
        "Em condições ideais, as três tensões de fase têm a mesma amplitude e estão "
        "defasadas de 120°. Qualquer assimetria é decomposta pelo **Teorema de "
        "Fortescue** em três sequências:"
    )
    _eq(r"\bar{V}_a = \bar{V}_{a1} + \bar{V}_{a2} + \bar{V}_{a0}")
    st.markdown(
        "Apenas a **sequência positiva** $\\bar{V}_1$ produz campo girante "
        "no sentido do motor. A **sequência negativa** $\\bar{V}_2$ cria um "
        "campo girante reverso, gerando torque de *frenagem*:"
    )
    _eq(r"T_e = T_{e,1}(s) \;+\; T_{e,2}(2-s)")
    st.markdown(
        "O resultado prático é redução de torque, aumento de corrente e aquecimento "
        "assimétrico das fases — a fase com menor tensão tende a ter maior corrente."
    )
    st.markdown("O **Fator de Desequilíbrio de Tensão (VUF)** padronizado pela NEMA é:")
    _eq(r"\text{VUF} = \frac{|\bar{V}_2|}{|\bar{V}_1|} \times 100\%")
    st.markdown(
        "- VUF $= 1\\%$ pode causar até $6$–$10\\%$ de elevação de corrente e $10\\%$ de redução de torque máximo.\n"
        "- NEMA MG-1: motores devem operar com VUF $\\leq 1\\%$; acima de $5\\%$ a operação deve ser interrompida."
    )
    st.markdown("No simulador, os desvios fracionais por fase são aplicados como:")
    _eq(r"V_a = \sqrt{\tfrac{2}{3}}\,V_l\,(1 + \delta_a)\sin(\omega_e t)")
    _eq(r"V_b = \sqrt{\tfrac{2}{3}}\,V_l\,(1 + \delta_b)\sin\!\left(\omega_e t - \tfrac{2\pi}{3}\right)")
    _eq(r"V_c = \sqrt{\tfrac{2}{3}}\,V_l\,(1 + \delta_c)\sin\!\left(\omega_e t + \tfrac{2\pi}{3}\right)")
    st.markdown("onde $\\delta_a,\\,\\delta_b,\\,\\delta_c \\in [-0{,}30,\\;+0{,}30]$ são os desvios configurados nos sliders.")

    st.write("")
    _h4("Falta de Fase — Operação Bifásica")
    st.markdown(
        "A falta de fase ocorre quando um dos condutores é interrompido — por ruptura de fusível, "
        "falha de contator ou cabo rompido. A tensão da fase afetada é forçada a zero, "
        "impondo o máximo desequilíbrio possível na alimentação:"
    )
    _eq(r"V_x = 0 \;\Rightarrow\; |\bar{V}_2| \approx |\bar{V}_1|")
    st.markdown(
        "Com uma fase suprimida, a máquina passa a operar em regime bifásico. "
        "O campo girante decompõe-se em duas componentes de mesma amplitude — "
        "sequência positiva (enfraquecida) e sequência negativa (oposta ao movimento) — "
        "produzendo torque pulsante e aquecimento assimétrico. "
        "As consequências operacionais são:"
    )
    st.markdown(
        "- A corrente nas duas fases ativas eleva-se para aproximadamente $\\sqrt{3}$ vezes o valor nominal.\n"
        "- O torque máximo disponível reduz-se a cerca de $50\\%$ do valor nominal; a partida com carga pode ser inviabilizada.\n"
        "- Surge uma componente de torque pulsante à frequência $2f$, gerando vibração e ruído audível.\n"
        "- O aquecimento do rotor e dos enrolamentos é severo — a proteção térmica deve atuar em poucos segundos."
    )
    st.markdown(
        "A relação entre as perdas no rotor em operação bifásica e nominal, "
        "a torque equivalente, é dada por:"
    )
    _eq(r"P_{cu,2}^{\,\text{bif}} \approx 2\, P_{cu,2}^{\,\text{nom}}")
    st.markdown(
        "No simulador, o *toggle* de falta de fase força $V_x = 0$ a partir de "
        "$t_{deseq}$. Recomenda-se limitar $t_{max}$ a poucos ciclos após o evento, "
        "pois o modelo não inclui proteção térmica."
    )
    _div_warn(
        "A simulação simultânea de duas ou mais fases em falta por longos períodos "
        "deve ser evitada: sem proteção térmica no modelo, as correntes tendem a crescer "
        "sem limite."
    )

    st.write("")
    _h4("Instante de Início do Desequilíbrio — $t_{deseq}$")
    st.markdown(
        "O parâmetro $t_{deseq}$ separa dois regimes na simulação:"
    )
    st.markdown(
        "- $0 \\leq t < t_{deseq}$: rede balanceada — motor parte e acelera normalmente.\n"
        "- $t \\geq t_{deseq}$: desequilíbrio e/ou falta de fase entra em ação."
    )
    st.markdown(
        "Isso permite estudar a **resposta transitória ao surgimento da falta**: "
        "observe a perturbação de velocidade, o pico de corrente e o novo ponto de regime "
        "(ou divergência) imediatamente após $t_{deseq}$."
    )
    _eq(r"V_x(t) = \begin{cases} V_{x,\,nom}(t) & t < t_{deseq} \\ V_{x,\,deseq}(t) & t \geq t_{deseq} \end{cases}")
    st.markdown(
        "Usando $t_{deseq} = 0$, a assimetria está presente desde a partida — "
        "útil para estudar a **partida com rede já desequilibrada**."
    )


# ─────────────────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def render_theory_tab() -> None:
    st.markdown(
        "Fundamentos físicos da máquina de indução trifásica — "
        "selecione uma aba para explorar o tema desejado."
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "1 - Modelagem e Circuitos",
        "2 - Dinâmica e Torque",
        "3 - Balanço Energético",
        "4 - Sensibilidade de Parâmetros",
        "5 - Configurações e Alertas",
        "6 - Dinâmica de Operação",
        "7 - Experimentos e Perturbações",
    ])

    with tab1:
        st.markdown("## Modelagem e Circuitos Equivalentes")
        _render_tab_circuitos()

    with tab2:
        st.markdown("## Comportamento Dinâmico e Torque")
        _render_tab_dinamica()

    with tab3:
        st.markdown("## Balanço Energético e Fluxo de Potência")
        _render_tab_potencia()

    with tab4:
        st.markdown("## Guia de Sensibilidade de Parâmetros")
        _render_tab_sensibilidade()

    with tab5:
        st.markdown("## Configurações de Simulação e Alertas")
        _render_tab_config()

    with tab6:
        st.markdown("## Dinâmica de Operação")
        _render_tab_dinamica_operacao()

    with tab7:
        st.markdown("## Experimentos e Perturbações de Rede")
        _render_tab_experimentos()
