# -*- coding: utf-8 -*-
"""Aba Teoria MCC — 7 subabas pedagógicas.

Exporta:
    render_theory_dc_tab — chamada em IWS_UI.py quando selected_machine == "dc"
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_PNG_DIR = Path(__file__).parent.parent / "docs" / "bases para simulação" / "cc" / "imgs"


def _png(name: str):
    p = _PNG_DIR / name
    return str(p) if p.exists() else None


def _show_png(name: str, caption: str = "") -> None:
    path = _png(name)
    if path:
        st.image(path, caption=caption, use_container_width=True)
    else:
        st.info(f"Imagem não encontrada: `{name}` — execute `mcc_desenhos.py` para gerar.")


def render_theory_dc_tab() -> None:
    """Renderiza as 7 subabas da aba Teoria MCC."""
    tabs = st.tabs([
        "1 · Modelagem e Circuitos",
        "2 · Dinâmica e Torque",
        "3 · Padrões de Corrente",
        "4 · Controle de Velocidade",
        "5 · Operação como Gerador",
        "6 · Estimador de Parâmetros",
        "7 · Manual de Uso",
    ])

    # ── Subaba 1: Modelagem e Circuitos ──────────────────────────────────
    with tabs[0]:
        st.markdown("## Modelagem da MCC — Circuitos Equivalentes")
        st.markdown(r"""
A máquina de corrente contínua é modelada por três equações diferenciais ordinárias:

**Circuito de armadura:**
$$\frac{di_a}{dt} = \frac{1}{L_a}\left(V_a - R_a i_a - k_b \Phi i_a\right)$$

**Circuito de campo (excitação separada/shunt):**
$$\frac{di_{fd}}{dt} = \frac{1}{L_f}\left(V_f - R_f i_{fd}\right)$$

**Equação mecânica:**
$$\frac{d\omega_m}{dt} = \frac{1}{J}\left(T_e - T_l - B\omega_m\right)$$

onde $T_e = k_b \, i_{fd} \, i_a$ e $E_a = k_b \, i_{fd} \, \omega_m$.
""")

        cols = st.columns(3)
        with cols[0]:
            _show_png("separate_motor.png", "Excitação Separada — Motor")
        with cols[1]:
            _show_png("shunt_motor.png", "Shunt — Motor")
        with cols[2]:
            _show_png("serie_motor.png", "Série — Motor")

        cols2 = st.columns(2)
        with cols2[0]:
            _show_png("separate_gerador.png", "Excitação Separada — Gerador")
        with cols2[1]:
            _show_png("shunt_gerador.png", "Shunt — Gerador")

        try:
            from ui.theory_dc_interactive import render_diagrama_blocos_mcc
            render_diagrama_blocos_mcc()
        except Exception:
            pass

    # ── Subaba 2: Dinâmica e Torque ★ ────────────────────────────────────
    with tabs[1]:
        st.markdown("## Dinâmica e Curvas Conjugado × Velocidade")
        st.markdown(r"""
O diferencial pedagógico da MCC é como cada tipo de excitação modifica o comportamento dinâmico:

| Excitação | Curva T×ωm | Corrente de partida |
|-----------|-----------|---------------------|
| **Série** | Hiperbólica ($T \propto i_a^2$) | Pico elevado |
| **Shunt** | Quasi-linear | Pico moderado |
| **Separada** | Ajustável por $V_f$ | Controlável |

**Enfraquecimento de campo (excitação separada):**
Reduzindo $V_f$ → $i_{fd}$ decresce → $E_a = k_b i_{fd} \omega_m$ reduz → $i_a$ aumenta → motor acelera além da velocidade base.
""")
        _show_png("wm_x_T.png", "Curvas T×ωm para as três excitações")

        try:
            from ui.theory_dc_interactive import render_curvas_comparativas_excitacao
            render_curvas_comparativas_excitacao()
        except Exception:
            pass

    # ── Subaba 3: Padrões de Corrente ★ ─────────────────────────────────
    with tabs[2]:
        st.markdown("## Padrões de Corrente de Armadura")
        st.markdown(r"""
A corrente de armadura $i_a(t)$ reflete diretamente as características de cada configuração:

- **Série:** pico de partida muito alto; estabelecimento mais lento
- **Shunt:** transitório suave; $i_{fd}$ atinge regime antes de $i_a$
- **Separada:** controle independente de $\Phi$ e $i_a$

