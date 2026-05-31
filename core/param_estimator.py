# -*- coding: utf-8 -*-
"""
param_estimator.py — Equivalent-circuit parameter estimation from nameplate data.

Method: classical IEEE equivalent circuit (steady-state T-circuit approximation).
References: IEEE Std 112, NEMA MG-1, IEC 60034.

Adopted assumptions (all documented in the returned dict):
  1. NEMA B distribution: Xls = 0.4·Xk  and  Xlr = 0.6·Xk
  2. Starting power factor: cos(φp) = 0.20  (NEMA B average value)
  3. Air-gap voltage: E1 = Vf − In_phase·|Zs|  (stator drop subtracted)
  4. Pole count deduced from N_nom and f — independent of external widget
  5. Y or Δ connection affects Vf and the equivalent-circuit phase current
  6. Rfe not estimated — use default value in UI (500 Ω)
  7. Thermal inertia: 15 kg/kW × cp_steel (460 J/kg·K) — NEMA/IEC TEFC
"""

from __future__ import annotations
import math


def estimate_params(
    Vl: float,
    f: float,
    p: int,          # received but not used internally — p is deduced from N_nom
    Pn_kW: float,
    N_nom: float,
    rend: float,
    fp: float,
    Ip_In: float,
    Tp_Tn: float,
    is_delta: bool = False,
) -> dict:
    """Estimates equivalent-circuit parameters from nameplate data.

    Args:
        Vl:       Nominal line voltage (V).
        f:        Nominal frequency (Hz).
        p:        Number of poles — ignored internally, deduced from N_nom.
        Pn_kW:    Nominal shaft power (kW).
        N_nom:    Nominal speed (RPM).
        rend:     Nominal efficiency (fraction, e.g. 0.91 for 91%).
        fp:       Nominal power factor (fraction).
        Ip_In:    Starting current / nominal current ratio (line).
        Tp_Tn:    Starting torque / nominal torque ratio.
        is_delta: True = Delta (Δ) connection; False = Star (Y, default).

    Returns:
        dict with keys: success, Rs, Rr, Xm, Xls, Xlr, Cth, Massa, p_est, n_s, s_n,
        In_lin, In_fase, Tn, Ip_fase, Tp, Zk, Xk, E1.
        On error: {'success': False, 'error': <message>}.
    """
    try:
        # ── Input validation ───────────────────────────────────────────────
        if not (0.0 < rend < 1.0):
            return {"success": False, "error": f"Efficiency {rend:.3f} is invalid — must be in (0, 1)."}
        if not (0.0 < fp < 1.0):
            return {"success": False, "error": f"Power factor {fp:.3f} is invalid — must be in (0, 1)."}
        if Ip_In <= 0.0:
            return {"success": False, "error": "Starting-to-nominal current ratio Ip/In must be positive."}
        if Tp_Tn <= 0.0:
            return {"success": False, "error": "Starting-to-nominal torque ratio Tp/Tn must be positive."}
        if Pn_kW <= 0.0:
            return {"success": False, "error": "Nominal power must be positive."}
        if N_nom <= 0.0:
            return {"success": False, "error": "Nominal speed must be positive."}
        if f <= 0.0:
            return {"success": False, "error": "Frequency must be positive."}

        # ── 1. General quantities ──────────────────────────────────────────
        # Phase voltage (assumption 5)
        Vf = Vl if is_delta else Vl / math.sqrt(3.0)

        # Pole count deduced from nameplate (assumption 4)
        # n_s ≥ N_nom: p_pairs = round(f / (N_nom/60)) → p = 2·p_pairs
        p_pares = max(1, round(f / (N_nom / 60.0)))
        p_est   = 2 * p_pares
        n_s     = 120.0 * f / p_est          # synchronous speed (RPM)
        ws      = 4.0 * math.pi * f / p_est  # mechanical synchronous angular speed (rad/s)
        s_n     = 1.0 - N_nom / n_s          # nominal slip

        if not (0.0 < s_n < 1.0):
            return {
                "success": False,
                "error": (
                    f"Calculated slip s_n = {s_n:.4f} is invalid "
                    f"(p_est = {p_est}, n_s = {n_s:.1f} RPM). "
                    "Verify the nominal speed."
                ),
            }

        # ── 2. Nominal quantities ──────────────────────────────────────────
        Pn_W    = Pn_kW * 1000.0
        P_in    = Pn_W / rend                          # absorbed electrical power (W)
        In_lin  = P_in / (3.0 * Vf * fp)              # line current (A)

        # Phase current for the single-phase T equivalent circuit:
        # Δ: i_phase = i_line / sqrt(3); Y: i_phase = i_line
        In_fase = In_lin / math.sqrt(3.0) if is_delta else In_lin

        Tn      = Pn_W / (ws * (1.0 - s_n))           # nominal torque (N·m)

        if In_fase <= 0.0:
            return {"success": False, "error": "Calculated phase current is invalid. Verify efficiency and power factor."}

        # ── 3. Starting (s = 1) ────────────────────────────────────────────
        Ip_lin  = In_lin * Ip_In                       # starting line current
        Ip_fase = Ip_lin / math.sqrt(3.0) if is_delta else Ip_lin
        Zk      = Vf / Ip_fase                         # short-circuit impedance (Ω)
        Tp      = Tn * Tp_Tn                           # starting torque (N·m)

        # ── 4. Rotor resistance ────────────────────────────────────────────
        # Te = (3/ws)·Rr·Ip_fase²  →  Rr = Tp·ws / (3·Ip_fase²)
        Rr = (Tp * ws) / (3.0 * Ip_fase ** 2)

        # ── 5. Reactances (NEMA B distribution, assumptions 1 and 2) ──────
        cos_phi_p = 0.20                                # NEMA B assumption
        Rk  = Zk * cos_phi_p
        Xk  = math.sqrt(max(Zk ** 2 - Rk ** 2, 1e-6))
        Xls = 0.4 * Xk
        Xlr = 0.6 * Xk

        # ── 6. Stator resistance ───────────────────────────────────────────
        Rs = max(Rk - Rr, 1e-3)

        # ── 7. Magnetising reactance with E₁ correction (assumption 3) ────
        # The voltage applied across Xm is not Vf but E₁ = Vf − In_phase·|Zs|.
        # Neglecting this drop overestimates Xm by the factor (Vf/E₁).
        Z_s = math.sqrt(Rs ** 2 + Xls ** 2)
        E1  = max(Vf - In_fase * Z_s, 0.5 * Vf)       # clamp: E1 ≥ 50% Vf
        I_mu = In_fase * math.sqrt(max(1.0 - fp ** 2, 1e-6))
        Xm   = max(E1 / I_mu - Xls, 1e-3)

        # ── 8. Core loss resistance — heuristic distribution ───────────────
        # Without a no-load test it is not possible to isolate Pfe from other losses.
        # NEMA/IEC statistical heuristic: core losses ≈ 20% of total losses
        # at nominal operation (typical range: 15–25% for TEFC motors).
        # Pfe is then referred to the air-gap voltage E1 (not Vf) for
        # consistency with the T equivalent-circuit model.
        P_perdas_totais = max(P_in - Pn_W, 1.0)        # W — total losses
        P_fe_total  = P_perdas_totais * 0.20            # W — 20% to core
        P_fe_fase   = P_fe_total / 3.0                  # W per phase
        Rfe = (E1 ** 2) / P_fe_fase                     # Ω — per phase

        # ── 9. Thermal inertia — NEMA/IEC TEFC heuristic ──────────────────
        # Industrial rule: 15 kg per installed kW (frame + windings + rotor).
        # Steel Cp ≈ 460 J/(kg·K) — dominant value of the active mass.
        Massa = Pn_kW * 15.0                            # kg
        Cth   = Massa * 460.0                           # J/K

        return {
            "success": True,
            "Rs":      round(Rs,      5),
            "Rr":      round(Rr,      5),
            "Xm":      round(Xm,      4),
            "Xls":     round(Xls,     5),
            "Xlr":     round(Xlr,     5),
            "Rfe":     round(Rfe,     2),
            "Cth":     round(Cth,     1),
            "Massa":   round(Massa,   1),
            "P_fe_total": round(P_fe_total, 1),
            # intermediate quantities for transparency card
            "p_est":   p_est,
            "n_s":     round(n_s,     1),
            "s_n":     round(s_n,     5),
            "In_lin":  round(In_lin,  3),
            "In_fase": round(In_fase, 3),
            "Tn":      round(Tn,      2),
            "Ip_fase": round(Ip_fase, 3),
            "Tp":      round(Tp,      2),
            "Zk":      round(Zk,      4),
            "Xk":      round(Xk,      4),
            "E1":      round(E1,      3),
        }

    except ZeroDivisionError as exc:
        return {"success": False, "error": f"Division by zero during estimation: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Unexpected error: {exc}"}


