# -*- coding: utf-8 -*-
"""
ui/theory/tabs/sensibilidade.py
================================
Theory Tab 4 — Parameter Sensitivity Guide.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn


_PARAMS_ELETRICOS = [
    {
        "nome": "$V_l$ — Line Voltage (RMS)",
        "desc": (
            "Defines the amplitude of the stator rotating magnetic field. "
            "Determines the air-gap flux: $\\Phi \\propto V_l/f$. "
            "This is the quantity with the greatest impact on available torque."
        ),
        "up": (
            "Maximum torque grows with $V_l^2$: $T_{max} \\propto V_{th}^2 \\propto V_l^2$. "
            "Starting current also increases significantly."
        ),
        "down": (
            "Starting torque decreases — may become insufficient to overcome load inertia, "
            "preventing starting (stall during acceleration)."
        ),
        "warn": (
            "Overvoltage ($> 110\\%\\,V_n$) causes **core saturation** and "
            "thermal degradation of insulation. "
            "Severe undervoltage ($< 85\\%\\,V_n$) may cause **stalling** under rated load."
        ),
    },
    {
        "nome": "$f$ — Grid Frequency",
        "desc": (
            "Determines synchronous speed: $n_s = 120\\,f/p\\;$(rpm). "
            "Reactances scale proportionally: $X = 2\\pi f L$."
        ),
        "up": (
            "Increases $n_s$, $X_m$, $X_{ls}$, $X_{lr}$. "
            "With constant $V_l$, the $V/f$ ratio falls, reducing flux and maximum torque."
        ),
        "down": (
            "Reduces operating speed. With constant $V_l$, the $V/f$ ratio rises, "
            "driving the core into **magnetic saturation**."
        ),
        "warn": (
            "Operating outside rated frequency without $V/f = $ const. control compromises "
            "flux, efficiency, and thermal integrity of the machine."
        ),
    },
    {
        "nome": "$R_s$ — Stator Resistance",
        "desc": (
            "Represents Joule losses in the stator windings: $P_{cu,1} = 3I_1^2 R_s$. "
            "Causes an internal voltage drop, reducing the effective voltage at the air gap."
        ),
        "up": (
            "Increases thermal dissipation and reduces $T_{max}$, "
            "since $R_{th} \\uparrow$ raises the denominator of the Boucherot expression."
        ),
        "down": (
            "Minimizes internal losses and improves efficiency. "
            "At extreme values, approximates an ideal transformer primary."
        ),
        "warn": (
            "Excessive $R_s$ (damaged or overheated windings) causes "
            "**progressive overheating**. "
            "Values near zero may cause **numerical instability** in the integrator."
        ),
    },
    {
        "nome": "$R_r$ — Rotor Resistance",
        "desc": (
            "Determining parameter of the torque curve. "
            "Defines critical slip: $s_{cr} = R_r / \\sqrt{R_{th}^2 + X_{eq}^2}$."
        ),
        "up": (
            "$s_{cr}$ increases — torque peak shifts to lower speeds. "
            "Starting torque grows up to the limit $T_{max}$ (when $s_{cr} = 1$)."
        ),
        "down": (
            "Improves efficiency ($s_{nom}$ decreases) and reduces steady-state slip. "
            "Starting torque decreases proportionally."
        ),
        "warn": (
            "Very high $R_r$ indicates **broken bars** — causes excessive slip and vibration. "
            "Zero values cause **mathematical singularity** in the rotor equations."
        ),
    },
    {
        "nome": "$X_m$ — Magnetizing Reactance",
        "desc": (
            "Represents the magnetizing (*shunt*) branch of the circuit: "
            "main flux path through the core. "
            "Related to mutual inductance: $X_m = 2\\pi f L_m$."
        ),
        "up": (
            "Reduces no-load magnetizing current $I_m = V_1/X_m$, "
            "improving power factor in steady state."
        ),
        "down": (
            "Increases $I_m$ — higher reactive current required to excite the core, "
            "degrading power factor."
        ),
        "warn": (
            "Low $X_m$ indicates poor-quality core or **magnetic saturation**. "
            "Excessively low values may cause **numerical divergence** in the integrator."
        ),
    },
    {
        "nome": "$R_{fe}$ — Core Loss Resistance",
        "desc": (
            "Models hysteresis and eddy currents in parallel with $X_m$. "
            "Core losses: $P_{fe} = 3\\,V_\\phi^2 / R_{fe}$. "
            "Typical values: $100$–$2000\\;\\Omega$ for medium-sized machines."
        ),
        "up": (
            "Lower $P_{fe}$. Motor operates with higher efficiency, "
            "especially at light load where core losses dominate."
        ),
        "down": (
            "Higher $P_{fe}$. Efficiency decreases, especially at no load. "
            "May indicate low-quality laminations or operation at elevated frequency."
        ),
        "warn": (
            "$R_{fe}$ is used **only in static power and efficiency calculations** — "
            "it does not influence the ODE or the simulated dynamics. "
            "Values $< 50\\;\\Omega$ indicate extremely poor-quality core."
        ),
    },
    {
        "nome": "$X_{ls}$ and $X_{lr}$ — Leakage Reactances",
        "desc": (
            "Model fluxes that do not link both windings (leakage). "
            "Define short-circuit reactance: $X_{cc} = X_{ls} + X_{lr}$, "
            "which limits maximum torque and starting current."
        ),
        "up": (
            "Increases $X_{cc}$, reducing $T_{max} \\propto 1/(X_{th}+X_{lr})$. "
            "Starting current decreases, facilitating protection."
        ),
        "down": (
            "$T_{max}$ increases and starting currents rise. "
            "Makes the motor more sensitive to load transients and voltage variations."
        ),
        "warn": (
            "Very low leakage results in **current peaks dangerous to the insulation**. "
            "Excessive leakage may **prevent starting** under rated load."
        ),
    },
]

_PARAMS_MECANICOS = [
    {
        "nome": "$p$ — Number of Poles",
        "desc": (
            "Defines synchronous speed: $n_s = 120\\,f/p\\;$(rpm), "
            "or equivalently $\\omega_s = 4\\pi f/p\\;$(rad/s)."
        ),
        "up": (
            "Reduces $n_s$. For the same power $P = T\\,\\omega$, "
            "rated torque must be proportionally larger."
        ),
        "down": (
            "Increases $n_s$ and $\\omega_s$. "
            "Rated torque decreases for the same output power."
        ),
        "warn": "$p$ must always be a positive even integer. Odd values invalidate the physical model.",
    },
    {
        "nome": "$J$ — Moment of Inertia",
        "desc": (
            "Governs acceleration dynamics via the mechanical equation: "
            "$J\\,\\dot{\\omega}_r = T_e - T_L - B\\,\\omega_r$. "
            "Includes the rotor and the load coupled to the shaft."
        ),
        "up": (
            "Slower acceleration — damped transients and longer starting time. "
            "Reduces sensitivity to sudden load changes."
        ),
        "down": (
            "Accelerated dynamic response — rotor reacts almost instantaneously to $T_e$ changes. "
            "Useful for servo drives, but requires protection against fast overloads."
        ),
        "warn": (
            "Very low $J$ may produce **noisy numerical oscillations** in the ODE. "
            "Very high $J$ may require very large $t_{max}$ to reach steady state."
        ),
    },
    {
        "nome": "$B$ — Viscous Friction Coefficient",
        "desc": (
            "Models mechanical losses proportional to speed: "
            "$T_{friction} = B\\,\\omega_r$ (bearings and ventilation)."
        ),
        "up": (
            "Increases system damping and mechanical dissipation. "
            "Steady-state equilibrium shifts to lower speed."
        ),
        "down": (
            "Reduces mechanical losses. "
            "If $B = 0$, damping depends exclusively on the external load $T_L$."
        ),
        "warn": (
            "High values simulate **catastrophic bearing failure** and "
            "may prevent the motor from reaching rated speed."
        ),
    },
]


def render_tab_sensibilidade() -> None:
    st.markdown(
        "**Simulator calibration guide**: how each parameter qualitatively affects "
        "machine behavior. Useful for diagnostics, model tuning, and fault studies."
    )

    st.divider()
    st.markdown("### Electrical Parameters")
    for item in _PARAMS_ELETRICOS:
        st.markdown(f"**{item['nome']}**")
        st.markdown(item["desc"])
        st.markdown(f"- **If increased:** {item['up']}")
        st.markdown(f"- **If decreased:** {item['down']}")
        _div_warn(f"**Caution — extreme calibrations:** {item['warn']}")
        st.write("")

    st.divider()
    st.markdown("### Mechanical Parameters")
    for item in _PARAMS_MECANICOS:
        st.markdown(f"**{item['nome']}**")
        st.markdown(item["desc"])
        st.markdown(f"- **If increased:** {item['up']}")
        st.markdown(f"- **If decreased:** {item['down']}")
        _div_warn(f"**Caution — extreme calibrations:** {item['warn']}")
        st.write("")

    st.divider()
    st.markdown("### Magnetic Parameter Input Mode — Reactances vs. Inductances")
    _h4("Reactances $X$ (Ω) vs. Inductances $L$ (H)")
    st.markdown(
        "The magnetic parameters $X_m$, $X_{ls}$, and $X_{lr}$ can be entered in two "
        "equivalent forms. The choice depends on the available data source."
    )

    col_x, col_l = st.columns(2)
    with col_x:
        _h4("Reactance Mode (Ω)")
        st.markdown(
            "Values are provided as reactances measured at a reference frequency "
            "$f_{ref}$. This is the standard format of test reports and manufacturer catalogs."
        )
        _eq(r"X = 2\pi\,f_{ref}\,L")
        st.markdown(
            "**$f_{ref}$** must be the frequency at which the parameters were measured — "
            "typically the machine's rated frequency (50 Hz or 60 Hz). "
            "The simulator converts internally to inductances:"
        )
        _eq(r"L = \frac{X}{2\pi\,f_{ref}}")
        _div_warn(
            "If $f_{ref}$ differs from the grid frequency $f$, the effective reactances in the simulation "
            "will be correctly recalculated — $L$ is invariant, $X$ scales with $f$."
        )
    with col_l:
        _h4("Inductance Mode (H)")
        st.markdown(
            "Values are provided directly as frequency-independent inductances. "
            "Indicated when parameters come from parametric identification, "
            "finite element simulation (FEM), or impedance bridge measurements."
        )
        _eq(r"X_m(f) = 2\pi\,f\,L_m")
        st.markdown(
            "Inductances are entered once and remain valid for any "
            "operating frequency — the simulator recalculates reactances automatically "
            "at each change of $f$."
        )
        _div_warn(
            "Prefer this mode when operating outside rated frequency or when comparing "
            "machines of different frequencies using the same parameter set."
        )

    st.divider()
    st.markdown("### Thermal Parameters")
    _h4("$R_{th}$ — Thermal Resistance (K/W)")
    st.markdown(
        "Represents the resistance to heat flow between the winding and the external environment. "
        "Defines steady-state temperature as a function of total losses:"
    )
    _eq(r"\Delta T_{steady} = R_{th}\,(P_{cu} + P_{fe})")
    st.markdown(
        "In automatic mode, $R_{th}$ is estimated from the electrical parameters by imposing "
        "a rated temperature rise $\\Delta T = 50\\;$K — a typical value for TEFC "
        "(Totally Enclosed Fan Cooled) motors at rated operation, corresponding to "
        "$T_{steady} \\approx 75\\;$°C with $T_{amb} = 25\\;$°C."
    )
    _div_warn(
        "Low $R_{th}$ values indicate a well-cooled motor (large frame, "
        "forced ventilation). High values indicate a small enclosed motor or "
        "one with compromised ventilation — higher steady-state temperature."
    )

    st.write("")
    _h4("$C_{th}$ — Thermal Capacitance (J/K)")
    st.markdown(
        "Represents the energy required to raise the motor temperature by 1 K. "
        "Governs the **heating rate** — the thermal time constant is:"
    )
    _eq(r"\tau_{th} = R_{th}\,C_{th}")
    st.markdown(
        "In automatic mode, thermal capacitance is estimated from the motor equivalent mass, "
        "assuming steel with specific heat $c_p = 460\\;$J/(kg·K) and an industrial rule of "
        "$15\\;$kg/kW of rated power:"
    )
    _eq(r"C_{th} \approx \underbrace{15\,P_{nom}}_{\text{estimated mass (kg)}} \times 460\;\frac{\text{J}}{\text{kg·K}}")
    _div_warn(
        "The thermal ODE integrated by the simulator is: "
        "$\\dot{T} = (P_{cu} + P_{fe})/C_{th} - (T - T_{amb})/(R_{th}\\,C_{th})$. "
        "In steady state, $\\dot{T} = 0$ and $T_{steady} = T_{amb} + R_{th}\\,(P_{cu}+P_{fe})$."
    )

    st.write("")
    _h4("$T_{amb}$ — Ambient Temperature (°C)")
    st.markdown(
        "External ambient temperature, used as the boundary condition of the thermal ODE "
        "and as the initial value of $T$ in the simulation. "
        "Motor temperature at any instant is:"
    )
    _eq(r"T(t) = T_{amb} + \Delta T(t), \quad \Delta T(t) = \Delta T_{steady}\!\left(1 - e^{-t/\tau_{th}}\right)")
    st.markdown(
        "Changing $T_{amb}$ shifts the entire temperature curve without modifying the dynamics — "
        "$\\tau_{th}$ and $\\Delta T_{steady}$ remain unchanged."
    )

    st.divider()
    st.markdown("### Grid Impedance")
    _h4("$R_{grid}$ and $L_{grid}$ — Supply Grid Impedance")
    st.markdown(
        "In a real installation, the motor is not fed directly by an ideal voltage source: "
        "there is a grid impedance between the point of delivery and the motor terminals, "
        "composed of the resistance and inductance of cables, transformers, and busbars. "
        "The simulator models this impedance as a series $R_{grid} + jX_{grid}$ "
        "inserted in each phase before the stator terminals:"
    )
    _eq(r"\bar{V}_{motor} = \bar{V}_{grid} - \bar{I}_s\,(R_{grid} + j\omega_e L_{grid})")
    st.markdown(
        "The effective voltage at the motor terminals drops with current — especially "
        "during starting, when $I_s$ is maximum. The effect is equivalent to a "
        "**current-proportional voltage sag** throughout the entire transient."
    )
    st.markdown(
        "- **$R_{grid}$:** causes resistive voltage drop and active power dissipation in the cable.\n"
        "- **$L_{grid}$:** causes reactive voltage drop and phase lag — more relevant in "
        "medium-voltage grids or with long cables."
    )
    _div_warn(
        "With $R_{grid} = L_{grid} = 0$ (default), the motor is fed by an ideal source — "
        "terminal voltage always equal to $V_l$. "
        "Typical values for low-voltage cables: $R_{grid} \\approx 0{,}01$–$0{,}1\\;\\Omega$, "
        "$L_{grid} \\approx 10$–$100\\;\\mu$H."
    )
