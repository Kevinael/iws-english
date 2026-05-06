# -*- coding: utf-8 -*-
"""
machine_model.py — Parametros e RHS do modelo 0dq de Krause

Exporta:
  MachineParams  — dataclass com todos os parametros da maquina (eletricos,
                   mecanicos, termicos, de rede) e campos derivados
  _lm_saturado   — modelo de Froelich para Lm nao-linear (legado, sem efeito no RHS)
  _xml_from_lm   — reatancia mutua resultante dado Lm
  _make_rhs      — monta e retorna a funcao rhs(t, y) para solve_ivp

Estados do ODE (8):
  [PSIqs, PSIds, PSIqr, PSIdr, wr, tetar, Temp, theta_slip]

Dependencias internas:
  core.thermal    — estimate_rth_cth, dTemp_dt
  core.transforms — abc_voltages, clarke_park_transform
  core.desequilibrio_falta — abc_voltages_deseq

Documentacao detalhada de cada decisao de implementacao:
  SME/2. Modulos/core/machine_model.md
  SME/2. Modulos/Guia de Leitura do Codigo.md  (secoes 1-2)
  SME/1. Fundamentos/4 - Modelo Matematico (RHS Krause).md
"""

from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass, field

from core.thermal import estimate_rth_cth, dTemp_dt
from core.transforms import abc_voltages, clarke_park_transform
from core.desequilibrio_falta import abc_voltages_deseq


# ═══════════════════════════════════════════════════════════════════════════
# PARAMETROS DA MAQUINA
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MachineParams:
    # ── Eletricos ──────────────────────────────────────────────────────────
    Vl:    float = 220.0
    f:     float = 60.0
    Rs:    float = 0.435
    Rr:    float = 0.816
    Xm:    float = 26.13
    Xls:   float = 0.754
    Xlr:   float = 0.754
    # Rfe em paralelo com Lm — use Rfe=1e9 para desativar sem alterar a UI
    Rfe:   float = 500.0

    # ── Mecanicos ──────────────────────────────────────────────────────────
    p:     int   = 4
    J:     float = 0.089
    B:     float = 0.005

    # ── Saturacao magnetica (legado — sem efeito no RHS apos rev-3) ────────
    # Campos mantidos para compatibilidade com sessoes gravadas e testes.
    sat_enable: bool  = False
    Im_sat:     float = 0.0    # 0 -> auto (2 x Im0)

    # ── Impedancia de rede ─────────────────────────────────────────────────
    Rgrid: float = 0.0    # Ohm por fase
    Lgrid: float = 0.0    # H por fase

    # ── Modelo Termico ─────────────────────────────────────────────────────
    # Rth=0 -> auto: calibrado para T_regime = T_amb + 50 K (operacao nominal TEFC)
    # Cth=0 -> auto: estimado por massa do motor (P_mec_kW x 15 kg/kW x 460 J/kg.K)
    Rth:   float = 0.0    # K/W
    Cth:   float = 0.0    # J/K
    T_amb: float = 25.0   # graus C

    # ── Modo de entrada dos parametros magneticos ──────────────────────────
    input_mode: str   = "X"    # "X" = reatancias (Ohm) | "L" = indutancias (H)
    f_ref:      float = 60.0   # frequencia em que Xm/Xls/Xlr foram ensaiados (Hz)

    # ── Derivados (calculados em __post_init__) ────────────────────────────
    Xml:       float = field(init=False)
    wb:        float = field(init=False)
    Lm:        float = field(init=False)
    Lls:       float = field(init=False)
    Llr:       float = field(init=False)
    Xls_a:     float = field(init=False)
    Xlr_a:     float = field(init=False)
    Xls_a_eff: float = field(init=False)  # Xls_a + Lgrid*wb (absorve rede no estator)

    def __post_init__(self) -> None:
        self.wb = 2.0 * np.pi * self.f

        # conversao usa f_ref (frequencia do ensaio), nao f (frequencia de operacao)
        # permite inserir dados de catalogo a 50 Hz em simulacao a 60 Hz
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
        # Xml provisorio — necessario para Im_sat; sera recalculado apos Lgrid
        self.Xml   = 1.0 / (1.0 / _Xm_a + 1.0 / self.Xls_a + 1.0 / self.Xlr_a)

        # Im_sat automatico: 2 x corrente de magnetizacao em vazio
        if self.Im_sat == 0.0:
            _Vfase     = self.Vl / np.sqrt(3.0)
            _Im0       = _Vfase / (self.wb * self.Lm) if self.Lm > 0 else 5.0
            self.Im_sat = 2.0 * _Im0

        # Rth/Cth automaticos via circuito T no escorregamento nominal.
        # Usa wb*Lm como ramo de magnetizacao (nao Xml — circuito T, nao pi).
        # Deve ocorrer ANTES de Xls_a_eff ser modificado por Lgrid.
        if self.Rth == 0.0 or self.Cth == 0.0:
            _Xm_a_th = self.wb * self.Lm
            _Rth_est, _Cth_est = estimate_rth_cth(
                Vl=self.Vl, Rs=self.Rs, Rr=self.Rr,
                Xls_a=self.Xls_a, Xlr_a=self.Xlr_a, Xm_a=_Xm_a_th,
            )
            if self.Rth == 0.0:
                self.Rth = _Rth_est
            if self.Cth == 0.0:
                self.Cth = _Cth_est

        # Lgrid absorvido em Xls_a_eff (impedancia serie vista pelo estator)
        # Xml recalculado para consistencia com o novo Xls_a_eff
        self.Xls_a_eff = self.Xls_a + self.Lgrid * self.wb
        _Xm_a_eff      = self.wb * self.Lm
        self.Xml       = 1.0 / (1.0 / _Xm_a_eff + 1.0 / self.Xls_a_eff + 1.0 / self.Xlr_a)

    @property
    def n_sync(self) -> float:
        return 120.0 * self.f / self.p


