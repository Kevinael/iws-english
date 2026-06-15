# -*- coding: utf-8 -*-
"""
sim_diagnostics.py
==================
Automatic post-simulation diagnostic module — analyses ODE states and
generates physics-based insights classified by severity.

Responsibilities:
  - Detect steady state from the state vectors
  - Check torque balance, temperature, voltage unbalance, and speed anomalies
  - Return a list of Insight objects (info / warning / error)

Relationships:
  Imported by : ui_components.sim_results
  Imports     : (math, numpy only)

Extending:
  - To add a new diagnostic rule, create a _check_X function and register it
    in the orchestrator's check list.
"""

from __future__ import annotations
import math
import numpy as np
from core.constants import (
    SPEED_RECOVERY_THRESHOLD,
    SLIP_OVERLOAD_ERROR, SLIP_OVERLOAD_WARN, SLIP_UNDERLOAD,
    SLIP_GEN_WARN, SLIP_GEN_ERROR,
    VUF_DETECTABLE_MIN_PCT, VUF_ERROR_PCT, VUF_WARN_HIGH_PCT, VUF_WARN_LOW_PCT,
    BBAR_ALPHA_ERROR, BBAR_ALPHA_WARN,
    SAG_ERROR_PCT, SAG_WARN_PCT,
    RELAY_CLASS_10_S, RELAY_CLASS_20_S, RELAY_CLASS_30_S,
)


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────

