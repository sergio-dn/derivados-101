"""Tests de opciones: payoffs, Garman-Kohlhagen, binomial y griegas."""

import math

import numpy as np
import pytest
from pydantic import ValidationError

from derivados101.forward import forward_rate
from derivados101.options import (
    OptionLeg,
    binomial_price,
    garman_kohlhagen,
    greeks,
    intrinsic_value,
    leg_payoff,
    leg_pnl,
    moneyness,
    premium_from_pct,
    time_value,
)

BASE = {"spot": 900.0, "years": 0.5, "r_dom": 0.0511, "r_for": 0.0407, "vol": 0.12}
STRIKES = [800.0, 880.0, 900.0, 920.0, 1000.0]


def gk(kind, strike, **over):
    p = {**BASE, **over}
    return garman_kohlhagen(kind, p["spot"], strike, p["years"], p["r_dom"], p["r_for"], p["vol"])


# --- Al vencimiento -------------------------------------------------------- #


def test_intrinsic_value_scalar_and_array():
    assert intrinsic_value("call", 950, 900) == 50
    assert intrinsic_value("call", 850, 900) == 0
    assert intrinsic_value("put", 850, 900) == 50
    arr = intrinsic_value("put", np.array([800.0, 900.0, 1000.0]), 900)
    np.testing.assert_allclose(arr, [100, 0, 0])


def test_moneyness():
    assert moneyness("call", 950, 900) == "ITM"
    assert moneyness("put", 950, 900) == "OTM"
    assert moneyness("put", 850, 900) == "ITM"
    assert moneyness("call", 902, 900) == "ATM"  # dentro del 0,5%


def test_leg_payoff_and_pnl_signs():
    spots = np.array([850.0, 900.0, 950.0])
    long_call = OptionLeg(kind="call", position="long", strike=900, notional_usd=10, premium=5)
    short_call = long_call.model_copy(update={"position": "short"})
    np.testing.assert_allclose(leg_payoff(long_call, spots), [0, 0, 500])
    np.testing.assert_allclose(leg_pnl(long_call, spots), [-50, -50, 450])
    np.testing.assert_allclose(leg_pnl(short_call, spots), [50, 50, -450])


def test_option_leg_validation_and_frozen():
    with pytest.raises(ValidationError):
        OptionLeg(kind="call", position="long", strike=0)
    with pytest.raises(ValidationError):
        OptionLeg(kind="call", position="long", strike=900, premium=-1)
    with pytest.raises(ValidationError):
        OptionLeg(kind="swap", position="long", strike=900)
    leg = OptionLeg(kind="put", position="short", strike=900)
    with pytest.raises(ValidationError):
        leg.strike = 1000


def test_premium_from_pct():
    assert premium_from_pct(0.02, 900) == pytest.approx(18)


# --- Garman-Kohlhagen ------------------------------------------------------ #


@pytest.mark.parametrize("strike", STRIKES)
def test_put_call_parity(strike):
    """C − P = S·(1+rf)^−T − K·(1+rd)^−T, equivalente a (F − K) descontado."""
    s, t, rd, rf = BASE["spot"], BASE["years"], BASE["r_dom"], BASE["r_for"]
    lhs = gk("call", strike) - gk("put", strike)
    rhs = s / (1 + rf) ** t - strike / (1 + rd) ** t
    assert lhs == pytest.approx(rhs, abs=1e-9)
    fwd = forward_rate(s, rd, rf, t)
    assert lhs == pytest.approx((fwd - strike) / (1 + rd) ** t, abs=1e-9)


