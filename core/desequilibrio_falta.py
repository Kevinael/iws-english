# -*- coding: utf-8 -*-
"""
desequilibrio_falta.py
======================
Módulo reservado para simulação de desequilíbrio de tensão e falta de fase.
Não é importado nem utilizado pelo restante da aplicação.

Para reativar: importe render_desequilibrio_ui em EMS_UI.py e adicione
deseq_a, deseq_b, deseq_c, falta_fase_a, falta_fase_b, falta_fase_c
como parâmetros de run_simulation em EMS_PY.py.
"""
from __future__ import annotations
import math
import numpy as np


# ── Geração de tensões com desequilíbrio/falta ──────────────────────────────

def abc_voltages_deseq(t, Vl: float, f: float,
                       deseq_a: float = 0.0,
                       deseq_b: float = 0.0,
                       deseq_c: float = 0.0,
                       falta_fase_a: bool = False,
                       falta_fase_b: bool = False,
                       falta_fase_c: bool = False,
                       df_a: float = 0.0,
                       df_b: float = 0.0,
                       df_c: float = 0.0):
    """Gera tensões abc com desequilíbrio e/ou falta de fase em qualquer fase.

    deseq_a / deseq_b / deseq_c : desvio fracional em Vl (ex: 0.1 = +10%, -0.1 = -10%).
    falta_fase_a/b/c             : se True, força a tensão da fase a zero.
    df_a / df_b / df_c           : desvio de frequência por fase em Hz (0 = nominal).
    Aceita t escalar ou np.ndarray; retorna o mesmo tipo.
    """
    scalar = np.ndim(t) == 0
    t_arr  = np.atleast_1d(np.asarray(t, dtype=float))
    zero   = np.zeros_like(t_arr)
    k      = np.sqrt(2.0 / 3.0)

    tetae_a = 2.0 * np.pi * (f + df_a) * t_arr
    tetae_b = 2.0 * np.pi * (f + df_b) * t_arr
    tetae_c = 2.0 * np.pi * (f + df_c) * t_arr

    Va = zero if falta_fase_a else k * Vl * (1.0 + deseq_a) * np.sin(tetae_a)
    Vb = zero if falta_fase_b else k * Vl * (1.0 + deseq_b) * np.sin(tetae_b - 2.0 * np.pi / 3.0)
    Vc = zero if falta_fase_c else k * Vl * (1.0 + deseq_c) * np.sin(tetae_c + 2.0 * np.pi / 3.0)

    if scalar:
        return float(Va[0]), float(Vb[0]), float(Vc[0])
    return Va, Vb, Vc


# ── Modelo de Barra Quebrada ─────────────────────────────────────────────────

def make_broken_bar_rr_fn(Rr_nominal: float, severity: float, wb: float):
    """Retorna função Rr(t, s) que modula a resistência do rotor ao dobro da freq. de escorregamento.

    Modelo: Rr(t) = Rr0 · (1 + α · cos(2·s·ωb·t))

    Args:
        Rr_nominal: resistência nominal do rotor (Ω).
        severity:   α — amplitude da oscilação (0 = saudável, 0.1 = 10% de quebra).
        wb:         frequência angular base (rad/s).

    Returns:
        Callable[[float, float], float] — (t, slip) → Rr efetivo.
        Se severity == 0, retorna None (sinal para desativar o modelo).
    """
    if severity == 0.0:
        return None

    def _rr_fn(theta_slip: float) -> float:
        return Rr_nominal * (1.0 + severity * math.cos(2.0 * theta_slip))

    return _rr_fn


# ── Bloco de UI ─────────────────────────────────────────────────────────────