# ─── Xls/Xlr split by class (IEEE Std 112-2017, Table 1) ─────────────────────
_IEEE_SPLIT_TABLE: dict[str, float] = {
    "A":      0.50,
    "B":      0.40,
    "C":      0.30,
    "D":      0.50,
    "WR":     0.50,
    "custom": 0.40,
}


def estimate_params_ieee_tests(
    V_dc: float,
    I_dc: float,
    is_delta: bool,
    Vl_nl: float,
    I_nl: float,
    P_nl: float,
    f_nl: float,
    Vl_lr: float,
    I_lr: float,
    P_lr: float,
    f_lr: float,
    Pfw: float = 0.0,
    split: str = "B",
    Xls_frac: float = 0.4,
) -> dict:
    """Estimates equivalent-circuit parameters from IEEE Std 112-2017 tests.

    Implements the three classical T-circuit tests:
      1. DC Test — Rs
      2. No-Load Test — Xm, Rfe
      3. Locked-Rotor Test — Rr, Xls, Xlr

    Args:
        V_dc:     DC voltage applied between two terminals (V).
        I_dc:     Measured DC current (A).
        is_delta: True = Delta (Δ) connection; False = Star (Y).
        Vl_nl:    No-load line voltage (V) — typically nominal.
        I_nl:     No-load line current (A).
        P_nl:     Total three-phase no-load power (W).
        f_nl:     No-load test frequency (Hz).
        Vl_lr:    Locked-rotor test line voltage (V) — reduced.
        I_lr:     Locked-rotor test line current (A).
        P_lr:     Total three-phase locked-rotor power (W).
        f_lr:     Locked-rotor test frequency (Hz) — IEEE recommends ≈ 25% of f_nl.
        Pfw:      Measured friction and windage losses (W); 0 = estimate as 0.8% of P_nl.
        split:    NEMA class: "A", "B", "C", "D", "WR" or "custom".
        Xls_frac: Xls/Xk fraction — used only when split="custom".

    Returns:
        dict with same structure as estimate_params() — main keys:
            success, Rs, Rr, Xm, Xls, Xlr, Rfe,
            E1_nl, Xk, Rk, Pfe_3ph, I_mu, Pfw_used,
            split_used, Xls_frac, f_nl, f_lr.
        On error: {'success': False, 'error': <message>}.
    """
    try:
        # ── Input validation ───────────────────────────────────────────────
        if V_dc <= 0.0 or I_dc <= 0.0:
            return {"success": False, "error": "DC test: V_dc and I_dc must be positive."}
        if Vl_nl <= 0.0 or I_nl <= 0.0 or P_nl <= 0.0:
            return {"success": False, "error": "No-load test: Vl_nl, I_nl and P_nl must be positive."}
        if Vl_lr <= 0.0 or I_lr <= 0.0 or P_lr <= 0.0:
            return {"success": False, "error": "Locked-rotor test: Vl_lr, I_lr and P_lr must be positive."}
        if f_nl <= 0.0 or f_lr <= 0.0:
            return {"success": False, "error": "Test frequencies must be positive."}
        if Pfw < 0.0:
            return {"success": False, "error": "Friction and windage losses (Pfw) cannot be negative."}

        split_key = split if split in _IEEE_SPLIT_TABLE else "B"
        frac = Xls_frac if split_key == "custom" else _IEEE_SPLIT_TABLE[split_key]
        if not (0.05 <= frac <= 0.95):
            return {
                "success": False,
                "error": f"Xls/Xk fraction = {frac:.3f} is outside the interval [0.05; 0.95].",
            }

        # ── Step 1 — Stator resistance (DC Test, IEEE 112 Cl. 6.4) ────────
        # Y: two windings in series     → Rs_phase = (V_dc / I_dc) / 2
        # Δ: two in parallel with one in series → Rs_phase = (V_dc / I_dc) · 1.5
        if is_delta:
            Rs = (V_dc / I_dc) * 1.5
        else:
            Rs = (V_dc / I_dc) / 2.0

        if Rs <= 0.0:
            return {"success": False, "error": "Calculated Rs is not positive. Verify V_dc and I_dc."}

        # ── Step 2 — No-Load Test (IEEE 112-2017 Sec. 5.6) ─────────────────
        m     = 3                              # number of phases
        V1_nl = Vl_nl / math.sqrt(3.0)        # phase voltage (wye equivalent) — Eq. (40)
        S_nl  = m * V1_nl * I_nl
        # Q0 — no-load reactive power — Eq. (38)
        Q0 = math.sqrt(max(S_nl ** 2 - P_nl ** 2, 0.0))

        # Friction and windage losses — IEEE heuristic: 0.8% of P_nl when not provided
        Pfw_used = Pfw if Pfw > 0.0 else 0.008 * P_nl

        # Core loss Ph (total core loss, Sec. 5.6.6)
        P_joule_st_nl = m * Rs * I_nl ** 2
        Ph = P_nl - P_joule_st_nl - Pfw_used
        if Ph <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Ph (core loss) calculated ≤ 0 (Ph = {Ph:.2f} W). "
                    f"P_nl = {P_nl:.1f} W is insufficient to cover 3·Rs·I_nl² = {P_joule_st_nl:.1f} W "
                    f"+ Pfw = {Pfw_used:.1f} W."
                ),
            }

        # ── Step 3 — Locked-Rotor Test (IEEE 112-2017 Sec. 5.10.2–5.10.3) ─
        V1_lr = Vl_lr / math.sqrt(3.0)
        Zk    = V1_lr / I_lr
        Rk    = P_lr / (m * I_lr ** 2)

        if Rk >= Zk:
            return {
                "success": False,
                "error": (
                    f"Locked-rotor test: Rk = {Rk:.4f} Ω ≥ Zk = {Zk:.4f} Ω. "
                    "Verify P_lr, V_lr and I_lr — the power factor is inconsistent."
                ),
            }

        Xk_lr = math.sqrt(max(Zk ** 2 - Rk ** 2, 1e-6))
        # Linear frequency correction to f_nl — Eq. (43) and (46)
        Xk = Xk_lr * (f_nl / f_lr)

        # ── Step 4 — Rs/Rr separation and Xls/Xlr distribution (Eq. 44–46) ─
        Rr = Rk - Rs
        if Rr <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Rr = Rk − Rs = {Rr:.4f} Ω ≤ 0. "
                    f"Rs (DC test) = {Rs:.4f} Ω is greater than Rk (locked-rotor test) = {Rk:.4f} Ω. "
                    "Verify the measurements."
                ),
            }

        Xls = frac * Xk        # X1 — Eq. (43) with frac = X1/(X1+X2)
        Xlr = (1.0 - frac) * Xk  # X2 — Eq. (45)

        # QL — locked-rotor reactive power — Eq. (39)
        S_lr = m * V1_lr * I_lr
        QL   = math.sqrt(max(S_lr ** 2 - P_lr ** 2, 0.0))

        # ── Step 5 — IEEE 112 Eq. 41–49 iteration until 0.1% convergence ───
        # Eq. (41): Xm = m·V1²·Xm / (Q0 - m·I0²·X1·(X1+Xm)/Xm)
        # Rearranged for iteration: given X1 and ratio r = X1/Xm:
        #   Xm_new = (Q0 - m·I0²·X1·(1+r)) / (m·V1²/Xm_est - m·I0²·r)
        # Using the more stable direct form:
        # Xm iterated from initial estimate X1+Xm ≈ Q0/(m·I0²)
        X1 = Xls
        XM_plus_X1_init = Q0 / max(m * I_nl ** 2, 1e-12)
        Xm = max(XM_plus_X1_init - X1, 1e-3)

        E1_nl_0 = math.sqrt(max(V1_nl ** 2 - (Rs * I_nl) ** 2, 1e-6))
        E1_nl   = E1_nl_0

        for _iter in range(50):
            Xm_prev = Xm
            X1_prev = X1

            # Eq. (41) — Xm from Q0, I0, V1, X1
            denom_41 = Q0 - m * I_nl ** 2 * X1 * (X1 + Xm) / max(Xm, 1e-9)
            Xm_new = m * V1_nl ** 2 / max(denom_41, 1e-9)
            Xm_new = max(Xm_new, 1e-3)

            # Eq. (42) — X1L from QL, IL, V1L, X1, Xm
            ratio_1_M = X1 / max(Xm_new, 1e-9)
            numer_42  = QL - m * I_lr ** 2 * X1 * (1.0 + ratio_1_M)
            denom_42  = m * I_lr ** 2 * (1.0 + ratio_1_M) ** 2 - m * V1_lr ** 2 / max(Xm_new, 1e-9)
            # stable alternative: solve Eq (42) directly for X1L
            # X1L ≈ (QL/(m·IL²) - X1*(X1/Xm)) / (1 + X1/Xm)
            X1L = (QL / max(m * I_lr ** 2, 1e-12) - X1 * ratio_1_M) / max(1.0 + ratio_1_M, 1e-9)
            X1L = max(X1L, 1e-4)

            # Eq. (43) — scale to nominal frequency
            X1_new = X1L * (f_nl / f_lr)
            X1_new = max(X1_new, 1e-4)

            # Eq. (41) — recalculate Xm with updated X1
            denom_41b = Q0 - m * I_nl ** 2 * X1_new * (X1_new + Xm_new) / max(Xm_new, 1e-9)
            Xm_new2 = m * V1_nl ** 2 / max(denom_41b, 1e-9)
            Xm = max(Xm_new2, 1e-3)
            X1 = X1_new

            # Convergence criterion 0.1% — Sec. 5.10.3.2 step 5
            if (abs(Xm - Xm_prev) / max(abs(Xm_prev), 1e-9) < 0.001 and
                    abs(X1 - X1_prev) / max(abs(X1_prev), 1e-9) < 0.001):
                break

        # Final Xls and Xlr after convergence
        Xls = X1
        Xlr = Xk * (f_nl / f_lr) - Xls  # X2 = Xk_total - X1, Eq. (45)/(46)
        Xlr = max(Xlr, 1e-4)

        # Eq. (47) — Gfe = Ph·Xm² / (m·V1²) → Rfe = 1/Gfe
        Gfe = Ph * Xm ** 2 / max(m * V1_nl ** 2 * Xm ** 2, 1e-12)
        # simplified correct form: Gfe = Ph / (m · E1²)
        # E1 iterated from current components:
        # Use E1 ≈ V1 (open-circuit approximation of the shunt branch)
        E1_nl = math.sqrt(max(V1_nl ** 2 - (Rs * I_nl) ** 2, 1e-6))
        Gfe   = Ph / max(m * E1_nl ** 2, 1e-12)
        Rfe   = 1.0 / max(Gfe, 1e-12)

        # Eq. (48) — Bm = 1/Xm
        Bm  = 1.0 / max(Xm, 1e-9)
        Ife = Gfe * E1_nl
        Imu = Bm  * E1_nl
        I_mu_check = math.sqrt(Ife ** 2 + Imu ** 2)

        # Eq. (49) — R2 (Rr) with Gfe and Bm correction
        # R2 = P_lr/(m·IL²) - Rs - (Xk²·Gfe)/(1+...) — robust approximate form
        # Use: Rr = Rk - Rs (already calculated; consistent with Eq. 49 for Xm >> Xk)
        # For machines with small Xm, apply full Eq. 49:
        ratio_fe = Gfe * Xk
        Rr_full = (P_lr / max(m * I_lr ** 2, 1e-12) - Rs
                   - Xk ** 2 * Gfe / max(1.0 + (Xk * Gfe) ** 2, 1e-9))
        Rr = max(Rr_full, Rk - Rs)  # fallback to Rk-Rs if Eq.49 yields negative
        if Rr <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Rr ≤ 0 after Eq. 49 (Rr = {Rr:.4f} Ω). "
                    f"Rs = {Rs:.4f} Ω, Rk = {Rk:.4f} Ω. Verify measurements."
                ),
            }

        Pfe_3ph = Ph  # alias for compatibility with existing return

        return {
            "success": True,
            "Rs":            round(Rs,      5),
            "Rr":            round(Rr,      5),
            "Xm":            round(Xm,      4),
            "Xls":           round(Xls,     5),
            "Xlr":           round(Xlr,     5),
            "Rfe":           round(Rfe,     2),
            # test traceability — IEEE 112 Eq. 38–49
            "E1_nl":         round(E1_nl,   3),
            "E1_nl_0":       round(E1_nl_0, 3),
            "E1_nl_1":       round(E1_nl,   3),  # converged — same as E1_nl
            "Xk":            round(Xk,      4),
            "Xk_lr":         round(Xk_lr,   4),
            "Rk":            round(Rk,      5),
            "Zk":            round(Zk,      4),
            "Pfe_3ph":       round(Pfe_3ph, 2),
            "P_joule_st_nl": round(P_joule_st_nl, 2),
            "I_mu":          round(Imu,     4),
            "I_fe":          round(Ife,     4),
            "Pfw_used":      round(Pfw_used, 2),
            "S_nl":          round(S_nl,    2),
            "Q_nl":          round(Q0,      2),
            "Vf_nl":         round(V1_nl,   3),
            "Vf_lr":         round(V1_lr,   3),
            "split_used":    split_key,
            "Xls_frac":      round(frac,    3),
            "f_nl":          f_nl,
            "f_lr":          f_lr,
        }

    except ZeroDivisionError as exc:
        return {"success": False, "error": f"Division by zero during IEEE estimation: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Unexpected error in IEEE estimator: {exc}"}
