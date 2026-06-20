# -*- coding: utf-8 -*-
"""
fft_utils.py
============
Centralized one-sided FFT helper for MIT signal analysis.

Responsibilities:
  - Compute rfft amplitude spectrum with configurable scaling
  - Single source of truth for FFT conventions across energy and harmonic modules

Relationships:
  Imported by : core.tim.energy_analysis, core.tim.harmonic_analysis
  Imports     : numpy
"""

from __future__ import annotations

import numpy as np


def compute_fft(
    signal: np.ndarray,
    dt: float,
    scale: str = "raw",
) -> tuple[np.ndarray, np.ndarray]:
    """One-sided FFT amplitude spectrum.

    Args:
        signal: 1-D time-domain array.
        dt: sample interval in seconds.
        scale: ``"raw"`` divides by N (suited for THD thresholds);
               ``"rms"`` multiplies by 2/N (peak amplitude for odd harmonics).

    Returns:
        ``(freqs, amplitudes)`` — matching 1-D arrays.
    """
    N = len(signal)
    spec = np.abs(np.fft.rfft(signal))
    if scale == "rms":
        spec = spec * (2.0 / N)
    else:
        spec = spec / N
    freqs = np.fft.rfftfreq(N, d=dt)
    return freqs, spec
