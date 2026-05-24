---
titulo: "Correntes a Partir de Fluxos"
capitulo: 05
status: publicado
iws_arquivo: "core/solver.py"
iws_linhas: "201–234"
---

# Correntes a Partir de Fluxos

> O solver integra fluxos — não correntes. Esta nota explica por que e como converter.

---

## O Problema

Você tem `y_history`: 8 linhas, N colunas. As 4 primeiras são fluxos magnéticos:

```
y[0] = PSIqs   (Wb) — fluxo de eixo q do estator
y[1] = PSIds   (Wb) — fluxo de eixo d do estator
y[2] = PSIqr   (Wb) — fluxo de eixo q do rotor
y[3] = PSIdr   (Wb) — fluxo de eixo d do rotor
```

Mas o gráfico precisa de correntes `ias`, `ibs`, `ics` — e a fórmula do torque também precisa de `ids`, `iqs`. Como chegar lá?

---

## A Tentativa Ingênua

Integrar correntes diretamente, como estado do ODE:

```python
# Parece mais direto: y[0]=iqs, y[1]=ids, y[2]=iqr, y[3]=idr
def rhs(t, y):
    iqs, ids, iqr, idr, wr, ... = y
    dIqs = (Vqs - Rs*iqs - wb*PSIds) / Xls
    ...
```

**Por que falha:** as equações de Krause são naturalmente expressas em fluxos. Reescrever em correntes exige inverter uma matriz 4×4 acoplada a cada passo — computacionalmente custoso e numericamente menos estável. Os fluxos variam mais suavemente que as correntes durante o inrush, o que facilita o controle de passo do LSODA.

---

## A Solução

Integrar fluxos (estável, natural para Krause) e reconstruir correntes **uma única vez** após a integração, operando sobre arrays inteiros. A inversão é analítica — não numérica.

**A chave:** fluxo total = fluxo de dispersão + fluxo mútuo.

```
PSIqs = Xls_eff * iqs + PSImq    →    iqs = (PSIqs - PSImq) / Xls_eff
```

Onde `PSImq` (fluxo mútuo de eixo q) é calculado primeiro:

```
PSImq = Xml * (PSIqs/Xls_eff + PSIqr/Xlr)
```

`Xml` é a reatância mútua do circuito π — ela redistribui o fluxo total entre estator e rotor proporcionalmente às dispersões.

---

## No Código

**`core/solver.py:201–234`** — função `_reconstruct_currents`:

```python
def _reconstruct_currents(PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp):
    # Passo 1: fluxo mútuo (eixos q e d separados)
    PSImq = mp.Xml * (PSIqs / mp.Xls_a_eff + PSIqr / mp.Xlr_a)
    PSImd = mp.Xml * (PSIds / mp.Xls_a_eff + PSIdr / mp.Xlr_a)

    # Passo 2: correntes de dispersão dq (inversão analítica)
    ids = (PSIds - PSImd) / mp.Xls_a_eff
    iqs = (PSIqs - PSImq) / mp.Xls_a_eff
    idr = (PSIdr - PSImd) / mp.Xlr_a
    iqr = (PSIqr - PSImq) / mp.Xlr_a

    # Passo 3: Park inversa (dq → αβ estático)
    # P^{-1} = P^T porque P é ortogonal — troca o sinal de sin
    cos_e, sin_e = np.cos(tetae), np.sin(tetae)
    cos_r, sin_r = np.cos(tetar), np.sin(tetar)
    iafs = ids * cos_e - iqs * sin_e   # componente α do estator
    ibts = ids * sin_e + iqs * cos_e   # componente β do estator
    iafr = idr * cos_r - iqr * sin_r   # componente α do rotor
    ibtr = idr * sin_r + iqr * cos_r   # componente β do rotor

    # Passo 4: Clarke inversa amplitude-invariante (αβ → abc)
    k    = np.sqrt(3.0 / 2.0)
    sq32 = _SQRT3_2   # sqrt(3)/2
    ias = k * iafs
    ibs = k * (-0.5 * iafs + sq32 * ibts)
    ics = k * (-0.5 * iafs - sq32 * ibts)
    # ... mesmo para rotor (iar, ibr, icr)
    return ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr
```

Chamada em **`core/IWS_PY.py:99`**:
```python
ids, iqs, idr, iqr, ias, ibs, ics, iar, ibr, icr = _reconstruct_currents(
    PSIqs, PSIds, PSIqr, PSIdr, tetae, tetar, mp
)
```

`tetae` (ângulo do referencial síncrono) = `mp.wb * t_values` — construído no pós-processamento, não vem do ODE. `tetar` é `y_history[5]` — o ângulo do rotor, integrado pelo solver.

---

## Consequências e Trade-offs

**Ganhos:**
- Reconstrução vetorizada: opera sobre arrays [N] em uma chamada — sem loop Python.
- Sem inversão matricial numérica a cada passo do ODE.
- `ias + ibs + ics = 0` é verificável — invariante físico para testar integridade.

**Custo:**
- `Xls_a_eff` vs `Xls_a`: o IWS usa uma reatância efetiva no circuito π, diferente da dispersão pura do circuito T. Confundir os dois dá correntes erradas.
- Se `Xml` estiver errado, todas as correntes ficam erradas — erro silencioso (não gera exceção).

---

## Referências

- IWS: `core/solver.py:201–234` (`_reconstruct_currents`)
- IWS: `core/IWS_PY.py:91–101` (extração de estados e chamada)
- [[Vetor_de_Estado_Detalhado]] — o que é cada `y[i]`
- [[Balanco_de_Potencia]] — usa `ids`, `iqs`, `Vds`, `Vqs` para P_in
