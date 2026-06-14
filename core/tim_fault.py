# -*- coding: utf-8 -*-
"""
desequilibrio_falta.py
======================
Generates unbalanced three-phase voltages and phase-loss conditions using
symmetrical components — UNDER DEVELOPMENT, not active in the current UI.

Responsibilities:
  - Generate abc_voltages_deseq with per-phase amplitude and angle adjustments
  - Support phase-loss mode (zero voltage on one phase)

Relationships:
  Imported by : core.machine_model, core.solver (conditionally)
  Imports     : (math, numpy only)

Extending:
  - To activate in the UI, integrate render_desequilibrio_ui in sim_config.py
    and pass parameters via a MachineParams.deseq_config field.
"""
from __future__ import annotations
import math
import numpy as np


# ── Voltage generation with unbalance/fault ──────────────────────────────────

def abc_voltages_deseq(t, Vl: float, f: float,
                       deseq_a: float = 0.0,
                       deseq_b: float = 0.0,
                       deseq_c: float = 0.0,
                       falta_fase_a: bool = False,
                       falta_fase_b: bool = False,
                       falta_fase_c: bool = False,
                       df_a: float = 0.0,
                       df_b: float = 0.0,
                       df_c: float = 0.0):
    """Generates abc voltages with unbalance and/or phase loss on any phase.

    deseq_a / deseq_b / deseq_c : fractional deviation in Vl (e.g. 0.1 = +10%, -0.1 = -10%).
    falta_fase_a/b/c             : if True, forces the phase voltage to zero.
    df_a / df_b / df_c           : per-phase frequency deviation in Hz (0 = nominal).
    Accepts t as scalar or np.ndarray; returns the same type.
    """
    scalar = np.ndim(t) == 0
    t_arr  = np.atleast_1d(np.asarray(t, dtype=float))
    zero   = np.zeros_like(t_arr)
    k      = np.sqrt(2.0 / 3.0)

    tetae_a = 2.0 * np.pi * (f + df_a) * t_arr
    tetae_b = 2.0 * np.pi * (f + df_b) * t_arr
    tetae_c = 2.0 * np.pi * (f + df_c) * t_arr

    Va = zero if falta_fase_a else k * Vl * (1.0 + deseq_a) * np.sin(tetae_a)
    Vb = zero if falta_fase_b else k * Vl * (1.0 + deseq_b) * np.sin(tetae_b - 2.0 * np.pi / 3.0)
    Vc = zero if falta_fase_c else k * Vl * (1.0 + deseq_c) * np.sin(tetae_c + 2.0 * np.pi / 3.0)

    if scalar:
        return float(Va[0]), float(Vb[0]), float(Vc[0])
    return Va, Vb, Vc


# ── Broken Bar Model ─────────────────────────────────────────────────────────

def make_broken_bar_rr_fn(Rr_nominal: float, severity: float, wb: float,
                          t_start: float = 0.0):
    """Returns function Rr(t, theta_slip) that modulates Rr at slip frequency from t_start.

    Model: Rr(t) = Rr0 · (1 + α · cos(2·θ_slip))  for t >= t_start
           Rr(t) = Rr0                               for t <  t_start

    Args:
        Rr_nominal: nominal rotor resistance (Ω).
        severity:   α — oscillation amplitude (0 = healthy, 0.1 = 10% breakage).
        wb:         base angular frequency (rad/s).
        t_start:    fault onset instant (s). 0 = fault present from the start.

    Returns:
        Callable[[float, float], float] — (t, theta_slip) → effective Rr.
        If severity == 0, returns None (signal to disable the model).
    """
    if severity == 0.0:
        return None

    def _rr_fn(t: float, theta_slip: float) -> float:
        if t < t_start:
            return Rr_nominal
        return Rr_nominal * (1.0 + severity * math.cos(2.0 * theta_slip))

    return _rr_fn


# ── UI Block ─────────────────────────────────────────────────────────────────

