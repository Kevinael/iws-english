# -*- coding: utf-8 -*-
"""
tim_config_params.py
====================
MIT parameter-source sub-renderers and the public render_machine_params() function.

Exports:
    _ElecParams                    — dataclass returned by each param sub-renderer
    _Te_rotor_bloqueado            — locked-rotor torque helper
    _reduced_start_warning        — starting feasibility warning
    _validate_params               — UI range checks
    _render_params_nameplate       — NEMA Nameplate estimation panel
    _render_params_ieee            — IEEE Std 112-2017 test panel
    _render_params_manual          — manual parameter entry panel
    _render_params_locked          — compact read-only display (experiment mode)
    _render_params_editable        — full editable panel (preset + source selection)
    render_machine_params          — public entry point (calls locked or editable)
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

from core.tim.facade import MachineParams
from core.constants import MIT_DEFAULTS
from data.machines_mit import MIT_PRESETS
from data.ui_labels import MIT_INPUT_MODE_LABELS, MIT_PARAM_SOURCE_LABELS, MIT_IEEE_SPLIT_LABELS
from core.tim import estimate_params, estimate_params_ieee_tests
from ui_components._shared_widgets import _pgroup, _ibox

if TYPE_CHECKING:
    pass

_DEFAULTS: dict = MIT_DEFAULTS
_PRESETS: dict = MIT_PRESETS


# ─────────────────────────────────────────────────────────────────────────────
# CACHED ESTIMATORS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_estimate_params(
    Vl: float, f: float, Pn_kW: float, N_nom: float,
    rend: float, fp: float, Ip_In: float, Tp_Tn: float, is_delta: bool,
) -> dict:
    return estimate_params(Vl, f, 0, Pn_kW, N_nom, rend, fp, Ip_In, Tp_Tn, is_delta=is_delta)


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
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _tl_sugerido(mp: MachineParams) -> float:
    """Estimates rated motor torque from electrical parameters (s=5%)."""
    ws = mp.wb / (mp.p / 2)
    Vf = mp.Vl / 3.0 ** 0.5
    s = 0.05
    Zr = complex(mp.Rr / s, mp.Xlr_a)
    Zm = complex(0.0, mp.wb * mp.Lm)
    Zs = complex(mp.Rs, mp.Xls_a)
    Z_par = Zr * Zm / (Zr + Zm)
    I_total = Vf / abs(Zs + Z_par)
    Ir = I_total * abs(Zm) / abs(Zr + Zm)
    Pmec = 3.0 * (mp.Rr / s - mp.Rr) * Ir ** 2
    return max(round(Pmec / ws, 2), 0.1)


def _Te_rotor_bloqueado(mp: MachineParams, voltage_ratio: float) -> float:
    """Electromagnetic torque at locked rotor (s=1) for reduced voltage."""
    Vf   = mp.Vl / np.sqrt(3.0)
    Vf_r = Vf * voltage_ratio
    Zr2  = (mp.Rs + mp.Rr) ** 2 + (mp.Xls_a + mp.Xlr_a) ** 2
    if Zr2 == 0.0:
        return 0.0
    return (3.0 * (mp.p / 2) / mp.wb) * (Vf_r ** 2) * mp.Rr / Zr2


def _reduced_start_warning(mp: MachineParams, voltage_ratio: float, Tl: float) -> None:
    """Displays reduced-voltage starting feasibility warning."""
    Te_bloq = _Te_rotor_bloqueado(mp, voltage_ratio)
    Te_nom  = _Te_rotor_bloqueado(mp, 1.0)
    if Tl <= 0.0:
        st.caption(
            f"Estimated starting torque (locked rotor): **{Te_bloq:.1f} N·m** "
            f"({voltage_ratio*100:.0f}% voltage → {voltage_ratio**2*100:.0f}% of rated T_e,lock {Te_nom:.1f} N·m)."
        )
        return
    margem = (Te_bloq / Tl - 1.0) * 100.0
    if Te_bloq < Tl:
        st.error(
            f"Estimated starting torque **{Te_bloq:.1f} N·m** < load **{Tl:.1f} N·m** — "
            f"the motor **may fail to start** at this reduced voltage. "
            f"Increase the tap/initial voltage or reduce the load."
        )
    elif margem < 20.0:
        st.warning(
            f"Estimated starting torque **{Te_bloq:.1f} N·m** — narrow margin of **+{margem:.0f}%** "
            f"above the {Tl:.1f} N·m load. Starting may fail with grid variations or static friction."
        )
    else:
        st.success(
            f"Starting feasible — estimated starting torque **{Te_bloq:.1f} N·m** "
            f"(margin of **+{margem:.0f}%** above the {Tl:.1f} N·m load)."
        )


def _validate_params(mp: MachineParams) -> None:
    """Issues UI warnings when parameters are outside physically plausible ranges."""
    warns: list[str] = []
    rs_rr = mp.Rs / mp.Rr if mp.Rr else float("inf")
    if not (0.1 <= rs_rr <= 10):
        warns.append(f"Ratio $R_s/R_r$ = {rs_rr:.2f} is outside the typical range [0.1, 10]. Check the values.")
    xm_xls = mp.Xm / mp.Xls if mp.Xls else float("inf")
    if not (5 <= xm_xls <= 200):
        warns.append(f"Ratio $X_m/X_{{ls}}$ = {xm_xls:.1f} is outside the typical range [5, 200]. Check the magnetic parameters.")
    tau_e_ms = (mp.Lm / mp.Rr * 1000) if mp.Rr else float("inf")
    if tau_e_ms < 0.5:
        warns.append(f"Electrical time constant $\\tau_e$ ≈ {tau_e_ms:.2f} ms (< 0.5 ms). A very small step $h$ may be required.")
    if mp.Xm > 0:
        _xls_ratio = mp.Xls_a / mp.Xm
        _xlr_ratio = mp.Xlr_a / mp.Xm
        if _xls_ratio < 0.01:
            warns.append(
                f"$X_{{ls}}$ = {mp.Xls:.5f} Ω appears too small "
                f"($X_{{ls}}/X_m$ = {_xls_ratio*100:.3f}%, typical: 2–15%). "
                "Check whether inductance (H) was entered instead of reactance (Ω) — "
                "incorrect values cause current and temperature blow-up."
            )
        if _xlr_ratio < 0.01:
            warns.append(
                f"$X_{{lr}}$ = {mp.Xlr:.5f} Ω appears too small "
                f"($X_{{lr}}/X_m$ = {_xlr_ratio*100:.3f}%, typical: 2–15%). "
                "Check whether inductance (H) was entered instead of reactance (Ω) — "
                "incorrect values cause current and temperature blow-up."
            )
    for w in warns:
        st.warning(w)


# ─────────────────────────────────────────────────────────────────────────────
# ELECTRICAL PARAMS DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class _ElecParams:
    """Electrical parameters returned by each parameter-source sub-renderer."""
    Vl:         float
    f:          float
    Rs:         float
    Rr:         float
    Xm:         float
    Xls:        float
    Xlr:        float
    Rfe:        float
    f_ref:      float
    input_mode: str     # "X" (reactances) or "L" (inductances)


# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER SOURCE SUB-RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _render_params_nameplate(wk: object, dis: bool) -> _ElecParams:
    """NAMEPLATE MODE — estimates parameters from motor nameplate data."""
    _pgroup("Grid Data")
    Vl = st.number_input("Line RMS voltage — $V_l$ (V)", min_value=50.0, max_value=15000.0, value=_DEFAULTS["Vl"], step=1.0, key=wk.Vl, disabled=dis)
    f  = st.number_input("Grid frequency — $f$ (Hz)",    min_value=1.0,  max_value=400.0,   value=_DEFAULTS["f"],  step=1.0, key=wk.f,  disabled=dis)
    is_delta = st.checkbox(
        "Delta (Δ) connection — uncheck for Star (Y)",
        value=False, key=wk.is_delta, disabled=dis,
        help="Affects the phase voltage and phase current used in the equivalent circuit calculation.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    _pgroup("Nameplate Data")
    Pn_kW = st.number_input(
        "Rated shaft power (kW)",
        min_value=0.01, max_value=10000.0, value=2.2, step=0.1, format="%.2f",
        key=wk.Pn_kW, disabled=dis,
        help="Rated mechanical power at the motor flange (nameplate value).",
    )
    N_nom = st.number_input(
        "Rated speed (RPM)",
        min_value=1.0, max_value=60000.0, value=1746.0, step=1.0, format="%.0f",
        key=wk.N_nom, disabled=dis,
        help="Full-load rated speed. Number of poles is deduced automatically.",
    )
    rend_placa = st.number_input(
        "Rated efficiency η (e.g. 0.91)",
        min_value=0.01, max_value=0.999, value=0.85, step=0.01, format="%.3f",
        key=wk.rend, disabled=dis,
        help="Full-load efficiency — η = P_shaft / P_electrical.",
    )
    fp_placa = st.number_input(
        "Rated power factor cos(φ) (e.g. 0.85)",
        min_value=0.01, max_value=0.999, value=0.85, step=0.01, format="%.3f",
        key=wk.fp_placa, disabled=dis,
        help="cos(φ) at full rated load.",
    )
    Ip_In = st.number_input(
        "Starting-to-rated current ratio  (Ip/In)",
        min_value=1.0, max_value=15.0, value=6.0, step=0.1, format="%.1f",
        key=wk.Ip_In, disabled=dis,
        help="DOL starting current in multiples of rated current (typically 5–8 for NEMA B).",
    )
    Tp_Tn = st.number_input(
        "Starting-to-rated torque ratio  (Tp/Tn)",
        min_value=0.1, max_value=5.0, value=1.5, step=0.1, format="%.2f",
        key=wk.Tp_Tn, disabled=dis,
        help="Starting torque (s=1) in multiples of rated torque (typically 1.0–2.0 for NEMA B).",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    resultado = _cached_estimate_params(Vl, f, Pn_kW, N_nom, rend_placa, fp_placa, Ip_In, Tp_Tn, is_delta)

    if not resultado["success"]:
        st.error(f"Inconsistent nameplate data: {resultado['error']}  Default parameters (Krause 3 HP) will be used.")
        Rs, Rr, Xm, Xls, Xlr = 0.435, 0.816, 26.13, 0.754, 0.754
        Rfe = _DEFAULTS["Rfe"]
    else:
        Rs, Rr    = resultado["Rs"],  resultado["Rr"]
        Xm        = resultado["Xm"]
        Xls       = resultado["Xls"]
        Xlr       = resultado["Xlr"]
        Rfe       = resultado["Rfe"]
        ligacao = "Delta (Δ)" if is_delta else "Star (Y)"
        with st.expander("How were these parameters estimated?", expanded=True):
            st.info(
                f"**Method:** IEEE T-equivalent circuit — steady-state.\n\n"
                f"**Assumed connection:** {ligacao}  "
                f"| **Poles deduced from nameplate:** {resultado['p_est']}\n\n"
                f"**Electrical assumptions:**\n"
                f"- NEMA B distribution: $X_{{ls}}$ = 40% · $X_k$, $X_{{lr}}$ = 60% · $X_k$\n"
                f"- Starting power factor: cos(φₚ) = 0.20\n"
                f"- Air-gap voltage: $E_1 \\approx V_f - I_n \\cdot |Z_s|$ "
                f"= {resultado['E1']:.2f} V (stator drop subtracted)\n"
                f"- $R_{{fe}}$ estimated heuristically: core losses ≈ 20% of total losses "
                f"({resultado['P_fe_total']:.1f} W) referred to $E_1$ → $R_{{fe}}$ = {Rfe:.1f} Ω"
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Synchronous speed (Estimated)",    f"{resultado['n_s']:.1f} RPM")
            c2.metric("Rated slip sₙ (Estimated)",        f"{resultado['s_n']*100:.2f}%")
            c3.metric("Rated current Iₙ (Estimated)",     f"{resultado['In_lin']:.2f} A")
            c4.metric("Rated torque Tₙ (Estimated)",      f"{resultado['Tn']:.2f} N·m")
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Starting current Iₚ (Estimated)",  f"{resultado['Ip_fase']:.2f} A")
            c6.metric("Starting torque Tₚ (Estimated)",   f"{resultado['Tp']:.2f} N·m")
            c7.metric("Zₖ (Estimated)",                   f"{resultado['Zk']:.4f} Ω")
            c8.metric("Xₖ (Estimated)",                   f"{resultado['Xk']:.4f} Ω")
            st.markdown("**Estimated equivalent circuit parameters:**")
            p1, p2, p3, p4, p5, p6 = st.columns(6)
            p1.metric("Rₛ (Estimated)",  f"{Rs:.4f} Ω")
            p2.metric("Rᵣ (Estimated)",  f"{Rr:.4f} Ω")
            p3.metric("Xₘ (Estimated)",  f"{Xm:.4f} Ω")
            p4.metric("Xls (Estimated)", f"{Xls:.4f} Ω")
            p5.metric("Xlr (Estimated)", f"{Xlr:.4f} Ω")
            p6.metric("Rfe (Estimated)", f"{Rfe:.1f} Ω")

    return _ElecParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe,
                       f_ref=f, input_mode="X")


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
    resultado: dict,
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
            f"**Distribution:** {MIT_IEEE_SPLIT_LABELS[resultado['split_used']]} "
            f"(fraction $X_{{ls}}/X_k$ = {resultado['Xls_frac']:.2f})."
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
                f"$E_{{1,NL}}$ = **{resultado['E1_nl']:.2f} V**  \n"
                f"$P_{{fe,3φ}}$ = **{resultado['Pfe_3ph']:.2f} W**  \n"
                f"$P_{{fw}}$ = **{resultado['Pfw_used']:.2f} W**"
            )
            st.caption(
                "Pfw measured" if Pfw > 0
                else "Pfw via heuristic (0.8% · P_NL)"
            )
        with t3:
            st.markdown("**Locked Rotor Test**")
            st.markdown(
                f"$Z_k$ = **{resultado['Zk']:.4f} Ω**  \n"
                f"$R_k$ = **{resultado['Rk']:.4f} Ω**  \n"
                f"$X_k$ @ {f_nl:.0f} Hz = **{resultado['Xk']:.4f} Ω**"
            )
            st.caption(
                f"$X_{{k,LR}}$ = {resultado['Xk_lr']:.4f} Ω · "
                f"correction $f_{{NL}}/f_{{LR}}$ = {(f_nl/f_lr):.2f}"
            )

        st.divider()

        st.markdown("##### Intermediate indicators")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("E₁ (no-load)",          f"{resultado['E1_nl']:.2f} V")
        c2.metric("Iμ magnetizing current", f"{resultado['I_mu']:.3f} A")
        c3.metric("Pfe three-phase",        f"{resultado['Pfe_3ph']:.1f} W")
        c4.metric("Pfw used",               f"{resultado['Pfw_used']:.1f} W")

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


def _render_params_ieee(wk: object, dis: bool) -> _ElecParams:
    """IEEE 112 MODE — three physical tests (DC + No-Load + Locked Rotor)."""
    Vl, f, is_delta = _render_ieee_grid_inputs(wk, dis)
    _render_ieee_guide(wk)
    V_dc, I_dc, Vl_nl, I_nl, P_nl, f_nl, Pfw, Vl_lr, I_lr, P_lr, f_lr, split_code, Xls_frac = (
        _render_ieee_test_inputs(wk, dis, Vl, f, is_delta)
    )

    resultado = _cached_estimate_ieee(
        V_dc, I_dc, is_delta,
        Vl_nl, I_nl, P_nl, f_nl,
        Vl_lr, I_lr, P_lr, f_lr,
        Pfw, split_code, Xls_frac,
    )

    if not resultado["success"]:
        st.error(
            f"Inconsistent IEEE tests: {resultado['error']}  "
            "Default parameters (Krause 3 HP) will be used."
        )
        Rs, Rr, Xm, Xls, Xlr = 0.435, 0.816, 26.13, 0.754, 0.754
        Rfe = _DEFAULTS["Rfe"]
    else:
        Rs  = resultado["Rs"]
        Rr  = resultado["Rr"]
        Xm  = resultado["Xm"]
        Xls = resultado["Xls"]
        Xlr = resultado["Xlr"]
        Rfe = resultado["Rfe"]
        _render_ieee_results(resultado, f_nl, f_lr, V_dc, I_dc, Pfw, Rs, Rr, Xm, Xls, Xlr, Rfe, is_delta)

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


def _render_params_manual(wk: object, dis: bool) -> _ElecParams:
    """MANUAL MODE — all parameters entered directly by the user."""
    _pgroup("Electrical Data")
    Vl = st.number_input("Line RMS voltage — $V_l$ (V)",               min_value=50.0,   max_value=15000.0, value=_DEFAULTS["Vl"],  step=1.0,   key=wk.Vl,  disabled=dis)
    f  = st.number_input("Grid frequency — $f$ (Hz)",                  min_value=1.0,    max_value=400.0,   value=_DEFAULTS["f"],   step=1.0,   key=wk.f,   disabled=dis)
    Rs = st.number_input("Stator resistance — $R_s$ (Ω)",              min_value=0.0001, max_value=100.0,   value=_DEFAULTS["Rs"],  step=0.001, key=wk.Rs,  format="%.3f", disabled=dis,
                         help="Stator winding resistance per phase. Typical: 0.01–10 Ω. Affects Joule losses and voltage drop during starting transient.")
    Rr = st.number_input("Rotor resistance — $R_r$ (Ω)",               min_value=0.0001, max_value=100.0,   value=_DEFAULTS["Rr"],  step=0.001, key=wk.Rr,  format="%.3f", disabled=dis,
                         help="Rotor winding resistance referred to the stator. Typical: similar to Rs (Class B). Determines rated slip and starting torque.")

    input_mode_label = st.radio(
        "Magnetic parameter format",
        MIT_INPUT_MODE_LABELS,
        index=0,
        key=wk.input_mode,
        disabled=dis,
        horizontal=True,
    )
    input_mode = "X" if input_mode_label.startswith("Reactances") else "L"

    if input_mode == "X":
        f_ref = st.number_input(
            "Test reference frequency — $f_{ref}$ (Hz)",
            min_value=1.0, max_value=400.0, value=60.0, step=1.0,
            key=wk.f_ref,
            help="Frequency at which $X_m$, $X_{ls}$, and $X_{lr}$ were measured (typically 50 Hz or 60 Hz).",
            disabled=dis,
        )
        Xm  = st.number_input("Magnetizing reactance — $X_m$ (Ω)",              min_value=0.0001, max_value=500.0, value=_DEFAULTS["Xm"],  step=0.01,  key=wk.Xm,  format="%.2f", disabled=dis,
                              help="Magnetizing reactance — represents the air-gap flux path. Typical: 10–30× Xls. Very low values indicate saturation or incorrect no-load test.")
        Xls = st.number_input("Stator leakage reactance — $X_{ls}$ (Ω)",        min_value=0.0001, max_value=50.0,  value=_DEFAULTS["Xls"], step=0.001, key=wk.Xls, format="%.3f", disabled=dis,
                              help="Stator leakage reactance — flux that does not cross the air gap. Typical: 0.1–2 Ω (motors up to 10 kW). Along with Xlr, determines the slope of the T×n curve at starting.")
        Xlr = st.number_input("Rotor leakage reactance — $X_{lr}$ (Ω)",         min_value=0.0001, max_value=50.0,  value=_DEFAULTS["Xlr"], step=0.001, key=wk.Xlr, format="%.3f", disabled=dis,
                              help="Rotor leakage reactance referred to the stator. Typically close to Xls (Class B/D) or larger (Class C).")
    else:
        f_ref   = 60.0
        _wb_ref = 2.0 * 3.141592653589793 * 60.0
        Xm  = st.number_input("Magnetizing inductance — $L_m$ (H)",              min_value=1e-6, max_value=10.0, value=round(_DEFAULTS["Xm"]  / _wb_ref, 6), step=0.0001, key=wk.Xm_L,  format="%.6f", disabled=dis,
                              help="Magnetizing inductance (frequency-independent). Related to reactance by Xm = 2π·f·Lm.")
        Xls = st.number_input("Stator leakage inductance — $L_{ls}$ (H)",        min_value=1e-6, max_value=1.0,  value=round(_DEFAULTS["Xls"] / _wb_ref, 6), step=0.0001, key=wk.Xls_L, format="%.6f", disabled=dis,
                              help="Stator leakage inductance. Determines the slope of the T×n curve in the starting region.")
        Xlr = st.number_input("Rotor leakage inductance — $L_{lr}$ (H)",         min_value=1e-6, max_value=1.0,  value=round(_DEFAULTS["Xlr"] / _wb_ref, 6), step=0.0001, key=wk.Xlr_L, format="%.6f", disabled=dis,
                              help="Rotor leakage inductance referred to the stator. Typically close to Lls (Class B/D).")

    Rfe = st.number_input("Core loss resistance — $R_{fe}$ (Ω)", min_value=10.0, max_value=10000.0, value=_DEFAULTS["Rfe"], step=10.0, key=wk.Rfe, format="%.1f", disabled=dis,
                          help="Parallel resistance representing core losses (hysteresis + eddy currents). Typical: 100–2000 Ω. Low values model poor-quality magnetic material or high frequencies.")
    st.caption("$R_{fe}$ affects both the ODE dynamics (core loss currents) and the steady-state power balance.")
    st.markdown('</div>', unsafe_allow_html=True)

    return _ElecParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe,
                       f_ref=f_ref, input_mode=input_mode)


def _render_params_locked(wk: object) -> tuple[MachineParams, int, float]:
    Vl  = float(st.session_state.get(wk.Vl,  _DEFAULTS["Vl"]))
    f   = float(st.session_state.get(wk.f,   _DEFAULTS["f"]))
    Rs  = float(st.session_state.get(wk.Rs,  _DEFAULTS["Rs"]))
    Rr  = float(st.session_state.get(wk.Rr,  _DEFAULTS["Rr"]))
    Xm  = float(st.session_state.get(wk.Xm,  _DEFAULTS["Xm"]))
    Xls = float(st.session_state.get(wk.Xls, _DEFAULTS["Xls"]))
    Xlr = float(st.session_state.get(wk.Xlr, _DEFAULTS["Xlr"]))
    Rfe = float(st.session_state.get(wk.Rfe, _DEFAULTS["Rfe"]))
    p   = int(st.session_state.get(wk.p,     _DEFAULTS["p"]))
    J   = float(st.session_state.get(wk.J,   _DEFAULTS["J"]))
    B   = float(st.session_state.get(wk.B,   _DEFAULTS["B"]))
    Rgrid = float(st.session_state.get(wk.Rgrid, 0.0))
    Lgrid = float(st.session_state.get(wk.Lgrid, 0.0))
    energy_tariff = float(st.session_state.get(wk.energy_tariff, 0.75))

    ref_label = st.session_state.get(wk.ref_park, "Synchronous  (ω = ωₑ)")
    ref_code = {"Synchronous  (ω = ωₑ)": 1,
                "Rotor  (ω = ωᵣ)": 2,
                "Stationary  (ω = 0)": 3}.get(ref_label, 1)

    input_mode = "X"
    f_ref = float(st.session_state.get(wk.f_ref, f))

    st.info(
        "**Parameters locked** — disable the toggle at the top of the page to edit.  "
        "Experiment variations (load, voltage, fault) will not affect the machine."
    )

    st.markdown('<p class="slabel">Electrical Parameters</p>', unsafe_allow_html=True)
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Vₗ (V)",   f"{Vl:.1f}")
    e2.metric("f (Hz)",   f"{f:.1f}")
    e3.metric("Rₛ (Ω)",   f"{Rs:.4f}")
    e4.metric("Rᵣ (Ω)",   f"{Rr:.4f}")

    e5, e6, e7, e8 = st.columns(4)
    e5.metric("Xₘ (Ω)",   f"{Xm:.3f}")
    e6.metric("Xₗₛ (Ω)",  f"{Xls:.4f}")
    e7.metric("Xₗᵣ (Ω)",  f"{Xlr:.4f}")
    e8.metric("Rfe (Ω)",  f"{Rfe:.1f}")

    st.markdown('<p class="slabel">Mechanical Parameters and Reference Frame</p>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("p (poles)",     f"{p}")
    m2.metric("J (kg·m²)",     f"{J:.4f}")
    m3.metric("B (N·m·s/rad)", f"{B:.4f}")
    m4.metric("Reference",     ref_label.split("(")[0].strip())

    mp = MachineParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe,
                       p=p, J=J, B=B,
                       input_mode=input_mode, f_ref=f_ref,
                       Rgrid=Rgrid, Lgrid=Lgrid)
    _validate_params(mp)

    st.write("")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Synchronous Speed $n_s$", f"{mp.n_sync:.1f} RPM")
    mc2.metric("Base Angular Velocity $\\omega_b$", f"{mp.wb/(mp.p/2):.2f} rad/s")
    mc3.metric("Mutual Reactance $X_{ml}$", f"{mp.Xml:.4f} Ω")

    return mp, ref_code, energy_tariff


def _render_params_editable(wk: object) -> tuple[MachineParams, int, float]:
    if st.session_state.pop("_reset_preset_select", False):
        st.session_state["preset_select"] = "— Select preset —"

    pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
    with pc1:
        preset_sel = st.selectbox(
            "Preset",
            ["— Select preset —"] + list(_PRESETS.keys()),
            label_visibility="collapsed",
            key="preset_select",
        )
    with pc2:
        if st.button("Load", key="btn_load_preset", width="stretch",
                     disabled=(preset_sel == "— Select preset —")):
            pdata = _PRESETS[preset_sel]
            _wk_preset = {
                "Vl": wk.Vl, "f": wk.f, "Rs": wk.Rs, "Rr": wk.Rr,
                "input_mode": wk.input_mode, "f_ref": wk.f_ref,
                "Xm": wk.Xm, "Xls": wk.Xls, "Xlr": wk.Xlr,
                "Rfe": wk.Rfe, "p": wk.p, "J": wk.J, "B": wk.B,
                "exp_type": wk.exp_type,
                "Tl_final": wk.Tl_final,
                "Tl_pulse": wk.Tl_pulse,
                "Tl_pulse_abs": wk.Tl_pulse_abs,
                "t_pulse_on": wk.t_pulse_on,
                "t_pulse_off": wk.t_pulse_off,
                "t_load": wk.t_load,
                "tmax": wk.tmax,
            }
            for key, widget_key in _wk_preset.items():
                if key in pdata:
                    st.session_state[widget_key] = pdata[key]
            st.session_state["_param_source_idx"] = 0
            st.session_state["_reset_preset_select"] = True
            st.rerun()

    dis = False

    _ps_idx = int(st.session_state.get("_param_source_idx", 0))
    param_source_label = st.radio(
        "Motor parameter source",
        MIT_PARAM_SOURCE_LABELS,
        index=_ps_idx,
        disabled=dis,
        horizontal=True,
    )
    st.session_state["_param_source_idx"] = MIT_PARAM_SOURCE_LABELS.index(param_source_label)
    use_placa = param_source_label.startswith("Estimate")
    use_ieee  = param_source_label.startswith("Determine")

    if use_placa:
        ep = _render_params_nameplate(wk, dis)
    elif use_ieee:
        ep = _render_params_ieee(wk, dis)
    else:
        ep = _render_params_manual(wk, dis)

    Vl, f   = ep.Vl, ep.f
    Rs, Rr  = ep.Rs, ep.Rr
    Xm, Xls, Xlr, Rfe = ep.Xm, ep.Xls, ep.Xlr, ep.Rfe
    f_ref, input_mode  = ep.f_ref, ep.input_mode

    _pgroup("Mechanical Data and Reference Frame")
    p = st.selectbox("Number of poles — $p$", options=[2, 4, 6, 8, 10, 12], index=1, key=wk.p, disabled=dis,
                     help="Number of magnetic poles. Determines synchronous speed ns = 120·f/p. Common industrial motors: 2, 4, or 6 poles.")
    J = st.number_input("Moment of inertia — $J$ (kg·m²)",                min_value=0.0001, max_value=100.0, value=_DEFAULTS["J"], step=0.001, key=wk.J, format="%.3f", disabled=dis,
                        help="Total rotational inertia on the shaft (rotor + coupled load). Determines starting time and mechanical time constant.")
    B = st.number_input("Viscous friction coefficient — $B$ (N·m·s/rad)", min_value=0.0,   max_value=10.0,  value=_DEFAULTS["B"], step=0.001, key=wk.B, format="%.3f", disabled=dis,
                        help="Viscous friction proportional to angular velocity (bearings + windage). B = 0 idealizes the motor without mechanical losses; leave at 0 to use the empirical estimate shown below.")
    if B == 0.0:
        _T_nom_est = float(st.session_state.get("wi_Tl_final", 0.0))
        _wr_nom    = (1.0 - 0.03) * 120.0 * f / p * 3.14159265 / 30.0
        if _T_nom_est > 0.0 and _wr_nom > 0.0:
            _B_est = 0.01 * _T_nom_est / _wr_nom
            st.caption(
                f"B = 0 in the reference — estimated by empirical rule "
                f"(0.01 × T_nom / ω_nom): **{_B_est:.4f} N·m·s/rad**. "
                "Edit manually if needed."
            )
            B = _B_est
    ref_label = st.selectbox(
        "Park Transform Reference Frame",
        ["Synchronous  (ω = ωₑ)", "Rotor  (ω = ωᵣ)", "Stationary  (ω = 0)"],
        disabled=dis,
        key=wk.ref_park,
        help=(
            "Coordinate system for the Park (dq0) transform:\n"
            "• Synchronous (ω = ωₑ): steady-state currents appear as DC — ideal for "
            "steady-state analysis and vector control.\n"
            "• Rotor (ω = ωᵣ): frame fixed to the rotor — useful for synchronous machine "
            "and permanent magnet studies.\n"
            "• Stationary (ω = 0): dq variables oscillate at grid frequency — useful "
            "for visualizing waveforms in the αβ domain."
        ),
    )
    ref_code = {"Synchronous  (ω = ωₑ)": 1,
                "Rotor  (ω = ωᵣ)": 2,
                "Stationary  (ω = 0)": 3}[ref_label]
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Advanced Parameters (IAS/Industrial)", expanded=False):
        _pgroup("Grid Impedance (Voltage Sag)")
        rg1, rg2 = st.columns(2)
        with rg1:
            Rgrid = st.number_input(
                "$R_{grid}$ (Ω/phase)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.01, format="%.4f",
                key=wk.Rgrid,
                disabled=dis,
                help="Feed line resistance per phase. 0 = no resistive voltage drop.",
            )
        with rg2:
            Lgrid = st.number_input(
                "$L_{grid}$ (H/phase)",
                min_value=0.0, max_value=1.0, value=0.0, step=0.0001, format="%.4f",
                key=wk.Lgrid,
                disabled=dis,
                help="Feed line inductance per phase (H). 0 = no inductive voltage drop.",
            )
        if Rgrid > 0 or Lgrid > 0:
            _wb = 2.0 * np.pi * f
            _Zgrid_mag = float(np.sqrt(Rgrid**2 + (_wb * Lgrid)**2))
            _ibox(
                f"Grid impedance: $R_{{grid}}$ = {Rgrid:.4f} Ω  |  "
                f"$X_{{grid}}$ = {_wb*Lgrid:.4f} Ω  |  "
                f"$|Z_{{grid}}|$ = {_Zgrid_mag:.4f} Ω. "
                "Terminal voltage at the motor will be less than $V_l$."
            )
        st.markdown('</div>', unsafe_allow_html=True)

        _pgroup("Economic Analysis")
        energy_tariff = st.number_input(
            "Electricity tariff ($/kWh)",
            min_value=0.0001, max_value=5.0, value=0.75, step=0.01, format="%.2f",
            key=wk.energy_tariff,
            disabled=dis,
            help=(
                "Average tariff used to project annual operating cost based on "
                "the simulated load profile. Typical industrial value: $0.60–0.90/kWh."
            ),
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    mp = MachineParams(Vl=Vl, f=f, Rs=Rs, Rr=Rr, Xm=Xm, Xls=Xls, Xlr=Xlr, Rfe=Rfe, p=p, J=J, B=B,
                       input_mode=input_mode, f_ref=f_ref,
                       Rgrid=Rgrid, Lgrid=Lgrid)
    _validate_params(mp)

    st.write("")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Synchronous Speed $n_s$", f"{mp.n_sync:.1f} RPM")
    mc2.metric("Base Angular Velocity $\\omega_b$", f"{mp.wb/(mp.p/2):.2f} rad/s")
    mc3.metric("Mutual Reactance $X_{ml}$", f"{mp.Xml:.4f} Ω")
    if input_mode == "X":
        st.caption(f"Inductances calculated at {f_ref:.0f} Hz → $L_m$ = {mp.Lm*1000:.4f} mH  |  $L_{{ls}}$ = {mp.Lls*1000:.4f} mH  |  $L_{{lr}}$ = {mp.Llr*1000:.4f} mH")

    return mp, ref_code, energy_tariff


def render_machine_params(
    dark: bool,
    experiment_mode: bool,
    wk: object,
) -> tuple[MachineParams, int]:
    """Left column: all parameter fields. Returns (mp, ref_code).

    Args:
        dark: dark theme active.
        experiment_mode: when True, locks all inputs.
        wk: widget key mapping (_WK singleton from tim_config).
    """
    st.markdown('<p class="slabel">Machine Physical Parameters</p>', unsafe_allow_html=True)
    if experiment_mode:
        return _render_params_locked(wk)
    return _render_params_editable(wk)
