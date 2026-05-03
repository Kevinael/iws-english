# -*- coding: utf-8 -*-
"""
param_estimator.py — Estimação de circuito equivalente a partir de dados de placa.

Método: aproximação clássica IEEE (circuito equivalente em T de regime permanente).
Referências: IEEE Std 112, NEMA MG-1, IEC 60034.

Premissas adotadas (todas documentadas no retorno do dict):
  1. Distribuição NEMA B: Xls = 0,4·Xk  e  Xlr = 0,6·Xk
  2. Fator de potência na partida: cos(φp) = 0,20  (valor médio NEMA B)
  3. Tensão no entreferro: E1 = Vf − In_fase·|Zs|  (queda estatórica subtraída)
  4. Número de polos deduzido de N_nom e f — independe do widget externo
  5. Ligação Y ou Δ afeta Vf e a corrente de fase do circuito equivalente
  6. Rfe não estimado — usar valor padrão na UI (500 Ω)
  7. Inércia térmica: 15 kg/kW × cp_aço (460 J/kg·K) — NEMA/IEC TEFC
"""

from __future__ import annotations
import math


def estimate_params(
    Vl: float,
    f: float,
    p: int,          # recebido mas não usado internamente — p é deduzido de N_nom
    Pn_kW: float,
    N_nom: float,
    rend: float,
    fp: float,
    Ip_In: float,
    Tp_Tn: float,
    is_delta: bool = False,
) -> dict:
    """Estima parâmetros do circuito equivalente a partir dos dados de placa.

    Args:
        Vl:       Tensão de linha nominal (V).
        f:        Frequência nominal (Hz).
        p:        Número de polos — ignorado internamente, deduzido de N_nom.
        Pn_kW:    Potência nominal no eixo (kW).
        N_nom:    Velocidade nominal (RPM).
        rend:     Rendimento nominal (fração, ex: 0.91 para 91%).
        fp:       Fator de potência nominal (fração).
        Ip_In:    Relação corrente de partida / corrente nominal (de linha).
        Tp_Tn:    Relação torque de partida / torque nominal.
        is_delta: True = ligação Triângulo (Δ); False = Estrela (Y, padrão).

    Returns:
        dict com chaves: success, Rs, Rr, Xm, Xls, Xlr, Cth, Massa, p_est, n_s, s_n,
        In_lin, In_fase, Tn, Ip_fase, Tp, Zk, Xk, E1.
        Em caso de erro: {'success': False, 'error': <mensagem>}.
    """
    try:
        # ── Validações de entrada ──────────────────────────────────────────
        if not (0.0 < rend < 1.0):
            return {"success": False, "error": f"Rendimento {rend:.3f} inválido — deve estar em (0, 1)."}
        if not (0.0 < fp < 1.0):
            return {"success": False, "error": f"Fator de potência {fp:.3f} inválido — deve estar em (0, 1)."}
        if Ip_In <= 0.0:
            return {"success": False, "error": "Relação Ip/In deve ser positiva."}
        if Tp_Tn <= 0.0:
            return {"success": False, "error": "Relação Tp/Tn deve ser positiva."}
        if Pn_kW <= 0.0:
            return {"success": False, "error": "Potência nominal deve ser positiva."}
        if N_nom <= 0.0:
            return {"success": False, "error": "Velocidade nominal deve ser positiva."}
        if f <= 0.0:
            return {"success": False, "error": "Frequência deve ser positiva."}

        # ── 1. Grandezas gerais ────────────────────────────────────────────
        # Tensão de fase (premissa 5)
        Vf = Vl if is_delta else Vl / math.sqrt(3.0)

        # Número de polos deduzido da placa (premissa 4)
        # n_s ≥ N_nom: p_pares = round(f / (N_nom/60)) → p = 2·p_pares
        p_pares = max(1, round(f / (N_nom / 60.0)))
        p_est   = 2 * p_pares
        n_s     = 120.0 * f / p_est          # velocidade síncrona (RPM)
        ws      = 4.0 * math.pi * f / p_est  # velocidade angular mecânica síncr. (rad/s)
        s_n     = 1.0 - N_nom / n_s          # escorregamento nominal

        if not (0.0 < s_n < 1.0):
            return {
                "success": False,
                "error": (
                    f"Escorregamento calculado s_n = {s_n:.4f} inválido "
                    f"(p_est = {p_est}, n_s = {n_s:.1f} RPM). "
                    "Verifique a velocidade nominal."
                ),
            }

        # ── 2. Grandezas nominais ──────────────────────────────────────────
        Pn_W    = Pn_kW * 1000.0
        P_in    = Pn_W / rend                          # potência elétrica absorvida (W)
        In_lin  = P_in / (3.0 * Vf * fp)              # corrente de linha (A)

        # Corrente de fase do circuito equivalente monofásico em T:
        # Em Δ: i_fase = i_linha / sqrt(3); em Y: i_fase = i_linha
        In_fase = In_lin / math.sqrt(3.0) if is_delta else In_lin

        Tn      = Pn_W / (ws * (1.0 - s_n))           # torque nominal (N·m)

        if In_fase <= 0.0:
            return {"success": False, "error": "Corrente de fase calculada inválida. Verifique rendimento e fator de potência."}

        # ── 3. Partida (s = 1) ─────────────────────────────────────────────
        Ip_lin  = In_lin * Ip_In                       # corrente de linha na partida
        Ip_fase = Ip_lin / math.sqrt(3.0) if is_delta else Ip_lin
        Zk      = Vf / Ip_fase                         # impedância de curto-circuito (Ω)
        Tp      = Tn * Tp_Tn                           # torque de partida (N·m)

        # ── 4. Resistência do rotor ────────────────────────────────────────
        # Te = (3/ws)·Rr·Ip_fase²  →  Rr = Tp·ws / (3·Ip_fase²)
        Rr = (Tp * ws) / (3.0 * Ip_fase ** 2)

        # ── 5. Reatâncias (distribuição NEMA B, premissa 1 e 2) ───────────
        cos_phi_p = 0.20                                # premissa NEMA B
        Rk  = Zk * cos_phi_p
        Xk  = math.sqrt(max(Zk ** 2 - Rk ** 2, 1e-6))
        Xls = 0.4 * Xk
        Xlr = 0.6 * Xk

        # ── 6. Resistência do estator ──────────────────────────────────────
        Rs = max(Rk - Rr, 1e-3)

        # ── 7. Reatância de magnetização com correção de E₁ (premissa 3) ──
        # A tensão aplicada sobre Xm não é Vf mas sim E₁ = Vf − In_fase·|Zs|.
        # Ignorar essa queda superestima Xm pelo fator (Vf/E₁).
        Z_s = math.sqrt(Rs ** 2 + Xls ** 2)
        E1  = max(Vf - In_fase * Z_s, 0.5 * Vf)       # clamp: E1 ≥ 50% Vf
        I_mu = In_fase * math.sqrt(max(1.0 - fp ** 2, 1e-6))
        Xm   = max(E1 / I_mu - Xls, 1e-3)

        # ── 8. Resistência de perdas no ferro — heurística de distribuição ──
        # Sem ensaio a vazio não é possível isolar Pfe das demais perdas.
        # Heurística estatística NEMA/IEC: perdas no núcleo ≈ 20% das perdas
        # totais em regime nominal (faixa típica: 15–25% para motores TEFC).
        # Pfe é então referida à tensão no entreferro E1 (não a Vf) para
        # manter consistência com o modelo de circuito equivalente em T.
        P_perdas_totais = max(P_in - Pn_W, 1.0)        # W — perdas totais
        P_fe_total  = P_perdas_totais * 0.20            # W — 20% para o ferro
        P_fe_fase   = P_fe_total / 3.0                  # W por fase
        Rfe = (E1 ** 2) / P_fe_fase                     # Ω — por fase

        # ── 9. Inércia térmica — heurística NEMA/IEC TEFC ─────────────────
        # Regra industrial: 15 kg por kW instalado (carcaça + enrolamentos + rotor).
        # Cp do aço ≈ 460 J/(kg·K) — valor dominante da massa ativa.
        Massa = Pn_kW * 15.0                            # kg
        Cth   = Massa * 460.0                           # J/K

        return {
            "success": True,
            "Rs":      round(Rs,      5),
            "Rr":      round(Rr,      5),
            "Xm":      round(Xm,      4),
            "Xls":     round(Xls,     5),
            "Xlr":     round(Xlr,     5),
            "Rfe":     round(Rfe,     2),
            "Cth":     round(Cth,     1),
            "Massa":   round(Massa,   1),
            "P_fe_total": round(P_fe_total, 1),
            # grandezas intermediárias para o card de transparência
            "p_est":   p_est,
            "n_s":     round(n_s,     1),
            "s_n":     round(s_n,     5),
            "In_lin":  round(In_lin,  3),
            "In_fase": round(In_fase, 3),
            "Tn":      round(Tn,      2),
            "Ip_fase": round(Ip_fase, 3),
            "Tp":      round(Tp,      2),
            "Zk":      round(Zk,      4),
            "Xk":      round(Xk,      4),
            "E1":      round(E1,      3),
        }

    except ZeroDivisionError as exc:
        return {"success": False, "error": f"Divisão por zero durante a estimação: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Erro inesperado: {exc}"}
