# IWS — Mapa de Conteúdo (MOC)

> Guia de navegação do simulador de máquinas de indução trifásica — Arquitetura, Programação e Expansão

---

## Estrutura

### **Bloco 1: Fundamentos**
- [[FUN01_Estrutura_Projeto]] — árvore, módulos, fluxo de entrada
- [[FUN02_Fachada_IWS_PY]] — contrato de API público

### **Bloco 2: Núcleo Matemático**

#### 2.1 Transformadas
- [[MAT01_Transformadas_Visao_Alto_Nivel]] — Park/Clarke conceitual
- [[MAT01_Transformadas_Codigo]] — implementação em Python (este documento)
- [[MAT01_Transformadas_Exemplos]] — numéricos e gráficos

#### 2.2 Modelo de Máquina (dq0 Krause)
- [[MAT02_MachineModel_Estrutura]] — class MachineModel, init, step()
- [[MAT02_MachineModel_Equacoes]] — tradução: física → código
- [[MAT02_MachineModel_Torque_Potencia]] — cálculo EM

#### 2.3 Modelo Térmico
- [[MAT03_Thermal_RC]] — equação térmica, perdas

#### 2.4 Fontes de Tensão
- [[MAT04_Sources_Tipos]] — DOL, Y-Δ, soft-starter, frenagem

#### 2.5 Desequilíbrio e Faltas
- [[MAT05_Desequilibrio_Falta]] — assimetria, barra quebrada

#### 2.6 Integrador LSODA
- [[MAT06_Solver_LSODA]] — inicialização, callback, tolerâncias

#### 2.7 Análise Energética
- [[MAT07_Energy_Analysis]] — potências, eficiência, perdas

#### 2.8 Análise Harmônica e MCSA
- [[MAT08_Harmonica_MCSA]] — FFT, diagnóstico de barra quebrada

#### 2.9 Diagnóstico
- [[MAT09_Diagnostics]] — detecção pós-simulação

### **Bloco 3: Visualização e Relatórios**
- [[VIZ01_Plotly_Frames]] — duto de dados, zero-latência
- [[VIZ02_PDF_Relatorios]] — ReportLab, estrutura acadêmica

### **Bloco 4: Interface e Componentes**
- [[UI01_SessionState_Streamlit]] — ciclo reativo, callbacks
- [[UI02_Configuracao]] — máquina, acionamento, experimento
- [[UI03_Resultados]] — abas de output
- [[UI04_Teoria]] — educacional, componentes interativos

### **Bloco 5: Orquestração**
- [[ORQ01_IWS_UI_Principal]] — entrada, roteamento de abas

### **Bloco 6: Expandibilidade**
- [[EXP01_Adicionar_Maquina]] — novo preset de parâmetros
- [[EXP02_Novo_Acionamento]] — novo Source
- [[EXP03_Novo_Experimento]] — distúrbio, duração
- [[EXP04_Novo_Diagnostico]] — módulo de análise
- [[EXP05_Novo_Grafico]] — Plotly interativo

---

## Roteiro de Aprendizado

| Semana | Blocos | Objetivo |
|--------|--------|----------|
| 1 | 1, 2.1–2.3 | Fluxo matemático: estado → torque EM |
| 2 | 2.4–2.6 | Solver, fontes, integração |
| 3 | 3–4 | Visualização + interface reativa |
| 4 | 5–6 | Orquestração + como estender |

---

## Convenções

- **Notas conceptuais:** prefixo `*_Visao_*`
- **Notas de código:** prefixo `*_Codigo` ou nome função
- **Guias de extensão:** `EXP*`
- **Links internos:** `[[nota_alvo]]`
- **Links para código:** `[path:linhas](file.py#L42-L60)`

---

## Status

| Bloco | Status |
|-------|--------|
| 1 | 🟠 Planejado |
| **2.1** | **🟢 Completo** |
| 2.2–2.9 | 🟠 Planejado |
| 3–6 | 🟠 Planejado |

## Notas Criadas

- ✅ [[MAT01_Transformadas_Visao_Alto_Nivel]] — Conceitual
- ✅ [[MAT01_Transformadas_Codigo]] — Implementação (aula)
- ✅ [[MAT01_Transformadas_Exemplos]] — Numéricos + gráficos
- 🟠 [[MAT01_Transformadas_Exercicio]] — Prático (Perguntas 1–3 + teste)

---

Criado: 2026-05-26 | Última revisão: 2026-05-26
