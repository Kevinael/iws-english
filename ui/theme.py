# -*- coding: utf-8 -*-
"""
theme.py
========
Defines the dark/light colour palette and applies global CSS styling to the Streamlit application.

Responsibilities:
  - Provide _palette(dark) returning a colour dict with surface, border, text, and accent keys.
  - Apply Streamlit-compatible CSS via apply_css(dark) for typography and component overrides.
  - Expose REF_COLORS and REF_DASHES constants for consistent chart theming across the project.

Relationships:
  Imported by : ui_components.sim_config, ui_components.sim_results, viz.pdf_commons,
                viz.pdf_report_v2, IWS_UI
  Imports     : streamlit

Extending:
  - To add a new theme variant, extend _palette with a new branch and update apply_css accordingly.
"""
import streamlit as st

REF_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
REF_DASHES = ["dash", "dot", "solid", "dash", "dot"]


def _palette(dark: bool) -> dict:
    if dark:
        return dict(
            bg="#0e0e0e", surface="#1a1a1a", surface2="#242424",
            border="#333333", accent="#ffffff", accent2="#ffffff",
            on_accent="#000000",
            text="#ffffff", muted="#b5b5b5",
            success="#22eb6c", danger="#ff4444", warning="#fd7e14",
            warn_bg="rgba(255,68,68,0.08)", input_bg="#111111",
            tag="#242424",
            # semantic: status
            info="#0dcaf0",
            # semantic: phases
            phase_a="#ef4444", phase_b="#22c55e", phase_c="#3b82f6",
            # semantic: energy flows (Sankey)
            energy_in="#3b82f6", energy_cu="#ef4444", energy_fe="#f59e0b",
            energy_fw="#a855f7", energy_mec="#22c55e", energy_out="#22c55e",
            # semantic: braking methods
            brake_plug="#ef4444", brake_dc="#3b82f6", brake_regen="#22c55e",
        )
    return dict(
        bg="#ffffff", surface="#ebebeb", surface2="#ebebeb",
        border="#d0d0d0", accent="#000000", accent2="#000000",
        on_accent="#ffffff",
        text="#000000", muted="#555555",
        success="#198754", danger="#dc3545", warning="#fd7e14",
        warn_bg="rgba(220,38,38,0.06)", input_bg="#ffffff",
        tag="#ffffff",
        # semantic: status
        info="#0d6efd",
        # semantic: phases
        phase_a="#dc3545", phase_b="#198754", phase_c="#0d6efd",
        # semantic: energy flows (Sankey)
        energy_in="#0d6efd", energy_cu="#dc3545", energy_fe="#fd7e14",
        energy_fw="#6f42c1", energy_mec="#198754", energy_out="#198754",
        # semantic: braking methods
        brake_plug="#dc3545", brake_dc="#0d6efd", brake_regen="#198754",
    )


