# Prompt — Nova Conversa: Execução do Plano de Refatoração IWS-English

## Contexto

Mapeamento completo do codebase IWS-English foi concluído. O plano detalhado está em `REFACTOR_PLAN.md` na raiz do projeto. Esta conversa deve executar as intervenções na ordem definida, uma de cada vez, com verificação entre grupos.

## Instruções

Leia `REFACTOR_PLAN.md` antes de qualquer ação. Execute as intervenções na ordem da tabela "Ordem de Execução Recomendada" (#1 ao #13).

Após cada intervenção ou grupo de baixo risco (ex: #1+#2+#3 juntos), rode:
```bash
pytest tests/ -x
streamlit run IWS_UI.py  # smoke test manual: MIT sim + DC sim + gerar PDF
```

Se os testes passarem, avance para a próxima. Se falharem, corrija antes de continuar.

## Intervenções em ordem

### Grupo 1 — Sem risco (executar junto)
- **#1** Adicionar constantes físicas e de estimação em `core/constants.py` e substituir ~40 literais inline nos 8 arquivos callers (ver tabela no plano, seção A)
- **#2** Criar `ui_components/_shared_widgets.py` com `_pgroup()` e `_ibox()`; atualizar imports em `tim_config.py:173,177` e `sim_config_dc.py:137,141`
- **#3** Verificar com grep se `viz/eqcircuit_plotter_dc.py` (v1, 220 LOC) tem algum import ativo; se não, deletar

### Grupo 2 — Baixo risco
- **#4** Criar `core/tim/fft_utils.py` com função FFT centralizada; importar em `energy_analysis.py` e `harmonic_analysis.py` (ver seção B3)
- **#5** Centralizar `_z2(R2, s, X2)` e `_thevenin(Vf, Zs, Xm)` em `ui/theory/tabs/_shared.py`; remover duplicatas de `transitorios.py:94`, `comparativo_partidas.py:36`, `boucherot.py:40`
- **#6** Envolver cálculo de figuras em `transitorios.py` e `zonas_operacao.py` em funções `@st.cache_data` separadas da renderização
- **#7** Mover preset auto-load para `tim_config._init_default_preset()`; criar `_on_machine_switch()` em `IWS_UI.py`

### Grupo 3 — Médio risco (um de cada vez)
- **#8** Split `ui_components/tim_results.py` [993 LOC] em 5 arquivos (ver estrutura no plano, seção C1)
- **#9** Split `ui_components/tim_config.py` [1609 LOC] em 3 arquivos (ver estrutura, seção C2) — mais arriscado, testar com cuidado
- **#10** Criar `viz/_chart_base.py` com funções Plotly parametrizadas; `tim_charts.py` e `plotly_charts_dc.py` viram wrappers (ver seção B2) — verificar visualmente os gráficos

### Grupo 4 — Cosmético / doc
- **#11** Ampliar `_palette()` em `ui/theme.py` com chaves semânticas; migrar ~25 cores hardcoded (ver seção E)
- **#12** Criar `core/session_schema.py` com TypedDict das 26 chaves de session_state (ver seção H)
- **#13** Aplicar `DC_STEADY_STATE_CONV_THRESHOLD` em `dc/solver.py` (ver seção D2)

## O que NÃO tocar
- `viz/pdf_commons.py`, `ui/theme.py`, `viz/pdf_academico.py`, `viz/pdf_industrial.py`
- Estratégia `@st.cache_data` existente
- `data/experiment_modes.py`, `data/variable_labels.py`

## Meta final
~600 LOC removidas por deduplicação + ~2.600 LOC redistribuídas em submódulos menores. Suite de testes deve passar integralmente ao final.
