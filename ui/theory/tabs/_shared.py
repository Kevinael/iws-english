# -*- coding: utf-8 -*-
"""
ui/theory/tabs/_shared.py
=========================
Shared helpers used by all Theory tab modules.
"""

from __future__ import annotations
import base64
import io
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams.update({"mathtext.fontset": "dejavusans", "text.usetex": False})
import matplotlib.pyplot as plt
import streamlit as st


# ── image helpers ─────────────────────────────────────────────────────────────

def _b64(fname: str) -> str:
    # tabs/ → theory/ → ui/ → project root
    root = Path(__file__).parent.parent.parent.parent
    for base in (root, root / "ui"):
        p = base / fname
        if p.exists():
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""


def _show_img(fname: str, width: str = "100%") -> None:
    b64 = _b64(fname)
    if not b64:
        st.caption(f"[{fname} not found]")
        return
    st.markdown(
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:{width};max-width:100%;display:block;'
        f'border-radius:6px;margin:.4rem auto;">',
        unsafe_allow_html=True,
    )


def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── equivalent-circuit helpers ────────────────────────────────────────────────

def _z2(R2: float, s: float, X2: float) -> complex:
    """Rotor branch impedance Z2 = (R2/s) + jX2."""
    return (R2 / s) + 1j * X2


# ── reference motor parameters for T×s curves ────────────────────────────────

_V1_REF, _f_REF, _p_REF = 220, 60, 4
_R1_REF, _X1_REF        = 0.50, 1.00
_R2_REF, _X2_REF        = 0.40, 1.00
_Xm_REF                 = 50.0
_ns_REF                 = 120 * _f_REF / _p_REF   # 1800 RPM


def _torque_ref(s: float) -> float:
    """Torque (N·m) for the reference motor used in the Theory tab."""
    if abs(s) < 1e-4:
        s = 1e-4
    Z2  = _R2_REF / s + 1j * _X2_REF
    Zeq = (1j * _Xm_REF * Z2) / (1j * _Xm_REF + Z2)
    Zt  = _R1_REF + 1j * _X1_REF + Zeq
    I1  = _V1_REF / Zt
    I2  = (I1 * Zeq) / Z2
    return 3 * abs(I2) ** 2 * (_R2_REF / s) / (2 * np.pi * _ns_REF / 60)


# ── rendering helpers ────────────────────────────────────────────────────────

def _h4(title: str) -> None:
    st.markdown(f"#### {title}")


def _eq(latex: str) -> None:
    st.markdown(f"$$\n{latex}\n$$")


def _p(text: str) -> None:
    st.markdown(text)


def _div_warn(text: str) -> None:
    st.warning(text)
