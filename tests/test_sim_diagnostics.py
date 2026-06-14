# -*- coding: utf-8 -*-
"""Testes para core/sim_diagnostics.py — Insight e generate_insights."""
import numpy as np
import pytest
from core.mit_diagnostics import (
    Insight,
    generate_insights,
    _is_steady_state_reached,
    _sort_insights,
)


# ── fixture de MachineParams mínimo (não depende de simulação completa) ───────

class _MP:
    """Substituto mínimo de MachineParams para os testes de diagnóstico."""
    def __init__(self):
        self.wb  = 2 * np.pi * 60
        self.p   = 4
        self.B   = 0.005
        self.J   = 0.089


@pytest.fixture
def mp():
    return _MP()


# ── resultado sintético em regime permanente ──────────────────────────────────

def _make_res(n=500, s_ss=0.03, n_sync=1800.0, Te_ss=12.0, steady=True):
    """Cria dict de resultado compatível com generate_insights."""
    t     = np.linspace(0, 3.0, n)
    ws    = n_sync * 2 * np.pi / 60.0
    wr_ss = ws * (1.0 - s_ss)
    n_ss  = n_sync * (1.0 - s_ss)

    # trajetória: parte de 0, estabiliza no segundo terço
    ss_start = n // 3
    wr = np.concatenate([
        np.linspace(0, wr_ss, ss_start),
        np.full(n - ss_start, wr_ss) + (0.0 if steady else np.linspace(0, wr_ss * 0.1, n - ss_start)),
    ])
    Te = np.concatenate([np.linspace(Te_ss * 2, Te_ss, ss_start), np.full(n - ss_start, Te_ss)])

    return {
        "t":        t,
        "wr":       wr,
        "Te":       Te,
        "n":        wr * 60 / (2 * np.pi),
        "_ss_start": ss_start,
        "n_ss":     n_ss,
        "Te_ss":    Te_ss,
        "wr_ss":    wr_ss,
        "s":        s_ss,
    }


# ── testes de Insight ─────────────────────────────────────────────────────────

def test_insight_niveis_validos():
    for lvl in ("info", "warning", "error"):
        i = Insight(lvl, "T", "B")
        assert i.level == lvl


def test_insight_nivel_invalido():
    with pytest.raises(ValueError):
        Insight("critical", "T", "B")


def test_insight_repr():
    i = Insight("info", "Título", "Corpo")
    assert "info" in repr(i)
    assert "Título" in repr(i)


# ── testes de _is_steady_state_reached ───────────────────────────────────────

def test_steady_state_constante():
    t  = np.linspace(0, 2.0, 300)
    wr = np.full(300, 188.0)
    assert _is_steady_state_reached(wr, t, ss_start=100) is True


def test_steady_state_ainda_acelerando():
    t  = np.linspace(0, 2.0, 300)
    wr = np.linspace(0, 188.0, 300)
    assert _is_steady_state_reached(wr, t, ss_start=10) is False


def test_steady_state_ss_start_no_fim():
    t  = np.linspace(0, 2.0, 300)
    wr = np.full(300, 188.0)
    assert _is_steady_state_reached(wr, t, ss_start=299) is False


# ── testes de _sort_insights ──────────────────────────────────────────────────

def test_sort_ordem_decrescente():
    ins = [
        Insight("info",    "A", ""),
        Insight("error",   "B", ""),
        Insight("warning", "C", ""),
    ]
    s = _sort_insights(ins)
    assert [i.level for i in s] == ["error", "warning", "info"]


# ── testes de generate_insights — casos básicos ───────────────────────────────

def test_retorno_vazio_dados_curtos(mp):
    res = {"t": [0, 1], "wr": [0, 1], "Te": [0, 1], "n": [0, 1]}
    assert generate_insights(res, mp, load_torque=10.0, tmax=3.0) == []


def test_balanco_torque_presente(mp):
    res = _make_res(s_ss=0.03, Te_ss=12.0)
    ins = generate_insights(res, mp, load_torque=10.0, tmax=3.0, exp_type="dol")
    titulos = [i.title for i in ins]
    assert any("Torque Balance" in t for t in titulos)