def render_desequilibrio_ui(config: dict, tmax: float = 2.0) -> None:
    """Renderiza o expander de desequilíbrio de tensão / falta de fase.

    Preenche config com as chaves:
      deseq_a, deseq_b, deseq_c,
      falta_fase_a, falta_fase_b, falta_fase_c,
      t_deseq.
    Deve ser chamado dentro do bloco de configuração do experimento em EMS_UI.py.
    """
    import streamlit as st
    st.write("")
    with st.expander("Desequilíbrio de Tensão / Falta de Fase", expanded=False):
        st.info("Simula assimetria na rede. Útil para estudar diagnóstico de falhas e proteção de motores.")

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("**Fase A**")
            deseq_a = st.slider(
                "Desvio amplitude A (%)", min_value=-30, max_value=30, value=0, step=1,
                help="Ex: +10 → Va = 1.1 × Vnominal", key="deseq_a"
            ) / 100.0
            df_a = float(st.slider(
                "Desvio frequência A (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Desvio de frequência em Va. 0 = nominal.", key="df_a"
            ))
            falta_a = st.toggle("Falta de Fase A (Va = 0)", value=False, key="falta_a")
            if falta_a:
                st.warning("Falta na fase A — correntes muito elevadas.")

        with col_b:
            st.markdown("**Fase B**")
            deseq_b = st.slider(
                "Desvio amplitude B (%)", min_value=-30, max_value=30, value=0, step=1,
                help="Ex: +10 → Vb = 1.1 × Vnominal", key="deseq_b"
            ) / 100.0
            df_b = float(st.slider(
                "Desvio frequência B (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Desvio de frequência em Vb. 0 = nominal.", key="df_b"
            ))
            falta_b = st.toggle("Falta de Fase B (Vb = 0)", value=False, key="falta_b")
            if falta_b:
                st.warning("Falta na fase B — correntes muito elevadas.")

        with col_c:
            st.markdown("**Fase C**")
            deseq_c = st.slider(
                "Desvio amplitude C (%)", min_value=-30, max_value=30, value=0, step=1,
                help="Ex: -10 → Vc = 0.9 × Vnominal", key="deseq_c"
            ) / 100.0
            df_c = float(st.slider(
                "Desvio frequência C (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Desvio de frequência em Vc. 0 = nominal.", key="df_c"
            ))
            falta_c = st.toggle("Falta de Fase C (Vc = 0)", value=False, key="falta_c")
            if falta_c:
                st.warning("Falta na fase C — correntes muito elevadas.")

        faltas_ativas = sum([falta_a, falta_b, falta_c])
        if faltas_ativas >= 2:
            st.error("Atenção: duas ou mais fases em falta — operação monofásica ou sem tensão. "
                     "Reduza o tempo de simulação.")
        elif faltas_ativas == 1:
            st.warning("Uma fase em falta: operação bifásica — correntes muito elevadas. "
                       "Reduza o tempo de simulação.")

        _tmax_deseq = float(tmax) if tmax > 0.0 else None
        _val_deseq  = min(1.0, float(tmax) - 0.1) if (tmax > 0.0 and tmax <= 1.0) else 1.0
        t_deseq = st.number_input(
            "Instante de início do desequilíbrio (s)",
            min_value=0.0, max_value=_tmax_deseq, value=_val_deseq, step=0.1, format="%.2f",
            help="O desequilíbrio começa a atuar neste instante. Use 0 para aplicar desde o início.",
        )

        any_active = any([deseq_a, deseq_b, deseq_c, falta_a, falta_b, falta_c])
        if any_active and t_deseq > 0.0:
            st.caption(f"Rede balanceada até {t_deseq:.2f} s — desequilíbrio/falta aplicado a partir desse instante.")

        config["deseq_a"]      = deseq_a
        config["deseq_b"]      = deseq_b
        config["deseq_c"]      = deseq_c
        config["falta_fase_a"] = falta_a
        config["falta_fase_b"] = falta_b
        config["falta_fase_c"] = falta_c
        config["t_deseq"]      = t_deseq
        config["df_a"]         = df_a
        config["df_b"]         = df_b
        config["df_c"]         = df_c
