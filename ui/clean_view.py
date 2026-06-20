# -*- coding: utf-8 -*-
"""
clean_view.py
=============
Renders clean HTML parameter tables for article screenshots — reads from session_state after a completed simulation.

Responsibilities:
  - Format machine parameters as an HTML table with styled rows and sections.
  - Render the clean view panel via render_clean_view().
  - Depend on sim_result being present in session_state before rendering.

Relationships:
  Imported by : IWS_UI
  Imports     : streamlit

Extending:
  - To add a new section, create a _section() call and append rows with _row().
"""
from __future__ import annotations
import streamlit as st


# ── formatting helpers ───────────────────────────────────────────────────────

def _row(name: str, symbol: str, value: str, unit: str = "", shade: bool = False) -> str:
    bg = "#f7f7f7" if shade else "#ffffff"
    sym = f'<span style="font-style:italic;">{symbol}</span>' if symbol else ""
    return (
        f'<tr style="background:{bg};">'
        f'  <td style="padding:7px 14px;border:1px solid #d0d0d0;">{name}</td>'
        f'  <td style="padding:7px 14px;border:1px solid #d0d0d0;text-align:center;width:60px;">{sym}</td>'
        f'  <td style="padding:7px 14px;border:1px solid #d0d0d0;text-align:right;width:110px;'
        f'      font-family:monospace;font-size:14px;">{value}</td>'
        f'  <td style="padding:7px 14px;border:1px solid #d0d0d0;width:50px;color:#555;">{unit}</td>'
        f'</tr>'
    )


def _section(title: str) -> str:
    return (
        f'<tr>'
        f'  <td colspan="4" style="padding:9px 14px;background:#1e293b;color:#ffffff;'
        f'      font-weight:600;font-size:13px;letter-spacing:0.06em;'
        f'      border:1px solid #1e293b;text-transform:uppercase;">'
        f'      {title}'
        f'  </td>'
        f'</tr>'
    )


def _fmt(v, decimals: int = 3) -> str:
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


# ── experiment → parameter rows ──────────────────────────────────────────────

def _exp_rows(cfg: dict) -> list[str]:
    rows = []
    et = cfg.get("exp_type", "dol")
    labels = {
        "dol":        "Direct-On-Line (DOL)",
        "yd":         "Star-Delta (Y-D)",
        "comp":       "Autotransformer",
        "soft":       "Soft-Starter (Voltage Ramp)",
        "load_pulse":"Load Pulse",
        "generator":    "Generator Operation",
    }
    rows.append(_row("Experiment type", "", labels.get(et, et), "", shade=False))

    if et in ("dol", "yd", "comp", "soft"):
        rows.append(_row("Load torque", "T<sub>L</sub>",
                         _fmt(cfg.get("Tl_final", 0.0), 2), "N·m", shade=True))
        _tc = cfg.get("t_load", 0.0)
        if _tc > 0:
            rows.append(_row("Load application instant", "t<sub>c</sub>",
                             _fmt(_tc, 3), "s", shade=False))

    if et in ("yd", "comp", "soft", "generator"):
        rows.append(_row("Switching / application instant", "t<sub>2</sub>",
                         _fmt(cfg.get("t_2", 0.0), 3), "s", shade=True))

    if et in ("comp", "soft"):
        vr = cfg.get("voltage_ratio", 1.0)
        rows.append(_row("Initial voltage (tap / ramp)", "V<sub>i</sub>",
                         f"{vr*100:.0f}", "%", shade=False))

    if et == "soft":
        rows.append(_row("Time to rated voltage", "t<sub>p</sub>",
                         _fmt(cfg.get("t_peak", 0.0), 2), "s", shade=True))

    if et == "load_pulse":
        rows.append(_row("Pulse torque", "T<sub>L</sub>",
                         _fmt(cfg.get("Tl_final", 0.0), 2), "N·m", shade=True))
        rows.append(_row("Pulse start", "t<sub>on</sub>",
                         _fmt(cfg.get("t_load", 0.0), 3), "s", shade=False))
        rows.append(_row("Pulse end", "t<sub>off</sub>",
                         _fmt(cfg.get("t_removal", 0.0), 3), "s", shade=True))

    if et == "generator":
        rows.append(_row("Mechanical torque (prime mover)", "T<sub>mec</sub>",
                         _fmt(cfg.get("Tl_mec", 0.0), 2), "N·m", shade=False))

    return rows


# ── main renderer ────────────────────────────────────────────────────────────

