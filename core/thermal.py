# -*- coding: utf-8 -*-
"""
thermal.py — Modelo térmico de 1ª ordem para motores de indução

Exporta:
  estimate_rth_cth(mp)  — estima Rth e Cth a partir dos parâmetros elétricos
  dTemp_dt(Temp, P_joule, P_fe, Rth, Cth, T_amb)  — EDO térmica (escalar)

Modelo:
  dT/dt = (P_joule + P_fe) / Cth  −  (T − T_amb) / (Rth · Cth)
  T_regime = T_amb + Rth · (P_joule + P_fe)   (equilíbrio térmico)

O Rth é calibrado para ΔT = 50 K em carga nominal — alvo típico de operação
de motores TEFC bem dimensionados (T_regime ≈ 75°C com T_amb = 25°C).
Esse valor é representativo do que se mede em campo; 105 K (Classe B) é o
limite de projeto, não a condição normal de operação.

O Cth é estimado a partir da massa do motor: Cth = massa × cp_aço (460 J/kg·K).
A massa é proxy da potência mecânica: massa ≈ P_mec_kW × 15 kg/kW.

Heurística de massa: ~15 kg/kW — razoável para motores TEFC 0.5–2500 kW
conforme catálogos WEG/Siemens (desvio típico < 30%).

Documentacao detalhada de cada decisao de implementacao:
  SME/2. Modulos/core/thermal.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (secao 6)
  SME/1. Fundamentos/4 - Modelo Matematico (RHS Krause).md
"""

from __future__ import annotations
import math


# ΔT de operação nominal típico para motores TEFC bem dimensionados
# (75°C em regime com T_amb=25°C); 105 K (Classe B) é o limite de projeto.
_DELTA_T_NOMINAL: float = 50.0   # K

# Calor específico do aço (J/kg·K) — usado para estimar Cth a partir da massa
_CP_ACO: float = 460.0             # J/(kg·K)

# kg de motor por kW de potência mecânica — heurística catálogos TEFC
_KG_POR_KW: float = 15.0


def estimate_rth_cth(
    Vl: float,
    Rs: float, Rr: float,
    Xls_a: float, Xlr_a: float, Xm_a: float,
    s_nom: float = 0.03,
) -> tuple[float, float]:
    """Estima Rth (K/W) e Cth (J/K) pelo circuito equivalente em T no escorregamento nominal.

    Args:
        Vl:     Tensão de linha (V).
        Rs, Rr: Resistências de estator e rotor (Ω), referidas ao estator.
        Xls_a:  Reatância de dispersão do estator em wb (Ω).
        Xlr_a:  Reatância de dispersão do rotor em wb (Ω).
        Xm_a:   Reatância de magnetização em wb (Ω) — ramo paralelo puro (wb·Lm).
        s_nom:  Escorregamento nominal (padrão 0.03 = 3%).

    Returns:
        (Rth, Cth) — ambos em unidades SI.
    """
    Vfase = Vl / math.sqrt(3.0)

    # Circuito T (nao pi): Xm_a e o ramo de magnetizacao puro (wb*Lm).
    # Usar Xml (circuito pi) superestimaria as correntes nominais — ver SME/2. Modulos/core/thermal.md
    Z_rotor    = complex(Rr / s_nom, Xlr_a)
    Z_mag      = complex(0.0, Xm_a)
    Z_paralelo = (Z_rotor * Z_mag) / (Z_rotor + Z_mag)
    Z_total    = complex(Rs, Xls_a) + Z_paralelo

    I_estator = Vfase / abs(Z_total)
    # divisor de corrente: fracao de I_estator que flui pelo ramo do rotor
    I_rotor   = I_estator * abs(Z_mag / (Z_rotor + Z_mag))

    # max(..., 10.0) e max(..., 0.5): guarda contra divisao por zero com parametros extremos
    P_perdas  = max(3.0 * (Rs * I_estator**2 + Rr * I_rotor**2), 10.0)
    P_mec_kw  = max(
        (3.0 * I_rotor**2 * (Rr / s_nom) * (1.0 - s_nom)) / 1000.0,
        0.5,
    )

    # massa como proxy de P_mec: ~15 kg/kW (heuristica catalogo TEFC WEG/Siemens)
    massa = P_mec_kw * _KG_POR_KW

    # Rth calibrado para DeltaT=50 K — T_regime tipico de TEFC bem dimensionado
    Rth = _DELTA_T_NOMINAL / P_perdas
    Cth = massa * _CP_ACO

    return Rth, Cth


def dTemp_dt(
    Temp: float,
    P_joule: float,
    P_fe: float,
    Rth: float,
    Cth: float,
    T_amb: float,
) -> float:
    """Derivada da temperatura do motor (EDO de 1ª ordem, parâmetros concentrados).

    dT/dt = (P_joule + P_fe) / Cth  −  (T − T_amb) / (Rth · Cth)

    Integrada dentro do ODE principal (estado 7) para que o LSODA controle o
    passo de integracao termico junto com os estados eletromagneticos.
    Ver SME/2. Modulos/core/thermal.md — secao 'Por que integrar dentro do ODE'.
    """
    return (P_joule + P_fe) / Cth - (Temp - T_amb) / (Rth * Cth)
