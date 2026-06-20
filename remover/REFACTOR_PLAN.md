# Plano: Simplificações, Otimizações e Modularizações — IWS-English

## Context

Mapeamento completo do codebase (100 arquivos, ~16.000 LOC) revelou arquitetura geral limpa (sem imports circulares, caching estratégico, separação MIT/DC), mas com duplicação real, constantes espalhadas, arquivos monolíticos e lógica de negócio deslocada. Este plano consolida todos os achados em intervenções priorizadas por impacto vs risco.

---

## Inventário Estrutural

| Camada | LOC | % | Arquivos críticos (>600 LOC) |
|---|---|---|---|
| Core (física) | ~4.500 | 28% | `diagnostics.py` 700, `param_estimator.py` 470, `solver.py` 398 |
| UI (Streamlit) | ~7.800 | 49% | `tim_config.py` 1609, `sim_config_dc.py` 1249, `tim_results.py` 993 |
| Viz (PDF+Plotly) | ~3.700 | 23% | `tim_pdf_dashboard.py` 1223, `tim_pdf_report.py` 1061, `pdf_dc.py` 643 |

---

## Achados por Categoria

### A. CONSTANTES MÁGICAS ESPALHADAS (~40 locais)

Raiz: `core/constants.py` centraliza bem as thresholds de diagnóstico, mas faltam constantes físicas e de estimação.

**Faltando em `core/constants.py`:**

| Constante | Valor | Onde ocorre |
|---|---|---|
| `RAD_TO_RPM` | `60/(2π)` | `facade.py:110`, `diagnostics.py:127,469`, `tim_charts.py:301`, `dc/solver.py:90` |
| `RPM_TO_RAD` | `2π/60` | `dc/estimator.py:48,141` |
| `N_SYNC_FACTOR` | `120.0` | `machine_model.py:139`, `param_estimator.py:97`, `tim_charts.py:299` |
| `AMPLITUDE_INVARIANT` | `1.5` (3/2) | `machine_model.py:252`, `facade.py:108`, `energy_analysis.py` |
| `NEMA_B_XLS_FRAC` | `0.4` | `param_estimator.py:139` |
| `NEMA_B_XLR_FRAC` | `0.6` | `param_estimator.py:140` |
| `NEMA_B_COS_PHI_P` | `0.20` | `param_estimator.py:136` |
| `NEMA_CORE_LOSS_FRAC` | `0.20` | `param_estimator.py:160` |
| `NEMA_MASS_PER_KW` | `15.0` | `param_estimator.py:167` |
| `STEEL_SPECIFIC_HEAT` | `460.0` | `param_estimator.py:168` |
| `FFT_WINDOW_LOW` | `0.5` | `energy_analysis.py:81`, `harmonic_analysis.py` |
| `FFT_WINDOW_HIGH` | `1.5` | ambos acima |
| `SHUTDOWN_THRESHOLD` | `0.01` | `dc/solver.py` implícito; `constants.py:127` define mas não é usado |
| `J_PER_KWH` | `3_600_000` | `constants.py` já tem; `pdf_report.py:38` usa inline |
| `HOURS_PER_YEAR` | `8760` | `constants.py` já tem; `pdf_report.py:42` usa inline |

**Ação:** Adicionar ao `core/constants.py` e substituir literais inline por imports. Custo: ~40 substituições em ~8 arquivos.

---

### B. DUPLICAÇÃO ENTRE MIT E DC

#### B1. Widgets helpers idênticos (4 linhas)
- `ui_components/tim_config.py:173,177` — `_pgroup()`, `_ibox()`
- `ui_components/sim_config_dc.py:137,141` — idênticas
- **Ação:** Extrair para `ui_components/_shared_widgets.py`

#### B2. Gráficos Plotly espelhados (~200 LOC)
Funções em `viz/tim_charts.py` vs `viz/plotly_charts_dc.py`:

| Par MIT/DC | Similaridade | Diferença real |
|---|---|---|
| `build_fig_stacked` / `build_fig_stacked_dc` | 95% | `decimals=2` vs `3`; label `TL` vs `$T_l$`; DC adiciona guard `if key not in res` |
| `build_fig_sidebyside` / `build_fig_sidebyside_dc` | 90% | MIT: `showlegend=key == "Te"`, DC: `showlegend=True` |
| `build_fig_overlay` / `build_fig_overlay_dc` | 85% | MIT: dual-axis para `n/wr`; DC: sem dual-axis |

DC já importa `_plot_theme`, `_colors`, `_TL_COLOR` de `tim_charts` — base parcialmente compartilhada.

**Ação:** Criar `viz/_chart_base.py` com versões parametrizadas. MIT e DC viram wrappers que passam `traces` e `layout_overrides`. Risco médio — exige teste visual.

#### B3. FFT duplicada (energy_analysis vs harmonic_analysis)
- `core/tim/energy_analysis.py:77–88` — FFT para THD
- `core/tim/harmonic_analysis.py:78–82` — FFT com lógica diferente (threshold `freq > 1.0` vs `0.5*f_fund`)
- **Ação:** Centralizar em `core/tim/fft_utils.py` com parâmetros explícitos (freq_min, freq_max). Importar nos dois módulos.

