# Infraestrutura Web de Simulação (IWS)

Simulador web interativo de máquinas de indução trifásica, desenvolvido como infraestrutura de pesquisa acadêmica. Cobre modelagem dinâmica (modelo dq0 de Krause), estimação de parâmetros, análise de falhas e geração de relatórios em PDF.

---

## Stack

- Python 3.9+
- Streamlit
- Plotly
- NumPy / SciPy
- ReportLab
- Schemdraw

---

## Instalação e execução

```bash
pip install -r requirements.txt
streamlit run IWS_UI.py
```

---

## Arquitetura

```
IWS_UI.py                          orquestrador (page_config, roteamento de abas principais)
├── ui/
│   ├── clean_view.py              layout "Visualização para Artigo" (sidebar, painel de controle)
│   ├── theory.py                  componentes da aba Teoria
│   ├── theory_interactive.py      widgets interativos da aba Teoria
│   └── theme.py                   sistema de tema CSS, paleta de cores
├── ui_components/
│   ├── sim_config.py              seletor de máquina, parâmetros, presets
│   ├── sim_results.py             visualização de resultados (4 sub-abas)
│   ├── sim_runner.py              orquestração da simulação e cache
│   └── theory_view.py             roteamento da aba Teoria
└── core/
    ├── IWS_PY.py                  fachada pública (MachineParams, run_simulation)
    ├── solver.py                  integrador LSODA (8 estados, h ≤ 1/20f)
    ├── machine_model.py           modelo dq0 (Krause 1986)
    ├── sources.py                 fontes de tensão (senoidal, rampa, falta)
    ├── thermal.py                 modelo térmico (resistência + capacitância)
    ├── energy_analysis.py         análise energética (Sankey, eficiência, perdas)
    ├── harmonica_analysis.py      análise harmônica e MCSA
    ├── sim_diagnostics.py         diagnóstico automatizado de falhas
    ├── desequilibrio_falta.py     desequilíbrio de tensão e falta de fase
    ├── param_estimator.py         estimador de parâmetros (Nameplate e IEEE)
    ├── curva_tn.py                curva de conjugado nominal × velocidade
    └── transforms.py              transformadas Park/Clarke

viz/
├── plotly_charts.py               gráficos interativos (zero-latência via frames Plotly)
├── eqcircuit_plotter.py           circuito equivalente interativo
├── pdf_report.py                  PDF acadêmico (ReportLab)
└── pdf_report_v2.py               PDF dashboard
```

---

## Abas principais

| Aba | Conteúdo |
|---|---|
| **Simulação** | Configuração de máquina, experimento, execução e resultados (4 sub-abas) |
| **Teoria** | 8 subabas com conceitos teóricos, componentes interativos e manual |
| **Visualização para Artigo** | Layout limpo otimizado para captura de figura em publicações |

### Sub-abas de Simulação (aba "Simulação")

| Sub-aba | Conteúdo |
|---|---|
| Visão Geral | Resumo executivo com painel de saúde, KPIs e gráficos sinópticos |
| Análise Dinâmica | Gráficos de forma de onda (correntes, tensões, torque, velocidade, temperatura) |
| Diagnóstico | Diagnóstico automatizado de anomalias, tabelas de assinatura e recomendações |
| Gestão de Ativos | Análise de ciclo de vida, eficiência, perdas e recomendações de operação |

---

## Modos de simulação

| Grupo | Modos | Notas |
|---|---|---|
| Partida | DOL, Y-Δ, Autotransformador, Soft-starter | Zoom automático até 95% de ωr_sinc |
| Regime | Pulso de Carga, Gerador | — |
| Transitório | Desligamento, Sag de Tensão | — |

Perturbações opcionais (toggle): assimetria de fases, falta de fase, barra quebrada.

---

## Funcionalidades

- **Simulação dinâmica** — modelo dq0 de Krause, integrador LSODA, 8 variáveis de estado
- **Estimação de parâmetros** — Nameplate (NEMA MG-1) e IEEE Std 112-2017 com iteração fasorial
- **Análise de falhas** — desequilíbrio de tensão, falta de fase, barra quebrada
- **MCSA** — análise da corrente do estator para diagnóstico de barra quebrada
- **Análise harmônica** — FFT de correntes e torque
- **Análise térmica** — evolução da temperatura no estator e rotor
- **Análise energética** — Sankey de potências, eficiência e perdas
- **Frenagem elétrica** — modos plugging e injeção de CC
- **Diagnóstico automatizado** — detecção de 7+ anomalias pós-simulação
- **Aba Teoria** — 8 subabas com componentes interativos, manual de uso e ferramentas
- **Painel de Saúde** — métricas compactas de operação (KPIs, status, alertas)
- **PDF Acadêmico** — relatório completo com figuras, equações e assinaturas
- **PDF Dashboard** — resumo executivo compacto com figuras principais
- **Visualização interativa** — gráficos Plotly zero-latência via frames pré-calculados
- **Circuito equivalente interativo** — diagrama dq0 com sliders de escorregamento

---

## Estimação de parâmetros

| Método | Entradas | Saída |
|---|---|---|
| Nameplate (NEMA MG-1) | Placa de identificação (Pn, Vn, fn, η, FP, escorregamento) | Rs, Rr, Xs, Xr, Xm estimados |
| IEEE Std 112-2017 | Ensaios a vazio + rotor bloqueado + carga nominal | Parâmetros com iteração fasorial de E1 |

---

## Aba Teoria — Estrutura

| Subaba | Conteúdo |
|---|---|
| 1 | Modelo dq0 — equações de estado e circuito equivalente |
| 2 | Análise de regime permanente — curva conjugado × velocidade |
| 3 | Desequilíbrio de tensão — componentes simétricas |
| 4 | MCSA — assinatura de corrente para diagnóstico |
| 5 | Frenagem elétrica — plugging e injeção de CC |
| 6 | Modelo de Krause — formulação algébrica de Te(s) |
| 7 | Estimador de Parâmetros — Nameplate e IEEE Std 112-2017 |
| 8 | Configuração, Experimentos e Manual de Uso |

---

## Repositório

- Branch principal: `master`
- Autor: Kevin · k.g.pinheiro.castro@gmail.com
