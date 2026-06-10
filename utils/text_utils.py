# -*- coding: utf-8 -*-
"""
text_utils.py
=============
Converts LaTeX inline notation to Unicode plain text — used to strip math
symbols from axis labels and UI strings.

Responsibilities:
  - Map LaTeX commands to Greek Unicode symbols via the _GREEK dict.
  - Strip $...$ delimiters and replace commands via _strip_latex(s).

Relationships:
  Imported by : core.harmonica_analysis, ui_components.sim_results
  Imports     : (re only)

Extending:
  - To support additional LaTeX commands, add entries to the _GREEK dict.
"""
from __future__ import annotations
import re

_GREEK: dict[str, str] = {
    '\\omega': 'ω', '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ',
    '\\delta': 'δ', '\\theta': 'θ', '\\tau': 'τ', '\\phi': 'φ',
    '\\psi': 'ψ', '\\lambda': 'λ', '\\mu': 'μ', '\\sigma': 'σ',
    '\\pi': 'π', '\\eta': 'η',
}

_LATEX_RE = re.compile(r'\$([^$]+)\$')


def _strip_latex(s: str) -> str:
    """Converts LaTeX $...$ notation to plain text (used in Plotly labels)."""
    def _convert(m: re.Match) -> str:
        inner = m.group(1)
        for cmd, uni in _GREEK.items():
            inner = inner.replace(cmd, uni)
        return inner.replace('{', '').replace('}', '').replace('_', '').replace('\\', '')
    return _LATEX_RE.sub(_convert, s)
