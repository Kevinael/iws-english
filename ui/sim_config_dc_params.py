# -*- coding: utf-8 -*-
"""
sim_config_dc_params.py
=======================
Parameter-source sub-renderers for the DC machine configuration panel:
Nameplate (NEMA), IEEE 113 tests, and Manual (locked/editable).

Responsibilities:
  - Render nameplate estimator widgets (_render_dc_nameplate).
  - Render IEEE 113 test widgets and calculation details (_render_dc_ieee).
  - Render manual parameter inputs, locked or editable (_render_dc_manual*).
  - Expose _PARAM_SOURCE_RENDERERS dispatch table for the orchestrator.

Relationships:
  Imported by : ui.sim_config_dc
  Imports     : core.dc.facade, data.experiment_modes, data.ui_labels,
                ui.sim_config_dc_keys, ui._shared_widgets
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.dc.facade import DCMachineParams
from data.experiment_modes import DC_EXC_LABELS
from data.ui_labels import DC_PARAM_SOURCE_LABELS
from ui.sim_config_dc_keys import _WK_DC, _wi
from ui._shared_widgets import _pgroup, _ibox


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — MACHINE PARAMETERS (col_params) — private sub-renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_dc_nameplate(exc: str) -> None:
    """Renders nameplate estimator widgets and writes estimated values to session_state."""
    from core.dc.facade import estimate_dc_nameplate

    _pgroup("Nameplate Data (NEMA)")
    p1, p2, p3, p4 = st.columns(4)
    _wi(_WK_DC.Pn_kW, 0.5)
    _wi(_WK_DC.Vn_nameplate, 24.0)
    _wi(_WK_DC.nn_rpm, 6500.0)
    _wi(_WK_DC.eta_nameplate, 0.85)
    Pn_kW  = p1.number_input("$P_n$ (kW)",  min_value=0.001, key=_WK_DC.Pn_kW,    format="%.3f")
    Vn_p   = p2.number_input("$V_n$ (V)",   min_value=1.0,   key=_WK_DC.Vn_nameplate, format="%.1f")
    nn_rpm = p3.number_input("$n_n$ (RPM)", min_value=1.0,   key=_WK_DC.nn_rpm,   format="%.0f")
    eta_p  = p4.number_input("$\\eta$",     min_value=0.01, max_value=1.0,
                               key=_WK_DC.eta_nameplate, format="%.3f")
    est = estimate_dc_nameplate(Pn_kW * 1000, Vn_p, nn_rpm, eta_p, exc)
    for fld, wk in [("Ra", _WK_DC.Ra), ("La", _WK_DC.La), ("kb", _WK_DC.kb),
                    ("Va", _WK_DC.Va), ("Vf", _WK_DC.Vf), ("Rf", _WK_DC.Rf),
                    ("Lf", _WK_DC.Lf), ("J", _WK_DC.J), ("B", _WK_DC.B)]:
        if fld in est:
            st.session_state[wk] = est[fld]

    with st.expander("How were these parameters estimated? (NEMA heuristic)", expanded=False):
        is_shunt_nameplate = exc == "shunt_motor"
        st.info(
            f"**Method:** NEMA heuristic — estimation from nameplate data.  \n"
            f"**Excitation:** {DC_EXC_LABELS.get(exc, exc)}  \n"
            f"**Assumptions:** resistive drop ≈ 5–10% of $V_n$; "
            f"τ_a = L_a/R_a ≈ 0.8 s; τ_f = L_f/R_f ≈ 0.1 s."
        )
        _mp1, _mp2, _mp3, _mp4 = st.columns(4)
        _mp1.metric("Ra (Ω)",       f"{est['Ra']:.4f}")
        _mp2.metric("La (H)",       f"{est['La']:.4f}")
        _mp3.metric("kb (V·s/rad)", f"{est['kb']:.5f}")
        _mp4.metric("Va (V)",       f"{est['Va']:.2f}")
        if exc != "series_motor":
            _mc1, _mc2, _mc3 = st.columns(3)
            _Vf_est = est.get("Vf", est["Va"])
            if is_shunt_nameplate:
                _mc1.metric("Vf = Va (V)", f"{_Vf_est:.2f}")
            else:
                _mc1.metric("Vf (V)", f"{_Vf_est:.2f}")
            _mc2.metric("Rf (Ω)", f"{est.get('Rf', 0):.4f}")
            _mc3.metric("Lf (H)", f"{est.get('Lf', 0):.5f}")
        _mm1, _mm2 = st.columns(2)
        _mm1.metric("J (kg·m²)", f"{est.get('J', 0):.4f}")
        _mm2.metric("B (N·m·s)", f"{est.get('B', 0):.2e}")
        if est["Ra"] / max(est["Va"], 1e-6) < 0.005:
            st.warning("$R_a/V_a$ very low — check armature resistance.")
        if est["kb"] <= 0:
            st.error("$k_b$ ≤ 0 — impossible. Review Vn, nn or η.")


def _render_dc_ieee(exc: str) -> None:
    """Renders IEEE 113 test widgets and writes estimated values to session_state."""
    from core.dc.facade import estimate_dc_tests

    with st.expander("How to perform the IEEE 113 tests (procedure, formulas, and tips)", expanded=False):
        st.markdown("""
