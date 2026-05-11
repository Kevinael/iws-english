# -*- coding: utf-8 -*-
"""Orquestrador principal do ElectraSim.

Responsabilidades deste arquivo:
  - Configuração da página Streamlit
  - Inicialização do session_state
  - Sidebar / cabeçalho
  - Instanciação das abas e delegação para ui_components/
"""

from __future__ import annotations

import streamlit as st

from ui.theme import apply_css, REF_COLORS, REF_DASHES
from ui.clean_view import render_clean_view
from viz.eqcircuit_plotter import render_circuit as _render_circuit_eqcircuit_plotter

from ui_components.theory_view import render_theory_tab
from ui_components.sim_config import (
    MACHINES,
    _WK,
    _PRESETS,
    render_machine_selector,
    render_machine_params,
    render_experiment_config,
)
from ui_components.sim_results import render_results, render_ref_panel
from ui_components.sim_runner import execute_simulation_flow


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ElectraSim",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS LOCAIS
# ─────────────────────────────────────────────────────────────────────────────

def _render_circuit(mp, dark: bool) -> None:
    from ui.theme import _palette
    _render_circuit_eqcircuit_plotter(mp, dark, _palette)


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTRADOR
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
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

    # Carrega o preset Krause automaticamente na primeira execução da sessão
    _KRAUSE_KEY = "Padrão — Krause 3 HP (2.2 kW / 12 N·m) 220 V/60 Hz"
    if "_preset_loaded" not in st.session_state:
        st.session_state["_preset_loaded"] = True
        _pdata = _PRESETS.get(_KRAUSE_KEY, {})
        _wk_map = {
            "Vl": _WK["Vl"], "f": _WK["f"], "Rs": _WK["Rs"], "Rr": _WK["Rr"],
            "input_mode": _WK["input_mode"], "f_ref": _WK["f_ref"],
            "Xm": _WK["Xm"], "Xls": _WK["Xls"], "Xlr": _WK["Xlr"],
            "Rfe": _WK["Rfe"], "p": _WK["p"], "J": _WK["J"], "B": _WK["B"],
            "exp_type": _WK["exp_type"], "Tl_final": _WK["Tl_final"],
        }
        for field, widget_key in _wk_map.items():
            if field in _pdata:
                st.session_state[widget_key] = _pdata[field]

    # responsividade via CSS puro — sem JS de viewport
    is_mobile = False

    dark = st.session_state.get("dark_mode", False)
    apply_css(dark)

    st.markdown(
        '<div class="app-header">'
        '<div class="app-title">ElectraSim</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state["selected_machine"]:
        render_machine_selector(dark)
        return

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

    tab_sim, tab_teoria, tab_clean = st.tabs(["Simulação", "Teoria", "Visualização para Artigo"])

    # ── ABA SIMULAÇÃO ─────────────────────────────────────────────────────
    with tab_sim:
        # controles globais
        ct1, ct2, ct3, _ = st.columns([1, 1.6, 0.8, 4])
        with ct1:
            st.toggle("Modo Escuro", value=dark, key="dark_mode")
        with ct2:
            st.toggle("Travar Parâmetros", value=False, key="experiment_mode")
        with ct3:
            st.number_input("Casas decimais", min_value=0, max_value=6, value=3, step=1, key="decimals")

        experiment_mode = st.session_state.get("experiment_mode", False)
        dec = int(st.session_state.get("decimals", 3))

        # parâmetros + circuito
        col_params, col_circuit = st.columns([1, 1], gap="large")

        with col_params:
            mp, ref_code, energy_tariff = render_machine_params(dark, experiment_mode, _WK)

        with col_circuit:
            st.markdown('<p class="slabel">Circuito Equivalente Monofásico</p>', unsafe_allow_html=True)
            _render_circuit(mp, dark)
            st.write("")
            exp_config, var_keys, var_labels, tmax, h = render_experiment_config(mp, _WK)

        # ── CTA principal ─────────────────────────────────────────────
        st.write("")
        run_clicked = st.button(
            "Executar Simulação", key="btn_run",
            use_container_width=True,
        )

        _can_save = (
            st.session_state["sim_result"] is not None
            and len(st.session_state["ref_list"]) < 5
        )
        ba1, ba2 = st.columns(2)
        with ba1:
            save_ref = st.button(
                "Salvar como Referência", key="btn_save_ref",
                use_container_width=True,
                disabled=not _can_save,
                help="Salva o resultado atual para comparação (máx. 5)",
            )
        with ba2:
            clear_ref = st.button(
                "Limpar Referências", key="btn_clear_ref",
                use_container_width=True,
                disabled=not st.session_state["ref_list"],
                help="Remove todas as referências salvas",
            )

        if save_ref and _can_save:
            new_ref = dict(st.session_state["sim_result"])
            _idx    = len(st.session_state["ref_list"])
            new_ref["color"] = REF_COLORS[_idx % len(REF_COLORS)]
            new_ref["dash"]  = REF_DASHES[_idx % len(REF_DASHES)]
            st.session_state["ref_list"].append(new_ref)
            st.rerun()
        if clear_ref:
            st.session_state["ref_list"] = []
            st.rerun()

        if run_clicked:
            execute_simulation_flow(
                mp=mp, exp_config=exp_config, var_keys=var_keys, var_labels=var_labels,
                tmax=tmax, h=h, ref_code=ref_code, dark=dark,
                energy_tariff=energy_tariff,
            )

        _toast = st.session_state.pop("_sim_toast", None)
        if _toast:
            st.success(_toast)

        sr = st.session_state.get("sim_result")
        render_ref_panel()
        ref_list = st.session_state["ref_list"]

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
                exp_config=sr.get("exp_config"),
                torque_fn=sr.get("torque_fn"),
            )

    # ── ABA TEORIA ────────────────────────────────────────────────────────
    with tab_teoria:
        render_theory_tab()

    # ── ABA VISUALIZAÇÃO PARA ARTIGO ──────────────────────────────────────
    with tab_clean:
        render_clean_view()


if __name__ == "__main__":
    main()
