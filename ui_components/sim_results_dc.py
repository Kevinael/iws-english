# -*- coding: utf-8 -*-
"""
sim_results_dc.py
=================
Renders the four DC machine result sub-tabs: Overview, Dynamic Analysis, Diagnostics & Faults, and Asset Management.

Responsibilities:
  - Render DCM KPI cards and health summary in the Overview sub-tab.
  - Build and cache Plotly waveform charts for the Dynamic Analysis sub-tab.
  - Display DCM diagnostics and fault analysis in the Diagnostics & Faults sub-tab.
  - Support PDF download for DCM simulation reports.

Relationships:
  Imported by : IWS_UI
  Imports     : core.dc_machine_model, viz.plotly_charts_dc

Extending:
  - To add a new DCM sub-tab, follow the same pattern as sim_results.py.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.dc_machine_model import DCMachineParams
from viz.plotly_charts_dc import (
    build_fig_stacked_dc,
    build_fig_sidebyside_dc,
    build_fig_overlay_dc,
    build_fig_torque_speed_dc,
)


# ─────────────────────────────────────────────────────────────────────────────
# CACHE LAYER (mirrors sim_results.py:28–56)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_fig_stacked_dc(
    res: dict,
    var_keys: tuple,
    var_labels: tuple,
    dark: bool,
    t_events: tuple,
    decimals: int,
    _cache_key: int = 0,
) -> go.Figure:
    return build_fig_stacked_dc(res, list(var_keys), list(var_labels), dark, list(t_events), decimals)


@st.cache_data(show_spinner=False)
def _cached_fig_torque_speed_dc(
    res: dict,
    exc: str,
    dark: bool,
    _cache_key: int = 0,
) -> go.Figure:
    return build_fig_torque_speed_dc(res, exc, dark)


_PLOT_CFG: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": False,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "dcm_simulation",
        "scale": 3,
        "height": 600,
        "width": 1200,
    },
}

_EXC_LABELS: dict[str, str] = {
    "sep_motor":    "Separately Excited — Motor",
    "shunt_motor":  "Shunt (Parallel) — Motor",
    "series_motor": "Series — Motor",
    "sep_gen":      "Separately Excited — Generator",
    "shunt_gen":    "Shunt (Parallel) — Generator",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _nota_apos_dc(key: str, mode: str, mp: DCMachineParams) -> None:
    """Displays contextual technical note below the chart, mirroring MIT sim_results.py."""
    _tau_a = mp.La / max(mp.Ra, 1e-9)
    exc = mp.excitation
    is_series = exc == "series_motor"

    notas: dict[str, str] = {
        "ia": (
            f"Armature current $i_a$ rises rapidly at switch-on ($\\tau_a = L_a/R_a = {_tau_a*1000:.2f}\\,\\text{{ms}}$) "
            f"and is limited as back-EMF $E_a = k_b \\cdot i_{{fd}} \\cdot \\omega_m$ grows. "
            f"Steady state satisfies $i_{{a,ss}} = (V_a - E_{{a,ss}}) / R_a$."
        ),
        "ifd": (
            f"Field current $i_{{fd}}$ determines magnetic flux and thus effective $k_b$. "
            f"Its dynamics are slower than the armature: $\\tau_f = L_f/R_f = {(mp.Lf/max(mp.Rf,1e-9))*1000:.2f}\\,\\text{{ms}}$."
        ) if not is_series else (
            "Series motor: $i_{fd} = i_a$ (field in series with armature). "
            "Torque is proportional to $i_a^2$, resulting in high starting torque."
        ),
        "wm": (
            f"Angular acceleration: $\\dot{{\\omega}}_m = (T_e - T_l - B\\,\\omega_m) / J$. "
            f"With $J = {mp.J:.4f}\\,\\text{{kg·m}}^2$, the typical mechanical time constant is "
            f"$\\tau_m = J \\cdot R_a / k_b^2 \\approx {(mp.J * mp.Ra / max(mp.kb**2, 1e-9)):.3f}\\,\\text{{s}}$."
        ),
        "n": (
            f"Speed in RPM. Steady state: $n_{{ss}} = 60 \\cdot \\omega_{{m,ss}} / (2\\pi)$. "
            f"Field weakening (↓$V_f$ or ↓$I_{{fd}}$) increases steady-state speed."
        ),
        "Te": (
            f"Electromagnetic torque: $T_e = k_b \\cdot i_{{fd}} \\cdot i_a$"
            if not is_series else
            f"Electromagnetic torque: $T_e = k_b \\cdot i_a^2$ (series — high starting torque)."
        ),
        "Ea": (
            f"Back-EMF: $E_a = k_b \\cdot i_{{fd}} \\cdot \\omega_m$. "
            f"In steady state, $E_a \\approx V_a - R_a \\cdot i_{{a,ss}}$."
        ),
        "Vt": (
            f"Terminal voltage. Motor: $V_t = V_a - R_a \\cdot i_a$ (resistive drop). "
            f"Generator: $V_t = E_a - R_a \\cdot i_a$ (below back-EMF)."
        ) if not exc.endswith("_gen") else (
            f"Generator terminal voltage: $V_t = E_a - R_a \\cdot i_a$. "
            f"In steady state, $V_t$ depends on load $R_l$."
        ),
    }

    nota = notas.get(key)
    if nota:
        st.caption(nota)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def render_results_dc(
    res: dict,
    var_keys: list[str],
    var_labels: list[str],
    dark: bool,
    t_events: list,
    mp: DCMachineParams,
    exp_label: str,
    exp_type: str,
    exp_config: dict,
    tmax: float,
    h: float,
    decimals: int = 3,
    ref_list: list | None = None,
    energy_tariff: float = 0.75,
    **kwargs,
) -> None:
    """Renders the 4 DC machine result sub-tabs."""
    d   = decimals
    exc = mp.excitation if mp else res.get("excitation", "sep_motor")
    is_gen = exc in ("sep_gen", "shunt_gen")

    _cache_key = hash(repr(res.get("ia", [])[:5]))

    tab_visao, tab_dinamica, tab_diag, tab_ativos = st.tabs(
        ["Overview", "Dynamic Analysis", "Diagnostics & Faults", "Asset Management"],
        key="results_tabs_dc",
    )

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1 — OVERVIEW
    # ══════════════════════════════════════════════════════════════════════
    with tab_visao:
        n_ss   = res.get("n_ss",   0.0)
        Te_ss  = res.get("Te_ss",  0.0)
        ia_ss  = res.get("ia_ss",  0.0)
        ifd_ss = res.get("ifd_ss", 0.0)
        Ea_ss  = res.get("Ea_ss",  0.0)
        Vt_ss  = res.get("Vt_ss",  0.0)
        wm_ss  = res.get("wm_ss",  0.0)

        # ── Health Panel ──────────────────────────────────────────────────
        ia_peak = float(np.max(np.abs(res["ia"])))
        Va_nom  = mp.Va if mp else 24.0
        overcurrent = ia_peak > 10.0 * abs(ia_ss) if abs(ia_ss) > 1e-6 else False

        if not res.get("success", True):
            st.error("🔴 **Numerical Failure** — integrator did not converge. Reduce $h$ or review parameters.")
        elif overcurrent:
            st.warning(f"🟡 **Attention** — peak $i_a$ = {ia_peak:.1f} A "
                       f"({ia_peak/max(abs(ia_ss),1e-6):.1f}× steady state). "
                       f"Steady-state speed: **{n_ss:.0f} RPM**")
        else:
            st.success(f"🟢 **Normal Operation** — $n$ = **{n_ss:.0f} RPM** | "
                       f"$T_e$ = **{Te_ss:.{d}f} N·m** | "
                       f"$i_a$ = **{ia_ss:.{d}f} A**")

        st.write("")

        # ── Operating KPIs ────────────────────────────────────────────────
        st.markdown('<p class="slabel">Operating Quantities</p>', unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric("Speed (RPM)",            f"{n_ss:.{d}f}")
        k2.metric("$T_e$ (N·m)",            f"{Te_ss:.{d}f}")
        k3.metric("$i_a$ (A)",              f"{ia_ss:.{d}f}")

        k4, k5, k6 = st.columns(3)
        k4.metric("$\\omega_m$ (rad/s)",    f"{wm_ss:.{d}f}")
        k5.metric("$E_a$ (V)",              f"{Ea_ss:.{d}f}")
        k6.metric("$V_t$ (V)",              f"{Vt_ss:.{d}f}")

        if exc not in ("series_motor",):
            k7, k8, _ = st.columns(3)
            k7.metric("$i_{fd}$ (A)",       f"{ifd_ss:.{d}f}")
            k8.metric("Excitation",         _EXC_LABELS.get(exc, exc))

        # ── Starting Transient ────────────────────────────────────────────
        with st.expander("Starting Transient", expanded=False):
            tc1, tc2 = st.columns(2)
            tc1.metric("Peak $i_a$ (A)",    f"{float(np.max(np.abs(res['ia']))):.{d}f}")
            tc2.metric("Peak $T_e$ (N·m)",  f"{float(np.max(res['Te'])):.{d}f}")

        # ── Protection Recommendations ────────────────────────────────────
        Ra_mp   = mp.Ra if mp else 1.0
        P_mec_out_nom = abs(Te_ss) * abs(wm_ss)
        if abs(Va_nom) > 1e-6 and P_mec_out_nom > 1e-6:
            _eta_nom = P_mec_out_nom / max(abs(Va_nom) * abs(ia_ss), 1e-9)
            Ia_nom = (P_mec_out_nom / max(abs(Va_nom) * _eta_nom, 1e-9))
        else:
            Ia_nom = abs(ia_ss)

        with st.expander("Protection Recommendations (IEC)", expanded=False):
            _pk_ratio = ia_peak / max(Ia_nom, 1e-6)
            _classe_rele = "Class 10" if _pk_ratio < 6 else ("Class 20" if _pk_ratio < 8 else "Class 30")
            _fusivel    = Ia_nom * 2.0
            _disjuntor  = f"{Ia_nom:.1f} – {Ia_nom * 1.25:.1f}"

            pr1, pr2, pr3 = st.columns(3)
            pr1.metric("Overload Relay",           _classe_rele,
                       help="IEC 60947-4-1 — based on peak-to-rated current ratio")
            pr2.metric("Fuse ≥ (A)",               f"{_fusivel:.1f}",
                       help="IEC 60269-1 — minimum 2× rated current")
            pr3.metric("Motor Circuit Breaker (A)", _disjuntor,
                       help="IEC 60947-2 — range 1.0–1.25× rated current")
            if exc in ("sep_motor", "sep_gen"):
                st.warning(
                    "**Open-field protection:** separately excited motors risk overspeed "
                    "if the field circuit opens under load — "
                    "use an open-field protection relay (IEC 60947-4-1)."
                )

        # ── Economic Summary ──────────────────────────────────────────────
        _P_elec_ss = abs(Va_nom) * abs(ia_ss)
        if energy_tariff > 0 and _P_elec_ss > 1e-3 and not is_gen:
            st.write("")
            _eta_pct   = P_mec_out_nom / max(_P_elec_ss, 1e-9) * 100
            _custo_ano = _P_elec_ss / 1000 * 8760 * energy_tariff
            ec1, ec2, ec3 = st.columns(3)
            ec1.metric("Efficiency η (%)",         f"{_eta_pct:.1f}")
            ec2.metric("Annual Cost ($)",           f"{_custo_ano:,.2f}",
                       help=f"Tariff: $ {energy_tariff:.4f}/kWh — continuous operation")
            ec3.metric("Input power (kW)",          f"{_P_elec_ss/1000:.3f}")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2 — DYNAMIC ANALYSIS
    # ══════════════════════════════════════════════════════════════════════
    with tab_dinamica:
        # ── Saved References Panel ────────────────────────────────────────
        if ref_list:
            try:
                from ui_components.tim_results import render_ref_panel
                render_ref_panel()
            except Exception:
                pass

        _cc1, _cc2, _cc3 = st.columns([2, 2, 1])
        with _cc1:
            viz_opts  = ["Stacked", "Side by Side", "Overlay"]
            plot_mode = st.radio("View", viz_opts, horizontal=True,
                                 key="plot_mode_dc", label_visibility="visible")
        with _cc2:
            zoom_opts = ["Full", "Transient", "Steady State"]
            zoom_mode = st.radio("Zoom", zoom_opts, horizontal=True,
                                 key="zoom_mode_dc", label_visibility="visible")
        with _cc3:
            dark_plot = st.toggle("Dark background", key="plot_dark_dc", value=dark)

        # Temporal zoom filter
        t_arr = res["t"]
        tmax_sim = float(t_arr[-1])
        if zoom_mode == "Transient":
            t_cut = tmax_sim * 0.3
            mask  = t_arr <= t_cut
        elif zoom_mode == "Steady State":
            t_cut = tmax_sim * 0.7
            mask  = t_arr >= t_cut
        else:
            mask = np.ones(len(t_arr), dtype=bool)

        res_zoom = {k: (v[mask] if isinstance(v, np.ndarray) and len(v) == len(t_arr) else v)
                    for k, v in res.items()}

        tl_arr = res_zoom.get("Tl")

        if plot_mode == "Stacked":
            fig = _cached_fig_stacked_dc(
                res_zoom, tuple(var_keys), tuple(var_labels),
                dark_plot, tuple(t_events), d, _cache_key=_cache_key,
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key="dc-stacked")
            # Contextual notes per variable
            for _vk in var_keys:
                _nota_apos_dc(_vk, exp_type, mp)

        elif plot_mode == "Side by Side":
            figs = build_fig_sidebyside_dc(
                res_zoom, var_keys, var_labels, dark_plot, list(t_events), d,
                ref_list=ref_list, tl_arr=tl_arr,
            )
            for i, f in enumerate(figs):
                st.plotly_chart(f, use_container_width=True, config=_PLOT_CFG, key=f"dc-side-{i}")

        else:  # Overlay
            fig = build_fig_overlay_dc(
                res_zoom, var_keys, var_labels, dark_plot, list(t_events), d,
                ref_list=ref_list, tl_arr=tl_arr,
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG, key="dc-overlay")

        # T×ωn curve
        st.markdown('<p class="slabel">Torque × Speed Curve</p>', unsafe_allow_html=True)
        fig_tn = _cached_fig_torque_speed_dc(res, exc, dark_plot, _cache_key=_cache_key)
        st.plotly_chart(fig_tn, use_container_width=True, config=_PLOT_CFG, key="dc-torque-speed")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3 — DIAGNOSTICS & FAULTS
    # ══════════════════════════════════════════════════════════════════════
    with tab_diag:
        n_ss   = res.get("n_ss",   0.0)
        Te_ss  = res.get("Te_ss",  0.0)
        ia_ss  = res.get("ia_ss",  0.0)
        ifd_ss = res.get("ifd_ss", 0.0)
        wm_ss  = res.get("wm_ss",  0.0)

        st.markdown('<p class="slabel">Commutation and Current Analysis</p>', unsafe_allow_html=True)

        ia_arr  = res["ia"]
        ia_max  = float(np.max(np.abs(ia_arr)))
        ia_std  = float(np.std(ia_arr[len(ia_arr)//2:]))

        d1, d2, d3 = st.columns(3)
        d1.metric("Peak $i_a$ (A)",              f"{ia_max:.{d}f}")
        d2.metric("$i_a$ steady state (A)",      f"{ia_ss:.{d}f}")
        d3.metric("Ripple $\\sigma(i_a)$",       f"{ia_std:.{d}f}")

        # Quality: relative ripple
        _ripple_rel = ia_std / max(abs(ia_ss), 1e-6) * 100
        if _ripple_rel > 5.0:
            st.warning(f"Relative $i_a$ ripple = {_ripple_rel:.1f}% — check $L_a$ and switching frequency.")

        # Automatic anomaly checks
        anomalias: list[tuple[str, str, str]] = []

        if ia_max > 15.0 * max(abs(ia_ss), 1e-6):
            anomalias.append(("🔴 Critical", "Extreme overcurrent at starting",
                               f"Peak {ia_max:.1f} A = {ia_max/max(abs(ia_ss),1e-6):.0f}× steady state. "
                               "Use series resistance or reduce $V_a$."))

        if not res.get("success", True):
            anomalias.append(("🔴 Critical", "Integrator numerical failure",
                               "Reduce $h$ to 1×10⁻⁵ s or check parameters."))

        if exc not in ("series_motor",):
            ifd_arr = res["ifd"]
            ifd_std = float(np.std(ifd_arr[len(ifd_arr)//2:]))
            if ifd_std > 0.05 * max(abs(ifd_ss), 1e-6):
                anomalias.append(("🟡 Warning", "Field instability",
                                   f"$\\sigma(i_{{fd}})$ = {ifd_std:.4f} A in steady state. "
                                   "Check $R_f$ and $L_f$."))

        wm_arr = res["wm"]
        if len(wm_arr) > 10 and float(np.mean(wm_arr[-10:])) < 0.01 * abs(wm_ss) and abs(wm_ss) > 1:
            anomalias.append(("🟡 Warning", "Steady state not reached",
                               f"$\\omega_m$ still in transient at end of simulation. "
                               "Increase $t_{{max}}$."))

        if not anomalias:
            st.success("🟢 No anomalies detected.")
        else:
            for sev, titulo, desc in anomalias:
                with st.expander(f"{sev} — {titulo}", expanded=True):
                    st.write(desc)


    # ══════════════════════════════════════════════════════════════════════
    # TAB 4 — ASSET MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativos:
        n_ss   = res.get("n_ss",   0.0)
        Te_ss  = res.get("Te_ss",  0.0)
        ia_ss  = res.get("ia_ss",  0.0)
        ifd_ss = res.get("ifd_ss", 0.0)
        wm_ss  = res.get("wm_ss",  0.0)

        st.markdown('<p class="slabel">Efficiency and Loss Analysis</p>', unsafe_allow_html=True)

        Ra   = mp.Ra if mp else 1.0
        Rf   = mp.Rf if mp else 0.0
        B    = mp.B  if mp else 0.0
        Va   = mp.Va if mp else 24.0

        P_Ra   = float(ia_ss ** 2 * Ra)
        P_Rf   = float(ifd_ss ** 2 * Rf) if exc not in ("series_motor",) else 0.0
        P_mec  = float(B * wm_ss ** 2)
        P_elec = float(abs(Va) * abs(ia_ss)) if not is_gen else 0.0
        P_mec_out = float(abs(Te_ss) * abs(wm_ss))

        if is_gen:
            eta = P_elec / max(P_mec_out, 1e-9) * 100 if P_mec_out > 0 else 0.0
        else:
            eta = P_mec_out / max(P_elec, 1e-9) * 100 if P_elec > 0 else 0.0

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Efficiency η (%)",         f"{eta:.1f}")
        a2.metric("Joule Loss $R_a$ (W)",     f"{P_Ra:.3f}")
        a3.metric("Joule Loss $R_f$ (W)",     f"{P_Rf:.3f}")
        a4.metric("Friction Loss (W)",        f"{P_mec:.4f}")

        b1, b2 = st.columns(2)
        b1.metric("Electrical Power (W)",     f"{P_elec:.3f}")
        b2.metric("Mechanical Power (W)",     f"{P_mec_out:.3f}")

        Te_nom = mp.Tload if mp else 2.493
        util   = abs(Te_ss) / max(abs(Te_nom), 1e-9) * 100
        st.metric("Utilization Factor (%)",   f"{util:.1f}")

        # Simplified Sankey
        with st.expander("Sankey Diagram (Power Flow)", expanded=False):
            try:
                if not is_gen and P_elec > 0:
                    labels = ["Electrical Power", "Mechanical Power", "Joule Loss Ra", "Joule Loss Rf", "Friction Loss"]
                    source = [0, 0, 0, 0]
                    target = [1, 2, 3, 4]
                    value  = [max(P_mec_out, 0), max(P_Ra, 0), max(P_Rf, 0), max(P_mec, 0)]
                    fig_s  = go.Figure(go.Sankey(
                        node=dict(label=labels, pad=15, thickness=20),
                        link=dict(source=source, target=target, value=value),
                    ))
                    fig_s.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_s, use_container_width=True, config=_PLOT_CFG, key="dc-sankey")
                else:
                    st.caption("Sankey available only in motor mode.")
            except Exception:
                st.caption("Sankey unavailable.")

        # Economic analysis (same as MIT)
        if energy_tariff > 0 and P_elec > 1e-3 and not is_gen:
            with st.expander("Consumption Details", expanded=False):
                try:
                    _t_arr   = res["t"]
                    _ia_arr  = res["ia"]
                    _P_elec_arr = np.abs(Va) * np.abs(_ia_arr)
                    _dt      = float(_t_arr[1] - _t_arr[0]) if len(_t_arr) > 1 else h
                    _E_kWh   = float(np.sum(_P_elec_arr) * _dt / 3600)
                    _custo_exp  = _E_kWh * energy_tariff
                    _tmax_sim   = float(_t_arr[-1])
                    _E_anual    = _E_kWh * (8760 * 3600 / max(_tmax_sim, 1e-6))
                    _custo_ano  = _E_anual * energy_tariff

                    ec1, ec2 = st.columns(2)
                    ec1.metric("Energy in experiment (kWh)",     f"{_E_kWh:.6f}")
                    ec2.metric("Experiment cost ($)",            f"{_custo_exp:.6f}")
                    ec3, ec4 = st.columns(2)
                    ec3.metric("Projected annual energy (kWh/yr)", f"{_E_anual:,.1f}")
                    ec4.metric("Projected annual cost ($/yr)",     f"{_custo_ano:,.2f}")
                    st.caption(
                        f"Tariff: $ {energy_tariff:.4f}/kWh. "
                        f"Projection assumes continuous operation (8,760 h/year) with the same load profile."
                    )
                except Exception:
                    st.caption("Economic analysis unavailable.")

    # ══════════════════════════════════════════════════════════════════════
    # PDF EXPORT
    # ══════════════════════════════════════════════════════════════════════
    from viz.pdf_dc import generate_dc  # noqa: E402

    st.markdown("---")
    st.markdown('<p class="slabel">Export Report</p>', unsafe_allow_html=True)

    if not st.session_state.get("pdf_bytes_dc"):
        if st.button("DC Machine Report (PDF)", key="btn_pdf_dc"):
            with st.spinner("Generating DC machine report..."):
                st.session_state["pdf_bytes_dc"] = generate_dc(
                    exp_label=exp_label,
                    mp=mp,
                    res=res,
                    var_keys=var_keys,
                    var_labels=var_labels,
                    t_events=t_events,
                    exp_type=exp_type,
                    tmax=tmax,
                    h=h,
                    exp_config=st.session_state.get("sim_result", {}).get("exp_config"),
                    input_mode=st.session_state.get("wi_dc_input_mode"),
                    ref_list=ref_list,
                )
            st.rerun()
    else:
        st.download_button(
            label="Download DC Machine Report (PDF)",
            data=st.session_state["pdf_bytes_dc"],
            file_name="report_iws_dcm.pdf",
            mime="application/pdf",
            key="btn_pdf_dc_download",
        )
        if st.button("Regenerate DCM", key="btn_pdf_dc_regen"):
            del st.session_state["pdf_bytes_dc"]
            st.rerun()

    if st.session_state.get("pdf_bytes_dc") and not st.session_state.get("pdf_bytes"):
        st.session_state["pdf_bytes"] = st.session_state["pdf_bytes_dc"]