**Overview.** The IEEE Std 113-1985 method determines the equivalent circuit parameters of a
DC motor through **two complementary physical tests**:

| Test | IEEE 113 Section | Extracted parameters |
|------|-----------------|---------------------|
| **[1a] DC Armature** | Sec. 4.2.2.2 | $R_a$ |
| **[1b] DC Field** | Sec. 4.2.2.1 | $R_f$ (separately excited) |
| **[2] AC Armature** | Sec. 7.5.1 | $L_a$ (locked rotor, shorted field) |
| **[3] Field Step** | Sec. 7.5.3 | $L_f$ (time constant $\tau_f$) |
| **[4] No-Load** | Sec. 5.6 | $k_b$, $E_{a,nl}$, $R_f$ (shunt via $V_a/I_f$) |

Tests [2] and [3] are optional — if not performed, $L_a$ and $L_f$ are estimated
heuristically ($L_a = R_a \\cdot 0{.}8$; $L_f = R_f \\cdot 0{.}1$).
        """)

        st.markdown("### [1a] DC Test — Armature Resistance")
        st.markdown("""
**Objective.** Measure $R_a$ with the motor at rest and disconnected from the operating DC supply.

**Equipment.** Adjustable DC source, DC voltmeter, DC ammeter.

**Procedure (IEEE 113 Sec. 3):**
1. Ensure the motor is **cold** (at ambient temperature) — resistance varies ~0.4%/°C.
2. Connect the DC source between the **two armature terminals** (A1–A2).
3. Raise the voltage until the current reaches approximately **25% of $I_n$**.
4. Wait **1 minute** for thermal stabilization.
5. Record $V_{dc,a}$ and $I_{dc,a}$ simultaneously.

**Applied formula:**

$$R_a = \\frac{V_{dc,a}}{I_{dc,a}}$$

**Practical tips:**
- Do not exceed 25% of $I_n$ — higher currents heat the armature and distort $R_a$.
- Repeat the test at **3 different commutator positions** and use the average — avoids brush contact errors.
- Typical value: 0.01–5 Ω, depending on motor rating and voltage.
        """)

        st.markdown("### [1b] DC Test — Field Resistance (separately excited)")
        st.markdown("""
**Objective.** Measure $R_f$ with the field circuit isolated from the armature.

**Equipment.** Adjustable DC source, DC voltmeter, DC ammeter.

**Procedure (IEEE 113 Sec. 3):**
1. Ensure the motor is **cold** — disconnect the armature supply.
2. Connect the DC source between the **field terminals** (F1–F2).
3. Raise the voltage until the current reaches approximately **25% of $I_{f,n}$**.
4. Wait **1 minute** for thermal stabilization.
5. Record $V_{dc,f}$ and $I_{dc,f}$ simultaneously.

**Applied formula:**

$$R_f = \\frac{V_{dc,f}}{I_{dc,f}}$$

**Note:** For **shunt** excitation, $R_f$ is calculated from the no-load test: $R_f = V_{a,nl}/I_{fd,nl}$.

**Practical tips:**
- Typical value: 10–500 Ω for separately excited field (high resistance, low current).
- For shunt motors, the direct test is also valid and more accurate.
        """)

        st.markdown("### [2] AC Test — Armature Inductance (Sec. 7.5.1)")
        st.markdown("""
**Objective.** Measure $L_a$ by AC impedance with the rotor mechanically locked.

**Equipment.** Adjustable single-phase AC source (50 or 60 Hz), AC voltmeter, AC ammeter,
oscilloscope or wattmeter (for phase angle measurement).

**Procedure (IEEE 113 Sec. 7.5.1):**
1. **Lock the rotor** mechanically — it must not rotate during the test.
2. **Short-circuit the field winding** (shunt) to avoid induced overvoltages.
3. Apply single-phase AC voltage between the armature terminals (A1–A2).
4. Limit AC current to **≤ 20% of $I_n$** to avoid brush overheating.
5. Measure $V_{ac}$, $I_{ac}$, and phase angle $\\theta$ between voltage and current.

**Applied formula (IEEE 113 Sec. 7.5.1):**

