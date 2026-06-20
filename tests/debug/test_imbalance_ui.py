import streamlit as st
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui_components.tim_fault_ui import render_imbalance_ui
from core.tim.fault_model import abc_voltages_imbalance
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Test — Voltage Unbalance", layout="wide")
st.title("Test: Voltage Unbalance / Phase Loss")

config = {}
render_imbalance_ui(config, tmax=2.0)

if st.button("Simular"):
    t = np.linspace(0.0, 2.0, 4000)
    Va, Vb, Vc = abc_voltages_imbalance(
        t, Vl=220.0, f=60.0,
        imbalance_a=config["imbalance_a"],
        imbalance_b=config["imbalance_b"],
        imbalance_c=config["imbalance_c"],
        phase_loss_a=config["phase_loss_a"],
        phase_loss_b=config["phase_loss_b"],
        phase_loss_c=config["phase_loss_c"],
    )
    t_imbalance = config["t_imbalance"]
    if t_imbalance > 0.0:
        mask = t < t_imbalance
        t_bal = t[mask]
        Va_bal, Vb_bal, Vc_bal = abc_voltages_imbalance(t_bal, 220.0, 60.0)
        Va[mask], Vb[mask], Vc[mask] = Va_bal, Vb_bal, Vc_bal

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=Va, name="Va", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=t, y=Vb, name="Vb", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=t, y=Vc, name="Vc", line=dict(color="green")))
    if t_imbalance > 0.0:
        fig.add_vline(x=t_imbalance, line_dash="dash", line_color="orange",
                      annotation_text=f"t={t_imbalance:.2f}s")
    fig.update_layout(title="Phase voltages", xaxis_title="Time (s)", yaxis_title="Voltage (V)")
    st.plotly_chart(fig, width="stretch")
