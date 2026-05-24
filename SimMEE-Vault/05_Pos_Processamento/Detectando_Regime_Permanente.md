---
titulo: "Detectando Regime Permanente"
capitulo: 05
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "237–279"
---

# Detectando Regime Permanente

> RMS e rendimento só fazem sentido em regime — esta nota explica como o IWS encontra quando o motor chegou lá.

---

## O Problema

Você quer calcular `ias_rms` e `eta` (rendimento). Mas a média ou RMS sobre toda a simulação inclui o transitório de partida — pico de inrush, torque oscilando, velocidade subindo. O resultado não representa o motor operando em carga.

Precisa de um índice `ss_start` tal que `arr["ias"][ss_start:]` seja regime permanente.

---

## A Tentativa Ingênua

```python
# "O motor está em regime quando wr > 95% da velocidade síncrona"
ws = mp.wb / (mp.p / 2)
ss_start = np.argmax(arr["wr"] > 0.95 * ws)
```

**Por que falha de duas formas:**

1. **Limiar fixo não generaliza:** modo gerador tem `wr > ws`; modo desligamento tem `wr` caindo até zero; `s=5%` é regime mas fica abaixo de 95%·ws.

2. **Janela não alinhada ao período:** mesmo com índice correto, se a janela `[ss_start:]` não for múltipla do período do sinal, o RMS fica enviesado. Sinal senoidal com 1.7 ciclos dá RMS diferente de 1.0 ciclo — o último meio-ciclo corta no pico ou no zero, afetando a média quadrática.

---

## A Solução

**Fase 1 — encontra o último ponto fora de tolerância:**

Calcula `wr_ref` como média dos últimos `MIN_SS_CYCLES` ciclos (assume que o final da simulação é regime). Varre de trás para frente e encontra o último índice onde `|wr - wr_ref| / wr_ref > SS_TOL` (0.5%). O regime começa no índice seguinte.

**Fase 2 — alinha ao LCM:**

Calcula `lcm(ciclo_elétrico, ciclo_rotor)` em amostras. Trunca `ss_start` para baixo de modo que `N - ss_start` seja múltiplo do LCM. Isso garante um número inteiro de períodos de cada componente frequencial no cálculo de RMS.

```
f_rotor = s * f_elétrica
LCM(T_elétrico, T_rotor) elimina batimento entre as duas frequências
```

---

## No Código

**`core/solver.py:237–279`** — função `_detect_steady_state`:

```python
SS_TOL        = 0.005   # 0.5% de desvio relativo de wr
MIN_SS_CYCLES = 5       # mínimo de ciclos elétricos consecutivos em regime
F_ROTOR_FLOOR = 0.01    # Hz — piso para evitar LCM astronômico quando s≈0

def _detect_steady_state(t_arr, wr_arr, mp):
    h = float(t_arr[1] - t_arr[0])
    samples_per_cycle = max(1, int(round(1.0 / (mp.f * h))))
    min_ss = MIN_SS_CYCLES * samples_per_cycle

    wr_ref = float(np.mean(wr_arr[-min_ss:]))   # referência = fim da simulação

    rel_dev   = np.abs((wr_arr[:-min_ss] - wr_ref) / wr_ref)
    violators = np.where(rel_dev > SS_TOL)[0]
    ss_start  = int(violators[-1]) + 1 if violators.size else 0

    # Fase 2: alinhamento ao LCM
    s_tmp   = (ws - wr_med_tmp) / ws
    f_rotor = max(abs(s_tmp) * mp.f, F_ROTOR_FLOOR)
    samples_per_rotor_cycle = max(1, int(round(1.0 / (f_rotor * h))))

    lcm_samples = math.lcm(samples_per_cycle, samples_per_rotor_cycle)
    lcm_samples = min(lcm_samples, N // 2)   # teto: metade da simulação

    ss_len   = max(N - ss_start, min_ss)
    ss_len   = max(ss_len // lcm_samples, 1) * lcm_samples
    ss_start = max(0, N - ss_len)
    return ss_start
```

`_ss_start` é salvo no `res` dict para que `compute_energy_metrics` e MCSA usem a mesma janela.

---

## Consequências e Trade-offs

**Ganhos:**
- Funciona para todos os modos: motor, gerador, desligamento, sag.
- Janela LCM elimina viés espectral sem necessidade de janelamento (Hanning etc.).

**Custo:**
- `F_ROTOR_FLOOR = 0.01 Hz` força LCM pequeno quando `s≈0` (operação a vazio). Sem ele, `f_rotor → 0` e `lcm_samples` fica na casa de milhões — impossível alocar.
- Se a simulação for muito curta (transitório não termina), `wr_ref` vem do meio do transitório e `ss_start` fica errado. Não há proteção explícita — cabe ao usuário escolher `tmax` adequado.

---

## Referências

- IWS: `core/solver.py:237–279` (`_detect_steady_state`)
- IWS: `core/solver.py:340–402` (`_compute_steady_state` — usa `ss_start`)
- [[Balanco_de_Potencia]] — usa a janela de regime para P_in, eta, RMS
- [[Como_solve_ivp_Funciona]] — `h` determina `samples_per_cycle`
