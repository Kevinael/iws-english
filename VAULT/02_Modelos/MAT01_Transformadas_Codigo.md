# Transformadas de Coordenadas — Implementação em Código

**Arquivo:** [`core/transforms.py`](../../core/transforms.py)

**Objetivo:** Entender **como e por quê** o código muda de abc para dq. Não apenas ler sintaxe, mas raciocinar sobre escolhas de engenharia.

---

## 0. Problema de Engenharia Que Motiva Tudo

Você está programando um integrador numérico (LSODA). Precisa escolher:

**Opção A:** Integrar 3 equações (abc) que **oscilam continuamente** a 60 Hz
```
ids(t) = I0 + 10·sin(377·t + φ)  ← muda a cada milissegundo
iqs(t) = I0 + 10·sin(377·t + φ)  ← mesma oscilação
idr(t) = ...
```

Solver LSODA precisa de passos **muito pequenos** (< 0.001 s) para não perder o seno. Lento, erros acumulam.

**Opção B:** Integrar 2 equações (dq) que são **quase-constantes**
```
ids = 5 A      ← muda lentamente ou fica cte
iqs = 8 A      ← muda lentamente ou fica cte
idr = 2 A
```

Solver pega passos **grandes** (0.01–0.1 s). Rápido, preciso.

**Transformada Park faz essa conversão.** É puro pragmatismo computacional.

---

## 1. Fluxo Visual (O que Acontece)

```
┌─────────────────────────────────────────────────┐
│ FONTE (gerador de tensão trifásica)             │
│   Gera Va(t), Vb(t), Vc(t) oscilando a 60 Hz  │
└────────────┬────────────────────────────────────┘
             │
             ↓ transforms.abc_voltages(t, Vl, f)
             │ "Pegue instante t, calcule 3 senoides"
             │
      ┌──────┴──────┐
      │ Va, Vb, Vc  │  Ainda oscilando
      └──────┬──────┘
             │
             ↓ transforms.clarke_park_transform(Va, Vb, Vc, tetae)
             │ "Mude referencial: saia de abc, entre em dq"
             │
      ┌──────┴──────┐
      │  Vds, Vqs   │  Quase-constantes em dq (rotor acompanha)
      └──────┬──────┘
             │
             ↓ core/machine_model.py::MachineModel.step()
             │ "Calcule as 8 derivadas com Vds, Vqs"
             │
      ┌──────┴──────┐
      │ dydt vetor  │  Retorna ao LSODA
      └─────────────┘
```

---

## 2. Por Quê k = √(2/3) e √(3/2)?

Abre [`core/transforms.py`](../../core/transforms.py) linhas 38–42.

```python
def abc_voltages(t, Vl: float, f: float):
    tetae = 2.0 * np.pi * f * t
    k = np.sqrt(2.0 / 3.0)  ← linha 39
    Va = k * Vl * np.sin(tetae)
    Vb = k * Vl * np.sin(tetae - 2.0 * np.pi / 3.0)
```

**Pergunta:** Por quê multiplicar por k antes?

**Resposta (antes do exercício):**

Pense em uma corrente elétrica fluindo. Se você tem:
```
Ia = 10 A
Ib = 10 A  
Ic = 10 A
```

A **potência total** é:
```
P_abc = Va·Ia + Vb·Ib + Vc·Ic
```

Agora, se você transforma para dq sem cuidado:
```
Ids, Iqs = transform(Ia, Ib, Ic)  → (7 A, 7 A) ← PERDEU energia!
```

A potência em dq fica:
```
P_dq = Vds·Ids + Vqs·Iqs  ← diferente de P_abc
```

**Solução:** Multiplique por fator k na **geração abc** e k⁻¹ na **transformação**, de forma que:

```
P_abc = Va·Ia + Vb·Ib + Vc·Ic
      = Vds·Ids + Vqs·Iqs = P_dq  ← mesma potência!
```

Isso chama **amplitude-invariante** — grandezas mudam de coordenada mas **mantêm magnitude**.

Linhas 57–58 fazem o inverso:

```python
def clarke_park_transform(Va, Vb, Vc, tetae):
    k = np.sqrt(3.0 / 2.0)  ← linha 57, inverso de √(2/3)
```

Multiplicar por √(3/2) "desfaz" o √(2/3) anterior, restaura amplitude.

**Teste mental:**
```
Va_abc_gerado = √(2/3) × 380 × sin(...) = 310 V (amplitude)
            ↓ Clarke-Park com k = √(3/2)
Vqs_dq = √(3/2) × (contas de Clarke) ≈ 310 V ← restaurado!
```

---

## 3. Clarke e Park São Operações Geometricamente Distintas

Linhas 59–64 fazem **duas transformações encadeadas**. Leia:

