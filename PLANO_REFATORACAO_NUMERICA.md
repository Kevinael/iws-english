# Refatoração de Estabilidade Numérica — `core/EMS_PY.py`

## Contexto

O integrador LSODA estima o Jacobiano do sistema por diferenças finitas. Dois padrões no
código atual corrompem essa estimativa:

1. **Lgrid via Picard:** a queda indutiva `Lgrid·diqs/dt` é aproximada usando `dPSIqs_0`
   (derivada calculada sem a própria queda), criando uma dependência circular que torna o
   Jacobiano inconsistente quando `Lgrid` é comparável a `Lls`.

2. **Saturação via bootstrap:** `Lm_sat` é calculado a partir de `im_mag` estimado com `Lm0`
   linear, convertendo o esquema de integração implícita do LSODA em Euler explícito na direção
   da saturação — colapsa o controle de erro em partidas severas.

---

## Tarefa 1.1 — Lgrid: Absorção em `Xls_a_eff`

**Princípio:** `Lgrid` é fisicamente em série com `Lls`. A equação de Krause para `dPSIqs/dt`
com `Lgrid` presente reescreve-se exatamente com `Xls_total = Xls_a + Lgrid·wb`, sem nenhuma
derivada residual no RHS.

### Mudanças em `MachineParams` (`core/EMS_PY.py` — `__post_init__`)

1. Adicionar campo derivado (após linha 105, junto com `Xls_a`/`Xlr_a`):
   ```python
   Xls_a_eff: float = field(init=False)
   ```

2. Em `__post_init__`, **após** o bloco de auto-calibração térmica (linha 143), adicionar:
   ```python
   self.Xls_a_eff = self.Xls_a + self.Lgrid * self.wb
   ```
   E recalcular `self.Xml` com o novo `Xls_a_eff`:
   ```python
   _Xm_a      = self.wb * self.Lm
   self.Xml   = 1.0 / (1.0 / _Xm_a + 1.0 / self.Xls_a_eff + 1.0 / self.Xlr_a)
   ```
   O bloco térmico (linhas 128–143) **permanece usando `self.Xls_a`** — calibra a máquina
   sem rede, o que é a definição correta de Rth/Cth.

### Mudanças em `_make_rhs()` (linhas 329–451)

1. Substituir `Xls_a = mp.Xls_a` → `Xls_a = mp.Xls_a_eff` (linha 329).

2. Mudar `use_grid = (Rgrid != 0.0 or Lgrid != 0.0)` → `use_grid = (Rgrid != 0.0)` (linha 342).
   `Lgrid` não aparece mais no RHS.

3. Remover completamente o sub-bloco `if Lgrid != 0.0:` (linhas 412–416) — as 4 linhas do
   cálculo Picard (`dPSIqs_0`, `dPSIds_0`, `Vqs_eff -=`, `Vds_eff -=`).

   O bloco de rede resultante fica simplesmente:
   ```python
   if Rgrid != 0.0:
       Vqs_eff = Vqs_src - Rgrid * iqs
       Vds_eff = Vds_src - Rgrid * ids
   else:
       Vqs_eff = Vqs_src
       Vds_eff = Vds_src
   ```

4. Todas as chamadas a `_xml_from_lm(Lm, wb, Xls_a, Xlr_a)` dentro do RHS já passarão
   `Xls_a_eff` automaticamente — nenhuma outra mudança necessária no RHS.

### Mudanças em `_reconstruct_currents()` (linhas 589–619)

Substituir `mp.Xls_a` por `mp.Xls_a_eff` nas 4 ocorrências:
```python
PSImq = mp.Xml * (PSIqs / mp.Xls_a_eff + PSIqr / mp.Xlr_a)
PSImd = mp.Xml * (PSIds / mp.Xls_a_eff + PSIdr / mp.Xlr_a)
ids   = (PSIds - PSImd) / mp.Xls_a_eff
iqs   = (PSIqs - PSImq) / mp.Xls_a_eff
```
(`idr`/`iqr` usam `mp.Xlr_a` — sem mudança.)

**Por que:** `mp.Xml` agora é calculado com `Xls_a_eff`; usar `Xls_a` original na
reconstrução criaria inconsistência. As correntes reconstruídas passam a representar a
corrente de linha real (inclui queda em `Lgrid`), o que é fisicamente correto.

---

## Tarefa 1.2 — Saturação: Solução Fechada (Quadrática)

