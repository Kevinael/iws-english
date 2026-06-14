# IWS — Test Suite Reference

**236 tests · pytest · Python 3.9+**

---

## Table of Contents

1. [Running the Tests](#1-running-the-tests)
2. [Test Files — What Each Covers](#2-test-files--what-each-covers)
3. [Fixtures and Shared Infrastructure](#3-fixtures-and-shared-infrastructure)
4. [Test Styles Used in This Project](#4-test-styles-used-in-this-project)
5. [Adding New Tests](#5-adding-new-tests)
6. [Known Limitations and Deliberate Exclusions](#6-known-limitations-and-deliberate-exclusions)
7. [Interpreting Failures](#7-interpreting-failures)

---

## 1. Running the Tests

### Full suite

```bash
python -m pytest
```

### Single file

```bash
python -m pytest tests/test_dc_machine.py
```

### Single test by name (substring match)

```bash
python -m pytest -k "back_emf"
python -m pytest -k "TestDCSteadyState"
```

### Verbose output (shows each test name)

```bash
python -m pytest -v
```

### Stop on first failure

```bash
python -m pytest -x
```

### Show local variables on failure

```bash
python -m pytest -l
```

### Run only fast tests (skip integration / slow simulations)

```bash
python -m pytest -m "not slow"
```

> Note: no `slow` marker is applied yet. All 236 tests finish in ~8 s on a modern CPU.

### Python interpreter

The project uses `C:\Users\gacas\AppData\Local\Python\bin\python.exe`.
If `python` on PATH points elsewhere (e.g., a virtual environment), invoke explicitly:

```bash
C:\Users\gacas\AppData\Local\Python\bin\python.exe -m pytest
```

---

## 2. Test Files — What Each Covers

### MIT (Three-Phase Induction Motor)

| File | Tests | What it verifies |
|---|---|---|
| `test_machine_model.py` | 13 | `MachineParams` post-init, inductance derivation, grid voltage effect, thermal model fields |
| `test_transforms.py` | 6 | Clarke-Park transform, `abc_voltages`, phase balance (Va+Vb+Vc=0), scalar vs array input |
| `test_sources.py` | 20 | All MIT voltage sources (DOL, Y-Δ, autotransformer, soft-starter, voltage sag), `build_fns` for every experiment type |
| `test_thermal.py` | 7 | `dTemp_dt` equilibrium, heating, cooling, `estimate_rth_cth` output bounds |
| `test_physics.py` | 19 | Full DOL simulation invariants: torque balance, power balance, efficiency ≤ 1, thermal convergence, slip ∈ [0,1] |
| `test_harmonica_analysis.py` | 12 | `build_fig_fft`, harmonic peak detection, FFT magnitude bounds, broken-bar sideband presence |
| `test_energy_analysis.py` | 12 | `compute_energy_metrics` output, energy positivity, cost proportionality to time, THD ≥ 0, power factor ∈ [0,1] |
| `test_param_estimator.py` | 30 | Nameplate (NEMA MG-1) round-trip vs Krause reference; IEEE Std 112-2017 fasor iteration convergence |
| `test_sim_diagnostics.py` | 20 | `Insight` dataclass, `generate_insights` rules: overload, underload, thermal anomaly, vibration |
| `test_curva_tn.py` | 8 | `calc_curva_tn` output keys and length, torque ≥ 0 in motor region, peak torque exists, generator region Te < 0, power conservation |
| `test_desequilibrio_falta.py` | 13 | `abc_voltages_deseq` balanced/unbalanced/phase-loss, symmetrical components (V2 grows with deseq), `make_broken_bar_rr_fn` severity scaling and t_start |

### DC Motor (MCC)

| File | Tests | What it verifies |
|---|---|---|
| `test_dc_machine.py` | 11 | `DCMachineParams` derived fields (series only), Tload sign convention, back-EMF formula, electromagnetic torque formula, power balance, solver output keys and array lengths |
| `test_dc_sources.py` | 11 | `make_voltage_fn_dc`: DOL (full voltage immediately), series resistance (reduced at t=0, full after ramp), plugging (Va reversed after t_freia), field weakening (Vf drops after t_campo). `make_torque_fn_dc`: constant for DOL, step for pulso_dc, positive for gerador_dc |
| `test_dc_presets.py` | 39 | Parametric smoke test over all 13 DC presets: instantiation, numeric field types, 2-second simulation completes with `success=True` |

### Legacy / Skipped

| File | Status | Notes |
|---|---|---|
| `test_dc_phase1_validation.py` | 1 test — SKIPPED | Phase-1 DC API (superseded). Kept as documentation of the migration. |
| `debug/test_deseq_ui.py` | Not collected by default | Streamlit render test; requires a live Streamlit session. Run manually if needed. |

---

## 3. Fixtures and Shared Infrastructure

### `conftest.py`

Provides three MIT reference motor fixtures sourced from `data/machines_mit.py`:

| Fixture | Motor | Source |
|---|---|---|
| `mp_3hp` | Krause 3 HP — 220 V / 60 Hz | Krause (2002) |
| `mp_50hp` | Krause 50 HP — 460 V / 60 Hz | Krause (2002) |
| `mp_2250hp` | Krause 2250 HP — 2300 V / 60 Hz | Krause (2002) |
| `dol_result` | Full DOL simulation of 3 HP (3 s) | Built from `mp_3hp` |

These fixtures are available to **all test files automatically** — no import needed.

```python
def test_something(mp_3hp):
    assert mp_3hp.Rs == pytest.approx(0.435)
```

### `data/machines_mit.py` and `data/machines_dc.py`

Single source of truth for all machine parameters. Fixtures and parametric tests read from here. When a preset changes, all tests that use it update automatically.

---

## 4. Test Styles Used in This Project

### Unit test
Tests one function in isolation with controlled inputs. No simulation run.

```python
def test_dTemp_dt_equilibrio(mp_3hp):
    # at thermal equilibrium, derivative must be zero
    result = dTemp_dt(T=mp_3hp.T_ref, T_amb=mp_3hp.T_ref, P_loss=0, Rth=1.0, Cth=1.0)
    assert result == pytest.approx(0.0)
```

### Integration test
Runs a full simulation (via `run_simulation` or `run_simulation_dc`) and checks invariants on the output arrays.

```python
def test_power_balance(dol_result):
    # electrical power in ≥ mechanical power out (losses account for the rest)
    assert dol_result["Pin"][-1] >= dol_result["Pmec"][-1] * 0.9
```

### Validation against reference
Checks that the simulator reproduces a known textbook result within an acceptable tolerance.

```python
def test_krause_3hp_params(mp_3hp):
    assert mp_3hp.Rs == pytest.approx(0.435, rel=0.01)   # Krause (2002) Table 4.10-1
```

### Parametric / smoke test
Runs the same assertion over many inputs using `@pytest.mark.parametrize`. Used in `test_dc_presets.py` to cover all 13 DC presets without writing 13 identical functions.

```python
@pytest.mark.parametrize("exc,name,vals", list(_all_presets()), ids=[...])
def test_preset_simulation_completes(exc, name, vals):
    ...
    assert res["success"]
```

---

## 5. Adding New Tests

### Adding a test to an existing file

Open the relevant file and add a function starting with `test_`. pytest discovers it automatically.

```python
# in test_dc_machine.py
def test_my_new_invariant():
    preset = _preset("sep_motor", "Sep. Motor 220 V — Sen Ex. 9.2")
    res = _run(preset, tmax=5.0)
    assert res["n_ss"] == pytest.approx(res["wm_ss"] * 60 / (2 * np.pi), rel=1e-4)
```

### Adding a test for a new MIT feature

1. Create `tests/test_<module_name>.py`
2. Add `sys.path.insert` at the top (copy from any existing test file)
3. Import from `conftest.py` fixtures as needed (they are auto-available)
4. Run `python -m pytest tests/test_<module_name>.py -v` to verify

**Template:**

```python
# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np
from core.<module> import <function>


def test_<behavior>(<fixture_if_needed>):
    result = <function>(...)
    assert result == pytest.approx(<expected>, rel=<tolerance>)
```

### Adding a test for a new DC feature

Same as above, but import from `core.dc_*` and use `data/machines_dc.py` for parameters:

```python
from core.dc_machine_model import DCMachineParams
from data.machines_dc import DC_PRESETS_BY_EXC

def test_my_dc_test():
    vals = DC_PRESETS_BY_EXC["sep_motor"]["Sep. Motor 220 V — Sen Ex. 9.2"]
    p = DCMachineParams(**{k: v for k, v in vals.items()
                           if not k.startswith("_") and k != "dol_vazio"})
    assert p.Va == 220.0
```

### Adding a new machine preset and testing it

1. Add the preset to `data/machines_mit.py` (MIT) or `data/machines_dc.py` (DC)
2. `test_dc_presets.py` parametric tests cover the new DC preset **automatically** — no code change needed
3. For MIT, add a fixture to `conftest.py` only if the preset will be used in many tests:

```python
# conftest.py
from data.machines_mit import MIT_PRESETS

@pytest.fixture
def mp_my_motor():
    from core.machine_model import MachineParams
    p = MIT_PRESETS["My Motor — 5 HP (3.7 kW) 380 V/50 Hz"]
    return MachineParams(**{k: p[k] for k in ("Vl","f","Rs","Rr","Xm","Xls","Xlr","Rfe","p","J","B")})
```

### Adding a validation test against a reference

Use `pytest.approx` with a relative tolerance. Justify the tolerance in a comment.

```python
def test_nameplate_efficiency_round_trip():
    # IEEE Std 112-2017 requires estimated η within ±2% of nameplate
    result = estimate_params(Vl=460, f=60, Pn=37000, N_nom=1746, rend=0.93, ...)
    assert result["eta_est"] == pytest.approx(0.93, rel=0.02)
```

### Tolerance guidelines

| Quantity | Typical `rel` tolerance | Reason |
|---|---|---|
| Electrical parameters (Rs, Rr, Xm) | `0.01` (1%) | LSODA precision + float arithmetic |
| Energy / power | `0.05` (5%) | Numerical integration over finite time window |
| Temperature | `0.02` (2%) | Thermal model is first-order approximation |
| Textbook reference values | `0.01` (1%) | Krause/Sen/Fitzgerald parameters are exact |
| Symmetrical components | `0.01` (1%) | Exact algebraic transform |

---

## 6. Known Limitations and Deliberate Exclusions

### UI layer (`ui/`, `ui_components/`)
Not tested. Streamlit widgets require a live server session; unit testing them would require mocking the entire `st.*` API. Correctness of UI logic (parameter validation, session state transitions) is verified manually via `streamlit run IWS_UI.py`.

### Visualization layer (`viz/`)
Not tested. Plotly and ReportLab outputs are visual artifacts — correctness is inherently subjective and requires human inspection. Chart data (the arrays fed into Plotly) is tested indirectly by the simulation tests.

### Okoro 24 V presets in shunt/series topology
`DC_PRESETS_BY_EXC["shunt_motor"]["Shunt Motor 24 V — Okoro et al. (2008)"]` and the series equivalent have `kb=0.004`, which was calibrated for the separately-excited topology. In shunt/series topology under DOL with full nominal load, the motor does not reach positive steady-state speed. The presets exist to demonstrate the topology configuration, not as physically validated operating points. They are excluded from `test_speed_positive_sep_motors` and pass the smoke test (`test_dc_presets.py`) only for instantiation and simulation completion, not for physical correctness.

### `test_dc_phase1_validation.py`
Marked `@pytest.mark.skip` because the Phase-1 DC API was superseded. The file is kept as a record of the original validation approach. Do not delete it.

### Series motor DOL convergence
The series motor characteristic curve (Te ∝ ia²) means the motor may not reach a stable positive speed under constant full-load DOL in 5 seconds. `test_series_motor_reaches_steady_state` only checks `success=True` and `ia_ss > 0`, not `wm_ss > 0`. This is physically correct — series motors should use `resistencia_dc` mode in practice.

---

## 7. Interpreting Failures

### `AssertionError: X == approx(Y)` in a physics test

The simulator produced a value outside the expected tolerance. Check:
1. Was a parameter changed in `data/machines_mit.py` or `data/machines_dc.py`?
2. Was the physics model changed in `core/`?
3. Is the tolerance too tight for the simulation window (`tmax` too short for steady-state)?

### `TypeError: unexpected keyword argument`

A preset dict contains a UI-only key (`_dc_mode_sel`, `dol_vazio`) that was passed to `DCMachineParams`. The helper `_run()` in `test_dc_machine.py` already filters these. If you add a new UI-only key to a preset, add it to the filter condition:

```python
# in _run() or _clean():
if not k.startswith("_") and k not in ("dol_vazio", "your_new_ui_key")
```

### `SKIPPED` in output

`test_dc_phase1_validation.py::test_sep_motor_dol` is intentionally skipped. Not a problem.

### `FAILED` in `test_dc_presets.py` after adding a preset

The new preset failed instantiation or simulation. Most common causes:
- Missing required field (`Va`, `Ra`, `La`, `kb`, `J`, `B`, `Tload`)
- Wrong excitation key (must be one of: `sep_motor`, `shunt_motor`, `series_motor`, `sep_gen`, `shunt_gen`)
- Generator preset missing `Rl`/`Ll` fields required by the solver
- `Tload` positive for a generator (must be negative)
