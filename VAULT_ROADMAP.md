# VAULT_ROADMAP — Ordem de Escrita das Notas
> Sequência didática recomendada. Escrever fora de ordem cria dependências não resolvidas.
> Última atualização: 2026-05-23.

---

## Princípio de Ordenação

Cada nota pode referenciar apenas notas de fases anteriores. Matemática → máquina → backend → frontend → integração → extensão. Nunca pular fases.

---

## Fase F0 — Meta (ancoragem de notação)

Escrever primeiro. Toda fórmula posterior referencia estas convenções.

| # | Nota | Dependência |
|---|------|-------------|
| 1 | `00_Meta/Convencoes.md` | — |
| 2 | `00_Meta/Glossario.md` | Convencoes |
| 3 | `00_Meta/Setup_e_Instalacao.md` | — (dependências, `streamlit run`, venv) |
| 4 | `00_Meta/Roadmap.md` | Glossario |
| 5 | `00_Meta/INDEX.md` | tudo (escrever por último dentro da fase) |

---

## Fase F0.5 — Python Aplicado ← **NOVA — escrever antes dos fundamentos**

Engenheiro que nunca programou orientado a objetos trava aqui. Esta fase remove o bloqueio antes de aparecer qualquer EDO.

| # | Nota | Conceito central | Código IWS que exemplifica |
|---|------|-----------------|---------------------------|
| 6 | `00_Python_Aplicado/NumPy_Vetorizacao.md` | arrays, operações sem loop | `_reconstruct_currents` (solver.py:201) |
| 7 | `00_Python_Aplicado/Typing_Anotacoes.md` | `float \| None`, `Callable` | assinatura de `run_simulation` |
| 8 | `00_Python_Aplicado/Dataclasses_Python.md` | `@dataclass`, `__post_init__` | `MachineParams` (machine_model.py:40) |
| 9 | `00_Python_Aplicado/Closures_e_Factories.md` | função que retorna função | `_make_rhs` (machine_model.py:183) |
| 10 | `00_Python_Aplicado/Scipy_solve_ivp.md` | assinatura `rhs(t,y)→list`, `rtol/atol` | `_solve` (solver.py:51) |

**Ponto de virada:** após nota 10, leitor consegue ler `_solve` e `_make_rhs` sem se perder na sintaxe.

---

## Fase F1 — Fundamentos Matemáticos

| # | Nota | Dependência |
|---|------|-------------|
| 11 | `01_Fundamentos/EDOs_Numericas.md` | Scipy_solve_ivp (F0.5) |
| 12 | `01_Fundamentos/Fasores_e_Regime_Permanente.md` | EDOs_Numericas |
| 13 | `01_Fundamentos/Circuito_Equivalente.md` | Fasores |
| 14 | `01_Fundamentos/Transformacoes_Park_Clarke.md` | Circuito_Equivalente |
| 15 | `01_Fundamentos/Componentes_Simetricas.md` | Fasores |

---

## Fase F2 — Máquina Âncora (MIT)

MIT primeiro: maior cobertura no IWS, todos os exemplos partem daqui.

| # | Nota | Dependência |
|---|------|-------------|
| 16 | `02_Maquinas/MIT/MIT_Visao_Geral.md` | Circuito_Equivalente |
| 17 | `02_Maquinas/MIT/MIT_Parametros.md` | MIT_Visao_Geral |
| 18 | `02_Maquinas/MIT/MIT_Modelo_dq0.md` | MIT_Parametros + Park_Clarke |
| 19 | `02_Maquinas/MIT/MIT_Regime_Permanente.md` | MIT_Modelo_dq0 + Fasores |
| 20 | `02_Maquinas/MIT/MIT_Estimacao_Params.md` | MIT_Parametros + IEEE 112-2017 |

---

## Fase F3 — Backend: Modelagem

Implementação segue o modelo matemático — nunca o contrário.

| # | Nota | Conceito central | Código IWS |
|---|------|-----------------|------------|
| 21 | `03_Backend/MachineParams_DataClass.md` | todos os campos, defaults | machine_model.py:40–73 |
| 22 | `03_Backend/MachineParams_Derivacoes.md` | `__post_init__`: Xml, wb, Xls_a_eff | machine_model.py:75–120 |
| 23 | `03_Backend/Estado_vs_Variavel_Algebrica.md` | por que fluxos são estados | Krause cap. 3 + machine_model.py |
| 24 | `03_Backend/Vetor_de_Estado_8D.md` | y[0..7] explicados; dTemp=0 e porquê | solver.py:51, machine_model.py:247 |
| 25 | `03_Backend/Referencial_dq0.md` | `ref_code` {0,1,2}: estacionário/síncrono/rotor; impacto nos resultados | IWS_PY.py, machine_model.py |
| 26 | `03_Backend/Machine_Model.md` | `_make_rhs`: closure, Krause linha a linha | machine_model.py:183–272 |
| 27 | `03_Backend/Sources_Tensao.md` | `build_fns`, voltage_fn, torque_fn | sources.py, IWS_PY.py |
| 28 | `03_Backend/Arquitetura_Camadas.md` | fachada pública, separação de responsabilidades | IWS_PY.py:1–38 |

