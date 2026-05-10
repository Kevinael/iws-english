# -*- coding: utf-8 -*-
"""
solver.py — Integracao numerica e pos-processamento do modelo Krause

Exporta:
  _solve                  — integra o ODE via LSODA; suporta clamp wr=0 e t_cutoff
  _voltages_vectorized    — reconstroi Va/Vb/Vc para todo o vetor t
  _reconstruct_currents   — correntes dq e abc a partir dos estados
  _detect_steady_state    — detecta indice de inicio do regime permanente
  _compute_steady_state   — RMS, medias e balanco de potencias em regime
  _compute_thermal        — integra EDO termica em pos-processamento sobre P_joule vetorizado

Constantes de integracao/analise (importadas por EMS_PY para compatibilidade):
  SS_TOL, MIN_SS_CYCLES, NYQUIST_LIMIT, F_ROTOR_FLOOR
  RTOL, ATOL, MAX_STEP_FACTOR

Documentacao detalhada de cada decisao de implementacao:
  SME/2. Modulos/core/solver.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (secoes 3-5)
"""

from __future__ import annotations
import math
import warnings
import numpy as np
from scipy.integrate import solve_ivp

from core.machine_model import MachineParams
from core.transforms import abc_voltages, clarke_park_transform, _SQRT3_2
from core.desequilibrio_falta import abc_voltages_deseq


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════

SS_TOL          = 0.005   # tolerancia relativa de wr para declarar regime (0.5%)
MIN_SS_CYCLES   = 5       # minimo de ciclos eletricos consecutivos em regime
NYQUIST_LIMIT   = 0.05    # h*f maximo — abaixo de 20 amostras/ciclo o RMS fica impreciso
F_ROTOR_FLOOR   = 0.01    # Hz — piso de f_rotor para evitar LCM astronomico em s≈0

RTOL            = 1e-6    # tolerancia relativa do LSODA
ATOL            = 1e-9    # tolerancia absoluta — fisicamente significativa em Wb e rad/s
MAX_STEP_FACTOR = 20.0    # max_step = 1/(20*f) garante >=20 amostras/ciclo ao LSODA


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRADOR
# ═══════════════════════════════════════════════════════════════════════════