def apply_css(dark: bool) -> None:
    c = _palette(dark)
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="block-container"] {{
        background-color: {c["bg"]} !important;
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    }}
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {{ display: none !important; }}

    /* ── application header ── */
    .app-header {{
        padding: 1.4rem 0 1rem 0;
        border-bottom: 1px solid {c["border"]};
        margin-bottom: 1.8rem;
    }}
    .app-title {{
        font-size: 4.5rem; font-weight: 700;
        color: {c["text"]}; letter-spacing: -0.02em;
    }}

    /* ── available machines grid (single card, centered) ── */
    .machine-grid-solo {{
        display: flex;
        justify-content: center;
        margin: 0.6rem 0 0.8rem 0;
    }}
    .mcard-solo {{
        max-width: 280px;
        width: 100%;
        padding: 1.4rem 1.6rem 1.2rem !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.14), 0 1px 6px rgba(0,0,0,0.08) !important;
    }}
    .mcard-solo .mcard-icon {{
        font-size: 2.4rem !important;
        margin-bottom: 0.4rem !important;
    }}
    .mcard-solo .mcard-name {{
        font-size: 1.3rem !important;
        margin-bottom: 0.3rem !important;
    }}

    /* ── machine selection cards (multi-column grid, future use) ── */
    .machine-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        grid-auto-rows: 1fr;
        gap: 1.2rem;
        margin: 1.6rem 0;
        align-items: stretch;
    }}
    .mcard {{
        background: {c["surface"]};
        border: 2px solid {c["border"]};
        border-radius: 14px;
        padding: 2rem 1.4rem 1.4rem 1.2rem;
        text-align: center;
        transition: border-color .18s, box-shadow .18s;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        height: 100%;
    }}
    .mcard.active {{
        border-color: {c["accent"]};
        background: {c["tag"]};
        box-shadow: 0 0 0 3px {c["accent"]}33;
    }}
    .mcard.disabled {{ opacity: .35; }}
    .mcard-icon {{
        font-family: 'Courier New', monospace;
        font-size: 2.7rem; font-weight: 900;
        color: {c["accent"]}; display: block;
        margin-bottom: .7rem;
    }}
    .mcard-name {{
        font-size: 1.5rem; font-weight: 700;
        color: {c["text"]}; margin-bottom: .5rem;
    }}
    .mcard-tag {{
        display: inline-block; font-size: .7rem;
        font-weight: 700; letter-spacing: .06em;
        text-transform: uppercase;
        background: {c["tag"]};
        color: {c["accent"]};
        border-radius: 4px; padding: .15rem .55rem;
    }}
    .mcard-tag.soon {{ background:{c["surface2"]}; color:{c["muted"]}; }}

    /* ── section label ── */
    .slabel {{
        font-size: .72rem; font-weight: 700;
        letter-spacing: .1em; text-transform: uppercase;
        color: {c["accent"]}; margin-bottom: .4rem;
    }}

    /* ── parameter group (flat design: soft shadow, no rigid border) ── */
    .pgroup {{
        background: {c["surface"]};
        border: none;
        border-radius: 14px;
        padding: 1.4rem 1.4rem 0.9rem;
        margin-bottom: 0.9rem;
        overflow: visible !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.10), 0 1px 8px rgba(0,0,0,0.06);
    }}
    .pgroup-title {{
        font-size: .74rem; font-weight: 700;
        letter-spacing: .08em; text-transform: uppercase;
        color: {c["muted"]};
        padding-bottom: .45rem;
        border-bottom: 1px solid {c["border"]}55;
        margin-bottom: .8rem;
    }}

    /* ── info box ── */
    .ibox {{
        background: {c["input_bg"]};
        border-left: 3px solid {c["accent"]};
        border-radius: 6px;
        padding: .75rem 1rem;
        font-size: .875rem;
        color: {c["muted"]};
        line-height: 1.65;
        margin: .6rem 0 .4rem 0;
    }}

    /* ── metrics (flat: no border, soft shadow) ── */
    [data-testid="stMetric"] {{
        background: {c["surface"]};
        border: none;
        border-radius: 12px;
        padding: .85rem 1.1rem;
        min-height: 90px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.09), 0 1px 6px rgba(0,0,0,0.05);
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: .78rem !important; font-weight: 500 !important;
        color: {c["muted"]} !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.45rem !important; font-weight: 700 !important;
        color: {c["text"]} !important;
    }}

    /* ── main button — all types, monochromatic ── */
    .stButton > button,
    .stButton > button[kind="primary"],
    .stButton > button[kind="secondary"],
    [data-testid="stFormSubmitButton"] > button {{
        background: {c["accent"]} !important;
        color: {c["on_accent"]} !important; border: none !important;
        border-radius: 8px !important; font-weight: 700 !important;
        font-size: 1rem !important; padding: .65rem 2.4rem !important;
        white-space: nowrap !important;
        min-height: 42px !important;
        height: 42px !important;
        line-height: 1 !important;
        transition: opacity .15s;
    }}
    .stButton > button:hover,
    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] > button:hover {{ opacity: .86 !important; }}
    .stButton > button:disabled,
    .stButton > button[disabled] {{
        background: {c["surface2"]} !important;
        color: {c["muted"]} !important;
        opacity: .6 !important;
        cursor: not-allowed !important;
    }}

    /* ── inputs ── */
    input[type="number"], select, textarea {{
        background: {c["input_bg"]} !important;
        color: {c["text"]} !important;
        border: 1px solid {c["border"]} !important;
        border-radius: 7px !important;
        font-size: .93rem !important;
    }}
    label, [data-testid="stWidgetLabel"] p {{
        font-size: 1rem !important;
        font-weight: 500 !important;
        color: {c["muted"]} !important;
    }}
    /* neutralizes negative margin-top that Streamlit injects in widgets inside columns/blocks */
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stElementContainer"],
    [data-testid="column"] {{
        overflow: visible !important;
    }}
    [data-testid="stNumberInput"] > div,
    [data-testid="stTextInput"]   > div,
    [data-testid="stSelectbox"]   > div,
    [data-testid="stSlider"]      > div {{
        margin-top: 0 !important;
    }}
    [data-testid="stNumberInput"],
    [data-testid="stTextInput"],
    [data-testid="stSelectbox"],
    [data-testid="stSlider"] {{
        padding-top: 0.4rem !important;
        overflow: visible !important;
    }}

    /* ── tabs ── */
    [data-baseweb="tab-list"] {{
        background: {c["surface"]} !important;
        border-radius: 10px !important;
        padding: .22rem !important;
        border: 1px solid {c["border"]} !important;
    }}
    [data-baseweb="tab"] {{
        font-size: .88rem !important; font-weight: 600 !important;
        border-radius: 7px !important;
        padding: .4rem 1rem !important;
        color: {c["muted"]} !important;
    }}
    [aria-selected="true"][data-baseweb="tab"] {{
        background: {c["accent"]} !important;
        color: {c["on_accent"]} !important;
    }}

    /* ── theory cards ── */
    .tcard {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-left: 4px solid {c["accent2"]};
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }}
    .tcard h4 {{
        font-size: 1rem; font-weight: 700;
        color: {c["text"]}; margin: 0 0 .55rem 0;
    }}
    .tcard p {{
        font-size: .91rem; line-height: 1.75;
        color: {c["muted"]}; margin: .3rem 0;
    }}
    .tc-up   {{ font-weight: 600; }}
    .tc-down {{ font-weight: 600; }}
    .tc-warn {{
        background: {c["warn_bg"]};
        border-left: 3px solid {c["danger"]};
        border-radius: 5px;
        padding: .5rem .8rem; margin-top: .7rem;
        font-size: .84rem; color: {c["danger"]}; line-height: 1.55;
    }}

    /* ══════════════════════════════════════════════════════
       MOBILE RESPONSIVENESS
    ══════════════════════════════════════════════════════ */

    /* ── Narrow portrait (< 480px) ── */
    @media (max-width: 479px) {{
        .app-title {{
            font-size: 2rem !important;
            letter-spacing: -0.01em !important;
        }}
        .app-header {{
            padding: 0.7rem 0 0.5rem 0 !important;
            margin-bottom: 0.9rem !important;
        }}

        /* Machines grid: 4 → 2 columns */
        .machine-grid {{
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 0.75rem !important;
        }}
        .mcard {{ padding: 1.2rem 0.9rem 1rem !important; }}
        .mcard-icon {{ font-size: 2rem !important; margin-bottom: 0.4rem !important; }}
        .mcard-name {{ font-size: 1.1rem !important; }}

        /* All Streamlit columns stack vertically */
        [data-testid="column"] {{
            flex: 0 0 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            width: 100% !important;
        }}

        /* Buttons with larger touch area */
        .stButton > button {{
            padding: 0.75rem 1.4rem !important;
            font-size: 0.95rem !important;
            min-height: 44px !important;
        }}

        /* Taller inputs for touch */
        input[type="number"] {{
            padding: 0.55rem 0.6rem !important;
            font-size: 1rem !important;
            min-height: 44px !important;
        }}

        /* Abas com texto menor para caber na tela */
        [data-baseweb="tab"] {{
            font-size: 0.78rem !important;
            padding: 0.4rem 0.6rem !important;
        }}

        /* Metrics: slightly smaller font */
        [data-testid="stMetricValue"] {{
            font-size: 1.15rem !important;
        }}
        [data-testid="stMetricLabel"] p {{
            font-size: 0.70rem !important;
        }}

        /* ── THEORY — mobile < 480px ── */

        /* Cards: smaller padding */
        .tcard {{
            padding: 0.85rem 0.9rem !important;
        }}

        /* Side-by-side layout → stacks vertically */
        .tcard-side-pair {{
            flex-direction: column !important;
            gap: 0.8rem !important;
        }}
        .tcard-side-pair > div {{
            flex: 0 0 100% !important;
            min-width: 0 !important;
            width: 100% !important;
        }}

        /* Images inside tcard: 100% width */
        .tcard img {{
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
        }}

        /* MathJax formulas: horizontal scroll to avoid overflow */
        .tcard .MathJax_Display,
        .tcard mjx-container[display="true"],
        .tcard .mjx-chtml,
        .tcard > div[style*="text-align:center"] {{
            overflow-x: auto !important;
            overflow-y: hidden !important;
            max-width: 100% !important;
            font-size: 0.82em !important;
        }}

        /* Power table: horizontal scroll */
        .tcard table {{
            font-size: 0.78rem !important;
            display: block !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            white-space: nowrap !important;
        }}

        /* Theory paragraph text */
        .tcard p {{
            font-size: 0.85rem !important;
            line-height: 1.65 !important;
        }}
        .tcard li {{
            font-size: 0.85rem !important;
            line-height: 1.7 !important;
        }}
    }}

    /* ── Tablet portrait (768–1024px) ── */
    @media (min-width: 769px) and (max-width: 1024px) {{
        .app-title {{
            font-size: 3.2rem !important;
        }}
        .machine-grid {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}
    }}

    /* ── Tablet / phone landscape (480–768px) ── */
    @media (min-width: 480px) and (max-width: 768px) {{
        .app-title {{
            font-size: 2.8rem !important;
        }}
        .machine-grid {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}

        /* Streamlit columns: 2 per row */
        [data-testid="column"] {{
            flex: 0 0 50% !important;
            min-width: 50% !important;
            max-width: 50% !important;
            width: 50% !important;
        }}

        /* Buttons with comfortable touch area */
        .stButton > button {{
            min-height: 42px !important;
        }}

        /* ── THEORY — tablet / landscape ── */

        /* Side-by-side layout: also stacks */
        .tcard-side-pair {{
            flex-direction: column !important;
            gap: 1rem !important;
        }}
        .tcard-side-pair > div {{
            flex: 0 0 100% !important;
            min-width: 0 !important;
            width: 100% !important;
        }}

        /* Images 100% */
        .tcard img {{
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
        }}

        /* Formulas: horizontal scroll */
        .tcard .MathJax_Display,
        .tcard mjx-container[display="true"],
        .tcard .mjx-chtml,
        .tcard > div[style*="text-align:center"] {{
            overflow-x: auto !important;
            overflow-y: hidden !important;
            max-width: 100% !important;
        }}

        /* Tabela: scroll horizontal */
        .tcard table {{
            display: block !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }}

        /* ── machine selection cards ── */
        .card-button-wrapper {{
            margin-bottom: 0.8rem !important;
        }}
        .card-button {{
            background: {c["surface"]} !important;
            border: 2px solid {c["border"]} !important;
            border-radius: 14px !important;
            padding: 1.8rem 1.4rem 1.4rem !important;
            text-align: center !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.8rem !important;
            transition: border-color .18s, box-shadow .18s !important;
        }}
        .card-button:hover {{
            border-color: {c["accent"]} !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.14) !important;
        }}
        .card-icon {{
            font-size: 3rem !important;
            line-height: 1 !important;
        }}
        .card-title {{
            flex: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        .card-name {{
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            color: {c["text"]} !important;
            line-height: 1.3 !important;
        }}
        .card-tag {{
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            color: {c["muted"]} !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)