#### B4. Cálculos físicos duplicados em ui/theory/
- `_torque_ref()` em `ui/theory/tabs/_shared.py:64` — hardcoda parâmetros `V1_REF=220, R1_REF=0.5, ...` sem usar `MachineParams` ativo
- Cálculo de `Z2 = R2/s + jX2` repetido em `transitorios.py:94`, `comparativo_partidas.py:36`, `_shared.py:68`
- Thevenin inline em `boucherot.py:40–45`
- **Ação curto prazo:** Centralizar em `_shared.py` com funções nomeadas `_z2(R2, s, X2)`, `_thevenin(Vf, Zs, Xm)`. Não requer MachineParams.
- **Ação médio prazo:** `_torque_ref()` aceitar `mp: MachineParams | None` com fallback para hardcoded.

---

### C. ARQUIVOS MONOLÍTICOS (SPLIT)

#### C1. `ui_components/tim_results.py` [993 LOC] → 4 módulos
Cada sub-tab tem ~200–300 LOC com responsabilidade única.

```
ui_components/tim_results.py              # orquestrador: importa e chama render de cada tab (~80 LOC)
ui_components/tim_results_overview.py     # Tab 1: KPIs, health panel (~200 LOC)
ui_components/tim_results_dynamics.py     # Tab 2: waveforms Plotly, @st.cache_data (~300 LOC)
ui_components/tim_results_diagnostics.py  # Tab 3: auto-diagnóstico, signature tables (~200 LOC)
ui_components/tim_results_asset.py        # Tab 4: efficiency, losses, lifetime (~150 LOC)
```

#### C2. `ui_components/tim_config.py` [1609 LOC] → 3 módulos
Sub-renderers de experimento são 9 funções de 40–200 LOC inline (linhas 1200–1462).

```
ui_components/tim_config.py               # orquestrador + seletor + _WidgetKeys (~400 LOC)
ui_components/tim_config_params.py        # nameplate, IEEE, manual panels (~400 LOC)
ui_components/exp_renderers_tim.py        # 9 _render_exp_* functions (~400 LOC)
```

O dispatch table `_EXP_RENDERERS` (já existe em `tim_config.py:1496`) permanece; apenas as funções referenciadas migram.

#### C3. `core/tim/diagnostics.py` [700 LOC]
11 funções internas de 18–74 LOC. Não requer split em arquivos — apenas extrair de closures para funções de módulo nomeadas. Reduz complexidade ciclomática sem fragmentar API pública.

---

### D. LÓGICA DE NEGÓCIO DESLOCADA

#### D1. `IWS_UI.py` — preset loading e machine switch
- **Linhas 95–109:** Preset auto-load do motor Krause — hardcoded por nome (`"Default — Krause 3 HP..."`) — lógica MIT-específica no orquestrador global
- **Linhas 87–93:** Machine switch reset — compara `_prev_machine` vs `selected_machine` inline

**Ação:**
1. Mover preset loading para `ui_components/tim_config.py::_init_default_preset()`, chamado pelo config renderer
2. Criar `_on_machine_switch(prev, cur)` em `IWS_UI.py` — encapsula resets (1 função, 4 linhas)

#### D2. `core/dc/solver.py` — step clamping ausente
- MIT: `max_step = 1.0 / (SOLVER_MAX_STEP_FACTOR * mp.f)` — correto
- DC: `max_step=1e-4` hardcoded — sem dependência de frequência (irrelevante para DC puro, mas inconsistente)
- `DC_STEADY_STATE_CONV_THRESHOLD` definido em `constants.py:127` mas **não usado** no solver DC
- **Ação:** Aplicar threshold de convergência em `dc/solver.py` via `constants.DC_STEADY_STATE_CONV_THRESHOLD`

---

### E. CORES HARDCODED FORA DE `ui/theme.py`

~25 violações identificadas:

| Arquivo | Linhas | Cores |
|---|---|---|
| `ui/clean_view.py` | 26–215 | ~15 cores em tabelas HTML inline |
| `ui/theory/sankey_potencia.py` | 47–52 | 6 cores de fluxo energético |
| `ui_components/tim_results.py` | 227, 723 | `#dc3545`, `#fd7e14`, `#198754`, `#f59e0b` |
| `ui/theory/fasorial.py` | 43–49 | 7 variáveis de cor local |
| `ui/theory/park_dinamico.py` | 30–35 | 6 variáveis de cor local |
| `ui/theory/frenagem.py` | 51–53 | 3 cores de método |
| `ui/theory/mcsa.py` | 82–84 | 3 cores de espectro |
| `ui/theory/boucherot.py` | 63–65 | 3 cores de curva |

**Ação:** Ampliar `_palette()` em `ui/theme.py` com chaves semânticas:
```python
"danger": "#dc3545", "warning": "#fd7e14", "success": "#198754",
"energy_in": ..., "energy_cu": ..., "energy_fe": ..., "energy_mec": ...,
"phase_a": ..., "phase_b": ..., "phase_c": ...,
"brake_reg": ..., "brake_plug": ..., "brake_dc": ...,
```
Migrar referências. Risco baixo para tim_results; médio para theory (paletas locais têm contexto semântico próprio).