$$L_a = \\frac{V_{ac} \\cdot \\sin\\theta}{I_{ac} \\cdot 2\\pi f}$$

**Practical tips:**
- Use an oscilloscope to observe the waveform and measure $\\theta$ accurately.
- Alternatively, use a wattmeter: $\\cos\\theta = P/(V_{ac}\\cdot I_{ac})$, so $\\sin\\theta = \\sqrt{1 - \\cos^2\\theta}$.
- Perform the test quickly — AC current heats brushes and commutator.
- If $\\theta = 0$, the inductance is negligible — check the circuit.
        """)

        st.markdown("### [3] Step Test — Field Inductance (Sec. 7.5.3)")
        st.markdown("""
**Objective.** Measure $L_f$ from the field time constant $\\tau_f$ (separately excited).

**Equipment.** Adjustable DC source, oscilloscope or recorder, fast switch.

**Procedure (IEEE 113 Sec. 7.5.3):**
1. Run the motor at rated speed in full field (armature open or unloaded).
2. Reduce field voltage to ~50% of rated value.
3. **Open the field circuit** and adjust the source to rated value $V_f$.
4. **Abruptly close** the circuit — apply a voltage step to the field.
5. Record $i_f(t)$ with an oscilloscope and determine $\\tau_f$ = time to reach **63.2%** of $I_{f,final}$.

**Applied formula (IEEE 113 Sec. 7.5.3):**

$$L_f = R_f \\cdot \\tau_f$$

**Practical tips:**
- Cycle the field twice between 50% and 100% before the test to stabilize saturation.
- The standard also defines $L_{f,ef}$ using armature voltage as a flux indicator — more accurate for saturated machines.
- Typical value: $\\tau_f$ = 0.1–2 s for industrial separately excited motors.
        """)

        st.markdown("### [4] No-Load Test — Machine Constant")
        st.markdown("""
**Objective.** Determine $k_b$ and $E_{a,nl}$ by operating the motor **with no mechanical load on the shaft**
at rated voltage and speed.

**Equipment.** Adjustable DC armature source, DC field source (separately excited),
DC voltmeter, DC ammeter, tachometer.

**Procedure (IEEE 113 Sec. 4):**
1. **Decouple** any mechanical load from the shaft (motor spins freely).
2. Apply rated armature voltage $V_{a,nom}$ and rated field current $I_{fd,nom}$.
3. Allow the motor to stabilize in speed (steady state).
4. Record $V_{a,nl}$, $I_{a,nl}$, $I_{fd,nl}$, and $n_{nl}$ (RPM).

**Applied formulas:**

$$E_{a,nl} = V_{a,nl} - R_a \\cdot I_{a,nl}$$

$$k_b = \\frac{E_{a,nl}}{I_{fd,nl} \\cdot \\omega_{nl}}, \\quad \\omega_{nl} = \\frac{2\\pi \\cdot n_{nl}}{60}$$

**About inductance $L_a$:**
- $L_a$ is not determined directly from the no-load test.
- The estimator applies the IEEE 113 heuristic: $\\tau_a = L_a/R_a \\approx 10\\text{–}50\\,\\text{ms}$ for industrial machines.
- For direct measurement, apply a voltage step to the armature (motor locked) and measure the current time constant.

**Practical tips:**
- Typical $I_{a,nl}$: 5–15% of $I_n$ (no-load losses dominated by friction and windage).
- Motors with **magnetic saturation** have variable $k_b$ with $I_{fd}$ — the test gives the value at the rated operating point.
- For **shunt** excitation, $I_{fd} = V_a / R_f$ — verify consistency with measured $R_f$.
        """)

        st.markdown("---")
        st.markdown("""
