    # ── DEBUG: RMS of all variables at steady state ──────────────────────────
    st.divider()
    st.markdown("**[DEBUG] RMS of variables at steady state**")
    _rms_keys = [
        ("ias","ias_rms"), ("ibs","ibs_rms"), ("ics","ics_rms"),
        ("iar","iar_rms"), ("ibr","ibr_rms"), ("icr","icr_rms"),
        ("ids","ids_rms"), ("iqs","iqs_rms"), ("idr","idr_rms"), ("iqr","iqr_rms"),
        ("Va","Va_rms"),   ("Vb","Vb_rms"),   ("Vc","Vc_rms"),
        ("Vds","Vds_rms"), ("Vqs","Vqs_rms"),
    ]
    _debug_rows = [{"Variable": k, "RMS (steady state)": f"{res[rk]:.6f}"}
                   for k, rk in _rms_keys if rk in res]
    st.dataframe(_debug_rows, width='stretch')