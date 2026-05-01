# -*- coding: utf-8 -*-
"""
EMS_PY.py — Núcleo físico do Simulador de Máquinas Elétricas
Modelo 0dq de Krause — integração via scipy.solve_ivp (LSODA).

Exporta:
  MachineParams       — dataclass com todos os parâmetros da máquina
  run_simulation      — integra o ODE e retorna dict com séries temporais
  build_fns           — monta funções de tensão e torque para cada experimento
"""

from __future__ import annotations
import math
import warnings
import numpy as np
from scipy.integrate import solve_ivp
from dataclasses import dataclass, field
from core.desequilibrio_falta import abc_voltages_deseq


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES DE INTEGRAÇÃO E ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════
SS_TOL          = 0.005   # tolerância relativa p/ detectar regime permanente em wr
MIN_SS_CYCLES   = 5       # janela mínima de regime: 5 ciclos da fundamental
NYQUIST_LIMIT   = 0.05    # avisa quando h*f > 0.05 (< 20 amostras/ciclo)
F_ROTOR_FLOOR   = 0.01    # Hz, evita div/0 no cálculo do ciclo do rotor

# Tolerâncias do solver — equivalentes ao default do odeint, mas conservadoras
RTOL            = 1e-6
ATOL            = 1e-9
MAX_STEP_FACTOR = 20.0    # max_step = 1/(MAX_STEP_FACTOR · f) → ≥20 passos/ciclo


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO A — MODELO MATEMATICO
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MachineParams:
    Vl:    float = 220.0
    f:     float = 60.0
    Rs:    float = 0.435
    Rr:    float = 0.816
    Xm:    float = 26.13
    Xls:   float = 0.754
    Xlr:   float = 0.754
    Rfe:   float = 500.0   # resistência de perdas no ferro (Ω) — usada no balanço de potências
    p:     int   = 4
    J:     float = 0.089
    B:     float = 0.005   # atrito + ventilação ≈ 1% de P_nom para motor ~15 kW
    # --- modo de entrada dos parâmetros magnéticos ---
    # input_mode = "X"  : Xm/Xls/Xlr são reatâncias (Ω) medidas em f_ref Hz
    # input_mode = "L"  : Xm/Xls/Xlr são na verdade indutâncias (H) — f_ref é ignorado
    input_mode: str   = "X"   # "X" ou "L"
    f_ref:      float = 60.0  # frequência em que as reatâncias foram ensaiadas (Hz)
    Xml:   float = field(init=False)
    wb:    float = field(init=False)
    Lm:    float = field(init=False)
    Lls:   float = field(init=False)
    Llr:   float = field(init=False)
    Xls_a: float = field(init=False)
    Xlr_a: float = field(init=False)

    def __post_init__(self) -> None:
        self.wb = 2.0 * np.pi * self.f
        if self.input_mode == "L":
            self.Lm  = self.Xm
            self.Lls = self.Xls
            self.Llr = self.Xlr
        else:
            _wb_ref  = 2.0 * np.pi * self.f_ref
            self.Lm  = self.Xm  / _wb_ref
            self.Lls = self.Xls / _wb_ref
            self.Llr = self.Xlr / _wb_ref
        self.Xls_a = self.wb * self.Lls
        self.Xlr_a = self.wb * self.Llr
        _Xm_a      = self.wb * self.Lm
        self.Xml   = 1.0 / (1.0/_Xm_a + 1.0/self.Xls_a + 1.0/self.Xlr_a)

    @property
    def n_sync(self) -> float:
        return 120.0 * self.f / self.p


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO B — TRANSFORMADAS E FONTES
# ═══════════════════════════════════════════════════════════════════════════

def abc_voltages(t, Vl, f):
    """Tensões abc balanceadas (vetorizada — t e Vl podem ser escalares ou arrays)."""
    tetae = 2.0*np.pi*f*t
    Va = np.sqrt(2.0/3.0)*Vl*np.sin(tetae)
    Vb = np.sqrt(2.0/3.0)*Vl*np.sin(tetae - 2.0*np.pi/3.0)
    Vc = np.sqrt(2.0/3.0)*Vl*np.sin(tetae + 2.0*np.pi/3.0)
    return Va, Vb, Vc


