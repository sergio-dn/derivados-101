"""Las cifras escritas a mano en los textos de los temas coinciden con el núcleo.

Los temas (src/derivados101/curso/cap*.py) citan cifras fijas: primas, strikes del collar,
promedio con cobertura parcial y resultados del backtest. Si cambian las tasas, la volatilidad
de ejemplo, los presets o el cálculo, estos tests fallan y avisan qué texto revisar.
"""

from datetime import date

import pytest

from derivados101.curso import CHAPTERS, Concept, Demo, Example, Summary
from derivados101.forward import forward_rate
from derivados101.market import hedge_backtest, load_usdclp
from derivados101.options import garman_kohlhagen
from derivados101.strategies import zero_cost_strike
from derivados101.ui import fmt_num

# Caso ancla de los temas (ejemplo fijo).
SPOT, R_DOM, R_FOR, YEARS, VOL, NOTIONAL = 890.0, 0.0511, 0.0407, 1.0, 0.12, 500_000


def _text(slug: str) -> str:
    """Todo el texto visible de un tema, en un solo string."""
    ch = next(c for c in CHAPTERS if c.slug == slug)
    parts: list[str] = []
    for s in ch.screens:
        if isinstance(s, Concept):
            parts += [s.title, s.body, *(t for pair in s.terms for t in pair), s.callout or ""]
        elif isinstance(s, Example):
            parts += [s.title, s.setup, *s.steps, s.takeaway]
        elif isinstance(s, Demo):
            parts += [s.title, s.prompt, s.takeaway or ""]
        elif isinstance(s, Summary):
            parts += [*s.points, s.next_hint or ""]
    return "\n".join(parts)


def _call(strike: float = 900.0, years: float = YEARS, vol: float = VOL) -> float:
    return garman_kohlhagen("call", SPOT, strike, years, R_DOM, R_FOR, vol)


def _put_zero_cost(call_strike: float) -> float:
    premium = garman_kohlhagen("call", SPOT, call_strike, YEARS, R_DOM, R_FOR, VOL)
    return zero_cost_strike("put", premium, SPOT, YEARS, R_DOM, R_FOR, VOL)


def _assert_in(slug: str, value: float, decimals: int = 2) -> None:
    shown = fmt_num(value, decimals)
    assert shown in _text(slug), f"el tema '{slug}' debería citar {shown}; revisa su texto"


def test_forward_ancla() -> None:
    fwd = forward_rate(SPOT, R_DOM, R_FOR, YEARS)
    _assert_in("que-es-un-forward", fwd)
    _assert_in("que-es-un-forward", fwd - SPOT)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(lambda: _call(), id="call 900"),
        pytest.param(lambda: _call(vol=0.20), id="vol 20%"),
        pytest.param(lambda: _call(years=0.5), id="6 meses"),
        pytest.param(lambda: _call(strike=950), id="strike 950"),
    ],
)
def test_primas_precio_de_una_opcion(value) -> None:
    _assert_in("precio-de-una-opcion", value())


def test_prima_y_techo_que_es_una_opcion() -> None:
    premium = _call()
    _assert_in("que-es-una-opcion", premium)
    _assert_in("que-es-una-opcion", 900 + premium)
    _assert_in("que-es-una-opcion", premium * NOTIONAL, decimals=0)


def test_collar_costo_cero() -> None:
    call_strike = SPOT * 1.02
    _assert_in("collar-costo-cero", call_strike)
    _assert_in("collar-costo-cero", _put_zero_cost(call_strike))
    _assert_in("collar-costo-cero", _call(strike=call_strike))  # prima de cada pata


def test_cobertura_parcial_50() -> None:
    fwd = forward_rate(SPOT, R_DOM, R_FOR, YEARS)
    _assert_in("cuanto-y-cuando-cubrirse", 0.5 * fwd + 0.5 * 950)


@pytest.mark.parametrize("start,millions", [(date(2024, 1, 2), 49.7), (date(2025, 1, 2), 48.5)])
def test_backtest_citado(start: date, millions: float) -> None:
    """Datos históricos: solo cambian si se corrige el CSV o las tasas de referencia."""
    result = hedge_backtest(load_usdclp(), start, 1.0, NOTIONAL)
    assert round(abs(result["savings"]) / 1e6, 1) == millions
    _assert_in("cuanto-y-cuando-cubrirse", millions, decimals=1)
