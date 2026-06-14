# Refactoring Notes — IWS English

## Session: 2026-06-14 (part 3)

### 1. `ui_components/tim_config.py` — Extraction of sub-functions from `render_machine_params()`

**Commits:** `af5f189`, `bab089c`

**Before:** `render_machine_params()` with 764 lines containing three parameter-source branches
(Nameplate, IEEE 112, Manual) interleaved with shared mechanical/advanced blocks. One closure
captured all local variables, making the data flow invisible.

**After:** `_ElecParams` frozen dataclass + 3 sub-renderers + slim orchestrator (~80 lines):

| Function | Responsibility | Lines |
|---|---|---|
| `_ElecParams` | Immutable carrier for the 10 electrical parameters between sub-renderers | dataclass |
| `_render_params_nameplate(wk, dis)` | Nameplate inputs → `_cached_estimate_params()` → expander with results | ~100 |
| `_render_params_ieee(wk, dis)` | Three IEEE 112 test sections → `_cached_estimate_ieee()` → results expander | ~260 |
| `_render_params_manual(wk, dis)` | Direct widget inputs for all parameters (X or L mode) | ~50 |
| `render_machine_params()` | Dispatcher: locked-mode early return → selects sub-renderer → mechanical/advanced/build | ~80 |

**Benefits:**

- **Visible data flow:** each sub-renderer declares its outputs via `_ElecParams` fields — no
  longer necessary to read the entire function to discover what variables are produced.
- **Isolated modes:** editing the IEEE 112 UI no longer risks breaking Nameplate logic —
  modes are in separate functions with no shared mutable state.
- **Cognitive load halved:** the orchestrator is now a ~80-line dispatcher. Previously, finding
  the mechanical block required scrolling past 600 lines of electrical widgets.
- **Bug fix:** `_WK.Tl_nom_dol` referenced the singleton `_WK` inside the class definition
  of `_WidgetKeys` — a `NameError` at import. Fixed to literal `"wi_dol_Tl_nom"`.

---

### 2. `ui_components/tim_config.py` — `_CRITICAL_EVENTS` data table replaces `if/elif` chain

**Commits:** `2851d26`

**Before:** 30-line `if/elif` block (8 branches) that mapped `exp_type → list of (label, symbol, config_key)` for tmax event-coverage validation.

**After:** one dict at module level:

```python
_CRITICAL_EVENTS: dict[str, list[tuple[str, str, str]]] = {
    "yd":          [("Y→D switching", r"t_2", "t_2"), ...],
    "comp":        [...],
    "soft":        [...],
    "pulso_carga": [...],
    "gerador":     [...],
    "shutdown":    [...],
}
```

Lookup: `_critical_raw = _CRITICAL_EVENTS.get(_etype, [])` — two lines replace 25.

**Benefits:**

- **Data, not code:** adding a new experiment type requires one dict entry, not a new `elif`.
- **30 → 10 lines** with identical runtime behaviour and no new dependencies.

---

### 3. `ui_components/sim_config_dc.py` — `_WK_DC` frozen dataclass (bug fix: circular reference)

**Commits:** `9f8754b`, `4466341`

**Before (broken):** the refactor that created `_WK_DC` had each field default referencing the
singleton itself (`Va: str = _WK_DC.Va`), which does not yet exist at class-definition time →
`NameError: name '_WK_DC' is not defined` at import.

**After:** all 52 fields use string literals directly, matching the original `"wi_dc_<field>"` keys:

```python
@dataclasses.dataclass(frozen=True)
class _WidgetKeysDC:
    Va:  str = "wi_dc_Va"
    Ra:  str = "wi_dc_Ra"
    ...  # 52 fields total
```

Singleton instantiated after the class: `_WK_DC = _WidgetKeysDC()`.

**Benefits:** same as `_WK` (autocomplete, typo detection, immutability) — now actually working.

---

### 4. `viz/plotly_config.py` — Shared Plotly chart configuration

**Commits:** (session part 2)

**Before:** `_PLOT_CFG` dict duplicated identically in `tim_results.py` and `dc_results.py`.

**After:** `viz/plotly_config.py` exports `MIT_PLOT_CFG` and `DC_PLOT_CFG` (differ only in
`filename`). Both consumers import from there.

**Benefits:** chart config change (e.g. image export scale) requires one edit, not two.

---

### 5. `ui_components/reference_manager.py` — DRY save-reference logic

**Commits:** (session part 2)

**Before:** 10-line save-reference block duplicated in `IWS_UI.py` for MIT and DC separately.

**After:** `save_reference(sim_result: dict) -> None` pure function handles color/dash cycling
and `st.rerun()`. Both call sites replaced with one line each.

---

### 6. `ui_components/chart_notes.py` — `_nota_apos` closure → top-level function

**Commits:** (session part 2)

**Before:** `_nota_apos` was a ~240-line closure inside `render_results()`, implicitly capturing
12 local variables. Untestable; impossible to call in isolation.

**After:** `MITNoteCtx` frozen dataclass bundles the 12 captured variables explicitly.
`emit_mit_note(key, ctx)` is a top-level function — testable, importable, no hidden state.

---

### 7. `viz/zoom_helpers.py` — Zoom calculation extracted from closures

**Commits:** (session part 2)

**Before:** zoom window calculation and axis range application were closures inside
`render_results()`, each capturing `res`, `exp_config`, `mp`, and timing variables implicitly.

**After:** `ZoomCtx` dataclass + three pure functions:

| Function | Signature |
|---|---|
| `compute_t_window(zoom_mode, ctx)` | Returns `(t0, t1) \| None` |
| `y_ranges(t_window, keys, res, tl_arr)` | Returns padded y-ranges per key |
| `apply_zoom(fig, keys, t_window, res, tl_arr)` | Mutates single-panel figure |
| `apply_zoom_overlay(fig, keys, t_window, res, tl_arr)` | Mutates dual-axis figure |

Reuses `STARTING_SPEED_THRESHOLD` from `core/constants.py`.

---

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
