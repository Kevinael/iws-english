"""Estimador de parâmetros para MCC.

Exporta:
    estimate_dc_nameplate  — a partir de dados de placa (Pn, Vn, nn, η)
    estimate_dc_tests      — a partir de ensaios (CC + a vazio)
"""

from __future__ import annotations

import math


def estimate_dc_nameplate(
    Pn_W: float,
    Vn: float,
    nn_rpm: float,
    eta: float,
    excitation: str = "sep_motor",
) -> dict[str, float]:
    """Estimativa a partir da placa de identificação (NEMA).

    Parâmetros
    ----------
    Pn_W      : Potência nominal na placa (W) — saída mecânica para motor
    Vn        : Tensão nominal de armadura (V)
    nn_rpm    : Velocidade nominal (RPM)
    eta       : Rendimento nominal (0–1)
    excitation: Configuração de excitação

    Retorna dict com Ra, kb, Vf, Rf estimados.
    """
    if eta <= 0 or eta > 1:
        eta = 0.85

    wm_n  = nn_rpm * 2.0 * math.pi / 60.0
    In    = Pn_W / (Vn * eta)           # corrente de armadura nominal
    Ea_n  = Pn_W / In if In > 1e-9 else Vn * 0.95

    # Ra estimado por queda ≈ 5–10% de Vn
    Ra = (Vn - Ea_n) / In if In > 1e-9 else Vn * 0.05 / max(In, 1.0)
    Ra = max(Ra, 1e-4)

    # kb: Ea = kb * ifd * wm; assumindo ifd ≈ 1 A (excitação típica)
    ifd_nom = 1.0
    if excitation in ("shunt_motor", "shunt_gen"):
        # ifd = Va/Rf → estimar Rf ≈ Vn/ifd_nom
        Rf_est = Vn / ifd_nom
    elif excitation == "sep_motor":
        Rf_est = Vn * 0.5 / ifd_nom   # Vf ≈ Vn/2 típico
    else:
        Rf_est = Vn / ifd_nom

    kb = Ea_n / (ifd_nom * wm_n) if wm_n > 1e-9 else 0.005

    Vf_est = Vn * 0.5 if excitation in ("sep_motor", "sep_gen") else Vn
    Lf_est = Rf_est * 0.1   # τ_f ≈ 100 ms típico
    La_est = Ra * 0.8       # τ_a ≈ Ra/La

    J_est = Pn_W * 0.01 / (wm_n ** 2) if wm_n > 1e-9 else 0.01
    B_est = Pn_W * 0.001 / max(wm_n, 1.0)

    return {
        "Ra": round(Ra, 5),
        "La": round(La_est, 5),
        "Rf": round(Rf_est, 4),
        "Lf": round(Lf_est, 4),
        "kb": round(kb, 6),
        "Va": round(Vn, 2),
        "Vf": round(Vf_est, 2),
        "J":  round(J_est, 4),
        "B":  round(B_est, 6),
    }


def estimate_dc_tests(
    V_dc: float,
    I_dc: float,
    V_nl: float,
    I_nl: float,
    If_nl: float,
    n_nl_rpm: float,
    excitation: str = "sep_motor",
) -> dict[str, float]:
    """Estimativa a partir de ensaios laboratoriais.

    Ensaio CC (rotor parado, campo excitado):
        Ra = V_dc / I_dc

    Ensaio a vazio (motor em velocidade nominal, carga zero):
        Ea = Va - Ra * Ia,nl
        kb = Ea / (ifd * wm)

    Parâmetros
    ----------
    V_dc    : Tensão CC aplicada no ensaio de resistência (V)
    I_dc    : Corrente CC no ensaio de resistência (A)
    V_nl    : Tensão de armadura no ensaio a vazio (V)
    I_nl    : Corrente de armadura no ensaio a vazio (A)
    If_nl   : Corrente de campo no ensaio a vazio (A)
    n_nl_rpm: Velocidade no ensaio a vazio (RPM)
    excitation: Configuração de excitação

    Retorna dict com Ra, kb estimados.
    """
    Ra = V_dc / max(I_dc, 1e-9)
    wm_nl = n_nl_rpm * 2.0 * math.pi / 60.0
    Ea_nl = V_nl - Ra * I_nl

    if If_nl > 1e-9 and wm_nl > 1e-9:
        kb = Ea_nl / (If_nl * wm_nl)
    else:
        kb = 0.005

    La_est = Ra * 0.8
    Lf_est = (V_nl / If_nl) * 0.1 if If_nl > 1e-9 else 1.0

    return {
        "Ra": round(Ra, 5),
        "La": round(La_est, 5),
        "kb": round(max(kb, 1e-6), 6),
        "Lf": round(Lf_est, 4),
        "Ea_nl": round(Ea_nl, 4),
    }
