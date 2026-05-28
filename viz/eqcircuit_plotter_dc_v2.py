"""Circuito equivalente MCC — topologia fiel a mcc_desenhos.py + injeção de valores.

Atributos disponíveis em DCMachineParams (use conforme excitação):
  mp.Ra      — resistência de armadura [Ω]
  mp.La      — indutância de armadura [H]
  mp.Rf      — resistência de campo (sep/shunt) [Ω]
  mp.Lf      — indutância de campo (sep/shunt) [H]
  mp.Rs_ser  — resistência série de campo [Ω]  (series_motor)
  mp.Ls_ser  — indutância série de campo [H]   (series_motor)
  mp.Vt      — tensão de armadura [V]
  mp.Vf      — tensão de campo (sep) [V]
  mp.excitation — "sep_motor"|"shunt_motor"|"series_motor"|"sep_gen"|"shunt_gen"

Campos calculados opcionais (use getattr):
  mp.Ea      — fcem nominal [V]
  mp.Ke      — constante de fcem
"""

from __future__ import annotations
import io

# ─────────────────────────────────────────────────────────────────────────────
# TÍTULOS
# ─────────────────────────────────────────────────────────────────────────────

_CIRCUIT_LABELS: dict[str, str] = {
    "sep_motor":    "Excitação Separada — Motor",
    "sep_gen":      "Excitação Separada — Gerador",
    "shunt_motor":  "Shunt (Paralelo) — Motor",
    "shunt_gen":    "Shunt (Paralelo) — Gerador",
    "series_motor": "Série — Motor",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ea_label(mp) -> str:
    Ea = getattr(mp, "Ea", None)
    return f"$E_a$\n{Ea:.1f} V" if Ea is not None else "$E_a$"


# ─────────────────────────────────────────────────────────────────────────────
# BUILDERS — topologia idêntica a mcc_desenhos.py
# ─────────────────────────────────────────────────────────────────────────────

def _build_series_motor(d, wire, mp):
    """Série — motor. Topologia idêntica a mcc_desenhos.py::serie_motor."""
    import schemdraw.elements as elm

    d.push()
    elm.Motor().down().color(wire).label("$E_a$", loc="top")
    elm.Line().right().color(wire)
    elm.Line().right().color(wire)
    elm.Line().right().color(wire)
    T2 = elm.Dot(open=True)
    d.pop()
    Ra_el = elm.Resistor().up().color(wire).label("$R_a$", loc="top").label(f"{mp.Ra:.3f} Ω", loc="bot")
    elm.Line().right().color(wire)
    elm.Line().down().color(wire)
    elm.Inductor().right().color(wire).label("$N_s$", loc="top")
    elm.Line().up().color(wire)
    Rs_ser = getattr(mp, "Rs_ser", 0.0)
    elm.Resistor().right().color(wire).label("$R_s$", loc="top").label(f"{Rs_ser:.3f} Ω", loc="bottom")
    T1 = elm.Dot(open=True)
    elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(T1.end, T2.end)


def _build_shunt_motor(d, wire, mp):
    """Shunt — motor. Topologia idêntica a mcc_desenhos.py::shunt_motor."""
    import schemdraw.elements as elm

    d.push()
    elm.Inductor().right().color(wire).label("$N_f$", loc="top")
    If = elm.Line().up().color(wire)
    elm.Resistor().up().color(wire).label("$R_{fw}$", loc="top").label(f"{mp.Rf:.0f} Ω", loc="bot")
    elm.Line().right().color(wire)
    elm.Line().right().color(wire).dot(open=True)
    d.pop()
    elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="bot")
    elm.Line().right().color(wire)
    elm.Line().right().color(wire)
    elm.Line().right().color(wire).dot(open=True)
    d.push()
    Vtm = elm.Line().right().color(wire).dot(open=True)
    d.pop()
    elm.Line().up().color(wire)
    elm.Motor().up().color(wire).label("$E_a$", loc="top")
    elm.Resistor().up().color(wire).label("$R_a$", loc="top").label(f"{mp.Ra:.3f} Ω", loc="bot")
    Vtp = elm.Line().right().color(wire).dot(open=True)
    elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(Vtp.end, Vtm.end)


