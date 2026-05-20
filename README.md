# Infraestrutura Web de Simulação (IWS)

Simulador web interativo de máquinas de indução trifásica, desenvolvido como infraestrutura de pesquisa acadêmica. Cobre modelagem dinâmica (modelo dq0 de Krause), estimação de parâmetros, análise de falhas e geração de relatórios em PDF.

---

## Stack

- Python 3.9+
- Streamlit
- Plotly
- NumPy / SciPy
- ReportLab / fpdf2
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
IWS_UI.py                          orquestrador (page_config, roteamento de abas)
├── ui/clean_view.py               layout principal (sidebar, painel de controle)
├── ui/theory.py                   aba Teoria (8 subabas)
├── ui/theory_interactive.py       componentes interativos da aba Teoria
├── ui_components/sim_config.py    configuração de parâmetros e experimento
├── ui_components/sim_results.py   visualização de resultados e diagnóstico
├── ui_components/sim_runner.py    execução da simulação e cache
└── core/IWS_PY.py                 fachada pública (MachineParams, run_simulation)
    ├── core/solver.py             integrador LSODA (8 estados, h ≤ 1/20f)
    ├── core/machine_model.py      modelo dq0 (Krause 1986)
    ├── core/sources.py            fontes de tensão (senoidal, rampa, falta)
    ├── core/thermal.py            modelo térmico
    ├── core/energy_analysis.py    análise energética (Sankey, eficiência)
    ├── core/harmonica_analysis.py análise harmônica e MCSA
    ├── core/sim_diagnostics.py    diagnóstico automatizado de falhas
    ├── core/desequilibrio_falta.py desequilíbrio de tensão e falta de fase
    └── core/transforms.py         transformadas Park/Clarke

viz/
├── plotly_charts.py               gráficos interativos (zero-latência via frames)
├── pdf_report.py                  PDF acadêmico (ReportLab)
└── pdf_report_v2.py               PDF dashboard
```

---

## Modos de simulação

| Grupo        | Modos                                                  |
|--------------|--------------------------------------------------------|
| Partida      | DOL, Y-Δ, Autotransformador, Soft-starter              |
| Regime       | Pulso de Carga, Gerador                                |
| Transitório  | Desligamento, Sag de Tensão                            |

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
- **Diagnóstico automatizado** — detecção de anomalias pós-simulação
- **Aba Teoria** — 8 subabas com componentes interativos e manual de uso
- **PDF Acadêmico** — relatório completo com figuras e equações
- **PDF Dashboard** — resumo executivo compacto
- **Visualização interativa** — gráficos Plotly zero-latência via frames pré-calculados

---

## Aba Teoria

| Subaba | Conteúdo                                                            |
|--------|---------------------------------------------------------------------|
| 1      | Modelo dq0 — equações de estado e circuito equivalente              |
| 2      | Análise de regime permanente — curva conjugado × velocidade         |
| 3      | Desequilíbrio de tensão — componentes simétricas                    |
| 4      | MCSA — assinatura de corrente para diagnóstico                      |
| 5      | Frenagem elétrica — plugging e injeção de CC                        |
| 6      | Modelo de Krause — formulação algébrica de Te(s)                    |
| 7      | Estimador de Parâmetros — Nameplate e IEEE Std 112-2017             |
| 8      | Config/Experimentos + Manual de Uso                                 |

---

## Estimação de parâmetros

| Método              | Entradas                                                    | Saída                              |
|---------------------|-------------------------------------------------------------|------------------------------------|
| Nameplate (NEMA MG-1) | Placa de identificação (Pn, Vn, fn, η, FP, escorregamento)  | Rs, Rr, Xs, Xr, Xm estimados       |
| IEEE Std 112-2017   | Ensaios a vazio + rotor bloqueado + carga nominal           | Parâmetros com iteração fasorial de E1 |

---

## Repositório

- Branch principal: `master`
- Autor: Kevin · k.g.pinheiro.castro@gmail.com
