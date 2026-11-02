"""Tests de los temas (una pregunta por página): estructura de CHAPTERS, demos y recorrido en la UI.

Genéricos a propósito: corren contra el contenido que haya en ``curso/cap*.py``.
"""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from derivados101.curso import CHAPTERS, Chapter, Choice, Concept, Example, Numeric, Summary
from derivados101.curso.model import ChartName, Demo, DemoName
from derivados101.curso_ui import DEMO_PARAMS
from derivados101.ui import PAGES

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 60
CHART_NAMES = set(ChartName.__args__)
DEMO_NAMES = set(DemoName.__args__)
LAB_PATHS = {p.path for p in PAGES}


def _charts(ch: Chapter):
    return [s.chart for s in ch.screens if isinstance(s, Concept | Example) and s.chart is not None]


# ---------------------------------------------------------------- estructura


def test_chapters_numbered_in_order() -> None:
    assert [ch.number for ch in CHAPTERS] == list(range(1, len(CHAPTERS) + 1))


def test_slugs_unique_and_url_safe() -> None:
    slugs = [ch.slug for ch in CHAPTERS]
    assert len(set(slugs)) == len(slugs)
    for slug in slugs:
        assert slug and "/" not in slug and slug == slug.strip().lower(), slug


@pytest.mark.parametrize("ch", CHAPTERS, ids=lambda c: c.slug)
def test_chapter_shape(ch: Chapter) -> None:
    assert ch.title.startswith("¿") and ch.title.endswith("?"), "el título es la pregunta"
    assert ch.icon.startswith(":material/")
    assert 3 <= len(ch.screens) <= 7, f"{ch.slug}: {len(ch.screens)} pantallas"
    assert isinstance(ch.screens[-1], Summary), "debe terminar en Summary"
    assert sum(isinstance(s, Summary) for s in ch.screens) == 1
    assert len(ch.demos) >= 1, "al menos una demo"
    assert not any(isinstance(s, Choice | Numeric) for s in ch.screens), "los temas no llevan preguntas"
    assert ch.screens[-1].points


@pytest.mark.parametrize("ch", CHAPTERS, ids=lambda c: c.slug)
def test_demos_well_formed(ch: Chapter) -> None:
    for s in ch.demos:
        assert s.demo in DEMO_NAMES, s.demo
        assert set(s.params) <= DEMO_PARAMS[s.demo], f"{s.demo}: params extra {set(s.params) - DEMO_PARAMS[s.demo]}"
        assert s.title and s.prompt, s.demo


def test_every_demo_name_has_params_spec() -> None:
    assert set(DEMO_PARAMS) == DEMO_NAMES


@pytest.mark.parametrize("ch", CHAPTERS, ids=lambda c: c.slug)
def test_charts_and_labs_valid(ch: Chapter) -> None:
    from derivados101.curso_ui import chart_figure

    for chart in _charts(ch):
        assert chart.name in CHART_NAMES, chart.name
        assert chart_figure(chart).data, chart.name
    for s in ch.screens:
        if isinstance(s, Example) and s.lab:
            assert s.lab in LAB_PATHS and (ROOT / s.lab).exists(), s.lab


def test_no_unescaped_dollar_pairs() -> None:
    """Pares de "$" sin escapar se vuelven LaTeX en Streamlit (rompen montos como US$500)."""
    for ch in CHAPTERS:
        for s in ch.screens:
            for text in _texts(s):
                assert not re.search(r"(?<!\\)\$", text), f"{ch.slug}: '$' sin escapar en {text[:60]!r}"


def _texts(s) -> list[str]:
    if isinstance(s, Concept):
        return [s.title, s.body, *(t for pair in s.terms for t in pair), s.callout or ""]
    if isinstance(s, Example):
        return [s.title, s.setup, *s.steps, s.takeaway]
    if isinstance(s, Demo):
        return [s.title, s.prompt, s.takeaway or ""]
    if isinstance(s, Summary):
        return [*s.points, s.next_hint or ""]
    return []


def test_every_chart_name_has_a_builder() -> None:
    from derivados101.curso.model import Chart
    from derivados101.curso_ui import chart_figure

    for name in CHART_NAMES:
        assert chart_figure(Chart(name=name)).data, name


# ---------------------------------------------------------------- UI: temas


def _chapter_app(index: int) -> AppTest:
    def script(index: int) -> None:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path.cwd() / "src"))
        from derivados101.curso import CHAPTERS
        from derivados101.curso_ui import render_chapter

        render_chapter(CHAPTERS[index])

    at = AppTest.from_function(script, args=(index,), default_timeout=TIMEOUT)
    at.run()
    return at


def _screen_counter(at: AppTest) -> str:
    return at.get("progress")[0].proto.text


