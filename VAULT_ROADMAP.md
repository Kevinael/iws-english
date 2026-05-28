# VAULT_ROADMAP — Ordem de Construção do Simulador
> Sequência narrativa: cada nota responde "por que precisei disso aqui".
> Última atualização: 2026-05-24.

---

## Princípio

A ordem é a ordem em que você **construiria** o simulador do zero.
Cada nota começa com um problema. A nota seguinte usa a solução da anterior.
Nunca apresentar uma ferramenta antes do problema que ela resolve.

**Padrão de escrita (revisado em 2026-05-24):** estrutura obrigatória em toda nota:

1. **Tentativa ingênua** — solução óbvia + por que falha (consequência concreta)
2. **Passos numerados** (mín. 2, máx. 6) — cada passo = uma decisão, um fragmento de código
3. **Código completo** — consolidação sem novidades
4. **O Que Você Acabou de Construir** — tabela ligando exemplo ao IWS real (arquivo + linha)
5. **Exercício** — tarefa verificável sem rodar o IWS completo
6. **Próxima nota** — obrigatória, indica o problema que a próxima resolve

Ver `VAULT_PLAN.md` → seção "Template de Nota" para o template completo com checklist.
Piloto: `SimMEE-Vault/01_Problema_Central/Primeiro_Simulador.md` (a escrever).

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
| 14 | `03_Conectando_Parametros_ao_Solver/make_rhs_Construindo.md` | Construir _make_rhs; mapeamento referencial estacionário→código; como dq0 de Krause vira as 8 EDOs |
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
| 23b | `05_Pos_Processamento/Validando_contra_Placa.md` | Motor simulado não bate com a placa: roteiro de debug — parâmetro errado, rtol/atol frouxo, ou erro de equação? |

**Ponto de chegada:** você entende todo o `res` dict e sabe verificar se os números fazem sentido físico.

---

## Capítulo 6 — Fontes de Excitação

**Narrativa:** "Quero simular DOL, Y-Δ, sag de tensão... sem duplicar `run_simulation` para cada um."

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 24 | `06_Fontes_de_Excitacao/voltage_fn_e_torque_fn.md` | Por que funções (não valores fixos) para tensão e torque |
| 25 | `06_Fontes_de_Excitacao/build_fns_A_Fabrica.md` | Como build_fns fabrica as funções certas para cada exp_type |
| 26 | `06_Fontes_de_Excitacao/Captura_por_Valor.md` | O bug clássico do lambda sem _x=x — com exemplo que falha |
| 27 | `06_Fontes_de_Excitacao/Cada_Modo_Explicado.md` | DOL, Y-Δ, soft-starter, sag: o diff de build_fns entre eles |
| 27b | `06_Fontes_de_Excitacao/Perfis_de_Carga_Mecanica.md` | Construir torque_fn constante, quadrática e rampa; separação explícita entre Te (eletromagnético) e Tl (carga) |

**Ponto de chegada:** você consegue adicionar um novo modo de tensão ou um novo perfil de carga apenas em `sources.py`.

---

## Capítulo 7 — Interface Streamlit

**Narrativa:** "Tenho o simulador funcionando. Agora quero uma UI onde o usuário digita parâmetros, clica 'Executar' e vê resultados — e que não quebre quando ele muda qualquer coisa."

O capítulo tem dois blocos: **comportamento** (como Streamlit executa) e **construção** (como programar layout, tema e componentes customizados).

### Bloco A — Comportamento do Streamlit

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 28 | `07_Interface_Streamlit/Como_Streamlit_Funciona.md` | Rerun: o que dispara, o que perde, o que persiste — o modelo mental |
| 29 | `07_Interface_Streamlit/Session_State.md` | Por que session_state existe; o que guardar nele |
| 30 | `07_Interface_Streamlit/WK_O_Elo_UI_Backend.md` | _WK: por que o dicionário de mapeamento evita bugs silenciosos |
| 31 | `07_Interface_Streamlit/Widgets_e_Keys.md` | key= no widget → session_state automático; o que acontece sem key |
| 32 | `07_Interface_Streamlit/Cache_e_Performance.md` | @st.cache_data: quando usar, quando não usar, armadilhas |

### Bloco B — Construindo a UI