class Insight:
    """Container for a diagnostic insight."""
    LEVELS = ("info", "warning", "error")

    def __init__(self, level: str, title: str, body: str) -> None:
        if level not in self.LEVELS:
            raise ValueError(f"level must be one of {self.LEVELS}")
        self.level = level
        self.title = title
        self.body  = body

    def __repr__(self) -> str:
        return f"Insight({self.level!r}, {self.title!r})"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_steady_state_reached(
    wr_arr: np.ndarray,
    t_arr: np.ndarray,
    ss_start: int,
    threshold_rad_s2: float = 0.5,
) -> bool:
    """Checks whether steady state has been reached.

    Criterion: the mean rate of change of wr in the steady-state window
    (|dwr/dt|_mean) must be less than threshold_rad_s2 (rad/s²).
    """
    if ss_start >= len(wr_arr) - 2:
        return False
    sl   = slice(ss_start, None)
    dwr  = np.diff(wr_arr[sl])
    dt   = np.diff(t_arr[sl])
    dt   = np.where(dt > 0, dt, 1e-9)
    accel_mean = float(np.mean(np.abs(dwr / dt)))
    return accel_mean < threshold_rad_s2


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def generate_insights(
    res: dict,
    mp,
    load_torque: float,
    tmax: float,
    exp_type: str = "dol",
    exp_config: dict | None = None,
) -> list[Insight]:
    """Analyses the solver result and returns a list of Insight objects.

    Args:
        res:        Dict returned by run_simulation() (includes keys from
                    _compute_steady_state: Te_ss, n_ss, wr_ss, s, _ss_start, …).
        mp:         MachineParams — machine parameters (B, p, wb, …).
        load_torque: Nominal load torque applied (N·m). May be 0
                    for experiments without a defined load (shutdown, generator).
        tmax:       Total simulation duration (s).
        exp_type:   Experiment type (dol, yd, comp, soft, …).
        exp_config: Experiment configuration dict (input parameters).

    Returns:
        List of Insight objects sorted by descending severity.
    """
    insights: list[Insight] = []
    cfg = exp_config or {}

    # ── basic arrays ─────────────────────────────────────────────────────
    t_arr   = np.asarray(res.get("t",  []), dtype=float)
    wr_arr  = np.asarray(res.get("wr", []), dtype=float)
    Te_arr  = np.asarray(res.get("Te", []), dtype=float)
    n_arr   = np.asarray(res.get("n",  []), dtype=float)

    if len(t_arr) < 10:
        return insights

    ss_start = int(res.get("_ss_start", 0))
    n_ss     = float(res.get("n_ss",  0.0))
    Te_ss    = float(res.get("Te_ss", 0.0))
    wr_ss    = float(res.get("wr_ss", 0.0))
    s_ss     = float(res.get("s",     0.0))

    # mechanical synchronous speed (rad/s)
    ws_mec = mp.wb / (mp.p / 2.0)
    n_sync = ws_mec * 60.0 / (2.0 * math.pi)

    # ── steady-state check ────────────────────────────────────────────────
    steady = _is_steady_state_reached(wr_arr, t_arr, ss_start)

    if not steady:
        insights.append(Insight(
            level="warning",
            title="Mechanical Steady State Not Reached",
            body=(
                f"The configured simulation time (tmax = {tmax:.2f} s) was insufficient "
                f"for the rotor to reach mechanical stability. The angular velocity "
                f"derivative was still significant at the final instant. It is recommended "
                f"to increase tmax or to verify whether the load torque exceeds the maximum "
                f"motor torque (risk of rotor stall)."
            ),
        ))
        # without steady state, torque balance and slip rules are invalid
        # acceleration margin is still analysed during the transient
        _check_acceleration_margin(insights, Te_arr, load_torque, n_sync, mp)
        return _sort_insights(insights)

    # ── Rule 1: Torque balance — friction and ventilation ─────────────────
    if exp_type not in ("shutdown", "gerador") and load_torque >= 0:
        T_atrito = mp.B * wr_ss                      # N·m — viscous torque at steady state
        T_balanco = Te_ss - load_torque              # should ≈ T_atrito (equilibrium)
        erro_rel  = abs(T_balanco - T_atrito) / max(abs(Te_ss), 1e-3)

        if abs(Te_ss) > 0.01:
            insights.append(Insight(
                level="info",
                title="Steady-State Torque Balance",
                body=(
                    f"At steady state (n = {n_ss:.1f} RPM), the equation of motion "
                    f"J·(dω/dt) = Tₑ − T_L − B·ωₘ yields dω/dt = 0, confirming "
                    f"dynamic equilibrium. The steady-state electromagnetic torque "
                    f"(Tₑ = {Te_ss:.3f} N·m) exceeds the load torque "
                    f"(T_L = {load_torque:.3f} N·m) exactly by the viscous friction "
                    f"and windage term B·ωₘ = {T_atrito:.4f} N·m "
                    f"(B = {mp.B:.6f} N·m·s/rad). The difference Tₑ − T_L − B·ωₘ = "
                    f"{Te_ss - load_torque - T_atrito:.6f} N·m is numerically zero, "
                    f"indicating that the integrator converged correctly to the "
                    f"steady-state operating point."
                ),
            ))

    # ── Rule 2: Torque margin (acceleration analysis) ─────────────────────
    _check_acceleration_margin(insights, Te_arr, load_torque, n_sync, mp)

    # ── Rule 3: Overload and extreme slip diagnostics ──────────────────────
    if exp_type not in ("shutdown", "gerador") and steady:
        _check_slip_overload(insights, s_ss, n_ss, n_sync, Te_ss, mp)

    # ── Rule 4: Underload diagnostics ─────────────────────────────────────
    if exp_type not in ("shutdown", "gerador") and load_torque > 0 and steady:
        _check_underload(insights, s_ss, mp)

    # ── Rule 5: Broken bar ────────────────────────────────────────────────
    _check_broken_bar(insights, res, s_ss, mp)

    # ── Rule 6: Voltage imbalance (NEMA MG-1) ─────────────────────────────
    _check_voltage_imbalance(insights, res, mp, cfg)

    # ── Rule 7: Voltage sag ───────────────────────────────────────────────
    if exp_type == "voltage_sag":
        _check_voltage_sag(insights, res, t_arr, Te_arr, wr_arr, cfg, mp, n_sync)

    # ── Rule 8: Prolonged start-up time ───────────────────────────────────
    _STARTUP_TYPES = ("dol", "yd", "comp", "soft")
    if exp_type in _STARTUP_TYPES and load_torque > 0:
        _check_startup_time(insights, t_arr, wr_arr, Te_arr, load_torque, ws_mec, mp, cfg)

    # ── Rules 9–11: Generator-mode specific diagnostics ───────────────────
    if exp_type == "gerador" and steady:
        _check_generator_mode(insights, res, s_ss, n_ss, n_sync, Te_ss, ws_mec, mp, cfg)

    return _sort_insights(insights)


# ─────────────────────────────────────────────────────────────────────────────
# Individual rules
# ─────────────────────────────────────────────────────────────────────────────

