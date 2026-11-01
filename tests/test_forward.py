"""Tests de forwards: cuadran con la hoja "Fwd" de la planilla."""

import pytest

from derivados101.forward import (
    forward_mtm,
    forward_points,
    forward_rate,
    settle_forward,
    synthetic_forward,
)


def test_forward_rate_matches_spreadsheet():
    fwd = forward_rate(890, 0.0511, 0.0407, 1)
    assert fwd == pytest.approx(898.89, abs=0.005)
    assert forward_points(890, fwd) == pytest.approx(8.89, abs=0.005)


def test_forward_rate_zero_years_is_spot():
    assert forward_rate(900, 0.05, 0.04, 0) == 900


def test_synthetic_forward_matches_spreadsheet():
    syn = synthetic_forward(500_000, 890, 0.0511, 0.0407, 1)
    assert syn.debt_clp_today == pytest.approx(445_000_000)
    assert syn.debt_clp_maturity == pytest.approx(445_000_000 * 1.0511)
    assert syn.usd_maturity == pytest.approx(500_000 * 1.0407)
    assert syn.implied_rate == pytest.approx(898.89, abs=0.005)
    assert syn.implied_points == pytest.approx(8.89, abs=0.005)
    assert syn.implied_rate == pytest.approx(forward_rate(890, 0.0511, 0.0407, 1))


def test_settlement_spreadsheet_example_buy():
    st = settle_forward(500_000, 948.91, 900, side="buy")
    assert st.compensation_clp == pytest.approx(-24_455_000)
    assert st.full_delivery_clp == pytest.approx(474_455_000)
    assert st.market_value_clp == pytest.approx(450_000_000)
    # costo efectivo del importador = valor de mercado − compensación = N·K
    assert st.market_value_clp - st.compensation_clp == pytest.approx(st.full_delivery_clp)


def test_settlement_sell_is_mirror():
    buy = settle_forward(500_000, 948.91, 900, side="buy")
    sell = settle_forward(500_000, 948.91, 900, side="sell")
    assert sell.compensation_clp == pytest.approx(-buy.compensation_clp)


def test_invalid_side_raises():
    with pytest.raises(ValueError):
        settle_forward(1, 900, 900, side="hold")


def test_mtm_at_inception_is_zero_and_at_maturity_is_compensation():
    k = forward_rate(890, 0.0511, 0.0407, 1)
    assert forward_mtm(500_000, k, 890, 0.0511, 0.0407, 1) == pytest.approx(0, abs=1e-6)
    st = settle_forward(500_000, k, 920)
    assert forward_mtm(500_000, k, 920, 0.0511, 0.0407, 0) == pytest.approx(st.compensation_clp)
    assert forward_mtm(500_000, k, 920, 0.0511, 0.0407, 0, side="sell") == pytest.approx(
        -st.compensation_clp
    )


def test_mtm_is_discounted():
    k = 900.0
    mtm = forward_mtm(1_000, k, 950, 0.05, 0.05, 0.5)  # tasas iguales -> F_t = spot
    assert mtm == pytest.approx(1_000 * 50 / 1.05**0.5)
