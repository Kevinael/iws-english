"""Fontes de tensão e torque para simulação MCC.

make_voltage_fn_dc(mode, params, exp_config) → callable(t) → (Va, Vf)
make_torque_fn_dc(mode, params, exp_config)  → callable(t) → Tl
"""

from __future__ import annotations

from typing import Callable

from core.dc_machine_model import DCMachineParams


def make_voltage_fn_dc(
    mode: str,
    params: DCMachineParams,
    exp_config: dict,
) -> Callable[[float], tuple[float, float]]:
    """Retorna função tensão (Va(t), Vf(t)) para o modo dado."""
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
            # Reduz R_serie de R_ini → 0 linearmente até t_ramp
            r = R_ini * max(0.0, 1.0 - t / t_ramp) if t_ramp > 0 else 0.0
            # Va efetivo equivale a Va com queda em R_serie pré-calculada
            # Mantemos Va nominal; r é tratado no modelo como parâmetro Ra temporário
            # Para simplificar, escalamos Va: Vef = Va * Ra/(Ra+r) → ia mesma corrente
            Va_eff = Va_nom * params.Ra / (params.Ra + r) if (params.Ra + r) > 0 else Va_nom
            return Va_eff, Vf_nom
        return fn

    if mode == "plugging_dc":
        t_freia = float(exp_config.get("t_freia", 3.0))

        def fn(t: float) -> tuple[float, float]:
            Va = -Va_nom if t >= t_freia else Va_nom
            return Va, Vf_nom
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

    raise ValueError(f"Modo de tensão desconhecido: {mode!r}")


def make_torque_fn_dc(
    mode: str,
    params: DCMachineParams,
    exp_config: dict,
) -> Callable[[float], float]:
    """Retorna função torque Tl(t)."""
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
            return Tl_gen   # tração mecânica (positivo → acelera gerador)
        return fn

    # Demais modos: torque constante
    def fn(t: float) -> float:
        return Tl_nom
    return fn