---

## Fase F4 — Backend: Solver e Pós-processamento

| # | Nota | Conceito central | Código IWS |
|---|------|-----------------|------------|
| 29 | `03_Backend/Solver_LSODA.md` | `_solve`: segmentação, clamp, max_step; tuning de rtol/atol para performance | solver.py:51–188 |
| 30 | `03_Backend/Reconstrucao_Correntes_abc.md` | fluxos dq → abc via Clarke-Park inverso | solver.py:201–236 |
| 31 | `03_Backend/Deteccao_Regime_Permanente.md` | janela LCM-alinhada | solver.py:237–281 |
| 32 | `03_Backend/Balanco_Potencia_Regime.md` | RMS, η, P_gap, P_cu, P_fe | solver.py:340–fim |
| 33 | `03_Backend/Thermal_Post_Processing.md` | Euler implícito; por que separado da ODE | solver.py:282–339 |

---

## Fase F5 — Modos de Operação

DOL é o template. Escrever DOL completo antes dos outros — os outros fazem diff com DOL.

| # | Nota | Novidade em relação a DOL |
|---|------|--------------------------|
| 34 | `05_Modos_Operacao/Partida_DOL.md` | template base |
| 35 | `05_Modos_Operacao/Partida_YD.md` | t_cutoff + chaveamento de tensão |
| 36 | `05_Modos_Operacao/Partida_SoftStarter.md` | rampa de tensão (`voltage_soft_starter`) |
| 37 | `05_Modos_Operacao/Partida_Autotransformador.md` | tensão reduzida fixa |
| 38 | `05_Modos_Operacao/Pulso_de_Carga.md` | `torque_pulse` |
| 39 | `05_Modos_Operacao/Modo_Gerador.md` | torque negativo, slip < 0 |
| 40 | `05_Modos_Operacao/Desligamento.md` | `clamp_wr_at_zero` |
| 41 | `05_Modos_Operacao/Sag_de_Tensao.md` | `voltage_sag` |

---

## Fase F6 — Falhas e Diagnóstico

Falhas pressupõem modo estável funcionando (F5 concluída).

| # | Nota | Dependência |
|---|------|-------------|
| 42 | `06_Falhas_Diagnostico/Desequilibrio_Tensao.md` | Componentes_Simetricas + DOL |
| 43 | `06_Falhas_Diagnostico/Falta_de_Fase.md` | Desequilibrio_Tensao |
| 44 | `06_Falhas_Diagnostico/Barra_Quebrada.md` | Machine_Model (Rr modulado) |
| 45 | `06_Falhas_Diagnostico/Diagnostico_Automatizado.md` | todos acima |

---

## Fase F7 — Frontend

UI só faz sentido após backend e modos claros.

| # | Nota | Conceito central | Código IWS |
|---|------|-----------------|------------|
| 44 | `04_Frontend/_WK_Pattern.md` | dicionário `_WK`: elo UI↔cálculo; origem do padrão, alternativas descartadas | sim_config.py:87 |
| 45 | `04_Frontend/Session_State_Widget_Keys.md` | widget key → session_state automático | sim_config.py |
| 46 | `04_Frontend/Cache_Streamlit.md` | `@st.cache_data` vs. `@st.cache_resource` | sim_results.py |
| 47 | `04_Frontend/Persistencia_Resultado.md` | `sim_result` persiste; quando invalida | sim_runner.py:116 |
| 48 | `04_Frontend/Estrutura_Abas.md` | roteamento, `page_config` | IWS_UI.py |
| 49 | `04_Frontend/Sidebar_e_Controles.md` | `render_machine_selector`, presets | sim_config.py:30 |
| 50 | `04_Frontend/Plotly_Frames_Zero_Latencia.md` | frames pré-calculados; estado atual vs. objetivo | plotly_charts.py |
| 51 | `04_Frontend/PDF_Report.md` | pipeline ReportLab: pdf_commons.py (base) + pdf_academico.py + pdf_industrial.py | viz/pdf_commons.py |

---

## Fase F8 — Fluxo de Dados E2E

Integra tudo. Escrever após F3–F7 completos.