def test_gk_known_value():
    # Valor de referencia calculado a mano con tasas continuas ln(1+r)
    rd, rf = math.log(1.05), math.log(1.04)
    s, k, t, v = 100.0, 100.0, 1.0, 0.2
    d1 = (math.log(s / k) + (rd - rf + 0.5 * v * v) * t) / (v * math.sqrt(t))
    d2 = d1 - v * math.sqrt(t)

    def n(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    expected = s * math.exp(-rf * t) * n(d1) - k * math.exp(-rd * t) * n(d2)
    assert garman_kohlhagen("call", s, k, t, 0.05, 0.04, v) == pytest.approx(expected)


def test_gk_edge_cases():
    assert gk("call", 850, years=0) == pytest.approx(50)
    assert gk("put", 850, years=0) == 0
    # sin volatilidad: forward descontado contra strike
    fwd = forward_rate(900, BASE["r_dom"], BASE["r_for"], 0.5)
    assert gk("call", 850, vol=0) == pytest.approx((fwd - 850) / (1 + BASE["r_dom"]) ** 0.5)
    assert gk("put", 850, vol=0) == 0


def test_price_increases_with_vol_and_bounds():
    for kind in ("call", "put"):
        assert gk(kind, 900, vol=0.20) > gk(kind, 900, vol=0.10)
    assert 0 <= gk("call", 900) <= BASE["spot"]


@pytest.mark.parametrize("kind", ["call", "put"])
def test_time_value_atm_positive(kind):
    tv = time_value(kind, 900, 900, 0.5, 0.0511, 0.0407, 0.12)
    assert tv > 0
    assert tv == pytest.approx(gk(kind, 900))


def test_time_value_can_be_negative_for_deep_itm_european_put():
    # rd alta, put muy ITM: el precio descuenta K y queda bajo el intrínseco
    tv = time_value("put", 600, 900, 2.0, 0.10, 0.0, 0.05)
    assert tv < 0


# --- Binomial -------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", STRIKES)
def test_binomial_european_converges_to_gk(kind, strike):
    p = BASE
    ref = gk(kind, strike)
    tree = binomial_price(kind, p["spot"], strike, p["years"], p["r_dom"], p["r_for"], p["vol"],
                          steps=500)
    assert abs(tree - ref) / ref < 0.005


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", STRIKES)
def test_american_ge_european(kind, strike):
    p = BASE
    args = (kind, p["spot"], strike, p["years"], p["r_dom"], p["r_for"], p["vol"])
    assert binomial_price(*args, american=True) >= binomial_price(*args) - 1e-12


def test_american_put_early_exercise_premium():
    # put muy ITM con tasa CLP alta: ejercer anticipado vale la pena
    args = ("put", 600, 900, 2.0, 0.10, 0.0, 0.05)
    assert binomial_price(*args, american=True) > binomial_price(*args) + 1
    assert binomial_price(*args, american=True) >= intrinsic_value("put", 600, 900) - 1e-9


# --- Griegas vs diferencias finitas --------------------------------------- #


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", [880.0, 900.0, 920.0])
def test_greeks_vs_finite_differences(kind, strike):
    s, t, rd, rf, v = BASE["spot"], BASE["years"], BASE["r_dom"], BASE["r_for"], BASE["vol"]
    g = greeks(kind, s, strike, t, rd, rf, v)

    def price(s=s, t=t, rd=rd, v=v):
        return garman_kohlhagen(kind, s, strike, t, rd, rf, v)

    h = 0.01
    delta_fd = (price(s=s + h) - price(s=s - h)) / (2 * h)
    gamma_fd = (price(s=s + 1) - 2 * price() + price(s=s - 1)) / 1.0
    vega_fd = (price(v=v + 1e-4) - price(v=v - 1e-4)) / 2e-4 * 0.01
    theta_fd = (price(t=t - 1 / 365) - price())  # un día menos de plazo
    rho_fd = (price(rd=rd + 1e-5) - price(rd=rd - 1e-5)) / 2e-5 * 0.01

    assert g["delta"] == pytest.approx(delta_fd, rel=1e-5)
    assert g["gamma"] == pytest.approx(gamma_fd, rel=1e-3)
    assert g["vega"] == pytest.approx(vega_fd, rel=1e-5)
    assert g["theta"] == pytest.approx(theta_fd, rel=1e-2)
    assert g["rho"] == pytest.approx(rho_fd, rel=1e-5)


def test_greeks_signs_and_expiry():
    c = greeks("call", 900, 900, 0.5, 0.0511, 0.0407, 0.12)
    p = greeks("put", 900, 900, 0.5, 0.0511, 0.0407, 0.12)
    assert 0 < c["delta"] < 1 and -1 < p["delta"] < 0
    assert c["gamma"] == pytest.approx(p["gamma"])
    assert c["vega"] == pytest.approx(p["vega"])
    assert c["rho"] > 0 > p["rho"]
    expired = greeks("call", 950, 900, 0, 0.05, 0.04, 0.1)
    assert expired == {"delta": 1.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
