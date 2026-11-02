"""Tests de estrategias: payoffs de cada preset, primas netas y breakevens."""

import numpy as np
import pytest

from derivados101.forward import forward_rate
from derivados101.options import OptionLeg, garman_kohlhagen, leg_payoff
from derivados101.strategies import (
    PRESETS,
    breakevens,
    net_premium,
    spot_grid,
    strategy_pnl,
    zero_cost_strike,
)

S0 = 1000.0
KEY_SPOTS = np.array([900.0, 1000.0, 1100.0])
# Mercado de ejemplo: vol 12%, 6 meses, CLP 4,65%, USD 3,94%
MKT = (0.12, 0.5, 0.0465, 0.0394)


def build(key: str, spot: float = S0, mkt: tuple = MKT):
    return PRESETS[key].build(spot, *mkt)


def payoff_at(legs, spots):
    return sum(leg_payoff(leg, spots) for leg in legs)

# Payoff de las opciones SIN prima en S = 900 / 1000 / 1100 (spot inicial 1000)
EXPECTED_PAYOFF = {
    "long_call": [0, 0, 100],
    "long_put": [100, 0, 0],
    "short_call": [0, 0, -100],
    "short_put": [-100, 0, 0],
    "bull_call_spread": [0, 0, 50],
    "bear_put_spread": [50, 0, 0],
    "straddle": [100, 0, 100],
    "strangle": [50, 0, 50],
    "seagull_importer": [-70, 0, 50],
}


def test_all_required_presets_exist():
    assert set(EXPECTED_PAYOFF) | {"collar_importer", "collar_exporter"} <= set(PRESETS)
    for key, preset in PRESETS.items():
        assert preset.key == key
        assert preset.name and preset.description and preset.objective
        assert preset.suggested_exposure in ("none", "long_usd", "short_usd")


@pytest.mark.parametrize("key", sorted(EXPECTED_PAYOFF))
def test_preset_payoff_at_key_points(key):
    legs = build(key)
    payoff = payoff_at(legs, KEY_SPOTS)
    np.testing.assert_allclose(payoff, EXPECTED_PAYOFF[key], atol=1e-9)


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_preset_pnl_equals_payoff_minus_net_premium(key):
    legs = build(key)
    df = strategy_pnl(legs, KEY_SPOTS)
    payoff = sum(leg_payoff(leg, KEY_SPOTS) for leg in legs)
    np.testing.assert_allclose(df["options_pnl"], payoff - net_premium(legs))


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_premiums_are_garman_kohlhagen(key):
    """Cada prima es el precio GK de su pata (los collares, vía el strike resuelto)."""
    vol, years, r_dom, r_for = MKT
    for leg in build(key):
        gk = garman_kohlhagen(leg.kind, S0, leg.strike, years, r_dom, r_for, vol)
        assert leg.premium == pytest.approx(gk, abs=1e-6)


def test_net_premium_signs():
    call = net_premium(build("long_call"))
    assert call > 0
    assert net_premium(build("short_call")) == pytest.approx(-call)
    assert net_premium(build("short_put")) < 0
    straddle = net_premium(build("straddle"))
    assert straddle == pytest.approx(call + net_premium(build("long_put")))
    # spread: más barato que la call sola, pero sigue siendo débito
    spread = net_premium(build("bull_call_spread"))
    assert 0 < spread < call
    # strangle (OTM) más barato que straddle (ATM)
    assert 0 < net_premium(build("strangle")) < straddle


@pytest.mark.parametrize("key", ["collar_importer", "collar_exporter"])
@pytest.mark.parametrize(
    "mkt",
    [MKT, (0.05, 1.0, 0.08, 0.05), (0.25, 0.25, 0.03, 0.05), (0.12, 2.0, 0.0465, 0.0394)],
)
def test_collars_are_zero_cost(key, mkt):
    legs = build(key, 950.0, mkt)
    assert net_premium(legs) == pytest.approx(0, abs=1e-9)
    long_leg, short_leg = legs
    vol, years, r_dom, r_for = mkt
    gk_short = garman_kohlhagen(short_leg.kind, 950.0, short_leg.strike, years, r_dom, r_for, vol)
    assert gk_short == pytest.approx(long_leg.premium, abs=1e-5)


def test_collar_strikes_bracket_the_forward():
    vol, years, r_dom, r_for = MKT
    fwd = forward_rate(S0, r_dom, r_for, years)
    call, put = build("collar_importer")
    assert (call.kind, call.position, put.kind, put.position) == ("call", "long", "put", "short")
    assert call.strike == pytest.approx(S0 * 1.02)
    assert put.strike < fwd < call.strike
    put_e, call_e = build("collar_exporter")
    assert (put_e.kind, put_e.position, call_e.kind, call_e.position) == ("put", "long", "call", "short")
    assert put_e.strike == pytest.approx(S0 * 0.98)
    assert put_e.strike < fwd < call_e.strike


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("target", [0.5, 10.0, 40.0, 150.0])
def test_zero_cost_strike_matches_target(kind, target):
    vol, years, r_dom, r_for = MKT
    k = zero_cost_strike(kind, target, S0, years, r_dom, r_for, vol)
    assert garman_kohlhagen(kind, S0, k, years, r_dom, r_for, vol) == pytest.approx(target, abs=1e-5)


