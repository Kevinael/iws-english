# -*- coding: utf-8 -*-
"""Orquestrador principal do Simulador de Máquinas Elétricas.

Responsabilidades deste arquivo:
  - Configuração da página Streamlit
  - Inicialização do session_state
  - Detecção de viewport
  - Sidebar / cabeçalho
  - Instanciação das abas e delegação para ui_components/
"""

from __future__ import annotations

import streamlit as st

from ui.theme import apply_css
from ui.clean_view import render_clean_view
from viz.eqcircuit_plotter import render_circuit as _render_circuit_eqcircuit_plotter

from ui_components.theory_view import render_theory_tab
from ui_components.sim_config import (
    MACHINES,
    _WK,
    render_machine_selector,
    render_machine_params,
    render_experiment_config,
)
from ui_components.sim_results import render_results
from ui_components.sim_runner import execute_simulation_flow


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador de Máquinas Elétricas",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS LOCAIS
# ─────────────────────────────────────────────────────────────────────────────

def _render_circuit(mp, dark: bool) -> None:
    from ui.theme import _palette
    _render_circuit_eqcircuit_plotter(mp, dark, _palette)


_REF_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
_REF_DASHES = ["dash", "dot", "solid", "dash", "dot"]


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTRADOR
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # inicializa session_state
    _defaults = {
        "dark_mode":        False,
        "experiment_mode":  False,
        "selected_machine": None,
        "sim_result":       None,
        "ref_list":         [],
        "decimals":         3,
        "pdf_bytes":        None,
    }
    for key, val in _defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # detecção de largura de viewport (executa apenas uma vez)
    if "_vw" not in st.session_state:
        st.html(
            """<script>
            var vw = window.innerWidth;
            var p  = new URLSearchParams(window.parent.location.search);
            if (p.get('_vw') !== String(vw)) {
                p.set('_vw', String(vw));
                window.parent.history.replaceState({}, '', '?' + p.toString());
                window.parent.location.reload();
            }
            </script>"""
        )
        st.session_state["_vw"] = int(st.query_params.get("_vw", "1200"))

    _vw       = int(st.session_state.get("_vw", 1200))
    is_mobile = _vw < 600

    dark = st.session_state.get("dark_mode", False)
    apply_css(dark)

    # cabeçalho
    st.markdown(
        '<div class="app-header">'
        '<div class="app-title">Simulador de Máquinas Elétricas</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # tela de seleção de máquina
    if not st.session_state["selected_machine"]:
        render_machine_selector(dark)
        return

    # navegação: voltar
    col_back, col_title = st.columns([1, 9], vertical_alignment="center")
    with col_back:
        if st.button("Voltar", key="btn_back"):
            st.session_state["selected_machine"] = None
            st.session_state["sim_result"]        = None
            st.rerun()
    with col_title:
        machine_name = next(
            m["name"] for m in MACHINES
            if m["key"] == st.session_state["selected_machine"]
        )
        st.markdown(f"### {machine_name}")

    st.divider()

    # ── abas ──────────────────────────────────────────────────────────────
    tab_sim, tab_teoria, tab_clean = st.tabs(["Simulação", "Teoria", "Visualização para Artigo"])

    # ── ABA SIMULAÇÃO ─────────────────────────────────────────────────────
    with tab_sim:
        ct1, ct2, ct3, _ = st.columns([1, 1.6, 0.8, 4])
        with ct1:
            st.toggle("Modo Escuro", value=dark, key="dark_mode")
        with ct2:
            st.toggle("Travar Parâmetros", value=False, key="experiment_mode")
        with ct3:
            st.number_input("Casas decimais dos resultados", min_value=0, max_value=6, value=3, step=1, key="decimals")

        experiment_mode = st.session_state.get("experiment_mode", False)
        dec = int(st.session_state.get("decimals", 3))

        st.write("")

        col_params, col_circuit = st.columns([1, 1], gap="large")

        with col_params:
            mp, ref_code, energy_tariff = render_machine_params(dark, experiment_mode, _WK)

        with col_circuit:
            st.markdown('<p class="slabel">Circuito Equivalente Monofásico</p>', unsafe_allow_html=True)
            _render_circuit(mp, dark)
            st.write("")
            exp_config, var_keys, var_labels, tmax, h = render_experiment_config(mp, _WK)

        st.write("")

        # botões de ação
        bc1, bc2, bc3, bc4, bc5 = st.columns([1.5, 1.2, 1.2, 1.2, 1.5], vertical_alignment="bottom")
        with bc2:
            run_clicked = st.button("Executar Simulação", key="btn_run", width='stretch')
        with bc3:
            _can_save = (
                st.session_state["sim_result"] is not None
                and len(st.session_state["ref_list"]) < 5
            )
            save_ref = st.button(
                "Salvar Referência", key="btn_save_ref", width='stretch',
                disabled=not _can_save,
                help="Salva o resultado atual como referência (máx. 5)",
            )
        with bc4:
            clear_ref = st.button(
                "Limpar Referências", key="btn_clear_ref", width='stretch',
                disabled=not st.session_state["ref_list"],
                help="Remove todas as referências salvas",
            )

        if save_ref and _can_save:
            new_ref = dict(st.session_state["sim_result"])
            _idx    = len(st.session_state["ref_list"])
            new_ref["color"] = _REF_COLORS[_idx % len(_REF_COLORS)]
            new_ref["dash"]  = _REF_DASHES[_idx % len(_REF_DASHES)]
            st.session_state["ref_list"].append(new_ref)
            st.rerun()
        if clear_ref:
            st.session_state["ref_list"] = []
            st.rerun()

        # execução da simulação
        if run_clicked:
            execute_simulation_flow(
                mp=mp, exp_config=exp_config, var_keys=var_keys, var_labels=var_labels,
                tmax=tmax, h=h, ref_code=ref_code, dark=dark,
                energy_tariff=energy_tariff,
            )

        # toast pós-simulação
        _toast = st.session_state.pop("_sim_toast", None)
        if _toast:
            st.success(_toast)

        sr       = st.session_state.get("sim_result")
        ref_list = st.session_state["ref_list"]

        # painel de referências salvas
        if ref_list:
            st.markdown('<p class="slabel">Referências Salvas</p>', unsafe_allow_html=True)
            _dash_opts = {"Tracejado": "dash", "Pontilhado": "dot", "Sólido": "solid"}
            _h1, _h2, _h3, _h4 = st.columns([5, 0.55, 1.5, 0.4])
            _h2.caption("Cor")
            _h3.caption("Linha")
            for _i, _ref in enumerate(ref_list):
                _c1, _c2, _c3, _c4 = st.columns([5, 0.55, 1.5, 0.4])
                with _c1:
                    st.markdown(
                        f'<div style="padding:0.38rem 0.75rem;border-radius:6px;'
                        f'background:rgba(128,128,128,0.08);font-size:0.88rem;'
                        f'border-left:3px solid {_ref.get("color","#888")};">'
                        f'<strong>{_ref.get("exp_label","Referência")}</strong></div>',
                        unsafe_allow_html=True,
                    )
                with _c2:
                    _ref["color"] = st.color_picker(
                        "Cor", value=_ref.get("color", "#888888"),
                        key=f"ref_color_{_i}", label_visibility="collapsed",
                    )
                with _c3:
                    _cur = _ref.get("dash", "dash")
                    _idx = list(_dash_opts.values()).index(_cur) if _cur in _dash_opts.values() else 0
                    _sel = st.selectbox(
                        "Linha", list(_dash_opts.keys()), index=_idx,
                        key=f"ref_dash_{_i}", label_visibility="collapsed",
                    )
                    _ref["dash"] = _dash_opts[_sel]
                with _c4:
                    if st.button("✕", key=f"ref_del_{_i}", help="Remover esta referência"):
                        st.session_state["ref_list"].pop(_i)
                        st.rerun()

        if sr is not None:
            render_results(
                res=sr["res"],
                var_keys=var_keys if var_keys else sr["var_keys"],
                var_labels=var_labels if var_labels else sr["var_labels"],
                dark=sr["dark"],
                t_events=sr["t_events"],
                mp=sr["mp"],
                exp_label=sr.get("exp_label", "Simulacao"),
                exp_type=sr.get("exp_type",   "dol"),
                decimals=dec,
                ref_list=ref_list,
                primary_color=None,
                is_mobile=is_mobile,
                energy_tariff=sr.get("energy_tariff", 0.75),
            )

    # ── ABA TEORIA ────────────────────────────────────────────────────────
    with tab_teoria:
        render_theory_tab()

    # ── ABA VISUALIZAÇÃO PARA ARTIGO ──────────────────────────────────────
    with tab_clean:
        render_clean_view()


if __name__ == "__main__":
    main()
