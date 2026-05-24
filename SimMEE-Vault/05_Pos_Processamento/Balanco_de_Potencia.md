---
titulo: "Balanço de Potência"
capitulo: 05
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "340–402"
---

# Balanço de Potência

> P_gap, P_cu_s, P_cu_r, P_fe e η: de onde vêm os números no `res` dict.

---

## O Problema

Você quer exibir rendimento, perdas Joule e potência mecânica no painel de resultados. O `res` dict tem chaves como `eta`, `P_gap`, `P_cu_s` — mas de onde saem esses valores? Se calcular errado (RMS fora do regime, P_in sem perdas no ferro), o η exibido é fisicamente inconsistente.

---

## A Tentativa Ingênua

```python
# "Rendimento é fácil: P_mec / P_in"
P_in  = 3 * Va_rms * ias_rms           # potência aparente?
P_mec = Te_med * wr_med
eta   = P_mec / P_in * 100
```

**Dois problemas:**

1. `Va_rms * ias_rms` é potência **aparente**, não ativa. P_in real precisa do fator de potência ou deve usar `P_in = (3/2)*(Vqs*iqs + Vds*ids)` (produto ponto no referencial dq).

2. `P_mec = Te·wr` ignora o escorregamento. A potência mecânica útil é `(1-s)·P_gap`, não `Te·wr_sinc`. Para `s=5%`, a diferença é 5% — relevante para rendimento.

---

## A Solução

O IWS usa a **cadeia de transferência de potência do motor de indução**:

```
P_in = P_gap + P_cu_s + P_fe
P_gap = Te_med × ωs              (potência no entreferro, em ωs síncrona)
P_cu_r = s × P_gap               (perdas Joule no rotor)
P_mec = (1-s) × P_gap            (potência mecânica no eixo)
P_out = P_mec                    (modo motor)
η = P_out / P_in × 100
```

Todas as grandezas vêm de **médias e RMS na janela de regime permanente** (`ss_start:`).

**Para o modo gerador** (`s < 0`), o fluxo inverte:
```
P_in  = |P_mec|    (entrada mecânica)
P_out = |P_gap| - P_cu_s - P_fe
```

---

## No Código

**`core/solver.py:340–402`** — função `_compute_steady_state`:

```python
def _compute_steady_state(arr, mp):
    ss_start = _detect_steady_state(arr["t"], arr["wr"], mp)
    sl       = slice(ss_start, None)

    # Médias simples (valores DC em regime)
    Te_med = _safe_mean(arr["Te"][sl])
    wr_med = _safe_mean(arr["wr"][sl])

    # Escorregamento a partir de ωr real vs ωs síncrona
    ws    = mp.wb / (mp.p / 2)
    s     = (ws - wr_med) / ws

    # Cadeia de potências
    P_gap  = Te_med * ws
    P_cu_r = s * P_gap
    P_mec  = (1.0 - s) * P_gap

    # RMS de correntes e tensões na janela de regime
    for k in ("ias", "ibs", "ics", ...):
        out[f"{k}_rms"] = float(np.sqrt(np.mean(arr[k][sl] ** 2)))

    # Perdas Joule no estator (3 fases, não 2/3 — RMS já é fase real)
    P_cu_s = mp.Rs * (out["ias_rms"]**2 + out["ibs_rms"]**2 + out["ics_rms"]**2)

    # Perdas no ferro via tensão de fase RMS (modelo Rfe em paralelo com Xm)
    V_phase_avg = (out["Va_rms"] + out["Vb_rms"] + out["Vc_rms"]) / 3.0
    P_fe = 3.0 * V_phase_avg**2 / mp.Rfe if mp.Rfe > 0 else 0.0

    # P_in: potência de entrada total (modo motor)
    P_in  = P_gap + P_cu_s + P_fe
    P_out = P_mec
    eta   = (P_out / P_in * 100.0) if P_in > 0 else 0.0
```

**Nota sobre `P_cu_s`:** usa correntes de fase abc (3 fases), **não** as dq. Com a convenção amplitude-invariante, `ias² + ibs² + ics²` = `(3/2)(ids² + iqs²)`. O código usa abc diretamente — mais intuitivo e sem o fator `3/2`.

---

## O que vai para o `res` dict

```python
# chaves de regime permanente (prefixo sem unidade — valor em SI)
"Te_ss"   — torque médio em regime (N.m)
"wr_ss"   — velocidade angular mecânica média (rad/s)
"n_ss"    — rotação em regime (RPM)
"s"       — escorregamento (adimensional)
"P_gap"   — potência no entreferro (W)
"P_cu_s"  — perdas Joule no estator (W)
"P_cu_r"  — perdas Joule no rotor (W)
"P_fe"    — perdas no ferro (W)
"P_mec"   — potência mecânica (W)
"P_in"    — potência elétrica de entrada (W)
"P_out"   — potência útil no eixo (W)
"eta"     — rendimento (%)
"ias_rms" — corrente de fase A RMS em regime (A)
"ias_pk"  — pico de corrente de fase A (A)
"Te_max"  — pico de torque (N.m)
"fator_pk"— relação ias_pk / ias_rms
"_ss_start"— índice do início do regime (para reuso em outras análises)
```

---

## Consequências e Trade-offs

**Ganhos:**
- Balanço fechado: `P_in = P_gap + P_cu_s + P_fe` é verificável por inspeção.
- Modo gerador tratado sem código separado — apenas troca de sinal de `s`.

**Custo:**
- `P_fe` via `Rfe` é modelo de perdas constante — não captura dependência com frequência e fluxo. Adequado para simulação educacional; insuficiente para otimização de máquina.
- Se `mp.Rfe = 0`, `P_fe = 0` silenciosamente — motor sem perdas no ferro. Não há aviso.

---

## Referências

- IWS: `core/solver.py:340–402` (`_compute_steady_state`)
- IWS: `core/solver.py:237–279` (`_detect_steady_state`)
- IWS: `core/energy_analysis.py:16–105` (`compute_energy_metrics` — usa `_ss_start` e `P_in`)
- [[Detectando_Regime_Permanente]] — como `ss_start` é calculado
- [[Correntes_a_Partir_de_Fluxos]] — de onde vêm `ids`, `iqs`, `ias`, `Vds`, `Vqs`
