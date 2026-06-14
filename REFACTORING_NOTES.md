# Refactoring Notes — IWS English

## Session: 2026-06-14 (part 2)

### 1. `data/machines_mit.py` and `data/machines_dc.py` — Extraction of machine presets

**Commits:** `ae11609`, `9071f73`

**Before:** motor presets (Krause 3 HP, Sen Ex. 9.2, Okoro et al., etc.) were hardcoded dicts
embedded inside `sim_config.py` (48 lines) and `sim_config_dc.py` (92 lines), mixed with
Streamlit widget logic.

**After:** one file per machine type, containing only data:

| File | Contents |
|---|---|
| `data/machines_mit.py` | `MIT_PRESETS` dict + exported constants `KRAUSE_3HP`, `KRAUSE_50HP`, `KRAUSE_2250HP` |
| `data/machines_dc.py` | `DC_PRESETS_BY_EXC` (keyed by excitation type) + `DC_PRESETS_FLAT` for legacy access |

`sim_config.py` and `sim_config_dc.py` now simply import and alias:
```python
_PRESETS: dict = MIT_PRESETS          # sim_config.py
_PRESETS_BY_EXC: dict = DC_PRESETS_BY_EXC  # sim_config_dc.py
```

`tests/conftest.py` fixtures simplified — use `KRAUSE_3HP` directly instead of repeating
parameter dicts in two places.

**Benefits:**

- **Single place to add a motor:** open `data/machines_mit.py`, copy a block, fill in values.
  No Streamlit knowledge required — pure Python dicts.
- **No duplication:** parameters defined once, referenced by both the UI and test fixtures.
- **Establishes `mit_` / `dc_` naming convention** for the `data/` layer — pattern to be
  extended to `core/` and `viz/` in the next session.

---

### 2. `core/constants.py` — Centralised numeric constants and defaults

**Commits:** `055ea0b`

**Before:** solver tolerances and machine defaults scattered across 4 files:

| Constant | Old location |
|---|---|
| `SS_TOL`, `RTOL`, `ATOL`, `MAX_STEP_FACTOR`, … | `core/solver.py` lines 38–45 |
| `Vl=220.0`, `Rs=0.435`, `Rr=0.816`, … | `ui_components/sim_config.py` line 183 (repeated 3×) |
| DC session defaults (12 keys) | `IWS_UI.py` lines 91–98 |

**After:** `core/constants.py` with three sections:

```
SOLVER_*          — integrator tuning (SS_TOL, RTOL, ATOL, NYQUIST_LIMIT, …)
MIT_DEFAULTS      — default MIT parameters (Krause 3 HP values)
DC_SESSION_DEFAULTS — default DC widget values keyed to session_state names
```

Consumers import what they need:
```python
from core.constants import SOLVER_RTOL as RTOL   # solver.py
from core.constants import MIT_DEFAULTS            # sim_config.py
from core.constants import DC_SESSION_DEFAULTS     # IWS_UI.py
```

**Benefits:**

- **One place to tune the integrator:** changing `SOLVER_ATOL` from `1e-9` to `1e-8` is a
  single-line edit. Previously required knowing which file owned the constant.
- **One place to change default parameters:** `MIT_DEFAULTS["Vl"] = 380.0` updates every
  widget that reads `_DEFAULTS` — no risk of missing a repeated literal.
- **Documented units:** each constant block has a comment with physical units (Ω, H, V, …),
  which was absent when the values were scattered.

---

### 3. `tests/` — Automated test suite (234 tests)

**Commits:** `9071f73`

**Before:** no test coverage for DC modules, presets, voltage sources, or fault models.

**After:** 8 new test files covering:

| File | What it tests |
|---|---|
| `test_dc_machine.py` | DC ODE physics — back-EMF, torque balance, steady state |
| `test_dc_presets.py` | All 13 DC presets instantiate and simulate without error |
| `test_dc_sources.py` | DC voltage/torque source functions (DOL, plugging, field weakening, …) |
| `test_desequilibrio_falta.py` | Voltage unbalance, phase loss, broken bar models |

**Benefits:**

- **Safe to refactor:** `pytest tests/` in 10 s confirms nothing broke after any change.
- **Presets as contracts:** `test_dc_presets.py` guarantees every preset in `data/machines_dc.py`
  produces a valid `DCMachineParams` and completes a simulation — catches typos in numeric values.
- **Physics regression guard:** `test_dc_machine.py` validates back-EMF formula, torque sign
  convention, and speed direction — catches model-level errors that UI testing would miss.

---

## Session: 2026-06-14

### 1. `sim_results.py` — Extraction of sub-tabs from `render_results()`

**Commits:** `904485d`

**Before:** `render_results()` with 1007 lines containing 4 embedded sub-tabs.

**After:** 5 extracted functions + orchestrator of ~55 lines:

| Function | Responsibility |
|---|---|
| `_render_tab_overview` | KPIs, health panel, protection, economic summary |
| `_render_tab_dynamic` | Waveform charts (`@st.fragment` at module level) |
| `_render_tab_diagnosis` | Insights, power quality, FFT/MCSA |
| `_render_tab_assets` | Economic analysis and consumption |
| `_render_export_panel` | PDF export buttons |

**Benefits:**

- **Readability:** each function fits in one screen (~150–200 lines); no need to scroll 1000 lines to find a specific tab.
- **Isolated testability:** each tab function can be tested independently with mocked `res`/`mp` — the flat monolith prevented this.
- **Reduced cognitive load:** `render_results()` is now a pure orchestrator (pre-compute shared state → delegate to tabs). The data flow is explicit.
- **`@st.fragment` promotion:** `_render_dinamica` was a closure defined inside `render_results()`. Promoting it to module level makes it reusable and eliminates a layer of indirection.
- **Easier future extensions:** adding a 5th sub-tab is a one-liner in `render_results()` + a new function — no need to navigate 1000-line code.

---

### 2. `sim_config.py` — `_WK` dict → `_WidgetKeys` frozen dataclass

**Commits:** `881e057`

**Before:** `_WK: dict[str, str]` with 43 string keys, accessed as `wk["Vl"]` in 108 sites.

**After:** `@dataclasses.dataclass(frozen=True)` with 43 typed attributes, accessed as `wk.Vl`.

**Benefits:**

- **IDE autocomplete:** `wk.` triggers suggestion of all 43 valid keys. With `wk["..."]` the IDE had no context to suggest or validate strings.
- **Typo detection at analysis time:** `wk.Vll` fails immediately with `AttributeError` (or highlighted red by static analysis). `wk["Vll"]` was a silent `KeyError` only detected at runtime during widget rendering.
- **Immutability:** `frozen=True` prevents accidental reassignment (`wk.Vl = "other"` raises `FrozenInstanceError`). The dict was mutable.
- **Typed signature:** `render_machine_params(wk: _WidgetKeys)` vs `wk: dict[str, str]` — mypy/pyright can now validate that the correct object type is passed.
- **No runtime cost:** dataclass with frozen=True has the same access cost as direct attribute access on any Python object — faster than `dict.__getitem__`.
