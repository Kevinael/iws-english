# -*- coding: utf-8 -*-
"""
tim_config_ieee.py
==================
IEEE Std 112-2017 parameter-estimation panel for the MIT machine (three physical tests).

Exports:
    render_params_ieee   — IEEE 112 mode entry point (grid + guide + tests + results)

Relationships:
  Imported by : ui.tim_config_params (lazily, inside _render_params_editable)
  Imports     : ui.tim_config_params (_ElecParams, _tl_sugerido), ui._shared_widgets,
                core.tim, core.constants, data.ui_labels, core.tim.facade

Note:
  _ElecParams and _tl_sugerido remain in tim_config_params (shared by all three
  parameter-source renderers). This module imports them at top level; the reverse
  dependency (tim_config_params → render_params_ieee) is a lazy import, so there is
  no import cycle at module load time.
"""

from __future__ import annotations

import streamlit as st

from core.tim.facade import MachineParams
from core.constants import MIT_DEFAULTS
from data.ui_labels import MIT_IEEE_SPLIT_LABELS
from core.tim import estimate_params_ieee_tests
from ui._shared_widgets import _pgroup
from ui.tim_config_params import _ElecParams, _tl_sugerido

_DEFAULTS: dict = MIT_DEFAULTS


# ─────────────────────────────────────────────────────────────────────────────
# CACHED ESTIMATOR
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_estimate_ieee(
    V_dc: float, I_dc: float, is_delta: bool,
    Vl_nl: float, I_nl: float, P_nl: float, f_nl: float,
    Vl_lr: float, I_lr: float, P_lr: float, f_lr: float,
    Pfw: float, split: str, Xls_frac: float,
) -> dict:
    return estimate_params_ieee_tests(
        V_dc, I_dc, is_delta, Vl_nl, I_nl, P_nl, f_nl,
        Vl_lr, I_lr, P_lr, f_lr, Pfw, split, Xls_frac,
    )


