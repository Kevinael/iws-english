# -*- coding: utf-8 -*-
"""
sources.py
==========
Implements voltage and torque excitation functions for each simulation mode,
and the build_fns factory that constructs them by experiment type.

Responsibilities:
  - Generate three-phase voltages with ramp, reduced-start, sag, and nominal profiles
  - Generate torques with step and pulse profiles
  - Map experiment type to a (voltage_fn, torque_fn) pair via build_fns

Relationships:
  Imported by : core.IWS_PY, ui.sim_runner, scripts.*
  Imports     : core.machine_model

Extending:
  - For a PWM inverter mode, add voltage_pwm() and register it in the
    build_fns dispatch dict.
"""

from __future__ import annotations
import numpy as np
from core.tim.machine_model import MachineParams


# ═══════════════════════════════════════════════════════════════════════════
# VOLTAGE SOURCES
# ═══════════════════════════════════════════════════════════════════════════

def voltage_reduced_start(t: float, Vl_nominal: float, Vl_reduced: float, t_switch: float) -> float:
    return Vl_nominal if t >= t_switch else Vl_reduced


def voltage_soft_starter(t: float, Vl_nominal: float, Vl_initial: float,
                         t_start_ramp: float, t_full: float) -> float:
    if t < t_start_ramp:
        return Vl_initial
    elif t < t_full:
        return Vl_initial + (Vl_nominal - Vl_initial) * (t - t_start_ramp) / (t_full - t_start_ramp)
    return Vl_nominal


def voltage_sag(t: float, Vl_nominal: float, sag_magnitude: float,
                t_start: float, t_end: float) -> float:
    """Rectangular sag: Vl drops to sag_magnitude*Vl within [t_start, t_end)."""
    if t_start <= t < t_end:
        return Vl_nominal * sag_magnitude
    return Vl_nominal


# ═══════════════════════════════════════════════════════════════════════════
# TORQUE SOURCES
# ═══════════════════════════════════════════════════════════════════════════

def torque_step(t: float, Tl_before: float, Tl_after: float, t_switch: float) -> float:
    return Tl_after if t >= t_switch else Tl_before


def torque_pulse(t: float, Tl_base: float, Tl_pulse: float, t_on: float, t_off: float) -> float:
    """Tl_base outside the pulse; Tl_pulse within [t_on, t_off)."""
    return Tl_pulse if t_on <= t < t_off else Tl_base


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENT FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def build_fns(config: dict, mp: MachineParams):
    """Builds (voltage_fn, torque_fn, t_events) for the selected experiment.

    All returned functions are scalar: they receive and return float.
    LSODA calls voltage_fn(t) and torque_fn(t) with a scalar at each step.

    Returns:
        (vfn, tfn, t_ev) — scalar callables and list of event instants.
    """
    exp  = config["exp_type"]
    t_ev: list = []

    if exp == "dol":
        Ti = config.get("Tl_inicial") or 0.0
        Tl = config["Tl_final"]
        tc = config.get("t_load", 0.0)
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Ti=Ti, _Tl=Tl, _tc=tc: torque_step(t, _Ti, _Tl, _tc)
        t_ev = [tc] if tc > 0 else []

    elif exp == "yd":
        Vy = mp.Vl / np.sqrt(3.0)
        Tl, t2, tc = config["Tl_final"], config["t_2"], config["t_load"]
        # capture by value: Vy and t2 are local to the if-branch and would be lost by ref
        vfn = lambda t, _Vl=mp.Vl, _Vy=Vy, _t2=t2: voltage_reduced_start(t, _Vl, _Vy, _t2)
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = [t2, tc]

    elif exp == "comp":
        Vr = mp.Vl * config["voltage_ratio"]
        Tl, t2, tc = config["Tl_final"], config["t_2"], config["t_load"]
        # Vr computed from voltage_ratio — capture by value
        vfn = lambda t, _Vl=mp.Vl, _Vr=Vr, _t2=t2: voltage_reduced_start(t, _Vl, _Vr, _t2)
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = [t2, tc]

    elif exp == "soft":
        Vi = mp.Vl * config["voltage_ratio"]
        t2, tp = config["t_2"], config["t_peak"]
        Tl, tc = config["Tl_final"], config["t_load"]
        # Vi, t2, tp: local variables — capture by value required
        vfn = lambda t, _Vl=mp.Vl, _Vi=Vi, _t2=t2, _tp=tp: voltage_soft_starter(t, _Vl, _Vi, _t2, _tp)
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = [t2, tc]

    elif exp == "load_pulse":
        Tb   = config.get("Tl_base", 0.0)
        Tl   = config["Tl_final"]
        ton  = config["t_load"]
        toff = config["t_removal"]
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Tb=Tb, _Tl=Tl, _ton=ton, _toff=toff: torque_pulse(t, _Tb, _Tl, _ton, _toff)
        t_ev = [ton, toff]

    elif exp == "generator":
        Tn = -config["Tl_mec"]
        t2 = config["t_2"]
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Tn=Tn, _t2=t2: _Tn if t >= _t2 else 0.0
        t_ev = [t2]

    elif exp == "shutdown":
        Tl    = config["Tl_final"]
        tc    = config["t_load"]
        t_cut = config["t_cutoff"]
        vfn = lambda t, _Vl=mp.Vl, _tc=t_cut: _Vl if t < _tc else 0.0
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = [tc, t_cut]

    elif exp == "voltage_sag":
        Tl    = config["Tl_final"]
        tc    = config.get("t_load", 0.0)
        mag   = config["sag_magnitude"]
        t_sag = config["t_start_sag"]
        t_end = config["t_start_sag"] + config["t_duration_sag"]
        vfn = lambda t, _Vl=mp.Vl, _m=mag, _ts=t_sag, _te=t_end: voltage_sag(t, _Vl, _m, _ts, _te)
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = sorted(set(v for v in [tc, t_sag, t_end] if v > 0))

    elif exp == "braking":
        Tl     = config["Tl_final"]
        tc     = config.get("t_load", 0.3)
        tb     = config["t_brake"]
        brake  = config.get("brake_method", "plugging")

        if brake == "plugging":
            vfn = lambda t, _Vl=mp.Vl, _tb=tb: (-_Vl if t >= _tb else _Vl)
        elif brake == "dc_injection":
            Vinj = float(config.get("Vcc_inj", mp.Vl * 0.1))
            vfn = lambda t, _Vl=mp.Vl, _Vi=Vinj, _tb=tb: (_Vi if t >= _tb else _Vl)
        elif brake == "regenerative":
            Vr = mp.Vl * float(config.get("V_regen", 50)) / 100.0
            vfn = lambda t, _Vl=mp.Vl, _Vr=Vr, _tb=tb: (_Vr if t >= _tb else _Vl)
        else:
            vfn = lambda t: mp.Vl

        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = sorted(v for v in [tc, tb] if v > 0)

    else:
        vfn = lambda t: mp.Vl
        tfn = lambda t: 0.0

    return vfn, tfn, t_ev
