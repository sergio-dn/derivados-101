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
    assert len(df) >= 706  # crece con la actualización automática de data/
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
    res = market.hedge_backtest(df, date(2024, 1, 2), 1.0, 500_000, r_dom=0.0511, r_for=0.0407)
    assert res["start_date"] == date(2024, 1, 2)
    assert res["spot_start"] == pytest.approx(877.12)
    assert res["end_date"] >= date(2025, 1, 1)
    assert res["fwd_rate"] == pytest.approx(forward_rate(877.12, 0.0511, 0.0407, 1.0))
    assert res["cost_unhedged"] == pytest.approx(500_000 * res["spot_end"])
    assert res["cost_hedged"] == pytest.approx(500_000 * res["fwd_rate"])
    assert (res["r_dom"], res["r_for"]) == (0.0511, 0.0407)
    # compensación (buy) = ahorro de la cobertura
    assert res["compensation"] == pytest.approx(res["savings"])


def test_hedge_backtest_uses_historical_rates_by_default(df):
    r_clp, r_usd, when = market.reference_rates(date(2024, 1, 2))
    assert when == date(2024, 1, 1)
    res = market.hedge_backtest(df, date(2024, 1, 2), 1.0, 500_000)
    assert (res["r_dom"], res["r_for"]) == (r_clp, r_usd)
    assert res["fwd_rate"] == pytest.approx(forward_rate(877.12, r_clp, r_usd, 1.0))
    # a inicios de 2024 la tasa CLP era bastante mayor que la USD
    assert r_clp > r_usd
    # se puede fijar solo una de las dos tasas
    only_dom = market.hedge_backtest(df, date(2024, 1, 2), 1.0, 1, r_dom=0.05)
    assert (only_dom["r_dom"], only_dom["r_for"]) == (0.05, r_usd)


def test_hedge_backtest_out_of_range(df):
    with pytest.raises(ValueError):
        market.hedge_backtest(df, date(2026, 6, 1), 1.0, 1, r_dom=0.05, r_for=0.04)


# --- Tasas de referencia --------------------------------------------------- #


def test_rates_csv_shape():
    rates = market._load_rates()
    assert list(rates.columns) == ["date", "r_clp", "r_usd"]
    assert rates["date"].iloc[0] == pd.Timestamp("2023-01-01")
    assert rates["date"].is_monotonic_increasing and rates["date"].is_unique
    assert (rates["date"].dt.day == 1).all()
    # mensual y sin huecos
    assert len(rates) == len(pd.date_range(rates["date"].iloc[0], rates["date"].iloc[-1], freq="MS"))
    # decimales razonables (no porcentajes)
    assert rates["r_clp"].between(0.0, 0.2).all() and rates["r_usd"].between(0.0, 0.1).all()


def test_reference_rates_edges():
    rates = market._load_rates()
    last = rates.iloc[-1]
    assert market.reference_rates() == (last["r_clp"], last["r_usd"], last["date"].date())
    # fecha intermedia: fila vigente en o antes
    r_clp, r_usd, when = market.reference_rates(date(2024, 6, 30))
    assert when == date(2024, 6, 1)
    row = rates[rates["date"] == pd.Timestamp("2024-06-01")].iloc[0]
    assert (r_clp, r_usd) == (row["r_clp"], row["r_usd"])
    # exactamente el primer día del mes
    assert market.reference_rates(date(2024, 7, 1))[2] == date(2024, 7, 1)
    # antes de la primera fila: la primera
    first = rates.iloc[0]
    assert market.reference_rates(date(2010, 1, 1)) == (
        first["r_clp"], first["r_usd"], first["date"].date())
    # en el futuro: la última
    assert market.reference_rates(date(2099, 1, 1))[2] == last["date"].date()


def test_reference_rates_without_csv(monkeypatch, tmp_path, capture_warnings):
    monkeypatch.setattr(market, "RATES_CSV", tmp_path / "no_existe.csv")
    assert market.reference_rates(date(2024, 1, 1)) == (0.0511, 0.0407, date(2024, 1, 1))
    assert any(r.levelno == logging.WARNING for r in capture_warnings.records)


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


# --- latest_spot ----------------------------------------------------------- #