def _solve(rhs, t_values, y0, mp: MachineParams, clamp_wr_at_zero: bool, t_cutoff=None):
    """Integra o ODE; suporta restart em t_cutoff e clamp wr=0 no shutdown.

    Segmentacao: t_cutoff forca reinicio do integrador na descontinuidade de tensao
    (shutdown). clamp_wr_at_zero adiciona evento terminal e segmento com dwr=0.
    Ver SME/2. Modulos/core/solver.md — secao _solve e Guia de Leitura do Codigo secao 3.

    Returns:
        y_history shape (8, N).
    """
    tmax     = float(t_values[-1])
    max_step = 1.0 / (MAX_STEP_FACTOR * mp.f)
    N        = len(t_values)

    def _run(rhs_fn, t_span, y_init, t_eval):
        sol = solve_ivp(rhs_fn, t_span, y_init, t_eval=t_eval,
                        method='LSODA', rtol=RTOL, atol=ATOL, max_step=max_step)
        if not sol.success:
            warnings.warn(f"solve_ivp falhou: {sol.message}")
        return sol

    def _fill(y_history, offset, sol):
        # escreve diretamente no buffer pre-alocado; evita concatenacao de arrays
        n = sol.y.shape[1]
        y_history[:, offset:offset + n] = sol.y
        return offset + n

    def _ffill(arr):
        # propaga o ultimo valor finito para frente — correto para motor parado
        # vetorizado: indices de valores finitos acumulados por linha
        for row in range(arr.shape[0]):
            r = arr[row]
            finite = np.isfinite(r)
            if not finite.any():
                continue
            idx = np.where(finite, np.arange(len(r)), 0)
            np.maximum.accumulate(idx, out=idx)
            arr[row] = r[idx]

    # NaN como sentinela: posicoes nao preenchidas pelo LSODA serao ffill'd depois
    y_history = np.full((8, N), np.nan)

    if not clamp_wr_at_zero:
        if t_cutoff is not None and t_cutoff < tmax:
            mask_a = t_values <= t_cutoff
            mask_b = t_values >  t_cutoff
            t_a    = t_values[mask_a]
            t_b    = t_values[mask_b]
            sol_a  = _run(rhs, [t_values[0], t_cutoff], y0, t_a)
            off    = _fill(y_history, 0, sol_a)
            if t_b.size > 0:
                sol_b = _run(rhs, [t_cutoff, tmax], sol_a.y[:, -1], t_b)
                _fill(y_history, off, sol_b)
        else:
            sol = _run(rhs, [t_values[0], tmax], y0, t_values)
            y_history[:, :sol.y.shape[1]] = sol.y
        _ffill(y_history)
        return y_history

    # modo shutdown: clamp wr=0 apos evento
    # y[4] = wr eletrico; threshold = 1% da velocidade sincrona
    # direction=-1: detecta apenas descida (evita disparo espurio na partida)
    _ws        = mp.wb / (mp.p / 2.0)
    _threshold = 0.01 * _ws

    def event_wr_zero(t, y):
        return y[4] - _threshold
    event_wr_zero.terminal  = True
    event_wr_zero.direction = -1

    if t_cutoff is not None and t_cutoff < tmax:
        mask_a = t_values <= t_cutoff
        mask_b = t_values >  t_cutoff
        t_a    = t_values[mask_a]
        t_b    = t_values[mask_b]

        sol_a = _run(rhs, [t_values[0], t_cutoff], y0, t_a)
        off   = _fill(y_history, 0, sol_a)
        y_cut = sol_a.y[:, -1]

        if t_b.size > 0:
            sol_b = solve_ivp(rhs, [t_cutoff, tmax], y_cut, t_eval=t_b,
                              method='LSODA', rtol=RTOL, atol=ATOL,
                              max_step=max_step, events=event_wr_zero)
            n_b = sol_b.y.shape[1]
            y_history[:, off:off + n_b] = sol_b.y

            if sol_b.t_events[0].size > 0 and off + n_b < N:
                t_ev    = float(sol_b.t_events[0][0])
                y_ev    = sol_b.y_events[0][0].copy()
                y_ev[4] = 0.0

                # rhs_clamped: mesmo RHS mas forca dwr=0 — wr permanece em zero
                # os demais estados (fluxos, temperatura) continuam evoluindo
                def rhs_clamped(t, y):
                    d    = rhs(t, y)
                    d[4] = 0.0
                    return d

                t_rest = t_values[off + n_b:]
                sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
                n_c    = sol_c.y.shape[1]
                y_history[:, off + n_b:off + n_b + n_c] = sol_c.y
                if off + n_b + n_c < N:
                    # preenche o restante com o ultimo estado (motor parado)
                    y_history[:, off + n_b + n_c:] = sol_c.y[:, -1:]
    else:
        sol_b = solve_ivp(rhs, [t_values[0], tmax], y0, t_eval=t_values,
                          method='LSODA', rtol=RTOL, atol=ATOL,
                          max_step=max_step, events=event_wr_zero)
        n_b = sol_b.y.shape[1]
        y_history[:, :n_b] = sol_b.y

        if sol_b.t_events[0].size > 0 and n_b < N:
            t_ev    = float(sol_b.t_events[0][0])
            y_ev    = sol_b.y_events[0][0].copy()
            y_ev[4] = 0.0

            def rhs_clamped(t, y):
                d    = rhs(t, y)
                d[4] = 0.0
                return d

            t_rest = t_values[n_b:]
            sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
            n_c    = sol_c.y.shape[1]
            y_history[:, n_b:n_b + n_c] = sol_c.y
            if n_b + n_c < N:
                y_history[:, n_b + n_c:] = sol_c.y[:, -1:]

    _ffill(y_history)
    return y_history


# ═══════════════════════════════════════════════════════════════════════════
# POS-PROCESSAMENTO
# ═══════════════════════════════════════════════════════════════════════════