def _check_acceleration_margin(
    insights: list[Insight],
    Te_arr: np.ndarray,
    load_torque: float,
    n_sync: float,
    mp,
) -> None:
    """Rule 2 — Torque margin during the start-up transient."""
    if len(Te_arr) == 0:
        return

    Te_max = float(np.nanmax(Te_arr))
    if Te_max <= 0 or load_torque <= 0:
        return

    ratio = Te_max / load_torque

    if ratio >= 2.0:
        insights.append(Insight(
            level="info",
            title="Ample Acceleration Torque Margin",
            body=(
                f"The peak electromagnetic torque during the start-up transient "
                f"(Tₑ_max = {Te_max:.2f} N·m) is {ratio:.1f}× the load torque "
                f"(T_L = {load_torque:.2f} N·m). The condition J·(dω/dt) = Tₑ − T_L − B·ω > 0 "
                f"was fully satisfied, ensuring positive rotor acceleration throughout "
                f"the entire start-up trajectory. The motor exhibits an ample pull-out "
                f"safety margin, characteristic of a safe start."
            ),
        ))
    elif ratio >= 1.2:
        insights.append(Insight(
            level="warning",
            title="Reduced Torque Margin — Moderate Start",
            body=(
                f"The peak torque (Tₑ_max = {Te_max:.2f} N·m) was only {ratio:.2f}× the "
                f"load torque (T_L = {load_torque:.2f} N·m). The acceleration margin "
                f"J·α = Tₑ − T_L − B·ωₘ was positive but narrow. "
                f"Supply voltage disturbances or load variations during start-up may "
                f"result in insufficient acceleration and a prolonged start time, "
                f"approaching the thermal relay trip threshold."
            ),
        ))
    else:
        insights.append(Insight(
            level="error",
            title="ROTOR STALL RISK — Heavy Start",
            body=(
                f"The peak electromagnetic torque (Tₑ_max = {Te_max:.2f} N·m) was less than "
                f"1.2× the load torque (T_L = {load_torque:.2f} N·m), yielding "
                f"ratio = {ratio:.2f}. The acceleration equation J·(dω/dt) = Tₑ − T_L was "
                f"marginally positive or negative along part of the trajectory, characterising "
                f"a heavy start. The rotor operated near the pull-out point, "
                f"with imminent risk of stall. Verify that the load is compatible with "
                f"the motor rating, or adopt a soft-starter or star-delta starting method."
            ),
        ))


def _check_slip_overload(
    insights: list[Insight],
    s_ss: float,
    n_ss: float,
    n_sync: float,
    Te_ss: float,
    mp,
) -> None:
    """Rule 3 — Extreme slip as an overload indicator."""
    if s_ss > SLIP_OVERLOAD_ERROR:
        insights.append(Insight(
            level="error",
            title="SEVERE OVERLOAD — Critical Slip",
            body=(
                f"The steady-state slip is s = {s_ss*100:.2f}%, "
                f"well above the typical nominal value for NEMA B motors (1–3%). "
                f"To induce the demanded torque (Te_ss = {Te_ss:.2f} N·m) at this "
                f"speed (n = {n_ss:.1f} RPM vs. synchronous n_s = {n_sync:.1f} RPM), "
                f"the rotating magnetic field induced excessively high rotor currents "
                f"via Faraday's law (Eᵣ proportional to s·ωₛ·Ψ). "
                f"This results in disproportionate rotor Joule losses P_Joule_r = s·P_ag, "
                f"accelerated winding heating and imminent risk of thermal overload relay "
                f"actuation (IEC 60947-4-1). "
                f"Review the motor sizing for this load."
            ),
        ))
    elif s_ss > SLIP_OVERLOAD_WARN:
        insights.append(Insight(
            level="warning",
            title="High Slip — Operation Outside Nominal Zone",
            body=(
                f"The steady-state slip is s = {s_ss*100:.2f}%, above the "
                f"typical design value (< 5% for general-purpose motors). "
                f"The motor operates outside the maximum-efficiency region of the Te × n curve. "
                f"Rotor Joule losses (P_Joule_r = s·P_ag) are elevated, "
                f"reducing efficiency and increasing winding temperature. "
                f"Consider a higher-rated motor or a reduction in mechanical load."
            ),
        ))
    elif s_ss < 0:
        # generator operation (should not enter here, but extra protection)
        pass
    elif s_ss < 0.001 and Te_ss > 0:
        insights.append(Insight(
            level="info",
            title="High-Efficiency Operation",
            body=(
                f"The steady-state slip is s = {s_ss*100:.3f}%, indicating operation "
                f"close to the synchronous point. Rotor Joule losses "
                f"(P_Joule_r = s·P_ag) are minimal, characteristic of "
                f"high-efficiency operation. This behaviour is expected for premium "
                f"efficiency motors (IE3/IE4) or under light-load conditions."
            ),
        ))


