# -*- coding: utf-8 -*-
"""
sim_config_dc.py
================
DC machine selector, parameter inputs, and experiment configuration widgets.

Responsibilities:
  - Render DCM parameter selector by excitation type (render_dc_machine_params).
  - Render mode and variable selection for DCM experiments (render_experiment_config_dc).
  - Expose _PRESETS_BY_EXC with motor and generator presets keyed by excitation type.

Relationships:
  Imported by : IWS_UI
  Imports     : core.dc.machine_model, data.machines_dc

Extending:
  - To add a new DCM preset, edit data/machines_dc.py — DC_PRESETS_BY_EXC dict.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
import streamlit as st

from core.dc.machine_model import DCMachineParams
from data.machines_dc import DC_PRESETS_BY_EXC, DC_PRESETS_FLAT
from data.experiment_modes import (
    DC_MODES_BY_EXC,
    DC_MODE_LABELS,
    DC_BRAKE_LABELS,
    DC_EXC_LABELS,
)
from data.ui_labels import DC_PARAM_SOURCE_LABELS
from data.variable_labels import (
    DC_VAR_MECANICAS,
    DC_VAR_ELETRICAS,
    DC_VAR_OPTIONS,
    DC_DEFAULT_VARS_MEC,
    DC_DEFAULT_VARS_ELE,
    DC_DEFAULT_VARS,
)


# ─────────────────────────────────────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────────────────────────────────────

_PRESETS_BY_EXC: dict[str, dict[str, dict[str, Any]]] = DC_PRESETS_BY_EXC
_PRESETS_DC: dict[str, dict[str, Any]] = DC_PRESETS_FLAT


# ─────────────────────────────────────────────────────────────────────────────
# WIDGET KEYS
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class _WidgetKeysDC:
    # machine parameters
    Va:            str = "wi_dc_Va"
    Ra:            str = "wi_dc_Ra"
    La:            str = "wi_dc_La"
    kb:            str = "wi_dc_kb"
    Vf:            str = "wi_dc_Vf"
    Rf:            str = "wi_dc_Rf"
    Lf:            str = "wi_dc_Lf"
    Rl:            str = "wi_dc_Rl"
    Ll:            str = "wi_dc_Ll"
    J:             str = "wi_dc_J"
    B:             str = "wi_dc_B"
    Tload:         str = "wi_dc_Tload"
    # selector / mode
    excitation:    str = "wi_dc_excitation"
    preset:        str = "wi_dc_preset"
    input_mode:    str = "wi_dc_input_mode"
    # nameplate estimator
    Pn_kW:         str = "wi_dc_Pn_kW"
    Vn_placa:      str = "wi_dc_Vn_placa"
    nn_rpm:        str = "wi_dc_nn_rpm"
    eta_placa:     str = "wi_dc_eta_placa"
    # DC resistance tests
    V_dc_test:     str = "wi_dc_V_dc_test"
    I_dc_test:     str = "wi_dc_I_dc_test"
    V_dc_f_test:   str = "wi_dc_V_dc_f_test"
    I_dc_f_test:   str = "wi_dc_I_dc_f_test"
    # AC inductance tests
    V_ac_test:     str = "wi_dc_V_ac_test"
    I_ac_test:     str = "wi_dc_I_ac_test"
    theta_test:    str = "wi_dc_theta_test"
    f_ac_test:     str = "wi_dc_f_ac_test"
    # field step / no-load tests
    tau_f_ms_test: str = "wi_dc_tau_f_ms_test"
    V_nl_test:     str = "wi_dc_V_nl_test"
    I_nl_test:     str = "wi_dc_I_nl_test"
    If_nl_test:    str = "wi_dc_If_nl_test"
    n_nl_test:     str = "wi_dc_n_nl_test"
    # economics
    energy_tariff: str = "wi_dc_energy_tariff"
    # experiment — DOL
    dol_vazio:     str = "wi_dc_dol_vazio"
    dol_t_carga:   str = "wi_dc_dol_t_carga"
    # experiment — series resistance
    R_ini:         str = "wi_dc_R_ini"
    t_ramp:        str = "wi_dc_t_ramp"
    # experiment — braking
    brake_method:  str = "wi_dc_brake_method"
    t_freia:       str = "wi_dc_t_freia"
    Vdc_inj:       str = "wi_dc_Vdc_inj"
    Va_regen:      str = "wi_dc_Va_regen"
    # experiment — field weakening
    Vf_fraco:      str = "wi_dc_Vf_fraco"
    t_campo:       str = "wi_dc_t_campo"
    t_trans:       str = "wi_dc_t_trans"
    # experiment — load pulse
    t_pulso:       str = "wi_dc_t_pulso"
    Tl_extra:      str = "wi_dc_Tl_extra"
    # experiment — generator
    Tl_gen:        str = "wi_dc_Tl_gen"
    # variable selection
    vars_mec:      str = "wi_dc_vars_mec"
    vars_ele:      str = "wi_dc_vars_ele"
    # simulation settings
    tmax_auto:     str = "wi_dc_tmax_auto"
    tmax:          str = "wi_dc_tmax"
    h:             str = "wi_dc_h"


_WK_DC = _WidgetKeysDC()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _pgroup(title: str) -> None:
    st.markdown(f'<div class="pgroup-title">{title}</div>', unsafe_allow_html=True)


def _ibox(html: str) -> None:
    st.markdown(f'<div class="ibox">{html}</div>', unsafe_allow_html=True)


def _wi(key: str, default: Any) -> None:
    """Initializes session_state if absent."""
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — MACHINE PARAMETERS (col_params)
# ─────────────────────────────────────────────────────────────────────────────

def render_dc_machine_params(dark: bool, experiment_mode: bool) -> tuple[DCMachineParams, int, float]:
    """Renders DC machine parameter selector.

    Returns (DCMachineParams, ref_code, energy_tariff).
    ref_code: integer hash for cache invalidation.
    energy_tariff: $/kWh tariff read from Advanced Parameters.
    """
    from core.dc.estimator import estimate_dc_nameplate, estimate_dc_tests

    st.markdown('<p class="slabel">Machine Parameters</p>', unsafe_allow_html=True)

    # ── Automatic default preset load on first open ───────────────────────────
    if _WK_DC.Va not in st.session_state:
        _default_preset = _PRESETS_BY_EXC["sep_motor"]["Sep. Motor 220 V — Sen Ex. 9.2"]
        for k, v in _default_preset.items():
            st.session_state[f"wi_dc_{k}"] = v
        st.session_state[_WK_DC.excitation] = "sep_motor"
        st.session_state[_WK_DC.preset]     = "Sep. Motor 220 V — Sen Ex. 9.2"
        st.rerun()

    # ── Excitation configuration ──────────────────────────────────────────────
    _wi(_WK_DC.excitation, "sep_motor")
    exc_options = list(DC_EXC_LABELS.keys())
    exc_labels  = [DC_EXC_LABELS[k] for k in exc_options]
    exc_stored  = st.session_state.get(_WK_DC.excitation, "sep_motor")
    exc_idx     = exc_options.index(exc_stored) if exc_stored in exc_options else 0

    exc_label_sel = st.selectbox(
        "Configuration", exc_labels, index=exc_idx,
        key="_dc_exc_sel", label_visibility="visible",
        disabled=experiment_mode,
    )
    exc = exc_options[exc_labels.index(exc_label_sel)]
    st.session_state[_WK_DC.excitation] = exc

    # ── Data source: Manual / Nameplate / Tests ───────────────────────────────
    _wi(_WK_DC.input_mode, DC_PARAM_SOURCE_LABELS[0])
    input_mode = st.radio(
        "Data source", DC_PARAM_SOURCE_LABELS,
        index=DC_PARAM_SOURCE_LABELS.index(
            st.session_state.get(_WK_DC.input_mode, DC_PARAM_SOURCE_LABELS[0])
        ),
        horizontal=True, key=_WK_DC.input_mode,
        disabled=experiment_mode,
    )

    if input_mode == "Estimate from nameplate data" and not experiment_mode:
        _pgroup("Nameplate Data (NEMA)")
        p1, p2, p3, p4 = st.columns(4)
        _wi(_WK_DC.Pn_kW, 0.5)
        _wi(_WK_DC.Vn_placa, 24.0)
        _wi(_WK_DC.nn_rpm, 6500.0)
        _wi(_WK_DC.eta_placa, 0.85)
        Pn_kW    = p1.number_input("$P_n$ (kW)",  min_value=0.001, key=_WK_DC.Pn_kW,     format="%.3f")
        Vn_p     = p2.number_input("$V_n$ (V)",   min_value=1.0,   key=_WK_DC.Vn_placa,  format="%.1f")
        nn_rpm   = p3.number_input("$n_n$ (RPM)", min_value=1.0,   key=_WK_DC.nn_rpm,    format="%.0f")
        eta_p    = p4.number_input("$\\eta$",      min_value=0.01, max_value=1.0,
                                    key=_WK_DC.eta_placa, format="%.3f")
        est = estimate_dc_nameplate(Pn_kW * 1000, Vn_p, nn_rpm, eta_p, exc)
        for fld, wk in [("Ra",_WK_DC.Ra),("La",_WK_DC.La),("kb",_WK_DC.kb),
                        ("Va",_WK_DC.Va),("Vf",_WK_DC.Vf),("Rf",_WK_DC.Rf),
                        ("Lf",_WK_DC.Lf),("J",_WK_DC.J),("B",_WK_DC.B)]:
            if fld in est:
                st.session_state[wk] = est[fld]

        with st.expander("How were these parameters estimated? (NEMA heuristic)", expanded=False):
            is_sep_placa  = exc in ("sep_motor", "sep_gen")
            is_shunt_placa = exc == "shunt_motor"
            _wm_n = nn_rpm * (2 * 3.14159265 / 60)
            _In   = (Pn_kW * 1000) / (Vn_p * max(eta_p, 0.01))
            _Ea_n = Vn_p - est["Ra"] * _In
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
            if not (exc == "series_motor"):
                _mc1, _mc2, _mc3 = st.columns(3)
                _Vf_est = est.get("Vf", est["Va"])
                if is_shunt_placa:
                    _mc1.metric("Vf = Va (V)", f"{_Vf_est:.2f}")
                else:
                    _mc1.metric("Vf (V)",  f"{_Vf_est:.2f}")
                _mc2.metric("Rf (Ω)",  f"{est.get('Rf', 0):.4f}")
                _mc3.metric("Lf (H)",  f"{est.get('Lf', 0):.5f}")
            _mm1, _mm2 = st.columns(2)
            _mm1.metric("J (kg·m²)", f"{est.get('J', 0):.4f}")
            _mm2.metric("B (N·m·s)", f"{est.get('B', 0):.2e}")
            # Sanity warnings
            if est["Ra"] / max(est["Va"], 1e-6) < 0.005:
                st.warning("$R_a/V_a$ very low — check armature resistance.")
            if est["kb"] <= 0:
                st.error("$k_b$ ≤ 0 — impossible. Review Vn, nn or η.")

    elif input_mode == "Determine from IEEE 113 tests" and not experiment_mode:
        # Procedure guide (collapsed by default)
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
        _Ra_preview = V_dc_t / max(I_dc_t, 1e-9)
        st.caption(f"→ $R_a$ ≈ **{_Ra_preview:.4f} Ω**")

        # DC field test — only for separately excited (IEEE 113 Sec. 3, terminals F1–F2)
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
            _Rf_preview = V_dc_f_t / max(I_dc_f_t, 1e-9)
            st.caption(f"→ $R_f$ ≈ **{_Rf_preview:.4f} Ω**")

        # AC armature inductance test (IEEE 113 Sec. 7.5.1)
        _pgroup("AC Test — Armature Inductance (IEEE 113 Sec. 7.5.1)")
        h1, h2, h3, h4 = st.columns(4)
        _wi(_WK_DC.V_ac_test,    0.0)
        _wi(_WK_DC.I_ac_test,    0.0)
        _wi(_WK_DC.theta_test,   0.0)
        _wi(_WK_DC.f_ac_test,   60.0)
        V_ac_t     = h1.number_input("$V_{ac}$ (V)",   min_value=0.0, key=_WK_DC.V_ac_test,  format="%.3f",
                                     help="AC voltage applied to the armature (locked rotor, shorted field). 0 = use heuristic.")
        I_ac_t     = h2.number_input("$I_{ac}$ (A)",   min_value=0.0, key=_WK_DC.I_ac_test,  format="%.3f",
                                     help="Measured AC current (≤ 20% of I_n per IEEE 113).")
        theta_t    = h3.number_input("$\\theta$ (°)",  min_value=0.0, max_value=90.0, key=_WK_DC.theta_test, format="%.1f",
                                     help="Phase angle between V and I measured by oscilloscope or wattmeter.")
        f_ac_t     = h4.number_input("$f_{ac}$ (Hz)",  min_value=1.0, key=_WK_DC.f_ac_test,  format="%.1f",
                                     help="AC source frequency (50 or 60 Hz per IEEE 113).")
        if V_ac_t > 1e-9 and I_ac_t > 1e-9 and theta_t > 0.1:
            import math as _math
            _La_prev = V_ac_t * _math.sin(_math.radians(theta_t)) / (I_ac_t * 2 * _math.pi * max(f_ac_t, 1.0))
            st.caption(f"→ $L_a$ ≈ **{_La_prev*1000:.3f} mH**")
        else:
            st.caption("→ $L_a$: heuristic ($R_a \\cdot 0{.}8$) — provide $V_{{ac}}$, $I_{{ac}}$, $\\theta$ for IEEE 113 calculation.")

        # Field step test — field inductance (IEEE 113 Sec. 7.5.3)
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
        else:
            tau_f_t = 0.0

        _pgroup("No-Load Test (IEEE 113 Sec. 5.6)")
        g1, g2, g3, g4 = st.columns(4)
        _wi(_WK_DC.V_nl_test,  24.0)
        _wi(_WK_DC.I_nl_test,  0.05)
        _wi(_WK_DC.If_nl_test, 8.4)
        _wi(_WK_DC.n_nl_test,  6500.0)
        V_nl_t  = g1.number_input("$V_{a,nl}$ (V)",    min_value=0.01,  key=_WK_DC.V_nl_test,  format="%.3f")
        I_nl_t  = g2.number_input("$I_{a,nl}$ (A)",    min_value=0.001, key=_WK_DC.I_nl_test,  format="%.3f")
        If_nl_t = g3.number_input("$I_{fd,nl}$ (A)",   min_value=0.001, key=_WK_DC.If_nl_test, format="%.3f")
        n_nl_t  = g4.number_input("$n_{nl}$ (RPM)",    min_value=1.0,   key=_WK_DC.n_nl_test,  format="%.1f")
        est = estimate_dc_tests(
            V_dc_t, I_dc_t, V_nl_t, I_nl_t, If_nl_t, n_nl_t, exc,
            V_dc_f=V_dc_f_t, I_dc_f=I_dc_f_t,
            V_ac=V_ac_t, I_ac=I_ac_t, theta_deg=theta_t, f_ac=f_ac_t,
            tau_f_ms=tau_f_t,
        )
        for fld, wk in [("Ra",_WK_DC.Ra),("La",_WK_DC.La),("kb",_WK_DC.kb),
                        ("Lf",_WK_DC.Lf),("Rf",_WK_DC.Rf)]:
            if fld in est:
                st.session_state[wk] = est[fld]

        # Calculation Details expander
        with st.expander("Calculation Details (IEEE Std 113-1985)", expanded=True):
            # Header — method and configuration
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

            # ── Physical tests: two or three side-by-side columns ────
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
                st.markdown("**No-Load Test**")
                _wm_nl = n_nl_t * (2 * 3.14159265 / 60)
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

            # ── Intermediate indicators ───────────────────────────
            st.markdown("##### Intermediate indicators")
            _tau_a = est["La"] / max(est["Ra"], 1e-9)
            _im_c1, _im_c2, _im_c3, _im_c4 = st.columns(4)
            _im_c1.metric("Ea_nl (V)",        f"{est['Ea_nl']:.3f}")
            _im_c2.metric("ω_nl (rad/s)",     f"{_wm_nl:.2f}")
            _im_c3.metric("τ_a = La/Ra (ms)", f"{_tau_a * 1000:.2f}")
            if exc in ("sep_motor", "sep_gen"):
                _Lf_est = est.get("Lf", 0.0)
                _Rf_est = float(st.session_state.get(_WK_DC.Rf, 1.0))
                _tau_f = _Lf_est / max(_Rf_est, 1e-9)
                _im_c4.metric("τ_f = Lf/Rf (ms)", f"{_tau_f * 1000:.2f}")

            # ── Estimated parameters ──────────────────────────────────
            st.markdown("##### Estimated parameters (equivalent circuit)")
            _p1 = st.columns(3)
            _p1[0].metric("Ra (Ω)",       f"{est['Ra']:.4f}")
            _p1[1].metric("La (H)",       f"{est['La']:.5f}")
            _p1[2].metric("kb (V·s/rad)", f"{est['kb']:.5f}")
            if exc in ("sep_motor", "sep_gen"):
                _p2 = st.columns(3)
                _p2[0].metric("Lf (H)",   f"{est.get('Lf', 0):.5f}")
                _p2[1].metric("Rf (Ω)",   f"{est.get('Rf', 0):.4f}" if "Rf" in est else "—")
                _p2[2].metric("If_nl (A)", f"{If_nl_t:.4f}")
            elif exc == "shunt_motor" and "Rf" in est:
                _p2 = st.columns(3)
                _p2[0].metric("Lf (H)",  f"{est.get('Lf', 0):.5f}")
                _p2[1].metric("Rf (Ω)",  f"{est['Rf']:.4f}")
                _p2[2].metric("If_nl (A)", f"{If_nl_t:.4f}")

            # Sanity warnings
            if est["kb"] <= 0:
                st.error("$k_b$ ≤ 0 — impossible. Check $V_{a,nl}$, $R_a$ and $I_{a,nl}$.")
            if est["Ra"] / max(V_nl_t, 1e-6) > 0.3:
                st.warning("$R_a/V_{a,nl}$ > 30% — Ra appears high for this operating voltage.")

        if st.button(
            "✔ Use these parameters in the simulation",
            key="btn_dc_use_tests",
            help="Copies the estimated parameters to Manual mode, allowing adjustments before simulating.",
        ):
            for fld, wk in [("Ra",_WK_DC.Ra),("La",_WK_DC.La),("kb",_WK_DC.kb),("Lf",_WK_DC.Lf)]:
                if fld in est:
                    st.session_state[wk] = est[fld]
            st.session_state[_WK_DC.input_mode] = "Enter parameters manually"
            st.rerun()

    # ── Preset loader — only in manual mode (estimators have their own data source) ──
    if input_mode == "Enter parameters manually":
        if st.session_state.pop("_dc_reset_preset", False):
            st.session_state[_WK_DC.preset] = "— Select preset —"

        _presets_exc = _PRESETS_BY_EXC.get(exc, {})
        _preset_names = ["— Select preset —"] + list(_presets_exc.keys())
        pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
        with pc1:
            preset_sel = st.selectbox(
                "Preset", _preset_names, key=_WK_DC.preset,
                label_visibility="collapsed",
                disabled=experiment_mode,
            )
        with pc2:
            if st.button("Load", key="btn_dc_load_preset", width="stretch",
                         disabled=(preset_sel == "— Select preset —" or experiment_mode)):
                ps = _presets_exc[preset_sel]
                _DIRECT_KEYS = {"_dc_mode_sel"}
                for k, v in ps.items():
                    if k in _DIRECT_KEYS:
                        st.session_state[k] = v
                    else:
                        st.session_state[f"wi_dc_{k}"] = v
                st.session_state["_dc_reset_preset"] = True
                st.rerun()

    is_gen    = exc in ("sep_gen", "shunt_gen")
    is_sep    = exc in ("sep_motor", "sep_gen")
    is_series = exc == "series_motor"

    _wi(_WK_DC.energy_tariff, 0.75)

    if experiment_mode:
        # Locked mode: compact summary with st.metric (same pattern as MIT)
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
        m1.metric("J (kg·m²)",   f"{J:.4f}")
        m2.metric("B (N·m·s)",   f"{B:.2e}")
        m3.metric("Tl (N·m)",    f"{Tload:.4f}")
    else:
        # Initialize defaults
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
        _is_ieee      = (input_mode == "Determine from IEEE 113 tests")

        if _is_manual:
            # ── Full armature group ──────────────────────────────
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

            # ── Field group ──────────────────────────────────────────
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
            # Ra, La, kb, Lf estimated in both modes — read silently
            ra = float(st.session_state.get(_WK_DC.Ra, 0.013))
            la = float(st.session_state.get(_WK_DC.La, 0.01))
            kb = float(st.session_state.get(_WK_DC.kb, 0.004))
            lf = float(st.session_state.get(_WK_DC.Lf, 0.167))

            if _is_nameplate:
                # Nameplate estimates all electrical — read Va, Vf, Rf silently
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
                        # Rf estimated from DC field test — read silently
                        rf = float(st.session_state.get(_WK_DC.Rf, 1.43))
                    else:
                        vf = va
                        st.caption("Shunt: $V_f = V_a$ (fixed — field in parallel with armature)")
                        # Rf estimated via V_nl/If_nl — read silently
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

        # Electrical load group (generators) — not estimated, always visible
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

        # Mechanical group — Nameplate estimates J and B; IEEE estimates neither
        if _is_nameplate:
            J     = float(st.session_state.get(_WK_DC.J,     0.21))
            B     = float(st.session_state.get(_WK_DC.B,     1.074e-6))
            Tload = float(st.session_state.get(_WK_DC.Tload, 2.493))
        else:
            # Manual and Tests: J, B, Tload editable
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

        # Derived metrics
        _tau_a_ms = (la / max(ra, 1e-9)) * 1000
        _n0_rpm   = (va / max(kb, 1e-9)) * (60 / (2 * 3.14159265)) - (B * va / max(kb**2, 1e-9)) * (60 / (2 * 3.14159265))
        _d1, _d2, _d3 = st.columns(3)
        _d1.metric("τ_a (ms)",      f"{_tau_a_ms:.2f}",   help="Armature electrical time constant = La/Ra")
        if not is_series and lf > 0 and rf > 0:
            _tau_f_ms = (lf / max(rf, 1e-9)) * 1000
            _d2.metric("τ_f (ms)",  f"{_tau_f_ms:.2f}",   help="Field circuit time constant = Lf/Rf")
        else:
            _d2.metric("τ_f (ms)",  "—",                  help="Not applicable for series motor")
        _d3.metric("n₀ est. (RPM)", f"{max(_n0_rpm, 0):.0f}", help="Estimated no-load speed (steady state)")

        # Advanced Parameters
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

    mp = DCMachineParams(
        Va=va, Ra=ra, La=la,
        Vf=vf, Rf=rf, Lf=lf,
        Rl=rl, Ll=ll,
        J=J, B=B, kb=kb,
        excitation=exc,
        Tload=Tload,
    )

    ref_code = hash((va, ra, la, vf, rf, lf, rl, ll, J, B, kb, exc, Tload))
    energy_tariff = float(st.session_state.get(_WK_DC.energy_tariff, 0.75))
    return mp, ref_code, energy_tariff


# ─────────────────────────────────────────────────────────────────────────────
# RENDER — EXPERIMENT (lower col_circuit)
# ─────────────────────────────────────────────────────────────────────────────

def _tl_sugerido_dc(mp: DCMachineParams) -> float:
    """Estimated rated torque: kb·ia_nominal, where ia_nominal = (Va-kb·wm_nom)/Ra."""
    try:
        wm_nom = mp.Tload if mp.Tload > 0 else mp.Va / mp.kb if mp.kb > 0 else 100.0
        ia_nom = (mp.Va - mp.kb * wm_nom) / mp.Ra if mp.Ra > 0 else mp.Va / mp.Ra
        return float(max(abs(mp.kb * ia_nom), 0.01))
    except Exception:
        return float(abs(mp.Tload)) if mp.Tload else 1.0


def render_experiment_config_dc(
    mp: DCMachineParams,
    _wk: Any = None,
) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    """Renders DC machine mode selector and experiment parameters.

    Returns (exp_config, var_keys, var_labels, tmax, h).
    """
    st.markdown('<p class="slabel">Experiment</p>', unsafe_allow_html=True)

    exc = mp.excitation
    available_modes = DC_MODES_BY_EXC.get(exc, ["dol_dc"])
    mode_labels = [DC_MODE_LABELS[m] for m in available_modes]

    mode_sel_label = st.selectbox(
        "Experiment Type", mode_labels, index=0, key="_dc_mode_sel",
        label_visibility="visible",
    )
    mode_sel_label = st.session_state.get("_dc_mode_sel", mode_labels[0])
    mode = available_modes[mode_labels.index(mode_sel_label)] if mode_sel_label in mode_labels else available_modes[0]

    exp_config: dict[str, Any] = {"exp_type": mode, "exp_label": DC_MODE_LABELS[mode]}

    _pgroup("Load and Voltage Parameters")

    _Tl_ref = float(st.session_state.get(_WK_DC.Tload, mp.Tload))
    _tl_sug = _tl_sugerido_dc(mp)
    st.caption(f"Configured load torque: **{_Tl_ref:.3f} N·m** | τ_a = L_a/R_a = {mp.La/mp.Ra:.4f} s")

    if mode == "dol_dc":
        tmax_def = 12.0
        h_def    = 1e-3
        partir_em_vazio = st.checkbox(
            "Start unloaded (apply load after starting)",
            value=True, key=_WK_DC.dol_vazio,
            help="When active, the motor starts unloaded and receives torque at t_carga. "
                 "When inactive, the load is present from time zero.",
        )
        exp_config["partir_em_vazio"] = partir_em_vazio
        if partir_em_vazio:
            _wi(_WK_DC.dol_t_carga, 2.0)
            exp_config["t_carga"] = st.number_input(
                "Load application instant — $t_{carga}$ (s)",
                min_value=0.0, key=_WK_DC.dol_t_carga, format="%.2f",
            )
            exp_config["Tl_inicial"] = 0.0
            exp_config["Tl_final"]   = _Tl_ref
            tmax_def = max(exp_config["t_carga"] + 8.0, 12.0)
            _ibox(
                f"<strong>t = 0 s</strong> — rated voltage ({mp.Va:.1f} V) applied; "
                f"motor accelerates unloaded (T<sub>l</sub> = 0).<br>"
                f"<strong>t = {exp_config['t_carga']:.2f} s</strong> — load of "
                f"<strong>{_Tl_ref:.3f} N·m</strong> applied to shaft; "
                f"motor settles to new steady-state operating point."
            )
        else:
            exp_config["Tl_inicial"] = None
            exp_config["Tl_final"]   = _Tl_ref
            exp_config["t_carga"]    = 0.0
            _ibox(
                f"<strong>t = 0 s</strong> — rated voltage ({mp.Va:.1f} V) and load of "
                f"<strong>{_Tl_ref:.3f} N·m</strong> applied simultaneously; "
                f"motor starts against full load and accelerates to steady state."
            )

    elif mode == "resistencia_dc":
        c1, c2 = st.columns(2)
        _wi(_WK_DC.R_ini, 5.0)
        _wi(_WK_DC.t_ramp, 2.0)
        exp_config["R_ini"]  = c1.number_input("$R_{ini}$ (Ω)", min_value=0.0, key=_WK_DC.R_ini,  format="%.2f")
        exp_config["t_ramp"] = c2.number_input("$t_{ramp}$ (s)", min_value=0.1, key=_WK_DC.t_ramp, format="%.2f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_ramp"] + 8.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor starts with series resistance of "
            f"<strong>{exp_config['R_ini']:.2f} Ω</strong> limiting starting current.<br>"
            f"<strong>t = {exp_config['t_ramp']:.2f} s</strong> — resistance removed (short-circuited); "
            f"motor accelerates to steady state with load of {_Tl_ref:.3f} N·m."
        )

    elif mode == "frenagem_dc":
        brake_labels = list(DC_BRAKE_LABELS.values())
        brake_keys   = list(DC_BRAKE_LABELS.keys())
        _wi(_WK_DC.brake_method, brake_labels[0])
        brake_sel = st.selectbox(
            "Braking Method", brake_labels,
            index=brake_labels.index(st.session_state.get(_WK_DC.brake_method, brake_labels[0])),
            key=_WK_DC.brake_method,
        )
        brake = brake_keys[brake_labels.index(brake_sel)]
        exp_config["brake_method"] = brake
        exp_config["Tl_final"]     = _Tl_ref

        _BRAKE_DESC_DC = {
            "plugging":    "Reverses the armature voltage polarity while the motor is still rotating. "
                           "Produces torque opposing motion — very fast braking, but with high "
                           "armature current and possible direction reversal if no stopping switch is provided.",
            "injecao_cc":  "Cuts the operating supply and injects a reduced DC voltage into the armature. "
                           "The maintained field flux produces braking torque without reversing direction. "
                           "Smooth and controlled braking — current limited by armature resistance.",
            "regenerativo":"Reduces armature voltage below the motor back-EMF. Armature current "
                           "reverses — the motor operates as a generator, returning energy to the source. "
                           "Gentle braking; effective only for high-inertia or high-speed loads.",
        }
        st.info(_BRAKE_DESC_DC[brake])

        if brake == "plugging":
            _wi(_WK_DC.t_freia, 3.0)
            exp_config["t_freia"] = st.number_input(
                "Reversal instant — $t_{brake}$ (s)", min_value=0.1,
                key=_WK_DC.t_freia, format="%.2f",
            )
            tmax_def = exp_config["t_freia"] * 2.5
            h_def    = 1e-3
            _ibox(
                f"<strong>t = 0 s</strong> — motor starts in positive direction with load {_Tl_ref:.3f} N·m.<br>"
                f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — armature polarity reversed; "
                f"braking torque opposes motion; rotor decelerates and reverses direction."
            )

        elif brake == "injecao_cc":
            c1, c2 = st.columns(2)
            _wi(_WK_DC.t_freia,   3.0)
            _wi(_WK_DC.Vdc_inj,   mp.Va * 0.1)
            exp_config["t_freia"]  = c1.number_input(
                "Cut-off instant — $t_{brake}$ (s)", min_value=0.1,
                key=_WK_DC.t_freia, format="%.2f",
            )
            exp_config["Vdc_inj"]  = c2.number_input(
                "Injected DC voltage — $V_{inj}$ (V)", min_value=0.0,
                key=_WK_DC.Vdc_inj, format="%.2f",
                help="DC voltage applied to the armature after supply cut. Typically 5–15% of Va.",
            )
            tmax_def = exp_config["t_freia"] * 2.5
            h_def    = 1e-3
            _ibox(
                f"<strong>t = 0 s</strong> — motor operates in steady state with load {_Tl_ref:.3f} N·m.<br>"
                f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — supply cut; "
                f"DC voltage of <strong>{exp_config['Vdc_inj']:.2f} V</strong> injected into armature; "
                f"current produces torque opposing motion — controlled braking without reversal."
            )

        elif brake == "regenerativo":
            c1, c2 = st.columns(2)
            _wi(_WK_DC.t_freia,  3.0)
            _wi(_WK_DC.Va_regen, mp.Va * 0.5)
            exp_config["t_freia"]   = c1.number_input(
                "Braking instant — $t_{brake}$ (s)", min_value=0.1,
                key=_WK_DC.t_freia, format="%.2f",
            )
            exp_config["Va_regen"]  = c2.number_input(
                "Reduced armature voltage — $V_{a,regen}$ (V)", min_value=0.0,
                key=_WK_DC.Va_regen, format="%.2f",
                help="Voltage below back-EMF — motor operates as generator returning energy.",
            )
            tmax_def = exp_config["t_freia"] * 2.5
            h_def    = 1e-3
            _ibox(
                f"<strong>t = 0 s</strong> — motor operates in steady state with load {_Tl_ref:.3f} N·m.<br>"
                f"<strong>t = {exp_config['t_freia']:.2f} s</strong> — armature voltage reduced to "
                f"<strong>{exp_config['Va_regen']:.2f} V</strong> (below back-EMF); "
                f"current reverses — motor operates as generator, returning energy to source."
            )

    elif mode == "campo_fraco_dc":
        c1, c2, c3 = st.columns(3)
        _wi(_WK_DC.Vf_fraco,  mp.Vf * 0.5 if mp.Vf > 0 else mp.Va * 0.5)
        _wi(_WK_DC.t_campo,   3.0)
        _wi(_WK_DC.t_trans,   0.5)
        exp_config["Vf_fraco"] = c1.number_input("$V_f$ weakened (V)", min_value=0.0,
                                                   key=_WK_DC.Vf_fraco, format="%.2f")
        exp_config["t_campo"]  = c2.number_input("$t_{field}$ (s)", min_value=0.1,
                                                   key=_WK_DC.t_campo, format="%.2f")
        exp_config["t_trans"]  = c3.number_input("$t_{trans}$ (s)", min_value=0.05,
                                                   key=_WK_DC.t_trans, format="%.2f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_campo"] + 10.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor operates at rated field; load {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {exp_config['t_campo']:.2f} s</strong> — field voltage reduced to "
            f"<strong>{exp_config['Vf_fraco']:.2f} V</strong> (field weakening); "
            f"flux drops, speed increases to maintain power — {exp_config['t_trans']:.2f} s transient."
        )

    elif mode == "pulso_dc":
        c1, c2 = st.columns(2)
        _wi(_WK_DC.t_pulso,  4.0)
        _wi(_WK_DC.Tl_extra, _Tl_ref * 0.5)
        exp_config["t_pulso"]  = c1.number_input("Pulse instant — $t_{pulse}$ (s)", min_value=0.1, key=_WK_DC.t_pulso,  format="%.2f")
        exp_config["Tl_extra"] = c2.number_input("Additional $\\Delta T_l$ (N·m)", min_value=0.0, key=_WK_DC.Tl_extra, format="%.3f")
        exp_config["Tl_final"] = _Tl_ref
        tmax_def = exp_config["t_pulso"] + 8.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — motor operates in steady state with load {_Tl_ref:.3f} N·m.<br>"
            f"<strong>t = {exp_config['t_pulso']:.2f} s</strong> — additional load pulse of "
            f"<strong>{exp_config['Tl_extra']:.3f} N·m</strong> applied; motor decelerates and settles.<br>"
            f"<strong>t = {exp_config['t_pulso']*2:.2f} s</strong> — pulse removed; motor recovers steady-state speed."
        )

    elif mode == "gerador_dc":
        _wi(_WK_DC.Tl_gen, abs(mp.Tload))
        exp_config["Tl_gen"] = st.number_input("Prime mover torque — $T_{mec}$ (N·m)", min_value=0.0, key=_WK_DC.Tl_gen, format="%.3f")
        tmax_def = 15.0
        h_def    = 1e-3
        _ibox(
            f"<strong>t = 0 s</strong> — machine accelerated by prime mover with torque of "
            f"<strong>{exp_config['Tl_gen']:.3f} N·m</strong>; field excited.<br>"
            f"<strong>Steady state</strong> — terminal voltage $V_t$ stabilizes; resistive load $R_L$ receives generated power."
        )
    else:
        tmax_def = 12.0
        h_def    = 1e-3

    st.markdown('</div>', unsafe_allow_html=True)

    # Variables for visualization — separated into Mechanical / Electrical (same as MIT)
    st.write("")
    st.markdown('<p class="slabel">Variables for Visualization</p>', unsafe_allow_html=True)
    _pgroup("Mechanical Quantities")
    sel_mec = st.multiselect(
        "Mechanical quantities",
        options=list(DC_VAR_MECANICAS.keys()),
        default=DC_DEFAULT_VARS_MEC,
        label_visibility="collapsed",
        key=_WK_DC.vars_mec,
    )
    _pgroup("Electrical Quantities")
    sel_ele = st.multiselect(
        "Electrical quantities",
        options=list(DC_VAR_ELETRICAS.keys()),
        default=DC_DEFAULT_VARS_ELE,
        label_visibility="collapsed",
        key=_WK_DC.vars_ele,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    selected_labels = sel_mec + sel_ele
    var_keys   = [DC_VAR_OPTIONS[v] for v in selected_labels if v in DC_VAR_OPTIONS]
    var_labels = [v for v in selected_labels if v in DC_VAR_OPTIONS]
    if not var_keys:
        var_keys   = DC_DEFAULT_VARS
        var_labels = [k for k, v in DC_VAR_OPTIONS.items() if v in DC_DEFAULT_VARS]

    # Simulation numerical parameters
    st.write("")
    st.markdown('<p class="slabel">Simulation Numerical Parameters</p>', unsafe_allow_html=True)
    _pgroup("Total Time and Integration Step")

    _t_acomo = float(min(max(15.0 * mp.J, 2.0), 30.0))
    _tmax_auto_val = round(tmax_def + _t_acomo, 1)

    tc1, tc2 = st.columns(2)
    with tc1:
        _tmax_auto = st.checkbox("Calculate tmax automatically (motor inertia)", value=True, key=_WK_DC.tmax_auto)
        _wi(_WK_DC.tmax, tmax_def)
        tmax = st.number_input("Total time — $t_{max}$ (s)", min_value=0.001, max_value=3600.0,
                                value=tmax_def, step=0.1, format="%.1f",
                                key=_WK_DC.tmax, disabled=_tmax_auto)
        if _tmax_auto:
            tmax = 0.0  # sentinel: runner resolves
            st.caption(f"Automatic: **{_tmax_auto_val:.1f} s**  (mode + {_t_acomo:.1f} s mechanical settling, J={mp.J:.4f} kg·m²)")
        else:
            st.caption(f"Suggestion: ≥ {round(tmax_def + 0.5, 1):.1f} s  (last event + 0.5 s to reach steady state)")

        _wi(_WK_DC.h, h_def)
        h = st.number_input("Integration step — $h$ (s)", min_value=1e-6, max_value=0.1,
                             value=h_def, step=1e-4, format="%.6f", key=_WK_DC.h)

        _tmax_display = _tmax_auto_val if _tmax_auto else tmax
        n_steps = int(_tmax_display / h) if (_tmax_display > 0 and h > 0) else 0
        st.caption(f"Total steps: {n_steps:,}")
        if n_steps > 500_000:
            st.warning("High number of steps. The simulation may take several seconds.")

        # Validation: critical event not covered by tmax
        if not _tmax_auto:
            _tmax_check = tmax
            _critical_dc: list[tuple[str, str, float]] = []
            if mode == "dol_dc" and exp_config.get("partir_em_vazio"):
                _critical_dc = [("load application", "t_{carga}", exp_config.get("t_carga", 0))]
            elif mode == "resistencia_dc":
                _critical_dc = [("resistance removal", "t_{ramp}", exp_config.get("t_ramp", 0))]
            elif mode == "frenagem_dc":
                _critical_dc = [("braking", "t_{brake}", exp_config.get("t_freia", 0))]
            elif mode == "campo_fraco_dc":
                _critical_dc = [("field weakening", "t_{field}", exp_config.get("t_campo", 0))]
            elif mode == "pulso_dc":
                _critical_dc = [("load pulse", "t_{pulse}", exp_config.get("t_pulso", 0))]
            for _lbl, _sym, _t in _critical_dc:
                if _t >= _tmax_check:
                    st.warning(
                        f"$t_{{max}}$ ({_tmax_check:.2f} s) ≤ ${_sym}$ ({_t:.2f} s): "
                        f"the **{_lbl}** event will not occur in the simulation — increase $t_{{max}}$."
                    )

    with tc2:
        _ibox(
            "<strong>t<sub>max</sub>:</strong> the larger the value, the more of the transient is captured, "
            "but at higher computational cost.<br><br>"
            "<strong>h (step):</strong> for DC machines, recommended h ≤ τ<sub>a</sub>/10, "
            "where τ<sub>a</sub> = L<sub>a</sub>/R<sub>a</sub> is the armature electrical time constant."
        )

    exp_config["_tmax_auto_val"] = _tmax_auto_val

    _ibox(f"<strong>Mode:</strong> {DC_MODE_LABELS[mode]} &nbsp;|&nbsp; "
          f"<strong>Excitation:</strong> {DC_EXC_LABELS.get(exc, exc)}")

    return exp_config, var_keys, var_labels, float(tmax), float(h)