def _build_sep_motor(d, wire, mp):
    """Excitação separada — motor. Topologia idêntica a mcc_desenhos.py::sep_motor."""
    import schemdraw.elements as elm

    d.push()
    Rf_el = elm.Inductor().right().color(wire).label("$N_f$", loc="top")
    If = elm.Line().down().color(wire)
    elm.Line().down().color(wire).dot(open=True)
    d.pop()
    d.push()
    elm.Resistor().down().color(wire).label("$R_{fw}$", loc="top").label(f"{mp.Rf:.0f} Ω", loc="bot")
    elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="bot").dot(open=True)
    elm.Gap().right().color(wire).label(("+", "$V_f$", "−"))
    d.pop()
    d.move_from(Rf_el.end, dx=2, dy=0)
    d.push()
    elm.Motor().down().color(wire).label("$E_a$", loc="top")
    elm.Line().down().color(wire)
    Neg = elm.Line().right().color(wire).dot(open=True)
    d.pop()
    elm.Line().up().color(wire)
    elm.Resistor().right().color(wire).label("$R_a$", loc="top").label(f"{mp.Ra:.3f} Ω", loc="bottom").dot(open=True)
    elm.Gap().down().toy(Neg.end).color(wire).label(("+", "$V_t$", "−"))


def _build_sep_gen(d, wire, mp):
    """Excitação separada — gerador. Topologia idêntica a mcc_desenhos.py::sep_gerador."""
    import schemdraw.elements as elm

    d.push()
    Rf_el = elm.Inductor().right().color(wire).label("$N_f$", loc="top")
    If = elm.Line().down().color(wire)
    elm.Line().down().color(wire).dot(open=True)
    d.pop()
    d.push()
    elm.Resistor().down().color(wire).label("$R_{fw}$", loc="top").label(f"{mp.Rf:.0f} Ω", loc="bot")
    elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="bot").dot(open=True)
    elm.Gap().right().color(wire).label(("+", "$V_f$", "−"))
    d.pop()
    d.move_from(Rf_el.end, dx=2, dy=0)
    d.push()
    elm.Motor().down().color(wire).label("$E_a$", loc="top")
    elm.Line().down().color(wire)
    Vtm = elm.Line().right().color(wire).dot(open=True)
    d.pop()
    Ia = elm.Line().up().color(wire)
    Vtp = elm.Resistor().right().color(wire).label("$R_a$", loc="top").label(f"{mp.Ra:.3f} Ω", loc="bottom").dot(open=True)
    elm.Line().right().color(wire)
    elm.Line().down().color(wire)
    elm.ResistorVar().down().color(wire).label("$R_L$", loc="top")
    elm.Line().down().color(wire)
    elm.Line().left().color(wire)
    elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(Vtp.end, Vtm.end)


def _build_shunt_gen(d, wire, mp):
    """Shunt — gerador. Topologia idêntica a mcc_desenhos.py::shunt_gerador."""
    import schemdraw.elements as elm

    d.push()
    elm.Inductor().right().color(wire).label("$N_f$", loc="top")
    If = elm.Line().up().color(wire)
    elm.Resistor().up().color(wire).label("$R_{fw}$", loc="top").label(f"{mp.Rf:.0f} Ω", loc="bot")
    elm.Line().right().color(wire)
    elm.Line().right().color(wire)
    elm.Line().right().color(wire).dot(open=True)
    d.pop()
    elm.ResistorVar().down().color(wire).label("$R_{fc}$", loc="bot")
    elm.Line().right().color(wire)
    elm.Line().right().color(wire)
    elm.Line().right().color(wire).dot(open=True)
    d.push()
    Vtm = elm.Line().right().color(wire).dot(open=True)
    d.pop()
    elm.Line().up().color(wire)
    elm.Motor().up().color(wire).label("$E_a$", loc="top")
    elm.Resistor().up().color(wire).label("$R_a$", loc="top").label(f"{mp.Ra:.3f} Ω", loc="bot")
    Vtp = elm.Line().right().color(wire).dot(open=True)
    elm.Line().right().color(wire)
    elm.Line().down().color(wire)
    elm.ResistorVar().down().color(wire).label("$R_L$", loc="top")
    elm.Line().down().color(wire)
    elm.Line().left().color(wire)
    elm.Gap().down().color(wire).label(("+", "$V_t$", "−")).endpoints(Vtp.end, Vtm.end)


_BUILDERS = {
    "sep_motor":    _build_sep_motor,
    "sep_gen":      _build_sep_gen,
    "shunt_motor":  _build_shunt_motor,
    "shunt_gen":    _build_shunt_gen,
    "series_motor": _build_series_motor,
}


# ─────────────────────────────────────────────────────────────────────────────
# GERADOR DE BYTES (cacheável, sem Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