def render_desequilibrio_ui(config: dict, tmax: float = 2.0) -> None:
    """Renders the voltage unbalance / phase-loss expander.

    Fills config with keys:
      deseq_a, deseq_b, deseq_c,
      falta_fase_a, falta_fase_b, falta_fase_c,
      t_deseq.
    Must be called within the experiment configuration block in IWS_UI.py.
    """
    import streamlit as st
    st.write("")
    with st.expander("Voltage Unbalance / Phase Loss", expanded=False):
        st.info("Simulates supply asymmetry. Useful for fault diagnosis and motor protection studies.")

        with st.expander("What is voltage unbalance? (theory, standards and guidelines)", expanded=False):
            st.markdown("""
**Definition.** A three-phase system is considered **unbalanced** when the three
line-voltage phasors do not have **equal magnitudes** and/or are not **displaced by 120°** from each other.

**Common causes:**
- Single-phase loads distributed asymmetrically along the feeder.
- Capacitor banks or transformers with misaligned tap voltages.
- Poor connections (oxidised terminals, partially open fuses).
- Single-phase faults (phase-to-ground short circuit) during the transient.

**Decomposition into symmetrical components (Fortescue).** Any unbalanced set
can be decomposed into three balanced systems:

| Component | Symbol | Characteristic | Effect on motor |
|-----------|--------|----------------|-----------------|
| Positive | $V_1$ | Normal ABC sequence | Produces useful torque |
| Negative | $V_2$ | ACB sequence (reverse rotating field) | Generates **braking** torque and elevated currents |
| Zero | $V_0$ | Three in-phase phasors | Circulates only if neutral is accessible |

The **negative-sequence component** is the primary cause of damage: it
sees a slip close to $2 - s \\approx 2$ (field rotates against the rotor),
generating currents ~5–6× the equivalent positive-sequence component.

**Voltage Unbalance Factor (VUF, NEMA MG-1 §14.36):**
$$\\text{VUF}_{\\%} = \\frac{\\text{maximum deviation of }V_l\\text{ from the mean}}{\\text{mean }V_l} \\times 100\\%$$

**Normative limits:**
- **NEMA MG-1:** motors shall operate with VUF ≤ **1%** without derating. Above this, a power derating factor applies (NEMA curve).
- **ANEEL PRODIST Module 8:** limit of **2%** at LV connections (≤ 1 kV) and **3%** at MV/HV.
- **IEC 60034-1:** limit of **1%** continuous, with transient excursions tolerated.

**Typical impacts on the motor:**
- Additional heating: $\\Delta T \\propto \\text{VUF}^2$ — a VUF of 3.5% can increase winding temperature by ~25%, halving service life.
- Electromagnetic torque with **2·f oscillation** (120 Hz on a 60 Hz supply) due to interaction between positive- and negative-sequence fields.
- Reduction of available maximum torque.
- Increased vibration and audible noise.

**How to configure this panel:**
- **Amplitude deviation (%):** modifies the magnitude of $V_a$, $V_b$ or $V_c$ individually, relative to nominal. Use small values (1–5%) to simulate typical supply unbalance; larger values (10–30%) to study the protection region.
- **Frequency deviation (Hz):** rare in real systems (the supply is synchronised), but useful for simulating isolated generators or inverters out of synchronism.
- **Phase loss:** forces $V_a$, $V_b$ or $V_c$ to zero. **Warning:** a phase loss raises the current in the remaining phases to 1.7–2.5× nominal — protect with a short simulation time (≤ 1 s).
- **Onset instant:** the system starts from a balanced supply and the unbalance is applied from this instant. Use 0 to apply from the start, or a value after steady state to visualise the unbalance transient.

**How to observe the effects:**
- Phase current waveforms $i_{as}, i_{bs}, i_{cs}$: unequal amplitudes.
- **Electromagnetic torque $T_e$**: visible 2·f oscillation superimposed on the mean value.
- **Speed $n$**: small speed oscillation (attenuated by inertia).
- **FFT analysis of torque**: peak at 120 Hz (60 Hz supply) confirms negative sequence.

**References:**
- NEMA MG-1, *Motors and Generators*, §14.36 ("Effects of Unbalanced Voltage on Motor Performance").
- ANEEL PRODIST, *Module 8 — Power Quality*, §3.4.
- IEC 60034-1, *Rotating Electrical Machines — Rating and Performance*, §7.2.
- Fitzgerald/Umans, *Electric Machinery*, §4.7 ("Symmetrical Components").
            """)

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("**Phase A**")
            deseq_a = st.slider(
                "Amplitude deviation A (%)", min_value=-30, max_value=30, value=0, step=1,
                help="E.g.: +10 → Va = 1.1 × Vnominal", key="deseq_a"
            ) / 100.0
            df_a = float(st.slider(
                "Frequency deviation A (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Frequency deviation in Va. 0 = nominal.", key="df_a"
            ))
            falta_a = st.toggle("Phase A Loss (Va = 0)", value=False, key="falta_a")
            if falta_a:
                st.warning("Phase A loss — very high currents.")

        with col_b:
            st.markdown("**Phase B**")
            deseq_b = st.slider(
                "Amplitude deviation B (%)", min_value=-30, max_value=30, value=0, step=1,
                help="E.g.: +10 → Vb = 1.1 × Vnominal", key="deseq_b"
            ) / 100.0
            df_b = float(st.slider(
                "Frequency deviation B (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Frequency deviation in Vb. 0 = nominal.", key="df_b"
            ))
            falta_b = st.toggle("Phase B Loss (Vb = 0)", value=False, key="falta_b")
            if falta_b:
                st.warning("Phase B loss — very high currents.")

        with col_c:
            st.markdown("**Phase C**")
            deseq_c = st.slider(
                "Amplitude deviation C (%)", min_value=-30, max_value=30, value=0, step=1,
                help="E.g.: -10 → Vc = 0.9 × Vnominal", key="deseq_c"
            ) / 100.0
            df_c = float(st.slider(
                "Frequency deviation C (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Frequency deviation in Vc. 0 = nominal.", key="df_c"
            ))
            falta_c = st.toggle("Phase C Loss (Vc = 0)", value=False, key="falta_c")
            if falta_c:
                st.warning("Phase C loss — very high currents.")

        faltas_ativas = sum([falta_a, falta_b, falta_c])
        if faltas_ativas >= 2:
            st.error("Warning: two or more phases lost — single-phase or de-energised operation. "
                     "Reduce simulation time.")
        elif faltas_ativas == 1:
            st.warning("One phase lost: two-phase operation — very high currents. "
                       "Reduce simulation time.")

        _tmax_deseq = float(tmax) if tmax > 0.0 else None
        _val_deseq  = min(1.0, float(tmax) - 0.1) if (tmax > 0.0 and tmax <= 1.0) else 1.0
        t_deseq = st.number_input(
            "Unbalance onset instant (s)",
            min_value=0.0, max_value=_tmax_deseq, value=_val_deseq, step=0.1, format="%.2f",
            help="The unbalance begins to act at this instant. Use 0 to apply from the start.",
        )

        any_active = any([deseq_a, deseq_b, deseq_c, falta_a, falta_b, falta_c])
        if any_active and t_deseq > 0.0:
            st.caption(f"Balanced supply until {t_deseq:.2f} s — unbalance/fault applied from that instant.")

        config["deseq_a"]      = deseq_a
        config["deseq_b"]      = deseq_b
        config["deseq_c"]      = deseq_c
        config["falta_fase_a"] = falta_a
        config["falta_fase_b"] = falta_b
        config["falta_fase_c"] = falta_c
        config["t_deseq"]      = t_deseq
        config["df_a"]         = df_a
        config["df_b"]         = df_b
        config["df_c"]         = df_c


