# VAULT_PLAN — Como o IWS Foi Construído
> Guia narrativo de construção do simulador IWS do zero.
> Última atualização: 2026-05-24.

---

## Objetivo

Ensinar **como programar um simulador** usando o IWS como caso real.

### Leitor-alvo

Você mesmo — com o seguinte perfil:

| Conhece bem | Conhece pouco ou nada |
|---|---|
| Engenharia elétrica (MIT, circuito equivalente, dq0 conceitualmente) | Python além do básico (closures, dataclasses, decorators) |
| O que é corrente, torque, velocidade síncrona | EDO numérica (o que solve_ivp faz internamente) |
| Física do motor de indução | Streamlit, Plotly, ReportLab |

O Vault parte do zero em Python avançado e EDO numérica. Não explica circuito equivalente — assume que você sabe o que Rs, Rr, Xm significam fisicamente.

**Objetivo concreto:** ao terminar o Vault, você consegue:
1. Explicar cada linha de `_make_rhs` em `core/machine_model.py`
2. Adicionar uma nova máquina ao IWS sem consultar ninguém
3. Debugar uma simulação que produz números errados
4. Adicionar um novo modo de operação em `sources.py`
5. Construir uma nova tela no IWS: layout, tema, widgets e componentes HTML customizados

O Vault não é documentação de referência. É a história de construção: cada capítulo começa com um problema real, mostra por que a solução simples não funciona, e explica a decisão que o código implementa.

---

## Princípio de Ordenação

**Problema → Tentativa ingênua → Por que falha → Solução real → Código IWS**

Não: "aqui está o módulo X e o que ele faz."
Sim: "queríamos Y. Tentamos Z. Não funcionou porque W. Então fizemos assim."

A ordem é a ordem em que *você construiria* o simulador do zero:

| Etapa de construção | Capítulos |
|---|---|
| 1. Simular o motor no tempo | Cap 0 (setup) + Cap 1 (EDO, primeiro simulador) |
| 2. Organizar os parâmetros | Cap 2 (MachineParams, dataclass) |
| 3. Conectar parâmetros ao integrador | Cap 3 (closure, _make_rhs) |
| 4. Rodar com precisão e estabilidade | Cap 4 (solver, segmentação) |
| 5. Extrair resultados úteis | Cap 5 (pós-processamento, balanço de potência) |
| 6. Suportar múltiplos experimentos | Cap 6 (fontes de tensão/carga) |
| 7. Ligar tudo a uma interface | Cap 7 (Streamlit: comportamento + layout + design) |
| 8. Mostrar o que aconteceu | Cap 8 (Plotly, frames, KPIs) |
| 9. Entender a arquitetura completa | Cap 9 (fluxo E2E, separação de responsabilidades) |
| 10. Adicionar diagnóstico e análise de falhas | Cap 10 (desequilíbrio, barra quebrada, MCSA) |
| 11. Tornar tudo extensível | Cap 11 (nova máquina, novo modo, nova aba) |
| — Referência | Cap 12 (API, snapshot de arquitetura) |

---

## Estrutura de Diretórios

