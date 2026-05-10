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

O Cth é derivado de τ_th empírico (catálogos TEFC WEG/ABB/Siemens):
τ_th ≈ 1500 s para 2,2 kW (3 HP), escalando por τ ∝ P_mec^0,25 para motores maiores.
A temperatura é calculada em pós-processamento (não como estado do ODE) para evitar
que o pico de inrush eletromagnético (P_joule >> P_nom em t < 50 ms) produza aquecimento
artificialmente elevado por erro de discretização com o passo h da simulação principal.

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

# Constante de tempo térmica de referência (s) para motor TEFC de 2,2 kW (3 HP).
# Calibrado contra catálogos WEG/ABB/Siemens: τ_th ≈ 20–25 min para motores pequenos.
# Escalonada por potência via _TAU_EXPONENT para reproduzir τ crescente com porte.
_TAU_REF_S: float  = 1500.0   # s  — τ_th para P_ref = 2,2 kW
_TAU_P_REF: float  =    2.2   # kW — potência de referência
_TAU_EXPONENT: float = 0.25   # τ ∝ P^0.25 (sublinear — validado: 37 kW → ~2000 s, 1678 kW → ~3200 s)


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

    # Rth calibrado para ΔT=50 K — T_regime típico de TEFC bem dimensionado
    Rth = _DELTA_T_NOMINAL / P_perdas

    # Cth derivado de τ_th empírico (catálogos TEFC): τ = Rth · Cth
    # τ escala sublinearmente com potência — motores maiores têm τ maior mas Rth menor
    tau_th = _TAU_REF_S * (P_mec_kw / _TAU_P_REF) ** _TAU_EXPONENT
    Cth = tau_th / Rth

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
