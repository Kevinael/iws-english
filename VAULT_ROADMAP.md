# VAULT_ROADMAP — Ordem de Construção do Simulador
> Sequência narrativa: cada nota responde "por que precisei disso aqui".
> Última atualização: 2026-05-24.

---

## Princípio

A ordem é a ordem em que você **construiria** o simulador do zero.
Cada nota começa com um problema. A nota seguinte usa a solução da anterior.
Nunca apresentar uma ferramenta antes do problema que ela resolve.

---

## Capítulo 0 — Setup (ler uma vez, voltar quando precisar)

| # | Nota | Por que ler |
|---|------|-------------|
| 1 | `00_Setup/Como_Rodar_o_IWS.md` | Rodar antes de ler qualquer outra nota |
| 2 | `00_Setup/Mapa_do_Codigo.md` | Saber onde cada coisa fica antes de mergulhar |
| 3 | `00_Setup/Glossario.md` | Referência — voltar quando aparecer termo desconhecido |

---

## Capítulo 1 — O Problema Central: Simular o Motor no Tempo

**Narrativa:** "Quero ver corrente, torque e velocidade de um motor ao longo do tempo. Como começo?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 4 | `01_Problema_Central/O_Que_Queremos_Simular.md` | Define o objetivo: séries temporais de wr, Te, ias |
| 5 | `01_Problema_Central/EDO_Como_Ferramenta.md` | Por que o estado do motor obedece EDOs; o que é rhs(t,y) |
| 6 | `01_Problema_Central/Primeiro_Simulador.md` | Motor CC: 2 estados, código mínimo que funciona |
| 7 | `01_Problema_Central/Por_Que_8_Estados.md` | De MCC (2 estados) para MIT (8): cada estado adicionado tem razão |

**Ponto de chegada:** após nota 7, você entende *por que* o IWS tem 8 estados e o que cada um representa.

---

## Capítulo 2 — Organizando os Parâmetros

**Narrativa:** "Tenho `Rs`, `Rr`, `Xm`, `f`, `p`... como organizo sem virar um caos?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 8 | `02_Organizando_Parametros/O_Problema_dos_Parametros.md` | Variáveis globais e dicionários falham: por quê |
| 9 | `02_Organizando_Parametros/Dataclass_Como_Solucao.md` | @dataclass: campos tipados, defaults, __post_init__ |
| 10 | `02_Organizando_Parametros/MachineParams_Campo_a_Campo.md` | Cada campo do MIT: o que é, unidade, por que existe |
| 11 | `02_Organizando_Parametros/Campos_Derivados.md` | wb, Xml, Xls_a_eff: calculados em __post_init__, não pelo usuário |

**Ponto de chegada:** você consegue instanciar `MachineParams` manualmente e entender o que cada campo faz.

---

## Capítulo 3 — Conectando Parâmetros ao Solver

**Narrativa:** "`solve_ivp` só aceita `rhs(t, y)`. Como passo `Rs`, `Rr`, `voltage_fn` para dentro?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 12 | `03_Conectando_Parametros_ao_Solver/O_Problema_da_Assinatura.md` | Por que `rhs(t, y, mp)` não funciona com solve_ivp |
| 13 | `03_Conectando_Parametros_ao_Solver/Closure_Como_Solucao.md` | Função que retorna função; captura por valor |
| 14 | `03_Conectando_Parametros_ao_Solver/make_rhs_Construindo.md` | Construir _make_rhs passo a passo a partir das equações de Krause |
| 15 | `03_Conectando_Parametros_ao_Solver/Performance_No_Hot_Path.md` | Por que `Rs = mp.Rs` antes de `def rhs` importa em 50k chamadas/s |

**Ponto de chegada:** você consegue escrever uma `_make_rhs` simples para uma máquina nova.

---

## Capítulo 4 — Rodando a Simulação

**Narrativa:** "Tenho `rhs`. Como rodo de t=0 até t=3s com passo controlado, sem instabilidade?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 16 | `04_Rodando_a_Simulacao/Como_solve_ivp_Funciona.md` | LSODA: rtol/atol, max_step, o que o retorno significa |
| 17 | `04_Rodando_a_Simulacao/Segmentacao_e_Eventos.md` | Por que _solve divide em segmentos em vez de rodar tudo de uma vez |
| 18 | `04_Rodando_a_Simulacao/Vetor_de_Estado_Detalhado.md` | y[0..7] linha a linha: ordem importa, unidades importam |
| 19 | `04_Rodando_a_Simulacao/Clamp_e_Estabilidade.md` | clamp_wr_at_zero: o que acontece sem ele no modo desligamento |