def test_tipo_info_balanco(mp):
    res = _make_res(s_ss=0.03, Te_ss=12.0)
    ins = generate_insights(res, mp, load_torque=10.0, tmax=3.0, exp_type="dol")
    info = [i for i in ins if "Torque Balance" in i.title]
    assert info[0].level == "info"


# ── testes de sobrecarga (escorregamento > 5%) ───────────────────────────────

def test_escorregamento_critico_gera_error(mp):
    res = _make_res(s_ss=0.10, Te_ss=25.0)
    ins = generate_insights(res, mp, load_torque=20.0, tmax=3.0, exp_type="dol")
    assert any(i.level == "error" and "OVERLOAD" in i.title.upper() for i in ins)


def test_escorregamento_alerta_gera_warning(mp):
    res = _make_res(s_ss=0.06, Te_ss=18.0)
    ins = generate_insights(res, mp, load_torque=15.0, tmax=3.0, exp_type="dol")
    assert any(i.level == "warning" and "Slip" in i.title for i in ins)


def test_escorregamento_normal_sem_sobrecarga(mp):
    res = _make_res(s_ss=0.03, Te_ss=12.0)
    ins = generate_insights(res, mp, load_torque=10.0, tmax=3.0, exp_type="dol")
    assert not any("OVERLOAD" in i.title.upper() for i in ins)


# ── testes de subcarga ────────────────────────────────────────────────────────

def test_subcarga_gera_warning(mp):
    res = _make_res(s_ss=0.002, Te_ss=2.0)
    ins = generate_insights(res, mp, load_torque=1.0, tmax=3.0, exp_type="dol")
    assert any("Underload" in i.title for i in ins)


def test_sem_subcarga_com_s_normal(mp):
    res = _make_res(s_ss=0.03, Te_ss=12.0)
    ins = generate_insights(res, mp, load_torque=10.0, tmax=3.0, exp_type="dol")
    assert not any("Underload" in i.title for i in ins)


# ── testes de reserva de conjugado ───────────────────────────────────────────

def test_ampla_reserva_gera_info(mp):
    res = _make_res(s_ss=0.03, Te_ss=12.0)
    # Te_max in array is 24 N·m (2× Te_ss), load = 10 → ratio = 2.4
    ins = generate_insights(res, mp, load_torque=10.0, tmax=3.0, exp_type="dol")
    assert any("Ample" in i.title for i in ins)


def test_partida_pesada_gera_error(mp):
    # Te_max ≈ 2×Te_ss = 12, load = 11 → ratio ≈ 1.09 < 1.2
    res = _make_res(s_ss=0.03, Te_ss=6.0)
    ins = generate_insights(res, mp, load_torque=11.0, tmax=3.0, exp_type="dol")
    assert any("STALL" in i.title.upper() or "Heavy" in i.title for i in ins)


# ── testes para tipos especiais de experimento ───────────────────────────────

def test_shutdown_sem_balanco(mp):
    res = _make_res(s_ss=0.03, Te_ss=12.0)
    ins = generate_insights(res, mp, load_torque=0.0, tmax=3.0, exp_type="shutdown")
    assert not any("Torque Balance" in i.title for i in ins)


def test_gerador_sem_sobrecarga(mp):
    res = _make_res(s_ss=-0.02, Te_ss=-10.0)
    ins = generate_insights(res, mp, load_torque=0.0, tmax=3.0, exp_type="gerador")
    assert not any("OVERLOAD" in i.title.upper() for i in ins)


# ── testes de ordenação de severidade ────────────────────────────────────────

def test_insights_ordenados_por_severidade(mp):
    res = _make_res(s_ss=0.10, Te_ss=25.0)
    ins = generate_insights(res, mp, load_torque=20.0, tmax=3.0, exp_type="dol")
    niveis = [i.level for i in ins]
    ordem  = {"error": 0, "warning": 1, "info": 2}
    assert niveis == sorted(niveis, key=lambda x: ordem[x])