def _check_underload(
    insights: list[Insight],
    s_ss: float,
    mp,
) -> None:
    """Rule 4 — Underload operation (low load factor)."""
    if 0 < s_ss < SLIP_UNDERLOAD:
        insights.append(Insight(
            level="warning",
            title="Motor Underloaded — Degraded Power Factor",
            body=(
                f"The slip s = {s_ss*100:.3f}% indicates that the motor is operating at "
                f"a load well below its rated power. Under underload conditions, the "
                f"magnetising current (Iₘ = E₁/Xₘ) remains practically constant and "
                f"represents a high fraction of the total current, resulting in "
                f"a low power factor and reduced efficiency. "
                f"Consider replacing the motor with a lower-rated unit to operate "
                f"closer to the design point."
            ),
        ))


def _check_broken_bar(
    insights: list[Insight],
    res: dict,
    s_ss: float,
    mp,
) -> None:
    """Rule 5 — Automatic broken-bar detection via severity and MCSA sidebands."""
    alpha = float(res.get("_broken_bar_severity", 0.0))
    if alpha <= 0:
        return

    f_fund = getattr(mp, "f", 60.0)
    sb_lo  = f_fund * (1.0 - 2.0 * abs(s_ss))
    sb_hi  = f_fund * (1.0 + 2.0 * abs(s_ss))

    if alpha >= BBAR_ALPHA_ERROR:
        level = "error"
        severidade_txt = f"severe (α = {alpha:.2f})"
    elif alpha >= BBAR_ALPHA_WARN:
        level = "warning"
        severidade_txt = f"moderate (α = {alpha:.2f})"
    else:
        level = "warning"
        severidade_txt = f"incipient (α = {alpha:.2f})"

    insights.append(Insight(
        level=level,
        title="Broken Bar Fault Detected — MCSA",
        body=(
            f"The simulation was executed with rotor resistance asymmetry "
            f"(severity: {severidade_txt}). By the MCSA (Motor Current Signature "
            f"Analysis) method, broken bars imprint sideband components on the stator "
            f"current at frequencies (1 ± 2s)·f: "
            f"f₋ = {sb_lo:.2f} Hz and f₊ = {sb_hi:.2f} Hz "
            f"(s = {s_ss*100:.2f}%, f = {f_fund:.1f} Hz). "
            f"Inspect the FFT spectrum of i_as in the Diagnostics tab and verify the "
            f"relative amplitude of the sidebands with respect to the fundamental. "
            f"Amplitudes above −40 dB indicate that intervention is required."
        ),
    ))


def _check_voltage_imbalance(
    insights: list[Insight],
    res: dict,
    mp,
    cfg: dict,
) -> None:
    """Rule 6 — Voltage imbalance via NEMA MG-1 (symmetrical components method)."""
    Va_rms = float(res.get("Va_rms", 0.0))
    Vb_rms = float(res.get("Vb_rms", 0.0))
    Vc_rms = float(res.get("Vc_rms", 0.0))

    if Va_rms <= 0 or Vb_rms <= 0 or Vc_rms <= 0:
        return

    # NEMA MG-1 method: VUF = max_deviation_from_mean / mean × 100%
    v_mean = (Va_rms + Vb_rms + Vc_rms) / 3.0
    if v_mean < 1e-6:
        return
    vuf = max(abs(Va_rms - v_mean), abs(Vb_rms - v_mean), abs(Vc_rms - v_mean)) / v_mean * 100.0

    # Diagnostic is only issued if imbalance is detectable (> VUF_DETECTABLE_MIN_PCT)
    if vuf < VUF_DETECTABLE_MIN_PCT:
        return

    if vuf > VUF_ERROR_PCT:
        level = "error"
        impacto = "imbalance current increase above 25% of nominal and severe overheating"
    elif vuf > VUF_WARN_HIGH_PCT:
        level = "warning"
        impacto = "efficiency reduction and winding temperature increase (NEMA MG-1 §14.35)"
    elif vuf > VUF_WARN_LOW_PCT:
        level = "warning"
        impacto = "operation in alert zone; monitoring recommended"
    else:
        level = "info"
        impacto = "imbalance below intervention limit (NEMA MG-1: 1%)"

    insights.append(Insight(
        level=level,
        title=f"Voltage Imbalance — VUF = {vuf:.2f}%",
        body=(
            f"The voltage imbalance factor (NEMA MG-1) calculated from the "
            f"steady-state phase voltages is VUF = {vuf:.2f}% "
            f"(Va = {Va_rms:.2f} V, Vb = {Vb_rms:.2f} V, Vc = {Vc_rms:.2f} V; "
            f"mean = {v_mean:.2f} V). "
            f"Consequence: {impacto}. "
            f"NEMA MG-1 recommends derating of nominal power for "
            f"operation with imbalance > 1%."
        ),
    ))