**Ponto de chegada:** você consegue chamar `_solve` manualmente e interpretar o array resultante.

---

## Capítulo 5 — Pós-Processamento

**Narrativa:** "`_solve` me deu fluxos e velocidade. Quero correntes abc, rendimento e temperatura."

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 20 | `05_Pos_Processamento/Correntes_a_Partir_de_Fluxos.md` | Por que integrar fluxos (não correntes); como inverter a transformada |
| 21 | `05_Pos_Processamento/Detectando_Regime_Permanente.md` | Por que janela LCM-alinhada em vez de média simples |
| 22 | `05_Pos_Processamento/Balanco_de_Potencia.md` | De onde vêm P_gap, P_cu_s, P_cu_r, P_fe, η no res dict |
| 23 | `05_Pos_Processamento/Modelo_Termico_Separado.md` | Por que temperatura não está na ODE — problema de escala de tempo |

**Ponto de chegada:** você entende todo o `res` dict — o que cada chave contém e de onde veio.

---

## Capítulo 6 — Fontes de Excitação

**Narrativa:** "Quero simular DOL, Y-Δ, sag de tensão... sem duplicar `run_simulation` para cada um."

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 24 | `06_Fontes_de_Excitacao/voltage_fn_e_torque_fn.md` | Por que funções (não valores fixos) para tensão e torque |
| 25 | `06_Fontes_de_Excitacao/build_fns_A_Fabrica.md` | Como build_fns fabrica as funções certas para cada exp_type |
| 26 | `06_Fontes_de_Excitacao/Captura_por_Valor.md` | O bug clássico do lambda sem _x=x — com exemplo que falha |
| 27 | `06_Fontes_de_Excitacao/Cada_Modo_Explicado.md` | DOL, Y-Δ, soft-starter, sag: o diff de build_fns entre eles |

**Ponto de chegada:** você consegue adicionar um novo modo apenas em `sources.py`.

---

## Capítulo 7 — Interface Streamlit

**Narrativa:** "Quero uma UI onde o usuário digita parâmetros e clica 'Executar'. Como Streamlit funciona?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 28 | `07_Interface_Streamlit/Como_Streamlit_Funciona.md` | Rerun: o que dispara, o que perde, o que persiste — o modelo mental |
| 29 | `07_Interface_Streamlit/Session_State.md` | Por que session_state existe; o que guardar nele |
| 30 | `07_Interface_Streamlit/WK_O_Elo_UI_Backend.md` | _WK: por que o dicionário de mapeamento evita bugs silenciosos |
| 31 | `07_Interface_Streamlit/Widgets_e_Keys.md` | key= no widget → session_state automático; o que acontece sem key |
| 32 | `07_Interface_Streamlit/Cache_e_Performance.md` | @st.cache_data: quando usar, quando não usar, armadilhas |

**Ponto de chegada:** você entende por que o IWS não quebra quando o usuário muda um parâmetro e clica Executar.

---

## Capítulo 8 — Mostrando Resultados

**Narrativa:** "Tenho o `res` dict. Como mostro gráficos interativos sem travar a UI?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 33 | `08_Mostrando_Resultados/O_Res_Dict.md` | Estrutura do dicionário: chaves temporais vs. chaves de regime |
| 34 | `08_Mostrando_Resultados/Plotly_No_Streamlit.md` | st.plotly_chart, _PLOT_CFG, responsive |
| 35 | `08_Mostrando_Resultados/Frames_Zero_Latencia.md` | Por que frames pré-calculados em vez de recalcular no slider |
| 36 | `08_Mostrando_Resultados/KPIs_e_Metricas.md` | st.metric, o que vale a pena exibir e como calcular |

**Ponto de chegada:** você consegue construir uma tela de resultados para uma nova análise.

---

## Capítulo 9 — Arquitetura Completa