```python
# Linha 59-60: Clarke (abc → αβ)
Vaf = k * (Va - 0.5 * Vb - 0.5 * Vc)
Vbt = k * _SQRT3_2 * (Vb - Vc)

# Linha 63-64: Park (αβ → dq)
Vds =  np.cos(tetae) * Vaf + np.sin(tetae) * Vbt
Vqs = -np.sin(tetae) * Vaf + np.cos(tetae) * Vbt
```

**O que Clarke faz (abc → αβ):**

Imagina 3 eixos xyz (representam abc). Clarke **projeta** tudo em um **plano 2D**:
```
3D (Va, Vb, Vc)  →  Projeção em plano (Vα, Vβ)
```

Por quê projetar? Porque a sequência **zero** (Va + Vb + Vc = 0 em balanço) é redundante — perde-se sem informação. Clarke elimina essa redundância.

**O que Park faz (αβ → dq):**

Imagina o plano αβ como um **quadro fixo no estator**. Park **roda esse quadro** para se alinhar com o **rotor girante**:
```
Quadro fixo (α, β)  →  Rotação por ângulo tetae  →  Quadro girante (d, q)
```

**Por quê rodar?** Para que coordenadas dq fiquem **quase-estacionárias** (não oscilem).

---

## 4. Ângulo tetae: A Chave de Tudo

Linha 51 diz: `tetae: angulo eletrico do referencial sincrono (rad)`.

**Onde vem tetae?**

No solver (`core/solver.py`), antes de chamar `clarke_park_transform()`, calcula:
```python
tetae = p * y[6]  # p = polos/2, y[6] = ωr (velocidade rotor)
```

**Interpretação:**
- Se rotor **parado** (ωr = 0) → tetae = 0 → Park não roda, dq = αβ
- Se rotor **acelerado** (ωr = 100 rad/s) → tetae = p × 100 → Park roda continuamente
- **Quanto mais rápido rotor gira, mais Park roda**, acompanhando rotação

Isso é **síncrono** — dq gira junto com rotor, vê mundo em câmera lenta.

---

## 5. Ordem Importa: (Vds, Vqs) Não é (Vqs, Vds)

Linhas 63–64 retornam `(Vds, Vqs)` nessa ordem.

**Por quê?**

Convenção Krause (standard em máquinas):
- **d = eixo direto (real)** = alinhado com fluxo do rotor
- **q = eixo quadratura (imaginário)** = perpendicular, **produtor de torque**

Se invertesse para `(Vqs, Vds)`:
```
Vqs entra onde Vds deveria → torque inverte
Simulação quebra
```

**Regra:** Sempre `(d_antes, q_depois)`. Esse padrão propaga no código todo.

---

## 6. Por Quê Não Usar Matriz Explícita?

Linhas 59–64 **poderiam** ser uma matriz:

```python
# ❌ Possível mas lento com arrays (muitos timesteps)
V_Clarke_Park = np.array([
    [k*cos(tetae), k*(-0.5*cos - √3/2*sin), ...],
    [k*sin(tetae), ...]
]) @ np.array([Va, Vb, Vc])
```

**Porquê não?** Porque `t` é um **array** (muitos instantes):
```python
t = np.linspace(0, 2, 10000)  # 10k instantes
Va, Vb, Vc = abc_voltages(t, ...)  # retorna arrays 10k × 1
```

NumPy vectoriza **operações escalares** mais eficiente que **operações matriciais**:
```python
# ✅ Rápido: elemento-a-elemento
Va - 0.5*Vb - 0.5*Vc  # vectorizado em 10k elementos

# ❌ Lento: alocação matriz por timestep
[np.linalg.inv(...) @ [...] for t_i in t]
```

**Decisão de design:** Código usa operações escalares que NumPy vectoriza.

---

## 7. Resumo: Lógica, Não Cópia

| Linha | O Que Faz | Por Quê |
|-------|-----------|--------|
| 39, 57 | k e k⁻¹ | Preservar energia (amplitude-invariante) |
| 59–60 | Clarke | Reduzir 3D → 2D, eliminar redundância zero |
| 63–64 | Park | Rodar para frame girante, valores quase-ctes |
| 51 param | tetae | Ângulo síncrono do rotor, conecta tudo |
| ordem dq | `(Vds, Vqs)` | Convenção Krause: d real, q imagináririo |
| funcs escalares | Não matriz | NumPy vectoriza melhor |

---

## Próximo: Exercício

Ver [[MAT01_Transformadas_Exercicio]].

---

## Função 1: `abc_voltages(t, Vl, f)`

**Assinatura:**
```python
def abc_voltages(t, Vl: float, f: float):
    """Tensoes abc balanceadas (amplitude-invariante).
    
    Args:
        t:   instante(s) em segundos — escalar ou array NumPy.
        Vl:  tensao de linha pico-a-pico (V).
        f:   frequencia (Hz).
    
    Returns:
        (Va, Vb, Vc) — tensoes de fase, mesma forma que t.
    """
```

