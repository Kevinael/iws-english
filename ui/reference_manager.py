# -*- coding: utf-8 -*-
"""
reference_manager.py
====================
Helpers for saving and clearing reference simulation overlays.

Responsibilities:
  - Append a simulation result to the reference list with a color/dash assignment.

Relationships:
  Imported by : IWS_UI
  Imports     : ui.theme, streamlit
"""

from __future__ import annotations

import streamlit as st

from ui.theme import REF_COLORS, REF_DASHES


def save_reference(sim_result: dict) -> None:
    """Append sim_result to ref_list with the next available color and dash style."""
    ref_list = st.session_state["ref_list"]
    new_ref = dict(sim_result)
    idx = len(ref_list)
    new_ref["color"] = REF_COLORS[idx % len(REF_COLORS)]
    new_ref["dash"]  = REF_DASHES[idx % len(REF_DASHES)]
    ref_list.append(new_ref)
    st.rerun()