def clarke_park_transform(Va, Vb, Vc, tetae):
    """Clarke (potência-invariante) + Park: abc → dq síncrono."""
    k = np.sqrt(3.0/2.0)
    Vaf = k*(Va - 0.5*Vb - 0.5*Vc)
    Vbt = k*(np.sqrt(3.0)/2.0*Vb - np.sqrt(3.0)/2.0*Vc)
    Vds =  np.cos(tetae)*Vaf + np.sin(tetae)*Vbt
    Vqs = -np.sin(tetae)*Vaf + np.cos(tetae)*Vbt
    return Vds, Vqs


def voltage_reduced_start(t, Vl_nominal, Vl_reduced, t_switch):
    return Vl_nominal if t >= t_switch else Vl_reduced


def voltage_soft_starter(t, Vl_nominal, Vl_initial, t_start_ramp, t_full):
    if t < t_start_ramp:
        return Vl_initial
    elif t < t_full:
        return Vl_initial + (Vl_nominal - Vl_initial)*(t - t_start_ramp)/(t_full - t_start_ramp)
    return Vl_nominal


def torque_step(t, Tl_before, Tl_after, t_switch):
    return Tl_after if t >= t_switch else Tl_before


def torque_pulse(t, Tl_base, Tl_pulso, t_on, t_off):
    """Tl_base fora do pulso; Tl_pulso em [t_on, t_off)."""
    return Tl_pulso if t_on <= t < t_off else Tl_base


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO C — RHS DO ODE (Krause, 6 estados: PSIqs, PSIds, PSIqr, PSIdr, wr, tetar)
# ═══════════════════════════════════════════════════════════════════════════

def _make_rhs(mp, voltage_fn, torque_fn, ref_code,
              deseq, t_deseq, deseq_active):
    """Fecha o RHS sobre os parâmetros para uso em solve_ivp."""
    Xls_a = mp.Xls_a; Xlr_a = mp.Xlr_a; Xml = mp.Xml
    Rs    = mp.Rs;    Rr    = mp.Rr;    wb  = mp.wb
    p     = mp.p;     J     = mp.J;     B   = mp.B

    def rhs(t, y):
        PSIqs, PSIds, PSIqr, PSIdr, wr, _tetar = y

        Vl_a = voltage_fn(t)
        Tl_a = torque_fn(t)
        if deseq_active and t >= t_deseq:
            Va, Vb, Vc = abc_voltages_deseq(t, Vl_a, mp.f, *deseq)
        else:
            Va, Vb, Vc = abc_voltages(t, Vl_a, mp.f)
        tetae = wb * t
        Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae)

        if   ref_code == 1: w_ref = wb
        elif ref_code == 2: w_ref = wr
        else:               w_ref = 0.0

        PSImq = Xml*(PSIqs/Xls_a + PSIqr/Xlr_a)
        PSImd = Xml*(PSIds/Xls_a + PSIdr/Xlr_a)
        iqs = (PSIqs - PSImq) / Xls_a
        ids = (PSIds - PSImd) / Xls_a

        dPSIqs = wb * (Vqs - (w_ref/wb)*PSIds + (Rs/Xls_a)*(PSImq - PSIqs))
        dPSIds = wb * (Vds + (w_ref/wb)*PSIqs + (Rs/Xls_a)*(PSImd - PSIds))
        slip_ref = (w_ref - wr) / wb
        dPSIqr = wb * (-slip_ref*PSIdr + (Rr/Xlr_a)*(PSImq - PSIqr))
        dPSIdr = wb * ( slip_ref*PSIqr + (Rr/Xlr_a)*(PSImd - PSIdr))

        Te  = (3.0/2.0)*(p/2.0)*(1.0/wb)*(PSIds*iqs - PSIqs*ids)
        dwr = (p/(2.0*J))*(Te - Tl_a) - (B/J)*wr
        dtetar = wr   # ângulo elétrico do rotor
        return [dPSIqs, dPSIds, dPSIqr, dPSIdr, dwr, dtetar]

    return rhs


