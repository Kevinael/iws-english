# VAULT_PLAN — Como o IWS Foi Construído
> Guia narrativo de construção do simulador IWS do zero.
> Última atualização: 2026-05-24.

---

## Objetivo

Ensinar **como programar um simulador** usando o IWS como caso real.

O leitor é você mesmo — sabe engenharia elétrica, quer dominar o código, quer ser autônomo para modificar e estender o IWS sem depender de ninguém.

O Vault não é documentação de referência. É a história de construção: cada capítulo começa com um problema real, mostra por que a solução simples não funciona, e explica a decisão que o código implementa.

---

## Princípio de Ordenação

**Problema → Tentativa ingênua → Por que falha → Solução real → Código IWS**

Não: "aqui está o módulo X e o que ele faz."
Sim: "queríamos Y. Tentamos Z. Não funcionou porque W. Então fizemos assim."

A ordem é a ordem em que *você construiria* o simulador do zero:

```
1. Simular o motor no tempo
2. Organizar os parâmetros
3. Ligar a simulação a uma interface
4. Suportar múltiplos experimentos
5. Mostrar o que aconteceu (resultados, gráficos)
6. Adicionar diagnóstico e análises
7. Tornar tudo extensível
```

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
│   ├── make_rhs_Construindo.md       ← construir _make_rhs passo a passo
│   └── Performance_No_Hot_Path.md    ← por que extrair Rs=mp.Rs antes de rhs
│
├── 📁 04_Rodando_a_Simulacao/
│   ├── Como_solve_ivp_Funciona.md    ← LSODA, rtol/atol, max_step, o que retorna
│   ├── Segmentacao_e_Eventos.md      ← por que _solve divide em segmentos (t_cutoff, eventos)
│   ├── Vetor_de_Estado_Detalhado.md  ← y[0..7]: o que cada índice é, por que nessa ordem
│   └── Clamp_e_Estabilidade.md       ← clamp_wr_at_zero: problema sem ele, solução com ele
│
├── 📁 05_Pos_Processamento/
│   ├── Correntes_a_Partir_de_Fluxos.md ← por que integrar fluxos e não correntes
│   ├── Detectando_Regime_Permanente.md ← janela LCM-alinhada: por que não média simples
│   ├── Balanco_de_Potencia.md          ← RMS, η, P_gap, P_cu: de onde vêm os números
│   └── Modelo_Termico_Separado.md      ← por que temperatura não está na ODE
│
├── 📁 06_Fontes_de_Excitacao/
│   ├── voltage_fn_e_torque_fn.md     ← por que funções e não valores fixos
│   ├── build_fns_A_Fabrica.md        ← como build_fns constrói as funções para cada experimento
│   ├── Captura_por_Valor.md          ← o bug do lambda sem _x=x, e como evitar
│   └── Cada_Modo_Explicado.md        ← DOL, Y-Δ, soft-starter, sag: diff de build_fns entre eles
│
├── 📁 07_Interface_Streamlit/
│   ├── Como_Streamlit_Funciona.md    ← rerun: o que dispara, o que perde, o que persiste
│   ├── Session_State.md              ← por que session_state existe, o que guardar nele
│   ├── WK_O_Elo_UI_Backend.md        ← _WK: por que o dicionário de mapeamento existe
│   ├── Widgets_e_Keys.md             ← key= no widget → session_state automático
│   └── Cache_e_Performance.md        ← @st.cache_data: quando usar, quando não usar
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
│   ├── Desequilibrio_de_Tensao.md    ← como o código aplica assimetria nas fases
│   ├── Falta_de_Fase.md              ← diferença de implementação vs. desequilíbrio
│   ├── Barra_Quebrada.md             ← Rr modulado no tempo: rr_fn como closure
│   └── Diagnostico_Automatizado.md   ← generate_insights: como detectar anomalia no res dict
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

## Template de Nota (Narrativo)

Cada nota segue a estrutura problema → solução:

```markdown
---
titulo: "..."
capitulo: 01 | 02 | ... | 12
status: rascunho | publicado
iws_arquivo: "..."
iws_linhas: "..."
---

# Título

> Uma frase: qual problema esta nota resolve.

---

## O Problema

[Descreve o que você estava tentando fazer e por que a abordagem óbvia não funciona.
Sempre começa de uma necessidade concreta, não de um conceito abstrato.]

## A Tentativa Ingênua

[Código ou raciocínio que parece certo mas não funciona — com explicação de por que falha.]

```python
# isso parece razoável, mas quebra porque...
```

## A Solução

[A decisão real que o IWS implementa, com a razão por trás dela.]

## No Código

[Localização exata no IWS. Snippet com anotações explicando cada linha relevante.]

```python
# core/arquivo.py:linha
```

## Consequências e Trade-offs

[O que essa solução ganha. O que ela sacrifica. O que fica mais difícil por causa dela.]

## Referências

- IWS: `arquivo.py:linha`
- [[Nota relacionada]]
```

---

## Notas que já existem (migrar para nova estrutura)

As notas escritas em F0–F9 têm conteúdo correto mas estrutura errada (módulo, não problema).
Migrar gradualmente: ao reescrever uma nota, mover para o capítulo correto e aplicar template narrativo.

Notas-piloto já reescritas (template narrativo aplicado):
- `Closures_e_Factories.md` → mover para `03_Conectando_Parametros_ao_Solver/`
- `Machine_Model.md` → mover para `03_Conectando_Parametros_ao_Solver/` ou `04_Rodando_a_Simulacao/`
- `Como_Adicionar_Nova_Maquina.md` → mover para `11_Extensao/`
