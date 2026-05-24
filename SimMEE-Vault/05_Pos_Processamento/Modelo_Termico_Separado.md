---
titulo: "Modelo Térmico Separado"
capitulo: 05
status: publicado
iws_arquivo: "core/thermal.py, core/solver.py"
iws_linhas: "thermal.py:1–113, solver.py:282–337"
---

# Modelo Térmico Separado

> Temperatura não está no ODE principal — esta nota explica por que e como funciona o modelo separado.

---

## O Problema

Você quer mostrar `Temp(t)` no gráfico — a evolução da temperatura do motor ao longo da simulação. O estado `y[6]` existe no vetor de estado... mas no código de `run_simulation`, há este comentário:

```python
# TEMP DESATIVADO: modelo térmico em revisão — retorna T_amb constante
Temp_arr = np.full(len(t_values), mp.T_amb)
```

Por que um campo de estado existe mas é ignorado? E onde a temperatura é realmente calculada?

---

## A Tentativa Ingênua

Colocar temperatura como estado `y[6]` do ODE e usar `dTemp_dt` direto no `rhs`:

```python
def rhs(t, y):
    iqs, ids, iqr, idr, wr, tetar, Temp, theta_slip = y
    ...
    P_joule = Rs * (ias**2 + ibs**2 + ics**2)
    dTemp   = dTemp_dt(Temp, P_joule, P_fe, Rth, Cth, T_amb)
    return [..., dTemp, ...]
```

**Por que falha:**

Escala de tempo incompatível. O LSODA controla o passo `h` para seguir os estados eletromagnéticos — que variam na escala de milissegundos (período de 1/60 Hz ≈ 16 ms). A constante de tempo térmica é `τ_th ≈ 1500 s` (25 minutos). O ODE fica implicitamente stiff na dimensão térmica: o solver usa passos minúsculos por causa dos fluxos, mas a temperatura precisaria de passos na escala de segundos.

Pior: durante o inrush (primeiros 5 ciclos elétricos, `t < 83 ms`), `P_joule` é 5–10× maior que o nominal porque as correntes são 5–10× maiores. Com `h` pequeno e `P_joule` enorme, a integração térmica acumula erro que produz aquecimento irreal de dezenas de graus em décimos de segundo.

---

## A Solução

Calcular temperatura em **pós-processamento**, com Euler implícito, sobre os arrays de corrente já integrados.

```
dT/dt = (P_joule + P_fe) / Cth  −  (T − T_amb) / (Rth · Cth)
```

Euler implícito é incondicionalmente estável para qualquer `dt` — pode usar `h` grande sem instabilidade. O pico de inrush é tratado separadamente: os primeiros `5/f` segundos recebem `P = P_ref` (média logo após o inrush) em vez do valor real, eliminando o aquecimento artificial.

**`Rth` e `Cth`** são estimados por `estimate_rth_cth` a partir dos parâmetros elétricos:
- `Rth = ΔT_nominal / P_perdas_nominal` — calibrado para ΔT=50 K em carga nominal (TEFC bem dimensionado).
- `Cth = τ_th / Rth` — onde `τ_th ∝ P_mec^0.25` (empírico de catálogos WEG/ABB/Siemens).

---

## No Código

**`core/thermal.py:46–93`** — `estimate_rth_cth`:

```python
def estimate_rth_cth(Vl, Rs, Rr, Xls_a, Xlr_a, Xm_a, s_nom=0.03):
    Vfase = Vl / sqrt(3)
    # Circuito T no escorregamento nominal
    Z_rotor    = complex(Rr / s_nom, Xlr_a)
    Z_mag      = complex(0.0, Xm_a)
    Z_paralelo = (Z_rotor * Z_mag) / (Z_rotor + Z_mag)
    Z_total    = complex(Rs, Xls_a) + Z_paralelo
    I_estator  = Vfase / abs(Z_total)
    I_rotor    = I_estator * abs(Z_mag / (Z_rotor + Z_mag))

    P_perdas = max(3 * (Rs*I_estator**2 + Rr*I_rotor**2), 10.0)
    Rth      = 50.0 / P_perdas          # ΔT=50 K alvo
    tau_th   = 1500.0 * (P_mec_kw / 2.2)**0.25   # τ ∝ P^0.25
    Cth      = tau_th / Rth
    return Rth, Cth
```

**`core/solver.py:282–337`** — `_compute_thermal`:

```python
def _compute_thermal(t_arr, ias, ibs, ics, iar, ibr, icr, PSImq, PSImd, mp, rr_arr=None):
    # P_joule via correntes abc com fator amplitude-invariante
    P_joule = (2/3) * (mp.Rs*(ias**2+ibs**2+ics**2) + Rr_arr*(iar**2+ibr**2+icr**2))
    P_fe    = mp.wb*(PSImq**2+PSImd**2)/mp.Rfe if mp.Rfe > 0 else 0

    # Substitui inrush (primeiros 5 ciclos) por P de referência
    n_skip  = int(round(5.0 / (mp.f * h)))
    P_total[:n_skip] = float(np.mean(P_total[n_skip:2*n_skip]))

    # Euler implícito: T[k+1] = (T[k] + dt*(P[k+1]/Cth + T_amb/(Rth*Cth))) / (1 + dt/(Rth*Cth))
    for k in range(N-1):
        dt      = t_arr[k+1] - t_arr[k]
        alpha   = dt / (Rth * Cth)
        Temp[k+1] = (Temp[k] + dt*(P_total[k+1]/Cth + T_amb/(Rth*Cth))) / (1 + alpha)
```

**Estado atual:** `_compute_thermal` existe mas está **desativado** em `IWS_PY.py:108`:
```python
# TEMP DESATIVADO: modelo térmico em revisão — retorna T_amb constante
Temp_arr = np.full(len(t_values), mp.T_amb)
```
A função está pronta; a decisão de reativar depende de validação dos parâmetros `Rth/Cth`.

---

## Consequências e Trade-offs

**Ganhos:**
- Euler implícito estável para qualquer `h` — sem restrição de passo para a térmica.
- Tratamento explícito do inrush: separa a física do artefato numérico.
- `_compute_thermal` aceita `rr_arr` — suporta barra quebrada com Rr variável no tempo.

**Custo:**
- Pós-processamento não retroalimenta o ODE: a temperatura não afeta `Rs` ou `Rr` durante a simulação. Motores reais têm `Rs(T)` — não modelado.
- `estimate_rth_cth` usa circuito T (não π): `Xm_a` e `Xls_a` devem ser do circuito T. Usar os parâmetros π do IWS sem conversão dá `Rth/Cth` errados.
- Estado `y[6]` (temperatura no ODE) foi planejado mas abandonado. O campo existe mas não é usado.

---

## Referências

- IWS: `core/thermal.py:46–93` (`estimate_rth_cth`)
- IWS: `core/thermal.py:96–112` (`dTemp_dt`)
- IWS: `core/solver.py:282–337` (`_compute_thermal`)
- IWS: `core/IWS_PY.py:107–108` (desativação atual)
- [[Vetor_de_Estado_Detalhado]] — `y[6]` como estado planejado
- [[Balanco_de_Potencia]] — `P_cu_s`, `P_cu_r`, `P_fe` alimentam o modelo térmico
