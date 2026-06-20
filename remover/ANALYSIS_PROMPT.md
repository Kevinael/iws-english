# Prompt — Análise Arquitetural IWS (próxima conversa)

## Objetivo
Analisar toda a codebase IWS e identificar:
1. Otimizações (performance, duplicação, acoplamento)
2. Modularizações necessárias
3. Padrões para facilitar adição de novas máquinas (BLDC, PMSM, etc.)

## Contexto já feito
- Knowledge graph gerado em `.understand-anything/knowledge-graph.json`
- 262 nós, 636 arestas, 8 camadas arquiteturais mapeadas
- Dashboard disponível via `/understand-dashboard`

## Achados já identificados (investigar primeiro)

### Problemas críticos
1. `ui_components/sim_config_dc.py` — 1242 linhas monolíticas. Mesma situação que `tim_config_params.py` tinha antes do split. Candidato imediato para quebrar em submódulos como foi feito com TIM.
2. `utils/_gen_theory_imgs.py` — reimplementa modelo TIM (funções `_torque`, `_torque_dupla`) **independente** de `core/tim/`. Duplicação de física — se `core/tim/machine_model.py` mudar, esse arquivo diverge silenciosamente.
3. `core/tim/fault.py` — módulo de física misturado com blocos Streamlit UI. Viola separação core/ui. Dificulta reutilização em contexto não-Streamlit.
4. `tests/test_dc_phase1_validation.py` — marcado com `pytestmark = pytest.mark.skip`. API obsoleta. Ou reescrever ou deletar.
5. `.devcontainer/devcontainer.json` — referencia `EMS_UI.py` (nome antigo do projeto).

### Padrão TIM vs DCM (assimetria)
- TIM tem: `facade.py` (API pública estável) → `machine_model.py` → `solver.py`
- DCM **não tem facade**. `sim_runner_dc.py` importa `core/dc/machine_model.py` e `core/dc/solver.py` diretamente.
- Para adicionar nova máquina, precisa replicar esse padrão. Falta `core/dc/facade.py`.

### Acoplamento UI ↔ Core
- `ui_components/tim_config_params.py` (961 linhas) ainda acessa `core/tim/param_estimator.py` diretamente sem passar pela facade.
- `ui/theory/tabs/experimentos.py` importa `core/tim/facade.py` diretamente — ok, mas inconsistente com outros tabs que só usam `ui/theory/_shared.py`.

### Visualização
- `viz/_chart_base.py` existe como base compartilhada TIM/DCM — bom padrão.
- Mas `viz/tim_eqcircuit.py` e `viz/eqcircuit_plotter_dc_v2.py` não herdam de `_chart_base.py`. Inconsistência.
- `viz/pdf_commons.py` é base compartilhada de PDF — bom. Mas `viz/pdf_academico.py` e `viz/pdf_industrial.py` coexistem com `viz/tim_pdf_report.py` e `viz/tim_pdf_dashboard.py`. Dois sistemas de naming (prefixo `tim_` vs sem prefixo).

### Para adicionar nova máquina (BLDC/PMSM)
Atualmente precisaria criar:
- `core/bldc/machine_model.py` ✓ (padrão existe)
- `core/bldc/solver.py` ✓
- `core/bldc/sources.py` ✓
- `core/bldc/facade.py` ✗ (DCM não tem, TIM tem — inconsistente)
- `ui_components/bldc_config.py` — sem template claro (DCM é 1 arquivo monolítico de 1242 linhas)
- `ui_components/bldc_runner.py` ✓ (padrão existe)
- `ui_components/bldc_results.py` ✓ (padrão existe, TIM quebrado em 4 sub-tabs)
- `viz/plotly_charts_bldc.py` — herdar de `_chart_base.py`? Às vezes sim, às vezes não.
- `IWS_UI.py` — adicionar branch manualmente (sem registry de máquinas)

**Problema raiz:** não existe um "contrato de máquina" formal. Cada nova máquina é adicionada por imitação, não por interface.

## Perguntas para `/understand-chat`

```
1. "Quais arquivos têm mais de 500 linhas e são candidatos a split?"
2. "Quais funções em core/ são importadas diretamente por ui/ sem passar por uma facade?"
3. "Mostre todos os arquivos que implementam lógica de física (ODE, integradores) fora de core/"
4. "Qual é o caminho completo de uma simulação DCM do clique do botão até o gráfico?"
5. "Quais módulos de viz/ não herdam de _chart_base.py?"
```

## Tarefas de refactoring priorizadas

### Alta prioridade (fazer antes de adicionar máquina nova)
- [ ] Criar `core/dc/facade.py` espelhando `core/tim/facade.py`
- [ ] Quebrar `ui_components/sim_config_dc.py` (1242 linhas) → `sim_config_dc_params.py` + `sim_config_dc_modes.py` + etc.
- [ ] Mover física de `core/tim/fault.py` para módulo puro (sem Streamlit imports)
- [ ] Fazer `utils/_gen_theory_imgs.py` usar `core/tim/torque_speed.py` em vez de reimplementar

### Média prioridade
- [ ] Padronizar naming em `viz/` (prefixo `tim_`/`dc_` em todos ou em nenhum)
- [ ] Criar `MachineRegistry` em `IWS_UI.py` para registrar máquinas sem if/elif cascata
- [ ] Reescrever ou deletar `tests/test_dc_phase1_validation.py`

### Baixa prioridade
- [ ] Corrigir `devcontainer.json` (EMS_UI.py → IWS_UI.py)
- [ ] Fazer `viz/tim_eqcircuit.py` herdar de `_chart_base.py`

## Como iniciar a próxima conversa

1. Abrir nova conversa no projeto `IWS - English`
2. Rodar `/understand-chat` 
3. Fazer as perguntas listadas acima para validar os achados
4. Começar pelas tarefas de alta prioridade na ordem listada
5. Para cada tarefa: usar `cavecrew-investigator` para localizar → `cavecrew-builder` para editar → `cavecrew-reviewer` para auditar
