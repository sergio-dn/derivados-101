"""UI de los temas (una pregunta por página, ej. "¿Qué es un forward?"): pantallas cortas en serie.

Recorre ``derivados101.curso.CHAPTERS`` y dibuja una pantalla a la vez (concepto, ejemplo,
demo interactiva o ideas clave) con botones Anterior / Siguiente. El contenido vive en
``curso/cap1.py`` … ``cap6.py``; acá solo hay presentación y gráficos.

Estado (``st.session_state``, claves no-widget, sobreviven al cambio de página):
- ``tema:<slug>:idx``               pantalla actual del tema.
- ``tema:<slug>:<i>:res``           resultado del último "Revisar" del ejercicio i (True/False).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import get_logger
from .curso import CHAPTERS, Chapter, Chart, Choice, Concept, Example, Numeric, Screen, Summary
from .curso.model import Demo
from .ui import PALETTE, disclaimer, fmt_clp, fmt_num, fmt_pct, fmt_rate, md_clp, md_usd, style_fig, vline

log = get_logger(__name__)

QUIZ_PATH = "app_pages/6_Quiz.py"

# Valores del caso ancla (ejemplo fijo): spot 890, 5,11% CLP / 4,07% USD, 1 año -> 898,89.
DEFAULTS = {"spot": 890.0, "r_dom": 0.0511, "r_for": 0.0407, "years": 1.0, "notional_usd": 500_000.0,
            "vol": 0.12}

KIND_BADGE = {
    "concept": ":blue-badge[:material/lightbulb: Concepto]",
    "example": ":orange-badge[:material/calculate: Ejemplo]",
    "choice": ":green-badge[:material/edit: Ejercicio]",
    "numeric": ":green-badge[:material/edit: Ejercicio]",
    "demo": ":green-badge[:material/touch_app: Pruébalo]",
    "summary": ":violet-badge[:material/check_circle: Ideas clave]",
}


# ---------------------------------------------------------------- páginas


def page_title(ch: Chapter) -> str:
    """Nombre del tema en el menú: corto ("Forward"); la página muestra la pregunta completa."""
    return ch.menu or ch.title


def _renderer(ch: Chapter) -> Callable[[], None]:
    def render() -> None:
        render_chapter(ch)

    # st.Page infiere el nombre desde __name__; se fija uno único y legible por tema.
    render.__name__ = ch.slug.replace("-", "_")
    return render


def chapter_page(ch: Chapter):
    """st.Page del tema. El hash de página sale del url_path (slug), así que crear la misma
    página en otro lugar (para st.page_link / st.switch_page) apunta al mismo registro."""
    return st.Page(_renderer(ch), title=page_title(ch), icon=ch.icon, url_path=ch.slug)


def chapter_pages() -> list:
    return [chapter_page(ch) for ch in CHAPTERS]


def _next_chapter(ch: Chapter) -> Chapter | None:
    slugs = [c.slug for c in CHAPTERS]
    if ch.slug not in slugs:
        return None  # tema suelto (tests): sin "siguiente"
    idx = slugs.index(ch.slug)
    return CHAPTERS[idx + 1] if idx + 1 < len(CHAPTERS) else None


# ---------------------------------------------------------------- estado


def _key(ch: Chapter, *parts: object) -> str:
    return ":".join(["tema", ch.slug, *map(str, parts)])


def current_index(ch: Chapter) -> int:
    idx = int(st.session_state.get(_key(ch, "idx"), 0))
    return min(max(idx, 0), len(ch.screens) - 1)


def _go(ch: Chapter, idx: int) -> None:
    st.session_state[_key(ch, "idx")] = idx


def _clear_result(ch: Chapter, i: int) -> None:
    st.session_state.pop(_key(ch, i, "res"), None)


# ---------------------------------------------------------------- render del tema


def render_chapter(ch: Chapter) -> None:
    """Dibuja el tema: encabezado, "k de n", la pantalla actual y la navegación."""
    st.set_page_config(page_title=f"{page_title(ch)} · Derivados 101", page_icon=ch.icon, layout="centered")
    n = len(ch.screens)
    idx = current_index(ch)

    st.title(ch.title, anchor=False)
    if ch.goal:
        st.markdown(f":gray[{ch.goal}]")
    st.progress((idx + 1) / n, text=f"{idx + 1} de {n}")

    screen = ch.screens[idx]
    with st.container(border=True):
        render_screen(ch, idx, screen)

    _nav(ch, idx)
    disclaimer()


def _nav(ch: Chapter, idx: int) -> None:
    n = len(ch.screens)
    nxt = _next_chapter(ch)
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.button("Anterior", icon=":material/arrow_back:", key=_key(ch, "prev"), disabled=idx == 0,
                  on_click=_go, args=(ch, idx - 1))
        if idx + 1 < n:
            st.button("Siguiente", icon=":material/arrow_forward:", icon_position="right", type="primary",
                      key=_key(ch, "next"), on_click=_go, args=(ch, idx + 1))
        elif nxt is not None:
            if st.button(f"Siguiente: {nxt.title}", icon=":material/arrow_forward:", icon_position="right",
                         type="primary", key=_key(ch, "next_ch")):
                st.switch_page(chapter_page(nxt))
        else:
            if st.button("Ir al quiz", icon=":material/quiz:", icon_position="right", type="primary",
                         key=_key(ch, "to_quiz")):
                st.switch_page(QUIZ_PATH)


def render_screen(ch: Chapter, i: int, screen: Screen) -> None:
    st.markdown(KIND_BADGE[screen.kind])
    if isinstance(screen, Concept):
        _concept(screen)
    elif isinstance(screen, Example):
        _example(screen)
    elif isinstance(screen, Demo):
        render_demo(ch, i, screen)
    elif isinstance(screen, Choice):
        _choice(ch, i, screen)
    elif isinstance(screen, Numeric):
        _numeric(ch, i, screen)
    elif isinstance(screen, Summary):
        _summary(ch, screen)


def _concept(s: Concept) -> None:
    st.subheader(s.title, anchor=False)
    st.markdown(s.body)
    if s.terms:
        st.markdown("\n".join(f"- **{term}:** {definition}" for term, definition in s.terms))
    if s.chart:
        render_chart(s.chart)
    if s.callout:
        st.warning(_strip_ojo(s.callout), title="Ojo", icon=":material/visibility:")


def _strip_ojo(text: str) -> str:
    """El recuadro ya se titula "Ojo": quita un "Ojo:" inicial del contenido para no repetirlo."""
    body = re.sub(r"^\s*\**ojo\**\s*[:.,]\s*\**\s*", "", text, flags=re.IGNORECASE)
    return body[:1].upper() + body[1:] if body else text


def _example(s: Example) -> None:
    st.subheader(s.title, anchor=False)
    st.markdown(s.setup)
    st.markdown("\n".join(f"{k}. {step}" for k, step in enumerate(s.steps, start=1)))
    if s.chart:
        render_chart(s.chart)
    st.success(s.takeaway, icon=":material/check_circle:")
    if s.lab:
        try:
            st.page_link(s.lab, label="Pruébalo en el simulador", icon=":material/science:")
        except Exception:  # noqa: BLE001 - st.page_link exige st.navigation; fuera de ella se omite
            pass


def _feedback(ok: bool, explanation: str) -> None:
    if ok:
        st.success(f"**Correcto.** {explanation}", icon=":material/check_circle:")
    else:
        st.error(f"**No es esa.** {explanation}", icon=":material/cancel:")


def _choice(ch: Chapter, i: int, s: Choice) -> None:
    st.subheader(s.question, anchor=False)
    widget = _key(ch, i, "w")
    choice = st.radio("Elige una alternativa", options=range(len(s.options)), format_func=lambda k: s.options[k],
                      index=None, key=widget, label_visibility="collapsed", on_change=_clear_result, args=(ch, i))
    res_key = _key(ch, i, "res")
    if st.button("Revisar", icon=":material/fact_check:", key=_key(ch, i, "check"), disabled=choice is None):
        st.session_state[res_key] = choice == s.answer
    if res_key in st.session_state:
        _feedback(st.session_state[res_key], s.explanation)


def _numeric(ch: Chapter, i: int, s: Numeric) -> None:
    st.subheader(s.question, anchor=False)
    widget = _key(ch, i, "w")
    step = 10.0 ** -s.decimals if s.decimals > 0 else 1.0
    value = st.number_input(
        f"Tu respuesta ({s.unit})", value=None, step=step, format=f"%.{max(s.decimals, 0)}f", key=widget,
        placeholder="Escribe un número", on_change=_clear_result, args=(ch, i),
    )
    st.caption("Sin separador de miles; usa punto para los decimales (ej. 898.89).")
    if s.hint:
        with st.expander("Pista", icon=":material/help:"):
            st.markdown(s.hint)
    res_key = _key(ch, i, "res")
    if st.button("Revisar", icon=":material/fact_check:", key=_key(ch, i, "check"), disabled=value is None):
        st.session_state[res_key] = is_close(value, s.answer, s.tolerance)
    if res_key in st.session_state:
        _feedback(st.session_state[res_key], s.explanation)


def is_close(value: float | None, answer: float, tolerance: float) -> bool:
    """Respuesta numérica dentro de la tolerancia absoluta (con holgura por redondeo binario)."""
    return value is not None and abs(float(value) - answer) <= tolerance + 1e-9


def _summary(ch: Chapter, s: Summary) -> None:
    st.subheader("Para llevarte", anchor=False)
    st.markdown("\n".join(f"{k}. {p}" for k, p in enumerate(s.points, start=1)))
    if s.next_hint:
        st.info(s.next_hint, icon=":material/arrow_forward:")


# ---------------------------------------------------------------- gráficos


def render_chart(chart: Chart) -> None:
    """Dibuja un gráfico del modelo. Si falla (parámetros raros), avisa sin romper la pantalla."""
    try:
        fig = chart_figure(chart)
    except Exception:  # noqa: BLE001 - un gráfico malo no debe tumbar la pantalla; los tests lo cubren
        log.exception("No se pudo dibujar el gráfico %s", chart.name)
        st.caption(":material/warning: No se pudo dibujar este gráfico.")
        return
    if not fig.layout.title.text:
        fig.update_layout(margin=dict(t=20))  # sin título, el margen reservado queda como hueco
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    if chart.caption:
        st.caption(chart.caption)


def _p(params: dict, name: str) -> float:
    return float(params.get(name, DEFAULTS[name]))


def chart_figure(chart: Chart) -> go.Figure:
    """Construye la figura Plotly de un ``Chart`` usando el núcleo. Parámetros faltantes = caso ancla."""
    builders: dict[str, Callable[[dict], go.Figure]] = {
        "usdclp_history": _fig_usdclp_history,
        "forward_points": _fig_forward_points,
        "forward_payoff": _fig_forward_payoff,
        "hedge_compare": _fig_hedge_compare,
        "option_payoff": _fig_option_payoff,
        "strategy_payoff": _fig_strategy_payoff,
        "hedge_backtest": _fig_hedge_backtest,
    }
    return builders[chart.name](chart.params or {})


@st.cache_data(show_spinner=False)
def _usdclp() -> pd.DataFrame:
    from .market import load_usdclp

    return load_usdclp()


def _fig_usdclp_history(params: dict) -> go.Figure:
    df = _usdclp()
    years = float(params.get("years", 3))
    cutoff = df["date"].max() - timedelta(days=round(years * 365))
    df = df[df["date"] >= cutoff]
    fig = go.Figure(go.Scatter(x=df["date"], y=df["usdclp"], mode="lines", name="Dólar observado",
                               line=dict(color=PALETTE["primary"], width=2),
                               hovertemplate="%{y:,.2f} CLP por USD<extra></extra>"))
    return style_fig(fig, x_title=None, y_title="CLP por USD", height=340)


def _fig_forward_points(params: dict) -> go.Figure:
    from .forward import forward_rate

    spot, r_dom, r_for = _p(params, "spot"), _p(params, "r_dom"), _p(params, "r_for")
    t = np.linspace(0, 2, 49)
    fwd = np.array([forward_rate(spot, r_dom, r_for, x) for x in t])
    fig = go.Figure(go.Scatter(x=t, y=fwd, mode="lines", name="Forward", customdata=fwd - spot,
                               line=dict(color=PALETTE["primary"], width=2.5),
                               hovertemplate="Plazo %{x:.2f} años<br>Forward %{y:,.2f}"
                                             "<br>Puntos %{customdata:,.2f}<extra></extra>"))
    fig.add_hline(y=spot, line_dash="dot", line_color=PALETTE["neutral"], line_width=1,
                  annotation_text=f"Spot {fmt_rate(spot)}", annotation_position="bottom right")
    f1 = forward_rate(spot, r_dom, r_for, 1.0)
    fig.add_trace(go.Scatter(x=[1.0], y=[f1], mode="markers+text", name="A 1 año",
                             marker=dict(color=PALETTE["secondary"], size=10),
                             text=[f"{fmt_rate(f1)}"], textposition="top left", hoverinfo="skip"))
    fig.update_layout(hovermode="closest", showlegend=False)
    return style_fig(fig, x_title="Plazo (años)", y_title="CLP por USD", height=340)


def _settle_grid(center: float, pct: float = 0.15, n: int = 121) -> np.ndarray:
    return np.linspace(center * (1 - pct), center * (1 + pct), n)


def _fig_forward_payoff(params: dict) -> go.Figure:
    from .forward import forward_rate

    spot = _p(params, "spot")
    k = float(params.get("forward", forward_rate(spot, DEFAULTS["r_dom"], DEFAULTS["r_for"], 1.0)))
    side = params.get("side", "buy")
    n = _p(params, "notional_usd")
    s = _settle_grid(k)
    comp = (s - k) * n if side == "buy" else (k - s) * n  # positivo = la empresa RECIBE
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s, y=np.where(comp >= 0, comp, np.nan) / 1e6, mode="lines", name="La empresa recibe",
                             line=dict(color=PALETTE["accent"], width=2.5)))
    fig.add_trace(go.Scatter(x=s, y=np.where(comp <= 0, comp, np.nan) / 1e6, mode="lines", name="La empresa paga",
                             line=dict(color=PALETTE["negative"], width=2.5)))
    vline(fig, k, f"Forward {fmt_rate(k)}")
    fig.update_traces(hovertemplate="Dólar al vencer %{x:,.2f}<br>%{y:,.1f} millones CLP<extra></extra>")
    fig.update_layout(hovermode="closest")
    return style_fig(fig, x_title="Dólar al vencimiento (CLP por USD)", y_title="Compensación (millones CLP)",
                     height=360)


def _fig_hedge_compare(params: dict) -> go.Figure:
    from .forward import forward_rate

    spot = _p(params, "spot")
    k = float(params.get("forward", forward_rate(spot, DEFAULTS["r_dom"], DEFAULTS["r_for"], 1.0)))
    side = params.get("side", "buy")
    n = _p(params, "notional_usd")
    s = _settle_grid(spot, 0.2)
    word = "Costo" if side == "buy" else "Ingreso"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s, y=s * n / 1e6, mode="lines", name=f"{word} sin cobertura",
                             line=dict(color=PALETTE["secondary"], width=2.5)))
    fig.add_trace(go.Scatter(x=s, y=np.full_like(s, k * n) / 1e6, mode="lines", name=f"{word} con forward",
                             line=dict(color=PALETTE["primary"], width=2.5)))
    vline(fig, spot, f"Spot hoy {fmt_rate(spot)}", position="top left")
    fig.update_traces(hovertemplate="%{y:,.1f} millones CLP<extra></extra>")
    return style_fig(fig, x_title="Dólar al vencimiento (CLP por USD)", y_title=f"{word} (millones CLP)",
                     height=360)


def _fig_option_payoff(params: dict) -> go.Figure:
    from .options import OptionLeg, leg_payoff, leg_pnl

    kind = params.get("kind", "call")
    position = params.get("position", "long")
    strike = float(params.get("strike", DEFAULTS["spot"]))
    premium = float(params.get("premium", 0.0))
    spot = float(params.get("spot", strike))
    leg = OptionLeg(kind=kind, position=position, strike=strike, premium=premium)
    s = _settle_grid(spot, 0.2, 161)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s, y=leg_payoff(leg, s), mode="lines", name="Pago al vencimiento (sin prima)",
                             line=dict(color=PALETTE["neutral"], width=1.5, dash="dash")))
    fig.add_trace(go.Scatter(x=s, y=leg_pnl(leg, s), mode="lines", name="Resultado (con prima)",
                             line=dict(color=PALETTE["primary"], width=2.5)))
    vline(fig, strike, f"Strike {fmt_rate(strike)}")
    fig.update_traces(hovertemplate="%{y:,.2f} CLP por USD<extra></extra>")
    return style_fig(fig, x_title="Dólar al vencimiento (CLP por USD)", y_title="CLP por USD de nocional",
                     height=360)


@st.cache_data(show_spinner=False)
def _strategy_frame(preset: str, spot: float, vol: float, years: float, r_dom: float, r_for: float):
    from .strategies import PRESETS, net_premium, spot_grid, strategy_pnl

    p = PRESETS[preset]
    legs = p.build(spot, vol, years, r_dom, r_for)
    df = strategy_pnl(legs, spot_grid(spot, 0.2, 161), exposure=p.suggested_exposure, spot0=spot)
    return df, p.name, p.suggested_exposure, net_premium(legs)


def _fig_strategy_payoff(params: dict) -> go.Figure:
    df, name, exposure, _prem = _strategy_frame(
        params.get("preset", "collar_importer"), _p(params, "spot"), _p(params, "vol"), _p(params, "years"),
        _p(params, "r_dom"), _p(params, "r_for"),
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["spot"], y=df["options_pnl"], mode="lines", name="Opciones",
                             line=dict(color=PALETTE["primary"], width=2)))
    if exposure != "none":
        label = "Negocio sin cubrir (importador)" if exposure == "short_usd" else "Negocio sin cubrir (exportador)"
        fig.add_trace(go.Scatter(x=df["spot"], y=df["underlying_pnl"], mode="lines", name=label,
                                 line=dict(color=PALETTE["secondary"], width=1.5, dash="dash")))
        fig.add_trace(go.Scatter(x=df["spot"], y=df["combined_pnl"], mode="lines", name="Negocio + opciones",
                                 line=dict(color=PALETTE["accent"], width=3)))
    vline(fig, _p(params, "spot"), f"Spot {fmt_rate(_p(params, 'spot'))}")
    fig.update_traces(hovertemplate="%{y:,.2f} CLP por USD<extra></extra>")
    fig.update_layout(title=dict(text=name))
    return style_fig(fig, x_title="Dólar al vencimiento (CLP por USD)", y_title="Resultado (CLP por USD)",
                     height=380)


@st.cache_data(show_spinner=False)
def _backtest_series(years: float, nominal_usd: float) -> pd.DataFrame:
    """Backtest mensual: un importador que cada inicio de mes fija un forward a ``years`` años."""
    from .market import hedge_backtest

    df = _usdclp()
    last = df["date"].max()
    first = df["date"].min().normalize().replace(day=1)  # inicio de mes: incluye enero 2024
    starts = pd.date_range(first, last - timedelta(days=round(years * 365)), freq="MS")
    rows = []
    for start in starts:
        try:
            bt = hedge_backtest(df, start.date(), years, nominal_usd)
        except ValueError:
            continue
        rows.append({"start": bt["start_date"], "fwd": bt["fwd_rate"], "spot_end": bt["spot_end"], **bt})
    return pd.DataFrame(rows)


def _fig_hedge_backtest(params: dict) -> go.Figure:
    years = float(params.get("years", 1.0))
    data = _backtest_series(years, float(params.get("nominal_usd", DEFAULTS["notional_usd"])))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["start"], y=data["spot_end"], mode="lines+markers",
                             name="Sin cobertura: dólar al pagar", line=dict(color=PALETTE["secondary"], width=2)))
    fig.add_trace(go.Scatter(x=data["start"], y=data["fwd"], mode="lines+markers",
                             name="Con forward: dólar fijado", line=dict(color=PALETTE["primary"], width=2)))
    fig.update_traces(hovertemplate="%{y:,.2f} CLP por USD<extra></extra>")
    plazo = fmt_num(years, 0 if years == int(years) else 1)
    unit = "año" if years == 1 else "años"
    return style_fig(fig, x_title=f"Mes en que se fija la cobertura (plazo: {plazo} {unit})",
                     y_title="CLP por USD pagado", height=360)


# ---------------------------------------------------------------- demos ("Pruébalo")
#
# Cada demo es una slide viva: controles arriba, el número clave grande (st.metric) y un gráfico
# que reacciona. Verde = la empresa recibe / le conviene; rojo = paga / le cuesta. Todas las
# cuentas salen del núcleo. Las keys de widgets son únicas por tema + pantalla: tema:<slug>:<i>:<x>.

# Parámetros que acepta cada demo (los tests validan que el contenido use solo estos).
DEMO_PARAMS: dict[str, set[str]] = {
    "dollar_move": {"spot", "notional_usd", "side"},
    "forward_calc": {"spot", "r_dom", "r_for", "years"},
    "forward_settlement": {"forward", "spot_T", "side", "notional_usd"},
    "forward_vs_none": {"spot", "forward", "notional_usd"},
    "mtm": {"forward", "market_forward", "notional_usd", "credit_line_clp", "side"},
    "option_payoff": {"kind", "position", "strike", "premium", "spot"},
    "option_price": {"kind", "spot", "strike", "vol", "years", "r_dom", "r_for"},
    "collar": {"spot", "vol", "years", "r_dom", "r_for", "call_strike"},
    "hedge_ratio": {"spot", "forward", "notional_usd"},
    "backtest": {"years", "nominal_usd"},
}

_GOOD, _BAD = "good", "bad"


def render_demo(ch: Chapter, i: int, s: Demo) -> None:
    """Dibuja una pantalla Demo: título, qué probar, controles, métricas y gráfico."""
    st.subheader(s.title, anchor=False)
    st.markdown(s.prompt)
    builders: dict[str, Callable[[Callable[[str], str], dict], None]] = {
        "dollar_move": _demo_dollar_move,
        "forward_calc": _demo_forward_calc,
        "forward_settlement": _demo_forward_settlement,
        "forward_vs_none": _demo_forward_vs_none,
        "mtm": _demo_mtm,
        "option_payoff": _demo_option_payoff,
        "option_price": _demo_option_price,
        "collar": _demo_collar,
        "hedge_ratio": _demo_hedge_ratio,
        "backtest": _demo_backtest,
    }

    def key(name: str) -> str:
        return _key(ch, i, name)

    builders[s.demo](key, s.params or {})
    if s.takeaway:
        st.info(s.takeaway, icon=":material/visibility:")


def _metrics(*items: tuple) -> None:
    """Fila de métricas de igual alto. Cada item: (label, value[, tone[, nota]]); tone 'good'/'bad'/None."""
    with st.container(horizontal=True):
        for item in items:
            label, value, tone, note = (*item, None, None)[:4]
            kwargs: dict = {}
            if note:
                color, arrow = {_GOOD: ("green", "up"), _BAD: ("red", "down")}.get(tone, ("gray", "off"))
                kwargs = {"delta": note, "delta_color": color, "delta_arrow": arrow}
            st.metric(label, value, border=True, height="stretch", **kwargs)


def _plot(fig: go.Figure) -> None:
    if not fig.layout.title.text:
        fig.update_layout(margin=dict(t=20))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _dot(fig: go.Figure, x: float, y: float, color: str, text: str | None = None) -> None:
    """Punto que marca dónde está el control ahora."""
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text" if text else "markers", showlegend=False,
                             marker=dict(color=color, size=12, line=dict(color="white", width=2)),
                             text=[text] if text else None, textposition="top center", hoverinfo="skip"))


def _mm(value: float) -> str:
    """Millones de pesos con un decimal: '$12,3 MM'."""
    return f"{fmt_clp(value / 1e6, 1)} MM"


def _spot_slider(label: str, key: str, center: float, value: float, pct: float = 0.2) -> float:
    lo, hi = float(round(center * (1 - pct))), float(round(center * (1 + pct)))
    return st.slider(label, min_value=lo, max_value=hi, value=float(min(max(value, lo), hi)), step=1.0,
                     format="%.0f", key=key)


# --- 1. dólar que se mueve


def _demo_dollar_move(key, p: dict) -> None:
    spot, n = _p(p, "spot"), _p(p, "notional_usd")
    importer = p.get("side", "importer") == "importer"
    s_t = _spot_slider("Dólar el día de pago (CLP por USD)", key("spot_T"), spot, spot)
    today, then = n * spot, n * s_t
    diff = then - today
    if importer:
        tone = _BAD if diff > 0 else _GOOD if diff < 0 else None
        note = "pagas más" if diff > 0 else "pagas menos" if diff < 0 else "igual que hoy"
        label = "Pesos a pagar"
    else:
        tone = _GOOD if diff > 0 else _BAD if diff < 0 else None
        note = "recibes más" if diff > 0 else "recibes menos" if diff < 0 else "igual que hoy"
        label = "Pesos a recibir"
    _metrics((label, fmt_clp(then)), ("Diferencia contra hoy", fmt_clp(diff), tone, note))
    grid = _settle_grid(spot, 0.2)
    fig = go.Figure(go.Scatter(x=grid, y=grid * n / 1e6, mode="lines", name=label,
                               line=dict(color=PALETTE["secondary"], width=2.5),
                               hovertemplate="%{y:,.1f} millones CLP<extra></extra>"))
    fig.add_hline(y=today / 1e6, line_dash="dot", line_color=PALETTE["neutral"], line_width=1,
                  annotation_text=f"Con el dólar de hoy ({fmt_rate(spot, 0)})", annotation_position="top left")
    _dot(fig, s_t, then / 1e6, PALETTE["negative" if tone == _BAD else "accent" if tone == _GOOD else "neutral"])
    fig.update_layout(showlegend=False, hovermode="closest")
    _plot(style_fig(fig, x_title="Dólar el día de pago (CLP por USD)", y_title="Millones de CLP", height=320))


# --- 2. cómo se calcula el forward


def _demo_forward_calc(key, p: dict) -> None:
    from .forward import forward_points, forward_rate

    spot = _p(p, "spot")
    with st.container(horizontal=True, gap="medium"):
        r_dom = st.slider("Tasa en pesos (%)", 0.0, 12.0, round(_p(p, "r_dom") * 100, 2), 0.01, format="%.2f%%",
                          key=key("r_dom")) / 100
        r_for = st.slider("Tasa en dólares (%)", 0.0, 12.0, round(_p(p, "r_for") * 100, 2), 0.01, format="%.2f%%",
                          key=key("r_for")) / 100
        years = st.slider("Plazo (años)", 0.25, 2.0, float(_p(p, "years")), 0.25, format="%.2f",
                          key=key("years"))
    fwd = forward_rate(spot, r_dom, r_for, years)
    pts = forward_points(spot, fwd)
    _metrics(("Spot hoy", fmt_rate(spot)), ("Forward", fmt_rate(fwd)),
             ("Puntos forward", fmt_num(pts, 2), None, "forward − spot"))
    fig = _fig_forward_points({"spot": spot, "r_dom": r_dom, "r_for": r_for})
    fig.data = fig.data[:1]  # sin el punto fijo a 1 año: el punto lo marca el plazo elegido
    _dot(fig, years, fwd, PALETTE["secondary"], fmt_rate(fwd))
    _plot(fig)


# --- 3. liquidación de un forward


_SIDE_LABEL = {"buy": "Compra USD (importador)", "sell": "Vende USD (exportador)"}


def _side_control(key: str, default: str) -> str:
    side = st.segmented_control("Contrato", options=list(_SIDE_LABEL), default=default, format_func=_SIDE_LABEL.get,
                                key=key, required=True)
    return side or default


def _demo_forward_settlement(key, p: dict) -> None:
    from .forward import settle_forward

    k, n = _p_fwd(p), _p(p, "notional_usd")
    side = _side_control(key("side"), p.get("side", "buy"))
    s_t = _spot_slider("Dólar al vencimiento (CLP por USD)", key("spot_T"), k, float(p.get("spot_T", k)), 0.15)
    st_ = settle_forward(n, k, s_t, side=side)
    c = st_.compensation_clp
    tone = _GOOD if c > 0 else _BAD if c < 0 else None
    note = "el banco te paga" if c > 0 else "tú pagas al banco" if c < 0 else "nadie paga"
    verb = "pagas" if side == "buy" else "recibes"
    _metrics(("Compensación", fmt_clp(c), tone, note),
             (f"Si fuera entrega física, {verb}", fmt_clp(st_.full_delivery_clp), None, f"US${fmt_num(n)} a {fmt_rate(k)}"))
    fig = _fig_forward_payoff({"spot": k, "forward": k, "side": side, "notional_usd": n})
    _dot(fig, s_t, c / 1e6, PALETTE["accent" if c >= 0 else "negative"])
    _plot(fig)


def _p_fwd(p: dict) -> float:
    from .forward import forward_rate

    if "forward" in p:
        return float(p["forward"])
    return forward_rate(_p(p, "spot"), DEFAULTS["r_dom"], DEFAULTS["r_for"], DEFAULTS["years"])


# --- 4. con forward vs sin cubrirse


def _demo_forward_vs_none(key, p: dict) -> None:
    spot, k, n = _p(p, "spot"), _p_fwd(p), _p(p, "notional_usd")
    s_t = _spot_slider("Dólar al vencimiento (CLP por USD)", key("spot_T"), spot, spot)
    none, hedged = n * s_t, n * k
    diff = none - hedged
    tone = _GOOD if diff > 0 else _BAD if diff < 0 else None
    note = "el forward te ahorró" if diff > 0 else "sin cubrirte pagabas menos" if diff < 0 else "da lo mismo"
    _metrics(("Costo sin cubrirse", fmt_clp(none)), ("Costo con forward", fmt_clp(hedged)),
             ("Diferencia", fmt_clp(abs(diff)), tone, note))
    fig = _fig_hedge_compare({"spot": spot, "forward": k, "notional_usd": n, "side": "buy"})
    _dot(fig, s_t, none / 1e6, PALETTE["secondary"])
    _dot(fig, s_t, hedged / 1e6, PALETTE["primary"])
    _plot(fig)


# --- 5. MtM y garantías


def _demo_mtm(key, p: dict) -> None:
    from .forward import forward_mtm

    k, n = _p_fwd(p), _p(p, "notional_usd")
    line = float(p.get("credit_line_clp", 10_000_000))
    side = p.get("side", "buy")
    lo, hi = float(round(k * 0.9)), float(round(k * 1.1))
    f_mkt = st.slider("Forward de mercado hoy (CLP por USD)", lo, hi, float(min(max(p.get("market_forward", k), lo), hi)),
                      0.01, format="%.2f", key=key("market_forward"))
    # Simplificación didáctica: MtM = N × (forward de mercado − pactado), sin descontar (tasas 0, plazo 0).
    mtm = forward_mtm(n, k, f_mkt, 0.0, 0.0, 0.0, side=side)
    against = max(-mtm, 0.0)
    used = min(against / line, 1.0) if line > 0 else 1.0
    margin = max(against - line, 0.0)  # sin colchón: todo lo que pasa la línea se pide como garantía
    _metrics(
        ("MtM para la empresa", fmt_clp(mtm), _GOOD if mtm > 0 else _BAD if mtm < 0 else None,
         "a favor" if mtm > 0 else "en contra" if mtm < 0 else "neutro"),
        ("Línea de crédito usada", fmt_pct(used, 0), _BAD if used >= 1 else None, f"línea de {fmt_clp(line)}"),
        ("Garantía que pide el banco", fmt_clp(margin), _BAD if margin > 0 else _GOOD,
         "sale caja hoy" if margin > 0 else "no sale caja"),
    )
    grid = np.linspace(lo, hi, 161)
    vals = np.array([forward_mtm(n, k, x, 0.0, 0.0, 0.0, side=side) for x in grid]) / 1e6
    fig = go.Figure(go.Scatter(x=grid, y=vals, mode="lines", name="MtM", line=dict(color=PALETTE["primary"], width=2.5),
                               hovertemplate="%{y:,.1f} millones CLP<extra></extra>"))
    fig.add_hrect(y0=-line / 1e6, y1=min(vals.min(), -line / 1e6) - 1, fillcolor=PALETTE["negative"], opacity=0.12,
                  line_width=0, annotation_text="Se piden garantías", annotation_position="bottom left")
    fig.add_hline(y=-line / 1e6, line_dash="dot", line_color=PALETTE["negative"], line_width=1)
    vline(fig, k, f"Pactado {fmt_rate(k)}")
    _dot(fig, f_mkt, mtm / 1e6, PALETTE["accent" if mtm >= 0 else "negative"])
    fig.update_layout(showlegend=False, hovermode="closest")
    _plot(style_fig(fig, x_title="Forward de mercado hoy (CLP por USD)", y_title="MtM (millones CLP)", height=340))
    st.caption("Simplificado: diferencia de precios × monto, sin traerla a valor presente. "
               "Por eso da algo más que el ejemplo anterior.")


# --- 6. resultado de una opción


_KIND_LABEL = {"call": "Call (derecho a comprar)", "put": "Put (derecho a vender)"}
_POS_LABEL = {"long": "Comprar", "short": "Vender"}


def _demo_option_payoff(key, p: dict) -> None:
    from .options import OptionLeg, garman_kohlhagen, leg_pnl

    strike = float(p.get("strike", DEFAULTS["spot"]))
    spot = float(p.get("spot", strike))
    with st.container(horizontal=True, gap="medium"):
        kind = st.segmented_control("Opción", list(_KIND_LABEL), default=p.get("kind", "call"),
                                    format_func=_KIND_LABEL.get, key=key("kind"), required=True) or "call"
        pos = st.segmented_control("Posición", list(_POS_LABEL), default=p.get("position", "long"),
                                   format_func=_POS_LABEL.get, key=key("position"), required=True) or "long"
    # La prima del contenido corresponde a su tipo de opción; para el otro tipo se calcula (GK, caso ancla).
    if kind == p.get("kind", "call") and "premium" in p:
        premium = float(p["premium"])
    else:
        premium = garman_kohlhagen(kind, spot, strike, DEFAULTS["years"], DEFAULTS["r_dom"], DEFAULTS["r_for"],
                                   DEFAULTS["vol"])
    s_t = _spot_slider("Dólar al vencimiento (CLP por USD)", key("spot_T"), strike, spot, 0.15)
    leg = OptionLeg(kind=kind, position=pos, strike=strike, premium=premium)
    res = float(leg_pnl(leg, np.array([s_t]))[0])
    paid = "pagas" if pos == "long" else "cobras"
    _metrics(("Strike", fmt_rate(strike)), (f"Prima que {paid}", fmt_rate(premium), None, "CLP por USD"),
             ("Resultado por USD", fmt_num(res, 2), _GOOD if res > 0 else _BAD if res < 0 else None,
              "ganas" if res > 0 else "pierdes" if res < 0 else "quedas igual"))
    fig = _fig_option_payoff({"kind": kind, "position": pos, "strike": strike, "premium": premium, "spot": strike})
    _dot(fig, s_t, res, PALETTE["accent" if res >= 0 else "negative"])
    _plot(fig)


# --- 7. de qué depende la prima


def _demo_option_price(key, p: dict) -> None:
    from .options import garman_kohlhagen, intrinsic_value

    kind = p.get("kind", "call")
    spot, r_dom, r_for = _p(p, "spot"), _p(p, "r_dom"), _p(p, "r_for")
    k0 = float(p.get("strike", spot))
    lo, hi = round(spot * 0.9 / 10) * 10.0, round(spot * 1.1 / 10) * 10.0
    with st.container(horizontal=True, gap="medium"):
        vol = st.slider("Volatilidad (%)", 5.0, 40.0, round(_p(p, "vol") * 100, 1), 1.0, format="%.0f%%",
                        key=key("vol")) / 100
        years = st.slider("Plazo (años)", 0.25, 2.0, float(_p(p, "years")), 0.25, format="%.2f", key=key("years"))
        strike = st.slider("Strike", lo, hi, float(min(max(k0, lo), hi)), 5.0, format="%.0f", key=key("strike"))
    price = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
    intr = intrinsic_value(kind, spot, strike)
    _metrics(("Prima", fmt_rate(price), None, "CLP por USD"), ("Valor intrínseco", fmt_rate(intr)),
             ("Valor temporal", fmt_rate(price - intr)))
    grid = _settle_grid(strike, 0.15, 121)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=[intrinsic_value(kind, x, strike) for x in grid], mode="lines",
                             name="Valor intrínseco", line=dict(color=PALETTE["neutral"], width=1.5, dash="dash")))
    fig.add_trace(go.Scatter(x=grid, y=[garman_kohlhagen(kind, x, strike, years, r_dom, r_for, vol) for x in grid],
                             mode="lines", name="Prima (intrínseco + temporal)",
                             line=dict(color=PALETTE["primary"], width=2.5)))
    vline(fig, strike, f"Strike {fmt_rate(strike, 0)}")
    _dot(fig, spot, price, PALETTE["secondary"], f"Spot {fmt_rate(spot, 0)}")
    fig.update_traces(hovertemplate="%{y:,.2f} CLP por USD<extra></extra>")
    _plot(style_fig(fig, x_title="Dólar hoy (CLP por USD)", y_title="Prima (CLP por USD)", height=340))


# --- 8. collar de costo cero


def _demo_collar(key, p: dict) -> None:
    from .forward import forward_rate
    from .options import garman_kohlhagen
    from .strategies import zero_cost_strike

    spot, vol, years = _p(p, "spot"), _p(p, "vol"), _p(p, "years")
    r_dom, r_for = _p(p, "r_dom"), _p(p, "r_for")
    k_c0 = float(p.get("call_strike", spot * 1.02))
    lo, hi = float(round(spot)), float(round(spot * 1.08))
    k_c = st.slider("Techo: strike de la call que compras", lo, hi, float(min(max(k_c0, lo), hi)), 0.1,
                    format="%.2f", key=key("call_strike"))
    call_prem = garman_kohlhagen("call", spot, k_c, years, r_dom, r_for, vol)
    k_p = zero_cost_strike("put", call_prem, spot, years, r_dom, r_for, vol)
    fwd = forward_rate(spot, r_dom, r_for, years)
    _metrics(("Techo (call comprada)", fmt_rate(k_c)), ("Piso (put vendida)", fmt_rate(k_p)),
             ("Prima neta", fmt_rate(0.0), None, f"call {fmt_rate(call_prem)} = put {fmt_rate(call_prem)}"))
    grid = _settle_grid(spot, 0.15, 151)
    collar = np.clip(grid, k_p, k_c)  # dólar efectivo del importador con el collar
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=grid, mode="lines", name="Sin cubrirse",
                             line=dict(color=PALETTE["secondary"], width=1.5, dash="dash")))
    fig.add_trace(go.Scatter(x=grid, y=np.full_like(grid, fwd), mode="lines", name=f"Forward ({fmt_rate(fwd)})",
                             line=dict(color=PALETTE["neutral"], width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(x=grid, y=collar, mode="lines", name="Con collar",
                             line=dict(color=PALETTE["accent"], width=3)))
    fig.add_hrect(y0=k_p, y1=k_c, fillcolor=PALETTE["accent"], opacity=0.08, line_width=0)
    fig.update_traces(hovertemplate="%{y:,.2f} CLP por USD<extra></extra>")
    _plot(style_fig(fig, x_title="Dólar al vencimiento (CLP por USD)", y_title="Dólar que paga el importador",
                    height=360))


# --- 9. cuánto cubrir


def hedge_ratio_scenarios(spot: float) -> list[float]:
    """Escenarios del dólar al vencimiento: −10%, hoy, ~+6,7% y ~+12%, redondeados a 10 (890 → 800/890/950/1.000)."""
    return [round(spot * 0.9, -1), spot, round(spot * 1.067, -1), round(spot * 1.12, -1)]


def _demo_hedge_ratio(key, p: dict) -> None:
    spot, k, n = _p(p, "spot"), _p_fwd(p), _p(p, "notional_usd")
    h = st.slider("Porción cubierta con forward", 0, 100, 50, 10, format="%d%%", key=key("ratio")) / 100
    scen = hedge_ratio_scenarios(spot)
    # Dólar promedio pagado. +1e-9 = redondeo "mitad hacia arriba" (924,445 se muestra 924,45, como el texto).
    avg = [round(h * k + (1 - h) * s + 1e-9, 2) for s in scen]
    _metrics(*[(f"Si el dólar termina en {fmt_rate(s, 0)}", fmt_rate(a)) for s, a in zip(scen, avg, strict=True)])
    rng = (max(avg) - min(avg)) * n
    st.caption(f"Entre el mejor y el peor escenario, la factura de {md_usd(n)} varía {md_clp(rng)}. "
               "Con 100% cubierto, no varía.")
    labels = [fmt_rate(s, 0) for s in scen]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=avg, name="Dólar promedio pagado", marker_color=PALETTE["primary"],
                         text=[fmt_rate(a) for a in avg], textposition="outside",
                         hovertemplate="%{y:,.2f} CLP por USD<extra></extra>"))
    fig.add_hline(y=k, line_dash="dot", line_color=PALETTE["neutral"], line_width=1,
                  annotation_text=f"Forward {fmt_rate(k)}", annotation_position="top left")
    fig.update_yaxes(range=[min(scen) * 0.95, max(scen) * 1.03])
    fig.update_layout(showlegend=False, hovermode="closest")
    _plot(style_fig(fig, x_title="Dólar al vencimiento (escenario)", y_title="Dólar promedio pagado", height=340))


# --- 10. backtest histórico


_MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _month_label(d) -> str:
    return f"{_MONTHS[d.month - 1]} {d.year}"


def _demo_backtest(key, p: dict) -> None:
    years, n = float(p.get("years", 1.0)), float(p.get("nominal_usd", DEFAULTS["notional_usd"]))
    data = _backtest_series(years, n)
    if data.empty:
        st.caption(":material/warning: No hay datos suficientes para este plazo.")
        return
    # Etiquetas "ene 2024" -> fila del backtest ya calculada (hedge_backtest desde el 1° de ese mes).
    by_label = {_month_label(row["start_date"]): row for row in data.to_dict("records")}
    labels = list(by_label)
    chosen = st.select_slider("Mes en que se decide cubrirse", options=labels, value=labels[0], key=key("start"))
    bt = by_label[chosen]
    sav = bt["savings"]
    _metrics(("Dólar fijado con forward", fmt_rate(bt["fwd_rate"])), ("Dólar al pagar", fmt_rate(bt["spot_end"])),
             ("Resultado de cubrirse", _mm(abs(sav)), _GOOD if sav > 0 else _BAD if sav < 0 else None,
              "ahorró" if sav > 0 else "costó más" if sav < 0 else "empate"))
    st.caption(f"Decisión el {bt['start_date']:%d-%m-%Y}, pago el {bt['end_date']:%d-%m-%Y}. "
               "Forward teórico con tasas de referencia de esa fecha; un banco cotizaría distinto.")
    fig = _fig_hedge_backtest({"years": years, "nominal_usd": n})
    fig.add_vline(x=pd.Timestamp(bt["start_date"]), line_dash="dot", line_color=PALETTE["neutral"], line_width=1)
    _plot(fig)
