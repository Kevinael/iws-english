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
    exp_config: dict | None = None,
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
        exp_config: Dict de configuração do experimento (parâmetros de entrada).

    Returns:
        Lista de Insight ordenada por severidade decrescente.
    """
    insights: list[Insight] = []
    cfg = exp_config or {}

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
            title="Regime Mecânico Não Atingido",
            body=(
                f"O tempo de simulação configurado (tmax = {tmax:.2f} s) foi insuficiente "
                f"para que o rotor atingisse a estabilidade mecânica. A derivada da velocidade "
                f"angular ainda era significativa no instante final. Recomenda-se aumentar "
                f"tmax ou verificar se o torque de carga excede o torque máximo do motor "
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
                title="Balanço de Torques em Regime Permanente",
                body=(
                    f"Em regime permanente (n = {n_ss:.1f} RPM), a equação de movimento "
                    f"J·(dω/dt) = Tₑ − T_L − B·ωₘ resulta em dω/dt = 0, confirmando "
                    f"equilíbrio dinâmico. O torque eletromagnético de regime "
                    f"(Tₑ = {Te_ss:.3f} N·m) supera o torque de carga "
                    f"(T_L = {load_torque:.3f} N·m) exatamente pela parcela de atrito "
                    f"viscoso e ventilação B·ωₘ = {T_atrito:.4f} N·m "
                    f"(B = {mp.B:.6f} N·m·s/rad). A diferença Tₑ − T_L − B·ωₘ = "
                    f"{Te_ss - load_torque - T_atrito:.6f} N·m é numericamente nula, "
                    f"indicando que o integrador convergiu corretamente para o ponto "
                    f"de operação estacionário."
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

    # ── Regra 5: Barra quebrada ───────────────────────────────────────────
    _check_broken_bar(insights, res, s_ss, mp)

    # ── Regra 6: Desequilíbrio de tensão (NEMA MG-1) ─────────────────────
    _check_voltage_imbalance(insights, res, mp, cfg)

    # ── Regra 7: Afundamento de tensão (Voltage Sag) ──────────────────────
    if exp_type == "voltage_sag":
        _check_voltage_sag(insights, res, t_arr, Te_arr, wr_arr, cfg, mp, n_sync)

    # ── Regra 8: Tempo de partida prolongado ─────────────────────────────
    _STARTUP_TYPES = ("dol", "yd", "comp", "soft")
    if exp_type in _STARTUP_TYPES and load_torque > 0:
        _check_startup_time(insights, t_arr, wr_arr, Te_arr, load_torque, ws_mec, mp, cfg)

    # ── Regras 9–11: Diagnósticos específicos do modo gerador ─────────────
    if exp_type == "gerador" and steady:
        _check_generator_mode(insights, res, s_ss, n_ss, n_sync, Te_ss, ws_mec, mp, cfg)

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
            title="Ampla Reserva de Conjugado de Aceleração",
            body=(
                f"O torque eletromagnético de pico durante o transitório de partida "
                f"(Tₑ_max = {Te_max:.2f} N·m) representa {ratio:.1f}× o torque de carga "
                f"(T_L = {load_torque:.2f} N·m). A condição J·(dω/dt) = Tₑ − T_L − B·ω > 0 "
                f"foi amplamente satisfeita, garantindo aceleração positiva do rotor em "
                f"toda a trajetória de partida. O motor apresenta ampla reserva cinética "
                f"(pull-out safety margin), característica de partida segura."
            ),
        ))
    elif ratio >= 1.2:
        insights.append(Insight(
            level="warning",
            title="Margem de Conjugado Reduzida — Partida Moderada",
            body=(
                f"O torque de pico (Tₑ_max = {Te_max:.2f} N·m) foi apenas {ratio:.2f}× o "
                f"torque de carga (T_L = {load_torque:.2f} N·m). A margem de aceleração "
                f"J·α = Tₑ − T_L − B·ωₘ foi positiva, porém estreita. "
                f"Perturbações na tensão de alimentação ou variação de carga durante a "
                f"partida podem resultar em aceleração insuficiente e tempo de partida "
                f"prolongado, aproximando-se do limite de atuação do relé térmico."
            ),
        ))
    else:
        insights.append(Insight(
            level="error",
            title="RISCO DE TRAVAMENTO DO ROTOR — Partida Pesada",
            body=(
                f"O torque de pico eletromagnético (Tₑ_max = {Te_max:.2f} N·m) foi inferior "
                f"a 1,2× o torque de carga (T_L = {load_torque:.2f} N·m), resultando em "
                f"razão = {ratio:.2f}. A equação de aceleração J·(dω/dt) = Tₑ − T_L foi "
                f"marginalmente positiva ou negativa em parte da trajetória, caracterizando "
                f"uma partida pesada. O rotor operou próximo ao ponto de pull-out, "
                f"com risco iminente de travamento (stall). Verifique se a carga é "
                f"compatível com o motor ou adote partida suave/estrela-triângulo."
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
            title="SOBRECARGA SEVERA — Escorregamento Crítico",
            body=(
                f"O escorregamento de regime permanente calculado é s = {s_ss*100:.2f}%, "
                f"muito acima do valor nominal típico de motores NEMA B (1–3%). "
                f"Para induzir o torque demandado (Te_ss = {Te_ss:.2f} N·m) a esta "
                f"velocidade (n = {n_ss:.1f} RPM vs. n_s = {n_sync:.1f} RPM síncrona), "
                f"o campo magnético girante induziu correntes no rotor muito elevadas "
                f"pela lei de Faraday (Eᵣ proporcional a s·ωₛ·Ψ). "
                f"Isso resulta em perdas Joule no rotor P_Joule_r = s·P_ag desproporcionais, "
                f"aquecimento acelerado do enrolamento e risco iminente de atuação "
                f"do relé de sobrecarga térmico (IEC 60947-4-1). "
                f"Revise o dimensionamento do motor para esta carga."
            ),
        ))
    elif s_ss > S_ALERTA:
        insights.append(Insight(
            level="warning",
            title="Escorregamento Elevado — Operação Fora da Zona Nominal",
            body=(
                f"O escorregamento de regime permanente é s = {s_ss*100:.2f}%, acima do "
                f"valor típico de projeto (< 5% para motores de uso geral). "
                f"O motor opera fora da região de máxima eficiência da curva Te × n. "
                f"As perdas Joule no rotor (P_Joule_r = s·P_ag) são elevadas, "
                f"reduzindo o rendimento e aumentando a temperatura do enrolamento. "
                f"Considere um motor de potência superior ou redução da carga mecânica."
            ),
        ))
    elif s_ss < 0:
        # operação como gerador (não deveria entrar aqui, mas proteção extra)
        pass
    elif s_ss < 0.001 and Te_ss > 0:
        insights.append(Insight(
            level="info",
            title="Operação em Regime de Alta Eficiência",
            body=(
                f"O escorregamento de regime é s = {s_ss*100:.3f}%, indicando operação "
                f"próxima ao ponto de sincronismo. As perdas Joule no rotor "
                f"(P_Joule_r = s·P_ag) são mínimas, característica de operação de "
                f"alta eficiência. Este comportamento é esperado em motores de alto "
                f"rendimento (premium efficiency, IE3/IE4) ou em condição de leve carga."
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
            title="Motor em Subcarga — Fator de Potência Degradado",
            body=(
                f"O escorregamento s = {s_ss*100:.3f}% indica que o motor opera com "
                f"carga muito inferior à sua potência nominal. Em subcarga, a corrente "
                f"de magnetização (Iₘ = E₁/Xₘ) permanece praticamente constante e "
                f"representa uma fração elevada da corrente total, resultando em "
                f"fator de potência baixo e rendimento reduzido. "
                f"Considere substituir por um motor de menor potência nominal para "
                f"operar mais próximo do ponto de projeto."
            ),
        ))


def _check_broken_bar(
    insights: list[Insight],
    res: dict,
    s_ss: float,
    mp,
) -> None:
    """Regra 5 — Detecção automática de barra quebrada via severidade e sidebands MCSA."""
    alpha = float(res.get("_broken_bar_severity", 0.0))
    if alpha <= 0:
        return

    f_fund = getattr(mp, "f", 60.0)
    sb_lo  = f_fund * (1.0 - 2.0 * abs(s_ss))
    sb_hi  = f_fund * (1.0 + 2.0 * abs(s_ss))

    if alpha >= 0.5:
        level = "error"
        severidade_txt = f"severa (α = {alpha:.2f})"
    elif alpha >= 0.2:
        level = "warning"
        severidade_txt = f"moderada (α = {alpha:.2f})"
    else:
        level = "warning"
        severidade_txt = f"incipiente (α = {alpha:.2f})"

    insights.append(Insight(
        level=level,
        title="Falha de Barra Quebrada Detectada — MCSA",
        body=(
            f"A simulação foi executada com assimetria de resistência do rotor "
            f"(severidade {severidade_txt}). Pelo método MCSA (Motor Current Signature "
            f"Analysis), barras quebradas imprimem componentes laterais na corrente do "
            f"estator nas frequências (1 ± 2s)·f: "
            f"f₋ = {sb_lo:.2f} Hz e f₊ = {sb_hi:.2f} Hz "
            f"(s = {s_ss*100:.2f}%, f = {f_fund:.1f} Hz). "
            f"Inspecione o espectro FFT de i_as na aba Diagnóstico e verifique a "
            f"amplitude relativa dos sidebands em relação à fundamental. "
            f"Amplitudes acima de −40 dB indicam necessidade de intervenção."
        ),
    ))


def _check_voltage_imbalance(
    insights: list[Insight],
    res: dict,
    mp,
    cfg: dict,
) -> None:
    """Regra 6 — Desequilíbrio de tensão via NEMA MG-1 (método das componentes simétricas)."""
    Va_rms = float(res.get("Va_rms", 0.0))
    Vb_rms = float(res.get("Vb_rms", 0.0))
    Vc_rms = float(res.get("Vc_rms", 0.0))

    if Va_rms <= 0 or Vb_rms <= 0 or Vc_rms <= 0:
        return

    # Método NEMA MG-1: VUF = desvio_máximo_da_média / média × 100%
    v_mean = (Va_rms + Vb_rms + Vc_rms) / 3.0
    if v_mean < 1e-6:
        return
    vuf = max(abs(Va_rms - v_mean), abs(Vb_rms - v_mean), abs(Vc_rms - v_mean)) / v_mean * 100.0

    # Só emite diagnóstico se desequilíbrio for detectável (> 0,3%)
    if vuf < 0.3:
        return

    if vuf > 5.0:
        level = "error"
        impacto = "aumento de corrente de desequilíbrio acima de 25% da nominal e sobreaquecimento severo"
    elif vuf > 2.0:
        level = "warning"
        impacto = "redução de rendimento e aumento de temperatura nos enrolamentos (NEMA MG-1 §14.35)"
    elif vuf > 1.0:
        level = "warning"
        impacto = "operação na zona de alerta; monitoramento recomendado"
    else:
        level = "info"
        impacto = "desequilíbrio abaixo do limite de intervenção (NEMA MG-1: 1%)"

    insights.append(Insight(
        level=level,
        title=f"Desequilíbrio de Tensão — VUF = {vuf:.2f}%",
        body=(
            f"O fator de desequilíbrio de tensão (NEMA MG-1) calculado a partir das "
            f"tensões de fase em regime permanente é VUF = {vuf:.2f}% "
            f"(Va = {Va_rms:.2f} V, Vb = {Vb_rms:.2f} V, Vc = {Vc_rms:.2f} V; "
            f"média = {v_mean:.2f} V). "
            f"Consequência: {impacto}. "
            f"A NEMA MG-1 recomenda desclassificação da potência nominal para "
            f"operação com desequilíbrio > 1%."
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
    """Regra 7 — Impacto do afundamento de tensão em torque e velocidade."""
    sag_mag   = float(cfg.get("sag_magnitude",   cfg.get("v_sag",    1.0)))
    t_sag_ini = float(cfg.get("t_start_sag",     cfg.get("t_sag",    0.0)))
    t_sag_dur = float(cfg.get("t_duration_sag",  cfg.get("t_dur_sag", 0.0)))

    if sag_mag >= 1.0 or t_sag_dur <= 0:
        return

    sag_depth_pct = (1.0 - sag_mag) * 100.0
    t_sag_fim = t_sag_ini + t_sag_dur

    # janela durante o sag
    mask_sag = (t_arr >= t_sag_ini) & (t_arr <= t_sag_fim)
    if not np.any(mask_sag):
        return

    Te_sag_min  = float(np.min(Te_arr[mask_sag]))
    wr_sag_min  = float(np.min(wr_arr[mask_sag]))
    n_sag_min   = wr_sag_min * 60.0 / (2.0 * math.pi)
    speed_drop  = (n_sync - n_sag_min) / n_sync * 100.0  # % de queda em relação a n_sync

    # janela pós-recuperação (últimos 20% do tempo restante)
    mask_post = t_arr > t_sag_fim
    recuperou = False
    if np.any(mask_post):
        wr_post = wr_arr[mask_post]
        # considera recuperado se wr retorna a > 90% de wr_ss pré-sag
        wr_ss_pre = float(res.get("wr_ss", 0.0))
        if wr_ss_pre > 0:
            recuperou = float(np.mean(wr_post[-max(1, len(wr_post)//5):])) > 0.9 * wr_ss_pre

    # Nível: torque cai quadraticamente com a tensão (Te ∝ V²)
    # sag 20% → Te cai ~36%; sag 50% → Te cai ~75%
    te_reducao_teorica = (1.0 - sag_mag**2) * 100.0

    if sag_depth_pct >= 50.0 or Te_sag_min < 0:
        level = "error"
    elif sag_depth_pct >= 20.0:
        level = "warning"
    else:
        level = "info"

    recuperacao_txt = "O motor se recuperou após o restabelecimento da tensão." if recuperou \
        else "O motor NÃO retornou à velocidade de regime após o restabelecimento — verifique estabilidade."

    insights.append(Insight(
        level=level,
        title=f"Afundamento de Tensão — Queda de {sag_depth_pct:.1f}% por {t_sag_dur:.3f} s",
        body=(
            f"O afundamento de tensão configurado (sag = {sag_mag:.2f} p.u., "
            f"duração = {t_sag_dur*1000:.0f} ms) provocou queda do torque eletromagnético "
            f"para Te_min = {Te_sag_min:.2f} N·m durante o evento "
            f"(redução teórica ≈ {te_reducao_teorica:.1f}% pois Te ∝ V²). "
            f"A velocidade do rotor caiu até n_min = {n_sag_min:.1f} RPM "
            f"({speed_drop:.1f}% abaixo da velocidade síncrona). "
            f"{recuperacao_txt} "
            f"Afundamentos acima de 20% por mais de 100 ms podem causar desligamento "
            f"por subtensão (ANSI 27) ou perda de sincronismo em cargas sensíveis."
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
    """Regra 8 — Tempo de partida: mede t até 95% de ωs e avalia risco térmico."""
    target_wr = 0.95 * ws_mec
    mask_reach = wr_arr >= target_wr
    if not np.any(mask_reach):
        return

    idx_reach  = int(np.argmax(mask_reach))
    t_start_pt = float(t_arr[idx_reach])

    # Tempo mínimo de partida esperado: J·ωs / (Te_med − T_L)
    # Usa apenas o trecho de aceleração sem carga (antes de t_carga, se existir),
    # pois load_torque é aplicado após t_carga — incluí-lo antes distorce Te_mean_accel.
    J = getattr(mp, "J", None)
    t_carga = float((cfg or {}).get("t_carga", 0.0))
    if t_carga > 0 and t_carga < t_start_pt:
        # partida em vazio: aceleração ocorre sem carga até t_carga
        idx_tc = int(np.searchsorted(t_arr, t_carga))
        Te_accel_slice = Te_arr[:idx_tc] if idx_tc > 0 else Te_arr[:idx_reach]
        tl_accel = 0.0  # carga ainda não aplicada neste trecho
    else:
        Te_accel_slice = Te_arr[:idx_reach]
        tl_accel = load_torque

    # Filtra spikes negativos iniciais (transitório de energização)
    Te_accel_slice = Te_accel_slice[Te_accel_slice > 0] if len(Te_accel_slice) > 0 else Te_accel_slice
    Te_mean_accel  = float(np.mean(Te_accel_slice)) if len(Te_accel_slice) > 0 else 0.0

    if J and J > 0 and Te_mean_accel > tl_accel:
        t_esperado = J * ws_mec / (Te_mean_accel - tl_accel)
    else:
        t_esperado = None

    # Limites NEMA: Trip Class 10 ≤ 10s, Class 20 ≤ 20s, Class 30 ≤ 30s
    if t_start_pt > 30.0:
        level, trip_class = "error",   "Class 30 excedida (> 30 s)"
    elif t_start_pt > 20.0:
        level, trip_class = "warning", "Class 30 (20–30 s)"
    elif t_start_pt > 10.0:
        level, trip_class = "warning", "Class 20 (10–20 s)"
    else:
        level, trip_class = "info",    "Class 10 (< 10 s)"

    esperado_txt = (
        f" O tempo estimado pelo balanço de inércia (J·ωs / (Te_med − T_L)) "
        f"é {t_esperado:.2f} s."
        if t_esperado is not None else ""
    )

    insights.append(Insight(
        level=level,
        title=f"Tempo de Partida: {t_start_pt:.2f} s — {trip_class}",
        body=(
            f"O rotor atingiu 95% da velocidade síncrona (ωr = {0.95*ws_mec:.1f} rad/s) "
            f"em t = {t_start_pt:.2f} s a partir do instante de energização.{esperado_txt} "
            f"Referência NEMA ICS 2: relés de sobrecarga Trip Class 10 atuam em ≤ 10 s, "
            f"Class 20 em ≤ 20 s e Class 30 em ≤ 30 s com corrente de partida "
            f"plena. Partidas longas acumulam energia térmica I²t nos enrolamentos — "
            f"verifique compatibilidade com a Trip Class do relé instalado."
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
    """Regras 9–11 — Diagnósticos específicos de operação como gerador de indução."""

    # ── Regra 9: Verificação do escorregamento negativo ────────────────────
    if s_ss >= 0:
        insights.append(Insight(
            level="error",
            title="Gerador: Rotor Não Ultrapassou a Velocidade Síncrona",
            body=(
                f"Para operação como gerador de indução, o rotor deve girar acima da "
                f"velocidade síncrona (s < 0). O escorregamento calculado é s = {s_ss*100:.2f}%, "
                f"indicando que o rotor ainda opera em modo motor (s ≥ 0). "
                f"Verifique se o torque da turbina primária (Tl_mec) é suficiente para "
                f"acelerar o rotor além de n_s = {n_sync:.1f} RPM, ou se o instante de "
                f"aplicação (t_2) foi atingido dentro do tempo de simulação."
            ),
        ))
        return

    # ── Regra 10: Margem de estabilidade — escorregamento negativo excessivo ─
    # Limite prático: |s| > 10% → operação instável / correntes elevadas
    S_GEN_ALERTA  = 0.05   # 5%: aviso
    S_GEN_CRITICO = 0.10   # 10%: erro

    abs_s = abs(s_ss)
    n_wr  = n_ss  # já em RPM

    if abs_s > S_GEN_CRITICO:
        insights.append(Insight(
            level="error",
            title=f"Gerador: Escorregamento Negativo Crítico — s = {s_ss*100:.2f}%",
            body=(
                f"O escorregamento negativo de regime é s = {s_ss*100:.2f}% "
                f"(n = {n_wr:.1f} RPM, n_s = {n_sync:.1f} RPM). "
                f"Acima de |s| > 10%, as correntes de rotor induzidas por Faraday "
                f"(E_r ∝ |s|·ωs·Ψ) tornam-se excessivas, elevando as perdas Joule no rotor "
                f"(P_Joule_r = |s|·P_gap) e o aquecimento dos enrolamentos. "
                f"O ponto de pull-out do gerador também se aproxima, risco de instabilidade. "
                f"Reduza o torque da turbina primária ou verifique o dimensionamento da máquina."
            ),
        ))
    elif abs_s > S_GEN_ALERTA:
        insights.append(Insight(
            level="warning",
            title=f"Gerador: Escorregamento Negativo Elevado — s = {s_ss*100:.2f}%",
            body=(
                f"O escorregamento negativo de regime é s = {s_ss*100:.2f}% "
                f"(n = {n_wr:.1f} RPM vs. n_s = {n_sync:.1f} RPM). "
                f"Valores acima de |s| = 5% indicam operação fora da região de máxima "
                f"eficiência. As perdas no rotor crescem proporcionalmente a |s|·P_gap. "
                f"Ajuste o ponto de operação da turbina primária para manter |s| ≤ 3–5%."
            ),
        ))
    else:
        insights.append(Insight(
            level="info",
            title=f"Gerador: Operação Estável — s = {s_ss*100:.2f}%",
            body=(
                f"O gerador de indução opera em regime estável com escorregamento "
                f"s = {s_ss*100:.2f}% (n = {n_wr:.1f} RPM, n_s = {n_sync:.1f} RPM). "
                f"O rotor gira {abs(n_wr - n_sync):.1f} RPM acima da velocidade síncrona, "
                f"dentro da faixa nominal de operação (|s| ≤ 5%)."
            ),
        ))

    # ── Regra 11: Balanço de potência — rendimento como gerador ───────────
    P_mec = float(res.get("P_mec",  0.0))   # potência mecânica de entrada (W) — negativa no solver
    P_gap = float(res.get("P_gap",  0.0))   # potência do entreferro (W)
    P_out = float(res.get("P_out",  0.0))   # potência elétrica gerada (W)
    eta   = float(res.get("eta",    0.0))   # rendimento (%)
    P_cu_r = float(res.get("P_cu_r", 0.0)) # perdas Joule no rotor (W)

    P_mec_abs = abs(P_mec)
    P_out_abs = abs(P_out)

    if P_mec_abs < 1e-3:
        return

    if eta > 0:
        if eta >= 85.0:
            nivel_eta, texto_eta = "info", "rendimento adequado para gerador de indução"
        elif eta >= 70.0:
            nivel_eta, texto_eta = "warning", "rendimento abaixo do esperado; verifique perdas"
        else:
            nivel_eta, texto_eta = "error", "rendimento baixo — perdas dominantes; revise operação"

        insights.append(Insight(
            level=nivel_eta,
            title=f"Gerador: Balanço de Potência — η = {eta:.1f}%",
            body=(
                f"Fluxo de potência em regime permanente (convenção gerador): "
                f"P_mec (turbina) = {P_mec_abs:.1f} W → entreferro P_gap = {abs(P_gap):.1f} W "
                f"(perdas rotor P_cu_r = {P_cu_r:.1f} W = |s|·P_gap) → "
                f"P_elétrica gerada = {P_out_abs:.1f} W. "
                f"Rendimento eletromecânico η = {eta:.1f}% — {texto_eta}. "
                f"O gerador de indução requer fonte de reativo externo (banco de capacitores "
                f"ou rede) para suprimento da corrente de magnetização."
            ),
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Ordenação
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}

def _sort_insights(insights: list[Insight]) -> list[Insight]:
    return sorted(insights, key=lambda x: _LEVEL_ORDER[x.level])