**Implementação:**

```python
tetae = 2.0 * np.pi * f * t
k = np.sqrt(2.0 / 3.0)
Va = k * Vl * np.sin(tetae)
Vb = k * Vl * np.sin(tetae - 2.0 * np.pi / 3.0)      # -120°
Vc = k * Vl * np.sin(tetae + 2.0 * np.pi / 3.0)      # +120°
return Va, Vb, Vc
```

### Análise Linha por Linha

| Linha | Operação | Por Quê |
|-------|----------|--------|
| `tetae = 2π·f·t` | Ângulo elétrico (rad) | Argumento do seno: ωe·t, onde ωe = 2πf |
| `k = √(2/3)` | Fator de normalização | **Convenção amplitude-invariante** — preserva |Vabcd| = |Vdq| |
| `Va = k·Vl·sin(tetae)` | Fase A, ref 0° | Senoide pura, defasagem 0 |
| `Vb = k·Vl·sin(...−2π/3)` | Fase B, ref -120° | Defasagem -120°, sequência abc |
| `Vc = k·Vl·sin(...+2π/3)` | Fase C, ref +120° | Defasagem +120°, sequência abc |

### Fator k = √(2/3): Amplitude-Invariante?

**Sem k:**
```
Va_abc (pico)    = 10 V
↓ Clarke-Park (sem k)
Vqs_dq (pico)    = 7 V  ← PERDEU amplitude!
```

**Com k = √(2/3):**
```
Va_abc (pico)    = 10 V
↓ Clarke-Park (com k inverso = √(3/2))
Vqs_dq (pico)    = 10 V  ← preservado
```

**Vantagem:** Fórmula de potência fica simples:
```
P = (3/2) × (Vqs·iqs + Vds·ids)
```

Sem k invertido, teríamos fator de correção feio.

### Exemplo Numérico

**Setup:**
- V_linha = 380 V
- f = 60 Hz
- t = 0 s

**Cálculo:**
```python
Va = √(2/3) * 380 * sin(0)           = 0 V
Vb = √(2/3) * 380 * sin(-2π/3)       ≈ -310 V
Vc = √(2/3) * 380 * sin(2π/3)        ≈ +310 V
```

Ponto: 3 tensões defasadas 120°, balanço (soma zero a cada instante).

---

## Função 2: `clarke_park_transform(Va, Vb, Vc, tetae)`

**Assinatura:**
```python
def clarke_park_transform(Va, Vb, Vc, tetae):
    """Clarke + Park: abc -> dq sincrono.
    
    Args:
        Va, Vb, Vc: tensoes de fase (escalar ou array).
        tetae:      angulo eletrico do referencial sincrono (rad).
    
    Returns:
        (Vds, Vqs) — componentes no referencial dq sincrono.
    """
```

**Implementação:**

```python
k   = np.sqrt(3.0 / 2.0)
# Clarke (abc -> αβ)
Vaf = k * (Va - 0.5 * Vb - 0.5 * Vc)
Vbt = k * _SQRT3_2 * (Vb - Vc)
# Park (αβ -> dq sincrono)
Vds =  np.cos(tetae) * Vaf + np.sin(tetae) * Vbt
Vqs = -np.sin(tetae) * Vaf + np.cos(tetae) * Vbt
return Vds, Vqs
```

### Decompondo Clarke-Park

#### Passo 1: Clarke (abc → αβ)

Matriz de Clarke (amplitude-invariante, k=√(3/2)):

```
     ┌───────────────────────────────┐
     │  Vα = k·(Va − 0.5·Vb − 0.5·Vc)│
     │  Vβ = k·√3/2·(Vb − Vc)        │
     └───────────────────────────────┘
```

**Intuição:** Projeção de abc (3D) em plano αβ (2D fixo no estator).

- **Vα:** combinação linear que elimina sequência zero (3·Va + 3·Vb + 3·Vc = 0 em balanço)
- **Vβ:** ortogonal a Vα, captura componente restante

#### Passo 2: Park (αβ → dq sincrono)

Rotação de coordenadas por ângulo tetae:

```
     ┌────────────────────────────────────────┐
     │ Vds =  cos(tetae)·Vα + sin(tetae)·Vβ   │
     │ Vqs = −sin(tetae)·Vα + cos(tetae)·Vβ   │
     └────────────────────────────────────────┘
```

**Intuição:** Muda frame de referência — do **frame fixo (αβ)** para **frame girante com rotor (dq)**.

- **Vds:** projeção no eixo d (direto), alinhado com fluxo do rotor
- **Vqs:** projeção no eixo q (quadratura), perpendicular a d

