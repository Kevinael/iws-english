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
from typing import Any

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
    deseq_on:  bool     # any voltage-unbalance / phase-fault flag active
    is_yd:     bool
    is_gen:    bool
    is_sd:     bool
    is_soft:   bool
    Tl_cfg:    float    # configured load torque
    Te_max:    float    # peak Te from simulation
    mp:        MachineParams


def emit_mit_note(key: str, ctx: MITNoteCtx) -> None:
    """Emit the contextual st.caption() note for variable *key*, if applicable."""
    cfg      = ctx.exp_config
    bb_sev   = ctx.bb_sev
    s_val    = ctx.s_val
    deseq_on = ctx.deseq_on
    is_yd    = ctx.is_yd
    is_gen   = ctx.is_gen
    is_sd    = ctx.is_sd
    is_soft  = ctx.is_soft
    Tl_cfg   = ctx.Tl_cfg
    Te_max   = ctx.Te_max
    mp       = ctx.mp
    exp_type = ctx.exp_type

    if key == "Te":
        if bb_sev > 0:
            _f_osc = 2.0 * abs(s_val) * mp.f
            st.caption(
                f"**Broken bar (α={bb_sev:.2f})** — $T_e$ oscillates at {_f_osc:.1f} Hz "
                f"($2sf$). Load torque $T_L$ remains essentially constant: "
                f"inertia $J$ damps speed oscillations, making $\\Delta T_L \\ll \\Delta T_e$. "
                f"The spectral signature appears in current as sidebands at $(1\\pm2s)f_e$ Hz — "
                f"see the **Diagnostics & Faults** tab."
            )
        elif deseq_on:
            st.caption(
                "**Voltage unbalance / Phase fault** — the negative-sequence component "
                "establishes a rotating field opposing $\\omega_s$, with effective slip "
                "$s^- = 2 - s^+$, generating pulsating braking torque at frequency $2f$ and reducing "
                "mean $T_e$ relative to balanced operation."
            )
        elif is_yd:
            st.caption(
                "**Star-Delta Starting (Y-$\\Delta$)** — at switching, the phase voltage jumps "
                "from $V_n/\\sqrt{3}$ to $V_n$, imposing an excitation step over the residual flux "
                "in the air gap. The second $T_e$ peak decays with time constant $\\tau_s = L_s/R_s$ to "
                "the new steady state $T_e = T_L + B\\,\\omega_r$."
            )
        elif exp_type == "autotrafo":
            _k = float(cfg.get("voltage_ratio", 0.5))
            st.caption(
                f"**Autotransformer Starting (tap $k$ = {_k:.0%})** — reduced voltage "
                f"$V_s = k\\,V_n$ attenuates $T_e$ by factor $k^2 = {_k**2:.2f}$, reducing the "
                f"inrush peak without eliminating transient oscillations. At switching to full "
                f"voltage a second transient occurs analogous to Y-$\\Delta$ mode."
            )
        elif is_soft:
            if Te_max < Tl_cfg * 1.05 and Tl_cfg > 0:
                st.caption(
                    "**Soft-starter** — maximum starting torque is close to load torque. "
                    "If $T_{e,\\max} < T_L$ the motor will not start. Consider increasing the initial "
                    "voltage or reducing load during acceleration."
                )
            else:
                st.caption(
                    "**Soft-starter** — the voltage ramp smooths $T_e$ growth, "
                    "eliminating the inrush peak of direct starting. Torque grows "
                    "approximately proportionally to $V_s^2(t)$ until reaching $T_e = T_L + B\\,\\omega_r$ "
                    "in steady state."
                )
        elif exp_type == "pulso_carga":
            st.caption(
                "**Load Pulse** — sudden insertion of $T_L$ causes transient drop in "
                "$\\omega_r$ and increase in slip $s$. Electromagnetic torque $T_e$ "
                "rises in response, with oscillations damped by time constant $\\tau_m = J/B$, "
                "until equaling $T_L + B\\,\\omega_r$ at the new operating point."
            )
        elif is_gen:
            st.caption(
                "**Generator Mode** — negative $T_e$ indicates the machine absorbs mechanical torque "
                "and injects active power into the grid (slip $s < 0$, rotor above "
                "synchronous speed $\\omega_s$). Motor sign convention adopted: "
                "positive = motor, negative = generator."
            )
        elif is_sd:
            _tau_r = mp.Lr / mp.Rr if mp.Rr > 0 else 0.0
            st.caption(
                f"**Shutdown** — after voltage cut, air-gap flux decays with "
                f"time constant $\\tau_r = L_r/R_r$ = {_tau_r:.3f} s and $T_e$ rapidly drops to zero. "
                f"The rotor continues spinning by inertia, decelerating under $T_L$ and viscous friction $B$."
            )
        elif exp_type == "voltage_sag":
            _sag = float(cfg.get("sag_magnitude", 0.5))
            st.caption(
                f"**Voltage Sag ($V_{{sag}}$ = {_sag:.0%}$V_n$)** — "
                f"$T_e$ drops proportionally to $V_s^2$, reducing to $\\approx {_sag**2:.0%}$ "
                f"of rated value during the disturbance. If $T_{{e,\\min}} < T_L$ the motor loses "
                f"synchronism and may stall ($s \\to 1$)."
            )
        elif exp_type == "dol":
            st.caption(
                "**Direct-On-Line Starting (DOL)** — at energization with $\\omega_r = 0$ and $s = 1$, "
                "low circuit impedance imposes inrush current $I_s \\approx 5$–$8\\,I_n$. "
                "Torque $T_e$ exhibits damped oscillations superimposed on a rising envelope, "
                "arising from transient fluxes in the $d$-$q$ axes, until stabilizing at "
                "$T_e = T_L + B\\,\\omega_r$."
            )

    elif key in ("ias", "ibs", "ics"):
        if bb_sev > 0:
            _f_osc = 2.0 * abs(s_val) * mp.f
            _f_lo  = (1.0 - 2.0 * abs(s_val)) * mp.f
            _f_hi  = (1.0 + 2.0 * abs(s_val)) * mp.f
            st.caption(
                f"**Broken bar (α={bb_sev:.2f})** — rotor circuit asymmetry "
                f"induces amplitude modulation in stator current, generating sidebands "
                f"at $(1\\pm2s)f_e$ = {_f_lo:.1f} Hz and {_f_hi:.1f} Hz visible in the MCSA spectrum "
                f"— see the **Diagnostics & Faults** tab."
            )
        elif deseq_on:
            st.caption(
                "**Voltage unbalance / Phase fault** — asymmetric phase currents "
                "indicate negative-sequence component $I_2$ circulating in the stator. "
                "The phase with lower voltage tends to carry higher current, accelerating "
                "insulation aging."
            )
        elif is_yd:
            st.caption(
                "**Star-Delta Starting (Y-$\\Delta$)** — in star mode, $I_s$ is "
                "reduced to $1/3$ of the equivalent DOL value. At delta switching "
                "a second current peak occurs, typically $1{.}5$–$2\\,I_n$, "
                "decaying with $\\tau_s = L_s/R_s$."
            )
        elif exp_type == "autotrafo":
            _k = float(cfg.get("voltage_ratio", 0.5))
            st.caption(
                f"**Autotransformer (tap $k$ = {_k:.0%})** — stator inrush current "
                f"is reduced by $k^2 = {_k**2:.2f}$ compared to direct starting, since "
                f"$I_{{s,\\text{{inrush}}}} \\propto V_s = k\\,V_n$."
            )
        elif is_soft:
            st.caption(
                "**Soft-starter** — the voltage ramp eliminates the inrush peak; current "
                "grows gradually from $I_s \\approx 0$ to $I_n$ in steady state, "
                "reducing electrical and mechanical stress at starting."
            )
        elif exp_type == "dol":
            st.caption(
                "**Direct-On-Line Starting (DOL)** — with $s = 1$, starting current reaches "
                "$I_{{s,0}} \\approx V_n / Z_s$, typically $5$–$8\\,I_n$. "
                "As $\\omega_r$ increases and $s$ decreases, $I_s$ reduces to $I_n$ "
                "in steady state."
            )
        elif exp_type == "voltage_sag":
            st.caption(
                "**Voltage Sag** — during the sag, $I_s$ may transiently rise "
                "if the motor decelerates and slip $s$ increases, "
                "typical behavior for loads with torque proportional to $\\omega_r^2$."
            )

    elif key in ("iar", "ibr", "icr"):
        if bb_sev > 0:
            st.caption(
                f"**Broken bar (α={bb_sev:.2f})** — asymmetric rotor currents "
                f"indicate that one or more bars have elevated resistance ($R_{{bar}} \\gg R_r$). "
                f"Non-uniform distribution generates $T_e$ pulsation and localized heating."
            )
        elif deseq_on:
            st.caption(
                "**Voltage unbalance** — the negative-sequence component induces "
                "rotor current at frequency $(2-s)f_e$, much larger than $sf_e$ of "
                "balanced operation, increasing rotor Joule losses."
            )

    elif key in ("Va", "Vb", "Vc"):
        if exp_type == "voltage_sag":
            _sag = float(cfg.get("sag_magnitude", 0.5))
            _t0  = float(cfg.get("t_start_sag", 0.5))
            _dt  = float(cfg.get("t_duration_sag", 0.1))
            st.caption(
                f"**Voltage Sag** — voltage reduced to {_sag:.0%}$V_n$ during "
                f"$\\Delta t_{{sag}}$ = {_dt:.3f} s (from $t$ = {_t0:.3f} s to "
                f"$t$ = {_t0+_dt:.3f} s). Abrupt recovery after the sag may generate "
                f"a re-excitation transient in stator flux."
            )
        elif deseq_on:
            _falta = any(cfg.get(k, 0) for k in ("falta_fase_a", "falta_fase_b", "falta_fase_c"))
            if _falta:
                st.caption(
                    "**Phase fault** — the open-phase voltage drops to zero at the terminals; "
                    "the remaining phases maintain rated amplitude, imposing non-zero "
                    "negative-sequence voltage $V_2$ on the stator."
                )
            else:
                st.caption(
                    "**Voltage unbalance** — unequal phase amplitudes indicate "
                    "supply asymmetry. Decomposition into symmetric components "
                    "reveals $V_2/V_1$ proportional to the degree of unbalance."
                )

    elif key in ("n", "wr"):
        _lbl_v = "$\\omega_r$" if key == "wr" else "$n$"
        _lbl_u = "rad/s" if key == "wr" else "rpm"
        if is_gen:
            st.caption(
                f"**Generator Mode** — {_lbl_v} above synchronous speed corresponds to "
                f"$s < 0$. The machine operates as an induction generator, injecting active power "
                f"into the grid without independent excitation (requires reactive power from the grid for magnetization)."
            )
        elif is_sd:
            _ws    = 2.0 * np.pi * mp.f / (mp.p / 2.0)
            _t_cut = float(cfg.get("t_cutoff", 0.0))
            if mp.B > 0 and Tl_cfg > 0:
                _t_stop = math.log(1.0 + mp.B * _ws / Tl_cfg) * mp.J / mp.B
            elif Tl_cfg > 0:
                _t_stop = mp.J * _ws / Tl_cfg
            else:
                _t_stop = mp.J / mp.B if mp.B > 0 else 0.0
            st.caption(
                f"**Shutdown** — after $t_{{off}}$ = {_t_cut:.2f} s the voltage is cut and "
                f"the motor decelerates freely. Estimated stop time: **{_t_stop:.2f} s** "
                f"($J/B \\cdot \\ln(1 + B\\omega_s/T_L)$)."
            )
        elif exp_type == "voltage_sag":
            st.caption(
                f"**Voltage Sag** — the drop in $T_e \\propto V_s^2$ during the sag "
                f"causes transient deceleration of {_lbl_v}. If the slip margin "
                f"is sufficient, the motor recovers rated speed after voltage restoration; "
                f"otherwise it stalls ($s \\to 1$)."
            )
        elif exp_type == "pulso_carga":
            st.caption(
                f"**Load Pulse** — sudden insertion of $T_L$ causes transient drop "
                f"in {_lbl_v}, increasing $s$ and consequently $T_e$. The system "
                f"damps and converges to the new equilibrium point with mechanical "
                f"time constant $\\tau_m \\approx J/B$."
            )
        elif is_yd:
            st.caption(
                f"**Star-Delta Starting (Y-$\\Delta$)** — {_lbl_v} grows monotonically "
                f"during star phase. At switching, the $T_e$ transient causes "
                f"a visible perturbation before stabilization in steady state."
            )
        elif exp_type == "autotrafo":
            st.caption(
                f"**Autotransformer** — acceleration under reduced voltage is slower than "
                f"in DOL (torque proportional to $k^2$). At switching to full voltage, "
                f"{_lbl_v} exhibits a transient perturbation before reaching steady state."
            )
        elif is_soft:
            st.caption(
                f"**Soft-starter** — {_lbl_v} grows smoothly with the progressive increase "
                f"of $V_s(t)$, without the mechanical shock of direct starting. Acceleration "
                f"is monotonic, limited by the configured ramp profile."
            )
        elif exp_type == "dol":
            _ws_rpm = 60.0 * mp.f / (mp.p / 2.0)
            st.caption(
                f"**Direct-On-Line Starting (DOL)** — {_lbl_v} starts from zero and accelerates to "
                f"$\\approx (1-s_{{nom}})\\,\\omega_s$ ({_ws_rpm*(1-abs(s_val)):.0f} {_lbl_u}). "
                f"Acceleration is determined by excess torque $T_e - T_L$ divided "
                f"by moment of inertia $J$."
            )