| # | Nota | Problema que resolve |
|---|------|---------------------|
| 32b | `07_Interface_Streamlit/Arquitetura_da_Pagina.md` | Quero parâmetros e circuito lado a lado, controles no topo, abas separando seções — como programar isso com `st.columns` e `st.tabs`? Tentei empilhar widgets verticalmente: ficou inutilizável. |
| 32c | `07_Interface_Streamlit/Tema_e_CSS.md` | Quero modo escuro, fonte Inter, sidebar escondida. Tentei o seletor de tema nativo do Streamlit: não controla o suficiente. Como injetar CSS global via `st.markdown` e estruturar `theme.py`? |
| 32d | `07_Interface_Streamlit/Componentes_HTML_Customizados.md` | Quero uma tabela densa de KPIs com estilo preciso. Tentei `st.dataframe` e `st.table`: sem controle visual. Como e por que usar `st.html()` com HTML puro, e como programar construtores `_row()`, `_section()`, `_fmt()` como fazemos em `clean_view.py`? |

**Ponto de chegada:** você entende o modelo de execução do Streamlit, não quebra o estado ao mudar parâmetros, e consegue construir uma nova tela do zero com layout, tema e componentes customizados — programando cada parte, não copiando.

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
| 44b | `10_Falhas_e_Diagnostico/Erros_Comuns_de_Interpretacao.md` | Te ≠ Tl, transitório ≠ regime permanente, MCSA mal-lida: armadilhas clássicas com exemplos concretos |

**Ponto de chegada:** você consegue simular falha, interpretar o diagnóstico corretamente, e não confundir grandezas eletromagnéticas com grandezas de carga.

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

## Resumo de Progresso (2026-05-24)

Legenda: ✅ completo · 🔧 existe mas incompleto (falta checklist) · ❌ não existe

| Cap | Tema | Notas planejadas | Existem | Status |
|-----|------|-----------------|---------|--------|
| 0 | Setup | 3 | 3 | ✅ Como_Rodar · ✅ Mapa_do_Codigo · ✅ Glossario |
| 1 | Problema Central | 4 | 4 | 🔧 O_Que_Queremos_Simular · EDO_Como_Ferramenta · Primeiro_Simulador · Por_Que_8_Estados |
| 2 | Parâmetros | 4 | 0 | ❌ |
| 3 | Closure / _make_rhs | 4 | 0 | ❌ (rascunhos em F0–F9, localizar) |
| 4 | Solver | 4 | 4 | 🔧 Migrar checklist |
| 5 | Pós-processamento | 5 | 4 | 🔧 Migrar checklist + escrever Validando_contra_Placa |
| 6 | Fontes | 5 | 4 | 🔧 Migrar checklist + escrever Perfis_de_Carga_Mecanica |
| 7 | Streamlit (comportamento + UI) | 8 | 5 | 🔧 5 existem (migrar checklist) + 3 UI a escrever |
| 8 | Resultados | 4 | 0 | ❌ |
| 9 | Arquitetura | 4 | 0 | ❌ |
| 10 | Falhas | 5 | 0 | ❌ |
| 11 | Extensão | 4 | 0 | ❌ (rascunho em F0–F9, localizar) |
| 12 | Referência | 4 | 0 | ❌ |
| **Total** | | **58 notas** | **24** | **41% existem, 7 prontas (Caps 0–1)** |

**Próxima ação:** escrever `02_Organizando_Parametros/O_Problema_dos_Parametros.md`.
Depois: `Dataclass_Como_Solucao.md` → `MachineParams_Campo_a_Campo.md` → `Campos_Derivados.md`.

---

## Dívida de Migração — Notas Existentes (Caps 4–7)

17 notas existentes têm conteúdo correto mas violam o template revisado.
Todas precisam dos mesmos 4 elementos antes de `status: publicado`:

| Elemento ausente | Notas afetadas |
|---|---|
| Passos numerados (`## Passo N`) | todas as 17 |
| Tabela "O Que Você Acabou de Construir" | todas as 17 |
| Exercício verificável | todas as 17 |
| "Próxima Nota" | 13 de 17 (Cap 5, 6, 7 incompletos) |

**Critério de migração:** ao reescrever qualquer nota, aplicar checklist completo e mudar `status: rascunho`.
Não reescrever em massa — fazer nota por nota, na ordem do capítulo.

**Prioridade:** Cap 0 e Cap 1 primeiro (não existem; são pré-requisito de tudo).
Só depois migrar Caps 4–7.

---

## Notas Antigas (F0–F9) — Status de Migração

Conteúdo correto, estrutura errada (módulo, não problema).
Migrar ao reescrever: aplicar template narrativo e mover para capítulo correto.

| Nota antiga | Capítulo novo | Status |
|---|---|---|
| `Closures_e_Factories.md` | Cap 3 | ✅ Reescrita (migrar checklist) |
| `Machine_Model.md` | Cap 3–4 | ✅ Reescrita (migrar checklist) |
| `Como_Adicionar_Nova_Maquina.md` | Cap 11 | ✅ Reescrita (migrar checklist) |
| Demais notas F0–F9 | Vários | A migrar |