| # | Nota | Descrição |
|---|------|-----------|
| 52 | `07_Fluxo_de_Dados/Input_para_MachineParams.md` | widget → _WK → MachineParams campo a campo |
| 53 | `07_Fluxo_de_Dados/MachineParams_para_Solver.md` | dataclass → build_fns → run_simulation |
| 54 | `07_Fluxo_de_Dados/Solver_para_Plotly.md` | res dict → figuras → st.plotly_chart |
| 55 | `07_Fluxo_de_Dados/Diagrama_E2E.md` | diagrama Mermaid das 7 etapas |

---

## Fase F9 — Guias de Extensão

Só após padrões estabelecidos nas fases anteriores.

| # | Nota |
|---|------|
| 58 | `03_Backend/Roteador_de_Maquinas.md` |
| 59 | `03_Backend/Como_Adicionar_Nova_Maquina.md` |
| 60 | `05_Modos_Operacao/Como_Adicionar_Novo_Modo.md` |
| 61 | `04_Frontend/Como_Adicionar_Nova_Aba.md` |
| 62 | `08_Guias_Extensao/Checklist_Nova_Maquina.md` |
| 63 | `08_Guias_Extensao/Checklist_Novo_Modo.md` |
| 64 | `08_Guias_Extensao/Checklist_Nova_Aba.md` |
| 65 | `08_Guias_Extensao/Padrao_Teste_Unitario.md` |

---

## Fase F10 — Máquinas Secundárias ⚠️ PLANEJADO — não implementadas no IWS atual

Motor CC primeiro (EDO mais simples). Transformador segundo (sem rotação). MSIP por último (compartilha estrutura dq0 com MIT).
Cada nota de teoria inclui disclaimer: _"Esta máquina ainda não possui implementação no IWS. Os snippets são referências para implementação futura."_
Cada nota `_Implementacao_IWS` é um checklist de 4 arquivos usando o padrão MIT como referência.

| # | Nota | Razão da ordem |
|---|------|---------------|
| 66 | `02_Maquinas/Motor_CC/MCC_Visao_Geral.md` | EDO de 1ª ordem — âncora didática |
| 67 | `02_Maquinas/Motor_CC/MCC_Modelo_EDO.md` | mais simples que MIT |
| 68 | `02_Maquinas/Motor_CC/MCC_Implementacao_IWS.md` | checklist padrão MIT; referência cruzada com [[Checklist_Nova_Maquina]] |
| 69 | `02_Maquinas/Transformador/TR_Visao_Geral.md` | circuito equivalente sem rotação |
| 70 | `02_Maquinas/Transformador/TR_Circuito_Equivalente.md` | base para entender Xm no MIT |
| 71 | `02_Maquinas/Transformador/TR_Implementacao_IWS.md` | diferença chave: sem `wr`, sem equação mecânica |
| 72 | `02_Maquinas/MSIP/MSIP_Visao_Geral.md` | pressupõe MIT_Modelo_dq0 |
| 73 | `02_Maquinas/MSIP/MSIP_Modelo_dq0.md` | diff com MIT: λ_pm, sem Rr independente |
| 74 | `02_Maquinas/MSIP/MSIP_Parametros.md` | — |
| 75 | `02_Maquinas/MSIP/MSIP_Implementacao_IWS.md` | λ_pm no vetor de estado; Te = 1.5·(p/2)·λ_pm·iqs |

---

## Fase F11 — Snapshot e Meta Final

| # | Nota |
|---|------|
| 76 | `09_Snapshots_IWS/Snapshot_Arquitetura_2026-05.md` |
| 77 | `09_Snapshots_IWS/Changelog_Decisoes.md` |
| 78 | `00_Meta/INDEX.md` (revisão final — ligar todas as notas) |

---

## Resumo de Progresso

| Fase | Notas | Status sugerido |
|------|-------|----------------|
| F0 Meta | 1–5 | Escrever no dia 1 |
| F0.5 Python | 6–10 | Escrever no dia 1–2 |
| F1 Fundamentos | 11–15 | Dia 2–3 |
| F2 MIT | 16–20 | Dia 3–4 |
| F3 Backend Modelagem | 21–28 | Dia 4–6 |
| F4 Solver + Pós-proc | 29–33 | Dia 6–8 |
| F5 Modos | 34–41 | Dia 8–10 |
| F6 Falhas | 42–45 | Dia 10–11 |
| F7 Frontend | 46–53 (incl. _WK) | Dia 11–13 |
| F8 Fluxo E2E | 54–57 | Dia 13–14 |
| F9 Extensão | 58–65 | Dia 14–16 |
| F10 Máq. Secundárias ⚠️ | 66–75 | Dia 16–20 |
| F11 Snapshot | 76–78 | Dia 20 |
| **Total** | **78 notas** | |