def test_latest_spot_live(monkeypatch):
    def handler(request):
        assert str(request.url) == "https://mindicador.cl/api/dolar"
        return httpx.Response(200, json={"serie": [
            {"fecha": "2026-11-02T03:00:00.000Z", "valor": 950.5},
            {"fecha": "2026-10-31T03:00:00.000Z", "valor": 949.0},
        ]})

    _mock_client(monkeypatch, handler)
    assert market.latest_spot() == (950.5, date(2026, 11, 2), "mindicador.cl")


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(200, content=b""),  # respuesta vacía (caso real de mindicador)
        lambda r: httpx.Response(200, json={"serie": []}),
        lambda r: (_ for _ in ()).throw(httpx.RemoteProtocolError("desconectado")),
    ],
    ids=["http_500", "cuerpo_vacio", "serie_vacia", "desconecta"],
)
def test_latest_spot_falls_back_to_csv(monkeypatch, handler, df):
    _mock_client(monkeypatch, handler)
    value, when, source = market.latest_spot()
    assert source == "csv"
    assert value == pytest.approx(df["usdclp"].iloc[-1])
    assert when == df["date"].iloc[-1].date()


def test_latest_spot_offline_does_not_call_network(monkeypatch, df):
    def handler(request):  # pragma: no cover - no debe llamarse
        raise AssertionError("no debía consultar la red")

    _mock_client(monkeypatch, handler)
    assert market.latest_spot(live=False)[2] == "csv"


def test_latest_spot_last_resort(monkeypatch, tmp_path, capture_warnings):
    _mock_client(monkeypatch, lambda r: httpx.Response(500))
    monkeypatch.setattr(market, "DEFAULT_CSV", tmp_path / "no_existe.csv")
    value, _, source = market.latest_spot()
    assert (value, source) == (900.0, "fijo")


# --- API del Banco Central (token) ------------------------------------ #

_TOKEN, _USER, _PASS = "token-super-secreto-123", "usuario@ejemplo.cl", "clave-super-secreta-456"


def _bcch_payload(obs, codigo=0):
    return {"Codigo": codigo, "Descripcion": "Success" if codigo == 0 else "Invalid",
            "Series": {"seriesId": market.BCCH_USDCLP_SERIES, "Obs": obs}}


def test_bcch_parses_and_skips_missing_days(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(request.url.params)
        return httpx.Response(200, json=_bcch_payload([
            {"indexDateString": "02-01-2024", "value": "877.12", "statusCode": "OK"},
            {"indexDateString": "06-01-2024", "value": "NaN", "statusCode": "ND"},
            {"indexDateString": "03-01-2024", "value": "884.59", "statusCode": "OK"},
        ]))

    _mock_client(monkeypatch, handler)
    rows = market.fetch_usdclp_bcch(date(2024, 1, 1), date(2024, 1, 10), token=_TOKEN)
    assert rows == [{"date": "2024-01-02", "usdclp": 877.12}, {"date": "2024-01-03", "usdclp": 884.59}]
    assert seen["timeseries"] == "F073.TCO.PRE.Z.D" and seen["firstdate"] == "2024-01-01"
    assert seen["token"] == _TOKEN and "user" not in seen and "pass" not in seen


@pytest.mark.parametrize("auth", [{"token": _TOKEN}, {"user": _USER, "password": _PASS}], ids=["token", "user"])
@pytest.mark.parametrize("response", [
    httpx.Response(500, text="error"),
    httpx.Response(200, json=_bcch_payload(None, codigo=-5)),
    httpx.Response(200, text="no es json"),
])
def test_bcch_failure_never_leaks_credentials(monkeypatch, capture_warnings, no_sleep, response, auth):
    """Ni el mensaje, ni la cadena de excepciones, ni los logs muestran el token o la URL."""
    _mock_client(monkeypatch, lambda request: response)
    with pytest.raises(RuntimeError) as info:
        market.fetch_usdclp_bcch(date(2024, 1, 1), date(2024, 1, 10), retries=2, **auth)
    exposed = [str(info.value), repr(info.value), capture_warnings.text,
               str(info.value.__cause__), str(info.value.__context__ if not info.value.__suppress_context__ else "")]
    for text in exposed:
        assert all(v not in text for v in (_TOKEN, _USER, _PASS, "si3.bcentral.cl"))


def test_bcch_bad_token_is_not_retried(monkeypatch, no_sleep):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=_bcch_payload(None, codigo=-5))

    _mock_client(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="código -5"):
        market.fetch_usdclp_bcch(date(2024, 1, 1), date(2024, 1, 10), token=_TOKEN, retries=3)
    assert len(calls) == 1 and no_sleep == []


def test_bcch_user_password_fallback(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(request.url.params)
        return httpx.Response(200, json=_bcch_payload([]))

    _mock_client(monkeypatch, handler)
    assert market.fetch_usdclp_bcch(date(2024, 1, 1), date(2024, 1, 2), user=_USER, password=_PASS) == []
    assert seen["user"] == _USER and seen["pass"] == _PASS and "token" not in seen


def test_bcch_requires_some_credential():
    with pytest.raises(ValueError):
        market.fetch_usdclp_bcch(date(2024, 1, 1), date(2024, 1, 2))
