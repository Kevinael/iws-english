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


# ─── Distribuição Xls/Xlr por classe (IEEE Std 112-2017, Tabela 1) ────────────
_IEEE_SPLIT_TABLE: dict[str, float] = {
    "A":      0.50,
    "B":      0.40,
    "C":      0.30,
    "D":      0.50,
    "WR":     0.50,
    "custom": 0.40,
}


def estimate_params_ieee_tests(
    V_dc: float,
    I_dc: float,
    is_delta: bool,
    Vl_nl: float,
    I_nl: float,
    P_nl: float,
    f_nl: float,
    Vl_lr: float,
    I_lr: float,
    P_lr: float,
    f_lr: float,
    Pfw: float = 0.0,
    split: str = "B",
    Xls_frac: float = 0.4,
) -> dict:
    """Estima parâmetros do circuito equivalente a partir dos ensaios IEEE Std 112-2017.

    Implementa os três ensaios clássicos do circuito equivalente em T:
      1. Ensaio CC (DC Test) — Rs
      2. Ensaio em Vazio (No-Load) — Xm, Rfe
      3. Ensaio de Rotor Bloqueado (Locked Rotor) — Rr, Xls, Xlr

    Args:
        V_dc:     Tensão CC aplicada entre dois terminais (V).
        I_dc:     Corrente CC medida (A).
        is_delta: True = ligação Triângulo (Δ); False = Estrela (Y).
        Vl_nl:    Tensão de linha em vazio (V) — tipicamente nominal.
        I_nl:     Corrente de linha em vazio (A).
        P_nl:     Potência trifásica total em vazio (W).
        f_nl:     Frequência do ensaio em vazio (Hz).
        Vl_lr:    Tensão de linha no ensaio bloqueado (V) — reduzida.
        I_lr:     Corrente de linha no ensaio bloqueado (A).
        P_lr:     Potência trifásica total no ensaio bloqueado (W).
        f_lr:     Frequência do ensaio bloqueado (Hz) — IEEE recomenda ≈ 25% de f_nl.
        Pfw:      Perdas mecânicas medidas (W); 0 = estimar como 0,8% de P_nl.
        split:    Classe NEMA: "A", "B", "C", "D", "WR" ou "custom".
        Xls_frac: Fração Xls/Xk — usado apenas quando split="custom".

    Returns:
        dict com mesma estrutura de estimate_params() — chaves principais:
            success, Rs, Rr, Xm, Xls, Xlr, Rfe,
            E1_nl, Xk, Rk, Pfe_3ph, I_mu, Pfw_used,
            split_used, Xls_frac, f_nl, f_lr.
        Em caso de erro: {'success': False, 'error': <mensagem>}.
    """
    try:
        # ── Validações de entrada ──────────────────────────────────────────
        if V_dc <= 0.0 or I_dc <= 0.0:
            return {"success": False, "error": "Ensaio CC: V_dc e I_dc devem ser positivos."}
        if Vl_nl <= 0.0 or I_nl <= 0.0 or P_nl <= 0.0:
            return {"success": False, "error": "Ensaio em vazio: Vl_nl, I_nl e P_nl devem ser positivos."}
        if Vl_lr <= 0.0 or I_lr <= 0.0 or P_lr <= 0.0:
            return {"success": False, "error": "Ensaio bloqueado: Vl_lr, I_lr e P_lr devem ser positivos."}
        if f_nl <= 0.0 or f_lr <= 0.0:
            return {"success": False, "error": "Frequências dos ensaios devem ser positivas."}
        if Pfw < 0.0:
            return {"success": False, "error": "Perdas mecânicas (Pfw) não podem ser negativas."}

        split_key = split if split in _IEEE_SPLIT_TABLE else "B"
        frac = Xls_frac if split_key == "custom" else _IEEE_SPLIT_TABLE[split_key]
        if not (0.05 <= frac <= 0.95):
            return {
                "success": False,
                "error": f"Fração Xls/Xk = {frac:.3f} fora do intervalo [0,05; 0,95].",
            }

        # ── Passo 1 — Resistência do estator (Ensaio CC, IEEE 112 Cl. 6.4) ─
        # Y: dois enrolamentos em série     → Rs_fase = (V_dc / I_dc) / 2
        # Δ: dois em paralelo c/ um em série → Rs_fase = (V_dc / I_dc) · 1,5
        if is_delta:
            Rs = (V_dc / I_dc) * 1.5
        else:
            Rs = (V_dc / I_dc) / 2.0

        if Rs <= 0.0:
            return {"success": False, "error": "Rs calculado não é positivo. Verifique V_dc e I_dc."}

        # ── Passo 2 — Ensaio em Vazio (IEEE 112 Cl. 6.5) ────────────────────
        Vf_nl = Vl_nl / math.sqrt(3.0)
        S_nl  = 3.0 * Vf_nl * I_nl
        # Q_nl (não usado diretamente, mas mantido para rastreabilidade)
        Q_nl  = math.sqrt(max(S_nl ** 2 - P_nl ** 2, 0.0))

        # Perdas mecânicas — heurística: 0,8% de P_nl quando não informadas
        Pfw_used = Pfw if Pfw > 0.0 else 0.008 * P_nl

        # Perdas no ferro (descontando Joule no estator e perdas mecânicas)
        P_joule_st_nl = 3.0 * Rs * I_nl ** 2
        Pfe_3ph = P_nl - P_joule_st_nl - Pfw_used
        if Pfe_3ph <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Pfe calculado ≤ 0 (Pfe_3ph = {Pfe_3ph:.2f} W). "
                    f"P_nl = {P_nl:.1f} W é insuficiente para cobrir 3·Rs·I_nl² = {P_joule_st_nl:.1f} W "
                    f"+ Pfw = {Pfw_used:.1f} W."
                ),
            }

        # Primeira passagem: E1_nl com Xls ≈ 0
        E1_nl_0 = math.sqrt(max(Vf_nl ** 2 - (Rs * I_nl) ** 2, 1e-6))

        # ── Passo 3 — Rotor Bloqueado (IEEE 112 Cl. 6.6) ────────────────────
        Vf_lr = Vl_lr / math.sqrt(3.0)
        Zk    = Vf_lr / I_lr
        Rk    = P_lr / (3.0 * I_lr ** 2)

        if Rk >= Zk:
            return {
                "success": False,
                "error": (
                    f"Ensaio bloqueado: Rk = {Rk:.4f} Ω ≥ Zk = {Zk:.4f} Ω. "
                    "Verifique P_lr, V_lr e I_lr — o fator de potência está incoerente."
                ),
            }

        Xk_lr = math.sqrt(max(Zk ** 2 - Rk ** 2, 1e-6))
        # Correção linear de frequência: Xk @ f_nl = Xk_lr · (f_nl / f_lr)
        Xk = Xk_lr * (f_nl / f_lr)

        # ── Passo 4 — Separação Rs/Rr e distribuição Xls/Xlr ────────────────
        Rr = Rk - Rs
        if Rr <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Rr = Rk − Rs = {Rr:.4f} Ω ≤ 0. "
                    f"Rs (ensaio CC) = {Rs:.4f} Ω é maior que Rk (ensaio bloqueado) = {Rk:.4f} Ω. "
                    "Verifique as medições."
                ),
            }

        Xls = frac * Xk
        Xlr = (1.0 - frac) * Xk

        # ── Passo 5 — Duas iterações fasoriais de E₁_nl ─────────────────────
        # Modelo fasorial: Vf_nl = E1 + (Rs + j·Xls)·I_nl
        # I_nl decompõe-se em I_fe (em fase com E1) e I_mu (atrasada de 90°).
        # Sem conhecer I_fe e I_mu a priori, refinamos E1 em duas iterações.

        # Iteração 1: aproximação inicial — assume I_nl em fase com Vf_nl
        E1_re_1 = Vf_nl - Rs * I_nl
        E1_im_1 = -Xls * I_nl
        E1_nl_1 = max(math.sqrt(E1_re_1 ** 2 + E1_im_1 ** 2), 0.5 * Vf_nl)

        # Estima componentes da corrente em vazio com E1 da iteração 1
        Rfe_1     = (3.0 * E1_nl_1 ** 2) / Pfe_3ph
        I_fe_1    = E1_nl_1 / Rfe_1
        I_mu_sq_1 = I_nl ** 2 - I_fe_1 ** 2
        if I_mu_sq_1 <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Componente de magnetização não positiva na 1ª iteração "
                    f"(I_nl² − I_fe² = {I_mu_sq_1:.4f}). Verifique P_nl e I_nl."
                ),
            }
        I_mu_1 = math.sqrt(I_mu_sq_1)

        # Iteração 2: usa decomposição fasorial correta de I_nl
        # I_nl = I_fe − j·I_mu  (referencial em E1)
        # Vf_nl = E1 + (Rs + j·Xls)·(I_fe − j·I_mu)
        # Componente em fase:        Vf_nl = E1 + Rs·I_fe + Xls·I_mu
        # Componente em quadratura:  0     =      Xls·I_fe − Rs·I_mu
        E1_re_2 = Vf_nl - Rs * I_fe_1 - Xls * I_mu_1
        E1_im_2 = -(Xls * I_fe_1 - Rs * I_mu_1)
        E1_nl   = max(math.sqrt(E1_re_2 ** 2 + E1_im_2 ** 2), 0.5 * Vf_nl)

        # Recalcula Rfe, I_mu e Xm com E1 final
        Rfe = (3.0 * E1_nl ** 2) / Pfe_3ph
        I_fe = E1_nl / Rfe
        I_mu_sq = I_nl ** 2 - I_fe ** 2
        if I_mu_sq <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Componente de magnetização não positiva (I_nl² − I_fe² = {I_mu_sq:.4f}). "
                    "Verifique P_nl e I_nl — possível erro de medição em vazio."
                ),
            }
        I_mu = math.sqrt(I_mu_sq)
        Xm = max(E1_nl / I_mu - Xls, 1e-3)

        return {
            "success": True,
            "Rs":          round(Rs,    5),
            "Rr":          round(Rr,    5),
            "Xm":          round(Xm,    4),
            "Xls":         round(Xls,   5),
            "Xlr":         round(Xlr,   5),
            "Rfe":         round(Rfe,   2),
            # rastreabilidade dos ensaios
            "E1_nl":       round(E1_nl, 3),
            "E1_nl_0":     round(E1_nl_0, 3),
            "E1_nl_1":     round(E1_nl_1, 3),
            "Xk":          round(Xk,    4),
            "Xk_lr":       round(Xk_lr, 4),
            "Rk":          round(Rk,    5),
            "Zk":          round(Zk,    4),
            "Pfe_3ph":     round(Pfe_3ph, 2),
            "P_joule_st_nl": round(P_joule_st_nl, 2),
            "I_mu":        round(I_mu,  4),
            "I_fe":        round(I_fe,  4),
            "Pfw_used":    round(Pfw_used, 2),
            "S_nl":        round(S_nl,  2),
            "Q_nl":        round(Q_nl,  2),
            "Vf_nl":       round(Vf_nl, 3),
            "Vf_lr":       round(Vf_lr, 3),
            "split_used":  split_key,
            "Xls_frac":    round(frac,  3),
            "f_nl":        f_nl,
            "f_lr":        f_lr,
        }

    except ZeroDivisionError as exc:
        return {"success": False, "error": f"Divisão por zero durante a estimação IEEE: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Erro inesperado no estimador IEEE: {exc}"}
