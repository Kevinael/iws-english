# -*- coding: utf-8 -*-
"""
theory_dc.py
============
DC machine Theory tab with 7 pedagogical sub-tabs covering modelling, dynamics, current patterns, speed control, generator operation, parameter estimator, and user manual.

Responsibilities:
  - Render 7 sub-tabs for DCM theory content in a structured Streamlit layout.
  - Load PNG images from imgs/ via _show_png.
  - Call interactive components from theory_dc_interactive for each sub-tab.

Relationships:
  Imported by : IWS_UI (indirectly via theory_view)
  Imports     : ui.theory_dc_interactive

Extending:
  - To add a sub-tab, create the interactive component in theory_dc_interactive.py and add a tab here.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_PNG_DIR = Path(__file__).parent.parent / "imgs"


def _png(name: str):
    p = _PNG_DIR / name
    return str(p) if p.exists() else None


def _show_png(name: str, caption: str = "") -> None:
    path = _png(name)
    if path:
        st.image(path, caption=caption, use_container_width=True)
    else:
        st.info(f"Image not found: `{name}` — run `mcc_desenhos.py` to generate.")


def render_theory_dc_tab() -> None:
    """Renders the 7 sub-tabs of the DC Machine Theory tab."""
    tabs = st.tabs([
        "1 · Modeling and Circuits",
        "2 · Dynamics and Torque",
        "3 · Current Patterns",
        "4 · Speed Control",
        "5 · Generator Operation",
        "6 · Parameter Estimator",
        "7 · User Manual",
    ])

    # ── Sub-tab 1: Modeling and Circuits ─────────────────────────────────
    with tabs[0]:
        st.markdown("## DC Machine Modeling — Equivalent Circuits")
        st.markdown(r"""
The direct current machine is modeled by three ordinary differential equations:

**Armature circuit:**
$$\frac{di_a}{dt} = \frac{1}{L_a}\left(V_a - R_a i_a - k_b \Phi i_a\right)$$

**Field circuit (separately excited / shunt):**
$$\frac{di_{fd}}{dt} = \frac{1}{L_f}\left(V_f - R_f i_{fd}\right)$$

**Mechanical equation:**
$$\frac{d\omega_m}{dt} = \frac{1}{J}\left(T_e - T_l - B\omega_m\right)$$

where $T_e = k_b \, i_{fd} \, i_a$ and $E_a = k_b \, i_{fd} \, \omega_m$.
""")

        cols = st.columns(3)
        with cols[0]:
            _show_png("separate_motor.png", "Separately Excited — Motor")
        with cols[1]:
            _show_png("shunt_motor.png", "Shunt — Motor")
        with cols[2]:
            _show_png("serie_motor.png", "Series — Motor")

        cols2 = st.columns(2)
        with cols2[0]:
            _show_png("separate_gerador.png", "Separately Excited — Generator")
        with cols2[1]:
            _show_png("shunt_gerador.png", "Shunt — Generator")

        try:
            from ui.theory_dc_interactive import render_diagrama_blocos_mcc
            render_diagrama_blocos_mcc()
        except Exception:
            pass

    # ── Sub-tab 2: Dynamics and Torque ★ ─────────────────────────────────
    with tabs[1]:
        st.markdown("## Dynamics and Torque × Speed Curves")
        st.markdown(r"""
The pedagogical distinction of the DC machine is how each excitation type modifies the dynamic behavior:

| Excitation | T×ωm Curve | Starting Current |
|-----------|-----------|---------------------|
| **Series** | Hyperbolic ($T \propto i_a^2$) | High peak |
| **Shunt** | Quasi-linear | Moderate peak |
| **Separately Excited** | Adjustable via $V_f$ | Controllable |

**Field weakening (separately excited):**
Reducing $V_f$ → $i_{fd}$ decreases → $E_a = k_b i_{fd} \omega_m$ reduces → $i_a$ increases → motor accelerates beyond base speed.
""")
        col_img, _ = st.columns([1, 1])
        with col_img:
            _show_png("wm_x_T.png", "T×ωm curves for the three excitation types")

        try:
            from ui.theory_dc_interactive import render_curvas_comparativas_excitacao
            render_curvas_comparativas_excitacao()
        except Exception:
            pass

    # ── Sub-tab 3: Current Patterns ★ ────────────────────────────────────
    with tabs[2]:
        st.markdown("## Armature Current Patterns")
        st.markdown(r"""
The armature current $i_a(t)$ directly reflects the characteristics of each configuration:

