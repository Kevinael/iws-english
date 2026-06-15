# -*- coding: utf-8 -*-
"""
zoom_helpers.py
===============
Zoom-window calculation and Plotly axis-range application for MIT charts.

Responsibilities:
  - Compute the (t_start, t_end) window for a given zoom mode.
  - Apply x/y axis ranges to a Plotly figure in-place.

Relationships:
  Imported by : ui_components.tim_results
  Imports     : numpy, plotly
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import plotly.graph_objects as go

from core.constants import (
    STARTING_SPEED_THRESHOLD,
    ZOOM_SS_LOOKBACK_FRAC,
    ZOOM_SS_MIN_PAD_S,
    ZOOM_START_PAD_S,
    ZOOM_PULSE_PAD_FRAC,
    ZOOM_PULSE_MIN_PAD_S,
    ZOOM_YAXIS_REL_FLOOR,
    ZOOM_YAXIS_ABS_FLOOR,
    ZOOM_YAXIS_PAD_FRAC,
)


@dataclass(frozen=True)
class ZoomCtx:
    """Immutable context for zoom-window calculation."""
    res:          dict[str, Any]
    exp_type:     str
    exp_config:   dict[str, Any]
    mp_f:         float   # mp.f
    mp_p:         int     # mp.p
    t_ss:         float   # time where steady-state begins
    tmax_data:    float
    t_pulso_on:   float   # load-pulse insertion time
    t_pulso_off:  float   # load-pulse removal time
    tl_arr:       Any     # optional TL time array (numpy array or None)


def compute_t_window(
    zoom_mode: str,
    ctx: ZoomCtx,
) -> tuple[float, float] | None:
    """Return (t0, t1) for the requested zoom_mode, or None for 'Full'."""
    res       = ctx.res
    exp_type  = ctx.exp_type
    cfg       = ctx.exp_config
    tmax_data = ctx.tmax_data
    t_ss      = ctx.t_ss

    if zoom_mode == "Steady State":
        return (max(0.0, t_ss - max(ZOOM_SS_LOOKBACK_FRAC * tmax_data, ZOOM_SS_MIN_PAD_S)), tmax_data)

    if zoom_mode == "Starting":
        _pad = ZOOM_START_PAD_S
        if exp_type == "dol":
            _ws_mec = 2.0 * np.pi * ctx.mp_f / (ctx.mp_p / 2.0)
            _wr     = np.asarray(res["wr"], dtype=float)
            _above  = np.where(_wr >= STARTING_SPEED_THRESHOLD * _ws_mec)[0]
            _t_acc  = float(res["t"][int(_above[0])]) if len(_above) > 0 else t_ss
            _tend   = _t_acc + _pad
        elif exp_type in ("yd", "comp"):
            _tend = max(float(cfg.get("t_carga", 0.0)), float(cfg.get("t_2", 0.0))) + _pad
        elif exp_type == "soft":
            _tend = max(float(cfg.get("t_pico", 0.0)), float(cfg.get("t_carga", 0.0))) + _pad
        elif exp_type == "voltage_sag":
            _tend = float(cfg.get("t_start_sag", 0.0)) + float(cfg.get("t_duration_sag", 0.1)) + _pad
        else:
            _tend = t_ss + _pad
        return (0.0, min(_tend, tmax_data))

    if zoom_mode == "Load Pulse":
        _dur = max(ctx.t_pulso_off - ctx.t_pulso_on, ZOOM_PULSE_MIN_PAD_S)
        _pad = max(ZOOM_PULSE_PAD_FRAC * _dur, ZOOM_PULSE_MIN_PAD_S)
        return (
            max(0.0, ctx.t_pulso_on - _pad),
            min(tmax_data, ctx.t_pulso_off + _pad),
        )

    return None  # "Full" or unrecognised


def y_ranges(
    t_window: tuple[float, float] | None,
    keys: list[str],
    res: dict[str, Any],
    tl_arr: Any = None,
) -> dict[str, tuple[float, float]]:
    """Compute padded y-ranges for each key within t_window."""
    if t_window is None:
        return {}
    t_arr = np.asarray(res["t"], dtype=float)
    mask  = (t_arr >= t_window[0]) & (t_arr <= t_window[1])
    ranges: dict[str, tuple[float, float]] = {}
    for key in keys:
        if key not in res:
            continue
        vals = np.asarray(res[key], dtype=float)[mask]
        if tl_arr is not None and key == "Te":
            vals = np.concatenate([vals, np.asarray(tl_arr, dtype=float)[mask]])
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            continue
        ymin, ymax = float(vals.min()), float(vals.max())
        ymid     = (ymin + ymax) / 2.0
        min_span = max(abs(ymid) * ZOOM_YAXIS_REL_FLOOR, ZOOM_YAXIS_ABS_FLOOR)
        if (ymax - ymin) < min_span:
            ymin, ymax = ymid - min_span / 2, ymid + min_span / 2
        pad = (ymax - ymin) * ZOOM_YAXIS_PAD_FRAC
        ranges[key] = (ymin - pad, ymax + pad)
    return ranges


def apply_zoom(
    fig: go.Figure,
    keys: list[str],
    t_window: tuple[float, float] | None,
    res: dict[str, Any],
    tl_arr: Any = None,
) -> go.Figure:
    """Apply x/y zoom to a single-panel figure. Returns fig (mutated)."""
    if t_window is None:
        return fig
    x0, x1 = t_window
    fig.update_xaxes(range=[x0, x1], autorange=False)
    yr = y_ranges(t_window, keys, res, tl_arr)
    if yr:
        ylo, yhi = next(iter(yr.values()))
        fig.update_layout(yaxis=dict(range=[ylo, yhi], autorange=False))
    return fig


_SPEED_KEYS = {"n", "wr"}


def apply_zoom_overlay(
    fig: go.Figure,
    keys: list[str],
    t_window: tuple[float, float] | None,
    res: dict[str, Any],
    tl_arr: Any = None,
) -> go.Figure:
    """Apply x/y zoom to an overlay figure with dual y-axes. Returns fig (mutated)."""
    if t_window is None:
        return fig
    x0, x1 = t_window
    fig.update_xaxes(range=[x0, x1], autorange=False)
    yr         = y_ranges(t_window, keys, res, tl_arr)
    left_keys  = [k for k in keys if k not in _SPEED_KEYS]
    right_keys = [k for k in keys if k in _SPEED_KEYS]
    if left_keys and any(k in yr for k in left_keys):
        all_v = np.concatenate([np.array(yr[k]) for k in left_keys if k in yr])
        fig.update_layout(yaxis=dict(range=[float(all_v.min()), float(all_v.max())], autorange=False))
    if right_keys and any(k in yr for k in right_keys):
        all_v = np.concatenate([np.array(yr[k]) for k in right_keys if k in yr])
        fig.update_layout(yaxis2=dict(range=[float(all_v.min()), float(all_v.max())], autorange=False))
    return fig