### Ordem de Eixos: d Antes de q

Note a ordem `(Vds, Vqs)`. Krause (2013) usa **d como eixo real, q como imaginário** (convenção padrão em máquinas).

⚠️ **Crítico:** Inverter ordem quebra simulação (inverte torque, oscilações spurias).

### Matriz Compacta (Alternativa Teórica)

Combinado Clarke + Park:

```
┌─────┐   ┌───────────────────────┐ ┌────────────────┐ ┌────┐
│ Vds │   │ cos·1  cos·(−0.5)  ... │ │   k            │ │ Va │
│ Vqs │ = │−sin·1 −sin·(−0.5)  ... │ │      √(3/2)    │ │ Vb │
└─────┘   └───────────────────────┘ │              .. │ │ Vc │
                                     └────────────────┘ └────┘
```

**Código não usa matriz:** Operações escalares vectorizam melhor com NumPy quando t é array (muitos instantes).

---

## Fluxo na Simulação

**Localização no projeto:**

```
core/solver.py::_dydt(t, y)
  ├─ t: instante atual
  ├─ y: vetor estado (8 elementos)
  │
  ├─ 1. Gerar tensões abc:
  │  Va, Vb, Vc = transforms.abc_voltages(t, Vl, f)
  │
  ├─ 2. Calcular ângulo síncrono:
  │  tetae = p * y[6]  # p=polos/2, y[6]=ωr
  │
  ├─ 3. Transformar para dq:
  │  Vds, Vqs = transforms.clarke_park_transform(Va, Vb, Vc, tetae)
  │
  └─ 4. Passar ao modelo de máquina:
     dydt_mech = machine_model.step(ids, iqs, idr, iqr, λds, λdr, ωr, Vds, Vqs, ...)
```

Saída: vetor `dydt` com 8 derivadas, retorna ao LSODA.

---

## Exemplo Numérico Completo

**Condições:**
- V_linha = 380 V
- f = 60 Hz
- t = 0.01 s
- ωr = 100 rad/s (rotor girando)
- p = 2 polos (máquina)

**Passo 1: abc_voltages**

```python
tetae_src = 2π * 60 * 0.01 = 3.77 rad ≈ 216°

Va = √(2/3) * 380 * sin(3.77) ≈ −255 V
Vb = √(2/3) * 380 * sin(3.77 − 2π/3) ≈ +127 V
Vc = √(2/3) * 380 * sin(3.77 + 2π/3) ≈ +127 V
```

**Passo 2: Ângulo síncrono**

```python
tetae_sinc = p * ωr = 2 * 100 = 200 rad ≈ 32.39 rad (módulo 2π)
```

**Passo 3: clarke_park_transform**

```python
Vaf = √(3/2) * (−255 − 0.5*127 − 0.5*127) ≈ −342 V
Vbt = √(3/2) * √3/2 * (127 − 127) = 0

Vds = cos(200)*Vaf + sin(200)*0 ≈ cos(32.39)*(-342) ≈ −288 V
Vqs = −sin(200)*Vaf + cos(200)*0 ≈ −sin(32.39)*(-342) ≈ +182 V
```

**Resultado:** Vds ≈ -288 V, Vqs ≈ +182 V (constantes em dq, se rotor velocidade cte).

---

## Convenções Críticas (Não Quebrar!)

| Convenção | Valor | Implicação |
|-----------|-------|-----------|
| **Amplitude-invariante** | k_abc = √(2/3), k_dq = √(3/2) | Modulo preservado abc ↔ dq |
| **Ordem dq** | Vds, Vqs (d primeiro) | Compatível com Krause 2013 |
| **Sequência abc** | Va, Vb -120°, Vc +120° | Sequência positiva (motor cc) |
| **Eixo d = real Park** | cos·α + sin·β | Alinhado com fluxo do rotor |
| **Eixo q = imag Park** | −sin·α + cos·β | Perpendicular, torque-produtor |

**Teste:** Se quebrar qualquer uma, simulação diverge ou inverte torque.

---

## Resumo de Funções

| Função | Entrada | Saída | Uso |
|--------|---------|-------|-----|
| `abc_voltages(t, Vl, f)` | tempo, amplitude, freq | Va, Vb, Vc | Gerar excitação |
| `clarke_park_transform(...)` | Va, Vb, Vc, tetae | Vds, Vqs | Transformar para simulador |

**Inverso (dq → abc):** Não implementado em `transforms.py`. Se precisar, ver `[ MAT01_Transformadas_Visao_Alto_Nivel ]` para fórmulas.

---

## Próximo Bloco

[[MAT02_MachineModel_Estrutura]] — Como Vds, Vqs entram no modelo dq0.

---

**Criado:** 2026-05-26 | **Status:** ✅ Completo (Bloco 2.1)
