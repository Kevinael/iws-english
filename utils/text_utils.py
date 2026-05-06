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
    """Converte notação LaTeX $...$ para texto simples (uso em labels do Plotly)."""
    def _convert(m: re.Match) -> str:
        inner = m.group(1)
        for cmd, uni in _GREEK.items():
            inner = inner.replace(cmd, uni)
        return inner.replace('{', '').replace('}', '').replace('_', '').replace('\\', '')
    return _LATEX_RE.sub(_convert, s)