def _solve(rhs, t_values, y0, mp, clamp_wr_at_zero, t_cutoff=None):
    """Integra o ODE; suporta restart em t_cutoff e clamp de wr=0 no shutdown.

    Retorna y_history shape (6, N).
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
        """Copia sol.y para y_history a partir de offset; retorna próximo offset."""
        n = sol.y.shape[1]
        y_history[:, offset:offset+n] = sol.y
        return offset + n

    def _ffill(arr):
        """Forward-fill NaN coluna a coluna."""
        for i in range(1, arr.shape[1]):
            mask = ~np.isfinite(arr[:, i])
            arr[:, i] = np.where(mask, arr[:, i-1], arr[:, i])

    y_history = np.full((6, N), np.nan)

    if not clamp_wr_at_zero:
        # integração simples, sem eventos
        if t_cutoff is not None and t_cutoff < tmax:
            # divide em dois segmentos para evitar divergência na descontinuidade
            mask_a = t_values <= t_cutoff
            mask_b = t_values >  t_cutoff
            t_a = t_values[mask_a]
            t_b = t_values[mask_b]
            sol_a = _run(rhs, [t_values[0], t_cutoff], y0, t_a)
            off = _fill(y_history, 0, sol_a)
            if t_b.size > 0:
                y_restart = sol_a.y[:, -1]
                sol_b = _run(rhs, [t_cutoff, tmax], y_restart, t_b)
                _fill(y_history, off, sol_b)
        else:
            sol = _run(rhs, [t_values[0], tmax], y0, t_values)
            y_history[:, :sol.y.shape[1]] = sol.y
        _ffill(y_history)
        return y_history

    # ── modo shutdown: divide em t_cutoff + clamp wr=0 ──────────────────────
    _ws        = mp.wb / (mp.p / 2.0)
    _threshold = 0.01 * _ws

    def event_wr_zero(t, y):
        return y[4] - _threshold
    event_wr_zero.terminal  = True
    event_wr_zero.direction = -1

    # segmento A: t0 → t_cutoff (motor acelerando/em carga, sem evento)
    if t_cutoff is not None and t_cutoff < tmax:
        mask_a = t_values <= t_cutoff
        mask_b = t_values >  t_cutoff
        t_a = t_values[mask_a]
        t_b = t_values[mask_b]

        sol_a = _run(rhs, [t_values[0], t_cutoff], y0, t_a)
        off   = _fill(y_history, 0, sol_a)
        y_cut = sol_a.y[:, -1]

        # segmento B: t_cutoff → tmax, com evento de parada
        if t_b.size > 0:
            sol_b = solve_ivp(rhs, [t_cutoff, tmax], y_cut, t_eval=t_b,
                              method='LSODA', rtol=RTOL, atol=ATOL,
                              max_step=max_step, events=event_wr_zero)
            n_b = sol_b.y.shape[1]
            y_history[:, off:off+n_b] = sol_b.y

            if sol_b.t_events[0].size > 0 and off + n_b < N:
                t_ev   = float(sol_b.t_events[0][0])
                y_ev   = sol_b.y_events[0][0].copy()
                y_ev[4] = 0.0

                def rhs_clamped(t, y):
                    d = rhs(t, y)
                    d[4] = 0.0
                    return d

                t_rest = t_values[off+n_b:]
                sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
                n_c    = sol_c.y.shape[1]
                y_history[:, off+n_b:off+n_b+n_c] = sol_c.y
                if off + n_b + n_c < N:
                    y_history[:, off+n_b+n_c:] = sol_c.y[:, -1:]
    else:
        # sem t_cutoff definido — integração com evento direto
        sol_b = solve_ivp(rhs, [t_values[0], tmax], y0, t_eval=t_values,
                          method='LSODA', rtol=RTOL, atol=ATOL,
                          max_step=max_step, events=event_wr_zero)
        n_b = sol_b.y.shape[1]
        y_history[:, :n_b] = sol_b.y

        if sol_b.t_events[0].size > 0 and n_b < N:
            t_ev   = float(sol_b.t_events[0][0])
            y_ev   = sol_b.y_events[0][0].copy()
            y_ev[4] = 0.0

            def rhs_clamped(t, y):
                d = rhs(t, y)
                d[4] = 0.0
                return d

            t_rest = t_values[n_b:]
            sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
            n_c    = sol_c.y.shape[1]
            y_history[:, n_b:n_b+n_c] = sol_c.y
            if n_b + n_c < N:
                y_history[:, n_b+n_c:] = sol_c.y[:, -1:]

    _ffill(y_history)
    return y_history


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO D — PÓS-PROCESSAMENTO (vetorizado)
# ═══════════════════════════════════════════════════════════════════════════

def _voltages_vectorized(t_arr, Vl_arr, mp, deseq, t_deseq, deseq_active):
    """Reconstrói Va/Vb/Vc para todo o vetor t (suporta switch em t_deseq)."""
    if not deseq_active:
        return abc_voltages(t_arr, Vl_arr, mp.f)
    Va_b, Vb_b, Vc_b = abc_voltages(t_arr, Vl_arr, mp.f)
    Va_u, Vb_u, Vc_u = abc_voltages_deseq(t_arr, Vl_arr, mp.f, *deseq)
    mask = t_arr >= t_deseq
    return (np.where(mask, Va_u, Va_b),
            np.where(mask, Vb_u, Vb_b),
            np.where(mask, Vc_u, Vc_b))


def _reconstruct_currents(PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp):
    """Reconstrução vetorizada de correntes dq e abc (estator e rotor)."""
    PSImq = mp.Xml*(PSIqs/mp.Xls_a + PSIqr/mp.Xlr_a)
    PSImd = mp.Xml*(PSIds/mp.Xls_a + PSIdr/mp.Xlr_a)
    ids = (PSIds - PSImd) / mp.Xls_a
    iqs = (PSIqs - PSImq) / mp.Xls_a
    idr = (PSIdr - PSImd) / mp.Xlr_a
    iqr = (PSIqr - PSImq) / mp.Xlr_a

    cos_e, sin_e = np.cos(tetae), np.sin(tetae)
    cos_r, sin_r = np.cos(tetar), np.sin(tetar)
    iafs = ids*cos_e - iqs*sin_e
    ibts = ids*sin_e + iqs*cos_e
    iafr = idr*cos_r - iqr*sin_r
    ibtr = idr*sin_r + iqr*cos_r

    k    = np.sqrt(3.0/2.0)
    sq32 = np.sqrt(3.0)/2.0
    ias = k*iafs
    ibs = k*(-0.5*iafs + sq32*ibts)
    ics = k*(-0.5*iafs - sq32*ibts)
    iar = k*iafr
    ibr = k*(-0.5*iafr + sq32*ibtr)
    icr = k*(-0.5*iafr - sq32*ibtr)
    return ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr


def _detect_steady_state(t_arr, wr_arr, mp):
    """Detecta o início do regime permanente (vetorizado)."""
    N = len(t_arr)
    h = float(t_arr[1] - t_arr[0]) if N > 1 else 1e-4
    samples_per_cycle = max(1, int(round(1.0 / (mp.f * h))))
    min_ss            = MIN_SS_CYCLES * samples_per_cycle

    # substitui NaN por zero para não propagar para int()
    wr_arr = np.where(np.isfinite(wr_arr), wr_arr, 0.0)

    wr_ref = float(np.mean(wr_arr[-min_ss:])) if N >= min_ss else float(np.mean(wr_arr))

    # varredura vetorizada: último índice onde wr ainda violava a tolerância
    if abs(wr_ref) < 1e-12:
        ss_start = 0
    else:
        rel_dev   = np.abs((wr_arr[:-min_ss] - wr_ref) / wr_ref)
        violators = np.where(rel_dev > SS_TOL)[0]
        ss_start  = int(violators[-1]) + 1 if violators.size else 0

    # estima escorregamento → ciclo do rotor (assume ref_code=1, rotor abc oscila a |s|·f)
    ss_len_tmp = max(N - ss_start, min_ss)
    wr_med_tmp = float(np.mean(wr_arr[max(0, N - ss_len_tmp):]))
    ws         = mp.wb / (mp.p / 2.0)
    s_tmp      = (ws - wr_med_tmp) / ws if ws != 0 else 0.0

    f_rotor = max(abs(s_tmp) * mp.f, F_ROTOR_FLOOR)
    samples_per_rotor_cycle = max(1, int(round(1.0 / (f_rotor * h))))

    lcm_samples = math.lcm(samples_per_cycle, samples_per_rotor_cycle)
    lcm_samples = min(lcm_samples, N // 2)

    ss_len = max(N - ss_start, min_ss)
    ss_len = max(ss_len // lcm_samples, 1) * lcm_samples
    ss_start = max(0, N - ss_len)
    return ss_start


def _compute_steady_state(arr, mp):
    """Calcula médias, RMS e fluxo de potência sobre a janela de regime."""
    t_arr  = arr["t"]
    wr_arr = arr["wr"]
    N      = len(t_arr)
    ss_start = _detect_steady_state(t_arr, wr_arr, mp)
    sl       = slice(ss_start, None)

    def _safe_mean(a):
        v = np.where(np.isfinite(a), a, 0.0)
        return float(np.mean(v))

    Te_med = _safe_mean(arr["Te"][sl])
    wr_med = _safe_mean(arr["wr"][sl])
    n_med  = _safe_mean(arr["n"][sl])

    ws     = mp.wb / (mp.p / 2.0)
    s      = (ws - wr_med) / ws if ws != 0 else 0.0
    P_gap  = Te_med * ws
    P_cu_r = s * P_gap
    P_mec  = (1.0 - s) * P_gap

    out = {}
    rms_keys = ("ias","ibs","ics","iar","ibr","icr",
                "ids","iqs","idr","iqr",
                "Va","Vb","Vc","Vds","Vqs")
    for k in rms_keys:
        vals = arr[k][sl]
        vals = np.where(np.isfinite(vals), vals, 0.0)
        out[f"{k}_rms"] = float(np.sqrt(np.mean(vals**2)))

    # FIX #3 — soma das três fases (correto sob desequilíbrio/falta)
    P_cu_s = mp.Rs * (out["ias_rms"]**2 + out["ibs_rms"]**2 + out["ics_rms"]**2)

    # FIX #5 — perdas no ferro: 3 · V_fase² / Rfe (modelo simplificado)
    V_phase_avg = (out["Va_rms"] + out["Vb_rms"] + out["Vc_rms"]) / 3.0
    P_fe = 3.0 * V_phase_avg**2 / mp.Rfe if mp.Rfe > 0 else 0.0

    if s >= 0:
        P_in  = P_gap + P_cu_s + P_fe
        P_out = P_mec
    else:
        P_in  = abs(P_mec)
        P_out = max(0.0, abs(P_gap) - P_cu_s - P_fe)   # FIX #4
    eta = (P_out / P_in * 100.0) if P_in > 0 else 0.0

    out.update({
        "P_gap": P_gap, "P_cu_r": P_cu_r, "P_mec": P_mec,
        "P_cu_s": P_cu_s, "P_fe": P_fe,
        "P_in": P_in, "P_out": P_out, "eta": eta,
        "s": s, "n_ss": n_med, "wr_ss": wr_med, "Te_ss": Te_med,
        "_ss_start": ss_start,
    })
    return out


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO E — DRIVER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def run_simulation(mp, tmax, h, voltage_fn, torque_fn, ref_code=1,
                   deseq_a=0.0, deseq_b=0.0, deseq_c=0.0,
                   falta_fase_a=False, falta_fase_b=False, falta_fase_c=False,
                   t_deseq=0.0, clamp_wr_at_zero=False, t_cutoff=None):
    """Integra o modelo Krause via solve_ivp e devolve as séries temporais.

    Convenção de saída:
      arr["wr"] — velocidade angular MECÂNICA do rotor (rad/s)
      arr["n"]  — rotação MECÂNICA do rotor (RPM)
      arr["Te"] — torque eletromagnético (N·m)
      Demais campos *_rms são calculados na janela de regime (inteiro de ciclos).

    A detecção de regime e o ciclo do rotor assumem ref_code=1 (referencial síncrono),
    em que as correntes do estator oscilam a f e as do rotor a |s|·f.
    """
    if mp.f * h > NYQUIST_LIMIT:
        warnings.warn(
            f"h·f = {mp.f*h:.3f} > {NYQUIST_LIMIT} (< {int(1/NYQUIST_LIMIT)} amostras/ciclo) "
            f"— RMS e detecção de regime podem ser imprecisos.",
            stacklevel=2,
        )

    t_values = np.arange(0.0, tmax, h)
    deseq    = (deseq_a, deseq_b, deseq_c, falta_fase_a, falta_fase_b, falta_fase_c)
    deseq_active = (deseq_a != 0.0 or deseq_b != 0.0 or deseq_c != 0.0
                    or falta_fase_a or falta_fase_b or falta_fase_c)

    rhs = _make_rhs(mp, voltage_fn, torque_fn, ref_code, deseq, t_deseq, deseq_active)
    y0  = [0.0]*6
    y_history = _solve(rhs, t_values, y0, mp, clamp_wr_at_zero, t_cutoff=t_cutoff)

    PSIqs, PSIds, PSIqr, PSIdr, wr_e, tetar = y_history
    tetae = mp.wb * t_values

    # ── tensões e correntes vetorizadas ─────────────────────────────────────
    Vl_arr = np.fromiter((voltage_fn(tv) for tv in t_values), dtype=float, count=len(t_values))
    Va, Vb, Vc = _voltages_vectorized(t_values, Vl_arr, mp, deseq, t_deseq, deseq_active)
    Vds, Vqs   = clarke_park_transform(Va, Vb, Vc, tetae)

    ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr = _reconstruct_currents(
        PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp)

    Te = (3.0/2.0)*(mp.p/2.0)*(1.0/mp.wb)*(PSIds*iqs - PSIqs*ids)

    wr_mec = wr_e / (mp.p / 2.0)
    n_rpm  = wr_e * 60.0 / (np.pi * mp.p)

    arr = {
        "t":   t_values,
        "wr":  wr_mec,        # MECÂNICA (rad/s) — convenção pública
        "n":   n_rpm,
        "Te":  Te,
        "ids": ids, "iqs": iqs, "idr": idr, "iqr": iqr,
        "ias": ias, "ibs": ibs, "ics": ics,
        "iar": iar, "ibr": ibr, "icr": icr,
        "Va":  Va,  "Vb":  Vb,  "Vc":  Vc,
        "Vds": Vds, "Vqs": Vqs,
    }
    arr.update(_compute_steady_state(arr, mp))
    return arr


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO F — FÁBRICA DE EXPERIMENTOS
# ═══════════════════════════════════════════════════════════════════════════

def build_fns(config: dict, mp: MachineParams):
    """Constrói as funções de tensão e torque para o experimento selecionado."""
    exp = config["exp_type"]
    t_ev = []
    if exp == "dol":
        Tl, tc = config["Tl_final"], config["t_carga"]
        vfn = lambda t: mp.Vl
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [tc]
    elif exp == "yd":
        Vy = mp.Vl/np.sqrt(3.0); Tl=config["Tl_final"]; t2=config["t_2"]; tc=config["t_carga"]
        vfn = lambda t: voltage_reduced_start(t, mp.Vl, Vy, t2)
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [t2, tc]
    elif exp == "comp":
        Vr=mp.Vl*config["voltage_ratio"]; Tl=config["Tl_final"]; t2=config["t_2"]; tc=config["t_carga"]
        vfn = lambda t: voltage_reduced_start(t, mp.Vl, Vr, t2)
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [t2, tc]
    elif exp == "soft":
        Vi=mp.Vl*config["voltage_ratio"]; t2=config["t_2"]; tp=config["t_pico"]
        Tl=config["Tl_final"]; tc=config["t_carga"]
        vfn = lambda t: voltage_soft_starter(t, mp.Vl, Vi, t2, tp)
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [t2, tc]
    elif exp == "carga":
        Ti=config.get("Tl_inicial", 0.0); Tl=config["Tl_final"]; tc=config["t_carga"]
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Ti=Ti, _Tl=Tl, _tc=tc: torque_step(t, _Ti, _Tl, _tc)
        t_ev = [tc]
    elif exp == "pulso_carga":
        Tb=config.get("Tl_base", 0.0); Tl=config["Tl_final"]
        ton=config["t_carga"]; toff=config["t_retirada"]
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Tb=Tb, _Tl=Tl, _ton=ton, _toff=toff: torque_pulse(t, _Tb, _Tl, _ton, _toff)
        t_ev = [ton, toff]
    elif exp == "gerador":
        Tn = -config["Tl_mec"]
        t2 = config["t_2"]
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Tn=Tn, _t2=t2: _Tn if t >= _t2 else 0.0
        t_ev = [t2]
    elif exp == "shutdown":
        Tl    = config["Tl_final"]
        tc    = config["t_carga"]
        t_cut = config["t_cutoff"]
        vfn = lambda t, _Vl=mp.Vl, _tc=t_cut: _Vl if t < _tc else 0.0
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = [tc, t_cut]
    else:
        vfn = lambda t: mp.Vl
        tfn = lambda t: 0.0
    return vfn, tfn, t_ev
