# Plano: Integração MCC ao IWS
## Versão 3 — 2026-05-27

---

## 1. Princípio Central

**Uniformidade UI obrigatória.** Toda UI da MCC espelha exatamente a UI MIT — mesmo layout de duas colunas, mesmas 4 sub-abas de resultados, mesmos CSS, mesmos padrões de componentes. Usuário que conhece MIT opera MCC sem surpresas.

---

## 2. Escopo

### Configurações de excitação (v1)

| Código | Tipo | Modo | ODEs — fonte Scilab |
|--------|------|------|---------------------|
| `sep_motor` | Excitação separada | Motor | `dcmei.sce:38–45` |
| `sep_gen` | Excitação separada | Gerador | `dgmei.sce:43–50` |
| `shunt_motor` | Shunt (paralelo) | Motor | `dcmp.sce:37–44` |
| `shunt_gen` | Shunt (paralelo) | Gerador | `dcgp.sce:33–36` (x1, x2) |
| `series_motor` | Série | Motor | `dcms.sce:38–43` |

Compound (`long_*`, `short_*`) — desenhados no notebook, **fora do escopo v1**.

### Modos de operação

| Modo | `exp_type` | Disponível para |
|------|-----------|-----------------|
| Partida direta (DOL) | `dol_dc` | todos motores |
| Partida com resistência série | `resistencia_dc` | todos motores |
| Reversão de rotação (plugging) | `plugging_dc` | todos motores |
| Pulso de carga | `pulso_dc` | todos motores |
| Gerador — carga resistiva | `gerador_dc` | sep_gen, shunt_gen |
| Enfraquecimento de campo | `campo_fraco_dc` | sep_motor |

### Ênfase pedagógica

Diferencial da MCC: mostrar como excitação altera comportamento.
- **Curva T×ωn:** série (hiperbólica T∝ia²), shunt (quase linear), separado (ajustável por Vf)
- **Transitório ia:** série pico maior; shunt estabelecimento suave
- **Enfraquecimento de campo:** ωn aumenta, Te reduz — controle acima da base

`ref_list` permite sobrepor sep_motor vs shunt_motor vs series_motor — uso pedagógico central, idêntico ao MIT.

---

## 3. Arquitetura de Arquivos

### Novos — core

```
core/dc_machine_model.py   DCMachineParams + _make_rhs_dc() (5 excitações)
core/dc_solver.py          run_simulation_dc() — LSODA, max_step=1e-4
core/dc_sources.py         make_voltage_fn_dc() — 6 modos
core/dc_estimator.py       estimate_dc_nameplate() + estimate_dc_tests()
```

### Novos — UI e visualização

```
ui_components/sim_config_dc.py    render_dc_machine_params() + render_experiment_config_dc()
ui_components/sim_runner_dc.py    execute_simulation_flow_dc()
ui_components/sim_results_dc.py   render_results_dc() — 4 sub-abas, KPIs DC
viz/plotly_charts_dc.py           build_fig_*_dc() — stacked, sidebyside, overlay, torque_speed
viz/eqcircuit_plotter_dc.py       _render_circuit_dc() — st.image(PNG por excitação)
viz/pdf_dc.py                     generate_pdf_dc() — relatório PDF DC
ui/theory_dc.py                   render_theory_dc_tab() — 7 subabas exclusivas MCC
ui/theory_dc_interactive.py       componentes interativos (curvas T×ωn, ia(t), estimador)
```

### Modificados

```
IWS_UI.py                    branch DC no roteamento; session_state defaults DC; tabs condicionais
ui_components/sim_config.py  MACHINES list: adicionar entrada "dc" (disabled: False)
```

### Não modificados (reutilizados direto)

```
IWS_UI.py:159–181                       botões Salvar/Limpar referência — machine-agnostic
ui_components/sim_results.py:218–260    render_ref_panel() — machine-agnostic
viz/plotly_charts.py                    _plot_theme(), _colors(), _PLOT_CFG_F — importados pelo DC
```

---

