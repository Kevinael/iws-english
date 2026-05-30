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

        # ── Passo 2 — Ensaio em Vazio (IEEE 112-2017 Sec. 5.6) ──────────────
        m     = 3                              # número de fases
        V1_nl = Vl_nl / math.sqrt(3.0)        # tensão de fase (wye equiv.) — Eq. (40)
        S_nl  = m * V1_nl * I_nl
        # Q0 — potência reativa no ensaio a vazio — Eq. (38)
        Q0 = math.sqrt(max(S_nl ** 2 - P_nl ** 2, 0.0))

        # Perdas mecânicas — heurística IEEE: 0,8% de P_nl quando não informadas
        Pfw_used = Pfw if Pfw > 0.0 else 0.008 * P_nl

        # Perdas no ferro Ph (total core loss, Sec. 5.6.6)
        P_joule_st_nl = m * Rs * I_nl ** 2
        Ph = P_nl - P_joule_st_nl - Pfw_used
        if Ph <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Ph (core loss) calculado ≤ 0 (Ph = {Ph:.2f} W). "
                    f"P_nl = {P_nl:.1f} W é insuficiente para cobrir 3·Rs·I_nl² = {P_joule_st_nl:.1f} W "
                    f"+ Pfw = {Pfw_used:.1f} W."
                ),
            }

        # ── Passo 3 — Rotor Bloqueado (IEEE 112-2017 Sec. 5.10.2–5.10.3) ───
        V1_lr = Vl_lr / math.sqrt(3.0)
        Zk    = V1_lr / I_lr
        Rk    = P_lr / (m * I_lr ** 2)

        if Rk >= Zk:
            return {
                "success": False,
                "error": (
                    f"Ensaio bloqueado: Rk = {Rk:.4f} Ω ≥ Zk = {Zk:.4f} Ω. "
                    "Verifique P_lr, V_lr e I_lr — o fator de potência está incoerente."
                ),
            }

        Xk_lr = math.sqrt(max(Zk ** 2 - Rk ** 2, 1e-6))
        # Correção linear de frequência para f_nl — Eq. (43) e (46)
        Xk = Xk_lr * (f_nl / f_lr)

        # ── Passo 4 — Separação Rs/Rr e distribuição Xls/Xlr (Eq. 44–46) ──
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

        Xls = frac * Xk        # X1 — Eq. (43) com frac = X1/(X1+X2)
        Xlr = (1.0 - frac) * Xk  # X2 — Eq. (45)

        # QL — potência reativa no ensaio bloqueado — Eq. (39)
        S_lr = m * V1_lr * I_lr
        QL   = math.sqrt(max(S_lr ** 2 - P_lr ** 2, 0.0))

        # ── Passo 5 — Iteração IEEE 112 Eq. 41–49 até convergência 0,1% ────
        # Eq. (41): Xm = m·V1²·Xm / (Q0 - m·I0²·X1·(X1+Xm)/Xm)
        # Rearranjada para iteração: dado X1 e razão r = X1/Xm:
        #   Xm_new = (Q0 - m·I0²·X1·(1+r)) / (m·V1²/Xm_est - m·I0²·r)
        # Usamos forma direta mais estável:
        # Xm iterado a partir de estimativa inicial X1+Xm ≈ Q0/(m·I0²)
        X1 = Xls
        XM_plus_X1_init = Q0 / max(m * I_nl ** 2, 1e-12)
        Xm = max(XM_plus_X1_init - X1, 1e-3)

        E1_nl_0 = math.sqrt(max(V1_nl ** 2 - (Rs * I_nl) ** 2, 1e-6))
        E1_nl   = E1_nl_0

        for _iter in range(50):
            Xm_prev = Xm
            X1_prev = X1

            # Eq. (41) — Xm a partir de Q0, I0, V1, X1
            denom_41 = Q0 - m * I_nl ** 2 * X1 * (X1 + Xm) / max(Xm, 1e-9)
            Xm_new = m * V1_nl ** 2 / max(denom_41, 1e-9)
            Xm_new = max(Xm_new, 1e-3)

            # Eq. (42) — X1L a partir de QL, IL, V1L, X1, Xm
            ratio_1_M = X1 / max(Xm_new, 1e-9)
            numer_42  = QL - m * I_lr ** 2 * X1 * (1.0 + ratio_1_M)
            denom_42  = m * I_lr ** 2 * (1.0 + ratio_1_M) ** 2 - m * V1_lr ** 2 / max(Xm_new, 1e-9)
            # forma estável: X1L = (QL - m·IL²·Xm·ratio²) / (m·IL²·(1+ratio) - m·V1L²/((Xm)·(1+1/ratio)))
            # Alternativa robusta: resolver diretamente Eq (42) para X1L
            # X1L ≈ (QL/(m·IL²) - X1*(X1/Xm)) / (1 + X1/Xm)
            X1L = (QL / max(m * I_lr ** 2, 1e-12) - X1 * ratio_1_M) / max(1.0 + ratio_1_M, 1e-9)
            X1L = max(X1L, 1e-4)

            # Eq. (43) — escala para frequência nominal
            X1_new = X1L * (f_nl / f_lr)
            X1_new = max(X1_new, 1e-4)

            # Eq. (41) — recalcula Xm com X1 atualizado
            denom_41b = Q0 - m * I_nl ** 2 * X1_new * (X1_new + Xm_new) / max(Xm_new, 1e-9)
            Xm_new2 = m * V1_nl ** 2 / max(denom_41b, 1e-9)
            Xm = max(Xm_new2, 1e-3)
            X1 = X1_new

            # Critério de convergência 0,1% — Sec. 5.10.3.2 step 5
            if (abs(Xm - Xm_prev) / max(abs(Xm_prev), 1e-9) < 0.001 and
                    abs(X1 - X1_prev) / max(abs(X1_prev), 1e-9) < 0.001):
                break

        # Xls e Xlr finais após convergência
        Xls = X1
        Xlr = Xk * (f_nl / f_lr) - Xls  # X2 = Xk_total - X1, Eq. (45)/(46)
        Xlr = max(Xlr, 1e-4)

        # Eq. (47) — Gfe = Ph·Xm² / (m·V1²) → Rfe = 1/Gfe
        Gfe = Ph * Xm ** 2 / max(m * V1_nl ** 2 * Xm ** 2, 1e-12)
        # forma simplificada correta: Gfe = Ph / (m · E1²)
        # E1 iterada pelas componentes de corrente:
        # Usar E1 ≈ V1 (aproximação de circuito aberto do ramo shunt)
        E1_nl = math.sqrt(max(V1_nl ** 2 - (Rs * I_nl) ** 2, 1e-6))
        Gfe   = Ph / max(m * E1_nl ** 2, 1e-12)
        Rfe   = 1.0 / max(Gfe, 1e-12)

        # Eq. (48) — Bm = 1/Xm
        Bm  = 1.0 / max(Xm, 1e-9)
        Ife = Gfe * E1_nl
        Imu = Bm  * E1_nl
        I_mu_check = math.sqrt(Ife ** 2 + Imu ** 2)

        # Eq. (49) — R2 (Rr) com correção de Gfe e Bm
        # R2 = P_lr/(m·IL²) - Rs - (Xk²·Gfe)/(1+...) — forma aproximada robusta
        # Usamos: Rr = Rk - Rs (já calculado; consistente com Eq. 49 para Xm >> Xk)
        # Para máquinas com Xm pequeno, aplicar Eq. 49 completa:
        ratio_fe = Gfe * Xk
        Rr_full = (P_lr / max(m * I_lr ** 2, 1e-12) - Rs
                   - Xk ** 2 * Gfe / max(1.0 + (Xk * Gfe) ** 2, 1e-9))
        Rr = max(Rr_full, Rk - Rs)  # fallback para Rk-Rs se Eq.49 der negativo
        if Rr <= 0.0:
            return {
                "success": False,
                "error": (
                    f"Rr ≤ 0 após Eq. 49 (Rr = {Rr:.4f} Ω). "
                    f"Rs = {Rs:.4f} Ω, Rk = {Rk:.4f} Ω. Verifique medições."
                ),
            }

        Pfe_3ph = Ph  # alias para compatibilidade com retorno existente

        return {
            "success": True,
            "Rs":            round(Rs,      5),
            "Rr":            round(Rr,      5),
            "Xm":            round(Xm,      4),
            "Xls":           round(Xls,     5),
            "Xlr":           round(Xlr,     5),
            "Rfe":           round(Rfe,     2),
            # rastreabilidade dos ensaios — IEEE 112 Eq. 38–49
            "E1_nl":         round(E1_nl,   3),
            "E1_nl_0":       round(E1_nl_0, 3),
            "E1_nl_1":       round(E1_nl,   3),  # convergido — mesmo que E1_nl
            "Xk":            round(Xk,      4),
            "Xk_lr":         round(Xk_lr,   4),
            "Rk":            round(Rk,      5),
            "Zk":            round(Zk,      4),
            "Pfe_3ph":       round(Pfe_3ph, 2),
            "P_joule_st_nl": round(P_joule_st_nl, 2),
            "I_mu":          round(Imu,     4),
            "I_fe":          round(Ife,     4),
            "Pfw_used":      round(Pfw_used, 2),
            "S_nl":          round(S_nl,    2),
            "Q_nl":          round(Q0,      2),
            "Vf_nl":         round(V1_nl,   3),
            "Vf_lr":         round(V1_lr,   3),
            "split_used":    split_key,
            "Xls_frac":      round(frac,    3),
            "f_nl":          f_nl,
            "f_lr":          f_lr,
        }

    except ZeroDivisionError as exc:
        return {"success": False, "error": f"Divisão por zero durante a estimação IEEE: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Erro inesperado no estimador IEEE: {exc}"}
