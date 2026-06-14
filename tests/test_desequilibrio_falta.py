# -*- coding: utf-8 -*-
"""
test_desequilibrio_falta.py
===========================
Unit tests for voltage unbalance and phase-fault functions (core/desequilibrio_falta.py).

Covers:
  - abc_voltages_deseq: balanced case, per-phase derating, phase loss
  - make_broken_bar_rr_fn: None for severity=0, callable otherwise
  - Symmetrical components: V2/V1 ratio increases with unbalance
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

from core.tim.fault import abc_voltages_deseq, make_broken_bar_rr_fn


VL  = 220.0
F   = 60.0
VPH = VL / np.sqrt(3)          # expected peak ≈ 127 V RMS → ×√2 peak


# ─── abc_voltages_deseq ──────────────────────────────────────────────────────

class TestAbcVoltagesDeseq:
    def test_balanced_peaks_equal(self):
        """No derating → all three phases have equal RMS amplitude."""
        t = np.linspace(0, 2/F, 10000, endpoint=False)
        Va, Vb, Vc = abc_voltages_deseq(t, VL, F)
        rms = lambda v: np.sqrt(np.mean(v**2))
        assert rms(Va) == pytest.approx(rms(Vb), rel=1e-3)
        assert rms(Vb) == pytest.approx(rms(Vc), rel=1e-3)

    def test_balanced_phase_shifts(self):
        """Phases are separated by 120°."""
        t = np.linspace(0, 2/F, 2000)
        Va, Vb, Vc = abc_voltages_deseq(t, VL, F)
        # Cross-correlate to find shift — simpler: check Va+Vb+Vc ≈ 0
        assert np.max(np.abs(Va + Vb + Vc)) == pytest.approx(0.0, abs=1e-6)

    def test_phase_a_derating(self):
        """deseq_a=-0.2 → phase A amplitude reduced by 20%."""
        t = np.linspace(0, 2/F, 2000)
        Va_nom, _, _ = abc_voltages_deseq(t, VL, F)
        Va_der, Vb_der, Vc_der = abc_voltages_deseq(t, VL, F, deseq_a=-0.2)
        rms = lambda v: np.sqrt(np.mean(v**2))
        assert rms(Va_der) == pytest.approx(rms(Va_nom) * 0.8, rel=0.02)
        assert rms(Vb_der) == pytest.approx(rms(Va_nom), rel=0.01)  # others unchanged

    def test_phase_b_loss(self):
        """falta_fase_b=True → phase B voltage is zero."""
        t = np.linspace(0, 2/F, 2000)
        _, Vb, _ = abc_voltages_deseq(t, VL, F, falta_fase_b=True)
        assert np.max(np.abs(Vb)) == pytest.approx(0.0, abs=1e-9)

    def test_phase_c_loss_others_intact(self):
        """falta_fase_c=True → A and B unchanged."""
        t = np.linspace(0, 2/F, 2000)
        Va_ref, Vb_ref, _  = abc_voltages_deseq(t, VL, F)
        Va,     Vb,     Vc = abc_voltages_deseq(t, VL, F, falta_fase_c=True)
        assert np.allclose(Va, Va_ref)
        assert np.allclose(Vb, Vb_ref)
        assert np.max(np.abs(Vc)) == pytest.approx(0.0, abs=1e-9)

    def test_scalar_t_returns_scalars(self):
        Va, Vb, Vc = abc_voltages_deseq(0.0, VL, F)
        assert np.isscalar(Va) or Va.ndim == 0

    def test_deseq_increases_negative_sequence(self):
        """Higher derating → larger negative sequence component (V2)."""
        t = np.linspace(0, 4/F, 4000)

        def negative_seq_rms(deseq):
            Va, Vb, Vc = abc_voltages_deseq(t, VL, F, deseq_a=deseq)
            a = np.exp(1j * 2 * np.pi / 3)
            V2 = (Va + a**2 * Vb + a * Vc) / 3
            return np.sqrt(np.mean(np.abs(V2)**2))

        assert negative_seq_rms(0.3) > negative_seq_rms(0.1)
        assert negative_seq_rms(0.1) > negative_seq_rms(0.0)

    def test_phase_angle_offset_df(self):
        """df_a ≠ 0 produces a different waveform for phase A."""
        t = np.linspace(0, 2/F, 2000)
        Va_ref, _, _ = abc_voltages_deseq(t, VL, F)
        Va_sh,  _, _ = abc_voltages_deseq(t, VL, F, df_a=10.0)
        assert not np.allclose(Va_sh, Va_ref)  # frequency-shifted → waveforms differ


# ─── make_broken_bar_rr_fn ───────────────────────────────────────────────────

class TestBrokenBarRrFn:
    def test_zero_severity_returns_none(self):
        result = make_broken_bar_rr_fn(Rr_nominal=0.816, severity=0.0, wb=1.0)
        assert result is None

    def test_nonzero_severity_returns_callable(self):
        fn = make_broken_bar_rr_fn(Rr_nominal=0.816, severity=0.3, wb=1.0)
        assert callable(fn)

    def test_rr_fn_increases_resistance(self):
        """Broken bar → Rr(t) ≥ Rr_nominal for all t."""
        fn = make_broken_bar_rr_fn(Rr_nominal=0.816, severity=0.5, wb=2.0)
        times = np.linspace(0, 1.0, 100)
        for t in times:
            assert fn(t, 0.0) >= 0.816 * 0.99  # allow tiny float error

    def test_rr_fn_scales_with_severity(self):
        """Higher severity → higher mean Rr."""
        fn_low  = make_broken_bar_rr_fn(0.816, severity=0.2, wb=1.0)
        fn_high = make_broken_bar_rr_fn(0.816, severity=0.8, wb=1.0)
        t_arr = np.linspace(0, 2.0, 200)
        mean_low  = np.mean([fn_low(t,  0.0) for t in t_arr])
        mean_high = np.mean([fn_high(t, 0.0) for t in t_arr])
        assert mean_high > mean_low

    def test_rr_fn_respects_t_start(self):
        """Before t_start, Rr = Rr_nominal."""
        fn = make_broken_bar_rr_fn(Rr_nominal=0.816, severity=0.5, wb=1.0, t_start=2.0)
        assert fn(0.5, 0.0) == pytest.approx(0.816, rel=1e-4)
        assert fn(1.9, 0.0) == pytest.approx(0.816, rel=1e-4)
