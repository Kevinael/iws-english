# -*- coding: utf-8 -*-
"""
exp_renderers_tim.py
====================
MIT experiment sub-renderers — one function per experiment type.

Each function signature:
    _render_exp_*(mp, config, _Tl_ref, wk) -> None | float

The dispatch table and public entry point live in tim_config.py.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from core.tim.facade import MachineParams
from ui_components._shared_widgets import _ibox


def _render_exp_dol(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    partir_em_vazio = st.checkbox(
        "Start unloaded (apply load after starting)",
        value=True,
        key="wi_dol_partir_vazio",
        help="When active, the motor starts unloaded and receives torque at t_carga. "
             "When inactive, the load is present from time zero.",
    )
    config["partir_em_vazio"] = partir_em_vazio

    if partir_em_vazio:
        Tl_nom = st.number_input("Rated reference torque — $T_{nom}$ (N·m)", value=_Tl_ref, min_value=0.0001, key=wk.Tl_nom_dol)
        pct_fin = st.number_input(
            "Applied load (%)", value=100.0,
            help="Load torque as a percentage of T_nom. Applied at t_carga.",
            key="wi_dol_pct_fin",
        )
        config["Tl_inicial"] = 0.0
        config["Tl_final"]   = Tl_nom * pct_fin / 100.0
        config["t_carga"]    = st.number_input("Load application instant — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk.t_carga)
        _ibox(
            f"<strong>t = 0 s</strong> — rated voltage ({mp.Vl:.0f} V) applied; motor accelerates unloaded (T<sub>l</sub> = 0).<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — load of "
            f"<strong>{config['Tl_final']:.2f} N·m</strong> ({pct_fin:.1f}% of T<sub>nom</sub>) applied to shaft; "
            f"motor settles to new steady-state operating point."
        )
    else:
        config["Tl_inicial"] = None
        config["Tl_final"]   = st.number_input("Load torque — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk.Tl_final)
        config["t_carga"]    = 0.0
        _ibox(
            f"<strong>t = 0 s</strong> — rated voltage ({mp.Vl:.0f} V) and load of "
            f"<strong>{config['Tl_final']:.2f} N·m</strong> applied simultaneously; "
            f"motor starts against full load and accelerates to steady state."
        )


def _render_exp_yd(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    config["Tl_final"] = st.number_input("Load torque — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk.Tl_final)
    config["t_2"]      = st.number_input("Y → D switching instant — $t_2$ (s)", value=0.5, min_value=0.0001, key="wi_yd_t2")
    config["t_carga"]  = st.number_input("Load application instant — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk.t_carga)
    _ibox(
        f"<strong>t = 0 s</strong> — motor starts in star (Y) with reduced voltage of "
        f"{mp.Vl/np.sqrt(3):.1f} V ({100/np.sqrt(3):.0f}% of V<sub>l</sub>); starting current and torque reduced to ≈ 1/3.<br>"
        f"<strong>t = {config['t_2']:.2f} s</strong> — Y → Δ switching: voltage rises to {mp.Vl:.0f} V; "
        f"re-starting current transient.<br>"
        f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied to shaft."
    )
    from ui_components.tim_config_params import _aviso_partida_reduzida
    _aviso_partida_reduzida(mp, 1.0 / np.sqrt(3.0), config["Tl_final"])


def _render_exp_comp(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    config["Tl_final"]      = st.number_input("Load torque — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk.Tl_final)
    config["voltage_ratio"] = st.slider("Autotransformer tap — $k$ (%)", 10, 95, 50, key="wi_comp_tap") / 100.0
    config["t_2"]           = st.number_input("Switching instant — $t_2$ (s)", value=0.5, min_value=0.0001, key="wi_comp_t2")
    config["t_carga"]       = st.number_input("Load application instant — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk.t_carga)
    _ibox(
        f"<strong>t = 0 s</strong> — motor starts with reduced voltage of "
        f"{config['voltage_ratio']*100:.0f}% of V<sub>l</sub> "
        f"({mp.Vl * config['voltage_ratio']:.1f} V); starting torque reduced to "
        f"{config['voltage_ratio']**2 * 100:.0f}% of full-voltage value.<br>"
        f"<strong>t = {config['t_2']:.2f} s</strong> — switching: autotransformer disconnected, "
        f"rated voltage {mp.Vl:.0f} V applied directly; re-starting current transient.<br>"
        f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied to shaft."
    )
    from ui_components.tim_config_params import _aviso_partida_reduzida
    _aviso_partida_reduzida(mp, config["voltage_ratio"], config["Tl_final"])


def _render_exp_soft(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    config["voltage_ratio"] = st.slider("Soft-Starter initial voltage — $V_0$ (%)", 10, 90, 50, key="wi_soft_v0") / 100.0
    config["t_2"]           = st.number_input("Voltage ramp start — $t_2$ (s)", value=0.0, min_value=0.0, key="wi_soft_t2")
    config["t_pico"]        = st.number_input("Time to reach rated voltage — $t_{peak}$ (s)", value=5.0, min_value=0.0001, key="wi_soft_t_pico")
    config["Tl_final"]      = st.number_input("Load torque — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk.Tl_final)
    config["t_carga"]       = st.number_input("Load application instant — $t_{carga}$ (s)", value=1.0, min_value=0.0, key=wk.t_carga)
    _ibox(
        f"<strong>t = 0 s</strong> — motor starts with initial voltage of "
        f"{config['voltage_ratio']*100:.0f}% of V<sub>l</sub> "
        f"({mp.Vl * config['voltage_ratio']:.1f} V); starting current and torque limited.<br>"
        f"<strong>t = {config['t_2']:.2f} s</strong> — voltage ramp started: voltage rises linearly to {mp.Vl:.0f} V.<br>"
        f"<strong>t = {config['t_pico']:.2f} s</strong> — rated voltage reached; Soft-Starter disconnected, "
        f"motor in direct operation (ramp duration: {config['t_pico'] - config['t_2']:.2f} s).<br>"
        f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied to shaft."
    )
    from ui_components.tim_config_params import _aviso_partida_reduzida
    _aviso_partida_reduzida(mp, config["voltage_ratio"], config["Tl_final"])


def _render_exp_pulso_carga(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    Tl_base = st.number_input("Base torque — $T_{base}$ (N·m)", value=_Tl_ref * 0.5, min_value=0.0, key=wk.Tl_pulso)
    st.caption("Load present on the shaft before and after the pulse. Use 0 for unloaded starting.")
    if Tl_base == 0.0:
        Tl_pulso = st.number_input("Torque during pulse — $T_{pulse}$ (N·m)", value=_Tl_ref, min_value=0.0001, key=wk.Tl_pulso_abs)
        st.caption("Torque applied in the interval $[t_{on},\\, t_{off})$. Outside this interval the motor runs unloaded.")
        pct = 0.0
    else:
        pct      = st.number_input("Variation during pulse (%)", value=50.0, key="wi_pct_pulso")
        st.caption("Percentage of $T_{base}$ added (positive) or subtracted (negative) during the pulse.")
        Tl_pulso = Tl_base * (1.0 + pct / 100.0)
    config["Tl_base"]  = Tl_base
    config["Tl_final"] = Tl_pulso
    t_on  = st.number_input("Pulse application instant — $t_{on}$ (s)",  value=1.0, min_value=0.0, step=0.1, format="%.2f", key=wk.t_pulso_on)
    t_off = st.number_input("Pulse removal instant — $t_{off}$ (s)",     value=1.5, min_value=0.0, step=0.1, format="%.2f", key=wk.t_pulso_off)
    config["t_carga"]    = t_on
    config["t_retirada"] = t_off
    if t_off <= t_on:
        st.error(f"t_off ({t_off:.2f} s) must be greater than t_on ({t_on:.2f} s).")
        config["_invalid"] = True
    else:
        duracao = t_off - t_on
        if Tl_base == 0.0:
            _ibox(
                f"<strong>t = 0 s</strong> — motor starts unloaded (T<sub>l</sub> = 0) at rated voltage {mp.Vl:.0f} V.<br>"
                f"<strong>t = {t_on:.2f} s</strong> — load pulse of <strong>{Tl_pulso:.2f} N·m</strong> applied; motor decelerates.<br>"
                f"<strong>t = {t_off:.2f} s</strong> — pulse removed (duration: {duracao:.2f} s); motor returns to no-load and recovers synchronous speed."
            )
        else:
            delta = Tl_pulso - Tl_base
            sinal = "increase" if delta >= 0 else "reduction"
            _ibox(
                f"<strong>t = 0 s</strong> — motor starts with base load of <strong>{Tl_base:.2f} N·m</strong> at rated voltage {mp.Vl:.0f} V.<br>"
                f"<strong>t = {t_on:.2f} s</strong> — {sinal} to <strong>{Tl_pulso:.2f} N·m</strong> "
                f"({pct:+.1f}% of T<sub>base</sub>); speed and torque transient.<br>"
                f"<strong>t = {t_off:.2f} s</strong> — return to base {Tl_base:.2f} N·m (pulse duration: {duracao:.2f} s)."
            )


def _render_exp_gerador(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    config["Tl_mec"] = st.number_input("Prime mover torque — $T_{mec}$ (N·m)", value=_Tl_ref, min_value=1.0, key=wk.Tl_mec)
    config["t_2"]    = st.number_input("Torque application instant — $t_2$ (s)", value=1.0, min_value=0.0, key=wk.t_2_gerador)
    _ibox(
        f"<strong>t = 0 s</strong> — machine connected to the grid ({mp.Vl:.0f} V) and accelerated by inertia to near synchronous speed.<br>"
        f"<strong>t = {config['t_2']:.2f} s</strong> — mechanical torque of <strong>{config['Tl_mec']:.2f} N·m</strong> applied by prime mover; "
        f"rotor exceeds synchronous speed (s &lt; 0) and the machine begins injecting active power into the grid."
    )


def _render_exp_shutdown(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    config["Tl_final"]  = st.number_input("Load torque — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk.Tl_final)
    config["t_carga"]   = st.number_input("Load application instant — $t_{carga}$ (s)", value=0.3, min_value=0.0, key=wk.t_carga)
    config["t_cutoff"]  = st.number_input("Shutdown instant — $t_{off}$ (s)", value=1.5, min_value=0.0001, key="wi_sd_t_cutoff")
    if config["t_carga"] >= config["t_cutoff"]:
        st.error(f"t_carga ({config['t_carga']:.2f} s) must be less than t_off ({config['t_cutoff']:.2f} s). Apply load before shutdown.")
        config["_invalid"] = True
    _ws    = 2.0 * np.pi * mp.f / (mp.p / 2)
    _Tl_sd = config["Tl_final"]
    _B_sd  = mp.B
    _J_sd  = mp.J
    if _B_sd > 0 and _Tl_sd > 0:
        _t_stop_mec = (_J_sd / _B_sd) * np.log(1.0 + _B_sd * _ws / _Tl_sd)
    elif _Tl_sd > 0:
        _t_stop_mec = _J_sd * _ws / _Tl_sd
    else:
        _tau_m_fb   = _J_sd / _B_sd if _B_sd > 0 else 10.0
        _t_stop_mec = 5.0 * _tau_m_fb
    _t_end_sd = config["t_cutoff"] + _t_stop_mec * 1.2
    config["_t_end_shutdown"] = float(_t_end_sd)
    _ibox(
        f"<strong>t = 0 s</strong> — motor starts at rated voltage {mp.Vl:.0f} V and accelerates unloaded.<br>"
        f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied; motor settles in steady state.<br>"
        f"<strong>t = {config['t_cutoff']:.2f} s</strong> — voltage cut (contactor opening); electromagnetic torque decays in milliseconds.<br>"
        f"<strong>Post-cutoff</strong> — mechanical load brakes the rotor to complete stop "
        f"(t<sub>stop</sub> ≈ {_t_stop_mec:.2f} s, calculated by J/B·ln(1 + B·ω₀/T<sub>L</sub>)).<br>"
        f"<strong>Automatic t<sub>end</sub>: {_t_end_sd:.2f} s</strong> (t<sub>off</sub> + t<sub>stop</sub> × 1.2)."
    )


def _render_exp_voltage_sag(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> None:
    sg1, sg2 = st.columns(2)
    with sg1:
        sag_mag = st.slider(
            "Voltage during sag — $V_{sag}$ (% of $V_l$)",
            min_value=5, max_value=95, value=50, step=5,
            key=wk.sag_magnitude,
            help="Percentage of rated voltage during the sag. 50% = 0.5 pu sag.",
        ) / 100.0
    with sg2:
        config["Tl_final"] = st.number_input(
            "Load torque — $T_l$ (N·m)",
            value=_Tl_ref, min_value=0.0,
            key=wk.sag_Tl,
            help="Mechanical load applied from the beginning of the simulation.",
        )
        config["t_carga"] = 0.0
    t_start_sag    = st.number_input("Sag start — $t_{sag}$ (s)",            value=0.5, min_value=0.0, step=0.05, format="%.3f", key=wk.t_start_sag)
    t_duration_sag = st.number_input("Sag duration — $\\Delta t_{sag}$ (s)", value=0.1, min_value=0.0001, max_value=5.0, step=0.01, format="%.3f", key=wk.t_duration_sag)
    t_end_sag = t_start_sag + t_duration_sag
    config["sag_magnitude"]  = sag_mag
    config["t_start_sag"]    = t_start_sag
    config["t_duration_sag"] = t_duration_sag
    _Vsag_line = mp.Vl * sag_mag
    _ibox(
        f"<strong>t = 0 s</strong> — motor starts at rated voltage {mp.Vl:.1f} V with load of "
        f"<strong>{config['Tl_final']:.2f} N·m</strong>; reaches steady state before the sag.<br>"
        f"<strong>t = {t_start_sag:.3f} s</strong> — voltage sag: "
        f"{mp.Vl:.1f} V → <strong>{_Vsag_line:.1f} V ({sag_mag*100:.0f}%)</strong>; "
        f"electromagnetic torque reduced, rotor decelerates.<br>"
        f"<strong>t = {t_end_sag:.3f} s</strong> — voltage restored ({t_duration_sag*1000:.0f} ms duration); "
        f"re-acceleration transient with current peak — main event of interest."
    )
    if t_duration_sag < 0.02:
        st.warning("Duration < 20 ms — sub-transient sag; reduce step $h$ to capture the transient.")
    if sag_mag <= 0.1:
        st.warning("Deep sag (≤ 10%) — the motor may decelerate significantly and the re-starting current may exceed the locked-rotor current.")


def _render_exp_frenagem(
    mp: MachineParams,
    config: dict[str, Any],
    _Tl_ref: float,
    wk: Any,
) -> float:
    """Returns h_def (braking needs smaller default step than other modes)."""
    _BRAKE_LABELS_MIT: dict[str, str] = {
        "plugging":    "Plugging (Polarity Reversal)",
        "injecao_cc":  "DC Injection Braking",
        "regenerativo":"Regenerative Braking",
    }
    brake_labels = list(_BRAKE_LABELS_MIT.values())
    brake_keys   = list(_BRAKE_LABELS_MIT.keys())
    _wi_brake_key = "wi_brake_method"
    if _wi_brake_key not in st.session_state:
        st.session_state[_wi_brake_key] = brake_labels[0]
    brake_sel = st.selectbox(
        "Braking Method", brake_labels,
        index=brake_labels.index(st.session_state.get(_wi_brake_key, brake_labels[0])),
        key=_wi_brake_key,
    )
    brake = brake_keys[brake_labels.index(brake_sel)]
    config["brake_method"] = brake

    _BRAKE_DESC_MIT = {
        "plugging":    "Reverses the polarity of the supply voltage while the motor is still rotating. "
                       "Produces torque opposing motion — very fast braking, but with high "
                       "current and possible direction reversal if no stopping switch is provided.",
        "injecao_cc":  "Cuts the AC supply and injects DC voltage into the stator. The fixed magnetic field "
                       "induces rotor currents that produce braking torque without reversing direction. "
                       "Smooth and controlled braking, no reversal risk.",
        "regenerativo":"Reduces the supply voltage below the motor back-EMF. Current reverses — "
                       "the motor operates as a generator, returning energy to the grid. Gentler braking; "
                       "effective only for high-inertia or high-speed loads.",
    }
    st.info(_BRAKE_DESC_MIT[brake])

    config["Tl_final"] = st.number_input(
        "Load torque — $T_l$ (N·m)", value=_Tl_ref, min_value=0.0, key=wk.Tl_final,
    )
    config["t_carga"] = st.number_input(
        "Load application instant — $t_{carga}$ (s)", value=0.3, min_value=0.0, key=wk.t_carga,
    )
    config["t_brake"] = st.number_input(
        "Braking instant — $t_{brake}$ (s)", value=1.5, min_value=0.001, key="wi_brake_t_freia",
    )

    if brake == "plugging":
        _ibox(
            f"<strong>t = 0 s</strong> — motor starts at rated voltage {mp.Vl:.0f} V.<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied.<br>"
            f"<strong>t = {config['t_brake']:.2f} s</strong> — voltage polarity reversed; "
            f"braking torque opposes motion — rotor decelerates and may reverse direction."
        )

    elif brake == "injecao_cc":
        config["Vcc_inj"] = st.number_input(
            "Injected DC voltage — $V_{inj}$ (V)", value=float(mp.Vl * 0.1),
            min_value=0.0, key="wi_brake_Vcc_inj",
            help="DC voltage applied to the stator after AC supply is cut. Typically 5–15% of Vl.",
        )
        _ibox(
            f"<strong>t = 0 s</strong> — motor starts at rated voltage {mp.Vl:.0f} V.<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied.<br>"
            f"<strong>t = {config['t_brake']:.2f} s</strong> — AC supply cut; "
            f"DC voltage of <strong>{config['Vcc_inj']:.1f} V</strong> injected into stator; "
            f"fixed field produces torque opposing motion — braking without reversal."
        )

    elif brake == "regenerativo":
        config["V_regen"] = st.number_input(
            "Reduced voltage — $V_{regen}$ (% of $V_l$)",
            value=50, min_value=5, max_value=95, key="wi_brake_V_regen",
            help="Voltage below back-EMF — motor operates as generator returning energy to the grid.",
        )
        _Vregen_v = mp.Vl * config["V_regen"] / 100.0
        _ibox(
            f"<strong>t = 0 s</strong> — motor starts at rated voltage {mp.Vl:.0f} V.<br>"
            f"<strong>t = {config['t_carga']:.2f} s</strong> — load of <strong>{config['Tl_final']:.2f} N·m</strong> applied.<br>"
            f"<strong>t = {config['t_brake']:.2f} s</strong> — voltage reduced to "
            f"<strong>{_Vregen_v:.1f} V ({config['V_regen']}%)</strong>; "
            f"back-EMF exceeds applied voltage — current reverses; motor operates as generator."
        )

    return 5e-4
