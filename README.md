# IWS — Interactive Web Simulator for Electrical Machines

**IWS** is an interactive web-based simulator for three-phase induction machines (TIM) and DC machines (DCM), built as academic research infrastructure. It covers dynamic modelling, parameter estimation, fault analysis, and PDF report generation.

| | |
|---|---|
| **Stack** | Python 3.9+ · Streamlit · Plotly · NumPy / SciPy · ReportLab · schemdraw |
| **Repository** | https://github.com/Kevinael/iws-english (branch `master`) |
| **Run** | `streamlit run IWS_UI.py` |

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Project Structure](#project-structure)
4. [Module Reference](#module-reference)
   - [core/](#core--physics-engine)
   - [ui/](#ui--views-and-theme)
   - [ui_components/](#ui_components--streamlit-widgets)
   - [viz/](#viz--charts-and-reports)
   - [utils/](#utils--utilities)
   - [scripts/](#scripts--figure-generation)
   - [analysis/](#analysis--comparative-studies)
   - [tests/](#tests--test-suite)
   - [data/](#data--reference-data)
5. [Session State Contract](#session-state-contract)
6. [Simulation Flow](#simulation-flow)
7. [Simulation Modes](#simulation-modes)
8. [Parameter Estimation](#parameter-estimation)
9. [How to Extend](#how-to-extend)
10. [Running Tests](#running-tests)
11. [Commit Conventions](#commit-conventions)
12. [Technical References](#technical-references)

---

## Overview

IWS provides a browser-based interface (via Streamlit) for:

- **Dynamic simulation** — 8-state Krause dq0 model (TIM) and 4-state model (DCM), integrated via LSODA.
- **Eight TIM operating modes** — four starting methods, steady-state regimes, generator, shutdown, and voltage sag.
- **Six DCM configurations** — separately excited, shunt, and series, in motor and generator variants, with multiple starting modes.
- **Parameter estimation** — Nameplate (NEMA MG-1) and IEEE Std 112-2017 with phasor iteration for TIM; nameplate and lab-test estimation for DCM.
- **Fault analysis** — voltage unbalance, phase loss, and broken rotor bar.
- **Motor Current Signature Analysis (MCSA)** — FFT-based broken-bar diagnostics.
- **Thermal analysis** — first-order stator and rotor temperature evolution.
- **Energy analysis** — Sankey power flow, efficiency, THD, and annual cost estimation.
- **Automated diagnostics** — post-simulation anomaly detection with severity classification.
- **Theory tab** — 8 interactive sub-tabs for TIM theory + 7 sub-tabs for DCM theory.
- **PDF reports** — academic (equations + full curves) and industrial (KPIs + diagnostics) styles.
- **Interactive charts** — Plotly with pre-computed frames for zero-latency rendering.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Kevinael/iws-english.git
cd iws-english

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run IWS_UI.py
```

The app opens at `http://localhost:8501`.

To clear bytecode cache and restart with file polling (Windows):

```bat
rodar.bat
```

---

## Project Structure

```
IWS - English/
│
├── IWS_UI.py                    Entry point — Streamlit orchestrator
│
├── core/                        Physics engine (TIM and DCM models)
│   ├── IWS_PY.py                Public facade (MachineParams, run_simulation, build_fns)
│   ├── machine_model.py         Krause dq0 model — MachineParams + ODE RHS
│   ├── solver.py                LSODA integrator + post-processing
│   ├── sources.py               Voltage/torque excitation factories
│   ├── transforms.py            Clarke-Park transforms (abc -> dq)
│   ├── thermal.py               First-order thermal model (Rth, Cth)
│   ├── energy_analysis.py       Steady-state energy metrics (efficiency, THD, cost)
│   ├── harmonica_analysis.py    FFT spectra + MCSA
│   ├── sim_diagnostics.py       Automatic anomaly detection
│   ├── desequilibrio_falta.py   Voltage unbalance / phase loss [UNDER DEVELOPMENT]
│   ├── param_estimator.py       TIM parameter estimator (Nameplate + IEEE Std 112)
│   ├── curva_tn.py              Torque-speed curve + power flow
│   ├── dc_machine_model.py      DCM model — DCMachineParams + ODE RHS
│   ├── dc_solver.py             LSODA integrator for DCM
│   ├── dc_sources.py            DCM excitation factories
│   └── dc_estimator.py          DCM parameter estimator
│
├── ui/                          Views and theme system
│   ├── theme.py                 Dark/light colour palette + global CSS
│   ├── clean_view.py            Article screenshot view (HTML tables)
│   ├── theory.py                TIM Theory tab orchestrator (8 sub-tabs)
│   ├── theory_interactive.py    TIM Theory interactive Plotly components
│   ├── theory_dc.py             DCM Theory tab (7 sub-tabs)
│   └── theory_dc_interactive.py DCM Theory interactive Plotly components
│
├── ui_components/               Streamlit widget modules
│   ├── sim_config.py            TIM machine selector + experiment config
│   ├── sim_config_dc.py         DCM machine selector + experiment config
│   ├── sim_results.py           TIM result tabs (KPIs, waveforms, diagnostics, PDF)
│   ├── sim_results_dc.py        DCM result tabs
│   ├── sim_runner.py            TIM simulation orchestrator + cache
│   ├── sim_runner_dc.py         DCM simulation orchestrator + cache
│   └── theory_view.py           Re-export wrapper for Theory tab
│
├── viz/                         Visualisation and report generation
│   ├── plotly_charts.py         TIM interactive Plotly charts
│   ├── plotly_charts_dc.py      DCM interactive Plotly charts
│   ├── eqcircuit_plotter.py     TIM equivalent circuit (schemdraw)
│   ├── eqcircuit_plotter_dc.py  DCM equivalent circuits (schemdraw)
│   ├── eqcircuit_plotter_dc_v2.py  DCM circuit variant [EXPERIMENTAL]
│   ├── pdf_commons.py           Shared PDF utilities (SimBlock, helpers)
│   ├── pdf_academico.py         Academic PDF report (TIM)
│   ├── pdf_industrial.py        Industrial PDF report (TIM)
│   ├── pdf_report.py            Legacy PDF generator [DEPRECATED]
│   ├── pdf_report_v2.py         PDF v2 — IEEE-formal + dashboard [TRANSITIONAL]
│   └── pdf_dc.py                DCM PDF report
│
├── utils/                       Utility scripts
│   ├── text_utils.py            LaTeX to Unicode converter (_strip_latex)
│   ├── gen_okoro_comparison.py  Okoro (2008) DCM validation figures
│   └── _gen_theory_imgs.py      Theory tab PNG generator (schemdraw)
│
├── scripts/                     Article figure generation
│   ├── gen_figures.py           Overleaf figures — TIM 60 Hz DOL
│   ├── gen_resultados_web.py    Overleaf figures — TIM 50 Hz
│   └── demo_potencias.py        Steady-state power metrics demo
│
├── analysis/                    Comparative studies
│   └── compare_dc_ac_dol.py     TIM vs. DCM DOL transient overlay
│
├── tests/                       pytest test suite
│   ├── conftest.py              Shared fixtures (mp_3hp, mp_50hp, mp_2250hp)
│   ├── test_curva_tn.py         Torque-speed curve tests
│   ├── test_energy_analysis.py  Energy metrics tests
│   ├── test_harmonica_analysis.py  FFT / MCSA tests
│   ├── test_machine_model.py    MachineParams init and derived fields
│   ├── test_param_estimator.py  TIM parameter estimator tests
│   ├── test_physics.py          Physical invariants (torque balance, energy)
│   ├── test_sim_diagnostics.py  Automated diagnostics tests
│   ├── test_sources.py          Excitation source tests
│   ├── test_thermal.py          Thermal model tests
│   ├── test_transforms.py       Clarke-Park transform tests
│   ├── test_dc_phase1_validation.py  DCM solver validation vs. dcmei.sce
│   └── debug/
│       ├── test_deseq_ui.py     Manual Streamlit test for unbalance UI
│       └── debug_rms.py         RMS value inspection for debugging
│
├── data/
│   └── examples/
│       └── sep_motor_DOL.csv    Reference DCM (sep. exc.) DOL simulation output
│
├── assets/
│   └── circuits_dc/             DCM circuit diagram PNGs (sep, shunt, series)
│
├── overleaf/
│   └── imagens/                 Generated figures for the associated article
│
├── imgs/                        Static images for the Theory tab
│
├── requirements.txt             Python package dependencies
├── rodar.bat                    Windows launcher (clears __pycache__, starts app)
├── SME - IAS.code-workspace     VS Code workspace
├── iws-english.code-workspace   VS Code workspace (alternative root)
├── iws-mcc-integration.code-workspace  VS Code workspace (DCM integration)
└── CLAUDE.md                    Claude Code project instructions
```

---

## Module Reference

### `core/` — Physics Engine

#### `core/IWS_PY.py` — Public Facade
The single import point for all simulation code. Downstream modules (`ui_components`, `scripts`, `tests`) should import from here rather than from the internal modules directly.

```python
from core.IWS_PY import MachineParams, run_simulation, build_fns
```

| Symbol | Type | Description |
|---|---|---|
| `MachineParams` | dataclass | All TIM parameters (electrical, mechanical, thermal) |
| `run_simulation(mp, tmax, h, voltage_fn, torque_fn, **kwargs)` | function | Runs the ODE and returns a result dict |
| `build_fns(cfg, mp)` | function | Returns `(voltage_fn, torque_fn, t_events)` for an experiment config |

#### `core/machine_model.py` — Krause dq0 Model
Implements the standard Krause (1986) qd0 formulation in the arbitrary reference frame. `MachineParams` has 30+ fields; `__post_init__` computes derived inductances (`Lm`, `Lls`, `Llr`) and reactances (`Xls_a`, `Xlr_a`, `Xm_a`).

Key fields:

| Field | Unit | Description |
|---|---|---|
| `Vl` | V | Line-to-line RMS voltage |
| `f` | Hz | Supply frequency |
| `p` | — | Number of poles |
| `Rs`, `Rr` | Ohm | Stator/rotor resistance |
| `Xls`, `Xlr`, `Xm` | Ohm | Leakage and magnetising reactances |
| `Rfe` | Ohm | Core loss resistance |
| `J` | kg·m² | Moment of inertia |
| `B` | N·m·s | Viscous friction |
| `Rth_e`, `Cth_e` | K/W, J/K | Stator thermal resistance/capacitance |

#### `core/solver.py` — LSODA Integrator
Wraps `scipy.integrate.solve_ivp` with `method='LSODA'` and a maximum step constraint `h <= 1/(20f)` for numerical stability. Post-processing reconstructs:

- Phase currents `ias`, `ibs`, `ics` (abc frame)
- Voltages `Va`, `Vb`, `Vc`
- Steady-state RMS values, active/reactive/apparent power
- Efficiency, power factor, THD

Steady-state detection uses a sliding-window torque variance criterion (`SS_TOL`, `MIN_SS_CYCLES`).

#### `core/sources.py` — Excitation Factories
`build_fns(cfg, mp)` reads `cfg['exp_type']` and returns callables:

| Mode key | Voltage profile | Torque profile |
|---|---|---|
| `dol` | Full voltage from t=0 | Constant or step |
| `estrela_triangulo` | Reduced (Y) then full (delta) | Constant |
| `autotransformador` | Reduced then full | Constant |
| `soft_starter` | Linear ramp | Constant |
| `pulso_carga` | Full | Pulse at `t_carga` |
| `gerador` | Full | Drive torque (negative load) |
| `desligamento` | Full then zero | Constant |
| `sag` | Full with rectangular sag | Constant |

#### `core/dc_machine_model.py` — DCM Model
`DCMachineParams` stores armature (`Ra`, `La`), field (`Rf`, `Lf` or `Lse`), mechanical (`J`, `B`), and load parameters. `_make_rhs_dc` returns the 4-state ODE RHS switching equations by `params.config`:

| Config | States | Field equation |
|---|---|---|
| `sep_motor` / `sep_gen` | wr, ia, if | Separate field circuit |
| `shunt_motor` / `shunt_gen` | wr, ia | Parallel field (Vf = Va) |
| `series_motor` | wr, ia | Series field (if = ia) |

---

### `ui/` — Views and Theme

#### `ui/theme.py`
Central theming module. Call `_palette(dark=True/False)` to get a colour dict with keys `surface`, `border`, `text`, `muted`, `accent`, etc. Call `apply_css(dark)` once per page load.

```python
from ui.theme import _palette, apply_css, REF_COLORS, REF_DASHES
palette = _palette(dark=st.session_state["dark_mode"])
apply_css(dark=st.session_state["dark_mode"])
```

#### `ui/theory.py` + `ui/theory_interactive.py`
`theory.py` lays out the 8 TIM sub-tabs and delegates to `render_*` functions in `theory_interactive.py`. Interactive components use Plotly with real-time slider updates via `st.session_state`.

Sub-tab routing:

| Sub-tab | Function in theory_interactive.py |
|---|---|
| dq0 model | `render_park_dinamico` |
| Steady state | `render_boucherot`, `render_zonas_operacao` |
| Unbalance | `render_fasorial_desequilibrio` |
| MCSA | `render_mcsa` |
| Braking | `render_comparador_frenagem` |
| Krause | `render_blocos_krause` |
| Estimator | inline in theory.py |
| Manual | inline in theory.py |

---

### `ui_components/` — Streamlit Widgets

#### `ui_components/sim_config.py`
Key exports:

| Symbol | Description |
|---|---|
| `MACHINES` | Dict of named motor presets |
| `_WK` | Logical field to widget key mapping |
| `_PRESETS` | Named preset configurations |
| `VARIABLE_CATALOG` | Full catalogue of plottable variables |
| `render_machine_selector()` | Machine selection UI |
| `render_machine_params()` | Physical parameter inputs |
| `render_experiment_config()` | Experiment type + variable selection |

#### `ui_components/sim_runner.py`
`execute_simulation_flow()` flow:
1. Read `MachineParams` from `session_state`
2. Call `calc_tmax_auto(cfg, mp)` for automatic time limit
3. Call `run_simulation(mp, tmax, h, voltage_fn, torque_fn)`
4. Write result dict to `session_state["sim_result"]`

`calc_tmax_auto` uses motor inertia J and nominal speed to estimate the time to reach 95% synchronous speed, with mode-specific overrides.

#### `ui_components/sim_results.py`
Four sub-tabs rendered by `render_results(res, mp, cfg, ...)`:

| Sub-tab | Content |
|---|---|
| **Overview** | KPI cards, health panel, synoptic charts |
| **Dynamic Analysis** | Waveform selector (currents, voltages, torque, speed, temperature) |
| **Diagnostics** | Automated anomaly table, MCSA FFT, signature recommendations |
| **Asset Management** | Lifecycle analysis, efficiency, losses, annual cost |

PDF download buttons call `generate_academico()` or `generate_industrial()` from `viz/`.

---

### `viz/` — Charts and Reports

#### `viz/plotly_charts.py`
All chart builders return a `go.Figure`. Pre-computed frames (`fig.frames`) enable zero-latency animation in Streamlit.

| Function | Description |
|---|---|
| `build_fig_stacked(res, var_keys, dark, ...)` | Vertically stacked traces |
| `build_fig_sidebyside(res, var_keys, dark, ...)` | Two-column layout |
| `build_fig_overlay(res, var_keys, dark, ...)` | All traces on one axis |

Theme helpers `_plot_theme(dark)` and `_colors(dark)` are imported by `plotly_charts_dc.py` and `harmonica_analysis.py`.

#### `viz/pdf_commons.py`
`SimBlock` is an fpdf2 base class. Helper functions:

| Function | Description |
|---|---|
| `safe_text(s)` | Strips non-latin-1 characters |
| `fmt_power(W)` | Formats W/kW/MW intelligently |
| `embed_fig(pdf, fig, w, h)` | Inserts a matplotlib figure |
| `build_circuit_bytes(mp, dark)` | Renders circuit to PNG bytes |
| `cell_rich(pdf, text, **kwargs)` | Rich-formatted table cell |

#### PDF Report Variants

| Module | Style | Status |
|---|---|---|
| `pdf_academico.py` | Academic (equations + full curves) | **Active** |
| `pdf_industrial.py` | Industrial (KPIs + diagnostics + economics) | **Active** |
| `pdf_dc.py` | DCM technical report | **Active** |
| `pdf_report_v2.py` | IEEE-formal + dashboard dual mode | Transitional |
| `pdf_report.py` | Original single-style | Legacy |

---

### `utils/` — Utilities

| File | Purpose |
|---|---|
| `text_utils.py` | `_strip_latex(s)` converts `$\omega_r$` to plain Unicode for axis labels |
| `gen_okoro_comparison.py` | Validation figures vs. Okoro et al. (2008) |
| `_gen_theory_imgs.py` | Regenerates circuit PNG images for the Theory tab |

---

### `scripts/` — Figure Generation

Standalone scripts — not imported by the app. Run from the project root:

```bash
python scripts/gen_figures.py          # TIM 60 Hz figures -> overleaf/imagens/
python scripts/gen_resultados_web.py   # TIM 50 Hz figures -> overleaf/imagens/
python scripts/demo_potencias.py       # Print steady-state power metrics
```

Output path is resolved relative to the project root via `pathlib` — no hardcoded user paths.

---

### `analysis/` — Comparative Studies

| File | Purpose |
|---|---|
| `compare_dc_ac_dol.py` | Overlays TIM vs. DCM DOL transients (ia, Te, wm) with matched mechanical parameters |
| `dc_ac_comparative.csv` | Reference output from above comparison |

---

### `tests/` — Test Suite

```bash
pytest tests/ -v                                    # full suite
pytest tests/test_physics.py -v                     # single file
pytest tests/ --cov=core --cov-report=term-missing  # with coverage
```

| File | What it tests |
|---|---|
| `conftest.py` | Fixtures: 3 HP, 50 HP, 2250 HP motors (Krause 1986) |
| `test_machine_model.py` | MachineParams init, derived inductances, reactances |
| `test_sources.py` | Voltage/torque callables for each experiment mode |
| `test_transforms.py` | Clarke-Park roundtrip accuracy |
| `test_thermal.py` | Rth/Cth estimation, dTemp_dt correctness |
| `test_energy_analysis.py` | Metrics with synthetic sinusoidal results |
| `test_harmonica_analysis.py` | FFT peak detection |
| `test_curva_tn.py` | Torque-speed curve keys and length |
| `test_param_estimator.py` | Nameplate and IEEE parameter estimates |
| `test_physics.py` | Torque balance invariant at multiple load points |
| `test_sim_diagnostics.py` | Diagnostic rule triggering |
| `test_dc_phase1_validation.py` | DCM LSODA solver vs. Scilab dcmei.sce reference |

#### `tests/debug/` — Manual Debug Tools
Not run by pytest automatically.

| File | Purpose |
|---|---|
| `test_deseq_ui.py` | Streamlit page to test the unbalance/fault module UI |
| `debug_rms.py` | Displays RMS values of all state variables at steady state |

---

### `data/` — Reference Data

| File | Description |
|---|---|
| `data/examples/sep_motor_DOL.csv` | Reference DCM (separately excited) DOL transient — columns: t, ia, ifd, wm, Te, Ea |

---

## Session State Contract

| Key | Type | Set by | Read by |
|---|---|---|---|
| `selected_machine` | `"mit"` or `"dc"` | `IWS_UI.py` | All ui_components |
| `dark_mode` | `bool` | `IWS_UI.py` | `ui.theme`, chart builders |
| `experiment_mode` | `bool` | `sim_config.py` | `sim_config.py` (locks inputs) |
| `sim_result` | `dict` | `sim_runner.py` | `sim_results.py`, `clean_view.py` |
| `dc_sim_result` | `dict` | `sim_runner_dc.py` | `sim_results_dc.py` |
| `ref_list` | `list[str]` | `sim_results.py` | `viz/pdf_*.py` |
| `decimals` | `int` | `IWS_UI.py` | `sim_results.py` |

`sim_result` dict keys (TIM):

| Key | Shape | Description |
|---|---|---|
| `t` | `(N,)` | Time vector (s) |
| `ias`, `ibs`, `ics` | `(N,)` | Stator phase currents (A) |
| `ids`, `iqs` | `(N,)` | d/q stator currents (A) |
| `idr`, `iqr` | `(N,)` | d/q rotor currents (A) |
| `wr` | `(N,)` | Rotor angular speed (rad/s) |
| `Te` | `(N,)` | Electromagnetic torque (N·m) |
| `Va`, `Vb`, `Vc` | `(N,)` | Phase voltages (V) |
| `Ts` | `(N,)` | Stator temperature (°C) — if thermal enabled |
| `ss_idx` | `int` | Index of steady-state onset |
| `ss` | `dict` | Steady-state scalar metrics |

---

## Simulation Flow

### TIM

```
User inputs (sim_config.py)
         |
         v
MachineParams + cfg dict
         |
         v
sim_runner.py: execute_simulation_flow()
  +-- calc_tmax_auto(cfg, mp)
  +-- build_fns(cfg, mp)  ->  (voltage_fn, torque_fn, t_events)
  +-- run_simulation(mp, ...)  ->  result dict
              |
              v
          solver.py: _solve()
            +-- scipy solve_ivp LSODA
            +-- _reconstruct_currents()
            +-- _voltages_vectorized()
            +-- _detect_steady_state()
            +-- _compute_steady_state()
            +-- _compute_thermal()
         |
         v
session_state["sim_result"]
         |
         v
sim_results.py: render_results()
  +-- Overview     <- energy_analysis.py
  +-- Dynamic      <- plotly_charts.py
  +-- Diagnostics  <- sim_diagnostics.py, harmonica_analysis.py
  +-- Assets       <- energy_analysis.py
```

### DCM

```
User inputs (sim_config_dc.py)
         |
         v
DCMachineParams + cfg dict
         |
         v
sim_runner_dc.py: execute_simulation_flow_dc()
  +-- make_voltage_fn_dc(mode, params, cfg)
  +-- make_torque_fn_dc(mode, params, cfg)
  +-- run_simulation_dc(params, tmax, h, ...)  ->  result dict
              |
              v
          dc_solver.py
            +-- scipy solve_ivp LSODA
            +-- reconstruct Ea, Pem, efficiency
         |
         v
session_state["dc_sim_result"]
         |
         v
sim_results_dc.py: render_results_dc()
```

---

## Simulation Modes

### TIM

| Group | Mode key | Description |
|---|---|---|
| Starting | `dol` | Direct-on-line |
| Starting | `estrela_triangulo` | Star-delta |
| Starting | `autotransformador` | Auto-transformer reduced voltage |
| Starting | `soft_starter` | Linear voltage ramp |
| Steady state | `pulso_carga` | Load torque pulse |
| Steady state | `gerador` | Generator operation |
| Transient | `desligamento` | Power-off coast-down |
| Transient | `sag` | Voltage sag (rectangular) |

Optional perturbations (toggle independently):

| Perturbation | Parameter |
|---|---|
| Phase asymmetry | `deseq_a`, `t_deseq` |
| Phase loss | `falta_fase`, `t_falta` |
| Broken rotor bar | `broken_bar_severity`, `t_broken_bar` |

### DCM

| Config | Mode | Description |
|---|---|---|
| sep_motor | `dol_dc` | Direct-on-line (sep. excited) |
| sep_motor | `resistencia_dc` | Armature resistance starting |
| sep_motor | `pulso_dc` | Load torque pulse |
| shunt_motor | `dol_dc` | Direct-on-line (shunt) |
| series_motor | `dol_dc` | Direct-on-line (series) |
| sep_gen | `gerador_dc` | Generator operation |

---

## Parameter Estimation

### TIM — Nameplate (NEMA MG-1)

```python
from core.param_estimator import estimate_params

params = estimate_params(
    Vl=220,      # V line-to-line
    f=60,        # Hz
    p=4,         # poles
    Pn=5500,     # W rated power
    N_nom=1750,  # rpm rated speed
    rend=0.88,   # efficiency at rated load
    fp=0.85,     # power factor at rated load
    Ip_In=6.5,   # locked-rotor to rated current ratio
    Tp_Tn=1.5,   # locked-rotor to rated torque ratio
    is_delta=False
)
# Returns dict: Rs, Rr, Xls, Xlr, Xm
```

### TIM — IEEE Std 112-2017

```python
from core.param_estimator import estimate_params_ieee_tests

params = estimate_params_ieee_tests(
    V_dc, I_dc,                    # DC resistance test
    is_delta,                      # winding connection
    Vl_nl, I_nl, P_nl, f_nl,      # no-load test
    Vl_lr, I_lr, P_lr, f_lr,      # locked-rotor test
    Pfw,                           # friction + windage losses
    split=0.5,                     # stator/rotor leakage split
    Xls_frac=0.5
)
```

### DCM — Nameplate

```python
from core.dc_estimator import estimate_dc_nameplate

params = estimate_dc_nameplate(
    Pn_W=5000, Vn=220, nn_rpm=1750, eta=0.88, excitation="sep"
)
# Returns dict: Ra, La, Rf, Lf, Ke, J
```

---

## How to Extend

### Add a New TIM Simulation Mode

1. **`core/sources.py`** — add a `voltage_<mode>(t, mp, cfg)` function and register it in the `build_fns` dispatch dict.
2. **`core/solver.py`** — if the mode requires special integration logic (e.g. mid-simulation parameter change), add a branch in `_solve`.
3. **`ui_components/sim_config.py`** — add the mode key to the `exp_type` selectbox options.
4. **`ui_components/sim_runner.py`** — add a `tmax` heuristic in `calc_tmax_auto` for the new mode.
5. **`tests/test_sources.py`** — add a test case for the new source callable.

### Add a New DCM Simulation Mode

1. **`core/dc_sources.py`** — add a voltage/torque factory for the new mode.
2. **`ui_components/sim_config_dc.py`** — add the mode to the selectbox.
3. **`ui_components/sim_runner_dc.py`** — add the dispatch case.

### Add a New Theory Sub-tab (TIM)

1. **`ui/theory_interactive.py`** — create `render_<name>(mp, dark)`.
2. **`ui/theory.py`** — add a `st.tab` entry and call `render_<name>`.

### Add a New Theory Sub-tab (DCM)

1. **`ui/theory_dc_interactive.py`** — create `render_<name>(dark)`.
2. **`ui/theory_dc.py`** — add a `st.tab` entry and call `render_<name>`.

### Add a New PDF Report Style

1. **`viz/`** — create `pdf_<style>.py`, import helpers from `pdf_commons.py`.
2. Define `generate_<style>(exp_label, mp, res, ...) -> bytes`.
3. **`ui_components/sim_results.py`** — add a download button calling the new generator.

### Add a New Plotly Chart

1. **`viz/plotly_charts.py`** — add `build_fig_<layout>(res, var_keys, dark, ...)`.
2. **`ui_components/sim_results.py`** — call the new builder in the appropriate sub-tab.

### Add a New Machine Type (e.g. PMSM)

1. **`core/`** — create `pmsm_model.py`, `pmsm_solver.py`, `pmsm_sources.py`.
2. **`ui_components/`** — create `sim_config_pmsm.py`, `sim_results_pmsm.py`, `sim_runner_pmsm.py`.
3. **`viz/`** — create `plotly_charts_pmsm.py`, `pdf_pmsm.py`.
4. **`IWS_UI.py`** — add a new tab and route `selected_machine == "pmsm"`.
5. **`tests/`** — add fixtures and test files.

### Activate Voltage Unbalance / Phase Loss

`core/desequilibrio_falta.py` is implemented but disabled. To activate:

1. Integrate `render_desequilibrio_ui()` in `ui_components/sim_config.py`.
2. Pass unbalance parameters through `MachineParams` or directly to `run_simulation`.
3. Remove the `UNDER DEVELOPMENT` note from the module docstring.

---

## Running Tests

```bash
# Full suite
pytest tests/ -v

# Single module
pytest tests/test_physics.py -v

# With coverage
pytest tests/ --cov=core --cov-report=term-missing
```

### Adding a Test

1. Add `test_<behaviour>()` to the appropriate `tests/test_*.py` file.
2. Use fixtures from `conftest.py` (`mp_3hp`, `mp_50hp`, `mp_2250hp`) for TIM parameter sets.
3. For DCM tests, instantiate `DCMachineParams` directly or add a new fixture to `conftest.py`.

Do **not** place automated tests in `tests/debug/` — that folder is for manual inspection only.

---

## Commit Conventions

Format: `type: short description` (under 72 characters).

| Type | When to use |
|---|---|
| `feat:` | New user-visible feature |
| `fix:` | Bug fix |
| `refactor:` | Code restructure with no behaviour change |
| `chore:` | Build, deps, tooling |
| `docs:` | Documentation only |
| `test:` | Tests only |

Examples:
```
feat: add compound DCM configuration to dc_machine_model
fix: clamp LSODA max step to 1/20f for high-frequency stability
refactor: extract _compute_steady_state from solver._solve
docs: update README with PMSM extension guide
```

- Identity: Kevin
- No `Co-Authored-By` lines.
- For high-impact changes (50+ lines, tab restructuring): commit before the change.

---

## Technical References

| Reference | Used in |
|---|---|
| Krause, P.C. (1986). *Analysis of Electric Machinery*. McGraw-Hill. | `core/machine_model.py`, `core/solver.py` |
| IEEE Std 112-2017. *IEEE Standard Test Procedure for Polyphase Induction Motors and Generators*. | `core/param_estimator.py` |
| NEMA MG-1. *Motors and Generators*. | `core/param_estimator.py` |
| Okoro, O.I. (2008). *Steady and Transient States Thermal Analysis*. | `utils/gen_okoro_comparison.py` |
| Fitzgerald, A.E., Kingsley, C., Umans, S.D. (2003). *Electric Machinery*. 6th ed. McGraw-Hill. | `core/curva_tn.py` |
