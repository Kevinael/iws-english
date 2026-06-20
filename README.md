# IWS — Interactive Web Simulator for Electrical Machines

**IWS** is an interactive web-based simulator for three-phase induction machines (TIM/MIT) and DC machines (DCM/MCC), built as academic research infrastructure. It covers dynamic modelling, parameter estimation, fault analysis, and PDF report generation.

| | |
|---|---|
| **Stack** | Python 3.9+ · Streamlit · Plotly · NumPy / SciPy · fpdf2 · schemdraw |
| **Repository** | https://github.com/Kevinael/iws-english |
| **Run (web app)** | `streamlit run IWS_UI.py` |
| **Run (headless)** | `from core.tim.facade import run_simulation` — see [ARCHITECTURE_HEADLESS.md](ARCHITECTURE_HEADLESS.md) |

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Module Reference](#module-reference)
6. [Session State Contract](#session-state-contract)
7. [Simulation Flow](#simulation-flow)
8. [Simulation Modes](#simulation-modes)
9. [Parameter Estimation](#parameter-estimation)
10. [How to Extend](#how-to-extend)
11. [Running Tests](#running-tests)
12. [Commit Conventions](#commit-conventions)
13. [Technical References](#technical-references)

---

## Overview

IWS provides a browser-based interface (via Streamlit) for:

- **Dynamic simulation** — 8-state Krause dq0 model (TIM) and 4-state model (DCM), integrated via LSODA.
- **Eight TIM operating modes** — four starting methods, steady-state regimes, generator, shutdown, and voltage sag.
- **Six DCM configurations** — separately excited, shunt, and series, in motor and generator variants, with multiple starting modes.
- **Parameter estimation** — Nameplate (NEMA MG-1) and IEEE Std 112-2017 with phasor iteration for TIM; nameplate and lab-test (IEEE 113) estimation for DCM.
- **Fault analysis** — voltage unbalance, phase loss, and broken rotor bar.
- **Motor Current Signature Analysis (MCSA)** — FFT-based broken-bar diagnostics.
- **Energy analysis** — Sankey power flow, efficiency, THD, and annual cost estimation.
- **Automated diagnostics** — post-simulation anomaly detection with severity classification.
- **Theory tab** — 8 interactive sub-tabs for TIM theory + sub-tabs for DCM theory.
- **PDF reports** — academic (equations + full curves) and industrial (KPIs + diagnostics) styles.
- **Interactive charts** — Plotly with pre-computed frames for zero-latency rendering.

### Headless / library mode

The physics engine (`core/`) is **fully decoupled from Streamlit**: it can be imported and run without the web framework, for use in notebooks, CI, batch scripts, or an alternative UI. See [ARCHITECTURE_HEADLESS.md](ARCHITECTURE_HEADLESS.md) for the full explanation and verified examples.

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

To clear bytecode cache and restart with file polling (Windows): `rodar.bat`.

**Dependencies** (`requirements.txt`): numpy, scipy, matplotlib, streamlit, plotly, schemdraw, fpdf2, kaleido, jinja2.

---

## Architecture

IWS is organised in **two layers** with a single-direction dependency: the UI depends on the core, never the reverse.

```
┌──────────────────────────────────────────────────────────┐
│  UI LAYER  (depends on Streamlit)                          │
│  IWS_UI.py · ui/ · ui_components/ · viz/                    │
└───────────────────────────┬──────────────────────────────┘
                            │ imports and calls (single arrow)
                            ▼
┌──────────────────────────────────────────────────────────┐
│  CORE LAYER  (ZERO Streamlit)                              │
│  core/tim/ · core/dc/ · core/transforms · core/constants   │
│  params in  →  NumPy arrays out                            │
└──────────────────────────────────────────────────────────┘
```

Each machine type exposes a **stable public facade**:

- `core.tim.facade` — `MachineParams`, `run_simulation`, `build_fns`
- `core.dc.facade` — `DCMachineParams`, `run_simulation_dc`, `make_voltage_fn_dc`, `make_torque_fn_dc`, `estimate_dc_nameplate`, `estimate_dc_tests`

Machine routing in `IWS_UI.py` is driven by a **`_MACHINE_REGISTRY`** (`dict[str, _MachineSpec]`) — adding a new machine means registering a spec, not editing if/elif branches.

---

## Project Structure

```
IWS - English/
│
├── IWS_UI.py                    Entry point — Streamlit orchestrator + _MACHINE_REGISTRY
│
├── core/                        Physics engine — ZERO Streamlit
│   ├── transforms.py            Clarke-Park transforms (abc <-> dq)
│   ├── constants.py             Physical constants + session defaults
│   ├── session_schema.py        TypedDicts for session_state keys
│   │
│   ├── tim/                     Three-phase induction machine (MIT)
│   │   ├── facade.py            Public API: MachineParams, run_simulation, build_fns
│   │   ├── machine_model.py     Krause dq0 model — MachineParams + ODE RHS
│   │   ├── solver.py            LSODA integrator + post-processing
│   │   ├── sources.py           Voltage/torque excitation factories (build_fns)
│   │   ├── fault_model.py       PURE fault physics (unbalance, broken bar)
│   │   ├── thermal.py           First-order thermal model (Rth, Cth)
│   │   ├── energy_analysis.py   Steady-state energy metrics (efficiency, THD, cost)
│   │   ├── harmonic_analysis.py FFT spectra + MCSA (build_fig_fft)
│   │   ├── diagnostics.py       Automatic anomaly detection (generate_insights)
│   │   ├── param_estimator.py   Nameplate (NEMA) + IEEE Std 112 estimators
│   │   ├── torque_speed.py      Torque-speed curve + power flow
│   │   └── fft_utils.py         Shared FFT helper
│   │
│   └── dc/                      DC machine (MCC)
│       ├── facade.py            Public API: DCMachineParams, run_simulation_dc, ...
│       ├── machine_model.py     DCM model — DCMachineParams + ODE RHS (6 configs)
│       ├── solver.py            LSODA integrator for DCM
│       ├── sources.py           DCM excitation factories
│       └── estimator.py         DCM nameplate + IEEE 113 estimators
│
├── ui/                          Views and theme system (Streamlit)
│   ├── theme.py                 Dark/light colour palette + global CSS
│   ├── clean_view.py            Article screenshot view
│   ├── theory/                  TIM Theory tab (package)
│   │   ├── __init__.py          Orchestrator — render_theory_tab (8 sub-tabs)
│   │   ├── tabs/                Sub-tab renderers (circuitos, dinamica, potencia, ...)
│   │   └── *.py                 Interactive components (park_dinamico, boucherot, mcsa, ...)
│   ├── theory_interactive.py    Shared TIM Theory interactive helpers
│   ├── theory_dc.py             DCM Theory tab
│   └── theory_dc_interactive.py DCM Theory interactive components
│
├── ui_components/               Streamlit widget modules
│   ├── _shared_widgets.py       Shared widget helpers (_pgroup, _ibox)
│   ├── tim_config.py            TIM machine selector + experiment config (orchestrator)
│   ├── tim_config_params.py     TIM parameter sub-renderers (Nameplate, IEEE, Manual)
│   ├── exp_renderers_tim.py     TIM experiment sub-renderers (one per mode)
│   ├── tim_fault_ui.py          TIM fault UI panels (unbalance, broken bar)
│   ├── tim_runner.py            TIM simulation orchestrator + cache
│   ├── tim_results.py           TIM results (orchestrator of 4 sub-tabs)
│   ├── tim_results_overview.py  Results sub-tab: KPIs + health
│   ├── tim_results_dynamics.py  Results sub-tab: waveforms
│   ├── tim_results_diagnostics.py Results sub-tab: diagnostics + MCSA
│   ├── tim_results_asset.py     Results sub-tab: asset management
│   ├── sim_config_dc.py         DCM machine selector + experiment config (orchestrator)
│   ├── sim_config_dc_keys.py    DCM widget-key registry (cycle-free)
│   ├── sim_config_dc_params.py  DCM parameter sub-renderers (Nameplate, IEEE 113, Manual)
│   ├── exp_renderers_dc.py      DCM experiment sub-renderers (one per mode)
│   ├── sim_runner_dc.py         DCM simulation orchestrator + cache
│   ├── sim_results_dc.py        DCM result tabs
│   ├── chart_notes.py           Chart annotation helpers
│   ├── reference_manager.py     Save/clear simulation references
│   └── theory_view.py           Re-export wrapper for the Theory tab
│
├── viz/                         Visualisation and report generation
│   ├── _chart_base.py           Parametric chart base (shared TIM/DC)
│   ├── plotly_config.py         Shared Plotly configs (MIT/DC)
│   ├── tim_charts.py            TIM Plotly charts + theme helpers (_plot_theme)
│   ├── plotly_charts_dc.py      DCM Plotly charts
│   ├── tim_eqcircuit.py         TIM equivalent circuit (schemdraw)
│   ├── eqcircuit_plotter_dc_v2.py DCM equivalent circuits (schemdraw)
│   ├── zoom_helpers.py          Zoom-window context for charts
│   ├── pdf_commons.py           Shared PDF utilities
│   ├── pdf_academico.py         Academic PDF report (TIM)
│   ├── pdf_industrial.py        Industrial PDF report (TIM)
│   ├── tim_pdf_report.py        TIM PDF report builder
│   ├── tim_pdf_dashboard.py     TIM PDF dashboard
│   └── pdf_dc.py                DCM PDF report
│
├── data/                        Reference data and labels
│   ├── machines_mit.py          TIM presets
│   ├── machines_dc.py           DCM presets
│   ├── experiment_modes.py      Mode/excitation label maps
│   ├── variable_labels.py       Plottable-variable catalogue
│   └── ui_labels.py             UI label maps (MACHINES, ...)
│
├── utils/                       Utility scripts
│   ├── text_utils.py            LaTeX to Unicode converter (_strip_latex)
│   ├── gen_okoro_comparison.py  Okoro (2008) DCM validation figures
│   └── _gen_theory_imgs.py      Theory tab PNG generator (uses core.tim torque)
│
├── scripts/                     Article / asset figure generation (standalone)
│   ├── gen_figures.py           Overleaf figures — TIM 60 Hz DOL
│   ├── gen_resultados_web.py    Overleaf figures — TIM 50 Hz
│   ├── gen_dc_imgs.py           DCM circuit PNGs
│   └── demo_potencias.py        Steady-state power metrics demo
│
├── tests/                       pytest test suite (235 tests, Streamlit-free)
│   ├── conftest.py              Shared fixtures (mp_3hp, mp_50hp, mp_2250hp)
│   ├── test_*.py                Physics, sources, transforms, thermal, estimators, ...
│   └── debug/                   Manual Streamlit debug pages (not run by pytest)
│
├── requirements.txt             Python package dependencies
├── rodar.bat                    Windows launcher (clears __pycache__, starts app)
├── README.md                    This file
├── ARCHITECTURE_HEADLESS.md     How IWS works with and without Streamlit
└── CLAUDE.md                    Claude Code project instructions
```

---

## Module Reference

### `core/` — Physics Engine (zero Streamlit)

#### Public facades

```python
# TIM (three-phase induction)
from core.tim.facade import MachineParams, run_simulation, build_fns

# DCM (DC machine)
from core.dc.facade import (
    DCMachineParams, run_simulation_dc,
    make_voltage_fn_dc, make_torque_fn_dc,
    estimate_dc_nameplate, estimate_dc_tests,
)
```

The facades are the single import point for downstream code (`ui_components`, `scripts`, `tests`). Import from them rather than from the internal submodules. `core.tim` (the package `__init__`) also re-exports the calculation symbols (`estimate_params`, `compute_energy_metrics`, `generate_insights`, `calc_curva_tn`, `_torque_array`, ...) as an aggregated entry point.

| Symbol | Type | Description |
|---|---|---|
| `MachineParams` | dataclass | TIM parameters (electrical, mechanical, thermal) — sensible defaults on every field |
| `run_simulation(mp, tmax, h, voltage_fn, torque_fn, **kwargs)` | function | Integrates the Krause model, returns a result dict (~53 arrays) |
| `build_fns(cfg, mp)` | function | Returns `(voltage_fn, torque_fn, t_events)` for an experiment config |
| `DCMachineParams` | dataclass | DCM parameters (armature, field, mechanical, load) |
| `run_simulation_dc(mp, tmax, h, voltage_fn, torque_fn)` | function | Integrates the DCM model, returns a result dict |

#### `core/tim/machine_model.py` — Krause dq0 Model

`MachineParams` key fields:

| Field | Unit | Description |
|---|---|---|
| `Vl` | V | Line-to-line RMS voltage |
| `f` | Hz | Supply frequency |
| `p` | — | Number of poles |
| `Rs`, `Rr` | Ω | Stator/rotor resistance |
| `Xls`, `Xlr`, `Xm` | Ω | Leakage and magnetising reactances |
| `Rfe` | Ω | Core loss resistance |
| `J` | kg·m² | Moment of inertia |
| `B` | N·m·s | Viscous friction |
| `Rth`, `Cth`, `T_amb` | K/W, J/K, °C | Thermal model parameters |

#### `core/tim/solver.py` — LSODA Integrator

Wraps `scipy.integrate.solve_ivp` with `method='LSODA'` and `h ≤ 1/(20f)` for stability. Post-processing reconstructs phase currents (`ias`, `ibs`, `ics`), voltages, steady-state RMS values, power, efficiency, power factor, and THD.

#### `core/tim/fault_model.py` — Pure Fault Physics

`abc_voltages_deseq(...)` (unbalanced voltages / phase loss) and `make_broken_bar_rr_fn(...)` (Rr modulation for broken-bar MCSA). No Streamlit — imported by `solver`, `machine_model`, and `facade`. The interactive panels for these faults live in `ui_components/tim_fault_ui.py`.

#### `core/dc/machine_model.py` — DCM Model

`_make_rhs_dc` returns the 4-state ODE RHS, switching equations by excitation:

| Config | States | Field equation |
|---|---|---|
| `sep_motor` / `sep_gen` | wr, ia, if | Separate field circuit |
| `shunt_motor` / `shunt_gen` | wr, ia | Parallel field (Vf = Va) |
| `series_motor` | wr, ia | Series field (if = ia) |

### `ui/` — Views and Theme

- `theme.py` — `_palette(dark)` colour dict + `apply_css(dark)`.
- `theory/` — package; `render_theory_tab()` (in `__init__.py`) lays out 8 sub-tabs, delegating to `theory/tabs/*` renderers.
- `theory_dc.py` — DCM Theory tab.

### `ui_components/` — Streamlit Widgets

Config and results are split into orchestrators + sub-renderers (mirrored for TIM and DCM):

| Concern | TIM | DCM |
|---|---|---|
| Config orchestrator | `tim_config.py` | `sim_config_dc.py` |
| Parameter sub-renderers | `tim_config_params.py` | `sim_config_dc_params.py` |
| Experiment sub-renderers | `exp_renderers_tim.py` | `exp_renderers_dc.py` |
| Runner | `tim_runner.py` | `sim_runner_dc.py` |
| Results | `tim_results*.py` (4 sub-tabs) | `sim_results_dc.py` |

### `viz/` — Charts and Reports

- `_chart_base.py` — parametric Plotly base shared by TIM/DC chart builders.
- `tim_charts.py` / `plotly_charts_dc.py` — machine-specific chart builders (zero-latency via pre-computed frames).
- PDF: `pdf_commons.py` (shared) + `pdf_academico.py`, `pdf_industrial.py`, `tim_pdf_report.py`, `tim_pdf_dashboard.py` (TIM), `pdf_dc.py` (DCM).

---

## Session State Contract

| Key | Type | Set by | Read by |
|---|---|---|---|
| `selected_machine` | `"mit"` or `"dc"` | `IWS_UI.py` | All ui_components |
| `dark_mode` | `bool` | `IWS_UI.py` | `ui.theme`, chart builders |
| `experiment_mode` | `bool` | config modules | config modules (locks inputs) |
| `sim_result` | `dict` | runner modules | results modules, `clean_view.py` |
| `ref_list` | `list` | results modules | `viz/pdf_*.py` |
| `decimals` | `int` | `IWS_UI.py` | results modules |

`sim_result` dict keys (TIM): `t`, `ias`/`ibs`/`ics`, `ids`/`iqs`, `idr`/`iqr`, `wr`, `n`, `Te`, `Va`/`Vb`/`Vc`, plus steady-state scalars. TypedDicts for all session keys are defined in `core/session_schema.py`.

---

## Simulation Flow

### TIM

```
User inputs (tim_config.py)
         │
         ▼
MachineParams + cfg dict
         │
         ▼
tim_runner.py: execute_simulation_flow()
  ├─ calc_tmax_auto(cfg, mp)
  ├─ build_fns(cfg, mp)        ── core.tim.facade ──▶ (voltage_fn, torque_fn, t_events)
  └─ run_simulation(mp, ...)   ── core.tim.facade ──▶ result dict
              │
              ▼
          core/tim/solver.py: scipy LSODA + reconstruct currents/voltages/steady-state
         │
         ▼
session_state["sim_result"]
         │
         ▼
tim_results.py: render_results()  ──▶  Overview / Dynamics / Diagnostics / Asset sub-tabs
```

### DCM

```
User inputs (sim_config_dc.py) ──▶ DCMachineParams + cfg
         │
         ▼
sim_runner_dc.py: execute_simulation_flow_dc()
  ├─ make_voltage_fn_dc(...) / make_torque_fn_dc(...)   ── core.dc.facade
  └─ run_simulation_dc(...)                             ── core.dc.facade ──▶ result dict
         │
         ▼
session_state["sim_result"] ──▶ sim_results_dc.py: render_results_dc()
```

---

## Simulation Modes

### TIM

| Group | Mode | Description |
|---|---|---|
| Starting | DOL | Direct-on-line |
| Starting | Star-delta | Y → Δ switching |
| Starting | Autotransformer | Reduced-voltage tap |
| Starting | Soft-starter | Linear voltage ramp |
| Regime | Load pulse | Load torque pulse |
| Regime | Generator | Generator operation |
| Transient | Shutdown | Power-off coast-down |
| Transient | Voltage sag | Rectangular sag |

Optional perturbations (toggle independently): phase asymmetry, phase loss, broken rotor bar.

### DCM

| Config | Modes |
|---|---|
| Separately excited (motor) | DOL, armature resistance, braking, field weakening, load pulse |
| Shunt (motor) | DOL |
| Series (motor) | DOL |
| Separately excited (generator) | Generator operation |

---

## Parameter Estimation

### TIM — Nameplate (NEMA MG-1)

```python
from core.tim import estimate_params  # aggregated entry point (also in core.tim.param_estimator)

params = estimate_params(
    Vl=220, f=60, p=4,
    Pn=5500, N_nom=1750, rend=0.88, fp=0.85,
    Ip_In=6.5, Tp_Tn=1.5, is_delta=False,
)   # -> dict: Rs, Rr, Xls, Xlr, Xm
```

### TIM — IEEE Std 112-2017

```python
from core.tim import estimate_params_ieee_tests

params = estimate_params_ieee_tests(
    V_dc, I_dc, is_delta,
    Vl_nl, I_nl, P_nl, f_nl,        # no-load test
    Vl_lr, I_lr, P_lr, f_lr,        # locked-rotor test
    Pfw, split=0.5, Xls_frac=0.5,
)
```

### DCM — Nameplate and IEEE 113

```python
from core.dc.facade import estimate_dc_nameplate, estimate_dc_tests
```

---

## How to Extend

### Add a new machine type (e.g. PMSM) — the registry pattern

1. **`core/pmsm/`** — `machine_model.py`, `solver.py`, `sources.py`, `facade.py` (mirror `core/dc/`).
2. **`ui_components/`** — config orchestrator + param/experiment sub-renderers + runner + results (mirror the `*_dc` set).
3. **`viz/`** — `plotly_charts_pmsm.py`, `pdf_pmsm.py` (reuse `_chart_base.py` / `pdf_commons.py`).
4. **`IWS_UI.py`** — write `_render_sim_tab_pmsm` / `_render_theory_pmsm` and register a `_MachineSpec` in `_MACHINE_REGISTRY`. **No if/elif branches change.**
5. **`tests/`** — add fixtures and test files.

### Add a new TIM simulation mode

1. **`core/tim/sources.py`** — add the voltage/torque profile in `build_fns`.
2. **`ui_components/exp_renderers_tim.py`** — add the experiment sub-renderer.
3. **`ui_components/tim_config.py`** — register the mode in the dispatch.
4. **`tests/test_sources.py`** — add a test case.

### Add a new Theory sub-tab (TIM)

1. **`ui/theory/tabs/<name>.py`** — create `render_tab_<name>()`.
2. **`ui/theory/__init__.py`** — add the `st.tabs` entry and call it.

---

## Running Tests

```bash
# Full suite (Streamlit-free)
pytest tests/ -q

# Single module
pytest tests/test_physics.py -v

# With coverage
pytest tests/ --cov=core --cov-report=term-missing
```

The suite imports only `core/` — it does **not** require a running Streamlit server. Use fixtures from `conftest.py` (`mp_3hp`, `mp_50hp`, `mp_2250hp`). Do not place automated tests in `tests/debug/` (manual Streamlit pages only).

---

## Commit Conventions

Format: `type: short description` (under 72 characters). Language: formal technical Portuguese.

| Type | When to use |
|---|---|
| `feat:` | New user-visible feature |
| `fix:` | Bug fix |
| `refactor:` | Code restructure with no behaviour change |
| `chore:` | Build, deps, tooling |
| `docs:` | Documentation only |
| `test:` | Tests only |

- Identity: Kevin · k.g.pinheiro.castro@gmail.com
- No `Co-Authored-By` lines.

---

## Technical References

| Reference | Used in |
|---|---|
| Krause, P.C. (1986). *Analysis of Electric Machinery*. McGraw-Hill. | `core/tim/machine_model.py`, `core/tim/solver.py` |
| IEEE Std 112-2017. *Test Procedure for Polyphase Induction Motors and Generators*. | `core/tim/param_estimator.py` |
| IEEE Std 113-1985. *Guide on Test Procedures for DC Machines*. | `core/dc/estimator.py` |
| NEMA MG-1. *Motors and Generators*. | `core/tim/param_estimator.py`, `core/dc/estimator.py` |
| Okoro, O.I. (2008). *Steady and Transient States Thermal Analysis*. | `utils/gen_okoro_comparison.py` |
| Fitzgerald, Kingsley, Umans (2003). *Electric Machinery*, 6th ed. McGraw-Hill. | `core/tim/torque_speed.py` |