## 4. Esquema UI (MCC = MIT exato)

### Layout da aba Simulação

```
+---------------------------------------------------------+
|  [dark mode]  [experiment lock]  [decimals]             |  IWS_UI.py:126
|  ct1(1.2)     ct2(1.8)           ct3(1.2)   _(6)        |
+---------------------------------------------------------+
+------------------------+--------------------------------+
|  col_params (1)        |  col_circuit (1)              |  IWS_UI.py:139
|                        |                               |  gap="large"
|  .slabel               |  .slabel                      |
|  Parametros Fisicos    |  Circuito Equivalente         |
|                        |                               |
|  [radio: Manual /      |  _render_circuit_dc(mp, dark) |
|   Placa / Ensaios]     |  → st.image(PNG por excitacao)|
|                        |                               |
|  [inputs condicionais] |  .slabel                      |
|  .pgroup por grupo     |  Experimento                  |
|                        |                               |
|                        |  [selectbox modo]             |
|                        |  .pgroup "Parametros"         |
|                        |  [inputs condicionais]        |
|                        |  .ibox com resumo             |
+------------------------+--------------------------------+
+---------------------------------------------------------+
|  [Executar Simulacao]  (full width)                     |  IWS_UI.py:151
+---------------------------------------------------------+
+--------------------------+------------------------------+
|  [Salvar como Referencia]|  [Limpar Referencias]       |  IWS_UI.py:161 — sem modificacao
+--------------------------+------------------------------+
+---------------------------------------------------------+
|  render_results_dc()                                    |  IWS_UI.py:200
|  +----------+----------+--------------+--------------+  |
|  |Visao     |Analise   |Diagnostico   |Gestao de     |  |
|  |Geral     |Dinamica  |e Falhas      |Ativos        |  |
|  +----------+----------+--------------+--------------+  |
+---------------------------------------------------------+
```

### Abas principais — condicionais por máquina

```python
# IWS_UI.py
if selected_machine == "dc":
    tab_sim, tab_teoria_dc = st.tabs(["Simulação", "Teoria MCC"])
else:
    tab_sim, tab_teoria, tab_clean = st.tabs(["Simulação", "Teoria", "Visualização para Artigo"])
```

DC não expõe "Visualização para Artigo" (MIT-only).

### CSS classes — obrigatórias (`ui/theme.py`)

| Classe | Uso | Linhas |
|--------|-----|--------|
| `.slabel` | Label de seção (uppercase, accent) | 127–131 |
| `.pgroup` | Container de grupo de parâmetros | 134–150 |
| `.pgroup-title` | Título do grupo (muted) | 143–150 |
| `.ibox` | Caixa informativa (borda accent) | 153–162 |
| `[data-testid="stMetric"]` | Card de métrica flat | 165–180 |
| `[data-baseweb="tab"]` | Estilo das abas | 237–253 |

### Helpers HTML — reutilizar sem modificação

```python
st.markdown('<p class="slabel">Título</p>', unsafe_allow_html=True)
st.markdown('<div class="pgroup-title">Grupo</div>', unsafe_allow_html=True)
st.markdown('<div class="ibox"><strong>K:</strong> V</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Label", "Valor")
```

---

## 5. Spec por Componente

### 5.1 `IWS_UI.py` — modificações

**Session state — defaults DC + reset na troca de máquina:**

```python
# IWS_UI.py:59 — adicionar junto aos defaults MIT
_DC_DEFAULTS = {
    "wi_dc_Va": 220.0, "wi_dc_Ra": 1.0, "wi_dc_La": 0.05,
    "wi_dc_Rf": 150.0, "wi_dc_Lf": 10.0, "wi_dc_kb": 1.2,
    "wi_dc_J": 0.05,   "wi_dc_B": 0.01,
    "wi_dc_excitation": "sep_motor",
}
for k, v in _DC_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# em render_machine_selector() — reset ao trocar máquina
if st.session_state.get("_prev_machine") != selected_machine:
    st.session_state["sim_result"] = None
    st.session_state["ref_list"]   = []
    st.session_state["_prev_machine"] = selected_machine
```