@pytest.mark.parametrize("index", range(len(CHAPTERS)), ids=[c.slug for c in CHAPTERS])
def test_chapter_walkthrough(index: int) -> None:
    """Cada tema renderiza y se puede avanzar con "Siguiente" hasta la última pantalla."""
    ch = CHAPTERS[index]
    at = _chapter_app(index)
    n = len(ch.screens)
    for k in range(1, n + 1):
        assert not at.exception, [e.message for e in at.exception]
        assert _screen_counter(at) == f"{k} de {n}"
        if k < n:
            at.button(key=f"tema:{ch.slug}:next").click().run()
    captions = " ".join(c.value for c in at.caption)
    assert "No es asesoría financiera" in captions
    at.button(key=f"tema:{ch.slug}:prev").click().run()
    assert _screen_counter(at) == f"{n - 1} de {n}"


# ---------------------------------------------------------------- UI: demos


def _demo_app(name: str, params: dict) -> AppTest:
    """Un tema mínimo con una sola demo (pantalla 0) y su Summary."""

    def script(name: str, params: dict) -> None:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path.cwd() / "src"))
        from derivados101.curso.model import Chapter, Demo, Summary
        from derivados101.curso_ui import render_chapter

        ch = Chapter(number=1, slug="demo-test", title="¿Demo?", icon=":material/science:", goal="", minutes=1,
                     screens=[Demo(title="Demo", prompt="Mueve el control.", demo=name, params=params),
                              Summary(points=["a", "b", "c"])])
        render_chapter(ch)

    at = AppTest.from_function(script, args=(name, params), default_timeout=TIMEOUT)
    at.run()
    return at


def _metric_values(at: AppTest) -> list[str]:
    return [f"{m.value}|{m.delta}" for m in at.metric]


def _move_first_control(at: AppTest) -> None:
    """Mueve el primer slider (o select_slider) a su máximo."""
    if at.slider:
        sl = at.slider[0]
        sl.set_value(sl.max).run()
    else:
        ss = at.select_slider[0]
        ss.set_value(ss.options[-1]).run()


# Una instancia por tipo de demo: params del contenido si existe, si no los valores por defecto.
_DEMO_CASES = {name: {} for name in sorted(DEMO_NAMES)}
for _ch in CHAPTERS:
    for _s in _ch.demos:
        _DEMO_CASES[_s.demo] = _s.params


@pytest.mark.parametrize("name", sorted(_DEMO_CASES))
def test_demo_renders_and_reacts(name: str) -> None:
    at = _demo_app(name, _DEMO_CASES[name])
    assert not at.exception, [e.message for e in at.exception]
    assert at.metric, "la demo muestra métricas"
    assert at.get("plotly_chart"), "la demo muestra un gráfico"
    before = _metric_values(at)
    _move_first_control(at)
    assert not at.exception, [e.message for e in at.exception]
    assert _metric_values(at) != before, "las métricas reaccionan al control"


@pytest.mark.parametrize("name", sorted(_DEMO_CASES))
def test_demo_defaults_without_params(name: str) -> None:
    at = _demo_app(name, {})
    assert not at.exception, [e.message for e in at.exception]


def _metric(at: AppTest, label_start: str):
    return next(m for m in at.metric if m.label.startswith(label_start))


def test_forward_settlement_signs() -> None:
    """Compra a 898,89 por US$500.000 con dólar 870: la empresa paga 14.445.000 (rojo)."""
    params = {"forward": 898.89, "spot_T": 870.0, "side": "buy", "notional_usd": 500000}
    at = _demo_app("forward_settlement", params)
    m = _metric(at, "Compensación")
    assert m.value == "-$14.445.000" and "pagas" in m.delta
    at.segmented_control[0].set_value("sell").run()
    m = _metric(at, "Compensación")
    assert m.value == "$14.445.000" and "te paga" in m.delta


def test_mtm_margin_call_without_buffer() -> None:
    params = {"forward": 898.89, "market_forward": 874.34, "notional_usd": 500000, "credit_line_clp": 10000000}
    at = _demo_app("mtm", params)
    assert _metric(at, "MtM").value == "-$12.275.000"
    assert _metric(at, "Garantía").value == "$2.275.000"


def test_hedge_ratio_includes_950_scenario() -> None:
    at = _demo_app("hedge_ratio", {"spot": 890.0, "forward": 898.89, "notional_usd": 500000.0})
    assert _metric(at, "Si el dólar termina en 950").value == "924,45"


def test_backtest_offers_january_2024_and_2025() -> None:
    at = _demo_app("backtest", {"years": 1.0, "nominal_usd": 500000.0})
    labels = list(at.select_slider[0].options)
    assert "ene 2024" in labels and "ene 2025" in labels


def test_navigation_reaches_every_chapter() -> None:
    """Desde app.py, "Empezar" en Inicio y "Siguiente: <pregunta>" al final de un tema funcionan."""
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.run()
    assert not at.exception
    at.button(key="start").click().run()
    assert not at.exception
    assert at.title[0].value == CHAPTERS[0].title
    first = CHAPTERS[0]
    at.session_state[f"tema:{first.slug}:idx"] = len(first.screens) - 1
    at.run()
    at.button(key=f"tema:{first.slug}:next_ch").click().run()
    assert not at.exception
    assert at.title[0].value == CHAPTERS[1].title
