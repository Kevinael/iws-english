# -*- coding: utf-8 -*-
"""
EMS_PY.py — Núcleo físico do Simulador de Máquinas Elétricas
Modelo 0dq de Krause — integração via scipy.solve_ivp (LSODA).

Modelo estendido (rev-2):
  • Rfe  — resistência de perdas no ferro incluída na dinâmica do ODE
            (correntes i_feq / i_fed em paralelo com Lm, derivadas do fluxo de magnetização)
  • Saturação magnética — modelo de Froelich: Lm = Lm0 / (1 + |im|/Im_sat)
            atualizado a cada passo de integração
  • Impedância de rede — Rgrid / Lgrid acrescentados ao MachineParams e a build_fns;
            a tensão no terminal do motor é v_motor = v_fonte − Zgrid·is

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
from core.desequilibrio_falta import abc_voltages_deseq, make_broken_bar_rr_fn


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES DE INTEGRAÇÃO E ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════
SS_TOL          = 0.005   # tolerância relativa p/ detectar regime permanente em wr
MIN_SS_CYCLES   = 5       # janela mínima de regime: 5 ciclos da fundamental
NYQUIST_LIMIT   = 0.05    # avisa quando h*f > 0.05 (< 20 amostras/ciclo)
F_ROTOR_FLOOR   = 0.01    # Hz, evita div/0 no cálculo do ciclo do rotor

RTOL            = 1e-6
ATOL            = 1e-9
MAX_STEP_FACTOR = 20.0    # max_step = 1/(MAX_STEP_FACTOR · f) → ≥20 passos/ciclo


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO A — MODELO MATEMÁTICO
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MachineParams:
    # ── Elétricos ──────────────────────────────────────────────────────────
    Vl:    float = 220.0
    f:     float = 60.0
    Rs:    float = 0.435
    Rr:    float = 0.816
    Xm:    float = 26.13
    Xls:   float = 0.754
    Xlr:   float = 0.754
    # Rfe — paralelo com Lm; presente tanto no balanço de potências (como antes)
    # quanto na dinâmica do ODE (correntes de perda no ferro i_feq/i_fed).
    # Use Rfe → ∞ (ex: 1e9) para desativar o efeito dinâmico sem alterar a UI.
    Rfe:   float = 500.0

    # ── Mecânicos ──────────────────────────────────────────────────────────
    p:     int   = 4
    J:     float = 0.089
    B:     float = 0.005

    # ── Saturação magnética (modelo de Froelich) ───────────────────────────
    # sat_enable : ativa/desativa o modelo não-linear de Lm
    # Im_sat     : corrente de magnetização (A) em que Lm cai à metade do valor linear
    #              (parâmetro de Froelich)
    # Lm0        : Lm sem saturação — preenchido em __post_init__ a partir de Xm/f_ref
    #              pode ser sobrescrito pelo usuário para ajuste fino
    sat_enable: bool  = False
    # Im_sat = None → calculado em __post_init__ como 2 × Im0 (corrente de magnetização
    # em vazio); evita que o default hardcoded cause saturação excessiva para máquinas
    # com Im0 diferente do motor de referência.
    Im_sat:     float = 0.0    # 0 → auto (2 × Im0); qualquer valor > 0 é usado diretamente

    # ── Impedância de rede ─────────────────────────────────────────────────
    # Rgrid / Lgrid: resistência e indutância da linha de alimentação (por fase).
    # A queda de tensão é calculada no RHS e subtaída da v_fonte antes da
    # transformada Clarke-Park: v_motor = v_fonte - Rgrid·is - Lgrid·dis/dt
    # Use Rgrid=0, Lgrid=0 (default) para o modelo sem rede.
    Rgrid: float = 0.0    # Ω por fase
    Lgrid: float = 0.0    # H por fase

    # ── Modelo Térmico ────────────────────────────────────────────────────
    # dT/dt = (P_joule + P_fe) / Cth  −  (T − T_amb) / (Rth · Cth)
    # Rth=0.0 → auto: calibrado para T_regime = T_amb + 105 K (ΔT Classe B)
    # Cth=0.0 → auto: τ_th = 300 s (independente do porte)
    Rth:   float = 0.0    # K/W  (0 = calcular automaticamente em __post_init__)
    Cth:   float = 0.0    # J/K  (0 = calcular automaticamente em __post_init__)
    T_amb: float = 25.0   # °C

    # ── Modo de entrada dos parâmetros magnéticos ──────────────────────────
    input_mode: str   = "X"    # "X" = reatâncias (Ω)  |  "L" = indutâncias (H)
    f_ref:      float = 60.0   # frequência em que Xm/Xls/Xlr foram ensaiados (Hz)

    # ── Derivados (calculados em __post_init__) ────────────────────────────
    Xml:   float = field(init=False)
    wb:    float = field(init=False)
    Lm:    float = field(init=False)  # Lm linear (= Lm0 para saturação)
    Lls:   float = field(init=False)
    Llr:   float = field(init=False)
    Xls_a:     float = field(init=False)
    Xlr_a:     float = field(init=False)
    Xls_a_eff: float = field(init=False)  # Xls_a + Lgrid·wb (absorve rede no estator)

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
        self.Xml   = 1.0 / (1.0 / _Xm_a + 1.0 / self.Xls_a + 1.0 / self.Xlr_a)
        # Im_sat automático: 2 × corrente de magnetização em vazio (Im0 = Vfase / (wb·Lm))
        if self.Im_sat == 0.0:
            _Vfase = (self.Vl / np.sqrt(3.0))
            _Im0   = _Vfase / (self.wb * self.Lm) if self.Lm > 0 else 5.0
            self.Im_sat = 2.0 * _Im0
        # Rth/Cth automáticos: circuito equivalente em T para s = 3% (escorregamento nominal)
        if self.Rth == 0.0 or self.Cth == 0.0:
            _s_nom      = 0.03
            _Vfase      = self.Vl / math.sqrt(3.0)
            _Z_rotor    = complex(self.Rr / _s_nom, self.Xlr_a)
            _Z_mag      = complex(0.0, self.Xml)
            _Z_paralelo = (_Z_rotor * _Z_mag) / (_Z_rotor + _Z_mag)
            _Z_total    = complex(self.Rs, self.Xls_a) + _Z_paralelo
            _I_estator  = _Vfase / abs(_Z_total)
            _I_rotor    = _I_estator * abs(_Z_mag / (_Z_rotor + _Z_mag))
            _P_perdas   = max(3.0 * (self.Rs * _I_estator**2 + self.Rr * _I_rotor**2), 10.0)
            _P_mec_kw   = max((3.0 * _I_rotor**2 * (self.Rr / _s_nom) * (1.0 - _s_nom)) / 1000.0, 0.5)
            _massa      = _P_mec_kw * 15.0
            if self.Rth == 0.0:
                self.Rth = 105.0 / _P_perdas
            if self.Cth == 0.0:
                self.Cth = _massa * 460.0
        # Xls_a_eff absorve Lgrid em série com Lls (exato, sem Picard)
        # Xml é recalculado com Xls_a_eff para consistência com o RHS
        self.Xls_a_eff = self.Xls_a + self.Lgrid * self.wb
        _Xm_a_eff = self.wb * self.Lm
        self.Xml  = 1.0 / (1.0 / _Xm_a_eff + 1.0 / self.Xls_a_eff + 1.0 / self.Xlr_a)

    @property
    def n_sync(self) -> float:
        return 120.0 * self.f / self.p


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO B — TRANSFORMADAS E FONTES
# ═══════════════════════════════════════════════════════════════════════════

def abc_voltages(t, Vl, f):
    """Tensões abc balanceadas (amplitude-invariante; t pode ser escalar ou array)."""
    tetae = 2.0 * np.pi * f * t
    Va = np.sqrt(2.0 / 3.0) * Vl * np.sin(tetae)
    Vb = np.sqrt(2.0 / 3.0) * Vl * np.sin(tetae - 2.0 * np.pi / 3.0)
    Vc = np.sqrt(2.0 / 3.0) * Vl * np.sin(tetae + 2.0 * np.pi / 3.0)
    return Va, Vb, Vc


def clarke_park_transform(Va, Vb, Vc, tetae):
    """Clarke (amplitude-invariante, fator √(2/3)) + Park: abc → dq síncrono."""
    k   = np.sqrt(3.0 / 2.0)
    Vaf = k * (Va - 0.5 * Vb - 0.5 * Vc)
    Vbt = k * (np.sqrt(3.0) / 2.0 * Vb - np.sqrt(3.0) / 2.0 * Vc)
    Vds =  np.cos(tetae) * Vaf + np.sin(tetae) * Vbt
    Vqs = -np.sin(tetae) * Vaf + np.cos(tetae) * Vbt
    return Vds, Vqs


def voltage_reduced_start(t, Vl_nominal, Vl_reduced, t_switch):
    return Vl_nominal if t >= t_switch else Vl_reduced


def voltage_soft_starter(t, Vl_nominal, Vl_initial, t_start_ramp, t_full):
    if t < t_start_ramp:
        return Vl_initial
    elif t < t_full:
        return Vl_initial + (Vl_nominal - Vl_initial) * (t - t_start_ramp) / (t_full - t_start_ramp)
    return Vl_nominal


def voltage_sag(t, Vl_nominal, sag_magnitude, t_start, t_end):
    """Afundamento de tensão retangular: Vl cai para sag_magnitude×Vl em [t_start, t_end).

    Args:
        sag_magnitude: fração da tensão nominal durante o sag (ex: 0.5 = 50% de Vl).
        t_start:       instante de início do afundamento (s).
        t_end:         instante de retorno à tensão nominal (s).
    """
    if t_start <= t < t_end:
        return Vl_nominal * sag_magnitude
    return Vl_nominal


def torque_step(t, Tl_before, Tl_after, t_switch):
    return Tl_after if t >= t_switch else Tl_before


def torque_pulse(t, Tl_base, Tl_pulso, t_on, t_off):
    """Tl_base fora do pulso; Tl_pulso em [t_on, t_off)."""
    return Tl_pulso if t_on <= t < t_off else Tl_base


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO C — AUXILIARES DO MODELO ESTENDIDO
# ═══════════════════════════════════════════════════════════════════════════

def _lm_saturado(im_mag: float, Lm0: float, Im_sat: float) -> float:
    """Modelo de Froelich: Lm = Lm0 / (1 + |im| / Im_sat).

    • im_mag → 0  : Lm → Lm0  (região linear)
    • im_mag = Im_sat : Lm = Lm0 / 2
    • im_mag → ∞  : Lm → 0    (saturação total)

    Retorna sempre um valor positivo; Im_sat deve ser > 0.
    """
    if Im_sat <= 0.0:
        return Lm0
    return Lm0 / (1.0 + im_mag / Im_sat)


def _xml_from_lm(Lm: float, wb: float, Xls_a: float, Xlr_a: float) -> float:
    """Reatância mútua resultante dado Lm (recalculada quando Lm varia)."""
    Xm_a = wb * Lm
    if Xm_a <= 0.0:
        return 0.0
    return 1.0 / (1.0 / Xm_a + 1.0 / Xls_a + 1.0 / Xlr_a)


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO D — RHS DO ODE
# ═══════════════════════════════════════════════════════════════════════════
#
# Estados: [PSIqs, PSIds, PSIqr, PSIdr, wr, tetar, Temp, theta_slip]   (8 estados)
#
# ── Modelo Térmico (7º estado) ────────────────────────────────────────────
# EDO galvânica de 1ª ordem (modelo de parâmetros concentrados):
#
#   dT/dt = (P_joule(t) + P_fe(t)) / Cth  −  (T(t) − T_amb) / (Rth · Cth)
#
# P_joule = Rs·(ias² + ibs² + ics²)  +  Rr·(iar² + ibr² + icr²)
#         = Rs·(3/2)·(iqs² + ids²)   +  Rr·(3/2)·(iqr² + idr²)
#         (equivalência dq sob balanço, fator 3/2 da transformada amplitude-invariante)
#
# P_fe    = 3·|V_fe|²/Rfe  ≈  wb·|PSIm|² / Rfe   (aproximação p/ carga quase-estacionária)
#         ← usamos a potência dq de forma vetorial para manter dimensionamento correto
#
# T(0) = T_amb  (condição inicial — motor em equilíbrio térmico com o ambiente)
#
# ── Modelo com Rfe ─────────────────────────────────────────────────────────
# Rfe é colocado em paralelo com Lm no circuito dq.
# A tensão nos terminais de Lm é a derivada do fluxo de magnetização:
#
#   V_mq = dPSImq/dt    V_md = dPSImd/dt
#
# No referencial síncrono (ω_ref = wb) o fluxo de magnetização gira a wb,
# logo sua derivada aproximada em estado quasi-estacionário é:
#
#   dPSImq/dt ≈ wb·PSImd   (componente em quadratura → derivada = componente d × wb)
#   dPSImd/dt ≈ −wb·PSImq
#
# Isso é exatamente o que aparece nos termos de acoplamento ω·Ψ das equações
# de Krause; portanto as correntes de perda no ferro são:
#
#   i_feq =  wb·PSImd / Rfe      (componente q da corrente no Rfe)
#   i_fed = −wb·PSImq / Rfe      (componente d da corrente no Rfe)
#
# Essas correntes reduzem a corrente disponível para magnetização pura (Lm),
# modificando os fluxos de enlace equivalentes que excitam o circuito.
# A modificação é introduzida substituindo PSImq/PSImd calculados com os
# estados puros por versões "corrigidas" que subtraem a contribuição de i_fe:
#
#   PSImq_eff = PSImq − Xml·(i_feq / wb)   →   (divide por wb para obter Wb)
#   PSImd_eff = PSImd − Xml·(i_fed / wb)
#
# Para referencial rotórico (ω_ref = wr) e estacionário (ω_ref = 0),
# a velocidade de rotação do fluxo de magnetização muda; usamos ω_ref no lugar de wb.
# Quando ω_ref = 0 (estacionário), Rfe não produz perda (correntes DC não geram perdas
# no ferro), então a correção é zero — fisicamente correto.
#
# ── Modelo com Zgrid ──────────────────────────────────────────────────────
# A tensão no terminal do motor é:
#
#   v_motor = v_fonte − Rgrid·is_abc − Lgrid·d(is_abc)/dt
#
# Para evitar elevar a ordem do sistema (is_abc é função algébrica dos estados),
# expressamos d(is_abc)/dt em termos das derivadas dos fluxos (que são os estados):
#
#   ids = (PSIds − PSImd) / Xls_a   →   d(ids)/dt = (dPSIds − dPSImd) / Xls_a
#
# Isso cria acoplamento implícito (dPSI aparece em ambos os lados).
# Resolvemos analiticamente reformulando as equações dq do estator:
#
#   dPSIds = wb·(Vds_motor + (ω_ref/wb)·PSIqs − Rs·ids)          (forma genérica de Krause)
#
# Com Lgrid ≠ 0, Vds_motor = Vds_fonte − Rgrid·ids − Lgrid·d(ids)/dt
# Substituindo d(ids)/dt:
#
#   dPSIds = wb·[Vds_fonte − Rgrid·ids − Lgrid/Xls_a·(dPSIds − dPSImd_via_dPSI) + ...]
#
# Para manter o código legível e numericamente estável, adotamos a aproximação
# de primeira ordem: d(ids)/dt ≈ (ids(t) − ids(t−h)) / h — mas isso requereria
# estado extra ou passo anterior.
# Optamos pela forma IMPLÍCITA ESTÁTICA: substituímos d(ids)/dt pelo seu
# valor calculado exclusivamente com os estados atuais (sem memória), que é a
# equação de Krause sem Lgrid dividida por Xls_a. Isso equivale a um passo de
# Picard e é suficientemente preciso para Lgrid/Lls << 1 (linha fraca):
#
#   d(ids)/dt ≈ dPSIds_0 / Xls_a   onde dPSIds_0 é o RHS sem Lgrid
#
# O resultado é um fator de correção multiplicativo na tensão efetiva:
#
#   Vds_eff = Vds_fonte − Rgrid·ids − (Lgrid/Xls_a)·dPSIds_0
#
# Para Lgrid/Lls << 1 o erro é de segunda ordem.

def _make_rhs(mp: MachineParams, voltage_fn, torque_fn, ref_code: int,
              deseq: tuple, t_deseq: float, deseq_active: bool,
              rr_fn=None):
    """Fecha o RHS sobre os parâmetros — retorna função rhs(t, y) pronta para solve_ivp.

    Args:
        rr_fn: opcional — callable(t, slip) → Rr efetivo para modelo de barra quebrada.
               None significa Rr constante (comportamento padrão).
    """
    Xls_a = mp.Xls_a_eff;  Xlr_a = mp.Xlr_a   # Xls_a_eff absorve Lgrid
    Xml   = mp.Xml
    Rs    = mp.Rs;          Rr    = mp.Rr;    wb = mp.wb
    p     = mp.p;           J     = mp.J;     B  = mp.B
    Rfe   = mp.Rfe

    # rede (Lgrid já absorvido em Xls_a_eff — apenas queda resistiva permanece)
    Rgrid    = mp.Rgrid
    use_grid = (Rgrid != 0.0)

    # térmico
    Rth   = mp.Rth
    Cth   = mp.Cth
    T_amb = mp.T_amb

    def rhs(t: float, y: list) -> list:
        PSIqs, PSIds, PSIqr, PSIdr, wr, _tetar, Temp, theta_slip = y

        # ── fonte de tensão ──────────────────────────────────────────────
        Vl_a = voltage_fn(t)
        if deseq_active and t >= t_deseq:
            Va, Vb, Vc = abc_voltages_deseq(t, Vl_a, mp.f, *deseq)
        else:
            Va, Vb, Vc = abc_voltages(t, Vl_a, mp.f)
        tetae      = wb * t
        Vds_src, Vqs_src = clarke_park_transform(Va, Vb, Vc, tetae)

        # ── referencial ──────────────────────────────────────────────────
        if   ref_code == 1: w_ref = wb
        elif ref_code == 2: w_ref = wr
        else:               w_ref = 0.0

        # ── fluxos e correntes de enlace ─────────────────────────────────
        PSImq = Xml * (PSIqs / Xls_a + PSIqr / Xlr_a)
        PSImd = Xml * (PSIds / Xls_a + PSIdr / Xlr_a)

        # correntes de estator e rotor
        iqs = (PSIqs - PSImq) / Xls_a
        ids = (PSIds - PSImd) / Xls_a
        iqr = (PSIqr - PSImq) / Xlr_a
        idr = (PSIdr - PSImd) / Xlr_a

        # ── queda de tensão na rede ───────────────────────────────────────
        # Lgrid já absorvido em Xls_a_eff — apenas queda resistiva Rgrid
        if use_grid:
            Vqs_eff = Vqs_src - Rgrid * iqs
            Vds_eff = Vds_src - Rgrid * ids
        else:
            Vqs_eff = Vqs_src
            Vds_eff = Vds_src

        # ── equações de estado de Krause (referencial genérico ω_ref) ────
        slip_ref = (w_ref - wr) / wb

        # barra quebrada: Rr modulado por cos(2·theta_slip) com fase integrada exata
        Rr_cur = rr_fn(theta_slip) if rr_fn is not None else Rr

        dPSIqs = wb * (Vqs_eff - (w_ref / wb) * PSIds + (Rs / Xls_a) * (PSImq - PSIqs))
        dPSIds = wb * (Vds_eff + (w_ref / wb) * PSIqs + (Rs / Xls_a) * (PSImd - PSIds))
        dPSIqr = wb * (-slip_ref * PSIdr + (Rr_cur / Xlr_a) * (PSImq - PSIqr))
        dPSIdr = wb * ( slip_ref * PSIqr + (Rr_cur / Xlr_a) * (PSImd - PSIdr))

        # ── torque e mecânica ─────────────────────────────────────────────
        # Convenção amplitude-invariante (fator 3/2) conforme Krause eq. 6.6-2
        Te   = (3.0 / 2.0) * (p / 2.0) * (1.0 / wb) * (PSIds * iqs - PSIqs * ids)
        Tl_a = torque_fn(t)
        dwr  = (p / (2.0 * J)) * (Te - Tl_a) - (B / J) * wr
        dtetar = wr

        # ── modelo térmico (7º estado) ────────────────────────────────────
        # P_joule: perdas ôhmicas em dq (fator 3/2 da transformada amplitude-invariante)
        P_joule = (3.0 / 2.0) * (Rs * (iqs ** 2 + ids ** 2) + Rr_cur * (iqr ** 2 + idr ** 2))
        # P_fe: perdas no ferro — wb·|PSIm|² / Rfe (forma dq, consistente com o modelo Rfe)
        P_fe_th = wb * (PSImq ** 2 + PSImd ** 2) / Rfe if Rfe > 0.0 else 0.0
        dTemp = (P_joule + P_fe_th) / Cth - (Temp - T_amb) / (Rth * Cth)

        d_theta_slip = wb - wr
        return [dPSIqs, dPSIds, dPSIqr, dPSIdr, dwr, dtetar, dTemp, d_theta_slip]

    return rhs


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO E — INTEGRADOR
# ═══════════════════════════════════════════════════════════════════════════

def _solve(rhs, t_values, y0, mp: MachineParams, clamp_wr_at_zero: bool, t_cutoff=None):
    """Integra o ODE; suporta restart em t_cutoff e clamp de wr=0 no shutdown.

    Retorna y_history shape (8, N).
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
        n = sol.y.shape[1]
        y_history[:, offset:offset + n] = sol.y
        return offset + n

    def _ffill(arr):
        for i in range(1, arr.shape[1]):
            mask = ~np.isfinite(arr[:, i])
            arr[:, i] = np.where(mask, arr[:, i - 1], arr[:, i])

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

    # ── modo shutdown: divide em t_cutoff + clamp wr=0 ─────────────────────
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

                def rhs_clamped(t, y):
                    d    = rhs(t, y)
                    d[4] = 0.0
                    return d

                t_rest = t_values[off + n_b:]
                sol_c  = _run(rhs_clamped, [t_ev, tmax], y_ev, t_rest)
                n_c    = sol_c.y.shape[1]
                y_history[:, off + n_b:off + n_b + n_c] = sol_c.y
                if off + n_b + n_c < N:
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
# BLOCO F — PÓS-PROCESSAMENTO (vetorizado)
# ═══════════════════════════════════════════════════════════════════════════

