import streamlit as st


def _palette(dark: bool) -> dict:
    if dark:
        return dict(
            bg="#0e0e0e", surface="#1a1a1a", surface2="#242424",
            border="#333333", accent="#ffffff", accent2="#ffffff",
            on_accent="#000000",
            text="#ffffff", muted="#b5b5b5",
            success="#22eb6c", danger="#ff4444",
            warn_bg="rgba(255,68,68,0.08)", input_bg="#111111",
            tag="#242424",
        )
    return dict(
        bg="#ffffff", surface="#ebebeb", surface2="#ebebeb",
        border="#d0d0d0", accent="#000000", accent2="#000000",
        on_accent="#ffffff",
        text="#000000", muted="#555555",
        success="#22eb6c", danger="#ff0000",
        warn_bg="rgba(220,38,38,0.06)", input_bg="#ffffff",
        tag="#ffffff",
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

    /* ── cabeçalho da aplicação ── */
    .app-header {{
        padding: 1.4rem 0 1rem 0;
        border-bottom: 1px solid {c["border"]};
        margin-bottom: 1.8rem;
    }}
    .app-title {{
        font-size: 4.5rem; font-weight: 700;
        color: {c["text"]}; letter-spacing: -0.02em;
    }}

    /* ── cartões de seleção de máquina ── */
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

    /* ── rotulo de secao ── */
    .slabel {{
        font-size: .72rem; font-weight: 700;
        letter-spacing: .1em; text-transform: uppercase;
        color: {c["accent"]}; margin-bottom: .4rem;
    }}

    /* ── grupo de parâmetros ── */
    .pgroup {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        padding: 1.6rem 1.4rem 1rem;
        margin-bottom: 1rem;
        overflow: visible !important;
    }}
    .pgroup-title {{
        font-size: .76rem; font-weight: 700;
        letter-spacing: .08em; text-transform: uppercase;
        color: {c["accent"]};
        padding-bottom: .5rem;
        border-bottom: 1px solid {c["border"]};
        margin-bottom: .85rem;
    }}

    /* ── caixa informativa ── */
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

    /* ── metricas ── */
    [data-testid="stMetric"] {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: .85rem 1.1rem;
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: .78rem !important; font-weight: 500 !important;
        color: {c["muted"]} !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.45rem !important; font-weight: 700 !important;
        color: {c["text"]} !important;
    }}

    /* ── botao principal ── */
    .stButton > button {{
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
    .stButton > button:hover {{ opacity: .86 !important; }}
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
    /* neutraliza margin-top negativo que o Streamlit injeta em widgets dentro de colunas/blocos */
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

    /* ── abas ── */
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

    /* ── cartoes de teoria ── */
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
       RESPONSIVIDADE MOBILE
    ══════════════════════════════════════════════════════ */

    /* ── Retrato estreito (< 480px) ── */
    @media (max-width: 479px) {{
        .app-title {{
            font-size: 2rem !important;
            letter-spacing: -0.01em !important;
        }}
        .app-header {{
            padding: 0.7rem 0 0.5rem 0 !important;
            margin-bottom: 0.9rem !important;
        }}

        /* Grade de máquinas: 4 → 2 colunas */
        .machine-grid {{
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 0.75rem !important;
        }}
        .mcard {{ padding: 1.2rem 0.9rem 1rem !important; }}
        .mcard-icon {{ font-size: 2rem !important; margin-bottom: 0.4rem !important; }}
        .mcard-name {{ font-size: 1.1rem !important; }}

        /* Todas as colunas Streamlit empilham verticalmente */
        [data-testid="column"] {{
            flex: 0 0 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            width: 100% !important;
        }}

        /* Botões com área de toque maior */
        .stButton > button {{
            padding: 0.75rem 1.4rem !important;
            font-size: 0.95rem !important;
            min-height: 44px !important;
        }}

        /* Inputs mais altos para toque */
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

        /* Métricas: fonte ligeiramente menor */
        [data-testid="stMetricValue"] {{
            font-size: 1.15rem !important;
        }}
        [data-testid="stMetricLabel"] p {{
            font-size: 0.70rem !important;
        }}

        /* ── TEORIA — mobile < 480px ── */

        /* Cartões: padding menor */
        .tcard {{
            padding: 0.85rem 0.9rem !important;
        }}

        /* Layout side-by-side → empilha verticalmente */
        .tcard-side-pair {{
            flex-direction: column !important;
            gap: 0.8rem !important;
        }}
        .tcard-side-pair > div {{
            flex: 0 0 100% !important;
            min-width: 0 !important;
            width: 100% !important;
        }}

        /* Imagens dentro de tcard: 100% da largura */
        .tcard img {{
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
        }}

        /* Fórmulas MathJax: scroll horizontal para não sair da tela */
        .tcard .MathJax_Display,
        .tcard mjx-container[display="true"],
        .tcard .mjx-chtml,
        .tcard > div[style*="text-align:center"] {{
            overflow-x: auto !important;
            overflow-y: hidden !important;
            max-width: 100% !important;
            font-size: 0.82em !important;
        }}

        /* Tabela de potências: scroll horizontal */
        .tcard table {{
            font-size: 0.78rem !important;
            display: block !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            white-space: nowrap !important;
        }}

        /* Texto dos parágrafos da teoria */
        .tcard p {{
            font-size: 0.85rem !important;
            line-height: 1.65 !important;
        }}
        .tcard li {{
            font-size: 0.85rem !important;
            line-height: 1.7 !important;
        }}
    }}

    /* ── Tablet / celular landscape (480–768px) ── */
    @media (min-width: 480px) and (max-width: 768px) {{
        .app-title {{
            font-size: 2.8rem !important;
        }}
        .machine-grid {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}

        /* Colunas Streamlit: 2 por linha */
        [data-testid="column"] {{
            flex: 0 0 50% !important;
            min-width: 50% !important;
            max-width: 50% !important;
            width: 50% !important;
        }}

        /* Botões com área de toque confortável */
        .stButton > button {{
            min-height: 42px !important;
        }}

        /* ── TEORIA — tablet / landscape ── */

        /* Layout side-by-side: empilha também */
        .tcard-side-pair {{
            flex-direction: column !important;
            gap: 1rem !important;
        }}
        .tcard-side-pair > div {{
            flex: 0 0 100% !important;
            min-width: 0 !important;
            width: 100% !important;
        }}

        /* Imagens 100% */
        .tcard img {{
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
        }}

        /* Fórmulas: scroll horizontal */
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
    }}
    </style>
    """, unsafe_allow_html=True)
