# -*- coding: utf-8 -*-
"""Testes de core/param_estimator.py — estimação por dados de placa e ensaios IEEE 112."""
import math

import pytest

from core.mit_param_estimator import estimate_params, estimate_params_ieee_tests


BASE = dict(Vl=220, f=60, p=4, Pn_kW=2.24, N_nom=1746,
            rend=0.84, fp=0.82, Ip_In=6.0, Tp_Tn=1.5, is_delta=False)


def test_estimate_returns_success():
    res = estimate_params(**BASE)
    assert res.get("success") is True


def test_estimate_Rs_positive():
    res = estimate_params(**BASE)
    assert res["Rs"] > 0.0


def test_estimate_Rr_positive():
    res = estimate_params(**BASE)
    assert res["Rr"] > 0.0


def test_estimate_Xm_positive():
    res = estimate_params(**BASE)
    assert res["Xm"] > 0.0


def test_estimate_Xls_positive():
    res = estimate_params(**BASE)
    assert res["Xls"] > 0.0


def test_estimate_Xlr_positive():
    res = estimate_params(**BASE)
    assert res["Xlr"] > 0.0


def test_estimate_Xm_greater_than_leakage():
    """Xm deve ser maior que as reatâncias de dispersão."""
    res = estimate_params(**BASE)
    assert res["Xm"] > res["Xls"]
    assert res["Xm"] > res["Xlr"]


def test_estimate_nema_b_ratio():
    """Distribuição NEMA B: Xls/Xlr ≈ 0.4/0.6 = 2/3."""
    res = estimate_params(**BASE)
    ratio = res["Xls"] / res["Xlr"]
    assert abs(ratio - 2.0/3.0) < 0.05


def test_estimate_delta_connection():
    """Ligação delta deve retornar sucesso e parâmetros coerentes."""
    params = {**BASE, "is_delta": True}
    res = estimate_params(**params)
    assert res.get("success") is True
    assert res["Rs"] > 0.0


def test_estimate_large_motor():
    """Motor de grande porte (2250 HP) deve convergir."""
    res = estimate_params(
        Vl=2300, f=60, p=4, Pn_kW=1678, N_nom=1786,
        rend=0.965, fp=0.89, Ip_In=5.5, Tp_Tn=1.3, is_delta=False,
    )
    assert res.get("success") is True
    assert res["Rs"] > 0.0
    assert res["Xm"] > res["Xls"]


# ═════════════════════════════════════════════════════════════════════════════
# Testes para estimate_params_ieee_tests() — IEEE Std 112-2017
# ═════════════════════════════════════════════════════════════════════════════

# Parâmetros conhecidos do preset Krause 3 HP — usados para round-trip
KRAUSE = dict(
    Rs=0.435, Rr=0.816, Xm=26.13, Xls=0.754, Xlr=0.754,
    Vl_nom=220.0, f_nom=60.0, Rfe_alvo=400.0,
)


def _gerar_medicoes_krause_Y(f_lr: float = 15.0):
    """Gera medições sintéticas a partir dos parâmetros do Krause 3 HP (ligação Y).

    Retorna kwargs prontos para estimate_params_ieee_tests().
    """
    Rs, Rr, Xls, Xlr = KRAUSE["Rs"], KRAUSE["Rr"], KRAUSE["Xls"], KRAUSE["Xlr"]
    Xm, Rfe = KRAUSE["Xm"], KRAUSE["Rfe_alvo"]
    Vl_nom, f_nom = KRAUSE["Vl_nom"], KRAUSE["f_nom"]
    Vf_nom = Vl_nom / math.sqrt(3.0)

    # ── Ensaio CC: V_dc/I_dc = 2·Rs (ligação Y) ────────────────────────────
    I_dc = 11.5
    V_dc = 2.0 * Rs * I_dc

    # ── Ensaio em vazio (s ≈ 0): I_mu via Xm+Xls, I_fe via Rfe ─────────────
    # Aproximação: tensão sobre o ramo de magnetização ≈ Vf_nom (queda em Rs+jXls pequena)
    E1_aprox = Vf_nom
    I_fe = E1_aprox / Rfe
    I_mu = E1_aprox / (Xm + Xls)
    I_nl = math.sqrt(I_fe ** 2 + I_mu ** 2)

    # Potência em vazio: Joule no estator + perdas no ferro + perdas mecânicas
    # Adotamos Pfw = 0 (a função usará 0,8% de P_nl como heurística)
    # P_nl·(1 - 0.008) = 3·Rs·I_nl² + 3·E1²/Rfe
    Pfe_3ph = 3.0 * E1_aprox ** 2 / Rfe
    P_joule_st = 3.0 * Rs * I_nl ** 2
    P_nl = (P_joule_st + Pfe_3ph) / (1.0 - 0.008)

    # ── Ensaio bloqueado (s = 1, Xm >> Xlr): Zk = (Rs+Rr) + j·(Xls+Xlr) ────
    Rk = Rs + Rr
    Xk_60 = Xls + Xlr
    # Escala linear para a frequência reduzida do ensaio
    Xk_lr = Xk_60 * (f_lr / f_nom)
    Zk_lr = math.sqrt(Rk ** 2 + Xk_lr ** 2)
    I_lr = 14.0
    Vf_lr = I_lr * Zk_lr
    Vl_lr = Vf_lr * math.sqrt(3.0)
    P_lr = 3.0 * Rk * I_lr ** 2

    return dict(
        V_dc=V_dc, I_dc=I_dc, is_delta=False,
        Vl_nl=Vl_nom, I_nl=I_nl, P_nl=P_nl, f_nl=f_nom,
        Vl_lr=Vl_lr, I_lr=I_lr, P_lr=P_lr, f_lr=f_lr,
        Pfw=0.0, split="B", Xls_frac=0.4,
    )