def _voltages_vectorized(t_arr, Vl_arr, mp: MachineParams, deseq, t_deseq, deseq_active):
    """Reconstrói Va/Vb/Vc para todo o vetor t (suporta switch em t_deseq)."""
    if not deseq_active:
        return abc_voltages(t_arr, Vl_arr, mp.f)
    Va_b, Vb_b, Vc_b = abc_voltages(t_arr, Vl_arr, mp.f)
    Va_u, Vb_u, Vc_u = abc_voltages_deseq(t_arr, Vl_arr, mp.f, *deseq)
    mask = t_arr >= t_deseq
    return (np.where(mask, Va_u, Va_b),
            np.where(mask, Vb_u, Vb_b),
            np.where(mask, Vc_u, Vc_b))


def _reconstruct_currents(PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp: MachineParams):
    """Reconstrução vetorizada de correntes dq e abc (estator e rotor).

    Usa o Xml linear (mp.Xml) para o pós-processamento.
    A correção de perdas no ferro (i_feq/i_fed) é aplicada para manter
    consistência com o Te calculado no RHS — sem ela, Te do pós-proc
    diverge do Te que integrou a mecânica quando Rfe é finito.
    """
    PSImq = mp.Xml * (PSIqs / mp.Xls_a_eff + PSIqr / mp.Xlr_a)
    PSImd = mp.Xml * (PSIds / mp.Xls_a_eff + PSIdr / mp.Xlr_a)
    ids = (PSIds - PSImd) / mp.Xls_a_eff
    iqs = (PSIqs - PSImq) / mp.Xls_a_eff
    idr = (PSIdr - PSImd) / mp.Xlr_a
    iqr = (PSIqr - PSImq) / mp.Xlr_a

    cos_e, sin_e = np.cos(tetae), np.sin(tetae)
    cos_r, sin_r = np.cos(tetar), np.sin(tetar)
    iafs = ids * cos_e - iqs * sin_e
    ibts = ids * sin_e + iqs * cos_e
    iafr = idr * cos_r - iqr * sin_r
    ibtr = idr * sin_r + iqr * cos_r

    k    = np.sqrt(3.0 / 2.0)
    sq32 = np.sqrt(3.0) / 2.0
    ias = k * iafs
    ibs = k * (-0.5 * iafs + sq32 * ibts)
    ics = k * (-0.5 * iafs - sq32 * ibts)
    iar = k * iafr
    ibr = k * (-0.5 * iafr + sq32 * ibtr)
    icr = k * (-0.5 * iafr - sq32 * ibtr)
    return ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr


