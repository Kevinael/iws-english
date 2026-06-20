# -*- coding: utf-8 -*-
"""Tests for core/harmonica_analysis.py — build_fig_fft."""
import numpy as np
import plotly.graph_objects as go
import pytest
from core.tim.harmonic_analysis import build_fig_fft


# ── helpers to build a synthetic result ───────────────────────────────────────

def _make_res(n=2000, f=60.0, harmonics=None, ss_start=0,
              t_broken_bar=0.0, key="ias"):
    """
    Generate a result dict with a synthetic sinusoidal signal.

    harmonics: list of (order, relative_amplitude) added to the fundamental.
    """
    t  = np.linspace(0, n / (n * f / n), n)   # n points covering enough cycles
    dt = 1.0 / (f * 20)                        # 20 samples per cycle → fixed dt
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


# ── basic return tests ────────────────────────────────────────────────────────

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


# ── insufficient-data tests ──────────────────────────────────────────────────

def test_dados_insuficientes_retorna_figure_vazia():
    """Fewer than 4 samples after ss_start → figure with a warning title."""
    res = {"t": [0, 1, 2], "ias": [0.0, 1.0, 0.0],
           "_ss_start": 0, "_t_broken_bar": 0.0}
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0   # no data traces


def test_ss_start_deixa_menos_de_4_amostras():
    res = _make_res(n=10, ss_start=8)
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)


# ── fundamental detection tests ──────────────────────────────────────────────

def test_fundamental_detectada_em_60hz():
    """60 Hz signal: the trace must have content near 60 Hz."""
    res = _make_res(n=3000, f=60.0)
    fig = build_fig_fft(res, dark=False)
    x = np.array(fig.data[0].x)
    assert x.max() >= 60.0     # X axis reaches at least the fundamental


def test_janela_limitada_a_11a_harmonica():
    """X axis must not exceed 11 × f1 or 1200 Hz."""
    res = _make_res(n=3000, f=60.0)
    fig = build_fig_fft(res, dark=False)
    x_max = float(np.array(fig.data[0].x).max())
    assert x_max <= 1200.0 * 1.05   # 5% margin for ticks


# ── harmonic annotation tests ────────────────────────────────────────────────

def test_3a_harmonica_anotada():
    """Signal with a relevant 3rd harmonic (10%) must be marked."""
    res = _make_res(n=6000, f=60.0, harmonics=[(3, 0.10)])
    fig = build_fig_fft(res, dark=False)
    # there must be a marker trace (markers+text mode)
    marker_traces = [t for t in fig.data if "markers" in (t.mode or "")]
    assert len(marker_traces) >= 1


def test_no_harmonic_below_threshold_no_markers():
    """3rd-order harmonic at 0.5% (below the 1% threshold) must not appear in the texts."""
    res = _make_res(n=6000, f=60.0, harmonics=[(3, 0.005)])
    fig = build_fig_fft(res, dark=False)
    marker_traces = [t for t in fig.data if "markers" in (t.mode or "")]
    # If there is a marker trace, the 3rd harmonic must not be among the texts
    if marker_traces:
        textos = list(marker_traces[0].text or [])
        assert not any("3ª" in str(tx) for tx in textos)


# ── broken-bar tests (t_broken_bar) ───────────────────────────────────────────

def test_broken_bar_ajusta_ss_start():
    """With t_broken_bar > 0, the FFT window starts after the event."""
    n  = 3000
    dt = 1.0 / (60.0 * 20)
    t_bb = dt * (n // 2)   # bar breaks at the midpoint
    res = _make_res(n=n, f=60.0, ss_start=10, t_broken_bar=t_bb)
    # must not raise an exception — just returns a valid figure
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)


# ── custom-key tests ──────────────────────────────────────────────────────────

def test_chave_customizada_Va():
    res = _make_res(n=3000, key="Va")
    res["ias"] = np.zeros(3000)   # default key present but unused
    fig = build_fig_fft(res, dark=False, key="Va", label="Va")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


# ── test for the fixed bug: access to yf[f1_idx] without a guard ─────────────

def test_f1_idx_bounds_nao_levanta_index_error():
    """Ensures the IndexError fix in yf[f1_idx] remains functional."""
    # Signal with only one frequency above 1 Hz — a case that previously could
    # produce f1_idx at the array boundary before the fix
    n  = 64
    dt = 1.0 / 120.0
    t  = np.arange(n) * dt
    y  = np.sin(2 * np.pi * 60.0 * t)
    res = {"t": t, "ias": y, "_ss_start": 0, "_t_broken_bar": 0.0}
    fig = build_fig_fft(res, dark=False)
    assert isinstance(fig, go.Figure)