**Princípio:** a interseção entre a curva de Froelich e o estado atual é uma equação
quadrática em `u = 1 + im_mag/Im_sat` com solução analítica exata. Elimina o bootstrap.

### Derivação

Definindo (constantes para o passo atual):
```
Sq    = PSIqs/Xls_a + PSIqr/Xlr_a
Sd    = PSIds/Xls_a + PSIdr/Xlr_a
S_mag = sqrt(Sq² + Sd²)
K     = 1/Xls_a + 1/Xlr_a          ← pré-calcular fora do rhs()
Wb_L0 = wb * Lm0                    ← pré-calcular fora do rhs()
```

A equação de ponto fixo `im_mag = g(im_mag) · S_mag` — onde `g` envolve `Lm_sat` e `Xml_sat`
via Froelich — reduz-se à quadrática (substituição `u = 1 + im_mag/Im_sat`):

```
C1·u² + C2·u + C3 = 0
C1 = Im_sat
C2 = Im_sat·(Wb_L0·K − 1) − S_mag
C3 = −Im_sat·Wb_L0·K
```

Discriminante: `disc = C2² − 4·C1·C3 = C2² + 4·Im_sat²·Wb_L0·K > 0` sempre
(todos termos positivos → sem risco de raiz complexa).

Raiz positiva: `u = (−C2 + sqrt(disc)) / (2·C1)`
Resultado: `im_mag = Im_sat · max(u − 1, 0.0)`

### Código a substituir no bloco `if sat:` (linhas 370–386)

```python
# Pré-calcular FORA do rhs(), no fechamento de _make_rhs():
K     = 1.0 / Xls_a + 1.0 / Xlr_a
Wb_L0 = wb * Lm0

# Dentro de rhs(t, y), substituir o bloco if sat: por:
if sat:
    Sq    = PSIqs / Xls_a + PSIqr / Xlr_a
    Sd    = PSIds / Xls_a + PSIdr / Xlr_a
    S_mag = math.sqrt(Sq * Sq + Sd * Sd)
    if S_mag < 1e-15 or Im_sat <= 0.0:
        Xml_cur = _xml_from_lm(Lm0, wb, Xls_a, Xlr_a)
    else:
        C1   = Im_sat
        C2   = Im_sat * (Wb_L0 * K - 1.0) - S_mag
        C3   = -Im_sat * Wb_L0 * K
        disc = C2 * C2 - 4.0 * C1 * C3
        u    = (-C2 + math.sqrt(disc)) / (2.0 * C1)
        im_mag  = Im_sat * max(u - 1.0, 0.0)
        Lm_cur  = _lm_saturado(im_mag, Lm0, Im_sat)
        Xml_cur = _xml_from_lm(Lm_cur, wb, Xls_a, Xlr_a)
else:
    Xml_cur = _xml_from_lm(Lm0, wb, Xls_a, Xlr_a)
```

Custo: ~12 flops vs ~10 anteriores. Sem iteração. Jacobiano numérico do LSODA passa a
refletir a derivada exata de `Xml_cur` em relação aos estados.

---

## Arquivos Modificados

| Arquivo | Mudanças |
|---------|---------|
| `core/EMS_PY.py` | `MachineParams`: novo campo `Xls_a_eff`, recálculo de `Xml`; `_make_rhs()`: `Xls_a_eff`, remoção Picard, saturação quadrática; `_reconstruct_currents()`: `Xls_a_eff` |
| `core/curva_tn.py` | **Nenhuma** — usa `mp.Xls_a` para a curva estática da máquina sem rede (correto) |
| `ui_components/sim_config.py` | **Nenhuma obrigatória** — `mp.Xml` exibido já reflete `Xls_a_eff` |
| `viz/pdf_report.py` | **Nenhuma** — opera sobre arrays de corrente já reconstruídos |

---

## Verificação

1. Com `Lgrid = 0`: `Xls_a_eff = Xls_a` → resultado idêntico ao atual em todos os cenários.
2. Com `Lgrid > 0` e `sat_enable = False`: simular DOL e verificar que correntes de partida
   são menores (impedância maior) e que o solver não diverge.
3. Com `sat_enable = True`: verificar que `im_mag` calculado analiticamente coincide com o
   bootstrap em regime (onde a diferença é pequena) e estabiliza a partida direta com saturação.
4. Comparar `ias_rms` e `eta` em regime permanente (preset Krause 3 HP, DOL) — devem ser
   idênticos ao caso atual para `Lgrid = 0`.