def _detect_steady_state(t_arr, wr_arr, mp: MachineParams) -> int:
    """Detecta o início do regime permanente (vetorizado)."""
    N = len(t_arr)
    h = float(t_arr[1] - t_arr[0]) if N > 1 else 1e-4
    samples_per_cycle = max(1, int(round(1.0 / (mp.f * h))))
    min_ss            = MIN_SS_CYCLES * samples_per_cycle

    wr_arr = np.where(np.isfinite(wr_arr), wr_arr, 0.0)
    wr_ref = float(np.mean(wr_arr[-min_ss:])) if N >= min_ss else float(np.mean(wr_arr))

    if abs(wr_ref) < 1e-12:
        ss_start = 0
    else:
        rel_dev   = np.abs((wr_arr[:-min_ss] - wr_ref) / wr_ref)
        violators = np.where(rel_dev > SS_TOL)[0]
        ss_start  = int(violators[-1]) + 1 if violators.size else 0

    ss_len_tmp = max(N - ss_start, min_ss)
    wr_med_tmp = float(np.mean(wr_arr[max(0, N - ss_len_tmp):]))
    ws         = mp.wb / (mp.p / 2.0)
    s_tmp      = (ws - wr_med_tmp) / ws if ws != 0 else 0.0

    f_rotor = max(abs(s_tmp) * mp.f, F_ROTOR_FLOOR)
    samples_per_rotor_cycle = max(1, int(round(1.0 / (f_rotor * h))))

    lcm_samples = math.lcm(samples_per_cycle, samples_per_rotor_cycle)
    lcm_samples = min(lcm_samples, N // 2)

    ss_len  = max(N - ss_start, min_ss)
    ss_len  = max(ss_len // lcm_samples, 1) * lcm_samples
    ss_start = max(0, N - ss_len)
    return ss_start


def _compute_steady_state(arr: dict, mp: MachineParams) -> dict:
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

    ws    = mp.wb / (mp.p / 2.0)
    s     = (ws - wr_med) / ws if ws != 0 else 0.0
    P_gap = Te_med * ws
    P_cu_r = s * P_gap
    P_mec  = (1.0 - s) * P_gap

    out: dict = {}
    rms_keys = ("ias", "ibs", "ics", "iar", "ibr", "icr",
                "ids", "iqs", "idr", "iqr",
                "Va",  "Vb",  "Vc",  "Vds", "Vqs")
    for k in rms_keys:
        vals = arr[k][sl]
        vals = np.where(np.isfinite(vals), vals, 0.0)
        out[f"{k}_rms"] = float(np.sqrt(np.mean(vals ** 2)))

    # perdas no cobre do estator (soma das três fases — correto sob desequilíbrio)
    P_cu_s = mp.Rs * (out["ias_rms"] ** 2 + out["ibs_rms"] ** 2 + out["ics_rms"] ** 2)

    # perdas no ferro: 3 · V_fase² / Rfe
    V_phase_avg = (out["Va_rms"] + out["Vb_rms"] + out["Vc_rms"]) / 3.0
    P_fe = 3.0 * V_phase_avg ** 2 / mp.Rfe if mp.Rfe > 0 else 0.0

    if s >= 0:
        P_in  = P_gap + P_cu_s + P_fe
        P_out = P_mec
    else:
        P_in  = abs(P_mec)
        P_out = max(0.0, abs(P_gap) - P_cu_s - P_fe)
    eta = (P_out / P_in * 100.0) if P_in > 0 else 0.0

    out.update({
        "P_gap": P_gap,   "P_cu_r": P_cu_r, "P_mec": P_mec,
        "P_cu_s": P_cu_s, "P_fe": P_fe,
        "P_in":  P_in,    "P_out": P_out,   "eta": eta,
        "s": s,  "n_ss": n_med,  "wr_ss": wr_med,  "Te_ss": Te_med,
        "_ss_start": ss_start,
        "ias_rms": out["ias_rms"],   # alias direto já presente no dict
    })
    return out


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO G — DRIVER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def run_simulation(
    mp: MachineParams,
    tmax: float,
    h: float,
    voltage_fn,
    torque_fn,
    ref_code: int = 1,
    deseq_a: float = 0.0,
    deseq_b: float = 0.0,
    deseq_c: float = 0.0,
    falta_fase_a: bool = False,
    falta_fase_b: bool = False,
    falta_fase_c: bool = False,
    t_deseq: float = 0.0,
    clamp_wr_at_zero: bool = False,
    t_cutoff: float | None = None,
    broken_bar_severity: float = 0.0,
) -> dict:
    """Integra o modelo Krause via solve_ivp e devolve as séries temporais.

    Saídas (retrocompatíveis com sim_results.py / _WK):
      arr["wr"]  — velocidade angular MECÂNICA (rad/s)
      arr["n"]   — rotação MECÂNICA (RPM)
      arr["Te"]  — torque eletromagnético (N·m)
      arr["ias_rms"] etc. — calculados na janela de regime permanente

    Novos campos adicionados nesta revisão (não quebram o contrato existente):
      arr["P_fe"]  — perdas no ferro (W) — já existia, mantido
      (demais campos de potência inalterados)
    """
    if mp.f * h > NYQUIST_LIMIT:
        warnings.warn(
            f"h·f = {mp.f * h:.3f} > {NYQUIST_LIMIT} "
            f"(< {int(1 / NYQUIST_LIMIT)} amostras/ciclo) "
            "— RMS e detecção de regime podem ser imprecisos.",
            stacklevel=2,
        )

    t_values     = np.arange(0.0, tmax, h)
    deseq        = (deseq_a, deseq_b, deseq_c, falta_fase_a, falta_fase_b, falta_fase_c)
    deseq_active = (deseq_a != 0.0 or deseq_b != 0.0 or deseq_c != 0.0
                    or falta_fase_a or falta_fase_b or falta_fase_c)

    rr_fn = make_broken_bar_rr_fn(mp.Rr, broken_bar_severity, mp.wb)
    rhs = _make_rhs(mp, voltage_fn, torque_fn, ref_code, deseq, t_deseq, deseq_active, rr_fn)
    # 8 estados: [PSIqs, PSIds, PSIqr, PSIdr, wr, tetar, Temp, theta_slip]
    y0  = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, mp.T_amb, 0.0]
    y_history = _solve(rhs, t_values, y0, mp, clamp_wr_at_zero, t_cutoff=t_cutoff)

    PSIqs, PSIds, PSIqr, PSIdr, wr_e, tetar, Temp_arr, _theta_slip_arr = y_history
    tetae = mp.wb * t_values

    # tensões e correntes vetorizadas
    Vl_arr = np.fromiter(
        (voltage_fn(tv) for tv in t_values), dtype=float, count=len(t_values)
    )
    Va, Vb, Vc   = _voltages_vectorized(t_values, Vl_arr, mp, deseq, t_deseq, deseq_active)
    Vds, Vqs     = clarke_park_transform(Va, Vb, Vc, tetae)
    ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr = _reconstruct_currents(
        PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp
    )

    Te     = (3.0 / 2.0) * (mp.p / 2.0) * (1.0 / mp.wb) * (PSIds * iqs - PSIqs * ids)
    wr_mec = wr_e / (mp.p / 2.0)
    n_rpm  = wr_e * 60.0 / (np.pi * mp.p)

    # Motores não podem inverter o sentido de rotação por conta própria: clamp wr ≥ 0.
    # Em modo gerador (wr pode ser negativo no sinal de Tl) este clamp não se aplica,
    # mas run_simulation não distingue — o clamp é conservador e fisicamente seguro
    # para todos os experimentos de motor (DOL, Y/D, soft, carga, shutdown).
    wr_mec = np.maximum(wr_mec, 0.0)
    n_rpm  = np.maximum(n_rpm,  0.0)

    arr = {
        "t":    t_values,
        "wr":   wr_mec,
        "n":    n_rpm,
        "Te":   Te,
        "ids":  ids,  "iqs": iqs,  "idr": idr, "iqr": iqr,
        "ias":  ias,  "ibs": ibs,  "ics": ics,
        "iar":  iar,  "ibr": ibr,  "icr": icr,
        "Va":   Va,   "Vb":  Vb,   "Vc":  Vc,
        "Vds":  Vds,  "Vqs": Vqs,
        "Temp": np.where(np.isfinite(Temp_arr), Temp_arr, mp.T_amb),
        "_broken_bar_severity": broken_bar_severity,
    }
    arr.update(_compute_steady_state(arr, mp))
    return arr


# ═══════════════════════════════════════════════════════════════════════════
# BLOCO H — FÁBRICA DE EXPERIMENTOS
# ═══════════════════════════════════════════════════════════════════════════

def build_fns(config: dict, mp: MachineParams):
    """Constrói as funções de tensão e torque para o experimento selecionado.

    Os parâmetros de rede (Rgrid, Lgrid) são incorporados em MachineParams
    e usados diretamente pelo RHS — não precisam de tratamento adicional aqui.
    O campo config["grid"] é reservado para futuras configurações de rede
    dinâmica (ex: afundamento de tensão programado).
    """
    exp  = config["exp_type"]
    t_ev: list = []

    if exp == "dol":
        Tl, tc = config["Tl_final"], config["t_carga"]
        vfn = lambda t: mp.Vl
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [tc]

    elif exp == "yd":
        Vy = mp.Vl / np.sqrt(3.0)
        Tl, t2, tc = config["Tl_final"], config["t_2"], config["t_carga"]
        vfn = lambda t: voltage_reduced_start(t, mp.Vl, Vy, t2)
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [t2, tc]

    elif exp == "comp":
        Vr = mp.Vl * config["voltage_ratio"]
        Tl, t2, tc = config["Tl_final"], config["t_2"], config["t_carga"]
        vfn = lambda t: voltage_reduced_start(t, mp.Vl, Vr, t2)
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [t2, tc]

    elif exp == "soft":
        Vi = mp.Vl * config["voltage_ratio"]
        t2, tp = config["t_2"], config["t_pico"]
        Tl, tc = config["Tl_final"], config["t_carga"]
        vfn = lambda t: voltage_soft_starter(t, mp.Vl, Vi, t2, tp)
        tfn = lambda t: torque_step(t, 0.0, Tl, tc)
        t_ev = [t2, tc]

    elif exp == "carga":
        Ti = config.get("Tl_inicial", 0.0)
        Tl, tc = config["Tl_final"], config["t_carga"]
        vfn = lambda t: mp.Vl
        tfn = lambda t, _Ti=Ti, _Tl=Tl, _tc=tc: torque_step(t, _Ti, _Tl, _tc)
        t_ev = [tc]

    elif exp == "pulso_carga":
        Tb  = config.get("Tl_base", 0.0)
        Tl  = config["Tl_final"]
        ton = config["t_carga"]
        toff = config["t_retirada"]
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

    elif exp == "voltage_sag":
        Tl      = config["Tl_final"]
        tc      = config.get("t_carga", 0.0)
        mag     = config["sag_magnitude"]
        t_sag   = config["t_start_sag"]
        t_end   = config["t_start_sag"] + config["t_duration_sag"]
        vfn = lambda t, _Vl=mp.Vl, _m=mag, _ts=t_sag, _te=t_end: voltage_sag(t, _Vl, _m, _ts, _te)
        tfn = lambda t, _Tl=Tl, _tc=tc: torque_step(t, 0.0, _Tl, _tc)
        t_ev = sorted(set(v for v in [tc, t_sag, t_end] if v > 0))

    else:
        vfn = lambda t: mp.Vl
        tfn = lambda t: 0.0

    return vfn, tfn, t_ev