**Roteamento no tab_sim:**

```python
if selected_machine == "dc":
    with col_params:
        mp_dc, ref_code = render_dc_machine_params(dark, experiment_mode)
    with col_circuit:
        _render_circuit_dc(mp_dc, dark)   # viz/eqcircuit_plotter_dc.py
        exp_config, var_keys, var_labels, tmax, h = render_experiment_config_dc(mp_dc, _WK_DC)
    # botões run + referência — IWS_UI.py:151–186 sem modificação
    execute_simulation_flow_dc(mp_dc, exp_config, var_keys, var_labels, tmax, h, ref_code, dark)
    if sr := st.session_state.get("sim_result"):
        render_results_dc(**sr, decimals=decimals, ref_list=ref_list)
else:
    # MIT — código existente inalterado
```

**PDF — branch por máquina (botões existentes mantidos):**

```python
if selected_machine == "dc":
    pdf_bytes = generate_pdf_dc(sr, mp_dc, ...)
else:
    pdf_bytes = generate_pdf_academico(sr, mp, ...)
```

### 5.2 `core/dc_machine_model.py`

```python
@dataclass
class DCMachineParams:
    # Elétricos armadura
    Va: float; Ra: float; La: float
    # Campo (sep/shunt — não usado em series_motor)
    Vf: float; Rf: float; Lf: float
    # Carga (geradores)
    Rl: float = 0.0; Ll: float = 0.0
    # Mecânicos
    J: float; B: float
    # Constante eletromecânica
    kb: float
    # Configuração
    excitation: str  # sep_motor | sep_gen | shunt_motor | shunt_gen | series_motor
    # __post_init__: shunt força Vf = Va; series combina Ra+Rf, La+Lf internamente
```

`_make_rhs_dc(params, voltage_fn, torque_fn) → rhs(t, y)`
- Estados: `[ia, ifd, wm]` (3 estados; series: ifd = ia)
- ODEs por excitação — fonte: arquivos Scilab listados na seção 2

### 5.3 `core/dc_solver.py`

`run_simulation_dc(params, tmax, h, voltage_fn, torque_fn) → dict`
- `solve_ivp(..., method="LSODA", max_step=1e-4)`
- IC: `[0.0, 0.0, 0.0]`
- Post-proc obrigatório (para compatibilidade com `render_ref_panel`):
  `Ea, Te, n (RPM), Vt, t, ia, ifd, wm, Tl`
- **`Te` e `n` obrigatórios no dict** — render_ref_panel usa essas chaves
- Steady-state: média dos últimos 10% do vetor temporal

### 5.4 `core/dc_sources.py`

`make_voltage_fn_dc(mode, params, exp_config) → callable(t) → (Va, Vf)`:

| `exp_type` | Comportamento |
|-----------|--------------|
| `dol_dc` | step Va em t=0, Vf constante |
| `resistencia_dc` | R_serie decresce de R_ini→0 em t_rampa |
| `plugging_dc` | Va inverte sinal em t_freia |
| `campo_fraco_dc` | Vf reduz de Vf_base→Vf_fraco em t_campo |
| `pulso_dc` | Va constante; torque_fn aplica degrau |
| `gerador_dc` | Va=0; tração mecânica por torque_fn |

### 5.5 `ui_components/sim_config_dc.py`

**Seletor de parâmetros** (col_params) — 3 fontes, radio idêntico ao MIT:
- **Manual:** inputs diretos Va, Ra, La, Rf, Lf, kb, J, B + selectbox excitação
- **Placa:** Pn_kW, Vn, nn_rpm, η → chama `estimate_dc_nameplate()`
- **Ensaios:** V_dc, I_dc (→Ra) + V_nl, I_nl, wm_nl, If_nl (→kb)

**Campos condicionais por excitação:**
- `Vf`, `Rf`, `Lf` → só em `sep_*` (shunt força Vf=Va internamente)
- `Rl`, `Ll` → só em geradores