```
📁 SimMEE-Vault/
│
├── 📁 00_Setup/
│   ├── Como_Rodar_o_IWS.md          ← streamlit run, venv, dependências
│   ├── Mapa_do_Codigo.md             ← quais arquivos existem e para que servem
│   └── Glossario.md                  ← termos técnicos usados no Vault
│
├── 📁 01_Problema_Central/
│   ├── O_Que_Queremos_Simular.md     ← motor no tempo: corrente, torque, velocidade
│   ├── EDO_Como_Ferramenta.md        ← o que é rhs(t,y), o que solve_ivp faz
│   ├── Primeiro_Simulador.md         ← versão mais simples possível: 1 EDO, motor CC
│   └── Por_Que_8_Estados.md          ← de 1 estado (MCC) para 8 (MIT): o que cada um representa
│
├── 📁 02_Organizando_Parametros/
│   ├── O_Problema_dos_Parametros.md  ← por que não usar variáveis globais ou dicionário
│   ├── Dataclass_Como_Solucao.md     ← @dataclass, campos com default, __post_init__
│   ├── MachineParams_Campo_a_Campo.md← cada campo do MIT, por que existe, unidade
│   └── Campos_Derivados.md           ← Xml, wb, Xls_a_eff: calculados de outros
│
├── 📁 03_Conectando_Parametros_ao_Solver/
│   ├── O_Problema_da_Assinatura.md   ← solve_ivp só aceita rhs(t,y): como passar Rs, Rr, Xm?
│   ├── Closure_Como_Solucao.md       ← função que retorna função, captura por valor
│   ├── make_rhs_Construindo.md       ← construir _make_rhs passo a passo; mapeamento referencial estacionário→código; dq0 nas 8 EDOs
│   └── Performance_No_Hot_Path.md    ← por que extrair Rs=mp.Rs antes de rhs
│
├── 📁 04_Rodando_a_Simulacao/
│   ├── Como_solve_ivp_Funciona.md    ← LSODA, rtol/atol, max_step, o que retorna
│   ├── Segmentacao_e_Eventos.md      ← por que _solve divide em segmentos (t_cutoff, eventos)
│   ├── Vetor_de_Estado_Detalhado.md  ← y[0..7]: o que cada índice é, por que nessa ordem
│   └── Clamp_e_Estabilidade.md       ← clamp_wr_at_zero: problema sem ele, solução com ele
│
├── 📁 05_Pos_Processamento/
│   ├── Correntes_a_Partir_de_Fluxos.md ← por que integrar fluxos e não correntes; inversão dq0→abc
│   ├── Detectando_Regime_Permanente.md ← janela LCM-alinhada: por que não média simples
│   ├── Balanco_de_Potencia.md          ← RMS, η, P_gap, P_cu: de onde vêm os números
│   ├── Modelo_Termico_Separado.md      ← por que temperatura não está na ODE
│   └── Validando_contra_Placa.md       ← como verificar se simulação bate com dados de placa; debug físico vs. numérico
│
├── 📁 06_Fontes_de_Excitacao/
│   ├── voltage_fn_e_torque_fn.md     ← por que funções e não valores fixos
│   ├── build_fns_A_Fabrica.md        ← como build_fns constrói as funções para cada experimento
│   ├── Captura_por_Valor.md          ← o bug do lambda sem _x=x, e como evitar
│   ├── Cada_Modo_Explicado.md        ← DOL, Y-Δ, soft-starter, sag: diff de build_fns entre eles
│   └── Perfis_de_Carga_Mecanica.md   ← construir torque_fn constante, quadrático, rampa; separação Te vs Tl
│
├── 📁 07_Interface_Streamlit/
│   ├── Como_Streamlit_Funciona.md    ← rerun: o que dispara, o que perde, o que persiste
│   ├── Session_State.md              ← por que session_state existe, o que guardar nele
│   ├── WK_O_Elo_UI_Backend.md        ← _WK: por que o dicionário de mapeamento existe
│   ├── Widgets_e_Keys.md             ← key= no widget → session_state automático
│   ├── Cache_e_Performance.md        ← @st.cache_data: quando usar, quando não usar
│   ├── Arquitetura_da_Pagina.md      ← st.columns, st.tabs, hierarquia top-to-bottom; por que cada decisão de layout existe
│   ├── Tema_e_CSS.md                 ← apply_css(): injetar CSS global; dark/light mode; quando Streamlit nativo não basta
│   └── Componentes_HTML_Customizados.md ← por que st.html() com HTML puro em vez de widgets; _row(), _section(), _fmt() como construtores de UI
│
├── 📁 08_Mostrando_Resultados/
│   ├── O_Res_Dict.md                 ← estrutura do dicionário de saída de run_simulation
│   ├── Plotly_No_Streamlit.md        ← st.plotly_chart, config, responsive
│   ├── Frames_Zero_Latencia.md       ← frames pré-calculados: por que não recalcular no slider
│   └── KPIs_e_Metricas.md            ← st.metric, como escolher o que exibir
│
├── 📁 09_Arquitetura_Completa/
│   ├── Fluxo_E2E.md                  ← diagrama Mermaid: widget → MachineParams → solver → Plotly
│   ├── Por_Que_Cada_Arquivo_Existe.md← IWS_PY, machine_model, solver, sources: responsabilidade de cada um
│   ├── Fachada_IWS_PY.md             ← por que IWS_PY.py existe: retrocompatibilidade, ponto único
│   └── Separacao_de_Responsabilidades.md ← regra: machine_model não importa Streamlit; por quê importa
│
├── 📁 10_Falhas_e_Diagnostico/
│   ├── Desequilibrio_de_Tensao.md          ← como o código aplica assimetria nas fases
│   ├── Falta_de_Fase.md                    ← diferença de implementação vs. desequilíbrio
│   ├── Barra_Quebrada.md                   ← Rr modulado no tempo: rr_fn como closure
│   ├── Diagnostico_Automatizado.md         ← generate_insights: como detectar anomalia no res dict
│   └── Erros_Comuns_de_Interpretacao.md    ← confundir Te com Tl, transitório vs. regime, outras armadilhas clássicas
│
├── 📁 11_Extensao/
│   ├── Adicionando_Nova_Maquina.md   ← 6 passos com motivação de cada um
│   ├── Adicionando_Novo_Modo.md      ← sources.py + sim_config: onde e por quê
│   ├── Adicionando_Nova_Aba.md       ← sim_results + IWS_UI: padrão e armadilhas
│   └── Padrao_de_Testes.md           ← como testar sem UI: invariantes físicos
│
└── 📁 12_Referencia/
    ├── API_run_simulation.md          ← todos os parâmetros, defaults, o que retorna
    ├── API_MachineParams.md           ← todos os campos com unidade e faixa típica
    ├── API_build_fns.md               ← exp_types suportados, estrutura de exp_config
    └── Snapshot_Arquitetura_2026-05.md← estado do código em 2026-05-24
```

