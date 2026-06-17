# -*- coding: utf-8 -*-
"""
_shared.py
==========
Shared helpers for ui.theory submodules — fallback machine parameters and
session-state accessors.

Responsibilities:
  - Provide _FallbackMP (Krause 3 HP defaults) and _MP_DEFAULT singleton.
  - Expose _get_mp() and _dark() for use by all theory submodules.

Relationships:
  Imported by : ui.theory.*
  Imports     : numpy, streamlit
"""

from __future__ import annotations

import numpy as np
import streamlit as st


class _FallbackMP:
    """Minimal subset of MachineParams for interactive components."""
    Vl    = 220.0          # phase voltage RMS (V)
    f     = 60.0           # frequency (Hz)
    Rs    = 0.435          # stator resistance (Ω)
    Rr    = 0.816          # rotor resistance (Ω)
    Xm    = 26.13          # magnetizing reactance (Ω)
    Xls   = 0.754          # stator leakage reactance (Ω)
    Xlr   = 0.754          # rotor leakage reactance (Ω)
    Rfe   = 500.0
    p     = 4              # number of poles
    J     = 0.089          # inertia (kg·m²)
    B     = 0.0

    @property
    def wb(self):
        return 2.0 * np.pi * self.f

    @property
    def Lm(self):
        return self.Xm / self.wb

    @property
    def Xls_a(self):
        return self.Xls

    @property
    def Xlr_a(self):
        return self.Xlr

    @property
    def n_sync(self):
        return 120.0 * self.f / self.p


_MP_DEFAULT = _FallbackMP()


def _get_mp():
    """Returns MachineParams from the last simulation or the fallback."""
    res = st.session_state.get("sim_result")
    if res and "mp" in res:
        return res["mp"]
    return _MP_DEFAULT


def _dark() -> bool:
    return bool(st.session_state.get("dark_mode", False))