---

### F. CACHE AUSENTE EM THEORY (PERFORMANCE)

3 renderizadores sem `@st.cache_data` que recomputam a cada rerun:

| Arquivo | Função | Custo estimado |
|---|---|---|
| `ui/theory/transitorios.py` | `render_transitorios_sincronizados()` — 3 cenários × 3 traces de updatemenus | médio |
| `ui/theory/zonas_operacao.py` | `render_zonas_operacao()` — T×n 3 regiões | baixo |
| `ui/theory/fasorial.py` | HTML iframe com JS `Math.sin` | baixo (JS roda no browser) |

**Ação:** Envolver computação de `transitorios` e `zonas_operacao` em funções `@st.cache_data` separadas da renderização Streamlit.

---

### G. ARQUIVOS LEGADOS / OBSOLETOS

| Arquivo | Status | Ação |
|---|---|---|
| `viz/eqcircuit_plotter_dc.py` [220 LOC] | v1 supersedido por `v2` [332 LOC] | Verificar grep; deletar se sem import ativo |
| `viz/tim_pdf_report.py` [1061 LOC] | Docstring: "Legacy — superseded by pdf_academico + pdf_industrial" | Manter por compatibilidade ou deprecar com aviso |
| `viz/tim_pdf_dashboard.py` [1223 LOC] | Transicional — preferir módulos dedicados | Idem |

---

### H. SESSION STATE — SCHEMA AUSENTE

26 chaves `st.session_state` dispersas, sem TypedDict ou validação central.

**Inconsistências identificadas:**
- `sim_result` (MIT) vs possível `dc_sim_result` — nomes confirmados apenas em parte dos arquivos
- Flags de reset dispersas: `_dc_reset_preset`, `_reset_preset_select`, `_preset_loaded`

**Ação:** Criar `core/session_schema.py` com TypedDict documentando todas as 26 chaves e seus defaults. `IWS_UI.py` usa `MIT_SESSION_DEFAULTS` e `DC_SESSION_DEFAULTS` (já existem em `constants.py`) — apenas adicionar type hints.

---

## O Que NÃO Tocar

- `viz/pdf_commons.py` — centraliza helpers ReportLab corretamente; nova arquitetura PDF já a usa
- `ui/theme.py` — foco único, bem organizado
- `@st.cache_data` — estratégia atual é correta; não consolidar
- Branching `selected_machine` em `IWS_UI.py` — aceitável no entry point
- `data/experiment_modes.py`, `data/variable_labels.py` — catálogos estáticos sem duplicação
- `viz/pdf_academico.py` + `viz/pdf_industrial.py` — paralelos intencionais (layouts diferentes)

---

## Ordem de Execução Recomendada

| # | Intervenção | Arquivos | Risco | LOC Δ |
|---|---|---|---|---|
| 1 | **Constantes** — `core/constants.py` + 8 arquivos | `constants.py` + callers | mínimo | −40 inline |
| 2 | **Shared widgets** — `_shared_widgets.py` | 2 config files | mínimo | −8 dup |
| 3 | **Deletar eqcircuit v1** | 1 arquivo | mínimo | −220 |
| 4 | **FFT utils** — `core/tim/fft_utils.py` | `energy_analysis`, `harmonic_analysis` | baixo | −60 dup |
| 5 | **Theory helpers** — centralizar `_z2`, `_thevenin` em `_shared.py` | 3 theory files | baixo | −30 dup |
| 6 | **Cache theory** — `transitorios`, `zonas_operacao` | 2 theory files | baixo | 0 LOC |
| 7 | **Lógica IWS_UI** — `_init_default_preset()`, `_on_machine_switch()` | `IWS_UI.py`, `tim_config.py` | baixo | −15 |
| 8 | **Split tim_results** — 4 submódulos | `tim_results.py` → 5 files | médio | 0 LOC |
| 9 | **Split tim_config** — orquestrador + params + exp_renderers | `tim_config.py` → 3 files | médio-alto | 0 LOC |
| 10 | **Chart base** — `viz/_chart_base.py` | `tim_charts.py`, `plotly_charts_dc.py` | médio | −200 dup |
| 11 | **Cores theme** — ampliar `_palette()` | `theme.py` + 8 theory/UI files | baixo | −50 inline |
| 12 | **Session schema** — `core/session_schema.py` | `IWS_UI.py`, `constants.py` | mínimo | doc only |
| 13 | **DC solver convergence** | `dc/solver.py` | baixo | −2 magic |

**Total estimado removido por duplicação/literais:** ~600 LOC  
**Split (redistribuição sem remoção):** ~2.600 LOC reorganizados em submódulos

---

## Verificação

Após cada grupo de intervenções:
```bash
streamlit run IWS_UI.py         # smoke test: MIT + DC, rodar simulação, gerar PDF
pytest tests/ -x               # suite deve passar sem falhas
```

Para #10 (chart base): verificar visualmente gráficos MIT e DC (stacked, overlay, sidebyside) após refactor.
