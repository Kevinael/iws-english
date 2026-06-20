# -*- coding: utf-8 -*-
"""
ui/theory/tabs/estimadores.py
==============================
Theory Tab 7 — Parameter Estimators.
"""

from __future__ import annotations
import streamlit as st
from ui.theory.tabs._shared import _h4, _eq, _div_warn


def render_tab_estimators() -> None:
    st.markdown(
        "This tab documents the **two parameter estimators** available in the "
        "simulator. Both are legitimate T-equivalent circuit methods in steady state, "
        "but apply to different use cases — the choice depends on the available data."
    )

    # ── Section 7.1: Nameplate ──────────────────────────────────────────────
    st.markdown("### Section 7.1 — Nameplate Estimator (nameplate data)")

    st.info(
        "**When to use:** only motor nameplate data available "
        "(manufacturer catalog, no physical tests). Indicated for initial studies, "
        "sensitivity analysis, and rapid simulation of NEMA class B motors."
    )

    _h4("Background — IEEE T-Equivalent with NEMA Assumptions")
    st.markdown(
        "When the equivalent circuit parameters "
        "($R_s, R_r', X_m, X_{ls}, X_{lr}'$) are not directly available, this "
        "method estimates them from the motor **nameplate** data. The formulation combines "
        "the IEEE Std 112 methodology with the statistical reactance distribution "
        "assumptions of NEMA MG-1. The implementation is in "
        "`core/param_estimator.py:22–179` (function `estimate_params`)."
    )

    st.markdown("**Required input data:**")
    st.markdown(
        "- Line voltage $V_l$ and frequency $f$.\n"
        "- Rated shaft power $P_n$ (kW).\n"
        "- Rated speed $n_{nom}$ (rpm) — used to derive the number of poles "
        "and $s_{nom}$.\n"
        "- Rated efficiency $\\eta$ and power factor $\\cos\\varphi$.\n"
        "- Starting-to-rated current ratio $I_p/I_n$.\n"
        "- Starting-to-rated torque ratio $T_p/T_n$."
    )

    st.markdown("**Calculation sequence:**")

    st.markdown("**1.** Derivation of slip and rated quantities:")
    _eq(r"s_{nom} = 1 - \frac{n_{nom}}{n_s}, \qquad n_s = \frac{120\,f}{p}")
    _eq(r"I_n = \frac{P_n}{\sqrt{3}\,V_l\,\eta\,\cos\varphi}, \qquad T_n = \frac{P_n}{\omega_{r,nom}}")

    st.markdown("**2.** Estimation of starting current and short-circuit impedance:")
    _eq(r"I_p = \left(\frac{I_p}{I_n}\right) I_n, \qquad Z_k = \frac{V_f}{I_p}, \qquad X_k = Z_k\,\sqrt{1 - \cos^2\!\varphi_p}")
    st.markdown(
        "where $\\cos\\varphi_p \\approx 0{,}20$ is the typical starting power factor "
        "(NEMA B assumption for single squirrel-cage motors)."
    )

    st.markdown("**3.** Leakage reactance distribution (NEMA B assumption):")
    _eq(r"X_{ls} = 0{,}4\,X_k, \qquad X_{lr}' = 0{,}6\,X_k")

    st.markdown(
        "**4.** Estimation of $R_s$ and $R_r'$ by rated power balance:"
    )
    _eq(r"P_{cu,s} = 3\,I_n^2\,R_s = P_{in} - P_{ag} - P_{fe}, \qquad P_{cu,r} = 3\,I_n^2\,R_r' = s_{nom}\,P_{ag}")

    st.markdown("**5.** Magnetizing reactance by subtraction:")
    _eq(r"X_m = X_{cc} - X_{ls}, \qquad X_{cc} = \frac{V_f}{I_{cc}}")

    _div_warn(
        "**Nameplate Estimator limitations:** the parameters obtained are approximations "
        "based on NEMA statistical assumptions — suitable for simulation and "
        "sensitivity analysis, but **do not replace physical identification tests** "
        "(no-load and locked-rotor tests per IEEE Std 112). For motors outside the "
        "NEMA B standard (double cage, wound rotor, high-efficiency IE4 motors), "
        "results may deviate significantly from real values."
    )

    st.divider()

    # ── Section 7.2: IEEE Std 112-2017 ──────────────────────────────────────
    st.markdown("### Section 7.2 — IEEE Std 112-2017 Estimator (three physical tests)")

    st.info(
        "**When to use:** physical test data available (DC, no-load, "
        "locked rotor). Indicated for high-precision parameters, dynamic model validation, "
        "commissioning, and comparison with nameplate data."
    )

    _h4("7.2.1 — Background")
    st.markdown(
        "The method identifies $R_s, R_r', X_m, X_{ls}, X_{lr}', R_{fe}$ from "
        "**three physical tests** described in IEEE Std 112-2017. The implementation "
        "is in `core/param_estimator.py:193–406` (function "
        "`estimate_params_ieee_tests`). Each test exploits a specific operating condition "
        "of the T-equivalent circuit, isolating a subset of the parameters."
    )

    _h4("7.2.2 — DC Test (IEEE 112 Cl. 6.4)")
    st.markdown(
        "DC voltage is applied between two terminals with the rotor at rest. Since "
        "$X = 0$ in DC steady state, only resistances are seen. The calculation of "
        "$R_s$ depends on the winding connection topology "
        "(cf. `core/param_estimator.py:263–266`):"
    )
    _eq(r"R_s\Big|_Y = \tfrac{1}{2}\,\frac{V_{dc}}{I_{dc}} \qquad\text{(star — two windings in series)}")
    _eq(r"R_s\Big|_\Delta = \tfrac{3}{2}\,\frac{V_{dc}}{I_{dc}} \qquad\text{(delta — two in parallel, one in series)}")
    st.markdown(
        "**Experimental precautions:** correct the measured value to operating temperature "
        "(IEEE 112 Cl. 5.4); wait for thermal stabilization before reading. "
        "Small errors in $R_s$ propagate to other parameters via "
        "$R_r' = R_k - R_s$."
    )

    _h4("7.2.3 — No-Load Test (IEEE 112 Cl. 6.5)")
    st.markdown(
        "The motor is run without a coupled load at rated voltage and frequency. "
        "$V_{l,NL}$, $I_{NL}$, $P_{NL}$, and $f_{NL}$ are measured. The test identifies $X_m$, "
        "$R_{fe}$, and the air-gap voltage $E_{1,NL}$. Loss separation follows:"
    )
    _eq(r"P_{NL} = 3\,R_s\,I_{NL}^{\,2} + P_{fe} + P_{fw}")
    st.markdown(
        "When $P_{fw}$ (friction and windage) is not measured by coast-down, the "
        "heuristic is used (cf. `core/param_estimator.py:278`):"
    )
    _eq(r"P_{fw} = 0{,}008\,P_{NL}")
    st.markdown(
        "**Double phasor iteration** to refine $E_{1,NL}$ "
        "(cf. `core/param_estimator.py:329–376`):"
    )
    st.markdown(
        "*Iteration 1* — initial approximation assuming $I_{NL}$ in phase with $V_{f,NL}$:"
    )
    _eq(r"E_{1,NL}^{(1)} = \sqrt{(V_{f,NL} - R_s\,I_{NL})^{\,2} + (X_{ls}\,I_{NL})^{\,2}}")
    st.markdown(
        "*Iteration 2* — correct decomposition of $I_{NL}$ into components $I_{fe}$ "
        "(in phase with $E_1$) and $I_\\mu$ (in quadrature):"
    )
    _eq(r"E_{1,NL}^{(2)} = \sqrt{(V_{f,NL} - R_s\,I_{fe} - X_{ls}\,I_\mu)^{\,2} + (X_{ls}\,I_{fe} - R_s\,I_\mu)^{\,2}}")
    st.markdown("**Final results of the no-load test:**")
    _eq(r"R_{fe} = \frac{3\,E_{1,NL}^{\,2}}{P_{fe}}, \qquad I_\mu = \sqrt{I_{NL}^{\,2} - I_{fe}^{\,2}}, \qquad X_m = \frac{E_{1,NL}}{I_\mu} - X_{ls}")

    _h4("7.2.4 — Locked-Rotor Test (IEEE 112 Cl. 6.6)")
    st.markdown(
        "The rotor is mechanically locked and reduced voltage is applied until rated current "
        "is reached. Testing at reduced frequency "
        "$f_{LR} \\approx 0{,}25\\,f_{nom}$ is recommended to minimize the skin effect. "
        "The measured quantities are $V_{l,LR}$, $I_{LR}$, $P_{LR}$, and $f_{LR}$ "
        "(cf. `core/param_estimator.py:296–327`):"
    )
    _eq(r"Z_k = \frac{V_{f,LR}}{I_{LR}}, \qquad R_k = \frac{P_{LR}}{3\,I_{LR}^{\,2}}, \qquad X_k\big|_{f_{LR}} = \sqrt{Z_k^{\,2} - R_k^{\,2}}")
    st.markdown(
        "**Linear frequency correction** to project $X_k$ to rated frequency "
        "(cf. `core/param_estimator.py:312`):"
    )
    _eq(r"X_k\big|_{f_{nom}} = X_k\big|_{f_{LR}}\cdot\frac{f_{NL}}{f_{LR}}")
    st.markdown("The referred rotor resistance is obtained by subtraction:")
    _eq(r"R_r' = R_k - R_s, \qquad \text{with validation } R_r' > 0")

    _h4("7.2.5 — $X_{ls}/X_k$ Distribution by NEMA Class")
    st.markdown(
        "The short-circuit reactance $X_k$ represents the sum $X_{ls} + X_{lr}'$ — no "
        "physical test can separate the two terms. IEEE 112 adopts a "
        "**tabulated fraction**, depending on the motor construction class "
        "(cf. table `_IEEE_SPLIT_TABLE` in `core/param_estimator.py:183–190`):"
    )
    st.markdown(
        "| NEMA Class | $X_{ls}/X_k$ | $X_{lr}'/X_k$ | Application |\n"
        "|---|---|---|---|\n"
        "| A | $0{,}50$ | $0{,}50$ | Motors above $45\\;\\text{kW}$, wound rotor |\n"
        "| **B (standard)** | **$0{,}40$** | **$0{,}60$** | Industrial NEMA $1$–$100\\;\\text{kW}$ |\n"
        "| C | $0{,}30$ | $0{,}70$ | High impedance, high slip |\n"
        "| D | $0{,}50$ | $0{,}50$ | High starting torque |\n"
        "| WR (wound rotor) | $0{,}50$ | $0{,}50$ | Slip rings |\n"
        "| Custom | $\\alpha$ | $1-\\alpha$ | User-defined |"
    )

    _h4("7.2.6 — Usage Instructions (step by step)")
    st.markdown(
        "The fields corresponding to this estimator are located in the simulator "
        "sidebar, under the **IEEE Std 112-2017** mode "
        "(cf. `ui_components/sim_config.py:763–862`)."
    )
    st.markdown("**DC Test** — three values:")
    st.markdown(
        "- $V_{dc}$ (V) — DC voltage applied between two terminals.\n"
        "- $I_{dc}$ (A) — DC current measured at thermal steady state.\n"
        "- **Connection** — choose between star ($Y$) or delta ($\\Delta$)."
    )
    st.markdown("**No-Load Test** — five values:")
    st.markdown(
        "- $V_{l,NL}$ (V) — line voltage applied at the terminals.\n"
        "- $I_{NL}$ (A) — no-load line current.\n"
        "- $P_{NL}$ (W) — three-phase active power absorbed at no load.\n"
        "- $f_{NL}$ (Hz) — source frequency during the test.\n"
        "- $P_{fw}$ (W) — mechanical losses measured by coast-down "
        "(optional; leave at zero to apply the $0{,}8\\%\\,P_{NL}$ heuristic)."
    )
    st.markdown("**Locked-Rotor Test** — four values:")
    st.markdown(
        "- $V_{l,LR}$ (V) — reduced line voltage.\n"
        "- $I_{LR}$ (A) — line current near rated value.\n"
        "- $P_{LR}$ (W) — three-phase active power.\n"
        "- $f_{LR}$ (Hz) — source frequency, ideally "
        "$f_{LR} \\approx 0{,}25\\,f_{nom}$."
    )
    st.markdown(
        "**$X_{ls}/X_k$ distribution** — select the motor NEMA class. For "
        "Custom, adjust the fraction $\\alpha$ slider."
    )

    _h4("7.2.7 — Result Interpretation and Physical Sanity Criteria")
    st.markdown(
        "After execution, the estimator automatically validates each output against "
        "physical criteria. Warnings displayed in the **Calculation Details** panel "
        "(cf. `ui_components/sim_config.py:886`) indicate violations:"
    )
    st.markdown(
        "| Criterion | Physical meaning | Implementation |\n"
        "|---|---|---|\n"
        "| $R_s, R_r' > 0$ | Physically positive resistances | `param_estimator.py:269, 316` |\n"
        "| $P_{fe} > 0$ | $P_{NL}$ exceeds Joule losses plus $P_{fw}$ | L:283–291 |\n"
        "| $I_\\mu^{\\,2} > 0$ | No-load test $\\cos\\varphi$ is consistent | L:366–372 |\n"
        "| $R_k < Z_k$ | Power factor $\\le 1$ in locked-rotor test | L:301–307 |\n"
        "| $X_m / X_{ls} \\ge 5$ | Typical ratio for industrial motor | warning in `sim_config.py:947–950` |\n"
        "| $R_{fe} \\ge 50\\;\\Omega$ | $P_{fe}$ in realistic range | warning in `sim_config.py:952–955` |"
    )
    st.markdown(
        "**Connection to `MachineParams`:** the dictionary returned by the estimator is "
        "written to the fields $R_s$, $R_r'$, $X_m$, $X_{ls}$, $X_{lr}'$, $R_{fe}$ of the "
        "dataclass (cf. `core/machine_model.py:40–51`). The reference frequency "
        "$f_{ref}$ is set to $f_{NL}$ (cf. `core/machine_model.py:88–101`) and the "
        "resulting mutual reactance $X_{ml}$ is recalculated in `_xml_from_lm` "
        "(cf. `core/machine_model.py:158–163`)."
    )

    _div_warn(
        "**Cross-check recommendation:** even when using the IEEE 112 estimator, "
        "it is recommended to run the Nameplate estimator as a cross-check. "
        "Discrepancies greater than $\\pm 20\\%$ between the two methods indicate problems "
        "in the tests (unstable measurements, off-nominal temperature, harmonic distortion in "
        "the source) or that the motor under test deviates from the NEMA B standard assumed by the Nameplate method."
    )
