# -*- coding: utf-8 -*-
"""Análise energética e econômica em regime permanente.

Exporta:
    compute_energy_metrics — energia, custo, THD e fator de potência

Documentacao detalhada de cada decisao de implementacao:
  SME/2. Modulos/core/energy_analysis.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (secao 8)
"""

from __future__ import annotations
import numpy as np


def compute_energy_metrics(res: dict, tarifa_brl_kwh: float) -> dict:
    """Calcula energia consumida, rendimento médio, custo operacional, THD e FP.

    Integra P_in = (3/2)·(Vqs·iqs + Vds·ids) sobre todo o intervalo de simulação.
    O rendimento é calculado na janela de regime permanente.
    THD = sqrt(Σ Ak² k≥2) / A1 × 100% via FFT de ias na janela de regime permanente.
    FP = P_in_ss / S_aparente onde S = 3 × Va_rms × ias_rms.

    Returns dict com:
        E_total_kwh   — energia total consumida no experimento (kWh)
        custo_exp_brl — custo do experimento (R$)
        horas_op_ano  — horas de operação projetadas por ano
        custo_ano_brl — custo operacional anual projetado (R$)
        eta_ss        — rendimento em regime permanente (%)
        P_in_ss_kw    — potência de entrada em regime (kW)
        thd_pct       — THD de ias em regime permanente (%)
        fp            — Fator de Potência em regime permanente (adimensional)
    """
    t   = np.asarray(res["t"],   dtype=float)
    Vqs = np.asarray(res["Vqs"], dtype=float)
    Vds = np.asarray(res["Vds"], dtype=float)
    iqs = np.asarray(res["iqs"], dtype=float)
    ids = np.asarray(res["ids"], dtype=float)

    # fator 3/2: convencao amplitude-invariante (P = (3/2)*(Vqs*iqs + Vds*ids))
    P_in_inst   = (3.0 / 2.0) * (Vqs * iqs + Vds * ids)
    # np.trapezoid integra numericamente; NaN substituido por 0 (passo com falha numerica)
    # 3_600_000 = 3.6e6 J/kWh — separador de milhar para legibilidade
    E_total_j   = float(np.trapezoid(np.where(np.isfinite(P_in_inst), P_in_inst, 0.0), t))
    E_total_kwh = E_total_j / 3_600_000.0
    custo_exp_brl = E_total_kwh * tarifa_brl_kwh

    ss_start   = int(res.get("_ss_start", 0))
    eta_ss     = float(res.get("eta", 0.0))
    P_in_ss    = float(res.get("P_in", 0.0))
    P_in_ss_kw = P_in_ss / 1000.0

    # custo anual extrapolado de P_in_ss (regime permanente), nao de E_total (transitorio)
    # representa operacao continua — cenario relevante para dimensionamento
    horas_op_ano  = 8_760.0
    E_ano_kwh     = P_in_ss_kw * horas_op_ano
    custo_ano_brl = E_ano_kwh * tarifa_brl_kwh

    thd_pct = 0.0
    fp      = 0.0
    try:
        ias_ss = np.asarray(res["ias"][ss_start:], dtype=float)
        t_ss   = t[ss_start:]
        if len(ias_ss) >= 16:
            dt_ss = float(t_ss[1] - t_ss[0]) if len(t_ss) > 1 else 1e-4
            N     = len(ias_ss)
            spec  = np.abs(np.fft.rfft(ias_ss)) / N
            freqs = np.fft.rfftfreq(N, d=dt_ss)
            f_fund = float(res.get("_f_fund", 60.0)) if "_f_fund" in res else 60.0
            # janela [0.5 fe, 1.5 fe]: robusta a pequenos erros no periodo da janela de regime
            mask_fund = (freqs > 0.5 * f_fund) & (freqs < 1.5 * f_fund)
            if mask_fund.any():
                A1        = float(spec[mask_fund].max())
                # harmônicas: tudo acima de 1.5 fe (evita incluir a propria fundamental)
                mask_harm = freqs > 1.5 * f_fund
                A_harm    = spec[mask_harm]
                if A1 > 0 and len(A_harm) > 0:
                    thd_pct = float(np.sqrt(np.sum(A_harm ** 2)) / A1 * 100.0)

        Vqs_ss  = Vqs[ss_start:]
        Vds_ss  = Vds[ss_start:]
        # |Vdq| = sqrt(Vqs²+Vds²) e a amplitude de pico da tensao de fase no ref sincrono
        Va_pk   = float(np.sqrt(np.mean(Vqs_ss ** 2 + Vds_ss ** 2)))
        Va_rms  = Va_pk / np.sqrt(2.0)
        ias_rms = float(res.get("ias_rms", 0.0))
        S_ap    = 3.0 * Va_rms * ias_rms
        # np.clip garante FP fisicamente valido mesmo com pequenos erros numericos
        if S_ap > 0 and np.isfinite(P_in_ss):
            fp = float(np.clip(abs(P_in_ss) / S_ap, 0.0, 1.0))
    except Exception:
        # analise espectral pode falhar por janela curta, NaN ou A1=0
        # retorna thd=0 e fp=0 — valores neutros sem alarmar a UI
        pass

    return {
        "E_total_kwh":   E_total_kwh,
        "custo_exp_brl": custo_exp_brl,
        "horas_op_ano":  horas_op_ano,
        "custo_ano_brl": custo_ano_brl,
        "eta_ss":        eta_ss,
        "P_in_ss_kw":    P_in_ss_kw,
        "thd_pct":       thd_pct,
        "fp":            fp,
    }
