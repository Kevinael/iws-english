---
titulo: "Como `solve_ivp` Funciona"
capitulo: 04
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "51–76"
---

# Como `solve_ivp` Funciona

> Chamar `solve_ivp` com parâmetros errados produz soluções silenciosamente imprecisas — o integrador não avisa, simplesmente avança com passos grandes demais.

## O Problema

A função `solve_ivp` do SciPy é o coração da simulação, mas exige configuração cuidadosa. Três parâmetros controlam toda a precisão numérica: `rtol`, `atol` e `max_step`. Errar qualquer um deles e a simulação "funciona" — mas os transitórios de partida ficam errados, as oscilações de torque somem, e os fluxos convergem para valores fantasma.

A pergunta central: **quais valores usar, e por quê esses e não outros?**

## A Tentativa Ingênua

Usar os defaults do SciPy: `rtol=1e-3`, `atol=1e-6`, sem `max_step`.

Resultado: o integrador LSODA escolhe passos de tempo livremente, podendo pular meio ciclo elétrico inteiro em uma única etapa. Para uma máquina a 60 Hz, isso significa que os transitórios de corrente (que oscilam a 60 Hz e seus harmônicos) ficam sub-amostrados — a curva de torque parece suave demais, sem as oscilações reais do transitório de partida.

## A Solução

O IWS usa três constantes definidas no topo de `solver.py`:

```python
RTOL            = 1e-6    # tolerância relativa
ATOL            = 1e-9    # tolerância absoluta (Wb, rad/s)
MAX_STEP_FACTOR = 20.0    # max_step = 1/(20·f)
```

**`RTOL = 1e-6`** — exige que o erro relativo seja menor que 0,0001%. Necessário porque os fluxos e correntes da máquina variam em ordens de magnitude durante a partida (de zero até regime).

**`ATOL = 1e-9`** — define o piso de erro absoluto em Webers e rad/s. Sem isso, quando `wr ≈ 0` no instante de partida, o erro relativo explode (divisão por número pequeno). O atol ancora a tolerância perto de zero.

**`max_step = 1/(20·f)`** — garante pelo menos 20 amostras por ciclo elétrico. A constante `NYQUIST_LIMIT = 0.05` documenta essa regra: `h·f ≤ 0.05`. Para 60 Hz, `max_step ≈ 833 µs`.

## No Código

A função interna `_run` encapsula a chamada ao integrador:

```python
# solver.py, linhas 65–70
def _run(rhs_fn, t_span, y_init, t_eval):
    sol = solve_ivp(rhs_fn, t_span, y_init, t_eval=t_eval,
                    method='LSODA', rtol=RTOL, atol=ATOL, max_step=max_step)
    if not sol.success:
        warnings.warn(f"solve_ivp falhou: {sol.message}")
    return sol
```

**Por que LSODA?** — O método LSODA (Livermore Solver for Ordinary Differential Equations with Automatic Stiffness Detection) detecta automaticamente se o sistema é *stiff* (rígido) ou não, e troca de algoritmo internamente. A máquina de indução é stiff durante a partida (constantes de tempo elétrica ~ms versus mecânica ~100ms) e não-stiff em regime — LSODA lida com ambos sem configuração extra.

**`t_eval`** — vetor de instantes onde o resultado é interpolado. O integrador usa passos adaptativos internamente, mas entrega valores exatamente nos pontos de `t_eval`. Isso garante que `y_history` tenha sempre `N` colunas, independente dos passos internos do LSODA.

**`sol.success`** — se `False`, o integrador não convergiu (tolerâncias muito apertadas, equação divergente, ou `max_step` muito pequeno). O `warnings.warn` sinaliza sem travar a UI.

A função `_fill` escreve o resultado no buffer pré-alocado:

```python
# solver.py, linhas 72–76
def _fill(y_history, offset, sol):
    n = sol.y.shape[1]
    y_history[:, offset:offset + n] = sol.y
    return offset + n
```

`sol.y` tem shape `(8, n_points)` — 8 estados, `n_points` instantes de tempo. `_fill` escreve na fatia correta de `y_history` sem criar arrays temporários.

## Consequências e Trade-offs

**Precisão vs. velocidade** — `RTOL=1e-6` e `ATOL=1e-9` são conservadores. A simulação é mais lenta que com os defaults do SciPy, mas os transitórios ficam corretos. Para simulações de 5 segundos a 60 Hz, o custo é aceitável (< 2s na maioria das máquinas).

**`max_step` é obrigatório** — sem ele, LSODA pode usar passos de 50ms em regime permanente (onde a dinâmica é lenta), mas isso produz gráficos com resolução temporal insuficiente para o usuário ver as oscilações de torque.

**`sol.y` vs `sol.t`** — o código usa `t_eval` externo e ignora `sol.t` nos resultados. Isso padroniza o shape do output: sempre `(8, N)`, mesmo que o integrador tenha usado 10× mais passos internamente.

## Próxima Nota

[[Segmentacao_e_Eventos]] — `_solve` não chama `_run` uma única vez. Divide a simulação em segmentos separados. Por quê?