**Presets DC** (botão "Carregar", mesmo padrão `sim_config.py:485`):

| Preset | Excitação | Parâmetros-base |
|--------|-----------|----------------|
| Motor Separado (dcmei) | sep_motor | `dcmei.sce` |
| Motor Shunt (dcmp) | shunt_motor | `dcmp.sce` |
| Motor Série (dcms) | series_motor | `dcms.sce` |
| Gerador Separado (dgmei) | sep_gen | `dgmei.sce` |
| Gerador Shunt (dcgp) | shunt_gen | `dcgp.sce` |

**`render_experiment_config_dc(mp, _WK_DC)`** — retorna `(config, var_keys, var_labels, tmax, h)` — mesma assinatura MIT.

**Experiment mode lock** — quando ativo, exibe métricas travadas (mesmo padrão `sim_config.py:415–478`).

### 5.6 `ui_components/sim_runner_dc.py`

`execute_simulation_flow_dc(mp, exp_config, var_keys, var_labels, tmax, h, ref_code, dark)`:
- Valida entradas; exibe spinner
- Chama `make_voltage_fn_dc()` + `run_simulation_dc()`
- Escreve `st.session_state["sim_result"]` com **exatamente as mesmas chaves** do MIT:
  `{res, var_keys, var_labels, dark, t_events, mp, exp_label, exp_type, energy_tariff, exp_config, torque_fn}`

### 5.7 `ui_components/sim_results_dc.py`

**4 sub-abas — mesmos nomes:**

```python
tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs([
    "Visão Geral", "Análise Dinâmica", "Diagnóstico e Falhas", "Gestão de Ativos"
])
```

**Visão Geral** — health panel + grade de KPIs + expander transitório + resumo econômico:

| KPI MIT | KPI MCC |
|---------|---------|
| ωr (rad/s) | n_ss (RPM) |
| Te (N·m) | Te_ss (N·m) |
| is (A) | ia_ss (A) |
| — | ifd_ss (A) |
| — | Ea_ss (V) |

**Análise Dinâmica** — seletor de visualização + gráficos Plotly:
```python
_cc1, _cc2, _cc3 = st.columns([2, 2, 1])
modo      = st.radio("Visualização", _viz_opts, key="plot_mode_dc")   # sufixo _dc
zoom_mode = st.radio("Zoom", _zoom_opts, key="zoom_mode_dc")
dark_plot = st.toggle("Fundo escuro", key="plot_dark_dc")
```

**Diagnóstico e Falhas** — conteúdo DC (não reutiliza MCSA/FFT MIT):
- Análise de ripple de ia (FFT de corrente de armadura)
- Verificação de comutação — pico ia_partida vs limite térmico
- Estado da excitação — ifd estável? (deriva = falha de campo)
- Tabela de anomalias: sobrecorrente, subexcitação, regime não atingido

**Gestão de Ativos** — métricas DC (não reutiliza THD/FP MIT):
- Eficiência: `η = Pmec / (Va·ia)` ou inverso (gerador)
- Perdas: `P_Ra = ia²·Ra`, `P_Rf = ifd²·Rf`, `P_mec = B·wm²`
- Fator de utilização: `Te_ss / Te_nominal`
- Layout idêntico (métricas + Sankey adaptado)

**Cache layer** (espelha `sim_results.py:28–56`):
```python
@st.cache_data(show_spinner=False)
def _cached_fig_stacked_dc(..., _cache_key): ...

@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed_dc(..., _cache_key): ...
```

### 5.8 `viz/plotly_charts_dc.py`

| Função | Retorno | Espelha |
|--------|---------|---------|
| `build_fig_stacked_dc(res, var_keys, var_labels, dark, t_events, decimals, tl_arr)` | `go.Figure` | `build_fig_stacked` |
| `build_fig_sidebyside_dc(res, var_keys, var_labels, dark, t_events, decimals, ref_list, primary_color, compact, tl_arr)` | `list[go.Figure]` | `build_fig_sidebyside` |
| `build_fig_overlay_dc(res, var_keys, var_labels, dark, t_events, decimals, ref_list, primary_color, compact, tl_arr)` | `go.Figure` | `build_fig_overlay` |
| `build_fig_torque_speed_dc(res, mp, dark)` | `go.Figure` | `build_fig_torque_speed` |

