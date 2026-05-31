# Interactive Web Simulator (IWS)

A free, browser-based platform for dynamic simulation of electrical machines in engineering education. Covers dynamic modeling (Krause dq0 model), parameter estimation, fault analysis, and PDF report generation.

---

## Stack

- Python 3.9+
- Streamlit
- Plotly
- NumPy / SciPy
- ReportLab
- Schemdraw

---

## Installation and Usage

```bash
pip install -r requirements.txt
streamlit run IWS_UI.py
```

---

## Architecture

```
IWS_UI.py                          main orchestrator (page_config, tab routing)
├── ui/
│   ├── clean_view.py              "Article View" layout (sidebar, control panel)
│   ├── theory.py                  Theory tab components
│   ├── theory_interactive.py      interactive widgets for Theory tab
│   └── theme.py                   CSS theme system, color palette
├── ui_components/
│   ├── sim_config.py              TIM machine selector, parameters, presets
│   ├── sim_config_dc.py           DCM machine selector, parameters, presets
│   ├── sim_results.py             TIM results view (4 sub-tabs)
│   ├── sim_results_dc.py          DCM results view
│   ├── sim_runner.py              TIM simulation orchestration and cache
│   ├── sim_runner_dc.py           DCM simulation orchestration and cache
│   └── theory_view.py             Theory tab routing
└── core/
    ├── IWS_PY.py                  public facade (MachineParams, run_simulation)
    ├── solver.py                  LSODA integrator (8 TIM states, h ≤ 1/20f)
    ├── machine_model.py           dq0 model (Krause 1986)
    ├── sources.py                 voltage sources (sinusoidal, ramp, fault)
    ├── thermal.py                 thermal model (resistance + capacitance)
    ├── energy_analysis.py         energy analysis (Sankey, efficiency, losses)
    ├── harmonica_analysis.py      harmonic analysis and MCSA
    ├── sim_diagnostics.py         automated fault diagnostics
    ├── desequilibrio_falta.py     voltage unbalance and phase loss
    ├── param_estimator.py         parameter estimator (Nameplate and IEEE)
    ├── dc_machine_model.py        DCM model (sep/shunt/series × motor/gen)
    ├── dc_solver.py               DCM LSODA integrator (4 states)
    ├── dc_sources.py              DCM voltage sources
    ├── curva_tn.py                nominal torque-speed curve
    └── transforms.py              Park/Clarke transforms

viz/
├── plotly_charts.py               TIM interactive charts (zero-latency via Plotly frames)
├── plotly_charts_dc.py            DCM interactive charts
├── eqcircuit_plotter.py           interactive equivalent circuit
├── eqcircuit_plotter_dc.py        DCM equivalent circuit
├── pdf_report.py                  academic PDF (ReportLab)
├── pdf_report_v2.py               dashboard PDF
└── pdf_dc.py                      DCM PDF report
```

---

## Main Tabs

| Tab | Content |
|---|---|
| **Simulation (TIM)** | Machine configuration, experiment setup, execution, results (4 sub-tabs) |
| **Simulation (DCM)** | DC machine configuration, execution, dynamic analysis |
| **Theory** | 8 sub-tabs with theoretical concepts, interactive components, and usage manual |
| **Article View** | Clean layout optimized for figure capture in publications |

### TIM Simulation Sub-tabs

| Sub-tab | Content |
|---|---|
| Overview | Executive summary with health panel, KPIs, and synoptic charts |
| Dynamic Analysis | Waveform plots (currents, voltages, torque, speed, temperature) |
| Diagnostics | Automated anomaly detection, signature tables, and recommendations |
| Asset Management | Lifecycle analysis, efficiency, losses, and operational recommendations |

---

## Simulation Modes

### TIM (Three-Phase Induction Motor)
| Group | Modes | Notes |
|---|---|---|
| Starting | DOL, Y-Δ, Autotransformer, Soft-starter | Auto-zoom to 95% of ωr_sync |
| Steady-state | Load Pulse, Generator | — |
| Transient | Shutdown, Voltage Sag | — |

Optional perturbations (toggles): phase asymmetry, phase loss, broken bar.

### DCM (DC Machine)
- **Configurations:** Separately excited (motor/generator), Shunt (motor), Series (motor)
- **Modes:** DOL, Resistance, Plugging, Pulse, Generator, Field Weakening

---

## Features

- **Dynamic simulation** — Krause dq0 model, LSODA integrator, 8 state variables (TIM)
- **Parameter estimation** — Nameplate (NEMA MG-1) and IEEE Std 112-2017 with phasor iteration
- **Fault analysis** — voltage unbalance, phase loss, broken bar
- **MCSA** — stator current signature analysis for broken-bar diagnosis
- **Harmonic analysis** — FFT of currents and torque
- **Thermal analysis** — stator and rotor temperature evolution
- **Energy analysis** — power Sankey, efficiency, and losses
- **Electric braking** — plugging and DC injection modes
- **Automated diagnostics** — detection of 7+ post-simulation anomalies
- **Theory tab** — 8 sub-tabs with interactive components and usage manual
- **Health panel** — compact operational KPIs, status indicators, alerts
- **Academic PDF** — full report with figures, equations, and signatures
- **Dashboard PDF** — compact executive summary
- **Interactive visualization** — zero-latency Plotly charts via pre-computed frames
- **Interactive equivalent circuit** — dq0 diagram with slip sliders

---

## Parameter Estimation

| Method | Inputs | Output |
|---|---|---|
| Nameplate (NEMA MG-1) | Nameplate data (Pn, Vn, fn, η, PF, slip) | Estimated Rs, Rr, Xs, Xr, Xm |
| IEEE Std 112-2017 | No-load + locked-rotor + rated-load tests | Parameters with E1 phasor iteration |
| IEEE Std 113-1985 | DC + no-load + locked-rotor tests (DCM) | Ra, Rf, La, Lf |

---

## Theory Tab Structure

| Sub-tab | Content |
|---|---|
| 1 | dq0 Model — state equations and equivalent circuit |
| 2 | Steady-state analysis — torque-speed curve |
| 3 | Voltage unbalance — symmetrical components |
| 4 | MCSA — stator current signature for diagnostics |
| 5 | Electric braking — plugging and DC injection |
| 6 | Krause model — algebraic formulation of Te(s) |
| 7 | Parameter Estimator — Nameplate and IEEE Std 112-2017 |
| 8 | Configuration, Experiments, and Usage Manual |

---

## Repository

- **URL:** https://github.com/Kevinael/iws-english
- **Branch:** `main`
- **Author:** Kevin · k.g.pinheiro.castro@gmail.com