def _check_voltage_sag(
    insights: list[Insight],
    res: dict,
    t_arr: np.ndarray,
    Te_arr: np.ndarray,
    wr_arr: np.ndarray,
    cfg: dict,
    mp,
    n_sync: float,
) -> None:
    """Rule 7 — Impact of voltage sag on torque and speed."""
    sag_mag   = float(cfg.get("sag_magnitude",   cfg.get("v_sag",    1.0)))
    t_sag_ini = float(cfg.get("t_start_sag",     cfg.get("t_sag",    0.0)))
    t_sag_dur = float(cfg.get("t_duration_sag",  cfg.get("t_dur_sag", 0.0)))

    if sag_mag >= 1.0 or t_sag_dur <= 0:
        return

    sag_depth_pct = (1.0 - sag_mag) * 100.0
    t_sag_fim = t_sag_ini + t_sag_dur

    # window during the sag
    mask_sag = (t_arr >= t_sag_ini) & (t_arr <= t_sag_fim)
    if not np.any(mask_sag):
        return

    Te_sag_min  = float(np.min(Te_arr[mask_sag]))
    wr_sag_min  = float(np.min(wr_arr[mask_sag]))
    n_sag_min   = wr_sag_min * 60.0 / (2.0 * math.pi)
    speed_drop  = (n_sync - n_sag_min) / n_sync * 100.0  # % drop relative to n_sync

    # post-recovery window (last 20% of remaining time)
    mask_post = t_arr > t_sag_fim
    recuperou = False
    if np.any(mask_post):
        wr_post = wr_arr[mask_post]
        # considered recovered if wr returns to > 90% of pre-sag wr_ss
        wr_ss_pre = float(res.get("wr_ss", 0.0))
        if wr_ss_pre > 0:
            recuperou = float(np.mean(wr_post[-max(1, len(wr_post)//5):])) > SPEED_RECOVERY_THRESHOLD * wr_ss_pre

    # Level: torque drops quadratically with voltage (Te ∝ V²)
    # 20% sag → Te drops ~36%; 50% sag → Te drops ~75%
    te_reducao_teorica = (1.0 - sag_mag**2) * 100.0

    if sag_depth_pct >= SAG_ERROR_PCT or Te_sag_min < 0:
        level = "error"
    elif sag_depth_pct >= SAG_WARN_PCT:
        level = "warning"
    else:
        level = "info"

    recuperacao_txt = "The motor recovered after voltage restoration." if recuperou \
        else "The motor DID NOT return to steady-state speed after voltage restoration — verify stability."

    insights.append(Insight(
        level=level,
        title=f"Voltage Sag — {sag_depth_pct:.1f}% Drop for {t_sag_dur:.3f} s",
        body=(
            f"The configured voltage sag (sag = {sag_mag:.2f} p.u., "
            f"duration = {t_sag_dur*1000:.0f} ms) caused the electromagnetic torque "
            f"to drop to Te_min = {Te_sag_min:.2f} N·m during the event "
            f"(theoretical reduction ≈ {te_reducao_teorica:.1f}% since Te ∝ V²). "
            f"The rotor speed dropped to n_min = {n_sag_min:.1f} RPM "
            f"({speed_drop:.1f}% below synchronous speed). "
            f"{recuperacao_txt} "
            f"Sags above 20% lasting more than 100 ms may cause undervoltage trip "
            f"(ANSI 27) or loss of synchronism in sensitive loads."
        ),
    ))


def _check_startup_time(
    insights: list[Insight],
    t_arr: np.ndarray,
    wr_arr: np.ndarray,
    Te_arr: np.ndarray,
    load_torque: float,
    ws_mec: float,
    mp,
    cfg: dict | None = None,
) -> None:
    """Rule 8 — Start-up time: measures t to 95% of ωs and evaluates thermal risk."""
    target_wr = 0.95 * ws_mec
    mask_reach = wr_arr >= target_wr
    if not np.any(mask_reach):
        return

    idx_reach  = int(np.argmax(mask_reach))
    t_start_pt = float(t_arr[idx_reach])

    # Expected minimum start-up time: J·ωs / (Te_mean − T_L)
    # Uses only the no-load acceleration segment (before t_carga, if defined),
    # since load_torque is applied after t_carga — including it before distorts Te_mean_accel.
    J = getattr(mp, "J", None)
    t_carga = float((cfg or {}).get("t_carga", 0.0))
    if t_carga > 0 and t_carga < t_start_pt:
        # no-load start: acceleration occurs without load up to t_carga
        idx_tc = int(np.searchsorted(t_arr, t_carga))
        Te_accel_slice = Te_arr[:idx_tc] if idx_tc > 0 else Te_arr[:idx_reach]
        tl_accel = 0.0  # load not yet applied in this segment
    else:
        Te_accel_slice = Te_arr[:idx_reach]
        tl_accel = load_torque

    # Filter initial negative spikes (energisation transient)
    Te_accel_slice = Te_accel_slice[Te_accel_slice > 0] if len(Te_accel_slice) > 0 else Te_accel_slice
    Te_mean_accel  = float(np.mean(Te_accel_slice)) if len(Te_accel_slice) > 0 else 0.0

    if J and J > 0 and Te_mean_accel > tl_accel:
        t_esperado = J * ws_mec / (Te_mean_accel - tl_accel)
    else:
        t_esperado = None

    # NEMA limits: Trip Class 10 ≤ 10s, Class 20 ≤ 20s, Class 30 ≤ 30s
    if t_start_pt > RELAY_CLASS_30_S:
        level, trip_class = "error",   "Class 30 exceeded (> 30 s)"
    elif t_start_pt > RELAY_CLASS_20_S:
        level, trip_class = "warning", "Class 30 (20–30 s)"
    elif t_start_pt > RELAY_CLASS_10_S:
        level, trip_class = "warning", "Class 20 (10–20 s)"
    else:
        level, trip_class = "info",    "Class 10 (< 10 s)"

    esperado_txt = (
        f" The estimated time from the inertia balance (J·ωs / (Te_mean − T_L)) "
        f"is {t_esperado:.2f} s."
        if t_esperado is not None else ""
    )

    insights.append(Insight(
        level=level,
        title=f"Start-up Time: {t_start_pt:.2f} s — {trip_class}",
        body=(
            f"The rotor reached 95% of synchronous speed (ωr = {0.95*ws_mec:.1f} rad/s) "
            f"at t = {t_start_pt:.2f} s from the energisation instant.{esperado_txt} "
            f"NEMA ICS 2 reference: Trip Class 10 overload relays actuate in ≤ 10 s, "
            f"Class 20 in ≤ 20 s and Class 30 in ≤ 30 s with full starting current. "
            f"Prolonged starts accumulate thermal energy I²t in the windings — "
            f"verify compatibility with the Trip Class of the installed relay."
        ),
    ))


def _check_generator_mode(
    insights: list[Insight],
    res: dict,
    s_ss: float,
    n_ss: float,
    n_sync: float,
    Te_ss: float,
    ws_mec: float,
    mp,
    cfg: dict,
) -> None:
    """Rules 9–11 — Specific diagnostics for induction generator operation."""

    # ── Rule 9: Negative slip verification ───────────────────────────────
    if s_ss >= 0:
        insights.append(Insight(
            level="error",
            title="Generator: Rotor Did Not Exceed Synchronous Speed",
            body=(
                f"For induction generator operation, the rotor must rotate above "
                f"synchronous speed (s < 0). The calculated slip is s = {s_ss*100:.2f}%, "
                f"indicating that the rotor is still operating in motor mode (s ≥ 0). "
                f"Verify whether the prime mover torque (Tl_mec) is sufficient to "
                f"accelerate the rotor beyond n_s = {n_sync:.1f} RPM, or whether the "
                f"application instant (t_2) was reached within the simulation time."
            ),
        ))
        return

    # ── Rule 10: Stability margin — excessive negative slip ───────────────
    # Practical limit: |s| > 10% → unstable operation / high currents
    abs_s = abs(s_ss)
    n_wr  = n_ss  # already in RPM

    if abs_s > SLIP_GEN_ERROR:
        insights.append(Insight(
            level="error",
            title=f"Generator: Critical Negative Slip — s = {s_ss*100:.2f}%",
            body=(
                f"The steady-state negative slip is s = {s_ss*100:.2f}% "
                f"(n = {n_wr:.1f} RPM, n_s = {n_sync:.1f} RPM). "
                f"Above |s| > 10%, the rotor currents induced by Faraday's law "
                f"(E_r ∝ |s|·ωs·Ψ) become excessive, increasing rotor Joule losses "
                f"(P_Joule_r = |s|·P_gap) and winding heating. "
                f"The generator pull-out point is also approached, risking instability. "
                f"Reduce the prime mover torque or verify the machine sizing."
            ),
        ))
    elif abs_s > SLIP_GEN_WARN:
        insights.append(Insight(
            level="warning",
            title=f"Generator: High Negative Slip — s = {s_ss*100:.2f}%",
            body=(
                f"The steady-state negative slip is s = {s_ss*100:.2f}% "
                f"(n = {n_wr:.1f} RPM vs. n_s = {n_sync:.1f} RPM). "
                f"Values above |s| = 5% indicate operation outside the maximum-efficiency "
                f"region. Rotor losses grow proportionally to |s|·P_gap. "
                f"Adjust the prime mover operating point to maintain |s| ≤ 3–5%."
            ),
        ))
    else:
        insights.append(Insight(
            level="info",
            title=f"Generator: Stable Operation — s = {s_ss*100:.2f}%",
            body=(
                f"The induction generator operates at stable steady state with slip "
                f"s = {s_ss*100:.2f}% (n = {n_wr:.1f} RPM, n_s = {n_sync:.1f} RPM). "
                f"The rotor rotates {abs(n_wr - n_sync):.1f} RPM above synchronous speed, "
                f"within the nominal operating range (|s| ≤ 5%)."
            ),
        ))

    # ── Rule 11: Power balance — generator efficiency ─────────────────────
    P_mec = float(res.get("P_mec",  0.0))   # mechanical input power (W) — negative in solver
    P_gap = float(res.get("P_gap",  0.0))   # air-gap power (W)
    P_out = float(res.get("P_out",  0.0))   # generated electrical power (W)
    eta   = float(res.get("eta",    0.0))   # efficiency (%)
    P_cu_r = float(res.get("P_cu_r", 0.0)) # rotor Joule losses (W)

    P_mec_abs = abs(P_mec)
    P_out_abs = abs(P_out)

    if P_mec_abs < 1e-3:
        return

    if eta > 0:
        if eta >= 85.0:
            nivel_eta, texto_eta = "info", "adequate efficiency for an induction generator"
        elif eta >= 70.0:
            nivel_eta, texto_eta = "warning", "efficiency below expected; verify losses"
        else:
            nivel_eta, texto_eta = "error", "low efficiency — dominant losses; review operation"

        insights.append(Insight(
            level=nivel_eta,
            title=f"Generator: Power Balance — η = {eta:.1f}%",
            body=(
                f"Steady-state power flow (generator convention): "
                f"P_mec (prime mover) = {P_mec_abs:.1f} W → air-gap P_gap = {abs(P_gap):.1f} W "
                f"(rotor losses P_cu_r = {P_cu_r:.1f} W = |s|·P_gap) → "
                f"generated P_electrical = {P_out_abs:.1f} W. "
                f"Electromechanical efficiency η = {eta:.1f}% — {texto_eta}. "
                f"The induction generator requires an external reactive power source (capacitor "
                f"bank or grid) to supply the magnetising current."
            ),
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Sorting
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}

def _sort_insights(insights: list[Insight]) -> list[Insight]:
    return sorted(insights, key=lambda x: _LEVEL_ORDER[x.level])