# ═══════════════════════════════════════════════════════════════════════════
# AUXILIARES DO MODELO
# ═══════════════════════════════════════════════════════════════════════════

def _lm_saturado(im_mag: float, Lm0: float, Im_sat: float) -> float:
    """Modelo de Froelich: Lm = Lm0 / (1 + |im| / Im_sat).

    Legado — saturacao removida do RHS em rev-3; funcao mantida para
    compatibilidade com codigo externo que a referencie.
    """
    if Im_sat <= 0.0:
        return Lm0
    return Lm0 / (1.0 + im_mag / Im_sat)


def _xml_from_lm(Lm: float, wb: float, Xls_a: float, Xlr_a: float) -> float:
    """Reatancia mutua resultante dado Lm."""
    Xm_a = wb * Lm
    if Xm_a <= 0.0:
        return 0.0
    return 1.0 / (1.0 / Xm_a + 1.0 / Xls_a + 1.0 / Xlr_a)


# ═══════════════════════════════════════════════════════════════════════════
# RHS DO ODE
# ═══════════════════════════════════════════════════════════════════════════
#
# Estados: [PSIqs, PSIds, PSIqr, PSIdr, wr, tetar, Temp, theta_slip]
#
# Modelo termico (7o estado):
#   dT/dt = (P_joule + P_fe) / Cth  -  (T - T_amb) / (Rth * Cth)
#   P_joule = (3/2) * (Rs*(iqs^2+ids^2) + Rr*(iqr^2+idr^2))
#   P_fe    = wb * (PSImq^2 + PSImd^2) / Rfe
#
# Impedancia de rede:
#   Lgrid absorvido em Xls_a_eff; apenas queda resistiva Rgrid permanece no RHS.
#
# Referencial generico (ref_code):
#   0 = estacionario (w_ref=0), 1 = sincrono (w_ref=wb), 2 = rotórico (w_ref=wr)

