"""Renderizador de circuito equivalente MCC — exibe PNG por excitação.

Se o PNG não existir, exibe placeholder informativo.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_PNG_MAP: dict[str, str] = {
    "sep_motor":    "separate_motor.png",
    "sep_gen":      "separate_gerador.png",
    "shunt_motor":  "shunt_motor.png",
    "shunt_gen":    "shunt_gerador.png",
    "series_motor": "serie_motor.png",
}

_PNG_DIR = Path(__file__).parent.parent / "docs" / "bases para simulação" / "cc" / "imgs"

_CIRCUIT_LABELS: dict[str, str] = {
    "sep_motor":    "Excitação Separada — Motor",
    "sep_gen":      "Excitação Separada — Gerador",
    "shunt_motor":  "Shunt (Paralelo) — Motor",
    "shunt_gen":    "Shunt (Paralelo) — Gerador",
    "series_motor": "Série — Motor",
}


@st.cache_data(show_spinner=False)
def render_circuit_dc(excitation: str, dark: bool) -> None:
    """Exibe o circuito equivalente da configuração MCC selecionada."""
    png_name = _PNG_MAP.get(excitation, "separate_motor.png")
    png_path = _PNG_DIR / png_name

    label = _CIRCUIT_LABELS.get(excitation, excitation)

    if png_path.exists():
        st.image(str(png_path), caption=label, use_container_width=True)
    else:
        # Placeholder enquanto PNGs não foram gerados
        bg = "#1e2330" if dark else "#f8f9fa"
        fg = "#94a3b8" if dark else "#6b7280"
        st.markdown(
            f'<div style="background:{bg};border-radius:8px;padding:24px;text-align:center;'
            f'color:{fg};font-size:13px;font-family:Inter,system-ui;">'
            f'<div style="font-size:32px;margin-bottom:8px;">⚡</div>'
            f'<strong>{label}</strong><br>'
            f'<span style="font-size:11px;">Circuito equivalente<br>'
            f'(execute docs/bases para simulação/cc/mcc_desenhos.py para gerar PNGs)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