**Tema** — importar direto do MIT:
```python
from viz.plotly_charts import _plot_theme, _colors, _PLOT_CFG_F
```

**Ref list overlay** — padrão `plotly_charts.py:105–115`:
```python
for ref_item in (ref_list or []):
    res_ref = ref_item.get("res")
    if res_ref is not None and key in res_ref:
        fig.add_trace(go.Scatter(x=res_ref["t"], y=res_ref[key],
                                 line=dict(color=ref_item["color"], dash=ref_item["dash"]),
                                 name=ref_item["label"]))
```

**TL overlay** — mesmo amber MIT:
```python
_TL_COLOR = "#f59e0b"   # plotly_charts.py:33
if key == "Te" and tl_arr is not None:
    fig.add_trace(go.Scatter(x=t, y=tl_arr, name="TL (N·m)",
                             line=dict(color=_TL_COLOR, dash="dash")))
```

**`build_fig_torque_speed_dc`** — curva analítica por excitação + trajetória simulada:
- Série: T∝ωn² hiperbólica — `Te = kb²·Va / (Ra·(wm + kb²/Ra)²)`
- Shunt/Sep: linear — `Te = (Va/kb − wm)·Ra_equiv`
- Trajetória dinâmica sobreposta (linha fina)
- Ponto SS marcado (estrela)
- Overlay `ref_list` — comparar excitações na mesma figura

**`st.plotly_chart`:**
```python
st.plotly_chart(fig, width="stretch", config=_PLOT_CFG_F, key="dc-...")
```

### 5.9 `viz/eqcircuit_plotter_dc.py`

```python
_PNG_MAP = {
    "sep_motor":    "separate_motor.png",
    "sep_gen":      "separate_gerador.png",
    "shunt_motor":  "shunt_motor.png",
    "shunt_gen":    "shunt_gerador.png",
    "series_motor": "serie_motor.png",
}
_PNG_DIR = Path("docs/bases para simulação/cc")

@st.cache_data(show_spinner=False)
def _render_circuit_dc(excitation: str, dark: bool) -> None:
    png = _PNG_DIR / _PNG_MAP[excitation]
    st.image(str(png), use_container_width=True)
```

Cache por `(excitation,)` — PNG estático, não depende de parâmetros numéricos.

### 5.10 Aba Teoria MCC — `ui/theory_dc.py`

7 subabas (espelha estrutura `ui/theory.py:2079`):

| Nº | Título | PNGs | Componente interativo |
|----|--------|------|-----------------------|
| 1 | Modelagem e Circuitos | `separate_motor.png`, `shunt_motor.png`, `serie_motor.png`, `separate_gerador.png`, `shunt_gerador.png` | `render_diagrama_blocos_mcc()` |
| 2 | Dinâmica e Torque ★ | `wm_x_T.png` | `render_curvas_comparativas_excitacao()` |
| 3 | Padrões de Corrente ★ | — | `render_padrao_corrente_dc()` |
| 4 | Controle de Velocidade | — | `render_controle_velocidade_dc()` |
| 5 | Operação como Gerador | `gerador_comparativo.png` | — |
| 6 | Estimador de Parâmetros | `curva_magnetizacao_simples_pb.png` | `render_estimador_dc()` |
| 7 | Manual de Uso | — | — |

★ Subabas 2 e 3 = núcleo pedagógico.

### 5.11 `ui/theory_dc_interactive.py`