def _make_rhs(mp: MachineParams, voltage_fn, torque_fn, ref_code: int,
              deseq: tuple, t_deseq: float, deseq_active: bool,
              rr_fn=None):
    """Fecha o RHS sobre os parametros — retorna rhs(t, y) pronta para solve_ivp.

    Padrao closure: parametros capturados como escalares locais para minimizar
    lookup de atributo no hot path (chamado ~50-200k vezes por segundo de simulacao).
    use_grid avaliado uma unica vez aqui, nao dentro de rhs.
    Ver SME/2. Modulos/core/machine_model.md — secao _make_rhs.

    Args:
        rr_fn: callable(theta_slip) -> Rr efetivo (modelo barra quebrada).
               None = Rr constante — evita overhead de chamada no caso comum.
    """
    # extrai escalares — lookup de celula de closure e mais rapido que atributo de objeto
    Xls_a = mp.Xls_a_eff;  Xlr_a = mp.Xlr_a
    Xml   = mp.Xml
    Rs    = mp.Rs;          Rr    = mp.Rr;    wb = mp.wb
    p     = mp.p;           J     = mp.J;     B  = mp.B
    Rfe   = mp.Rfe
    Rgrid    = mp.Rgrid
    use_grid = (Rgrid != 0.0)   # avaliado uma vez; branch em rhs e previsivel
    Rth   = mp.Rth;  Cth = mp.Cth;  T_amb = mp.T_amb

    def rhs(t: float, y: list) -> list:
        # _tetar (posicao do rotor) e estado mas nao entra nas equacoes de Krause
        # no referencial sincrono — apenas integrado para pos-processamento
        PSIqs, PSIds, PSIqr, PSIdr, wr, _tetar, Temp, theta_slip = y

        # fonte de tensao: deseq ativado condicionalmente por t_deseq
        Vl_a = voltage_fn(t)
        if deseq_active and t >= t_deseq:
            Va, Vb, Vc = abc_voltages_deseq(t, Vl_a, mp.f, *deseq)
        else:
            Va, Vb, Vc = abc_voltages(t, Vl_a, mp.f)
        tetae            = wb * t   # angulo do referencial sincrono (exato, sem integracao)
        Vds_src, Vqs_src = clarke_park_transform(Va, Vb, Vc, tetae)

        # velocidade angular do referencial (ref_code: 0=estacionario, 1=sincrono, 2=rotórico)
        if   ref_code == 1: w_ref = wb
        elif ref_code == 2: w_ref = wr
        else:               w_ref = 0.0

        # fluxo mutuo e correntes de dispersao (relacoes algebricas — nao EDOs)
        PSImq = Xml * (PSIqs / Xls_a + PSIqr / Xlr_a)
        PSImd = Xml * (PSIds / Xls_a + PSIdr / Xlr_a)
        iqs = (PSIqs - PSImq) / Xls_a
        ids = (PSIds - PSImd) / Xls_a
        iqr = (PSIqr - PSImq) / Xlr_a
        idr = (PSIdr - PSImd) / Xlr_a

        # queda resistiva da rede (Lgrid ja absorvido em Xls_a_eff — apenas Rgrid aqui)
        if use_grid:
            Vqs_eff = Vqs_src - Rgrid * iqs
            Vds_eff = Vds_src - Rgrid * ids
        else:
            Vqs_eff = Vqs_src
            Vds_eff = Vds_src

        slip_ref = (w_ref - wr) / wb
        # rr_fn=None no caso comum: evita chamada de funcao em cada passo
        Rr_cur   = rr_fn(theta_slip) if rr_fn is not None else Rr

        # equacoes de fluxo de Krause (2013), Eq. 6.5-17, forma normalizada por wb
        dPSIqs = wb * (Vqs_eff - (w_ref / wb) * PSIds + (Rs / Xls_a) * (PSImq - PSIqs))
        dPSIds = wb * (Vds_eff + (w_ref / wb) * PSIqs + (Rs / Xls_a) * (PSImd - PSIds))
        dPSIqr = wb * (-slip_ref * PSIdr + (Rr_cur / Xlr_a) * (PSImq - PSIqr))
        dPSIdr = wb * ( slip_ref * PSIqr + (Rr_cur / Xlr_a) * (PSImd - PSIdr))

        # fator 3/2 decorre da convencao amplitude-invariante (nao potencia-invariante)
        Te     = (3.0 / 2.0) * (p / 2.0) * (1.0 / wb) * (PSIds * iqs - PSIqs * ids)
        Tl_a   = torque_fn(t)
        dwr    = (p / (2.0 * J)) * (Te - Tl_a) - (B / J) * wr
        dtetar = wr

        # EDO termica de 1a ordem — ver SME/2. Modulos/core/thermal.md
        P_joule = (3.0 / 2.0) * (Rs * (iqs**2 + ids**2) + Rr_cur * (iqr**2 + idr**2))
        P_fe_th = wb * (PSImq**2 + PSImd**2) / Rfe if Rfe > 0.0 else 0.0
        dTemp   = dTemp_dt(Temp, P_joule, P_fe_th, Rth, Cth, T_amb)

        # theta_slip integrado como estado para o modelo de barra quebrada (rr_fn)
        d_theta_slip = wb - wr
        return [dPSIqs, dPSIds, dPSIqr, dPSIdr, dwr, dtetar, dTemp, d_theta_slip]

    return rhs