def test_zero_cost_strike_edge_cases():
    vol, years, r_dom, r_for = MKT
    fwd = forward_rate(S0, r_dom, r_for, years)
    # sin volatilidad la prima objetivo 0 se alcanza en el borde ≈ forward
    assert zero_cost_strike("put", 0.0, S0, years, r_dom, r_for, 0.0) == pytest.approx(fwd, rel=1e-6)
    with pytest.raises(ValueError):
        zero_cost_strike("put", -1.0, S0, years, r_dom, r_for, vol)
    with pytest.raises(ValueError):
        zero_cost_strike("forward", 1.0, S0, years, r_dom, r_for, vol)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        zero_cost_strike("call", 1.0, 0.0, years, r_dom, r_for, vol)


def test_seagull_is_not_zero_cost_in_general():
    assert abs(net_premium(build("seagull_importer"))) > 0.01


def test_strategy_pnl_columns_and_exposure():
    legs = build("long_call")
    premium = net_premium(legs)
    spots = spot_grid(S0, 0.1, 21)
    df = strategy_pnl(legs, spots, exposure="short_usd", spot0=S0, exposure_usd=1.0)
    assert list(df.columns) == ["spot", "options_pnl", "underlying_pnl", "combined_pnl"]
    np.testing.assert_allclose(df["underlying_pnl"], S0 - spots)
    np.testing.assert_allclose(df["combined_pnl"], df["options_pnl"] + df["underlying_pnl"])
    # call comprada + pasivo en USD = pérdida máxima acotada a la prima
    assert df["combined_pnl"].min() == pytest.approx(-premium)
    long_df = strategy_pnl([], spots, exposure="long_usd", spot0=S0, exposure_usd=2)
    np.testing.assert_allclose(long_df["underlying_pnl"], (spots - S0) * 2)
    none_df = strategy_pnl(legs, spots)
    assert (none_df["underlying_pnl"] == 0).all()


def test_spot0_defaults_to_grid_center():
    spots = spot_grid(S0, 0.1, 21)
    a = strategy_pnl([], spots, exposure="long_usd")
    b = strategy_pnl([], spots, exposure="long_usd", spot0=S0)
    np.testing.assert_allclose(a["underlying_pnl"], b["underlying_pnl"])


def test_collar_importer_bounds_combined_result():
    call, put = build("collar_importer")
    df = strategy_pnl([call, put], spot_grid(S0), exposure="short_usd", spot0=S0)
    # costo cero: la banda va del strike de la put (piso) al de la call (techo)
    assert df["combined_pnl"].min() == pytest.approx(S0 - call.strike)
    assert df["combined_pnl"].max() == pytest.approx(S0 - put.strike)


def test_spot_grid():
    g = spot_grid(900, 0.2, 401)
    assert g[0] == pytest.approx(720) and g[-1] == pytest.approx(1080)
    assert g[200] == pytest.approx(900)
    with pytest.raises(ValueError):
        spot_grid(900, 1.5)


# --- Breakevens ------------------------------------------------------------ #


def test_breakeven_long_call():
    legs = build("long_call")
    spots = spot_grid(S0)
    df = strategy_pnl(legs, spots)
    assert breakevens(spots, df["options_pnl"].to_numpy()) == pytest.approx([S0 + legs[0].premium])


def test_breakeven_straddle_two_points():
    legs = build("straddle")
    total = net_premium(legs)
    spots = spot_grid(S0)
    df = strategy_pnl(legs, spots)
    assert breakevens(spots, df["options_pnl"].to_numpy()) == pytest.approx([S0 - total, S0 + total])


def test_breakeven_interpolates_between_grid_points():
    leg = OptionLeg(kind="call", position="long", strike=1000, premium=12.3)
    spots = np.linspace(900, 1100, 11)  # paso de 20: 1012,3 no está en la grilla
    df = strategy_pnl([leg], spots)
    assert breakevens(spots, df["options_pnl"].to_numpy()) == pytest.approx([1012.3])


def test_breakeven_edge_cases():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert breakevens(x, np.array([1, 1, 1, 1, 1.0])) == []
    assert breakevens(x, np.array([-1, 0, 0, 0, 1.0])) == [3.0]  # tramo plano que cruza
    assert breakevens(x, np.array([1, 0, 0, 0, 1.0])) == []  # toca y vuelve: no cruza
    assert breakevens(x, np.array([-2, -1, 0, 1, 2.0])) == [3.0]
    with pytest.raises(ValueError):
        breakevens(x, np.array([1.0, 2.0]))
