---
titulo: "Segmentação e Eventos"
capitulo: 04
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "51–182"
---

# Segmentação e Eventos

> Um integrador ODE assume que o lado direito da equação é contínuo — mas perturbações de tensão e desligamentos são descontinuidades abruptas. Ignorar isso e integrar em um único bloco produz erros numéricos que corrompem os transitórios.

## O Problema

Vários modos de simulação do IWS envolvem mudanças abruptas no meio da simulação:

- **Sag de tensão** — a tensão cai de 100% para 70% em `t = t_cutoff`
- **Pulso de carga** — o torque de carga dobra em `t = t_cutoff`
- **Desligamento** — a tensão vai a zero e o motor começa a desacelerar

Se `solve_ivp` integrar do início ao fim sem saber dessas mudanças, o LSODA usa sua heurística de passo adaptativo e pode atravessar `t_cutoff` com um único passo grande — perdendo completamente o transitório no instante da perturbação.

## A Tentativa Ingênua

Passar `t_span = (0, T_total)` e deixar o LSODA decidir os passos internamente. Ele vai chegar em `t_cutoff`, mas como a descontinuidade não está sinalizada, o erro de truncamento explode naquele instante e o integrador encolhe o passo *depois* — quando o dano já está feito.

Alternativa ingênua 2: integrar com passo fixo muito pequeno o tempo todo. Funciona, mas é 10–100× mais lento e desperdiça computação em regime permanente onde a dinâmica é lenta.

## A Solução

`_solve` divide a simulação em **segmentos independentes**. Cada segmento tem seu próprio `solve_ivp`, e o estado final de um segmento vira o estado inicial do próximo. A descontinuidade ocorre *entre* segmentos — nunca dentro de uma chamada ao integrador.

Dois mecanismos de divisão:

**1. `t_cutoff` — divisão determinística por tempo**

Quando o modo de simulação tem uma perturbação em instante conhecido, `_solve` recebe `t_cutoff`. A integração roda de `t=0` até `t_cutoff`, para, depois continua de `t_cutoff` até `T_total` com a nova equação (nova fonte de tensão, novo torque de carga).

```
Segmento 1: [0, t_cutoff]   ← tensão nominal
Segmento 2: [t_cutoff, T]   ← tensão com sag / torque novo
```

**2. `event_wr_zero` — divisão por evento (detecção de parada do motor)**

Para modos de desligamento, o motor desacelera até parar. O instante de parada não é conhecido a priori — depende da inércia, do atrito, do torque residual. `_solve` usa o mecanismo de *eventos* do `solve_ivp`:

```python
# solver.py, linhas 116–119
def event_wr_zero(t, y):
    return y[4] - 0.01 * _ws   # wr < 1% da velocidade síncrona

event_wr_zero.terminal = True
event_wr_zero.direction = -1
```

Quando `wr` cai abaixo de 1% da velocidade síncrona, o `solve_ivp` encerra o segmento no instante exato — sem ultrapassar. O restante do histórico é preenchido via `_ffill` (forward-fill do último estado).

## No Código

Estrutura de `_solve` (simplificada):

```python
# solver.py, linhas 51–182
def _solve(rhs, t_values, y0, mp, clamp_wr_at_zero, t_cutoff=None):
    y_history = np.full((8, len(t_values)), np.nan)  # buffer pré-alocado

    if not clamp_wr_at_zero:
        # Caminho simples: 1 ou 2 segmentos por t_cutoff
        if t_cutoff is not None:
            idx = np.searchsorted(t_values, t_cutoff)
            sol1 = _run(rhs, (t0, t_cutoff), y0, t_values[:idx])
            _fill(y_history, 0, sol1)
            sol2 = _run(rhs, (t_cutoff, T), sol1.y[:, -1], t_values[idx:])
            _fill(y_history, sol1.y.shape[1], sol2)
        else:
            sol = _run(rhs, (t0, T), y0, t_values)
            _fill(y_history, 0, sol)
        _ffill(y_history)
        return y_history

    else:
        # Caminho com clamp: detecta parada por evento, depois trava wr=0
        sol1 = _run(rhs, (t0, T), y0, t_values, events=event_wr_zero)
        _fill(y_history, 0, sol1)
        if sol1.t_events[0].size > 0:
            # Motor parou: continua com rhs_clamped (dwr/dt = 0)
            t_stop = sol1.t_events[0][0]
            y_stop = sol1.y_events[0][0]
            rhs_clamped = _make_clamped_rhs(rhs, y_stop[4])
            sol2 = _run(rhs_clamped, (t_stop, T), y_stop, t_values[offset:])
            _fill(y_history, offset, sol2)
        _ffill(y_history)
        return y_history
```

**`np.full(..., np.nan)`** — inicializa o buffer com NaN. Qualquer fatia não preenchida fica como NaN, que `_ffill` resolve com o último valor finito. Isso evita zeros espúrios se um segmento terminar antes do esperado.

**`np.searchsorted`** — encontra o índice de `t_cutoff` em `t_values` em O(log N). Divide o vetor de tempo sem copiar dados.

**`sol1.y[:, -1]`** — estado final do segmento 1 vira `y_init` do segmento 2. Continuidade garantida.

## Consequências e Trade-offs

**Precisão nos transitórios** — a divisão em segmentos garante que o LSODA recebe um problema suave em cada chamada. Os transitórios no instante de perturbação ficam corretos.

**Custo de múltiplos `solve_ivp`** — cada chamada tem overhead de inicialização do integrador (~1ms). Para 2–3 segmentos, insignificante. Se alguém tentar criar 100 perturbações no mesmo instante, o design não escala — mas esse caso não existe no IWS.

**`_ffill` como safety net** — se um segmento terminar cedo (por divergência numérica ou evento inesperado), o forward-fill propaga o último estado válido em vez de deixar NaN nos gráficos. O usuário vê uma curva plana no final em vez de um crash.

**`t_cutoff=None` é o caso comum** — a maioria dos modos (DOL, Y-Δ, autotransformador) não tem perturbação. `_solve` cai no caminho simples: um único `_run` do início ao fim.

## Próxima Nota

[[Vetor_de_Estado_Detalhado]] — `y0` tem 8 componentes. Qual é qual, em que unidade, e por que essa ordem específica?