def _voltages_vectorized(t_arr, Vl_arr, mp: MachineParams, deseq, t_deseq, deseq_active):
    """Reconstroi Va/Vb/Vc para todo o vetor t (suporta switch em t_deseq)."""
    if not deseq_active:
        return abc_voltages(t_arr, Vl_arr, mp.f)
    Va_b, Vb_b, Vc_b = abc_voltages(t_arr, Vl_arr, mp.f)
    Va_u, Vb_u, Vc_u = abc_voltages_deseq(t_arr, Vl_arr, mp.f, *deseq)
    mask = t_arr >= t_deseq
    return (np.where(mask, Va_u, Va_b),
            np.where(mask, Vb_u, Vb_b),
            np.where(mask, Vc_u, Vc_b))


def _reconstruct_currents(PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp: MachineParams):
    """Reconstrucao vetorizada de correntes dq e abc (estator e rotor).

    Opera sobre arrays inteiros [N] — chamada uma unica vez apos a integracao.
    Sequencia: fluxos -> correntes dq -> Park inversa -> Clarke inversa -> abc.
    Ver SME/2. Modulos/core/solver.md — secao _reconstruct_currents.
    """
    # fluxo mutuo: Xml redistribui o fluxo total entre estator e rotor
    PSImq = mp.Xml * (PSIqs / mp.Xls_a_eff + PSIqr / mp.Xlr_a)
    PSImd = mp.Xml * (PSIds / mp.Xls_a_eff + PSIdr / mp.Xlr_a)
    # corrente de dispersao = (fluxo total - fluxo mutuo) / reatancia de dispersao
    ids = (PSIds - PSImd) / mp.Xls_a_eff
    iqs = (PSIqs - PSImq) / mp.Xls_a_eff
    idr = (PSIdr - PSImd) / mp.Xlr_a
    iqr = (PSIqr - PSImq) / mp.Xlr_a

    # Park inversa: P^{-1} = P^T (matriz ortogonal) — troca sinal de sin
    cos_e, sin_e = np.cos(tetae), np.sin(tetae)
    cos_r, sin_r = np.cos(tetar), np.sin(tetar)
    iafs = ids * cos_e - iqs * sin_e   # componente alpha do estator (frame estatico)
    ibts = ids * sin_e + iqs * cos_e   # componente beta do estator
    iafr = idr * cos_r - iqr * sin_r   # componente alpha do rotor
    ibtr = idr * sin_r + iqr * cos_r   # componente beta do rotor

    # Clarke inversa amplitude-invariante: k = sqrt(3/2)
    k    = np.sqrt(3.0 / 2.0)
    sq32 = _SQRT3_2
    ias = k * iafs
    ibs = k * (-0.5 * iafs + sq32 * ibts)
    ics = k * (-0.5 * iafs - sq32 * ibts)
    iar = k * iafr
    ibr = k * (-0.5 * iafr + sq32 * ibtr)
    icr = k * (-0.5 * iafr - sq32 * ibtr)
    return ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr


