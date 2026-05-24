---
titulo: "Vetor de Estado Detalhado"
capitulo: 04
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "91, 111–114"
---

# Vetor de Estado Detalhado

> O vetor `y` com 8 componentes é o "DNA" da simulação — tudo o que o integrador conhece sobre a máquina em qualquer instante. Entender cada índice é entender por que a simulação converge (ou explode).

## O Problema

`solve_ivp` entrega um array `sol.y` com shape `(8, N)`. Sem conhecer o significado de cada linha, é impossível extrair correntes, velocidade ou temperatura — e impossível depurar quando um valor diverge.

A pergunta: **o que é `y[0]`, `y[4]`, `y[7]`? Por que fluxos e não correntes? Por que esse ordenamento?**

## A Tentativa Ingênua

Usar correntes `[ids, iqs, idr, iqr]` como variáveis de estado — que é o que aparece nas equações elétricas do motor na maioria dos livros-texto.

Problema: as equações de corrente envolvem derivadas de fluxo que por sua vez dependem das correntes — o sistema fica implícito. Para resolve com `solve_ivp` (método explícito), seria necessário inverter a matriz de indutâncias a cada passo de tempo. Computacionalmente mais caro e numericamente mais sensível quando `Xm` domina.

## A Solução

O modelo de Krause usa **fluxos concatenados** como variáveis de estado. As equações de estado ficam explícitas: `dΨ/dt = V - R·i`, onde as correntes `i` são calculadas algebricamente a partir dos fluxos (inversão analítica da matriz de indutâncias, feita uma vez, não a cada passo).

Isso torna o lado direito `rhs(t, y)` explícito e barato de avaliar — ideal para LSODA.

## No Código

O vetor de estado `y[0..7]` é definido implicitamente pela função `rhs` em `machine_model.py` e pela condição inicial `y0` montada em `solver.py`:

| Índice | Símbolo | Grandeza | Unidade | Referencial |
|--------|---------|----------|---------|-------------|
| `y[0]` | `ΨDs` | Fluxo concatenado d-estator | Wb | Eixo d (referencial estacionário) |
| `y[1]` | `ΨQs` | Fluxo concatenado q-estator | Wb | Eixo q (referencial estacionário) |
| `y[2]` | `ΨDr` | Fluxo concatenado d-rotor | Wb | Eixo d (referencial estacionário) |
| `y[3]` | `ΨQr` | Fluxo concatenado q-rotor | Wb | Eixo q (referencial estacionário) |
| `y[4]` | `ωr` | Velocidade elétrica do rotor | rad/s | — |
| `y[5]` | `θe` | Ângulo elétrico do estator | rad | Cumulativo |
| `y[6]` | `θr` | Ângulo elétrico do rotor | rad | Cumulativo |
| `y[7]` | `T` | Temperatura do enrolamento | K | Absoluta |

**Por que fluxos d e q separados para estator e rotor?**

A transformação de Park projeta as três fases (a, b, c) em dois eixos ortogonais (d, q) no referencial estacionário. Estator e rotor giram em referenciais diferentes — o rotor gira à velocidade `ωr` enquanto o estator está fixo. Por isso, fluxos do estator e do rotor são estados independentes: 4 fluxos no total.

**Por que `θe` e `θr` como estados separados?**

`θe = ωs·t` (ângulo da tensão de alimentação) e `θr = ∫ωr·dt` (ângulo mecânico acumulado do rotor). O escorregamento `s = (ωs - ωr)/ωs` é calculado a partir da diferença entre os dois. Armazenar ambos como estados evita recalcular integrais — o integrador faz esse trabalho automaticamente ao integrar `dθe/dt = ωs` e `dθr/dt = ωr`.

**Por que `T` como estado?**

A temperatura do enrolamento evolui como `dT/dt = (P_joule - (T-T_amb)/Rth) / Cth` — uma equação diferencial ordinária acoplada ao resto do sistema (pois `P_joule` depende das correntes, que dependem dos fluxos). Colocar `T` no vetor de estado deixa o integrador tratar o acoplamento térmico-elétrico automaticamente.

**Condição inicial `y0`:**

```python
# solver.py, linha 91 (implícita via MachineParams)
y0 = [0.0,  # ΨDs: fluxo d-estator em repouso
      0.0,  # ΨQs: fluxo q-estator em repouso
      0.0,  # ΨDr: fluxo d-rotor em repouso
      0.0,  # ΨQr: fluxo q-rotor em repouso
      0.0,  # ωr: motor parado
      0.0,  # θe: ângulo inicial da tensão
      0.0,  # θr: ângulo inicial do rotor
      T_amb]  # T: temperatura ambiente (K)
```

Todos os fluxos partem de zero (motor em repouso, sem campo magnético residual). A temperatura parte da temperatura ambiente `T_amb` definida em `MachineParams`.

## Consequências e Trade-offs

**Extração de correntes** — `sol.y` não contém correntes diretamente. Para plotar `ids(t)`, é necessário aplicar a inversão analítica: `ids = (ΨDs·Xr - ΨDr·Xm) / (Xs·Xr - Xm²)`. Essa conversão ocorre em `core/transforms.py` ou diretamente em `plotly_charts.py`.

**Ângulos crescem sem limite** — `θe` e `θr` são integrais cumulativas. Para uma simulação de 10s a 60 Hz, `θe ≈ 3770 rad`. Isso não é problema para LSODA (que trabalha com derivadas), mas ao exibir ao usuário converte-se para `mod(θe, 2π)`.

**`y[7]` (temperatura) acopla escalas** — fluxos estão na ordem de `1e-1` Wb, temperatura na ordem de `300` K. O `atol=1e-9` é adequado para os fluxos mas conservador para a temperatura. Esse mismatch de escala é inofensivo — LSODA controla o erro relativo por variável.

**Ordem importa** — o índice de cada componente em `y` é um contrato implícito entre `solver.py`, `machine_model.py`, `transforms.py` e `plotly_charts.py`. Mudar a ordem de `y[4]` (ωr) quebraria o `clamp_wr_at_zero`, que acessa `y[4]` diretamente.

## Próxima Nota

[[Clamp_e_Estabilidade]] — `y[4] = ωr` pode ir negativo durante o desligamento. O que acontece quando cruza zero, e por que isso instabiliza o integrador?