**Narrativa:** "Entendo cada peça isolada. Como elas se encaixam?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 37 | `09_Arquitetura_Completa/Fluxo_E2E.md` | Diagrama Mermaid: widget → MachineParams → solver → Plotly |
| 38 | `09_Arquitetura_Completa/Por_Que_Cada_Arquivo_Existe.md` | IWS_PY, machine_model, solver, sources: responsabilidade e fronteira |
| 39 | `09_Arquitetura_Completa/Fachada_IWS_PY.md` | Por que IWS_PY.py existe: ponto único de entrada, retrocompatibilidade |
| 40 | `09_Arquitetura_Completa/Separacao_de_Responsabilidades.md` | Por que machine_model não importa Streamlit — e por que isso importa |

**Ponto de chegada:** você consegue explicar a arquitetura completa em 5 minutos para alguém novo.

---

## Capítulo 10 — Falhas e Diagnóstico

**Narrativa:** "Quero simular motor com defeito. Como modificar o modelo sem quebrar o caso normal?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 41 | `10_Falhas_e_Diagnostico/Desequilibrio_de_Tensao.md` | Como aplicar assimetria nas 3 fases sem alterar rhs |
| 42 | `10_Falhas_e_Diagnostico/Falta_de_Fase.md` | Diferença de implementação vs. desequilíbrio |
| 43 | `10_Falhas_e_Diagnostico/Barra_Quebrada.md` | rr_fn como closure: Rr modulado no tempo |
| 44 | `10_Falhas_e_Diagnostico/Diagnostico_Automatizado.md` | generate_insights: como detectar anomalia nos dados do res dict |

---

## Capítulo 11 — Extensão

**Narrativa:** "Quero adicionar nova máquina / novo modo / nova aba. Por onde começo?"

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 45 | `11_Extensao/Adicionando_Nova_Maquina.md` | 6 arquivos, motivação de cada passo |
| 46 | `11_Extensao/Adicionando_Novo_Modo.md` | sources.py + sim_config: onde e por quê |
| 47 | `11_Extensao/Adicionando_Nova_Aba.md` | sim_results + IWS_UI: padrão e armadilhas |
| 48 | `11_Extensao/Padrao_de_Testes.md` | Como testar sem UI: invariantes físicos que não mudam |

---

## Capítulo 12 — Referência (consulta, não leitura)

| # | Nota | Quando consultar |
|---|------|-----------------|
| 49 | `12_Referencia/API_run_simulation.md` | Todos os parâmetros de run_simulation |
| 50 | `12_Referencia/API_MachineParams.md` | Todos os campos com unidade e faixa típica |
| 51 | `12_Referencia/API_build_fns.md` | exp_types, estrutura de exp_config |
| 52 | `12_Referencia/Snapshot_Arquitetura_2026-05.md` | Estado do código em 2026-05-24 |

---

## Resumo de Progresso

| Cap | Tema | Notas | Status |
|-----|------|-------|--------|
| 0 | Setup | 3 | A escrever |
| 1 | Problema Central | 4 | A escrever |
| 2 | Parâmetros | 4 | A escrever |
| 3 | Closure / _make_rhs | 4 | Parcial (Closures_e_Factories reescrita) |
| 4 | Solver | 4 | A escrever |
| 5 | Pós-processamento | 4 | A escrever |
| 6 | Fontes | 4 | A escrever |
| 7 | Streamlit | 5 | A escrever |
| 8 | Resultados | 4 | A escrever |
| 9 | Arquitetura | 4 | A escrever |
| 10 | Falhas | 4 | A escrever |
| 11 | Extensão | 4 | Parcial (Como_Adicionar_Nova_Maquina reescrita) |
| 12 | Referência | 4 | A escrever |
| **Total** | | **52 notas** | |

---

## Notas Antigas (F0–F9) — Status de Migração

Conteúdo correto, estrutura errada (módulo, não problema).
Migrar ao reescrever: aplicar template narrativo e mover para capítulo correto.

| Nota antiga | Capítulo novo | Status |
|---|---|---|
| `Closures_e_Factories.md` | Cap 3 | ✅ Reescrita |
| `Machine_Model.md` | Cap 3–4 | ✅ Reescrita |
| `Como_Adicionar_Nova_Maquina.md` | Cap 11 | ✅ Reescrita |
| Demais notas F0–F9 | Vários | A migrar |
