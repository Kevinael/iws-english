# -*- coding: utf-8 -*-
"""
_shared_widgets.py
==================
Shared Streamlit rendering helpers used by both MIT and DC configuration panels.

Responsibilities:
  - _pgroup: render a section-header div with CSS class "pgroup-title"
  - _ibox  : render an info-box div with CSS class "ibox"

Relationships:
  Imported by : ui_components.tim_config, ui_components.sim_config_dc
  Imports     : streamlit
"""

from __future__ import annotations
import streamlit as st


def _pgroup(title: str) -> None:
    st.markdown(f'<div class="pgroup-title">{title}</div>', unsafe_allow_html=True)


def _ibox(html: str) -> None:
    st.markdown(f'<div class="ibox">{html}</div>', unsafe_allow_html=True)
