"""DC machine equivalent circuit renderer — on-the-fly schemdraw, same as IM.

Generates PNG in memory (io.BytesIO, dpi=150) via matplotlib + schemdraw.
Caches bytes by (excitation, dark). st.image(bytes, width='stretch').
"""

from __future__ import annotations

import io

import streamlit as st


_CIRCUIT_LABELS: dict[str, str] = {
    "sep_motor":    "Separately Excited — Motor",
    "sep_gen":      "Separately Excited — Generator",
    "shunt_motor":  "Shunt (Parallel) — Motor",
    "shunt_gen":    "Shunt (Parallel) — Generator",
    "series_motor": "Series — Motor",
}


# ─────────────────────────────────────────────────────────────────────────────
# BUILDERS — one per excitation type
# ─────────────────────────────────────────────────────────────────────────────

def _build_sep_motor(d, wire):
    import schemdraw.elements as elm
    d.push()
    Rf = d.add(elm.Inductor2().right().color(wire).label("$N_f$", loc="top"))
    d.add(elm.Line().down().color(wire))
    d.add(elm.Line().down().color(wire).dot(open=True))
    d.pop()
    d.push()
    d.add(elm.Resistor().down().color(wire).label("$R_{fw}$", loc="right"))
    d.add(elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="right").dot(open=True))
    d.add(elm.Gap().right().color(wire).label(("+", "$V_f$", "−")))
    d.pop()
    d.move_from(Rf.end, dx=2, dy=1)
    d.push()
    Ea = d.add(elm.Motor().down().color(wire).label("$E_a$", loc="right"))
    d.add(elm.Line().down().color(wire))
    Neg = d.add(elm.Line().right().color(wire).dot(open=True))
    d.pop()
    d.add(elm.Line().up().color(wire))
    d.add(elm.Resistor().right().color(wire).label("$R_a$", loc="top").dot(open=True))
    import schemdraw.elements as elm2
    d.add(elm2.Gap().down().toy(Neg.end).color(wire).label(("+", "$V_t$", "−")))


def _build_shunt_motor(d, wire):
    import schemdraw.elements as elm
    d.push()
    Nf = d.add(elm.Inductor2().right().color(wire).label("$N_f$", loc="top"))
    d.add(elm.Line().up().color(wire))
    d.add(elm.Resistor().up().color(wire).label("$R_{fw}$", loc="right"))
    d.add(elm.Line().right().color(wire).dot(open=True))
    d.pop()
    d.add(elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="right"))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().right().color(wire).dot(open=True))
    d.push()
    Vtm = d.add(elm.Line().right().color(wire).dot(open=True))
    d.pop()
    d.add(elm.Line().up().color(wire))
    d.add(elm.Motor().up().color(wire).label("$E_a$", loc="right"))
    d.add(elm.Resistor().up().color(wire).label("$R_a$", loc="right"))
    Vtp = d.add(elm.Line().right().color(wire).dot(open=True))
    d.add(elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(Vtp.end, Vtm.end))


def _build_series_motor(d, wire):
    import schemdraw.elements as elm
    d.push()
    Ea = d.add(elm.Motor().down().color(wire).label("$E_a$", loc="right"))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().right().color(wire))
    T2 = d.add(elm.Dot(open=True))
    d.pop()
    d.add(elm.Resistor().up().color(wire).label("$R_a$", loc="right"))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().down().color(wire))
    d.add(elm.Inductor2().right().color(wire).label("$N_s$", loc="top"))
    d.add(elm.Line().up().color(wire))
    d.add(elm.Resistor().right().color(wire).label("$R_s$", loc="top"))
    T1 = d.add(elm.Dot(open=True))
    d.add(elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(T1.end, T2.end))