def build_circuit_png_dc(mp, dark: bool) -> bytes:
    import matplotlib
    try:
        matplotlib.use("Agg")
    except Exception:
        pass
    import matplotlib.pyplot as plt
    import schemdraw

    bg_hex = "#0d1117" if dark else "#ffffff"
    wire   = "#ffffff" if dark else "#000000"
    text_c = "#ffffff" if dark else "#000000"

    with matplotlib.rc_context({"mathtext.fontset": "dejavusans", "text.usetex": False}):
        fig, ax = plt.subplots()
        fig.patch.set_facecolor(bg_hex)
        ax.set_facecolor(bg_hex)
        ax.set_axis_off()
        ax.set_title(_CIRCUIT_LABELS.get(mp.excitation, mp.excitation), color=text_c, fontsize=13, pad=8)

        with schemdraw.Drawing(canvas=ax) as d:
            d.config(unit=2, fontsize=13, color=wire)
            builder = _BUILDERS.get(mp.excitation, _build_sep_motor)
            builder(d, wire, mp)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=bg_hex, bbox_inches="tight")
        plt.close(fig)

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER (Streamlit) — substitui render_circuit_dc() após integração
# ─────────────────────────────────────────────────────────────────────────────

def render_circuit_dc_v2(mp, dark: bool) -> None:
    import streamlit as st

    @st.cache_data(show_spinner=False)
    def _cached(excitation: str, Ra: float, La: float, Rf: float, Lf: float,
                Vt: float, Vf: float, dk: bool) -> bytes:
        return build_circuit_png_dc(mp, dk)

    try:
        Vf = getattr(mp, "Vf", 0.0)
        Rf = getattr(mp, "Rf", 0.0)
        Lf = getattr(mp, "Lf", 0.0)
        png = _cached(mp.excitation, mp.Ra, mp.La, Rf, Lf, mp.Vt, Vf, dark)
    except Exception:
        png = build_circuit_png_dc(mp, dark)

    st.image(png, width="stretch")


# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW LOCAL — python viz/eqcircuit_plotter_dc_v2.py [excitation|all] [dark]
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import sys
    import time
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import schemdraw
    from types import SimpleNamespace

    _EXC_ALL = ["sep_motor", "shunt_motor", "series_motor", "sep_gen", "shunt_gen"]

    exc  = sys.argv[1] if len(sys.argv) > 1 else "sep_motor"
    dark = (sys.argv[2].lower() == "true") if len(sys.argv) > 2 else False

    if exc == "all":
        targets = _EXC_ALL
    elif exc in _EXC_ALL:
        targets = [exc]
    else:
        print(f"Excitação inválida. Opções: {_EXC_ALL + ['all']}")
        sys.exit(1)

    mp_mock = SimpleNamespace(
        Ra=0.850,   La=0.012,
        Rf=180.0,   Lf=8.50,
        Rs_ser=0.3, Ls_ser=0.05,
        Vt=220.0,   Vf=220.0,
        Ea=195.0,   Ke=1.85,
    )

    THIS_FILE = os.path.abspath(__file__)

    def _draw(figs: list):
        for f in figs:
            plt.close(f)
        figs.clear()

        bg_hex = "#0d1117" if dark else "#ffffff"
        wire   = "#ffffff" if dark else "#000000"
        text_c = "#ffffff" if dark else "#000000"

        for exc_type in targets:
            mp_mock.excitation = exc_type
            with matplotlib.rc_context({"mathtext.fontset": "dejavusans", "text.usetex": False}):
                fig, ax = plt.subplots(figsize=(9, 4), num=exc_type)
                fig.patch.set_facecolor(bg_hex)
                ax.set_facecolor(bg_hex)
                ax.set_axis_off()
                ax.set_title(_CIRCUIT_LABELS.get(exc_type, exc_type), color=text_c, fontsize=13, pad=8)
                with schemdraw.Drawing(canvas=ax) as d:
                    d.config(unit=2, fontsize=13, color=wire)
                    builder = _BUILDERS.get(exc_type, _build_sep_motor)
                    builder(d, wire, mp_mock)
                figs.append(fig)

        plt.pause(0.05)
        print(f"[preview] atualizado — {time.strftime('%H:%M:%S')}")

    figs: list = []
    _draw(figs)
    last_mtime = os.stat(THIS_FILE).st_mtime

    print("[preview] monitorando alterações — feche a janela para sair")
    while plt.get_fignums():
        plt.pause(0.5)
        try:
            mtime = os.stat(THIS_FILE).st_mtime
        except FileNotFoundError:
            break
        if mtime != last_mtime:
            last_mtime = mtime
            import importlib
            import viz.eqcircuit_plotter_dc_v2 as _self
            importlib.reload(_self)
            globals().update({k: getattr(_self, k) for k in ("_BUILDERS", "_CIRCUIT_LABELS")})
            _draw(figs)