def render_broken_bar_ui(config: dict, tmax: float = 2.0, wk: dict | None = None) -> None:
    """Renders the Digital Twin — Broken Bar Fault expander.

    Available for any experiment, regardless of starting method.
    Fills config with keys:
      broken_bar_severity, t_broken_bar.
    """
    import streamlit as st

    _wk_key   = wk.broken_bar_severity if wk is not None else "wi_broken_bar_severity"
    _t_ref    = float(config.get("t_carga", 0.0))

    # reads values from session_state BEFORE the expander — ensures config is filled
    # even when the expander has never been opened by the user.
    broken_bar_severity = float(st.session_state.get(_wk_key, 0.0))
    t_broken_bar        = float(st.session_state.get("wi_broken_bar_t_start", max(0.0, _t_ref)))
    if broken_bar_severity == 0.0:
        t_broken_bar = 0.0
    config["broken_bar_severity"] = broken_bar_severity
    config["t_broken_bar"]        = t_broken_bar

    st.write("")
    with st.expander("Digital Twin — Broken Bar Fault", expanded=False):
        st.info(
            "Simulates mechanical rotor fault via Rᵣ modulation. "
            "Useful for MCSA (Motor Current Signature Analysis) studies."
        )

        with st.expander("What is a broken bar fault? (theory, MCSA and guidelines)", expanded=False):
            st.markdown("""
**Definition.** The squirrel-cage rotor is formed by **conducting bars** (cast aluminium
or copper) short-circuited at both ends by **end rings**.
A **broken bar** (cracked, severed or with poor contact at the ring) interrupts current
conduction along that rotor path.

**Common causes:**
- Thermal stress from repeated DOL starts (gradient $\\Delta T > 200\\,°C$ in the bar).
- Mechanical fatigue from vibration and load cycles.
- Casting defects (porosity in aluminium) or cold welds at the rings.
- Electrochemical corrosion in aggressive environments.

**Field statistics (IEEE/EPRI):** rotor faults represent **8–15%** of total
induction motor failures, with broken bars being the dominant cause in motors
above 100 kW with frequent starting duty.

**Why does the fault generate $(1 \\pm 2s)f_e$?**
In a healthy rotor, the $N_r$ bar currents are sinusoidal and balanced at the
slip frequency $s \\cdot f_e$. A broken bar creates a **spatial asymmetry**
that rotates at rotor speed. Decomposing this asymmetry:

- The **forward** component induces in the stator a current at $f_e(1 - 2s)$ — **lower sideband**.
- The **reverse** component induces at $f_e(1 + 2s)$ — upper sideband.

These two sidebands, symmetric about the fundamental $f_e$, are the **classical
spectral signature** of the fault (Thomson & Fenger, 2001).

**Model implemented in this simulator:**

$$R_r(t) = R_{r0} \\cdot (1 + \\alpha \\cdot \\cos(2\\theta_{slip}))$$

The modulation at $2\\theta_{slip}$ generates in the stator current exactly the sideband pairs
$(1 \\pm 2s)f_e$ predicted by theory. Approximation valid for mild to moderate faults
($\\alpha \\leq 0{,}3$); severe faults require individual bar models (not
implemented).

**Severity $\\alpha$ vs. number of broken bars (empirical approximation):**

| $\\alpha$ | Condition | Typical sideband amplitude (dB) |
|----------|-----------|----------------------------------|
| 0.00 | Healthy | < −55 |
| 0.05 | Onset of crack, 1 partial bar | −50 to −45 |
| 0.10 | 1 broken bar | −45 to −40 |
| 0.15–0.20 | 2 adjacent broken bars | −40 to −35 |
| 0.30+ | Severe fault, multiple bars | > −30 |

Reference: ratio $20 \\log_{10}(I_{sideband}/I_{fundamental})$.

**IEC 60034-26 severity criterion:**

| Sideband (dB) | Diagnosis |
|---------------|-----------|
| < −50 | Healthy rotor |
| −50 to −45 | Possible crack, monitor |
| −45 to −40 | Confirmed fault, schedule maintenance |
| −40 to −35 | Advanced fault, urgent intervention |
| > −35 | Risk of end-ring rupture, immediate shutdown |

**MCSA procedure (Motor Current Signature Analysis):**
1. Acquire one stator phase current with **high resolution** ($\\Delta f \\leq 0{,}1$ Hz).
2. Run **FFT** over a long window (≥ 10 s) to resolve the sidebands.
3. Identify the fundamental $f_e$ and measure the bands at $f_e(1 \\pm 2s)$.
4. Calculate amplitude in dB: $20 \\log_{10}(I_{sideband}/I_{fundamental})$.
5. Compare against the IEC 60034-26 criterion above.

**Simulation guidelines:**
- Use **DOL or direct-on-load start** so the motor reaches steady state before the fault.
- Set $t_{fault}$ **after the transient** (≥ 2× starting time) to isolate the signature.
- Increase $t_{max}$ to **≥ 5 s** to obtain sufficient spectral resolution for the FFT.
- The simulator FFT analysis will display the sidebands when $\\alpha > 0$.
- To visualise the **pulsating torque**: plot $T_e$ — the low-frequency oscillation ($2s \\cdot f_e$, typically 1–5 Hz) is visible to the naked eye.
- Very **low slip speeds** ($s < 0{,}5\\%$) push the sidebands too far from the fundamental, making detection difficult — starting under load helps.

**Model limitations:**
- Assumes sinusoidal distribution of asymmetry — does not capture non-uniform adjacent bar effects.
- Does not model the **end ring** (whose fault generates bands at $(1 \\pm 2s/p)f_e$).
- Magnetic saturation and dynamic eccentricity are not represented.

**References:**
- IEC 60034-26, *Effects of Unbalanced Voltages on the Performance of Three-Phase Cage Induction Motors* (also applicable to rotor fault signatures).
- Thomson, W. T. & Fenger, M., *Current Signature Analysis to Detect Induction Motor Faults*, IEEE Industry Applications Magazine, vol. 7, no. 4, 2001.
- Nandi, S., Toliyat, H. A. & Li, X., *Condition Monitoring and Fault Diagnosis of Electrical Motors — A Review*, IEEE Trans. on Energy Conversion, vol. 20, no. 4, 2005.
- IEEE Std 1129, *Recommended Practice for Maintenance, Testing, and Replacement of Induction Motors*.
            """)

        st.markdown(
            "Model: $R_r(t) = R_{r0} \\cdot (1 + \\alpha \\cdot \\cos(2\\theta_{slip}))$  "
            "for $t \\geq t_{fault}$. "
            "The spectral signature exhibits sideband components at $(1 \\pm 2s)f_e$."
        )
        broken_bar_severity = st.slider(
            "Fault severity — $\\alpha$",
            min_value=0.0, max_value=0.5, value=0.0, step=0.01, format="%.2f",
            key=_wk_key,
            help="0 = healthy motor. 0.1 ≈ 1 broken bar. 0.3+ = severe fault.",
        )
        if broken_bar_severity > 0:
            _tmax_bb   = float(tmax) if tmax > 0.0 else None
            _val_bb    = max(0.0, _t_ref)
            t_broken_bar = st.number_input(
                "Fault onset instant — $t_{fault}$ (s)",
                min_value=0.0, max_value=_tmax_bb,
                value=_val_bb, step=0.1, format="%.2f",
                key="wi_broken_bar_t_start",
                help="Rᵣ modulation begins at this instant. "
                     "Use a value after t_load to simulate fault at steady state.",
            )
            st.caption(
                f"α = {broken_bar_severity:.2f} — expected sideband components at "
                f"$(1 \\pm 2s)f$ Hz. Use the FFT analysis to verify the signature."
            )
            if broken_bar_severity >= 0.3:
                st.warning("High severity (α ≥ 0.3) — may cause visible oscillations in electromagnetic torque.")
        else:
            t_broken_bar = 0.0
            st.caption("α = 0 — healthy motor. Increase α to activate the fault model.")

        # updates config with interactive values inside the expander
        config["broken_bar_severity"] = broken_bar_severity
        config["t_broken_bar"]        = t_broken_bar
