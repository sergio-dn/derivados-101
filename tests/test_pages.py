"""Smoke tests de la UI: cada página corre sin excepciones (streamlit.testing.v1.AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["app.py", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "app_pages").glob("*.py"))]
TIMEOUT = 60


def _run(path: str) -> AppTest:
    at = AppTest.from_file(str(ROOT / path), default_timeout=TIMEOUT)
    at.run()
    return at


# 0_Inicio usa st.page_link hacia las páginas registradas en app.py: solo corre vía el router
# (cubierto por "app.py", cuya página por defecto es Inicio).
@pytest.mark.parametrize("page", [p for p in PAGES if not p.endswith("0_Inicio.py")])
def test_page_runs_without_exception(page: str) -> None:
    at = _run(page)
    assert not at.exception, [e.message for e in at.exception]
    # Toda página muestra el disclaimer.
    captions = " ".join(c.value for c in at.caption)
    assert "No es asesoría financiera" in captions


def test_forward_default_matches_spreadsheet() -> None:
    at = _run("app_pages/2_Forward.py")
    values = {m.label: m.value for m in at.metric}
    assert values["Forward a plazo"] == "898,89"


def test_forward_slider_and_sell_side() -> None:
    at = _run("app_pages/2_Forward.py")
    at.segmented_control(key="fwd_side").set_value("sell").run()
    at.slider(key="fwd_spot_T").set_value(at.slider(key="fwd_spot_T").max).run()
    assert not at.exception


@pytest.mark.parametrize("kind_idx,pos_idx", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_options_all_combinations(kind_idx: int, pos_idx: int) -> None:
    at = _run("app_pages/3_Opciones.py")
    at.segmented_control(key="opt_kind").set_value(["call", "put"][kind_idx])
    at.segmented_control(key="opt_position").set_value(["long", "short"][pos_idx])
    at.segmented_control(key="opt_prem_mode").set_value("manual").run()
    assert not at.exception


def test_strategies_every_preset() -> None:
    at = _run("app_pages/4_Estrategias.py")
    for key in at.selectbox(key="strat_preset").options:
        at.selectbox(key="strat_preset").set_value(key).run()
        assert not at.exception, key


def test_usdclp_backtest_runs() -> None:
    at = _run("app_pages/5_USDCLP.py")
    labels = [m.label for m in at.metric]
    assert "Costo con forward teórico" in labels


def test_quiz_perfect_score() -> None:
    at = _run("app_pages/6_Quiz.py")
    correct = [opts[c] for _, opts, c, _ in _questions()]
    for radio, ans in zip(at.radio, correct, strict=True):
        radio.set_value(ans)
    at.button[0].click().run()
    assert not at.exception
    assert any(m.value == f"{len(correct)} / {len(correct)}" for m in at.metric)


def _questions():
    """Extrae QUESTIONS del script del quiz sin ejecutar Streamlit."""
    import ast

    tree = ast.parse((ROOT / "app_pages/6_Quiz.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "QUESTIONS":
            return ast.literal_eval(node.value)
    raise AssertionError("QUESTIONS no encontrado")


@pytest.mark.parametrize("page", [p for p in PAGES if p.startswith("app_pages/")])
def test_navigation_reaches_every_page(page: str) -> None:
    """Entrando por app.py (st.navigation), cada página se puede abrir sin excepciones."""
    at = _run("app.py")
    at.switch_page(page).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.title, page
