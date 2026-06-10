# -*- coding: utf-8 -*-
"""
dc_estimator.py
===============
Estimates DC machine parameters from nameplate data and laboratory tests.

Responsibilities:
  - Compute Ra, La, Rf, Lf, Ke, J from Pn, Vn, nn, η, and excitation type
    (nameplate method)
  - Process locked-rotor and no-load test data (tests method)

Relationships:
  Imported by : ui.theory_dc_interactive
  Imports     : (math only)

Extending:
  - To include field-to-armature mutual inductance Laf, add it to the
    separately-excited nameplate estimator.
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
    """Estimates parameters from nameplate data (NEMA).

    Parameters
    ----------
    Pn_W      : Rated power on nameplate (W) — mechanical output for motor
    Vn        : Rated armature voltage (V)
    nn_rpm    : Rated speed (RPM)
    eta       : Rated efficiency (0–1)
    excitation: Excitation configuration

    Returns dict with estimated Ra, kb, Vf, Rf.
    """
    if eta <= 0 or eta > 1:
        eta = 0.85

    wm_n  = nn_rpm * 2.0 * math.pi / 60.0
    In    = Pn_W / (Vn * eta)           # rated armature current
    Ea_n  = Pn_W / In if In > 1e-9 else Vn * 0.95

    # Ra estimated from ≈ 5–10% drop of Vn
    Ra = (Vn - Ea_n) / In if In > 1e-9 else Vn * 0.05 / max(In, 1.0)
    Ra = max(Ra, 1e-4)

    # kb: Ea = kb * ifd * wm; assuming ifd ≈ 1 A (typical excitation)
    ifd_nom = 1.0
    if excitation in ("shunt_motor", "shunt_gen"):
        # ifd = Va/Rf → estimate Rf ≈ Vn/ifd_nom
        Rf_est = Vn / ifd_nom
    elif excitation == "sep_motor":
        Rf_est = Vn * 0.5 / ifd_nom   # Vf ≈ Vn/2 typical
    else:
        Rf_est = Vn / ifd_nom

    kb = Ea_n / (ifd_nom * wm_n) if wm_n > 1e-9 else 0.005

    Vf_est = Vn * 0.5 if excitation in ("sep_motor", "sep_gen") else Vn
    Lf_est = Rf_est * 0.1   # τ_f ≈ 100 ms typical
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
    """Estimates parameters from laboratory tests (IEEE Std 113-1985).

    DC armature test (Sec. 4.2.2.2):
        Ra = V_dc / I_dc

    DC field test (Sec. 4.2.2.1, terminals F1-F2, separate excitation):
        Rf = V_dc_f / I_dc_f

    AC armature inductance test (Sec. 7.5.1):
        La = V_ac · sin(theta) / (I_ac · 2π · f_ac)
        (rotor locked, field short-circuited, I_ac ≤ 20% of I_n)

    Field step test — field inductance (Sec. 7.5.3):
        Lf = Rf · tau_f   where tau_f = time to reach 63.2% of If_final

    No-load test (Sec. 5.6):
        Ea = Va - Ra · Ia,nl
        kb = Ea / (ifd · wm)

    Parameters
    ----------
    V_dc     : DC voltage — Ra test (V)
    I_dc     : DC current — Ra test (A)
    V_nl     : Armature voltage at no load (V)
    I_nl     : Armature current at no load (A)
    If_nl    : Field current at no load (A)
    n_nl_rpm : No-load speed (RPM)
    excitation: Excitation configuration
    V_dc_f   : DC voltage — Rf test (V), separate excitation
    I_dc_f   : DC current — Rf test (A), separate excitation
    V_ac     : AC voltage — La test (V)
    I_ac     : AC current — La test (A)
    theta_deg: V-I phase angle — La test (degrees)
    f_ac     : AC frequency — La test (Hz)
    tau_f_ms : Measured field time constant — Lf test (ms)
    """
    Ra = V_dc / max(I_dc, 1e-9)
    wm_nl = n_nl_rpm * 2.0 * math.pi / 60.0
    Ea_nl = V_nl - Ra * I_nl

    if If_nl > 1e-9 and wm_nl > 1e-9:
        kb = Ea_nl / (If_nl * wm_nl)
    else:
        kb = 0.005

    # La: Sec. 7.5.1 — AC test (rotor locked, field short-circuited)
    # L = V·sin(θ) / (I·2πf)
    if V_ac > 1e-9 and I_ac > 1e-9 and abs(theta_deg) > 0.1:
        theta_rad = math.radians(theta_deg)
        La = V_ac * math.sin(theta_rad) / (I_ac * 2.0 * math.pi * max(f_ac, 1.0))
        La = max(La, 1e-6)
    else:
        La = Ra * 0.8  # heuristic when AC test not performed

    # Rf: Sec. 4.2.2.1 — DC field test (sep) or V_nl/If_nl (shunt)
    is_sep = excitation in ("sep_motor", "sep_gen")
    if is_sep and V_dc_f > 1e-9 and I_dc_f > 1e-9:
        Rf = V_dc_f / I_dc_f
    elif not is_sep and If_nl > 1e-9:
        Rf = V_nl / If_nl
    else:
        Rf = 0.0

    # Lf: Sec. 7.5.3 — step test; Lf = Rf · tau_f
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