**References:**
- IEEE Std 113-1985 — *Guide on Test Procedures for DC Machines*, Sec. 4.2 (resistance), Sec. 5.6 (no-load), Sec. 7.5 (inductance).
- Sen, P. C. — *Principles of Electric Machines and Power Electronics*, 3rd ed., §7.3 ("Testing of DC Machines").
- Chapman, S. J. — *Electric Machinery Fundamentals*, 5th ed., §8.5 ("Determination of DC Motor Parameters").
        """)

    _pgroup("DC Resistance Test — Armature (IEEE 113 Sec. 3)")
    e1, e2 = st.columns(2)
    _wi(_WK_DC.V_dc_test, 1.0)
    _wi(_WK_DC.I_dc_test, 0.1)
    V_dc_t = e1.number_input("$V_{dc,a}$ (V)", min_value=0.001, key=_WK_DC.V_dc_test, format="%.3f")
    I_dc_t = e2.number_input("$I_{dc,a}$ (A)", min_value=0.001, key=_WK_DC.I_dc_test, format="%.3f")
    st.caption(f"→ $R_a$ ≈ **{V_dc_t / max(I_dc_t, 1e-9):.4f} Ω**")

    _is_sep_test = exc in ("sep_motor", "sep_gen")
    V_dc_f_t = 0.0
    I_dc_f_t = 0.0
    if _is_sep_test:
        _pgroup("DC Resistance Test — Field (IEEE 113 Sec. 3)")
        f1, f2 = st.columns(2)
        _wi(_WK_DC.V_dc_f_test, 1.0)
        _wi(_WK_DC.I_dc_f_test, 0.1)
        V_dc_f_t = f1.number_input("$V_{dc,f}$ (V)", min_value=0.001, key=_WK_DC.V_dc_f_test, format="%.3f")
        I_dc_f_t = f2.number_input("$I_{dc,f}$ (A)", min_value=0.001, key=_WK_DC.I_dc_f_test, format="%.3f")
        st.caption(f"→ $R_f$ ≈ **{V_dc_f_t / max(I_dc_f_t, 1e-9):.4f} Ω**")

    _pgroup("AC Test — Armature Inductance (IEEE 113 Sec. 7.5.1)")
    h1, h2, h3, h4 = st.columns(4)
    _wi(_WK_DC.V_ac_test,   0.0)
    _wi(_WK_DC.I_ac_test,   0.0)
    _wi(_WK_DC.theta_test,  0.0)
    _wi(_WK_DC.f_ac_test,  60.0)
    V_ac_t  = h1.number_input("$V_{ac}$ (V)",  min_value=0.0, key=_WK_DC.V_ac_test,  format="%.3f",
                               help="AC voltage applied to the armature (locked rotor, shorted field). 0 = use heuristic.")
    I_ac_t  = h2.number_input("$I_{ac}$ (A)",  min_value=0.0, key=_WK_DC.I_ac_test,  format="%.3f",
                               help="Measured AC current (≤ 20% of I_n per IEEE 113).")
    theta_t = h3.number_input("$\\theta$ (°)", min_value=0.0, max_value=90.0, key=_WK_DC.theta_test, format="%.1f",
                               help="Phase angle between V and I measured by oscilloscope or wattmeter.")
    f_ac_t  = h4.number_input("$f_{ac}$ (Hz)", min_value=1.0, key=_WK_DC.f_ac_test,  format="%.1f",
                               help="AC source frequency (50 or 60 Hz per IEEE 113).")
    if V_ac_t > 1e-9 and I_ac_t > 1e-9 and theta_t > 0.1:
        import math as _math
        _La_prev = V_ac_t * _math.sin(_math.radians(theta_t)) / (I_ac_t * 2 * _math.pi * max(f_ac_t, 1.0))
        st.caption(f"→ $L_a$ ≈ **{_La_prev*1000:.3f} mH**")
    else:
        st.caption("→ $L_a$: heuristic ($R_a \\cdot 0{.}8$) — provide $V_{{ac}}$, $I_{{ac}}$, $\\theta$ for IEEE 113 calculation.")

    tau_f_t = 0.0
    if _is_sep_test:
        _pgroup("Step Test — Field Inductance (IEEE 113 Sec. 7.5.3)")
        _wi(_WK_DC.tau_f_ms_test, 0.0)
        tau_f_t = st.number_input(
            "$\\tau_f$ measured (ms)", min_value=0.0, key=_WK_DC.tau_f_ms_test, format="%.1f",
            help="Time to 63.2% of final field current after voltage step. 0 = use heuristic (Rf·0.1).",
        )
        if tau_f_t > 1e-3:
            _Rf_prev = V_dc_f_t / max(I_dc_f_t, 1e-9)
            _Lf_prev = _Rf_prev * (tau_f_t / 1000.0)
            st.caption(f"→ $L_f$ ≈ **{_Lf_prev:.5f} H**  ($R_f \\cdot \\tau_f$ = {_Rf_prev:.4f}·{tau_f_t/1000:.4f})")
        else:
            st.caption("→ $L_f$: heuristic ($R_f \\cdot 0{.}1$) — provide $\\tau_f$ for IEEE 113 calculation.")

    _pgroup("No-Load Test (IEEE 113 Sec. 5.6)")
    g1, g2, g3, g4 = st.columns(4)
    _wi(_WK_DC.V_nl_test,  24.0)
    _wi(_WK_DC.I_nl_test,  0.05)
    _wi(_WK_DC.If_nl_test, 8.4)
    _wi(_WK_DC.n_nl_test,  6500.0)
    V_nl_t  = g1.number_input("$V_{a,nl}$ (V)",  min_value=0.01,  key=_WK_DC.V_nl_test,  format="%.3f")
    I_nl_t  = g2.number_input("$I_{a,nl}$ (A)",  min_value=0.001, key=_WK_DC.I_nl_test,  format="%.3f")
    If_nl_t = g3.number_input("$I_{fd,nl}$ (A)", min_value=0.001, key=_WK_DC.If_nl_test, format="%.3f")
    n_nl_t  = g4.number_input("$n_{nl}$ (RPM)",  min_value=1.0,   key=_WK_DC.n_nl_test,  format="%.1f")
    est = estimate_dc_tests(
        V_dc_t, I_dc_t, V_nl_t, I_nl_t, If_nl_t, n_nl_t, exc,
        V_dc_f=V_dc_f_t, I_dc_f=I_dc_f_t,
        V_ac=V_ac_t, I_ac=I_ac_t, theta_deg=theta_t, f_ac=f_ac_t,
        tau_f_ms=tau_f_t,
    )
    for fld, wk in [("Ra", _WK_DC.Ra), ("La", _WK_DC.La), ("kb", _WK_DC.kb),
                    ("Lf", _WK_DC.Lf), ("Rf", _WK_DC.Rf)]:
        if fld in est:
            st.session_state[wk] = est[fld]

    with st.expander("Calculation Details (IEEE Std 113-1985)", expanded=True):
        _exc_label_map = {
            "sep_motor": "Separately excited (motor)",
            "sep_gen":   "Separately excited (generator)",
            "shunt":     "Shunt",
            "series_motor": "Series",
        }
        st.markdown(
            f"**Method:** IEEE Std 113-1985 — two physical tests. "
            f"**Configuration:** {_exc_label_map.get(exc, exc)}."
        )
        st.markdown("##### Physical tests")
        _has_rf = "Rf" in est
        _t1, _t2, *_t3 = st.columns(3 if _has_rf else 2)
        with _t1:
            st.markdown("**DC Test — Armature**")
            st.markdown(f"$R_a$ = **{est['Ra']:.4f} Ω**")
            st.caption(f"via $V_{{dc,a}}/I_{{dc,a}}$ = {V_dc_t / max(I_dc_t, 1e-9):.4f} Ω")
        if _has_rf and _t3:
            with _t3[0]:
                st.markdown("**DC Test — Field**")
                st.markdown(f"$R_f$ = **{est['Rf']:.4f} Ω**")
                st.caption(f"via $V_{{dc,f}}/I_{{dc,f}}$ = {V_dc_f_t / max(I_dc_f_t, 1e-9):.4f} Ω")
        with _t2:
            _wm_nl = n_nl_t * (2 * 3.14159265 / 60)
            st.markdown("**No-Load Test**")
            st.markdown(
                f"$E_{{a,nl}}$ = **{est['Ea_nl']:.3f} V**  \n"
                f"$\\omega_{{nl}}$ = **{_wm_nl:.2f} rad/s**  \n"
                f"$k_b$ = **{est['kb']:.5f} V·s/rad**"
            )
            st.caption(
                f"via $E_{{a,nl}} = V_{{a,nl}} - R_a \\cdot I_{{a,nl}}$ "
                f"= {V_nl_t:.3f} − {est['Ra']:.4f}·{I_nl_t:.3f}"
            )
        st.divider()
        st.markdown("##### Intermediate indicators")
        _tau_a = est["La"] / max(est["Ra"], 1e-9)
        _im_c1, _im_c2, _im_c3, _im_c4 = st.columns(4)
        _im_c1.metric("Ea_nl (V)",        f"{est['Ea_nl']:.3f}")
        _im_c2.metric("ω_nl (rad/s)",     f"{_wm_nl:.2f}")
        _im_c3.metric("τ_a = La/Ra (ms)", f"{_tau_a * 1000:.2f}")
        if exc in ("sep_motor", "sep_gen"):
            _Lf_est = est.get("Lf", 0.0)
            _Rf_est = float(st.session_state.get(_WK_DC.Rf, 1.0))
            _tau_f  = _Lf_est / max(_Rf_est, 1e-9)
            _im_c4.metric("τ_f = Lf/Rf (ms)", f"{_tau_f * 1000:.2f}")
        st.markdown("##### Estimated parameters (equivalent circuit)")
        _p1 = st.columns(3)
        _p1[0].metric("Ra (Ω)",       f"{est['Ra']:.4f}")
        _p1[1].metric("La (H)",       f"{est['La']:.5f}")
        _p1[2].metric("kb (V·s/rad)", f"{est['kb']:.5f}")
        if exc in ("sep_motor", "sep_gen"):
            _p2 = st.columns(3)
            _p2[0].metric("Lf (H)",    f"{est.get('Lf', 0):.5f}")
            _p2[1].metric("Rf (Ω)",    f"{est.get('Rf', 0):.4f}" if "Rf" in est else "—")
            _p2[2].metric("If_nl (A)", f"{If_nl_t:.4f}")
        elif exc == "shunt_motor" and "Rf" in est:
            _p2 = st.columns(3)
            _p2[0].metric("Lf (H)",    f"{est.get('Lf', 0):.5f}")
            _p2[1].metric("Rf (Ω)",    f"{est['Rf']:.4f}")
            _p2[2].metric("If_nl (A)", f"{If_nl_t:.4f}")
        if est["kb"] <= 0:
            st.error("$k_b$ ≤ 0 — impossible. Check $V_{a,nl}$, $R_a$ and $I_{a,nl}$.")
        if est["Ra"] / max(V_nl_t, 1e-6) > 0.3:
            st.warning("$R_a/V_{a,nl}$ > 30% — Ra appears high for this operating voltage.")

    if st.button(
        "✔ Use these parameters in the simulation",
        key="btn_dc_use_tests",
        help="Copies the estimated parameters to Manual mode, allowing adjustments before simulating.",
    ):
        for fld, wk in [("Ra", _WK_DC.Ra), ("La", _WK_DC.La), ("kb", _WK_DC.kb), ("Lf", _WK_DC.Lf)]:
            if fld in est:
                st.session_state[wk] = est[fld]
        st.session_state[_WK_DC.input_mode] = "Enter parameters manually"
        st.rerun()


def _render_dc_manual_locked(exc: str) -> dict[str, float]:
    """Renders locked (experiment_mode) parameter summary. Returns parameter dict."""
    is_gen    = exc in ("sep_gen", "shunt_gen")
    is_sep    = exc in ("sep_motor", "sep_gen")
    is_series = exc == "series_motor"

    va    = float(st.session_state.get(_WK_DC.Va,    24.0))
    ra    = float(st.session_state.get(_WK_DC.Ra,    0.013))
    la    = float(st.session_state.get(_WK_DC.La,    0.01))
    vf    = float(st.session_state.get(_WK_DC.Vf,    va if not is_sep else 12.0))
    rf    = float(st.session_state.get(_WK_DC.Rf,    1.43))
    lf    = float(st.session_state.get(_WK_DC.Lf,    0.167))
    rl    = float(st.session_state.get(_WK_DC.Rl,    0.0))
    ll    = float(st.session_state.get(_WK_DC.Ll,    0.0))
    kb    = float(st.session_state.get(_WK_DC.kb,    0.004))
    J     = float(st.session_state.get(_WK_DC.J,     0.21))
    B     = float(st.session_state.get(_WK_DC.B,     1.074e-6))
    Tload = float(st.session_state.get(_WK_DC.Tload, 2.493))

    st.info(
        "**Parameters locked** — disable the toggle at the top of the page to edit.  "
        "Experiment variations (load, voltage) will not affect the machine."
    )

    st.markdown('<p class="slabel">Armature Parameters</p>', unsafe_allow_html=True)
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Va (V)",       f"{va:.3f}")
    e2.metric("Ra (Ω)",       f"{ra:.4f}")
    e3.metric("La (H)",       f"{la:.4f}")
    e4.metric("kb (V·s/rad)", f"{kb:.4f}")

    if not is_series:
        st.markdown('<p class="slabel">Field Parameters</p>', unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        if is_sep:
            f1.metric("Vf (V)", f"{vf:.3f}")
        else:
            f1.metric("Vf = Va (V)", f"{va:.3f}")
        f2.metric("Rf (Ω)", f"{rf:.4f}")
        f3.metric("Lf (H)", f"{lf:.4f}")
    else:
        st.markdown('<p class="slabel">Series Field</p>', unsafe_allow_html=True)
        s1, s2 = st.columns(2)
        s1.metric("Rf_s (Ω)", f"{rf:.4f}")
        s2.metric("Lf_s (H)", f"{lf:.4f}")

    if is_gen:
        st.markdown('<p class="slabel">Electrical Load</p>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        g1.metric("Rl (Ω)", f"{rl:.3f}")
        g2.metric("Ll (H)", f"{ll:.4f}")

    st.markdown('<p class="slabel">Mechanical Parameters</p>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("J (kg·m²)", f"{J:.4f}")
    m2.metric("B (N·m·s)", f"{B:.2e}")
    m3.metric("Tl (N·m)",  f"{Tload:.4f}")

    return dict(va=va, ra=ra, la=la, vf=vf, rf=rf, lf=lf, rl=rl, ll=ll, kb=kb, J=J, B=B, Tload=Tload)


def _render_dc_manual_editable(exc: str, input_mode: str) -> dict[str, float]:
    """Renders editable parameter inputs for manual/nameplate/IEEE modes. Returns parameter dict."""
    is_gen    = exc in ("sep_gen", "shunt_gen")
    is_sep    = exc in ("sep_motor", "sep_gen")
    is_series = exc == "series_motor"

    _wi(_WK_DC.Va,    24.0)
    _wi(_WK_DC.Ra,    0.013)
    _wi(_WK_DC.La,    0.01)
    _wi(_WK_DC.Vf,    12.0)
    _wi(_WK_DC.Rf,    1.43)
    _wi(_WK_DC.Lf,    0.167)
    _wi(_WK_DC.Rl,    0.0)
    _wi(_WK_DC.Ll,    0.0)
    _wi(_WK_DC.kb,    0.004)
    _wi(_WK_DC.J,     0.21)
    _wi(_WK_DC.B,     1.074e-6)
    _wi(_WK_DC.Tload, 2.493)

    _is_manual    = (input_mode == "Enter parameters manually")
    _is_nameplate = (input_mode == "Estimate from nameplate data")

    if _is_manual:
        _pgroup("Armature Data")
        va = st.number_input(
            "Armature voltage — $V_a$ (V)",
            min_value=0.0, key=_WK_DC.Va, format="%.3f",
            help="DC voltage applied to the armature winding.",
        )
        ra = st.number_input(
            "Armature resistance — $R_a$ (Ω)",
            min_value=1e-6, key=_WK_DC.Ra, format="%.4f",
            help="Armature winding resistance (including brushes). Affects Joule losses and starting current.",
        )
        la = st.number_input(
            "Armature inductance — $L_a$ (H)",
            min_value=1e-6, key=_WK_DC.La, format="%.4f",
            help="Armature circuit inductance. Determines electrical time constant τ_a = L_a / R_a.",
        )
        kb = st.number_input(
            "Back-EMF constant — $k_b$ (V·s/rad)",
            min_value=1e-6, key=_WK_DC.kb, format="%.4f",
            help="Relates back-EMF (Ea) and angular velocity: Ea = kb · ωm. Also equal to torque constant kt.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if not is_series:
            _pgroup("Field Data")
            if is_sep:
                vf = st.number_input(
                    "Field voltage — $V_f$ (V)",
                    min_value=0.0, key=_WK_DC.Vf, format="%.3f",
                    help="Independent field source voltage (separately excited).",
                )
            else:
                vf = va
                st.caption("Shunt: $V_f = V_a$ (fixed — field in parallel with armature)")
            rf = st.number_input(
                "Field resistance — $R_f$ (Ω)",
                min_value=1e-6, key=_WK_DC.Rf, format="%.4f",
                help="Total field circuit resistance (winding + field rheostat).",
            )
            lf = st.number_input(
                "Field inductance — $L_f$ (H)",
                min_value=1e-6, key=_WK_DC.Lf, format="%.4f",
                help="Field winding inductance. Determines τ_f = L_f / R_f.",
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            _pgroup("Series Field (in series with armature)")
            rf = st.number_input(
                "Series field resistance — $R_s$ (Ω)",
                min_value=1e-6, key=_WK_DC.Rf, format="%.4f",
                help="Series field winding resistance (in series with the armature).",
            )
            lf = st.number_input(
                "Series field inductance — $L_s$ (H)",
                min_value=1e-6, key=_WK_DC.Lf, format="%.4f",
                help="Series field winding inductance.",
            )
            vf = 0.0
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        ra = float(st.session_state.get(_WK_DC.Ra, 0.013))
        la = float(st.session_state.get(_WK_DC.La, 0.01))
        kb = float(st.session_state.get(_WK_DC.kb, 0.004))
        lf = float(st.session_state.get(_WK_DC.Lf, 0.167))

        if _is_nameplate:
            va = float(st.session_state.get(_WK_DC.Va, 24.0))
            rf = float(st.session_state.get(_WK_DC.Rf, 1.43))
            vf = float(st.session_state.get(_WK_DC.Vf, va if not is_sep else 12.0))
        else:
            # IEEE 113: Va and Vf not estimated — editable; Rf estimated from DC field test
            _pgroup("Armature Data")
            va = st.number_input(
                "Armature voltage — $V_a$ (V)",
                min_value=0.0, key=_WK_DC.Va, format="%.3f",
                help="DC voltage applied to the armature winding.",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            if not is_series:
                _pgroup("Field Data")
                if is_sep:
                    vf = st.number_input(
                        "Field voltage — $V_f$ (V)",
                        min_value=0.0, key=_WK_DC.Vf, format="%.3f",
                        help="Independent field source voltage (separately excited).",
                    )
                    rf = float(st.session_state.get(_WK_DC.Rf, 1.43))
                else:
                    vf = va
                    st.caption("Shunt: $V_f = V_a$ (fixed — field in parallel with armature)")
                    rf = float(st.session_state.get(_WK_DC.Rf, 1.43))
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                _pgroup("Series Field (in series with armature)")
                rf = st.number_input(
                    "Series field resistance — $R_s$ (Ω)",
                    min_value=1e-6, key=_WK_DC.Rf, format="%.4f",
                    help="Series field winding resistance (in series with the armature).",
                )
                vf = 0.0
                st.markdown('</div>', unsafe_allow_html=True)

    if is_gen:
        _pgroup("Electrical Load")
        rl = st.number_input(
            "Load resistance — $R_l$ (Ω)",
            min_value=1e-6, key=_WK_DC.Rl, format="%.3f",
            help="Load resistance connected to the generator.",
        )
        ll = st.number_input(
            "Load inductance — $L_l$ (H)",
            min_value=0.0, key=_WK_DC.Ll, format="%.4f",
            help="Load inductance connected to the generator (0 for purely resistive load).",
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        rl = float(st.session_state.get(_WK_DC.Rl, 0.0))
        ll = float(st.session_state.get(_WK_DC.Ll, 0.0))

    if _is_nameplate:
        J     = float(st.session_state.get(_WK_DC.J,     0.21))
        B     = float(st.session_state.get(_WK_DC.B,     1.074e-6))
        Tload = float(st.session_state.get(_WK_DC.Tload, 2.493))
    else:
        _pgroup("Mechanical Data")
        J = st.number_input(
            "Moment of inertia — $J$ (kg·m²)",
            min_value=1e-6, key=_WK_DC.J, format="%.4f",
            help="Total inertia of motor + load assembly. Determines τ_m = J·Ra / kb².",
        )
        B = st.number_input(
            "Viscous friction coeff. — $B$ (N·m·s/rad)",
            min_value=0.0, key=_WK_DC.B, format="%.2e",
            help="Viscous friction coefficient. Typically very small.",
        )
        Tload = st.number_input(
            "Load torque — $T_l$ (N·m)",
            min_value=0.0, key=_WK_DC.Tload, format="%.4f",
            help="Steady-state resistive torque applied to the shaft.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    _tau_a_ms = (la / max(ra, 1e-9)) * 1000
    _n0_rpm   = (va / max(kb, 1e-9)) * (60 / (2 * 3.14159265)) - (B * va / max(kb**2, 1e-9)) * (60 / (2 * 3.14159265))
    _d1, _d2, _d3 = st.columns(3)
    _d1.metric("τ_a (ms)",      f"{_tau_a_ms:.2f}",         help="Armature electrical time constant = La/Ra")
    if not is_series and lf > 0 and rf > 0:
        _tau_f_ms = (lf / max(rf, 1e-9)) * 1000
        _d2.metric("τ_f (ms)", f"{_tau_f_ms:.2f}",          help="Field circuit time constant = Lf/Rf")
    else:
        _d2.metric("τ_f (ms)", "—",                         help="Not applicable for series motor")
    _d3.metric("n₀ est. (RPM)", f"{max(_n0_rpm, 0):.0f}",  help="Estimated no-load speed (steady state)")

    with st.expander("Advanced Parameters", expanded=False):
        _pgroup("Economic Analysis")
        _wi(_WK_DC.energy_tariff, 0.75)
        st.number_input(
            "Energy tariff — $/kWh",
            min_value=0.0001, max_value=5.0,
            step=0.01, format="%.4f",
            key=_WK_DC.energy_tariff,
            help="Tariff used to calculate annual operating cost in the Asset Management tab.",
        )

    return dict(va=va, ra=ra, la=la, vf=vf, rf=rf, lf=lf, rl=rl, ll=ll, kb=kb, J=J, B=B, Tload=Tload)


def _render_dc_manual(exc: str, experiment_mode: bool, input_mode: str) -> dict[str, float]:
    """Dispatches to locked or editable manual renderer. Returns parameter dict."""
    if experiment_mode:
        return _render_dc_manual_locked(exc)
    return _render_dc_manual_editable(exc, input_mode)


# ── Dispatch table: input_mode label → renderer ──────────────────────────────
# Renderers for nameplate and IEEE only run when not experiment_mode.
# Manual renderer handles both locked and editable internally.
_PARAM_SOURCE_RENDERERS: dict[str, Any] = {
    DC_PARAM_SOURCE_LABELS[0]: _render_dc_manual,    # "Enter parameters manually"
    DC_PARAM_SOURCE_LABELS[1]: _render_dc_nameplate, # "Estimate from nameplate data"
    DC_PARAM_SOURCE_LABELS[2]: _render_dc_ieee,      # "Determine from IEEE 113 tests"
}