- **Series:** very high starting peak; slower settling
- **Shunt:** smooth transient; $i_{fd}$ reaches steady state before $i_a$
- **Separately Excited:** independent control of $\Phi$ and $i_a$

Use the interactive tool below to compare waveforms.
""")
        try:
            from ui.theory_dc_interactive import render_padrao_corrente_dc
            render_padrao_corrente_dc()
        except Exception:
            st.info("Interactive component unavailable.")

    # ── Sub-tab 4: Speed Control ──────────────────────────────────────────
    with tabs[3]:
        st.markdown("## Speed Control")
        st.markdown(r"""
Two primary methods:

**1. Armature voltage control** ($V_a$):
$$\omega_m = \frac{V_a - R_a i_a}{k_b \Phi}$$
Valid for $\omega_m \leq \omega_{base}$.

**2. Field weakening** (reduction of $V_f$):
$$\omega_m \propto \frac{1}{i_{fd}}$$
Valid for $\omega_m > \omega_{base}$ — $T_e$ decreases, constant power.
""")
        try:
            from ui.theory_dc_interactive import render_controle_velocidade_dc
            render_controle_velocidade_dc()
        except Exception:
            st.info("Interactive component unavailable.")

    # ── Sub-tab 5: Generator Operation ───────────────────────────────────
    with tabs[4]:
        st.markdown("## DC Generator Operation")
        st.markdown(r"""
When external mechanical torque drives $\omega_m$ and the machine receives no $V_a$ (or $V_a = 0$):

$$E_a = k_b i_{fd} \omega_m \quad \Rightarrow \quad i_a = \frac{E_a}{R_a + R_l}$$

The terminal voltage is:
$$V_t = R_l \, i_a$$

**Shunt generator:** the field current is supplied by the generated voltage itself — requires self-excitation via magnetic remanence.

**Separately excited generator:** $V_f$ is an independent source — does not depend on $V_t$.
""")
        _show_png("gerador_comparativo.png", "Characteristic curves Vt×Ia")

    # ── Sub-tab 6: Parameter Estimator ───────────────────────────────────
    with tabs[5]:
        st.markdown("## DC Parameter Estimator")
        st.markdown(r"""
**DC resistance test:** $R_a = V_{dc} / I_{dc}$

**No-load test:** $E_a = V_a - R_a I_{a,nl}$, $k_b = E_a / (i_{fd} \omega_{m,nl})$

**Magnetization curve:** $\Phi$ vs $i_{fd}$ — relates flux to field current.
""")
        _show_png("curva_magnetizacao_simples_pb.png", "Magnetization Curve")

        try:
            from ui.theory_dc_interactive import render_estimador_dc
            render_estimador_dc()
        except Exception:
            st.info("Interactive component unavailable.")

    # ── Sub-tab 7: User Manual ────────────────────────────────────────────
    with tabs[6]:
        st.markdown("## User Manual — DC Machine Simulator")
        st.markdown(r"""
### Typical simulation workflow

1. **Select the configuration** (Separately Excited Motor, Shunt Motor, Series Motor, Separately Excited Generator, Shunt Generator)
2. **Adjust parameters** or load a factory **preset**
3. **Choose the operating mode** (DOL, Resistance, Plugging, Pulse, Field Weakening, Generator)
4. **Configure the experiment** (duration, mode-specific parameters)
5. **Select quantities** to plot ($i_a$, $\omega_m$, $T_e$, $E_a$, $V_t$, $n$)
6. Click **Run Simulation**
7. Navigate through the 4 result sub-tabs

### Available presets

| Preset | Source | Highlight |
|--------|-------|----------|
| Separately Excited Motor (dcmei) | Scilab `dcmei.sce` | Okoro 2008 parameters |
| Shunt Motor (dcmp)               | Scilab `dcmp.sce`  | Parallel excitation   |
| Series Motor (dcms)              | Scilab `dcms.sce`  | Hyperbolic curve      |
| Separately Excited Generator     | Scilab `dgmei.sce` | Resistive load        |
| Shunt Generator                  | Scilab `dcgp.sce`  | Self-excitation       |

### Comparing excitation types

Use **Save as Reference** after simulating each excitation type. Overlays up to 5 curves on the same figure.

### Result quantities

| Symbol | Description |
|---------|-----------|
| $i_a$   | Armature current |
| $i_{fd}$| Field current |
| $\omega_m$ | Angular speed (rad/s) |
| $n$     | Speed (RPM) |
| $T_e$   | Electromagnetic torque |
| $E_a$   | Back electromotive force |
| $V_t$   | Terminal voltage |
""")
