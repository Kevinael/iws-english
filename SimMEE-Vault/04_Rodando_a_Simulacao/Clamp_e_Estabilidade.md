---
titulo: "Clamp e Estabilidade"
capitulo: 04
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "110–182"
---

# Clamp e Estabilidade

> Quando um motor real para, ele fica parado. Quando um motor simulado para sem o clamp, ele começa a girar para trás — e o integrador diverge tentando acompanhar uma física impossível.

## O Problema

No modo de desligamento, a tensão vai a zero e o motor desacelera. A equação mecânica é:

```
dωr/dt = (Te - Tload - B·ωr) / J
```

Com `Te → 0` (sem tensão) e `Tload > 0` (atrito, carga), a derivada `dωr/dt` é sempre negativa. O motor desacelera corretamente até `ωr = 0` — mas então a equação continua sendo integrada com `dωr/dt < 0`, e `ωr` passa a ficar negativo.

`ωr < 0` significa que o modelo matemático começa a simular o motor girando para trás como gerador reverso — o que não corresponde a nenhum fenômeno físico no cenário de desligamento simples. Pior: como `ωr` entra nas equações de fluxo via termos `ωr·Ψ`, valores negativos crescentes fazem as derivadas de fluxo explodirem, e o LSODA entra em colapso numérico (passos cada vez menores, custo computacional infinito).

## A Tentativa Ingênua

Adicionar um `if wr < 0: wr = 0` dentro do `rhs`. 

Problema: `rhs` é chamado pelo LSODA centenas de vezes por instante de tempo para estimar derivadas e erros. Modificar `y[4]` dentro de `rhs` viola a hipótese do integrador de que `rhs` é uma função pura — o LSODA esperaria que `rhs(t, y)` e `rhs(t, y)` retornassem o mesmo valor, mas com o clamp interno isso deixa de ser verdade. O resultado é divergência numérica silenciosa.

## A Solução

O IWS resolve isso com dois mecanismos coordenados:

**1. Detecção por evento** — `solve_ivp` encerra o segmento exatamente quando `ωr` atinge 1% da velocidade síncrona:

```python
# solver.py, linhas 116–119
def event_wr_zero(t, y):
    return y[4] - 0.01 * _ws  # cruza zero quando ωr = 1% de ωs

event_wr_zero.terminal = True   # encerra a integração
event_wr_zero.direction = -1    # detecta cruzamento descendente
```

`direction = -1` garante que o evento só dispara quando `ωr` está caindo (não na partida, quando `ωr` também cruza esse limiar subindo).

**2. Continuação com RHS travado** — após a parada, um novo `rhs_clamped` é construído com `dωr/dt = 0` forçado:

```python
# solver.py, linhas 145–148
def rhs_clamped(t, y):
    dydt = rhs(t, y)  # calcula derivadas normais
    dydt[4] = 0.0     # trava: ωr não muda mais
    return dydt
```

Este `rhs_clamped` é então passado para um segundo `solve_ivp` que integra do instante de parada até o final da simulação. Os fluxos e temperatura continuam evoluindo (o motor desmagnetiza gradualmente), mas `ωr` permanece exatamente em zero.

Por que não simplesmente parar a simulação quando o motor para? Porque o usuário quer ver a desmagnetização — o decaimento exponencial dos fluxos após o desligamento é fisicamente correto e visualmente importante.

## No Código

O fluxo completo do caminho `clamp_wr_at_zero=True`:

```python
# solver.py, linhas 110–182 (simplificado)
if clamp_wr_at_zero:
    # Segmento 1: integração normal, com evento de parada
    sol1 = _run(rhs, (t0, T_total), y0, t_eval_1, events=event_wr_zero)
    offset = _fill(y_history, 0, sol1)

    if sol1.t_events[0].size > 0:
        # Motor parou: captura instante e estado exatos
        t_stop = sol1.t_events[0][0]     # tempo exato da parada
        y_stop = sol1.y_events[0][0]     # estado exato no instante da parada

        # Garante que ωr seja exatamente 0 no estado inicial do seg. 2
        y_stop[4] = 0.0

        # Segmento 2: fluxos e temperatura continuam, ωr travado
        rhs_clamped = lambda t, y: [*rhs(t, y)[:4], 0.0, *rhs(t, y)[5:]]
        sol2 = _run(rhs_clamped, (t_stop, T_total), y_stop, t_eval_2)
        _fill(y_history, offset, sol2)

    _ffill(y_history)
```

**`sol1.t_events[0]`** — lista de instantes em que `event_wr_zero` disparou. `[0]` pega o primeiro (e único) evento. Se estiver vazia, o motor não chegou a parar no tempo simulado — sem segmento 2.

**`y_stop[4] = 0.0`** — correção explícita: o evento dispara em `ωr = 0.01·ωs` (não exatamente zero), então o estado capturado tem `ωr ≈ 0.01·ωs`. Forçar para zero exato elimina o drift no segmento 2.

**`_ffill` no final** — se o motor parou antes do fim de `t_eval`, as colunas restantes ficaram NaN. `_ffill` propaga o estado da parada para todos os instantes restantes — a curva de ωr aparece plana em zero no gráfico.

## Consequências e Trade-offs

**Precisão do instante de parada** — o evento do `solve_ivp` localiza `t_stop` com precisão do `rtol` (~1e-6s). Muito mais preciso que um loop manual verificando `ωr < threshold` a cada passo.

**Custo do `clamp_wr_at_zero=False`** — para modos que não têm desligamento (DOL, Y-Δ, etc.), o clamp é desnecessário. O parâmetro `clamp_wr_at_zero=False` pula toda a lógica de evento e usa o caminho simples. Sem overhead para o caso comum.

**`rhs_clamped` não é fisicamente perfeito** — ao travar `dωr/dt = 0`, o torque elétrico `Te` calculado internamente pode não ser zero (resíduo numérico). Fisicamente, isso equivale a assumir que o rotor está mecanicamente travado — uma aproximação aceitável para o propósito de mostrar a desmagnetização.

**Limite de aplicabilidade** — `clamp_wr_at_zero` é ativado apenas para modos de desligamento e frenagem por injeção de CC. Para o modo de plugging (inversão de fase para frear), `ωr` pode legitimamente cruzar zero e reverter — nesse caso o clamp não seria aplicado.

## Próxima Nota

Este capítulo completa a jornada de `rhs` ao resultado numérico. O Cap 5 cobre o pós-processamento: como `y_history` (8×N de fluxos e ωr) vira correntes, torque, potência e temperatura exibíveis nos gráficos.

[[../05_Pos_Processamento/Extraindo_Correntes_dos_Fluxos]]