def render_clean_view() -> None:
    sr  = st.session_state.get("sim_result")
    if sr is None:
        st.info("Run a simulation first to view the parameters.")
        return

    mp       = sr.get("mp")
    if mp is None:
        st.warning("Incomplete simulation result — machine parameters missing.")
        return
    exp_cfg  = sr.get("exp_config", {})
    tmax     = sr.get("tmax", 0.0)
    h        = sr.get("h", 0.0)

    # ── magnetic parameter input mode ────────────────────────────────────
    im = getattr(mp, "input_mode", "X")
    if im == "L":
        mag_rows = [
            _row("Magnetizing inductance",        "L<sub>m</sub>",   f"{mp.Lm*1000:.4f}",  "mH",  shade=False),
            _row("Stator leakage inductance",     "L<sub>ls</sub>",  f"{mp.Lls*1000:.4f}", "mH",  shade=True),
            _row("Rotor leakage inductance",      "L<sub>lr</sub>",  f"{mp.Llr*1000:.4f}", "mH",  shade=False),
        ]
    else:
        f_ref = getattr(mp, "f_ref", 60.0)
        mag_rows = [
            _row(f"Magnetizing reactance (at {f_ref:.0f} Hz)",       "X<sub>m</sub>",   f"{mp.Xm:.4f}",  "Ω",  shade=False),
            _row(f"Stator leakage reactance (at {f_ref:.0f} Hz)",    "X<sub>ls</sub>",  f"{mp.Xls:.4f}", "Ω",  shade=True),
            _row(f"Rotor leakage reactance (at {f_ref:.0f} Hz)",     "X<sub>lr</sub>",  f"{mp.Xlr:.4f}", "Ω",  shade=False),
        ]

    # ── derived data summary ──────────────────────────────────────────────
    ns = mp.n_sync

    # ── assemble rows ─────────────────────────────────────────────────────
    elec_rows = [
        _row("Line voltage (RMS)",            "V<sub>l</sub>",  f"{mp.Vl:.1f}",   "V",   shade=False),
        _row("Supply frequency",              "f",              f"{mp.f:.1f}",    "Hz",  shade=True),
        _row("Stator resistance",             "R<sub>s</sub>",  f"{mp.Rs:.4f}",   "Ω",   shade=False),
        _row("Rotor resistance",              "R<sub>r</sub>",  f"{mp.Rr:.4f}",   "Ω",   shade=True),
        *mag_rows,
        _row("Core loss resistance",          "R<sub>fe</sub>", f"{mp.Rfe:.1f}",  "Ω",   shade=True),
    ]
    mec_rows = [
        _row("Number of poles",               "p",              str(mp.p),                   "",      shade=False),
        _row("Moment of inertia",             "J",              f"{mp.J:.4f}",               "kg·m²", shade=True),
        _row("Viscous friction coefficient",  "B",              f"{mp.B:.4f}",               "N·m·s", shade=False),
        _row("Synchronous speed",             "n<sub>s</sub>",  f"{ns:.1f}",                 "RPM",   shade=True),
    ]
    exp_rows = _exp_rows(exp_cfg)
    num_rows = [
        _row("Total simulation time",         "t<sub>max</sub>",f"{tmax:.3f}",    "s",   shade=False),
        _row("Integration step",              "h",              f"{h:.6f}",       "s",   shade=True),
    ]

    all_rows = (
        [_section("Electrical Parameters")]      + elec_rows +
        [_section("Mechanical Parameters")]      + mec_rows  +
        [_section("Experiment Configuration")]   + exp_rows  +
        [_section("Numerical Parameters")]       + num_rows
    )

    table_body = "\n".join(all_rows)

    html = f"""
<div style="
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #111111;
    background: #ffffff;
    padding: 28px 32px;
    max-width: 720px;
    margin: 0 auto;
">
  <div style="border-bottom:2px solid #1e293b;padding-bottom:10px;margin-bottom:18px;">
    <div style="font-size:18px;font-weight:700;letter-spacing:0.02em;color:#1e293b;">
      Web Simulation Infrastructure
    </div>
    <div style="font-size:13px;color:#555;margin-top:4px;">
      Configuration parameters
    </div>
  </div>

  <table style="
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      line-height: 1.5;
  ">
    <colgroup>
      <col style="width:46%">
      <col style="width:12%">
      <col style="width:22%">
      <col style="width:10%">
    </colgroup>
    <thead>
      <tr style="background:#f0f0f0;">
        <th style="padding:7px 14px;border:1px solid #d0d0d0;text-align:left;font-weight:600;">
          Parameter
        </th>
        <th style="padding:7px 14px;border:1px solid #d0d0d0;text-align:center;font-weight:600;">
          Symbol
        </th>
        <th style="padding:7px 14px;border:1px solid #d0d0d0;text-align:right;font-weight:600;">
          Value
        </th>
        <th style="padding:7px 14px;border:1px solid #d0d0d0;font-weight:600;">
          Unit
        </th>
      </tr>
    </thead>
    <tbody>
      {table_body}
    </tbody>
  </table>
</div>
"""
    st.html(html)