def _detect_steady_state(t_arr, wr_arr, mp: MachineParams) -> int:
    """Detecta o indice de inicio do regime permanente.

    Fase 1: encontra o ultimo ponto fora de SS_TOL em relacao a wr_ref.
    Fase 2: ajusta a janela para ser multipla do LCM(ciclo_eletrico, ciclo_rotor)
            eliminando vies espectral no calculo de RMS.
    Ver SME/2. Modulos/core/solver.md — secao _detect_steady_state.
    """
    N = len(t_arr)
    h = float(t_arr[1] - t_arr[0]) if N > 1 else 1e-4
    samples_per_cycle = max(1, int(round(1.0 / (mp.f * h))))
    min_ss            = MIN_SS_CYCLES * samples_per_cycle

    wr_arr = np.where(np.isfinite(wr_arr), wr_arr, 0.0)
    # referencia = media dos ultimos min_ss pontos (assumidos em regime)
    wr_ref = float(np.mean(wr_arr[-min_ss:])) if N >= min_ss else float(np.mean(wr_arr))

    if abs(wr_ref) < 1e-12:
        ss_start = 0
    else:
        rel_dev   = np.abs((wr_arr[:-min_ss] - wr_ref) / wr_ref)
        violators = np.where(rel_dev > SS_TOL)[0]
        # +1 porque o regime comeca no ponto APOS o ultimo violador
        ss_start  = int(violators[-1]) + 1 if violators.size else 0

    # estimativa provisoria de s para calcular f_rotor
    ss_len_tmp = max(N - ss_start, min_ss)
    wr_med_tmp = float(np.mean(wr_arr[max(0, N - ss_len_tmp):]))
    ws         = mp.wb / (mp.p / 2.0)
    s_tmp      = (ws - wr_med_tmp) / ws if ws != 0 else 0.0

    # F_ROTOR_FLOOR evita lcm_samples astronomico quando s≈0 (operacao a vazio)
    f_rotor = max(abs(s_tmp) * mp.f, F_ROTOR_FLOOR)
    samples_per_rotor_cycle = max(1, int(round(1.0 / (f_rotor * h))))

    # janela alinhada ao LCM elimina vies de RMS por periodo incompleto
    lcm_samples = math.lcm(samples_per_cycle, samples_per_rotor_cycle)
    lcm_samples = min(lcm_samples, N // 2)

    ss_len   = max(N - ss_start, min_ss)
    ss_len   = max(ss_len // lcm_samples, 1) * lcm_samples
    ss_start = max(0, N - ss_len)
    return ss_start


def _compute_thermal(
    t_arr: np.ndarray,
    ias: np.ndarray, ibs: np.ndarray, ics: np.ndarray,
    iar: np.ndarray, ibr: np.ndarray, icr: np.ndarray,
    PSImq: np.ndarray, PSImd: np.ndarray,
    mp: MachineParams,
    rr_arr: np.ndarray | None = None,
) -> np.ndarray:
    """Integra a EDO térmica em pós-processamento sobre os arrays de corrente já integrados.

    Usa correntes de fase abc (não dq de dispersão) para P_joule, o que é correto
    para o modelo de perdas em motores de indução com convenção amplitude-invariante.
    Separar a térmica do ODE eletromagnético elimina o erro de discretização causado
    pelo pico de inrush: o LSODA resolve o ODE com passo adaptativo, e a EDO térmica
    (tau_th ~ 1500 s) é integrada via Euler implícito sobre esses arrays.

    Args:
        rr_arr: array de Rr efetivo ao longo do tempo (barra quebrada). None = Rr constante.
    """
    N      = len(t_arr)
    h      = float(t_arr[1] - t_arr[0]) if N > 1 else 1e-3
    Rr_arr = rr_arr if rr_arr is not None else np.full(N, mp.Rr)

    # P_joule via correntes abc com fator de escala da convenção amplitude-invariante:
    # ias = sqrt(3/2)*iafs => ias² = (3/2)*iafs²  => P_abc = (3/2)*P_dq
    # Fator correto: P = (2/3)*soma_abc = P_dq
    P_joule = (2.0 / 3.0) * (
        mp.Rs * (ias**2 + ibs**2 + ics**2)
        + Rr_arr * (iar**2 + ibr**2 + icr**2)
    )
    P_fe = (mp.wb * (PSImq**2 + PSImd**2) / mp.Rfe
            if mp.Rfe > 0.0 else np.zeros(N))
    P_total = P_joule + P_fe

    # Os primeiros ~5 ciclos elétricos concentram o pico de inrush de magnetização
    # (fluxos partem de zero): energia real insignificante (< 0.5°C) mas P instantâneo
    # muito alto. Tratar esses pontos como P = P_nom_estimado evita aquecimento
    # artificial sem afetar a dinâmica térmica relevante (tau_th ~ 1500 s >> 5/f).
    n_skip = max(0, int(round(5.0 / (mp.f * h))))   # 5 ciclos elétricos em amostras
    if n_skip > 0 and n_skip < N:
        # valor de referência: P médio da janela logo após o pico de inrush
        win_ref = min(n_skip, N - n_skip)
        P_ref   = float(np.mean(P_total[n_skip: n_skip + win_ref])) if win_ref > 0 else 0.0
        P_total[:n_skip] = P_ref

    # Euler implícito: estável para qualquer dt, correto para tau_th >> dt
    #   T[k+1] = (T[k] + dt*(P[k+1]/Cth + T_amb/(Rth*Cth))) / (1 + dt/(Rth*Cth))
    Rth = mp.Rth; Cth = mp.Cth; T_amb = mp.T_amb
    Temp = np.empty(N)
    Temp[0] = T_amb
    for k in range(N - 1):
        dt    = float(t_arr[k + 1] - t_arr[k])
        alpha = dt / (Rth * Cth)
        Temp[k + 1] = (Temp[k] + dt * (P_total[k + 1] / Cth + T_amb / (Rth * Cth))) / (1.0 + alpha)

    return np.where(np.isfinite(Temp), Temp, T_amb)


def _compute_steady_state(arr: dict, mp: MachineParams) -> dict:
    """Calcula medias, RMS e balanco de potencias na janela de regime permanente.

    Balanco: P_gap = Te_med * ws; P_cu_r = s*P_gap; P_mec = (1-s)*P_gap.
    Modo gerador (s<0): fluxo de potencia invertido — ver SME/2. Modulos/core/solver.md.
    """
    t_arr  = arr["t"]
    wr_arr = arr["wr"]
    N      = len(t_arr)
    ss_start = _detect_steady_state(t_arr, wr_arr, mp)
    sl       = slice(ss_start, None)

    # substitui NaN por 0 antes de medias — NaN indica falha numerica pontual
    def _safe_mean(a):
        return float(np.mean(np.where(np.isfinite(a), a, 0.0)))

    Te_med = _safe_mean(arr["Te"][sl])
    wr_med = _safe_mean(arr["wr"][sl])
    n_med  = _safe_mean(arr["n"][sl])

    ws     = mp.wb / (mp.p / 2.0)
    s      = (ws - wr_med) / ws if ws != 0 else 0.0
    P_gap  = Te_med * ws
    P_cu_r = s * P_gap
    P_mec  = (1.0 - s) * P_gap

    out: dict = {}
    rms_keys = ("ias", "ibs", "ics", "iar", "ibr", "icr",
                "ids", "iqs", "idr", "iqr",
                "Va",  "Vb",  "Vc",  "Vds", "Vqs")
    for k in rms_keys:
        vals = np.where(np.isfinite(arr[k][sl]), arr[k][sl], 0.0)
        out[f"{k}_rms"] = float(np.sqrt(np.mean(vals ** 2)))

    P_cu_s = mp.Rs * (out["ias_rms"]**2 + out["ibs_rms"]**2 + out["ics_rms"]**2)

    V_phase_avg = (out["Va_rms"] + out["Vb_rms"] + out["Vc_rms"]) / 3.0
    P_fe = 3.0 * V_phase_avg**2 / mp.Rfe if mp.Rfe > 0 else 0.0

    if s >= 0:
        # modo motor: entrada eletrica, saida mecanica
        P_in  = P_gap + P_cu_s + P_fe
        P_out = P_mec
    else:
        # modo gerador (s<0): entrada mecanica, saida eletrica
        P_in  = abs(P_mec)
        P_out = max(0.0, abs(P_gap) - P_cu_s - P_fe)
    eta = (P_out / P_in * 100.0) if P_in > 0 else 0.0

    out.update({
        "P_gap": P_gap,   "P_cu_r": P_cu_r, "P_mec": P_mec,
        "P_cu_s": P_cu_s, "P_fe": P_fe,
        "P_in":  P_in,    "P_out": P_out,   "eta": eta,
        "s": s,  "n_ss": n_med,  "wr_ss": wr_med,  "Te_ss": Te_med,
        "_ss_start": ss_start,
    })
    return out