def test_ieee_returns_success():
    """Medições sintéticas Krause 3 HP devem produzir success=True."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    assert res.get("success") is True, res.get("error")


def test_ieee_krause_round_trip_Y_Rs():
    """Round-trip Y: Rs estimado deve bater com Rs do preset (±2%)."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    assert abs(res["Rs"] - KRAUSE["Rs"]) / KRAUSE["Rs"] < 0.02


def test_ieee_krause_round_trip_Y_Rr():
    """Round-trip Y: Rr estimado deve bater com Rr do preset (±5%)."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    assert abs(res["Rr"] - KRAUSE["Rr"]) / KRAUSE["Rr"] < 0.05


def test_ieee_krause_round_trip_Y_Xls_Xlr():
    """Round-trip Y: Xls + Xlr = Xk and both are positive after E1 convergence.

    The E1 iteration moves X1 away from frac·Xk (fraction is not preserved
    after convergence), so we only verify the conservation identity and signs.
    """
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    Xk = res["Xk"]
    assert abs(res["Xls"] + res["Xlr"] - Xk) < 1e-3
    assert res["Xls"] > 0.0
    assert res["Xlr"] > 0.0


def test_ieee_krause_round_trip_Y_Xm():
    """Round-trip Y: Xm estimated within 10% of preset (E1 iteration shifts Xls slightly)."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    assert abs(res["Xm"] - KRAUSE["Xm"]) / KRAUSE["Xm"] < 0.10


def test_ieee_krause_round_trip_Y_Rfe():
    """Round-trip Y: Rfe estimado deve bater com Rfe-alvo (±5%)."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    assert abs(res["Rfe"] - KRAUSE["Rfe_alvo"]) / KRAUSE["Rfe_alvo"] < 0.05


def test_ieee_grandezas_positivas():
    """Todas as grandezas resultantes devem ser positivas."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    for k in ("Rs", "Rr", "Xm", "Xls", "Xlr", "Rfe"):
        assert res[k] > 0.0, f"{k} = {res[k]} não é positivo"


@pytest.mark.parametrize("classe,frac_esperada", [
    ("A", 0.50), ("B", 0.40), ("C", 0.30), ("D", 0.50), ("WR", 0.50),
])
def test_ieee_split_classes(classe, frac_esperada):
    """Each NEMA class uses the correct initial Xls fraction (reported in Xls_frac).

    The E1 iteration moves the final Xls away from frac·Xk, so we verify the
    reported fraction and the conservation identity Xls + Xlr = Xk instead.
    """
    args = _gerar_medicoes_krause_Y()
    args["split"] = classe
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    Xk = res["Xk"]
    assert abs(res["Xls_frac"] - frac_esperada) < 1e-9
    assert abs(res["Xls"] + res["Xlr"] - Xk) < 1e-3


def test_ieee_split_custom():
    """split='custom' uses the provided Xls_frac; conservation holds."""
    args = _gerar_medicoes_krause_Y()
    args["split"] = "custom"
    args["Xls_frac"] = 0.35
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    Xk = res["Xk"]
    assert abs(res["Xls_frac"] - 0.35) < 1e-9
    assert abs(res["Xls"] + res["Xlr"] - Xk) < 1e-3