| Função | Subaba | Descrição |
|--------|--------|-----------|
| `render_curvas_comparativas_excitacao()` | 2 | Plotly T×ωn das 3 excitações — sliders Va, Ra |
| `render_padrao_corrente_dc()` | 3 | Radio excitação → simula on-the-fly → gráfico ia(t) |
| `render_controle_velocidade_dc()` | 4 | Slider Vf → curva T×ωn atualizada |
| `render_estimador_dc()` | 6 | Formulário ensaios → Ra, kb passo a passo |
| `render_diagrama_blocos_mcc()` | 1 | Diagrama de blocos do modelo de estado |

---

## 6. Circuitos Equivalentes Disponíveis

Notebook `docs/bases para simulação/cc/MCC_Desenhos.ipynb` — gerado via schemdraw em `mcc_desenhos.py`:

| PNG | Configuração | Usado em |
|-----|-------------|----------|
| `separate_motor.png` | Excitação separada — motor | Simulação (col_circuit) + Teoria sub 1 |
| `separate_gerador.png` | Excitação separada — gerador | Simulação + Teoria sub 1 |
| `shunt_motor.png` | Shunt — motor | Simulação + Teoria sub 1 |
| `shunt_gerador.png` | Shunt — gerador | Simulação + Teoria sub 1 |
| `serie_motor.png` | Série — motor | Simulação + Teoria sub 1 |
| `wm_x_T.png` | Curvas T×ωn (4 excitações) | Teoria sub 2 |
| `curva_magnetizacao_simples_pb.png` | Curva de magnetização | Teoria sub 6 |
| `gerador_comparativo.png` | Vt×Ia externas comparativas | Teoria sub 5 |
| `serie_gerador.png` | Série — gerador | Fora escopo v1 |
| `long_motor.png`, `long_gerador.png` | Compound longa | Fora escopo v1 |
| `short_motor.png`, `short_gerador.png` | Compound curta | Fora escopo v1 |

---

## 7. Notas Técnicas

- **Integrador:** `max_step = 1e-4 s` — La/Ra ≈ 0.77 ms (muito menor que MIT)
- **Shunt gerador:** transformação x1, x2 de `dcgp.sce` preservada — evita singularidade (Leq = Lla·Llf − Ll²)
- **Série motor:** ifd = ia — sem widgets Vf/Rf separados; Rf+Ra e Lf+La combinados internamente em `__post_init__`
- **kb único:** back-EMF constant = torque constant em SI
- **Widget namespace:** prefixo `wi_dc_*` — sem colisão com MIT no session_state
- **Keys Plotly:** sufixo `_dc` em todos os `key=` de widgets na aba DC
- **render_ref_panel:** machine-agnostic, mas requer `res["Te"]` e `res["n"]` — `dc_solver.py` garante essas chaves
- **Compound:** desenhos existem, fora de escopo v1

---

## 8. Sequência de Implementação

### Fase 1 — Core (sem UI)
1. `core/dc_machine_model.py` — DCMachineParams + ODEs 5 excitações
2. `core/dc_solver.py` — integrador LSODA + post-proc (garantir chaves `Te`, `n`)
3. `core/dc_sources.py` — funções tensão/torque por modo
4. **Validação:** DOL sep_motor → ia_ss ≈ 192 A, wm_ss ≈ 2.49 rad/s, Te_ss ≈ 2.49 N·m (ref: `dcmei.sce`)

### Fase 2 — UI básica uniforme
5. `ui_components/sim_config_dc.py` — render_dc_machine_params + render_experiment_config_dc + presets
6. `ui_components/sim_runner_dc.py` — execute_simulation_flow_dc
7. `ui_components/sim_results_dc.py` — 4 sub-abas, KPIs, cache layer
8. `ui_components/sim_config.py:250` — habilitar `"dc"` em MACHINES
9. `IWS_UI.py` — session_state DC defaults; reset na troca; roteamento branch DC; tabs condicionais
10. **Teste:** sep_motor DOL → salvar ref → series_motor → sobrepor curvas ia(t)

