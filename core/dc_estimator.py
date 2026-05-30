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
    V_dc_f: float = 0.0,
    I_dc_f: float = 0.0,
    V_ac: float = 0.0,
    I_ac: float = 0.0,
    theta_deg: float = 0.0,
    f_ac: float = 60.0,
    tau_f_ms: float = 0.0,
) -> dict[str, float]:
    """Estimativa a partir de ensaios laboratoriais (IEEE Std 113-1985).

    Ensaio CC armadura (Sec. 4.2.2.2):
        Ra = V_dc / I_dc

    Ensaio CC campo (Sec. 4.2.2.1, terminais F1-F2, excitação separada):
        Rf = V_dc_f / I_dc_f

    Ensaio CA de indutância de armadura (Sec. 7.5.1):
        La = V_ac · sin(theta) / (I_ac · 2π · f_ac)
        (rotor travado, campo curto-circuitado, I_ac ≤ 20% de I_n)

    Ensaio de degrau de campo — indutância de campo (Sec. 7.5.3):
        Lf = Rf · tau_f   onde tau_f = tempo para 63,2% de If_final

    Ensaio a vazio (Sec. 5.6):
        Ea = Va - Ra · Ia,nl
        kb = Ea / (ifd · wm)

    Parâmetros
    ----------
    V_dc     : Tensão CC — ensaio de Ra (V)
    I_dc     : Corrente CC — ensaio de Ra (A)
    V_nl     : Tensão de armadura a vazio (V)
    I_nl     : Corrente de armadura a vazio (A)
    If_nl    : Corrente de campo a vazio (A)
    n_nl_rpm : Velocidade a vazio (RPM)
    excitation: Configuração de excitação
    V_dc_f   : Tensão CC — ensaio de Rf (V), excitação separada
    I_dc_f   : Corrente CC — ensaio de Rf (A), excitação separada
    V_ac     : Tensão CA — ensaio de La (V)
    I_ac     : Corrente CA — ensaio de La (A)
    theta_deg: Ângulo de fase V-I — ensaio de La (graus)
    f_ac     : Frequência CA — ensaio de La (Hz)
    tau_f_ms : Constante de tempo de campo medida — ensaio de Lf (ms)
    """
    Ra = V_dc / max(I_dc, 1e-9)
    wm_nl = n_nl_rpm * 2.0 * math.pi / 60.0
    Ea_nl = V_nl - Ra * I_nl

    if If_nl > 1e-9 and wm_nl > 1e-9:
        kb = Ea_nl / (If_nl * wm_nl)
    else:
        kb = 0.005

    # La: Sec. 7.5.1 — ensaio CA (rotor travado, campo curto-circuitado)
    # L = V·sin(θ) / (I·2πf)
    if V_ac > 1e-9 and I_ac > 1e-9 and abs(theta_deg) > 0.1:
        theta_rad = math.radians(theta_deg)
        La = V_ac * math.sin(theta_rad) / (I_ac * 2.0 * math.pi * max(f_ac, 1.0))
        La = max(La, 1e-6)
    else:
        La = Ra * 0.8  # heurística quando ensaio CA não realizado

    # Rf: Sec. 4.2.2.1 — ensaio CC campo (sep) ou V_nl/If_nl (shunt)
    is_sep = excitation in ("sep_motor", "sep_gen")
    if is_sep and V_dc_f > 1e-9 and I_dc_f > 1e-9:
        Rf = V_dc_f / I_dc_f
    elif not is_sep and If_nl > 1e-9:
        Rf = V_nl / If_nl
    else:
        Rf = 0.0

    # Lf: Sec. 7.5.3 — ensaio de degrau; Lf = Rf · tau_f
    if tau_f_ms > 1e-3 and Rf > 1e-9:
        Lf = Rf * (tau_f_ms / 1000.0)
    else:
        Lf = Rf * 0.1 if Rf > 1e-9 else ((V_nl / If_nl) * 0.1 if If_nl > 1e-9 else 1.0)

    result = {
        "Ra":    round(Ra, 5),
        "La":    round(La, 5),
        "kb":    round(max(kb, 1e-6), 6),
        "Lf":    round(Lf, 4),
        "Ea_nl": round(Ea_nl, 4),
    }
    if Rf > 1e-9:
        result["Rf"] = round(Rf, 4)
    return result