---

## Template de Nota (Código Incremental)

O objetivo de cada nota é fazer o leitor **construir** o código, não lê-lo.

### Princípio

- Cada passo introduz **uma** decisão ou conceito antes de mostrar código.
- Nunca apresentar um bloco grande pronto. Construir em camadas.
- Explicar cada conceito novo antes de usá-lo (ex: "o que é um estado?" antes de escrever `y = [ia, wr]`).
- O código completo aparece **somente no final**, como consolidação — depois que cada parte foi construída nos passos anteriores.
- O leitor ao final da nota deve ser capaz de reproduzir o código **sem olhar para ele**.
- Toda nota termina com um exercício prático mínimo — o leitor faz algo com o que acabou de aprender.

---

### Estrutura completa de uma nota

```markdown
---
titulo: "..."
capitulo: 01 | 02 | ... | 12
status: rascunho | publicado
iws_arquivo: "..."          ← arquivo real do IWS onde o conceito aparece
iws_linhas: "..."           ← intervalo de linhas exato
prerequisitos: ["...", "..."]  ← notas que o leitor deve ter lido antes
---

# [Título da Nota]

> [Uma frase: o risco de não entender isso. Ex: "Errar rtol produz resultados silenciosamente errados."]

---

## O Problema

[Parágrafo curto: qual necessidade concreta gerou essa nota.
Sempre em primeira pessoa do leitor: "Quero X. Como faço?"]

---

## A Tentativa Ingênua

[Mostrar a solução óbvia. Código mínimo que parece funcionar.]

```python
# tentativa: código errado ou incompleto
```

[Explicar por que falha — com consequência concreta, não abstrata.
Ex: "o gráfico de torque aparece suave demais" em vez de "produz imprecisão".]

---

## Passo 1 — [Nome da primeira decisão de design]

[Uma decisão, uma razão. Sem código ainda.]

[Fragmento mínimo introduzindo apenas essa decisão:]

```python
# passo 1: fragmento mínimo
```

[O que mudou e por quê funciona agora.]

---

## Passo 2 — [Nome da segunda decisão]

[Usa o resultado do Passo 1. Introduz um conceito novo antes de usá-lo.]

[Fragmento expandido:]

```python
# passo 2: adiciona sobre o passo 1
```

[...]

---

## Passo N — [Último ajuste ou caso especial]

[...]

---

## Código Completo

> Consolidação dos passos anteriores. Nenhuma linha nova aqui.

```python
# código completo — cada linha foi construída acima
```

---

## O Que Você Acabou de Construir

| Elemento local | Equivalente no IWS | Arquivo | Linha |
|---|---|---|---|
| [variável/função do exemplo] | [nome real no IWS] | [arquivo] | [linha] |

---

## Exercício

[Uma tarefa que o leitor resolve sozinho, usando exatamente o que foi ensinado.
Escopo: 5–15 minutos. Sem resposta na nota — o leitor deve conseguir verificar sozinho
se acertou usando um invariante físico ou teste simples.]

**Exemplo:** "Escreva uma `voltage_fn` que simula queda de 20% em t=1s e retorno em t=2s.
Verifique: `voltage_fn(0.5)` deve retornar `mp.Vl`; `voltage_fn(1.5)` deve retornar `0.8 * mp.Vl`."

---

## Próxima Nota

[[Nome_Da_Proxima_Nota]] — [frase: que problema ela resolve, por que você precisa dela agora]

---

## Referências

- IWS: `arquivo:linhas` — [o que está lá]
- [[Nota_Relacionada_1]] — [por quê é relevante]
- [[Nota_Relacionada_2]] — [por quê é relevante]
```