### Fase 3 — Visualização
11. `viz/eqcircuit_plotter_dc.py` — _render_circuit_dc (PNG por excitação)
12. `viz/plotly_charts_dc.py` — build_fig_stacked/sidebyside/overlay/torque_speed_dc
13. Integrar cache layer no sim_results_dc.py (_cached_fig_* DC)
14. `viz/pdf_dc.py` — generate_pdf_dc + branch em IWS_UI.py

### Fase 4 — Aba Teoria MCC
15. `ui/theory_dc.py` — 7 subabas, PNGs por subaba
16. `ui/theory_dc_interactive.py` — 5 componentes interativos
17. `IWS_UI.py` — rotear aba "Teoria MCC" quando `selected_machine == "dc"`

### Fase 5 — Estimador DC
18. `core/dc_estimator.py` — estimate_dc_nameplate + estimate_dc_tests
19. Integrar em sim_config_dc.py (fontes "Placa" e "Ensaios") e theory_dc.py subaba 6

---

## 9. Verificação Final

- Selecionar MCC → "Separada — Motor" → DOL → simular → ia_ss ≈ 192 A, wm_ss ≈ 2.49 rad/s, Te_ss ≈ 2.49 N·m
- Salvar ref → "Série — Motor" → simular → sobrepor: ia(t) série com pico maior
- Gerador shunt: Vt positivo, ia negativo
- Campo fraco: wm_ss > wm_base, Te_ss < Te_base
- Trocar para MIT → sim_result e ref_list zerados automaticamente
- Layout 4 sub-abas idêntico ao MIT (mesmos nomes, mesma ordem)
- Circuito equivalente muda conforme excitação selecionada
- Aba "Teoria MCC" visível só com DC; "Teoria" e "Visualização para Artigo" só com MIT
- PDF gerado via `generate_pdf_dc()` sem erro

---

## 10. Referências de Código

| Arquivo | Relevância |
|---------|-----------|
| `docs/bases para simulação/cc/dcmei.sce` | ODEs sep_motor — fonte primária |
| `docs/bases para simulação/cc/dgmei.sce` | ODEs sep_gen |
| `docs/bases para simulação/cc/dcmp.sce` | ODEs shunt_motor |
| `docs/bases para simulação/cc/dcgp.sce` | ODEs shunt_gen (x1, x2) |
| `docs/bases para simulação/cc/dcms.sce` | ODEs series_motor |
| `docs/bases para simulação/cc/MCC_Desenhos.ipynb` | PNGs circuitos + curvas |
| `docs/bases para simulação/cc/mcc_desenhos.py` | Script exportação PNGs |
| `core/machine_model.py:183` | Padrão `_make_rhs` a replicar |
| `core/IWS_PY.py:39` | Padrão `run_simulation` a replicar |
| `ui_components/sim_config.py:250` | MACHINES list |
| `ui_components/sim_config.py:393–1158` | render_machine_params — padrão UI |
| `ui_components/sim_config.py:1165–1501` | render_experiment_config — padrão |
| `ui_components/sim_config.py:415–478` | experiment mode lock — padrão |
| `ui_components/sim_config.py:485` | preset selector — padrão |
| `ui_components/sim_runner.py:41–100` | execute_simulation_flow — padrão |
| `ui_components/sim_results.py:28–56` | cache layer — padrão |
| `ui_components/sim_results.py:337–339` | 4 sub-abas — padrão |
| `ui_components/sim_results.py:590–599` | seletor visualização — padrão |
| `ui_components/sim_results.py:218–260` | render_ref_panel — não modificar |
| `viz/plotly_charts.py:15–30` | _plot_theme — importar direto |
| `viz/plotly_charts.py:33` | _TL_COLOR amber — importar direto |
| `viz/plotly_charts.py:105–115` | ref_list overlay loop — replicar |
| `ui/theory.py:2079` | render_theory_tab — estrutura a espelhar |
| `IWS_UI.py:59` | session_state defaults — adicionar DC |
| `IWS_UI.py:126` | controles globais (dark/lock/decimals) |
| `IWS_UI.py:139` | col_params + col_circuit — sem modificar proporções |
| `IWS_UI.py:159–181` | botões referência — não modificar |
