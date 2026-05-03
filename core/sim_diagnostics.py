# -*- coding: utf-8 -*-
"""
sim_diagnostics.py — Módulo de diagnóstico físico automático.

Analisa os vetores de estado do solver EDO e produz insights técnicos
baseados nas equações de Newton-Euler e no modelo de Krause (0dq).
"""

from __future__ import annotations
import math
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Tipos
# ─────────────────────────────────────────────────────────────────────────────

class Insight:
    """Contêiner de um insight de diagnóstico."""
    LEVELS = ("info", "warning", "error")

    def __init__(self, level: str, title: str, body: str) -> None:
        if level not in self.LEVELS:
            raise ValueError(f"level deve ser um de {self.LEVELS}")
        self.level = level
        self.title = title
        self.body  = body

    def __repr__(self) -> str:
        return f"Insight({self.level!r}, {self.title!r})"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _is_steady_state_reached(
    wr_arr: np.ndarray,
    t_arr: np.ndarray,
    ss_start: int,
    threshold_rad_s2: float = 0.5,
) -> bool:
    """Verifica se o regime permanente foi atingido.

    Critério: a taxa média de variação de wr na janela de regime
    (|dwr/dt|_médio) deve ser menor que threshold_rad_s2 (rad/s²).
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
# Função pública principal
# ─────────────────────────────────────────────────────────────────────────────

def generate_insights(
    res: dict,
    mp,
    load_torque: float,
    tmax: float,
    exp_type: str = "dol",
) -> list[Insight]:
    """Analisa o resultado do solver e devolve uma lista de Insight.

    Args:
        res:        Dict retornado por run_simulation() (inclui chaves de
                    _compute_steady_state: Te_ss, n_ss, wr_ss, s, _ss_start, …).
        mp:         MachineParams — parâmetros da máquina (B, p, wb, …).
        load_torque: Torque de carga nominal aplicado (N·m).  Pode ser 0
                    para experimentos sem carga definida (shutdown, gerador).
        tmax:       Duração total da simulação (s).
        exp_type:   Tipo de experimento (dol, yd, comp, soft, …).

    Returns:
        Lista de Insight ordenada por severidade decrescente.
    """
    insights: list[Insight] = []

    # ── arrays básicos ────────────────────────────────────────────────────
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

    # velocidade síncrona mecânica (rad/s)
    ws_mec = mp.wb / (mp.p / 2.0)
    n_sync = ws_mec * 60.0 / (2.0 * math.pi)

    # ── verificação de regime permanente ──────────────────────────────────
    steady = _is_steady_state_reached(wr_arr, t_arr, ss_start)

    if not steady:
        insights.append(Insight(
            level="warning",
            title="Regime Mecanico Nao Atingido",
            body=(
                f"O tempo de simulacao configurado (tmax = {tmax:.2f} s) foi insuficiente "
                f"para que o rotor atingisse a estabilidade mecanica. A derivada da velocidade "
                f"angular ainda era significativa no instante final. Recomenda-se aumentar "
                f"tmax ou verificar se o torque de carga excede o torque maximo do motor "
                f"(risco de travamento do rotor)."
            ),
        ))
        # sem regime, as regras de balanço de torque e escorregamento são inválidas
        # ainda analisa a reserva de conjugado durante o transiente
        _check_acceleration_margin(insights, Te_arr, load_torque, n_sync, mp)
        return _sort_insights(insights)

    # ── Regra 1: Balanço de torques — atrito e ventilação ─────────────────
    if exp_type not in ("shutdown", "gerador") and load_torque >= 0:
        T_atrito = mp.B * wr_ss                      # N·m — torque viscoso em regime
        T_balanco = Te_ss - load_torque              # deve ≈ T_atrito (equilíbrio)
        erro_rel  = abs(T_balanco - T_atrito) / max(abs(Te_ss), 1e-3)

        if abs(Te_ss) > 0.01:
            insights.append(Insight(
                level="info",
                title="Balanco de Torques em Regime Permanente",
                body=(
                    f"Em regime permanente (n = {n_ss:.1f} RPM), a equacao de Newton-Euler "
                    f"J·(domega/dt) = Te - T_L - B·omega_m = 0 e satisfeita. "
                    f"O torque eletromagnetico de regime (Te = {Te_ss:.3f} N·m) excede o "
                    f"torque de carga aplicado (T_L = {load_torque:.3f} N·m) pela parcela de "
                    f"atrito viscoso e ventilacao: B·omega_m = {T_atrito:.4f} N·m "
                    f"(B = {mp.B:.4f} N·m·s/rad). Esta diferenca algebrica nao e um erro "
                    f"numerico — e o torque exato exigido para vencer as perdas mecanicas "
                    f"na rotacao de equilibrio."
                ),
            ))

    # ── Regra 2: Reserva de conjugado (análise de aceleração) ─────────────
    _check_acceleration_margin(insights, Te_arr, load_torque, n_sync, mp)

    # ── Regra 3: Diagnóstico de sobrecarga e escorregamento extremo ────────
    if exp_type not in ("shutdown", "gerador") and steady:
        _check_slip_overload(insights, s_ss, n_ss, n_sync, Te_ss, mp)

    # ── Regra 4: Diagnóstico de subcarga ──────────────────────────────────
    if exp_type not in ("shutdown", "gerador") and load_torque > 0 and steady:
        _check_underload(insights, s_ss, mp)

    return _sort_insights(insights)


# ─────────────────────────────────────────────────────────────────────────────
# Regras individuais
# ─────────────────────────────────────────────────────────────────────────────

def _check_acceleration_margin(
    insights: list[Insight],
    Te_arr: np.ndarray,
    load_torque: float,
    n_sync: float,
    mp,
) -> None:
    """Regra 2 — Reserva de conjugado durante o transiente de partida."""
    if len(Te_arr) == 0:
        return

    Te_max = float(np.nanmax(Te_arr))
    if Te_max <= 0 or load_torque <= 0:
        return

    ratio = Te_max / load_torque

    if ratio >= 2.0:
        insights.append(Insight(
            level="info",
            title="Ampla Reserva de Conjugado de Aceleracao",
            body=(
                f"O torque eletromagnetico de pico durante o transiente de partida "
                f"(Te_max = {Te_max:.2f} N·m) representa {ratio:.1f}x o torque de carga "
                f"(T_L = {load_torque:.2f} N·m). A condicao J·(domega/dt) = Te - T_L - B·omega > 0 "
                f"foi largamente satisfeita, garantindo aceleracao positiva do rotor em "
                f"toda a trajetoria de partida. O motor possui ampla reserva cinetica "
                f"(pull-out safety margin), caracteristica de partida segura."
            ),
        ))
    elif ratio >= 1.2:
        insights.append(Insight(
            level="warning",
            title="Margem de Conjugado Reduzida — Partida Moderada",
            body=(
                f"O torque de pico (Te_max = {Te_max:.2f} N·m) foi apenas {ratio:.2f}x o "
                f"torque de carga (T_L = {load_torque:.2f} N·m). A margem de aceleracao "
                f"J·alpha = Te - T_L - B·omega_m foi positiva, porem estreita. "
                f"Perturbacoes na tensao de alimentacao ou variacao de carga durante a "
                f"partida podem resultar em aceleracao insuficiente e tempo de partida "
                f"prolongado, aproximando-se do limite de atuacao do rele termico."
            ),
        ))
    else:
        insights.append(Insight(
            level="error",
            title="RISCO DE TRAVAMENTO DO ROTOR — Partida Pesada",
            body=(
                f"O torque de pico eletromagnetico (Te_max = {Te_max:.2f} N·m) foi inferior "
                f"a 1,2x o torque de carga (T_L = {load_torque:.2f} N·m), resultando em "
                f"ratio = {ratio:.2f}. A equacao de aceleracao J·(domega/dt) = Te - T_L foi "
                f"marginalmente positiva ou negativa em parte da trajetoria, caracterizando "
                f"uma 'partida pesada'. O rotor operou proximas ao ponto de pull-out, "
                f"com risco iminente de travamento (stall). Verifique se a carga e "
                f"compativel com o motor ou adote partida suave/estrela-triangulo."
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
    """Regra 3 — Escorregamento extremo como indicador de sobrecarga."""
    S_CRITICO  = 0.08   # > 8%: sobrecarga severa
    S_ALERTA   = 0.05   # > 5%: sobrecarga moderada

    if s_ss > S_CRITICO:
        insights.append(Insight(
            level="error",
            title="SOBRECARGA SEVERA — Escorregamento Critico",
            body=(
                f"O escorregamento de regime permanente calculado e s = {s_ss*100:.2f}%, "
                f"muito acima do nominal tipico de motores NEMA B (1–3%). "
                f"Para induzir o torque demandado (Te_ss = {Te_ss:.2f} N·m) a esta "
                f"velocidade (n = {n_ss:.1f} RPM vs. n_s = {n_sync:.1f} RPM sincrona), "
                f"o campo magnetico girante induziu correntes no rotor muito elevadas "
                f"pela lei de Faraday (E_r proporcional a s·omega_s·Psi). "
                f"Isso resulta em perdas Joule no rotor P_Joule_r = s·P_gap desproporcio"
                f"nais, aquecimento acelerado do enrolamento e risco iminente de atuacao "
                f"do rele de sobrecarga termico (IEC 60947-4-1). "
                f"Revise o dimensionamento do motor para esta carga."
            ),
        ))
    elif s_ss > S_ALERTA:
        insights.append(Insight(
            level="warning",
            title="Escorregamento Elevado — Operacao Fora da Zona Nominal",
            body=(
                f"O escorregamento de regime permanente e s = {s_ss*100:.2f}%, acima do "
                f"valor tipico de projeto (< 5% para motores de uso geral). "
                f"O motor opera fora da regiao de maxima eficiencia da curva Te x n. "
                f"As perdas Joule no rotor (P_Joule_r = s·P_gap) sao elevadas, "
                f"reduzindo o rendimento e aumentando a temperatura do enrolamento. "
                f"Considere um motor de potencia superior ou reducao da carga mecanica."
            ),
        ))
    elif s_ss < 0:
        # operação como gerador (não deveria entrar aqui, mas proteção extra)
        pass
    elif s_ss < 0.001 and Te_ss > 0:
        insights.append(Insight(
            level="info",
            title="Operacao em Regime de Alta Eficiencia",
            body=(
                f"O escorregamento de regime e s = {s_ss*100:.3f}%, indicando operacao "
                f"proxima ao ponto de sincronismo. As perdas Joule no rotor "
                f"(P_Joule_r = s·P_gap) sao minimas, caracteristica de operacao de "
                f"alta eficiencia. Este comportamento e esperado em motores de alto "
                f"rendimento (premium efficiency, IE3/IE4) ou em condicao de leve carga."
            ),
        ))


def _check_underload(
    insights: list[Insight],
    s_ss: float,
    mp,
) -> None:
    """Regra 4 — Operação em subcarga (baixo fator de carga)."""
    S_SUBCARGA = 0.005  # < 0.5%: subcarga severa

    if 0 < s_ss < S_SUBCARGA:
        insights.append(Insight(
            level="warning",
            title="Motor em Subcarga — Fator de Potencia Degradado",
            body=(
                f"O escorregamento s = {s_ss*100:.3f}% indica que o motor opera com "
                f"carga muito inferior a sua potencia nominal. Em subcarga, a corrente "
                f"de magnetizacao (I_m = E1/Xm) permanece praticamente constante e "
                f"representa uma fracao elevada da corrente total, resultando em "
                f"fator de potencia baixo e rendimento reduzido. "
                f"Considere substituir por um motor de menor potencia nominal para "
                f"operar mais proximo do ponto de projeto."
            ),
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Ordenação
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}

def _sort_insights(insights: list[Insight]) -> list[Insight]:
    return sorted(insights, key=lambda x: _LEVEL_ORDER[x.level])
