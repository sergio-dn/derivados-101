"""Tests de estrategias: payoffs de cada preset, primas netas y breakevens."""

import numpy as np
import pytest

from derivados101.options import OptionLeg, leg_payoff
from derivados101.strategies import (
    PRESETS,
    breakevens,
    net_premium,
    spot_grid,
    strategy_pnl,
)

S0 = 1000.0
KEY_SPOTS = np.array([900.0, 1000.0, 1100.0])

# Payoff de las opciones SIN prima en S = 900 / 1000 / 1100 (spot inicial 1000)
EXPECTED_PAYOFF = {
    "long_call": [0, 0, 100],
    "long_put": [100, 0, 0],
    "short_call": [0, 0, -100],
    "short_put": [-100, 0, 0],
    "bull_call_spread": [0, 0, 50],
    "bear_put_spread": [50, 0, 0],
    "collar_importer": [-80, 0, 80],
    "collar_exporter": [80, 0, -80],
    "straddle": [100, 0, 100],
    "strangle": [50, 0, 50],
    "seagull_importer": [-70, 0, 50],
}


def test_all_required_presets_exist():
    assert set(EXPECTED_PAYOFF) <= set(PRESETS)
    for key, preset in PRESETS.items():
        assert preset.key == key
        assert preset.name and preset.description and preset.objective
        assert preset.suggested_exposure in ("none", "long_usd", "short_usd")


@pytest.mark.parametrize("key", sorted(EXPECTED_PAYOFF))
def test_preset_payoff_at_key_points(key):
    legs = PRESETS[key].build(S0, 0.02)
    payoff = sum(leg_payoff(leg, KEY_SPOTS) for leg in legs)
    np.testing.assert_allclose(payoff, EXPECTED_PAYOFF[key], atol=1e-9)


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_preset_pnl_equals_payoff_minus_net_premium(key):
    legs = PRESETS[key].build(S0, 0.02)
    df = strategy_pnl(legs, KEY_SPOTS)
    payoff = sum(leg_payoff(leg, KEY_SPOTS) for leg in legs)
    np.testing.assert_allclose(df["options_pnl"], payoff - net_premium(legs))


def test_net_premium_signs():
    assert net_premium(PRESETS["long_call"].build(S0, 0.02)) == pytest.approx(20)
    assert net_premium(PRESETS["short_put"].build(S0, 0.02)) == pytest.approx(-20)
    assert net_premium(PRESETS["straddle"].build(S0, 0.02)) == pytest.approx(40)
    # spread: más barato que la call sola, pero sigue siendo débito
    spread = net_premium(PRESETS["bull_call_spread"].build(S0, 0.02))
    assert 0 < spread < 20
    # collar simétrico: costo cero con la aproximación de primas
    assert net_premium(PRESETS["collar_importer"].build(S0, 0.02)) == pytest.approx(0, abs=1e-9)


def test_otm_legs_are_cheaper_and_itm_include_intrinsic():
    strangle = PRESETS["strangle"].build(S0, 0.02)
    assert all(leg.premium == pytest.approx(10) for leg in strangle)  # 5% OTM -> 50%


def test_strategy_pnl_columns_and_exposure():
    legs = PRESETS["long_call"].build(S0, 0.02)
    spots = spot_grid(S0, 0.1, 21)
    df = strategy_pnl(legs, spots, exposure="short_usd", spot0=S0, exposure_usd=1.0)
    assert list(df.columns) == ["spot", "options_pnl", "underlying_pnl", "combined_pnl"]
    np.testing.assert_allclose(df["underlying_pnl"], S0 - spots)
    np.testing.assert_allclose(df["combined_pnl"], df["options_pnl"] + df["underlying_pnl"])
    # call comprada + pasivo en USD = pérdida máxima acotada a la prima
    assert df["combined_pnl"].min() == pytest.approx(-20)
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
    legs = PRESETS["collar_importer"].build(S0, 0.02)
    df = strategy_pnl(legs, spot_grid(S0), exposure="short_usd", spot0=S0)
    # banda: pierde a lo más 20 (techo 1020) y gana a lo más 20 (piso 980)
    assert df["combined_pnl"].min() == pytest.approx(-20)
    assert df["combined_pnl"].max() == pytest.approx(20)


def test_spot_grid():
    g = spot_grid(900, 0.2, 401)
    assert g[0] == pytest.approx(720) and g[-1] == pytest.approx(1080)
    assert g[200] == pytest.approx(900)
    with pytest.raises(ValueError):
        spot_grid(900, 1.5)


# --- Breakevens ------------------------------------------------------------ #


def test_breakeven_long_call():
    legs = PRESETS["long_call"].build(S0, 0.02)
    spots = spot_grid(S0)
    df = strategy_pnl(legs, spots)
    assert breakevens(spots, df["options_pnl"].to_numpy()) == pytest.approx([1020])


def test_breakeven_straddle_two_points():
    legs = PRESETS["straddle"].build(S0, 0.02)
    spots = spot_grid(S0)
    df = strategy_pnl(legs, spots)
    assert breakevens(spots, df["options_pnl"].to_numpy()) == pytest.approx([960, 1040])


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