# ─────────────────────────────────────────────────────────────────────────────
# IEEE 112 SUB-RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _render_ieee_grid_inputs(wk: object, dis: bool) -> tuple[float, float, bool]:
    """Grid Data block: Vl, f, is_delta."""
    _pgroup("Grid Data")
    Vl = st.number_input(
        "Line RMS voltage — $V_l$ (V)",
        min_value=50.0, max_value=15000.0, value=_DEFAULTS["Vl"], step=1.0,
        key=wk.Vl, disabled=dis,
    )
    f = st.number_input(
        "Grid frequency — $f$ (Hz)",
        min_value=1.0, max_value=400.0, value=_DEFAULTS["f"], step=1.0,
        key=wk.f, disabled=dis,
    )
    is_delta = st.checkbox(
        "Delta (Δ) connection — uncheck for Star (Y)",
        value=False, key=wk.is_delta, disabled=dis,
        help="Defines the DC test factor: Y → Rs = (V_dc/I_dc)/2; Δ → Rs = (V_dc/I_dc)·1.5.",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return Vl, f, is_delta


def _render_ieee_guide(_wk: object) -> None:
    """Didactic guide expander for the three IEEE 112 tests."""
    with st.expander("How to perform the IEEE 112 tests (procedure, formulas, and tips)", expanded=False):
        st.markdown("""
**Overview.** The IEEE Std 112-2017 (Cl. 6) method determines the T-equivalent circuit
of an induction machine through **three complementary physical tests**:

| Test | What it measures | Extracted parameters |
|------|-----------------|---------------------|
| **[1] DC** (Cl. 6.4) | Cold stator ohmic resistance | $R_s$ |
| **[2] No-Load** (Cl. 6.5) | Magnetizing branch at rated voltage, $s \\approx 0$ | $X_m$, $R_{fe}$, $P_{fw}$ |
| **[3] Locked Rotor** (Cl. 6.6) | Short-circuit impedance, $s = 1$ | $R_r$, $X_{ls}$, $X_{lr}$ |

All values are per phase. For $\\Delta$ connection, enable the checkbox above — the
estimator handles the conversion internally.
        """)

        st.markdown("### [1] DC Test — Stator Resistance")
        st.markdown("""
**Objective.** Measure $R_s$ per phase with the motor at rest and de-energized from AC.

**Equipment.** Adjustable DC source, DC voltmeter, DC ammeter.

**Procedure (IEEE 112 Cl. 6.4):**
1. Ensure the motor is **cold** (at ambient temperature) — resistance varies ~0.4%/°C.
2. Connect the DC source between **two terminals** of the motor.
3. Raise the voltage until the current reaches approximately **25% of $I_n$**.
4. Wait **1 minute** for thermal stabilization.
5. Record $V_{dc}$ and $I_{dc}$ simultaneously.

**Applied formula:**
- Star (Y): $R_s = \\dfrac{V_{dc}}{2 \\cdot I_{dc}}$ — two windings in series
- Delta (Δ): $R_s = 1{.}5 \\cdot \\dfrac{V_{dc}}{I_{dc}}$ — two in parallel with one in series

**Practical tips:**
- Do not exceed 25% of $I_n$ — higher currents heat the windings and distort $R_s$.
- Repeat the test for the other two terminal pairs and use the **average**.
- Typical value: 0.01–10 Ω, depending on motor rating.
        """)

        st.markdown("### [2] No-Load Test — Magnetization")
        st.markdown("""
**Objective.** Determine $X_m$, $R_{fe}$ and estimate mechanical losses ($P_{fw}$),
operating the motor **unloaded** at rated voltage and frequency.

**Equipment.** Rated three-phase AC source, three-phase wattmeter, voltmeter, ammeter.

**Procedure (IEEE 112 Cl. 6.5):**
1. **Decouple** any mechanical load from the shaft (motor spins freely).
2. Apply **rated** line voltage $V_l$ at rated frequency $f$.
3. Allow the motor to stabilize (slip $s \\to 0$, thermal steady state).
4. Record $V_{l,NL}$, $I_{NL}$ (line), $P_{NL}$ (total three-phase).

**Loss separation.** The no-load absorbed power covers three components:

$$P_{NL} = \\underbrace{3 \\cdot R_s \\cdot I_{NL}^2}_{\\text{Stator Joule}} + \\underbrace{P_{fe}}_{\\text{core}} + \\underbrace{P_{fw}}_{\\text{friction+windage}}$$

**Applied formulas:**
- $V_{f,NL} = V_{l,NL}/\\sqrt{3}$
- $E_{1,NL} \\approx V_{f,NL} - (R_s + jX_{ls}) \\cdot I_{NL}$ — refined in 2 phasor iterations
- $R_{fe} = 3 \\cdot E_{1,NL}^2 / P_{fe}$
- $I_\\mu = \\sqrt{I_{NL}^2 - I_{fe}^2}$, then $X_m = E_{1,NL}/I_\\mu - X_{ls}$

**About $P_{fw}$:**
- If you **measured** $P_{fw}$ separately (coast-down test or zero-voltage extrapolation), enter the value.
- If left at **0**, the estimator applies the IEEE heuristic: $P_{fw} = 0{.}8\\% \\cdot P_{NL}$.

**Practical tips:**
- Typical $I_{NL}$: 25–40% of $I_n$ (small motors), 15–25% (large motors).
- No-load power factor is very low (~0.1–0.3) — analog wattmeters must be of good accuracy class.
- If possible, run the motor at high speed for 30 min beforehand to warm the bearings and stabilize friction.
        """)

        st.markdown("### [3] Locked Rotor Test")
        st.markdown("""
**Objective.** Determine $R_r$, $X_{ls}$ and $X_{lr}$ with the rotor **mechanically locked**
($s = 1$, no back-EMF).

**Equipment.** Three-phase AC source with **variable frequency** (ideally), wattmeter,
voltmeter, ammeter, mechanical shaft locking device.

**Procedure (IEEE 112 Cl. 6.6):**
1. **Lock the rotor** mechanically (screwdriver in slot, brake, etc.) — it must not rotate.
2. Start with **very low voltage** (5–10% of $V_n$) and increase gradually.
3. Raise until the current reaches **rated current** $I_n$ (or slightly above, per the standard).
4. Record $V_{l,LR}$, $I_{LR}$, $P_{LR}$, and frequency $f_{LR}$.

**Why reduce the frequency?**
At $s = 1$ and rated frequency, magnetic saturation in the rotor bars distorts the
measurements. The standard recommends $f_{LR} \\approx 25\\% \\cdot f_{rated}$ (e.g., 15 Hz for a 60 Hz grid)
to reduce saturation. Since $X$ is proportional to frequency, the estimator scales the
result back:

$$X_k\\big|_{f_{nom}} = X_k\\big|_{f_{LR}} \\cdot \\frac{f_{nom}}{f_{LR}}$$

**Applied formulas:**
- $V_{f,LR} = V_{l,LR}/\\sqrt{3}$
- $Z_k = V_{f,LR}/I_{LR}$
- $R_k = P_{LR}/(3 \\cdot I_{LR}^2) = R_s + R_r$
- $X_k\\big|_{f_{LR}} = \\sqrt{Z_k^2 - R_k^2}$, then scaled to $f_{nom}$
- $R_r = R_k - R_s$ (must be positive)

**$X_{ls}/X_{lr}$ distribution:** the test provides only the **sum** $X_k = X_{ls} + X_{lr}$.
Separation uses Table 1 of IEEE 112, according to the **NEMA class** selected below
(B = 40/60 is the standard for common industrial motors).

**Practical tips and precautions:**
- **Warning:** do not apply rated voltage with the rotor locked — the current would reach 5–8× $I_n$ and burn the windings in seconds.
- Perform the test **quickly** (a few seconds per point) to avoid overheating.
- If no variable-frequency source is available, a 60 Hz test is acceptable for educational purposes, but the error in $X_k$ may reach 5–10%.
- Typical $R_r$ value: similar to $R_s$ for Class B motors; much higher for Class D.
        """)

        st.markdown("---")
        st.markdown("""
**References:**
- IEEE Std 112-2017 — *Standard Test Procedure for Polyphase Induction Motors and Generators*, Cl. 6.
- Sen, P. C. — *Principles of Electric Machines and Power Electronics*, 3rd ed., §4.6 ("Determination of Equivalent Circuit Parameters").
- Fitzgerald/Umans — *Electric Machinery*, 7th ed., §6.5 ("Tests to Determine Equivalent Circuit Parameters").
        """)


def _render_ieee_test_inputs(
    wk: object, dis: bool, Vl: float, f: float, is_delta: bool,
) -> tuple[float, float, float, float, float, float, float, float, float, float, str, float]:
    """Three test input sections + Xls/Xlr distribution. Returns all test values."""
    _pgroup("[1] DC Test — Stator Resistance")
    c_dc1, c_dc2 = st.columns(2)
    V_dc = c_dc1.number_input(
        "Applied DC voltage — $V_{dc}$ (V)",
        min_value=0.01, max_value=1000.0, value=10.0, step=0.1, format="%.3f",
        key=wk.ieee_V_dc, disabled=dis,
        help="DC voltage applied between two motor terminals (cold resistance).",
    )
    I_dc = c_dc2.number_input(
        "Measured DC current — $I_{dc}$ (A)",
        min_value=0.001, max_value=10000.0, value=11.5, step=0.1, format="%.3f",
        key=wk.ieee_I_dc, disabled=dis,
        help="Stabilized DC current after the thermal transient.",
    )
    if I_dc > 0:
        Rs_prev = (V_dc / I_dc) * (1.5 if is_delta else 0.5)
        st.caption(f"$R_s$ calculated (preview): **{Rs_prev:.4f} Ω**")
    st.markdown('</div>', unsafe_allow_html=True)

    _pgroup("[2] No-Load Test")
    c_nl1, c_nl2 = st.columns(2)
    Vl_nl = c_nl1.number_input(
        "Line voltage — $V_{l,NL}$ (V)",
        min_value=10.0, max_value=15000.0, value=float(Vl), step=1.0, format="%.1f",
        key=wk.ieee_Vl_nl, disabled=dis,
        help="Line voltage applied during the no-load test (typically equal to rated).",
    )
    I_nl = c_nl2.number_input(
        "Line current — $I_{NL}$ (A)",
        min_value=0.001, max_value=10000.0, value=4.5, step=0.1, format="%.3f",
        key=wk.ieee_I_nl, disabled=dis,
        help="Steady-state line current, motor uncoupled.",
    )
    c_nl3, c_nl4 = st.columns(2)
    P_nl = c_nl3.number_input(
        "Three-phase power — $P_{NL}$ (W)",
        min_value=0.1, max_value=1e7, value=180.0, step=1.0, format="%.2f",
        key=wk.ieee_P_nl, disabled=dis,
        help="Total three-phase active power absorbed in the no-load test.",
    )
    f_nl = c_nl4.number_input(
        "Frequency — $f_{NL}$ (Hz)",
        min_value=1.0, max_value=400.0, value=float(f), step=1.0, format="%.2f",
        key=wk.ieee_f_nl, disabled=dis,
    )
    Pfw = st.number_input(
        "Mechanical losses — $P_{fw}$ (W) — 0 = estimate as 0.8% of $P_{NL}$",
        min_value=0.0, max_value=1e6, value=0.0, step=1.0, format="%.2f",
        key=wk.ieee_Pfw, disabled=dis,
        help="Friction + windage. If left at 0, the IEEE heuristic estimates 0.8% of P_NL.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    _pgroup("[3] Locked Rotor Test")
    c_lr1, c_lr2 = st.columns(2)
    Vl_lr = c_lr1.number_input(
        "Line voltage — $V_{l,LR}$ (V)",
        min_value=0.1, max_value=15000.0, value=31.68, step=0.1, format="%.2f",
        key=wk.ieee_Vl_lr, disabled=dis,
        help="Reduced voltage applied with rotor locked (caution: rated current).",
    )
    I_lr = c_lr2.number_input(
        "Line current — $I_{LR}$ (A)",
        min_value=0.001, max_value=10000.0, value=14.0, step=0.1, format="%.3f",
        key=wk.ieee_I_lr, disabled=dis,
        help="Line current measured with rotor locked.",
    )
    c_lr3, c_lr4 = st.columns(2)
    P_lr = c_lr3.number_input(
        "Three-phase power — $P_{LR}$ (W)",
        min_value=0.1, max_value=1e7, value=735.59, step=1.0, format="%.2f",
        key=wk.ieee_P_lr, disabled=dis,
    )
    f_lr = c_lr4.number_input(
        "Frequency — $f_{LR}$ (Hz)",
        min_value=1.0, max_value=400.0, value=15.0, step=0.5, format="%.2f",
        key=wk.ieee_f_lr, disabled=dis,
        help="IEEE Std 112 recommends f_LR ≈ 25% of rated frequency to minimize saturation.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    _pgroup("$X_{ls}$ / $X_{lr}$ Distribution")
    split_label = st.selectbox(
        "NEMA distribution class",
        list(MIT_IEEE_SPLIT_LABELS.values()),
        index=0,
        key=wk.ieee_split, disabled=dis,
        help="IEEE Std 112-2017, Table 1 — fraction of Xk assigned to Xls.",
    )
    split_code = next(k for k, v in MIT_IEEE_SPLIT_LABELS.items() if v == split_label)
    if split_code == "custom":
        Xls_frac = st.slider(
            "Fraction $X_{ls} / X_k$",
            min_value=0.10, max_value=0.90, value=0.40, step=0.05,
            key=wk.ieee_Xls_frac, disabled=dis,
        )
    else:
        Xls_frac = 0.4
    st.markdown('</div>', unsafe_allow_html=True)

    return V_dc, I_dc, Vl_nl, I_nl, P_nl, f_nl, Pfw, Vl_lr, I_lr, P_lr, f_lr, split_code, Xls_frac


def _render_ieee_results(
    result: dict,
    f_nl: float, f_lr: float,
    V_dc: float, I_dc: float,
    Pfw: float,
    Rs: float, Rr: float, Xm: float, Xls: float, Xlr: float, Rfe: float,
    is_delta: bool,
) -> None:
    """Calculation Details expander + sanity warnings (only called on success)."""
    ligacao = "Delta (Δ)" if is_delta else "Star (Y)"
    with st.expander("Calculation Details (IEEE Std 112-2017)", expanded=True):
        st.markdown(
            f"**Method:** IEEE Std 112-2017 — three physical tests. "
            f"**Connection:** {ligacao}. "
            f"**Distribution:** {MIT_IEEE_SPLIT_LABELS[result['split_used']]} "
            f"(fraction $X_{{ls}}/X_k$ = {result['Xls_frac']:.2f})."
        )

        st.markdown("##### Physical tests")
        t1, t2, t3 = st.columns(3)
        with t1:
            st.markdown("**DC Test**")
            st.markdown(f"$R_s$ = **{Rs:.4f} Ω**")
            st.caption(f"via $V_{{dc}}/I_{{dc}}$ = {(V_dc/I_dc):.4f} Ω")
        with t2:
            st.markdown("**No-Load Test**")
            st.markdown(
                f"$E_{{1,NL}}$ = **{result['E1_nl']:.2f} V**  \n"
                f"$P_{{fe,3φ}}$ = **{result['Pfe_3ph']:.2f} W**  \n"
                f"$P_{{fw}}$ = **{result['Pfw_used']:.2f} W**"
            )
            st.caption(
                "Pfw measured" if Pfw > 0
                else "Pfw via heuristic (0.8% · P_NL)"
            )
        with t3:
            st.markdown("**Locked Rotor Test**")
            st.markdown(
                f"$Z_k$ = **{result['Zk']:.4f} Ω**  \n"
                f"$R_k$ = **{result['Rk']:.4f} Ω**  \n"
                f"$X_k$ @ {f_nl:.0f} Hz = **{result['Xk']:.4f} Ω**"
            )
            st.caption(
                f"$X_{{k,LR}}$ = {result['Xk_lr']:.4f} Ω · "
                f"correction $f_{{NL}}/f_{{LR}}$ = {(f_nl/f_lr):.2f}"
            )

        st.divider()

        st.markdown("##### Intermediate indicators")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("E₁ (no-load)",          f"{result['E1_nl']:.2f} V")
        c2.metric("Iμ magnetizing current", f"{result['I_mu']:.3f} A")
        c3.metric("Pfe three-phase",        f"{result['Pfe_3ph']:.1f} W")
        c4.metric("Pfw used",               f"{result['Pfw_used']:.1f} W")

        st.markdown("##### Estimated parameters (equivalent circuit)")
        r1 = st.columns(3)
        r1[0].metric("Rₛ",  f"{Rs:.4f} Ω")
        r1[1].metric("Rᵣ",  f"{Rr:.4f} Ω")
        r1[2].metric("Xₘ",  f"{Xm:.4f} Ω")
        r2 = st.columns(3)
        r2[0].metric("Xₗₛ", f"{Xls:.4f} Ω")
        r2[1].metric("Xₗᵣ", f"{Xlr:.4f} Ω")
        r2[2].metric("Rfe", f"{Rfe:.1f} Ω")

    if Xm < 5.0 * Xls:
        st.warning(
            f"$X_m / X_{{ls}}$ = {Xm/Xls:.2f} < 5 — atypical ratio. "
            "Check the no-load test data."
        )
    if Rfe < 50.0:
        st.warning(
            f"$R_{{fe}}$ = {Rfe:.1f} Ω very low — check $P_{{NL}}$ "
            "and the mechanical loss separation (Pfw)."
        )


def render_params_ieee(wk: object, dis: bool) -> _ElecParams:
    """IEEE 112 MODE — three physical tests (DC + No-Load + Locked Rotor)."""
    Vl, f, is_delta = _render_ieee_grid_inputs(wk, dis)
    _render_ieee_guide(wk)
    V_dc, I_dc, Vl_nl, I_nl, P_nl, f_nl, Pfw, Vl_lr, I_lr, P_lr, f_lr, split_code, Xls_frac = (
        _render_ieee_test_inputs(wk, dis, Vl, f, is_delta)
    )

    result = _cached_estimate_ieee(
        V_dc, I_dc, is_delta,
        Vl_nl, I_nl, P_nl, f_nl,
        Vl_lr, I_lr, P_lr, f_lr,
        Pfw, split_code, Xls_frac,
    )

    if not result["success"]:
        st.error(
            f"Inconsistent IEEE tests: {result['error']}  "
            "Default parameters (Krause 3 HP) will be used."
        )
        Rs, Rr, Xm, Xls, Xlr = 0.435, 0.816, 26.13, 0.754, 0.754
        Rfe = _DEFAULTS["Rfe"]
    else:
        Rs  = result["Rs"]
        Rr  = result["Rr"]
        Xm  = result["Xm"]
        Xls = result["Xls"]
        Xlr = result["Xlr"]
        Rfe = result["Rfe"]
        _render_ieee_results(result, f_nl, f_lr, V_dc, I_dc, Pfw, Rs, Rr, Xm, Xls, Xlr, Rfe, is_delta)

        st.divider()
        if st.button(
            "✔ Use these parameters in the simulation",
            key="ieee_apply_btn",
            help="Copies the estimated parameters to Manual mode, allowing adjustments before simulating.",
        ):
            _p_tmp = int(st.session_state.get(wk.p, _DEFAULTS["p"]))
            _mp_tmp = MachineParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe, p=_p_tmp)
            _tl_tmp = _tl_sugerido(_mp_tmp)
            st.session_state["_param_source_idx"] = 0
            st.session_state[wk.Rs]  = Rs
            st.session_state[wk.Rr]  = Rr
            st.session_state[wk.Xm]  = Xm
            st.session_state[wk.Xls] = Xls
            st.session_state[wk.Xlr] = Xlr
            st.session_state[wk.Rfe] = Rfe
            st.session_state[wk.Tl_final] = _tl_tmp
            # wk.Tl_nom_dol exists on the _WidgetKeys dataclass — access via attribute
            if hasattr(wk, "Tl_nom_dol"):
                st.session_state[wk.Tl_nom_dol] = _tl_tmp
            st.rerun()

    return _ElecParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe,
                       f_ref=f, input_mode="X")