---

### Regras de aplicação

**Passos:** mínimo 2, máximo 6. Se precisar de mais de 6, a nota cobre dois conceitos — dividir.

**Fragmentos de código:** cada passo mostra apenas o delta em relação ao passo anterior. O leitor
vê o código crescer linha a linha.

**Tentativa ingênua:** obrigatória. Sem ela, o leitor não entende por que a solução real existe.

**Exercício:** obrigatório. Sem ele, o leitor sabe o conceito mas não praticou. O exercício deve
ser verificável por inspeção ou teste simples — nunca depender de rodar o IWS completo.

**Próxima nota:** obrigatória. Sempre indica qual problema a próxima nota resolve. Nunca deixar
o leitor sem direção.

**Links:** usar `[[NomeDaNota]]` (Obsidian) **e** path relativo como fallback em comentário:
```markdown
[[Segmentacao_e_Eventos]]
<!-- fallback: ../04_Rodando_a_Simulacao/Segmentacao_e_Eventos.md -->
```

**Frontmatter `prerequisitos`:** listar todos os slugs de notas que o leitor precisa ter lido.
Permite verificar dependências sem ler o conteúdo.

---

### Checklist antes de marcar `status: publicado`

- [ ] Tentativa ingênua presente e com consequência concreta
- [ ] Pelo menos 2 passos numerados
- [ ] Cada passo introduz **uma** decisão/conceito
- [ ] Nenhum conceito novo no bloco "Código Completo"
- [ ] Tabela "O Que Você Acabou de Construir" preenchida com linhas reais do IWS
- [ ] Exercício presente e verificável sem rodar o IWS completo
- [ ] "Próxima nota" presente com descrição do problema que ela resolve
- [ ] Links com fallback de path relativo

---

### Piloto aprovado

`SimMEE-Vault/01_Problema_Central/Primeiro_Simulador.md` — referência de estilo para todas as notas.
(A ser escrito seguindo este template revisado.)

---

## Estado Atual do Vault (2026-05-24)

### Notas existentes — Caps 4–7

17 notas existem nos diretórios Caps 4–7. Conteúdo correto; estrutura incompleta (faltam exercício, passos numerados, tabela IWS, "Próxima nota" em 13/17).
**Não estão prontas para leitura** — `status: publicado` é incorreto nelas; corrigir para `rascunho` ao migrar.

| Cap | Notas existentes | Faltando |
|---|---|---|
| 4 | 4/4 | exercício, passos, tabela, "próxima" em 0/4 |
| 5 | 4/5 (`Validando_contra_Placa.md` ausente) | exercício, passos, tabela em todos |
| 6 | 4/5 (`Perfis_de_Carga_Mecanica.md` ausente) | exercício, passos, tabela; "próxima" em 0/4 |
| 7 | 5/8 (3 notas de UI ausentes) | exercício, passos, tabela; "próxima" em 0/5 existentes |

### Notas inexistentes — Caps 0–3 e 8–12

41 notas não existem. **Prioridade de escrita:**

1. **Cap 0** — pré-requisito de tudo (setup, mapa do código, glossário)
2. **Cap 1** — núcleo pedagógico (EDO, primeiro simulador, 8 estados)
3. **Cap 2** — MachineParams (pré-requisito de Cap 3)
4. **Cap 3** — closure e _make_rhs (pré-requisito de Cap 4)
5. **Migrar Caps 4–7** — aplicar checklist nas 17 existentes + escrever 5 ausentes
6. **Caps 8–12** — completar o vault

### Notas Antigas (F0–F9) — Status de Migração

Conteúdo correto, estrutura errada (módulo, não problema). Localização atual desconhecida — verificar antes de migrar.

| Nota | Capítulo destino | Status |
|---|---|---|
| `Closures_e_Factories.md` | `03_Conectando_Parametros_ao_Solver/` | ✅ Reescrita (migrar checklist) |
| `Machine_Model.md` | `03_Conectando_Parametros_ao_Solver/` ou `04_` | ✅ Reescrita (migrar checklist) |
| `Como_Adicionar_Nova_Maquina.md` | `11_Extensao/` | ✅ Reescrita (migrar checklist) |
| Demais F0–F9 | Vários | A migrar |