def _build_sep_gen(d, wire):
    import schemdraw.elements as elm
    d.push()
    Rf = d.add(elm.Inductor2().right().color(wire).label("$N_f$", loc="top"))
    d.add(elm.Line().down().color(wire))
    d.add(elm.Line().down().color(wire).dot(open=True))
    d.pop()
    d.push()
    d.add(elm.Resistor().down().color(wire).label("$R_{fw}$", loc="right"))
    d.add(elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="right").dot(open=True))
    d.add(elm.Gap().right().color(wire).label(("+", "$V_f$", "−")))
    d.pop()
    d.move_from(Rf.end, dx=2, dy=1)
    d.push()
    Ea = d.add(elm.Motor().down().color(wire).label("$E_a$", loc="right"))
    d.add(elm.Line().down().color(wire))
    Vtm = d.add(elm.Line().right().color(wire).dot(open=True))
    d.pop()
    d.add(elm.Line().up().color(wire))
    Vtp = d.add(elm.Resistor().right().color(wire).label("$R_a$", loc="top").dot(open=True))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().down().color(wire))
    d.add(elm.ResistorVar().down().color(wire).label("$R_L$", loc="right"))
    d.add(elm.Line().down().color(wire))
    d.add(elm.Line().left().color(wire))
    d.add(elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(Vtp.end, Vtm.end))


def _build_shunt_gen(d, wire):
    import schemdraw.elements as elm
    d.push()
    Nf = d.add(elm.Inductor2().right().color(wire).label("$N_f$", loc="top"))
    d.add(elm.Line().up().color(wire))
    d.add(elm.Resistor().up().color(wire).label("$R_{fw}$", loc="right"))
    d.add(elm.Line().right().color(wire).dot(open=True))
    d.pop()
    d.add(elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="right"))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().right().color(wire).dot(open=True))
    d.push()
    Vtm = d.add(elm.Line().right().color(wire).dot(open=True))
    d.pop()
    d.add(elm.Line().up().color(wire))
    d.add(elm.Motor().up().color(wire).label("$E_a$", loc="right"))
    d.add(elm.Resistor().up().color(wire).label("$R_a$", loc="right"))
    Vtp = d.add(elm.Line().right().color(wire).dot(open=True))
    d.add(elm.Line().right().color(wire))
    d.add(elm.Line().down().color(wire))
    d.add(elm.ResistorVar().down().color(wire).label("$R_L$", loc="right"))
    d.add(elm.Line().down().color(wire))
    d.add(elm.Line().left().color(wire))
    d.add(elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(Vtp.end, Vtm.end))


_BUILDERS = {
    "sep_motor":    _build_sep_motor,
    "sep_gen":      _build_sep_gen,
    "shunt_motor":  _build_shunt_motor,
    "shunt_gen":    _build_shunt_gen,
    "series_motor": _build_series_motor,
}


# ─────────────────────────────────────────────────────────────────────────────
# BYTE GENERATOR (cacheable, no Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

def _build_circuit_png_dc(excitation: str, dark: bool) -> bytes:
    import matplotlib
    try:
        matplotlib.use("Agg")
    except Exception:
        pass
    import matplotlib.pyplot as plt
    import schemdraw

    bg_hex = "#0d1117" if dark else "#ffffff"
    wire   = "#ffffff" if dark else "#000000"

    with matplotlib.rc_context({"mathtext.fontset": "dejavusans", "text.usetex": False}):
        fig, ax = plt.subplots(figsize=(9, 4))
        fig.patch.set_facecolor(bg_hex)
        ax.set_facecolor(bg_hex)
        ax.set_axis_off()

        with schemdraw.Drawing(canvas=ax) as d:
            d.config(fontsize=14, color=wire)
            builder = _BUILDERS.get(excitation, _build_sep_motor)
            builder(d, wire)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=180, facecolor=bg_hex, bbox_inches="tight")
        plt.close(fig)

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER (Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

def render_circuit_dc(excitation: str, dark: bool) -> None:
    """Generates and displays DC machine circuit via st.image(bytes) — same pattern as IM."""
    @st.cache_data(show_spinner=False)
    def _cached(exc: str, dk: bool) -> bytes:
        return _build_circuit_png_dc(exc, dk)

    try:
        png_bytes = _cached(excitation, dark)
    except Exception:
        png_bytes = _build_circuit_png_dc(excitation, dark)

    st.image(png_bytes, width="stretch")