Use a ferramenta interativa abaixo para comparar as formas de onda.
""")
        try:
            from ui.theory_dc_interactive import render_padrao_corrente_dc
            render_padrao_corrente_dc()
        except Exception:
            st.info("Componente interativo indisponível.")

    # ── Subaba 4: Controle de Velocidade ─────────────────────────────────
    with tabs[3]:
        st.markdown("## Controle de Velocidade")
        st.markdown(r"""
Dois métodos principais:

**1. Controle de tensão de armadura** ($V_a$):
$$\omega_m = \frac{V_a - R_a i_a}{k_b \Phi}$$
Válido para $\omega_m \leq \omega_{base}$.

**2. Enfraquecimento de campo** (redução de $V_f$):
$$\omega_m \propto \frac{1}{i_{fd}}$$
Válido para $\omega_m > \omega_{base}$ — $T_e$ reduz, potência constante.
""")
        try:
            from ui.theory_dc_interactive import render_controle_velocidade_dc
            render_controle_velocidade_dc()
        except Exception:
            st.info("Componente interativo indisponível.")

    # ── Subaba 5: Operação como Gerador ──────────────────────────────────
    with tabs[4]:
        st.markdown("## Operação como Gerador de CC")
        st.markdown(r"""
Quando o torque mecânico externo impõe $\omega_m$ e a máquina não recebe $V_a$ (ou $V_a = 0$):

$$E_a = k_b i_{fd} \omega_m \quad \Rightarrow \quad i_a = \frac{E_a}{R_a + R_l}$$

A tensão de terminal é:
$$V_t = R_l \, i_a$$

**Gerador shunt:** a corrente de campo é alimentada pela própria tensão gerada — requer autoexcitação via remanência magnética.

**Gerador separado:** $V_f$ é fonte independente — não depende de $V_t$.
""")
        _show_png("gerador_comparativo.png", "Curvas características Vt×Ia")

    # ── Subaba 6: Estimador de Parâmetros ────────────────────────────────
    with tabs[5]:
        st.markdown("## Estimador de Parâmetros DC")
        st.markdown(r"""
**Ensaio de resistência CC:** $R_a = V_{dc} / I_{dc}$

**Ensaio a vazio (sem carga):** $E_a = V_a - R_a I_{a,nl}$, $k_b = E_a / (i_{fd} \omega_{m,nl})$

**Curva de magnetização:** $\Phi$ vs $i_{fd}$ — relaciona fluxo com corrente de campo.
""")
        _show_png("curva_magnetizacao_simples_pb.png", "Curva de Magnetização")

        try:
            from ui.theory_dc_interactive import render_estimador_dc
            render_estimador_dc()
        except Exception:
            st.info("Componente interativo indisponível.")

    # ── Subaba 7: Manual de Uso ───────────────────────────────────────────
    with tabs[6]:
        st.markdown("## Manual de Uso — Simulador MCC")
        st.markdown(r"""
### Fluxo típico de simulação

1. **Selecione a configuração** (Separada Motor, Shunt Motor, Série Motor, Separada Gerador, Shunt Gerador)
2. **Ajuste os parâmetros** ou carregue um **preset** de fábrica
3. **Escolha o modo de operação** (DOL, Resistência, Plugging, Pulso, Campo Fraco, Gerador)
4. **Configure o experimento** (tempo, parâmetros específicos do modo)
5. **Selecione grandezas** a plotar ($i_a$, $\omega_m$, $T_e$, $E_a$, $V_t$, $n$)
6. Clique em **Executar Simulação**
7. Navegue pelas 4 sub-abas de resultados

### Presets disponíveis

| Preset | Fonte | Destaque |
|--------|-------|----------|
| Motor Separado (dcmei) | Scilab `dcmei.sce` | Parâmetros Okoro 2008 |
| Motor Shunt (dcmp)     | Scilab `dcmp.sce`  | Excitação em paralelo |
| Motor Série (dcms)     | Scilab `dcms.sce`  | Curva hiperbólica     |
| Gerador Separado       | Scilab `dgmei.sce` | Carga resistiva       |
| Gerador Shunt          | Scilab `dcgp.sce`  | Autoexcitação         |

### Comparação entre excitações

Use **Salvar como Referência** após simular cada excitação. Sobrepõe até 5 curvas na mesma figura.

### Grandezas do resultado

| Símbolo | Descrição |
|---------|-----------|
| $i_a$   | Corrente de armadura |
| $i_{fd}$| Corrente de campo |
| $\omega_m$ | Velocidade angular (rad/s) |
| $n$     | Velocidade (RPM) |
| $T_e$   | Conjugado eletromagnético |
| $E_a$   | Força eletromotriz de retorno |
| $V_t$   | Tensão de terminal |
""")