def test_ieee_pfw_zero_usa_heuristica():
    """Pfw = 0 → função adota Pfw_used = 0,8% de P_nl."""
    args = _gerar_medicoes_krause_Y()
    args["Pfw"] = 0.0
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    P_nl = args["P_nl"]
    assert abs(res["Pfw_used"] - 0.008 * P_nl) < 0.01


def test_ieee_pfw_informado_usa_valor_dado():
    """Pfw informado deve ser usado integralmente (sem heurística)."""
    args = _gerar_medicoes_krause_Y()
    args["Pfw"] = 25.0
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    assert abs(res["Pfw_used"] - 25.0) < 0.01


def test_ieee_freq_lr_correcao():
    """Xk a 60 Hz deve ser escalado linearmente de Xk_lr a f_lr."""
    args = _gerar_medicoes_krause_Y(f_lr=15.0)
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    # Xk_lr · (f_nl / f_lr) = Xk
    assert abs(res["Xk"] - res["Xk_lr"] * (args["f_nl"] / args["f_lr"])) < 1e-3


def test_ieee_rr_negativo_retorna_erro():
    """Rs > Rk deve retornar success=False com mensagem descritiva."""
    args = _gerar_medicoes_krause_Y()
    # Inflar Rs via ensaio CC: V_dc alto, I_dc baixo → Rs imenso
    args["V_dc"] = 200.0
    args["I_dc"] = 1.0
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is False
    assert "Rr" in res["error"] or "Rs" in res["error"]


def test_ieee_rejeita_v_dc_invalido():
    """V_dc <= 0 must return success=False with a DC-test error message."""
    args = _gerar_medicoes_krause_Y()
    args["V_dc"] = 0.0
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is False
    assert "DC" in res["error"] or "V_dc" in res["error"]


def test_ieee_rejeita_pnl_invalido():
    """P_nl <= 0 must return success=False with a no-load error message."""
    args = _gerar_medicoes_krause_Y()
    args["P_nl"] = -1.0
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is False
    assert "No-load" in res["error"] or "P_nl" in res["error"]


def test_ieee_rejeita_zk_inconsistente():
    """Rk ≥ Zk (fator de potência > 1) deve retornar success=False."""
    args = _gerar_medicoes_krause_Y()
    # Inflar P_lr além do possível: Rk > Zk
    args["P_lr"] = 10000.0
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is False
    assert "bloqueado" in res["error"] or "Rk" in res["error"]


def test_ieee_delta_connection():
    """Ligação Δ deve produzir Rs coerente (Rs_Y = Rs_Δ · 3) com V_dc/I_dc ajustados."""
    args = _gerar_medicoes_krause_Y()
    # Em Δ: Rs_fase = (V_dc/I_dc)·1,5 → para Rs = 0.435, V_dc/I_dc = 0.29
    args["is_delta"] = True
    # Ajustar V_dc para obter mesmo Rs em Δ: V_dc = Rs · I_dc / 1,5
    args["V_dc"] = KRAUSE["Rs"] * args["I_dc"] / 1.5
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    assert abs(res["Rs"] - KRAUSE["Rs"]) / KRAUSE["Rs"] < 0.02


def test_ieee_mesma_interface_que_placa():
    """As chaves comuns devem coincidir entre os dois estimadores."""
    res_ieee = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    res_placa = estimate_params(**BASE)
    # Chaves de parâmetros do circuito equivalente que populam MachineParams
    chaves_obrigatorias = {"success", "Rs", "Rr", "Xm", "Xls", "Xlr", "Rfe"}
    assert chaves_obrigatorias.issubset(res_ieee.keys())
    assert chaves_obrigatorias.issubset(res_placa.keys())


def test_ieee_split_invalido_cai_para_b():
    """Unknown split key must fall back to NEMA B (40%) and report split_used='B'."""
    args = _gerar_medicoes_krause_Y()
    args["split"] = "Z_INEXISTENTE"
    res = estimate_params_ieee_tests(**args)
    assert res["success"] is True
    assert res["split_used"] == "B"
    assert abs(res["Xls_frac"] - 0.40) < 1e-9


def test_ieee_xm_maior_que_dispersoes():
    """Xm deve ser muito maior que Xls e Xlr (motor saudável)."""
    res = estimate_params_ieee_tests(**_gerar_medicoes_krause_Y())
    assert res["Xm"] > res["Xls"]
    assert res["Xm"] > res["Xlr"]
    assert res["Xm"] > 5.0 * res["Xls"]
