"""Tests de datos de mercado: CSV real, métricas y descarga en vivo (sin red)."""

import logging
from datetime import date

import httpx
import numpy as np
import pandas as pd
import pytest

from derivados101 import market
from derivados101.forward import forward_rate


@pytest.fixture(scope="module")
def df():
    return market.load_usdclp()


@pytest.fixture
def capture_warnings(caplog):
    """El logger del paquete no propaga al root: le colgamos el handler de caplog."""
    market.logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger=market.logger.name)
    yield caplog
    market.logger.removeHandler(caplog.handler)


@pytest.fixture
def no_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr(market, "_sleep", calls.append)
    return calls


def _mock_client(monkeypatch, handler):
    monkeypatch.setattr(
        market, "_make_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )


# --- CSV ------------------------------------------------------------------- #


def test_load_csv(df):
    assert list(df.columns) == ["date", "usdclp"]
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert len(df) == 706
    assert df["date"].is_monotonic_increasing and df["date"].is_unique
    assert df["date"].iloc[0] == pd.Timestamp("2024-01-02")
    assert df["usdclp"].iloc[0] == pytest.approx(877.12)
    assert df["usdclp"].between(700, 1200).all()


def test_load_usdclp_sorts_and_dedupes(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("date,usdclp\n2024-01-03,2\n2024-01-02,1\n2024-01-03,3\n")
    out = market.load_usdclp(p)
    assert out["usdclp"].tolist() == [1, 3]


def test_realized_vol(df):
    vol = market.realized_vol(df)
    assert vol.index.equals(pd.DatetimeIndex(df["date"]))
    assert vol.iloc[:21].isna().all()
    valid = vol.dropna()
    assert valid.between(0.01, 0.6).all()  # el USD/CLP se mueve ~5-20% anual


def test_realized_vol_constant_returns_is_zero():
    d = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=30),
                      "usdclp": 900 * 1.001 ** np.arange(30)})
    assert market.realized_vol(d, window=5).dropna().abs().max() < 1e-12


def test_horizon_changes(df):
    out = market.horizon_changes(df)
    assert list(out.columns) == ["horizon_days", "n", "min", "p5", "p50", "p95", "max", "std"]
    assert out["horizon_days"].tolist() == [21, 63, 126, 189, 252]
    assert (out["n"] == len(df) - out["horizon_days"]).all()
    assert (out["min"] <= out["p5"]).all() and (out["p5"] <= out["p50"]).all()
    assert (out["p50"] <= out["p95"]).all() and (out["p95"] <= out["max"]).all()
    # a mayor plazo, mayor dispersión
    assert out["std"].iloc[-1] > out["std"].iloc[0]
    assert market.horizon_changes(df, (10_000,)).empty


def test_hedge_backtest(df):
    res = market.hedge_backtest(df, date(2024, 1, 2), 1.0, 0.0511, 0.0407, 500_000)
    assert res["start_date"] == date(2024, 1, 2)
    assert res["spot_start"] == pytest.approx(877.12)
    assert res["end_date"] >= date(2025, 1, 1)
    assert res["fwd_rate"] == pytest.approx(forward_rate(877.12, 0.0511, 0.0407, 1.0))
    assert res["cost_unhedged"] == pytest.approx(500_000 * res["spot_end"])
    assert res["cost_hedged"] == pytest.approx(500_000 * res["fwd_rate"])
    # compensación (buy) = ahorro de la cobertura
    assert res["compensation"] == pytest.approx(res["savings"])


def test_hedge_backtest_out_of_range(df):
    with pytest.raises(ValueError):
        market.hedge_backtest(df, date(2026, 6, 1), 1.0, 0.05, 0.04, 1)


def test_simulate_gbm():
    paths = market.simulate_gbm(900, 0.12, 1.0, 0.0511, 0.0407, n_paths=20_000, n_steps=50)
    assert paths.shape == (51, 20_000)
    assert (paths[0] == 900).all()
    assert (paths > 0).all()
    # neutral al riesgo: el promedio final ≈ forward
    assert paths[-1].mean() == pytest.approx(forward_rate(900, 0.0511, 0.0407, 1.0), rel=0.005)
    again = market.simulate_gbm(900, 0.12, 1.0, 0.0511, 0.0407, n_paths=20_000, n_steps=50)
    np.testing.assert_array_equal(paths, again)  # reproducible con la semilla


# --- Descarga en vivo (mockeada) ------------------------------------------ #


def test_fetch_live_success(monkeypatch, no_sleep):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        year = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={"serie": [
            {"fecha": f"{year}-01-03T03:00:00.000Z", "valor": 901.5},
            {"fecha": f"{year}-01-02T03:00:00.000Z", "valor": 900.0},
        ]})

    _mock_client(monkeypatch, handler)
    out = market.fetch_usdclp_live([2024, 2025])
    assert seen == ["https://mindicador.cl/api/dolar/2024", "https://mindicador.cl/api/dolar/2025"]
    assert out["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2024-01-02", "2024-01-03", "2025-01-02", "2025-01-03"]
    assert out["usdclp"].tolist() == [900.0, 901.5, 900.0, 901.5]
    assert no_sleep == []


def test_fetch_live_retries_then_succeeds(monkeypatch, no_sleep):
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"serie": [{"fecha": "2024-01-02T03:00:00Z", "valor": 1}]})

    _mock_client(monkeypatch, handler)
    out = market.fetch_usdclp_live([2024], retries=3)
    assert len(out) == 1 and attempts["n"] == 3
    assert no_sleep == [0.5, 1.0]  # backoff exponencial


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(200, json={"sin_serie": []}),
        lambda r: httpx.Response(200, json={"serie": []}),
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("sin red")),
    ],
    ids=["http_500", "json_raro", "vacio", "sin_red"],
)
def test_fetch_live_falls_back_to_csv(monkeypatch, no_sleep, capture_warnings, handler, df):
    _mock_client(monkeypatch, handler)
    out = market.fetch_usdclp_live([2024], retries=3)
    pd.testing.assert_frame_equal(out, df)
    assert any(r.levelno == logging.WARNING for r in capture_warnings.records)


def test_fetch_live_never_raises_even_without_csv(monkeypatch, no_sleep, tmp_path):
    _mock_client(monkeypatch, lambda r: httpx.Response(500))
    monkeypatch.setattr(market, "DEFAULT_CSV", tmp_path / "no_existe.csv")
    out = market.fetch_usdclp_live([2024], retries=1)
    assert out.empty and list(out.columns) == ["date", "usdclp"]
