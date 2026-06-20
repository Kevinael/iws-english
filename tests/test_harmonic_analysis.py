# -*- coding: utf-8 -*-
"""Testes para core/harmonica_analysis.py — build_fig_fft."""
import numpy as np
import plotly.graph_objects as go
import pytest
from core.tim.harmonic_analysis import build_fig_fft


# ── helpers para construir resultado sintético ────────────────────────────────

def _make_res(n=2000, f=60.0, harmonics=None, ss_start=0,
              t_broken_bar=0.0, key="ias"):
    """
    Gera dict de resultado com sinal senoidal sintético.

    harmonics: lista de (ordem, amplitude_relativa) adicionada à fundamental.
    """
    t  = np.linspace(0, n / (n * f / n), n)   # n pontos cobrindo ciclos suficientes
    dt = 1.0 / (f * 20)                        # 20 amostras por ciclo → dt fixo
    t  = np.arange(n) * dt
    w  = 2.0 * np.pi * f
    y  = np.sin(w * t)
    if harmonics:
        for order, amp in harmonics:
            y += amp * np.sin(order * w * t)

    res = {
        "t":           t,
        key:           y,
        "_ss_start":   ss_start,
        "_t_broken_bar": t_broken_bar,
    }
    return res


# ── testes de retorno básico ──────────────────────────────────────────────────

def test_retorna_figure():
    res = _make_res()
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)


def test_retorna_figure_dark():
    res = _make_res()
    fig = build_fig_fft(res, dark=True)
    assert isinstance(fig, go.Figure)


def test_tem_ao_menos_um_trace():
    res = _make_res()
    fig = build_fig_fft(res, dark=False)
    assert len(fig.data) >= 1


# ── testes de dados insuficientes ────────────────────────────────────────────

def test_dados_insuficientes_retorna_figure_vazia():
    """Menos de 4 amostras após ss_start → figura com título de aviso."""
    res = {"t": [0, 1, 2], "ias": [0.0, 1.0, 0.0],
           "_ss_start": 0, "_t_broken_bar": 0.0}
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0   # sem traces de dados


def test_ss_start_deixa_menos_de_4_amostras():
    res = _make_res(n=10, ss_start=8)
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)


# ── testes de detecção da fundamental ────────────────────────────────────────

def test_fundamental_detectada_em_60hz():
    """Sinal a 60 Hz: o trace deve ter conteúdo próximo de 60 Hz."""
    res = _make_res(n=3000, f=60.0)
    fig = build_fig_fft(res, dark=False)
    x = np.array(fig.data[0].x)
    assert x.max() >= 60.0     # eixo X alcança pelo menos a fundamental


def test_janela_limitada_a_11a_harmonica():
    """Eixo X não deve exceder 11 × f1 ou 1200 Hz."""
    res = _make_res(n=3000, f=60.0)
    fig = build_fig_fft(res, dark=False)
    x_max = float(np.array(fig.data[0].x).max())
    assert x_max <= 1200.0 * 1.05   # margem de 5% para ticks


# ── testes de anotação de harmônicas ─────────────────────────────────────────

def test_3a_harmonica_anotada():
    """Sinal com 3ª harmônica relevante (10%) deve ser marcada."""
    res = _make_res(n=6000, f=60.0, harmonics=[(3, 0.10)])
    fig = build_fig_fft(res, dark=False)
    # deve haver trace de marcadores (modo markers+text)
    marker_traces = [t for t in fig.data if "markers" in (t.mode or "")]
    assert len(marker_traces) >= 1


def test_no_harmonic_below_threshold_no_markers():
    """Harmônica de 3ª ordem com 0.5% (abaixo do limiar de 1%) não deve aparecer nos textos."""
    res = _make_res(n=6000, f=60.0, harmonics=[(3, 0.005)])
    fig = build_fig_fft(res, dark=False)
    marker_traces = [t for t in fig.data if "markers" in (t.mode or "")]
    # Se houver trace de marcadores, a 3ª harmônica não deve estar entre os textos
    if marker_traces:
        textos = list(marker_traces[0].text or [])
        assert not any("3ª" in str(tx) for tx in textos)


# ── testes de barra quebrada (t_broken_bar) ───────────────────────────────────

def test_broken_bar_ajusta_ss_start():
    """Com t_broken_bar > 0, a janela FFT começa após o evento."""
    n  = 3000
    dt = 1.0 / (60.0 * 20)
    t_bb = dt * (n // 2)   # barra quebra na metade
    res = _make_res(n=n, f=60.0, ss_start=10, t_broken_bar=t_bb)
    # não deve levantar exceção — apenas retorna figure válida
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)


# ── testes de chave customizada ───────────────────────────────────────────────

def test_chave_customizada_Va():
    res = _make_res(n=3000, key="Va")
    res["ias"] = np.zeros(3000)   # chave padrão presente mas não usada
    fig = build_fig_fft(res, dark=False, key="Va", label="Va")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


# ── teste do bug corrigido: acesso a yf[f1_idx] sem guarda ───────────────────

def test_f1_idx_bounds_nao_levanta_index_error():
    """Garante que a correção do IndexError em yf[f1_idx] permanece funcional."""
    # Sinal com apenas uma frequência acima de 1 Hz — caso que antes podia
    # gerar f1_idx no limite do array antes da correção
    n  = 64
    dt = 1.0 / 120.0
    t  = np.arange(n) * dt
    y  = np.sin(2 * np.pi * 60.0 * t)
    res = {"t": t, "ias": y, "_ss_start": 0, "_t_broken_bar": 0.0}
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)
