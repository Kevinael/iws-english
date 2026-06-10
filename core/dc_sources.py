# -*- coding: utf-8 -*-
"""
dc_sources.py
=============
Factory for DC machine voltage and torque excitation functions — supports DOL,
resistor starting, load pulse, and generator modes.

Responsibilities:
  - Build callable(t) → (Va, Vf) for armature and field voltages
  - Build callable(t) → Tl for load torque

Relationships:
  Imported by : ui_components.sim_runner_dc
  Imports     : core.dc_machine_model

Extending:
  - For DC injection braking, add a make_voltage_fn_dc variant with a Va
    reversal profile.
"""

from __future__ import annotations

from typing import Callable

from core.dc_machine_model import DCMachineParams


def make_voltage_fn_dc(
    mode: str,
    params: DCMachineParams,
    exp_config: dict,
) -> Callable[[float], tuple[float, float]]:
    """Returns voltage function (Va(t), Vf(t)) for the given mode."""
    Va_nom = params.Va
    Vf_nom = params.Vf

    if mode == "dol_dc":
        def fn(t: float) -> tuple[float, float]:
            return Va_nom, Vf_nom
        return fn

    if mode == "resistencia_dc":
        R_ini  = float(exp_config.get("R_ini", 5.0))
        t_ramp = float(exp_config.get("t_ramp", 2.0))
        Ra     = params.Ra

        def fn(t: float) -> tuple[float, float]:
            # Reduces R_series from R_ini → 0 linearly until t_ramp
            r = R_ini * max(0.0, 1.0 - t / t_ramp) if t_ramp > 0 else 0.0
            # Effective Va equals Va with pre-calculated R_series voltage drop
            # Keep nominal Va; r is treated in model as temporary Ra parameter
            # For simplicity, scale Va: Vef = Va * Ra/(Ra+r) → same ia current
            Va_eff = Va_nom * params.Ra / (params.Ra + r) if (params.Ra + r) > 0 else Va_nom
            return Va_eff, Vf_nom
        return fn

    if mode == "plugging_dc":
        t_freia = float(exp_config.get("t_freia", 3.0))

        def fn(t: float) -> tuple[float, float]:
            Va = -Va_nom if t >= t_freia else Va_nom
            return Va, Vf_nom
        return fn

    if mode == "frenagem_dc":
        brake  = exp_config.get("brake_method", "plugging")
        t_freia = float(exp_config.get("t_freia", 3.0))

        if brake == "plugging":
            def fn(t: float) -> tuple[float, float]:
                return (-Va_nom if t >= t_freia else Va_nom), Vf_nom
            return fn

        if brake == "injecao_cc":
            Vdc_inj = float(exp_config.get("Vdc_inj", Va_nom * 0.1))
            def fn(t: float) -> tuple[float, float]:
                Va = Vdc_inj if t >= t_freia else Va_nom
                return Va, Vf_nom
            return fn

        if brake == "regenerativo":
            Va_regen = float(exp_config.get("Va_regen", Va_nom * 0.5))
            def fn(t: float) -> tuple[float, float]:
                Va = Va_regen if t >= t_freia else Va_nom
                return Va, Vf_nom
            return fn

        # fallback
        def fn(t: float) -> tuple[float, float]:
            return Va_nom, Vf_nom
        return fn

    if mode == "campo_fraco_dc":
        Vf_fraco = float(exp_config.get("Vf_fraco", Vf_nom * 0.5))
        t_campo  = float(exp_config.get("t_campo", 3.0))
        t_trans  = float(exp_config.get("t_trans", 0.5))

        def fn(t: float) -> tuple[float, float]:
            if t < t_campo:
                Vf = Vf_nom
            elif t < t_campo + t_trans:
                alpha = (t - t_campo) / t_trans
                Vf = Vf_nom + alpha * (Vf_fraco - Vf_nom)
            else:
                Vf = Vf_fraco
            return Va_nom, Vf
        return fn

    if mode in ("pulso_dc", "gerador_dc"):
        def fn(t: float) -> tuple[float, float]:
            return Va_nom, Vf_nom
        return fn

    raise ValueError(f"Unknown voltage mode: {mode!r}")


def make_torque_fn_dc(
    mode: str,
    params: DCMachineParams,
    exp_config: dict,
) -> Callable[[float], float]:
    """Returns torque function Tl(t)."""
    Tl_nom = params.Tload

    if mode == "pulso_dc":
        t_pulso  = float(exp_config.get("t_pulso", 4.0))
        Tl_extra = float(exp_config.get("Tl_extra", Tl_nom * 0.5))

        def fn(t: float) -> float:
            return Tl_nom + Tl_extra if t >= t_pulso else Tl_nom
        return fn

    if mode == "gerador_dc":
        Tl_gen = float(exp_config.get("Tl_gen", abs(Tl_nom)))

        def fn(t: float) -> float:
            return Tl_gen   # mechanical traction (positive → accelerates generator)
        return fn

    # Other modes: constant torque
    def fn(t: float) -> float:
        return Tl_nom
    return fn
