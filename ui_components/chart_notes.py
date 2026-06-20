# -*- coding: utf-8 -*-
"""
chart_notes.py
==============
Contextual technical notes displayed below MIT simulation charts.

Responsibilities:
  - Emit an st.caption() note relevant to a given variable key and experiment context.

Relationships:
  Imported by : ui_components.tim_results
  Imports     : streamlit, numpy, core.tim.facade
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import streamlit as st

from core.tim.facade import MachineParams


@dataclass(frozen=True)
class MITNoteCtx:
    """Immutable context bundle passed to emit_mit_note()."""
    exp_type:  str
    exp_config: dict[str, Any]
    bb_sev:    float    # broken-bar severity α
    s_val:     float    # slip (signed)
    imbalance_on:  bool     # any voltage-unbalance / phase-fault flag active
    is_yd:     bool
    is_gen:    bool
    is_sd:     bool
    is_soft:   bool
    Tl_cfg:    float    # configured load torque
    Te_max:    float    # peak Te from simulation
    mp:        MachineParams


# ---------------------------------------------------------------------------
# Auxiliary note builders for entries with internal branching
# ---------------------------------------------------------------------------

def _note_te_soft(ctx: MITNoteCtx) -> str:
    if ctx.Te_max < ctx.Tl_cfg * 1.05 and ctx.Tl_cfg > 0:
        return (
            "**Soft-starter** — maximum starting torque is close to load torque. "
            "If $T_{e,\\max} < T_L$ the motor will not start. Consider increasing the initial "
            "voltage or reducing load during acceleration."
        )
    return (
        "**Soft-starter** — the voltage ramp smooths $T_e$ growth, "
        "eliminating the inrush peak of direct starting. Torque grows "
        "approximately proportionally to $V_s^2(t)$ until reaching $T_e = T_L + B\\,\\omega_r$ "
        "in steady state."
    )


def _note_te_sd(ctx: MITNoteCtx) -> str:
    _tau_r = ctx.mp.Lr / ctx.mp.Rr if ctx.mp.Rr > 0 else 0.0
    return (
        f"**Shutdown** — after voltage cut, air-gap flux decays with "
        f"time constant $\\tau_r = L_r/R_r$ = {_tau_r:.3f} s and $T_e$ rapidly drops to zero. "
        f"The rotor continues spinning by inertia, decelerating under $T_L$ and viscous friction $B$."
    )


def _note_va_imbalance(ctx: MITNoteCtx) -> str:
    cfg = ctx.exp_config
    _falta = any(cfg.get(k, 0) for k in ("phase_loss_a", "phase_loss_b", "phase_loss_c"))
    if _falta:
        return (
            "**Phase fault** — the open-phase voltage drops to zero at the terminals; "
            "the remaining phases maintain rated amplitude, imposing non-zero "
            "negative-sequence voltage $V_2$ on the stator."
        )
    return (
        "**Voltage unbalance** — unequal phase amplitudes indicate "
        "supply asymmetry. Decomposition into symmetric components "
        "reveals $V_2/V_1$ proportional to the degree of unbalance."
    )



# ---------------------------------------------------------------------------
# Condition predicates
# ---------------------------------------------------------------------------

def _bb(ctx: MITNoteCtx)       -> bool: return ctx.bb_sev > 0
def _imbalance(ctx: MITNoteCtx)    -> bool: return ctx.imbalance_on
def _yd(ctx: MITNoteCtx)       -> bool: return ctx.is_yd
def _autotrafo(ctx: MITNoteCtx)-> bool: return ctx.exp_type == "autotrafo"
def _soft(ctx: MITNoteCtx)     -> bool: return ctx.is_soft
def _pulse(ctx: MITNoteCtx)    -> bool: return ctx.exp_type == "load_pulse"
def _gen(ctx: MITNoteCtx)      -> bool: return ctx.is_gen
def _sd(ctx: MITNoteCtx)       -> bool: return ctx.is_sd
def _vsag(ctx: MITNoteCtx)     -> bool: return ctx.exp_type == "voltage_sag"
def _dol(ctx: MITNoteCtx)      -> bool: return ctx.exp_type == "dol"


# ---------------------------------------------------------------------------
# Dispatch table
# Each entry: (predicate, text_builder)
# text_builder receives ctx and returns str
# ---------------------------------------------------------------------------

_NoteEntry = tuple[Callable[[MITNoteCtx], bool], Callable[[MITNoteCtx], str]]

_NOTES: dict[str, list[_NoteEntry]] = {
    "Te": [
        (_bb,       lambda ctx: (
            f"**Broken bar (α={ctx.bb_sev:.2f})** — $T_e$ oscillates at "
            f"{2.0 * abs(ctx.s_val) * ctx.mp.f:.1f} Hz "
            f"($2sf$). Load torque $T_L$ remains essentially constant: "
            f"inertia $J$ damps speed oscillations, making $\\Delta T_L \\ll \\Delta T_e$. "
            f"The spectral signature appears in current as sidebands at $(1\\pm2s)f_e$ Hz — "
            f"see the **Diagnostics & Faults** tab."
        )),
        (_imbalance,    lambda _: (
            "**Voltage unbalance / Phase fault** — the negative-sequence component "
            "establishes a rotating field opposing $\\omega_s$, with effective slip "
            "$s^- = 2 - s^+$, generating pulsating braking torque at frequency $2f$ and reducing "
            "mean $T_e$ relative to balanced operation."
        )),
        (_yd,       lambda _: (
            "**Star-Delta Starting (Y-$\\Delta$)** — at switching, the phase voltage jumps "
            "from $V_n/\\sqrt{3}$ to $V_n$, imposing an excitation step over the residual flux "
            "in the air gap. The second $T_e$ peak decays with time constant $\\tau_s = L_s/R_s$ to "
            "the new steady state $T_e = T_L + B\\,\\omega_r$."
        )),
        (_autotrafo, lambda ctx: (
            f"**Autotransformer Starting (tap $k$ = {float(ctx.exp_config.get('voltage_ratio', 0.5)):.0%})** — reduced voltage "
            f"$V_s = k\\,V_n$ attenuates $T_e$ by factor $k^2 = {float(ctx.exp_config.get('voltage_ratio', 0.5))**2:.2f}$, reducing the "
            f"inrush peak without eliminating transient oscillations. At switching to full "
            f"voltage a second transient occurs analogous to Y-$\\Delta$ mode."
        )),
        (_soft,     _note_te_soft),
        (_pulse,    lambda _: (
            "**Load Pulse** — sudden insertion of $T_L$ causes transient drop in "
            "$\\omega_r$ and increase in slip $s$. Electromagnetic torque $T_e$ "
            "rises in response, with oscillations damped by time constant $\\tau_m = J/B$, "
            "until equaling $T_L + B\\,\\omega_r$ at the new operating point."
        )),
        (_gen,      lambda _: (
            "**Generator Mode** — negative $T_e$ indicates the machine absorbs mechanical torque "
            "and injects active power into the grid (slip $s < 0$, rotor above "
            "synchronous speed $\\omega_s$). Motor sign convention adopted: "
            "positive = motor, negative = generator."
        )),
        (_sd,       _note_te_sd),
        (_vsag,     lambda ctx: (
            f"**Voltage Sag ($V_{{sag}}$ = {float(ctx.exp_config.get('sag_magnitude', 0.5)):.0%}$V_n$)** — "
            f"$T_e$ drops proportionally to $V_s^2$, reducing to $\\approx {float(ctx.exp_config.get('sag_magnitude', 0.5))**2:.0%}$ "
            f"of rated value during the disturbance. If $T_{{e,\\min}} < T_L$ the motor loses "
            f"synchronism and may stall ($s \\to 1$)."
        )),
        (_dol,      lambda _: (
            "**Direct-On-Line Starting (DOL)** — at energization with $\\omega_r = 0$ and $s = 1$, "
            "low circuit impedance imposes inrush current $I_s \\approx 5$–$8\\,I_n$. "
            "Torque $T_e$ exhibits damped oscillations superimposed on a rising envelope, "
            "arising from transient fluxes in the $d$-$q$ axes, until stabilizing at "
            "$T_e = T_L + B\\,\\omega_r$."
        )),
    ],
    "ias": [
        (_bb,       lambda ctx: (
            f"**Broken bar (α={ctx.bb_sev:.2f})** — rotor circuit asymmetry "
            f"induces amplitude modulation in stator current, generating sidebands "
            f"at $(1\\pm2s)f_e$ = {(1.0 - 2.0 * abs(ctx.s_val)) * ctx.mp.f:.1f} Hz and "
            f"{(1.0 + 2.0 * abs(ctx.s_val)) * ctx.mp.f:.1f} Hz visible in the MCSA spectrum "
            f"— see the **Diagnostics & Faults** tab."
        )),
        (_imbalance,    lambda _: (
            "**Voltage unbalance / Phase fault** — asymmetric phase currents "
            "indicate negative-sequence component $I_2$ circulating in the stator. "
            "The phase with lower voltage tends to carry higher current, accelerating "
            "insulation aging."
        )),
        (_yd,       lambda _: (
            "**Star-Delta Starting (Y-$\\Delta$)** — in star mode, $I_s$ is "
            "reduced to $1/3$ of the equivalent DOL value. At delta switching "
            "a second current peak occurs, typically $1{.}5$–$2\\,I_n$, "
            "decaying with $\\tau_s = L_s/R_s$."
        )),
        (_autotrafo, lambda ctx: (
            f"**Autotransformer (tap $k$ = {float(ctx.exp_config.get('voltage_ratio', 0.5)):.0%})** — stator inrush current "
            f"is reduced by $k^2 = {float(ctx.exp_config.get('voltage_ratio', 0.5))**2:.2f}$ compared to direct starting, since "
            f"$I_{{s,\\text{{inrush}}}} \\propto V_s = k\\,V_n$."
        )),
        (_soft,     lambda _: (
            "**Soft-starter** — the voltage ramp eliminates the inrush peak; current "
            "grows gradually from $I_s \\approx 0$ to $I_n$ in steady state, "
            "reducing electrical and mechanical stress at starting."
        )),
        (_dol,      lambda _: (
            "**Direct-On-Line Starting (DOL)** — with $s = 1$, starting current reaches "
            "$I_{{s,0}} \\approx V_n / Z_s$, typically $5$–$8\\,I_n$. "
            "As $\\omega_r$ increases and $s$ decreases, $I_s$ reduces to $I_n$ "
            "in steady state."
        )),
        (_vsag,     lambda _: (
            "**Voltage Sag** — during the sag, $I_s$ may transiently rise "
            "if the motor decelerates and slip $s$ increases, "
            "typical behavior for loads with torque proportional to $\\omega_r^2$."
        )),
    ],
    "iar": [
        (_bb,       lambda ctx: (
            f"**Broken bar (α={ctx.bb_sev:.2f})** — asymmetric rotor currents "
            f"indicate that one or more bars have elevated resistance ($R_{{bar}} \\gg R_r$). "
            f"Non-uniform distribution generates $T_e$ pulsation and localized heating."
        )),
        (_imbalance,    lambda _: (
            "**Voltage unbalance** — the negative-sequence component induces "
            "rotor current at frequency $(2-s)f_e$, much larger than $sf_e$ of "
            "balanced operation, increasing rotor Joule losses."
        )),
    ],
    "Va": [
        (_vsag,     lambda ctx: (
            f"**Voltage Sag** — voltage reduced to {float(ctx.exp_config.get('sag_magnitude', 0.5)):.0%}$V_n$ during "
            f"$\\Delta t_{{sag}}$ = {float(ctx.exp_config.get('t_duration_sag', 0.1)):.3f} s (from $t$ = "
            f"{float(ctx.exp_config.get('t_start_sag', 0.5)):.3f} s to "
            f"$t$ = {float(ctx.exp_config.get('t_start_sag', 0.5)) + float(ctx.exp_config.get('t_duration_sag', 0.1)):.3f} s). "
            f"Abrupt recovery after the sag may generate "
            f"a re-excitation transient in stator flux."
        )),
        (_imbalance,    _note_va_imbalance),
    ],
    "n": [
        (_gen,      lambda ctx: (
            f"**Generator Mode** — $n$ above synchronous speed corresponds to "
            f"$s < 0$. The machine operates as an induction generator, injecting active power "
            f"into the grid without independent excitation (requires reactive power from the grid for magnetization)."
        )),
        (_sd,       lambda ctx: _note_speed_sd_keyed(ctx, "$n$", "rpm")),
        (_vsag,     lambda ctx: (
            f"**Voltage Sag** — the drop in $T_e \\propto V_s^2$ during the sag "
            f"causes transient deceleration of $n$. If the slip margin "
            f"is sufficient, the motor recovers rated speed after voltage restoration; "
            f"otherwise it stalls ($s \\to 1$)."
        )),
        (_pulse,    lambda ctx: (
            f"**Load Pulse** — sudden insertion of $T_L$ causes transient drop "
            f"in $n$, increasing $s$ and consequently $T_e$. The system "
            f"damps and converges to the new equilibrium point with mechanical "
            f"time constant $\\tau_m \\approx J/B$."
        )),
        (_yd,       lambda ctx: (
            f"**Star-Delta Starting (Y-$\\Delta$)** — $n$ grows monotonically "
            f"during star phase. At switching, the $T_e$ transient causes "
            f"a visible perturbation before stabilization in steady state."
        )),
        (_autotrafo, lambda ctx: (
            f"**Autotransformer** — acceleration under reduced voltage is slower than "
            f"in DOL (torque proportional to $k^2$). At switching to full voltage, "
            f"$n$ exhibits a transient perturbation before reaching steady state."
        )),
        (_soft,     lambda ctx: (
            f"**Soft-starter** — $n$ grows smoothly with the progressive increase "
            f"of $V_s(t)$, without the mechanical shock of direct starting. Acceleration "
            f"is monotonic, limited by the configured ramp profile."
        )),
        (_dol,      lambda ctx: (
            f"**Direct-On-Line Starting (DOL)** — $n$ starts from zero and accelerates to "
            f"$\\approx (1-s_{{nom}})\\,\\omega_s$ ({60.0 * ctx.mp.f / (ctx.mp.p / 2.0) * (1 - abs(ctx.s_val)):.0f} rpm). "
            f"Acceleration is determined by excess torque $T_e - T_L$ divided "
            f"by moment of inertia $J$."
        )),
    ],
    "wr": [
        (_gen,      lambda ctx: (
            f"**Generator Mode** — $\\omega_r$ above synchronous speed corresponds to "
            f"$s < 0$. The machine operates as an induction generator, injecting active power "
            f"into the grid without independent excitation (requires reactive power from the grid for magnetization)."
        )),
        (_sd,       lambda ctx: _note_speed_sd_keyed(ctx, "$\\omega_r$", "rad/s")),
        (_vsag,     lambda ctx: (
            f"**Voltage Sag** — the drop in $T_e \\propto V_s^2$ during the sag "
            f"causes transient deceleration of $\\omega_r$. If the slip margin "
            f"is sufficient, the motor recovers rated speed after voltage restoration; "
            f"otherwise it stalls ($s \\to 1$)."
        )),
        (_pulse,    lambda ctx: (
            f"**Load Pulse** — sudden insertion of $T_L$ causes transient drop "
            f"in $\\omega_r$, increasing $s$ and consequently $T_e$. The system "
            f"damps and converges to the new equilibrium point with mechanical "
            f"time constant $\\tau_m \\approx J/B$."
        )),
        (_yd,       lambda ctx: (
            f"**Star-Delta Starting (Y-$\\Delta$)** — $\\omega_r$ grows monotonically "
            f"during star phase. At switching, the $T_e$ transient causes "
            f"a visible perturbation before stabilization in steady state."
        )),
        (_autotrafo, lambda ctx: (
            f"**Autotransformer** — acceleration under reduced voltage is slower than "
            f"in DOL (torque proportional to $k^2$). At switching to full voltage, "
            f"$\\omega_r$ exhibits a transient perturbation before reaching steady state."
        )),
        (_soft,     lambda ctx: (
            f"**Soft-starter** — $\\omega_r$ grows smoothly with the progressive increase "
            f"of $V_s(t)$, without the mechanical shock of direct starting. Acceleration "
            f"is monotonic, limited by the configured ramp profile."
        )),
        (_dol,      lambda ctx: (
            f"**Direct-On-Line Starting (DOL)** — $\\omega_r$ starts from zero and accelerates to "
            f"$\\approx (1-s_{{nom}})\\,\\omega_s$ ({2.0 * np.pi * ctx.mp.f / (ctx.mp.p / 2.0) * (1 - abs(ctx.s_val)):.1f} rad/s). "
            f"Acceleration is determined by excess torque $T_e - T_L$ divided "
            f"by moment of inertia $J$."
        )),
    ],
}

# aliases: ibs/ics share ias entries; ibr/icr share iar entries; Vb/Vc share Va entries
_NOTES["ibs"] = _NOTES["ias"]
_NOTES["ics"] = _NOTES["ias"]
_NOTES["ibr"] = _NOTES["iar"]
_NOTES["icr"] = _NOTES["iar"]
_NOTES["Vb"]  = _NOTES["Va"]
_NOTES["Vc"]  = _NOTES["Va"]


def _note_speed_sd_keyed(ctx: MITNoteCtx, lbl_v: str, lbl_u: str) -> str:
    mp = ctx.mp
    cfg = ctx.exp_config
    _ws    = 2.0 * np.pi * mp.f / (mp.p / 2.0)
    _t_cut = float(cfg.get("t_cutoff", 0.0))
    if mp.B > 0 and ctx.Tl_cfg > 0:
        _t_stop = math.log(1.0 + mp.B * _ws / ctx.Tl_cfg) * mp.J / mp.B
    elif ctx.Tl_cfg > 0:
        _t_stop = mp.J * _ws / ctx.Tl_cfg
    else:
        _t_stop = mp.J / mp.B if mp.B > 0 else 0.0
    return (
        f"**Shutdown** — after $t_{{off}}$ = {_t_cut:.2f} s the voltage is cut and "
        f"the motor decelerates freely. Estimated stop time: **{_t_stop:.2f} s** "
        f"($J/B \\cdot \\ln(1 + B\\omega_s/T_L)$)."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def emit_mit_note(key: str, ctx: MITNoteCtx) -> None:
    """Emit the contextual st.caption() note for variable *key*, if applicable."""
    entries = _NOTES.get(key)
    if not entries:
        return
    for predicate, builder in entries:
        if predicate(ctx):
            st.caption(builder(ctx))
            return
