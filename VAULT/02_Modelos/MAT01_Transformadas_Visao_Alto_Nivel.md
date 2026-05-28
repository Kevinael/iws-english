# Transformadas de Coordenadas — Visão Conceitual

**Foco:** Por quê e para quê mudar de abc para dq.

---

## O Problema Original

Máquinas trifásicas **naturalmente** geram 3 tensões/correntes abc, defasadas 120°:

```
Va(t) = Vm·sin(ωe·t + φa)
Vb(t) = Vm·sin(ωe·t + φb − 2π/3)
Vc(t) = Vm·sin(ωe·t + φc + 2π/3)
```

**Simulação ingênua:** integrar 3 ODEs para Va, Vb, Vc → caótico, lento, impreciso.

```
dVa/dt = f(Va, Vb, Vc, ωr, ...)
dVb/dt = f(...)
dVc/dt = f(...)
```

Valores **oscilam continuamente** (senoidal a 60 Hz) → solver precisa de passos muito pequenos.

---

## A Solução: Referencial Dq Síncrono

**Ideia:** observar motor **de um referencial que gira com o rotor**.

De lá, tensões/correntes não oscilam mais:

```
Vds(t) = constante (ou lentamente variável)
Vqs(t) = constante
```

**Por quê?** Se senoide em abc oscila a 60 Hz (ωe), e você olha de um referencial girando a 60 Hz, o seno **vira constante**.

```
abc:  V(t) = Vm·sin(60Hz·t)     ← senoide que oscila
                    ↓
dq:   V(t) = Vm·sin(60Hz·t − 60Hz·t) = Vm·sin(0) = Vm  ← constante!
```

---

## Benefícios Matemáticos

### 1. **Redução de Equações**

- **abc:** 3 tensões trifásicas → 3 ODEs
- **dq:** 2 componentes (d e q) → 2 ODEs
- **Prática:** 8 estados totais (ids, iqs, idr, iqr, λds, λdr, ωr, θr)

### 2. **Regime Permanente DC**

Em regime (motor em velocidade constante):

```
abc:  Va(t) = 310·sin(377·t) ← oscila 60 vezes/seg
dq:   Vqs = 310 V            ← constante
```

Solver LSODA adora constantes → passos grandes, menos iterações.

### 3. **Desacoplamento Parcial**

Eixos d e q acoplam **via velocidade angular ωr** (termo 2·ωr·Ψ tipo):

```
ids' = f(ids, iqs, ωr, ...)
iqs' = f(ids, iqs, ωr, ...)  ← ωr é o acoplador
```

Mas **não há acoplamento cruzado** (ids não aparece isoladamente em iqs'). Isso torna Jacobiano mais esparso → solver mais rápido.

---

## Geometria: Os Três Referenciais

```
┌─────────────────────────────────────────────────────────┐
│ REFERENCIAL FIXO NO ESTATOR (abc e αβ)                │
│                                                        │
│            Va                                          │
│            ↑                                           │
│         0°/ \                                          │
│           /   \120°                                    │
│        Vc/     \Vb                                     │
│                                                        │
│  Eixo α ← —— →                                         │
│  (referencial fijo, não gira)                         │
└─────────────────────────────────────────────────────────┘
        
        ↓ Rotação por tetae
        
┌─────────────────────────────────────────────────────────┐
│ REFERENCIAL GIRANTE (dq sincrono)                       │
│                                                        │
│           Vqs (quadratura)                            │
│            ↑                                           │
│            │  tetae                                   │
│            │    / (ângulo síncrono)                  │
│   ─ ─ ─ ─ ─ ┴ ─ ─ ─ ─ → Vds (direto)               │
│    (rotor está aqui!)                                │
│                                                        │
└─────────────────────────────────────────────────────────┘
```

**Transformada Park:** Rodar αβ para alinhar com rotor.

---

## Ângulo Síncrono tetae

```
tetae(t) = ∫₀ᵗ ωe(τ) dτ = ∫₀ᵗ p·ωr(τ) dτ
```

- **p = polos/2** (máquina com 4 polos → p=2)
- **ωr = velocidade mecânica** (rad/s)
- **ωe = p·ωr = velocidade elétrica** (rad/s)

**Interpretação:** Se rotor gira a ωr, referencial elétrico dq gira a ωe = p·ωr.

---

## Transformações Passo a Passo

### Clarke: abc → αβ (Estator Fixo)

```
     ┌───────────────┐
     │  Va, Vb, Vc  │
     │  (3 fases)   │
     └───────┬───────┘
             │
      [Matriz Clarke]  ← projeção em plano αβ
             │
     ┌───────▼───────┐
     │  Vα, Vβ       │
     │  (2 eixos)    │
     └───────────────┘
```

Matriz:
```
[Vα]      [1      -1/2    -1/2  ] [Va]
[Vβ]  = k*[0   √3/2  -√3/2 ] [Vb]
           [...]                 [Vc]
```

Fator k = √(3/2) para amplitude-invariante.

### Park: αβ → dq (Síncrono Girante)

```
     ┌───────────────┐
     │  Vα, Vβ       │
     │  (fixo)       │
     └───────┬───────┘
             │
      [Rotação por tetae]  ← mudar frame de referência
             │
     ┌───────▼───────┐
     │  Vds, Vqs     │
     │  (girante)    │
     └───────────────┘
```

Matriz (2D):
```
[Vds]    [cos(tetae)   sin(tetae) ] [Vα]
[Vqs]  = [-sin(tetae)  cos(tetae) ] [Vβ]
```

---

## Exemplo Intuitivo: Motor em Partida

**Cenário:** Motor DOL (direct-on-line) a 60 Hz, rotor inicialmente parado.

**t = 0 (rotor parado, ωr = 0):**
- tetae = 0 (dq alinhado com abc)
- Va(t) = 310·sin(377·t) ← oscila
- Vqs(t) varia rapidamente ← dq muda com abc

**t = 0.1 s (rotor acelerado a ωr ≈ 60 Hz mecânico = 120 rad/s elétrico):**
- tetae = p·ωr ≈ 2·(ramp de 0 a 120) = variação contínua
- Va(t) = 310·sin(377·t) ← ainda oscila em abc
- Vqs(t) ≈ 310 V **constante** em dq (dq gira com o fluxo)

**Vantagem:** Solver trabalha com valores quase-DC, passos maiores.

---

## Perdas de Informação? Não!

Transformada Park é **reversível** (bijetiva):

```
abc → Clarke → Park → dq        (sempre reversível)
dq → Park⁻¹ → Clarke⁻¹ → abc   (volta ao original)
```

Nenhuma informação é perdida. Apenas **muda de frame de referência**.

---

## Sequência de Rotação (abc vs cba)

Convenção: **Va ref 0°, Vb -120°, Vc +120°** = sequência **positiva (abc)**.

Se invertesse (Va, Vc, Vb), torque invertia. **Crítico não quebrar.**

---

## Resumo Conceitual

| Aspecto | abc | dq sincrono |
|---------|-----|------------|
| **Nº eixos** | 3 | 2 |
| **Regime permanente** | Senoidal 60 Hz | DC (constante) |
| **Tipo solver** | Passos pequenos | Passos grandes |
| **Velocidade soluçao** | Lenta | Rápida |
| **Interpretação física** | Máquina fixa | Máquina girante |

---

## Próximo: Código

Ver [[MAT01_Transformadas_Codigo]] para implementação em Python com NumPy.

---

**Criado:** 2026-05-26 | **Status:** ✅ Completo (Visão conceitual)
