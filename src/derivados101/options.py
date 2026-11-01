"""Opciones de moneda (USD/CLP): payoffs, valorización y griegas.

Una opción da el DERECHO (no la obligación) de comprar (*call*) o vender
(*put*) dólares a un precio fijado (*strike*, K). Ese derecho cuesta una
*prima*. Su valor tiene dos partes:

- **Valor intrínseco**: lo que valdría ejercerla ahora mismo.
- **Valor temporal**: lo que se paga por la posibilidad de que el dólar se
  mueva a favor antes del vencimiento (crece con la volatilidad y el plazo).

Para valorizar usamos Garman-Kohlhagen (1983), que es Black-Scholes adaptado a
monedas: el dólar "paga" la tasa USD igual que una acción paga dividendos.

Convención de tasas: el resto del proyecto usa tasas con capitalización
compuesta anual ``(1 + r) ** T``. Las fórmulas de opciones usan tasas
continuas, así que convertimos con ``r_c = ln(1 + r)``. Así el forward implícito
en las opciones es exactamente el mismo que :func:`derivados101.forward.forward_rate`.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "OptionKind",
    "OptionLeg",
    "Position",
    "binomial_price",
    "garman_kohlhagen",
    "greeks",
    "intrinsic_value",
    "leg_payoff",
    "leg_pnl",
    "moneyness",
    "premium_from_pct",
    "time_value",
]

OptionKind = Literal["call", "put"]
Position = Literal["long", "short"]


class OptionLeg(BaseModel):
    """Una "pata" de una estrategia: una opción comprada o vendida.

    Atributos:
        kind: ``"call"`` (derecho a comprar USD) o ``"put"`` (derecho a vender USD).
        position: ``"long"`` (la compro, pago prima) o ``"short"`` (la vendo, cobro prima).
        strike: precio de ejercicio en CLP por USD (> 0).
        notional_usd: dólares cubiertos por la opción (> 0).
        premium: prima en CLP por cada USD de nocional (>= 0). Se paga si es
            long y se recibe si es short.
    """

    model_config = ConfigDict(frozen=True)

    kind: OptionKind
    position: Position
    strike: float = Field(gt=0)
    notional_usd: float = Field(default=1.0, gt=0)
    premium: float = Field(default=0.0, ge=0)

    @property
    def sign(self) -> int:
        """+1 para posiciones compradas, -1 para vendidas."""
        return 1 if self.position == "long" else -1


# --------------------------------------------------------------------------- #
# Helpers matemáticos
# --------------------------------------------------------------------------- #


def _norm_cdf(x: float) -> float:
    """Distribución normal estándar acumulada, N(x), usando ``math.erf``."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Densidad normal estándar, n(x)."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _cont(r: float) -> float:
    """Convierte una tasa compuesta anual a tasa continua equivalente: ln(1 + r)."""
    if r <= -1:
        raise ValueError("la tasa debe ser > -100%")
    return math.log1p(r)


def _check_kind(kind: str) -> None:
    if kind not in ("call", "put"):
        raise ValueError(f"kind debe ser 'call' o 'put', no {kind!r}")


# --------------------------------------------------------------------------- #
# Al vencimiento
# --------------------------------------------------------------------------- #


def intrinsic_value(kind: OptionKind, spot, strike: float):
    """Valor intrínseco por USD: lo que vale ejercer la opción ahora.

    - call: ``max(S - K, 0)`` → conviene si el dólar está sobre el strike.
    - put:  ``max(K - S, 0)`` → conviene si el dólar está bajo el strike.

    Acepta un número o un arreglo de numpy en ``spot`` (devuelve el mismo tipo).
    Nunca es negativo: si no conviene ejercer, simplemente no se ejerce.
    """
    _check_kind(kind)
    diff = (spot - strike) if kind == "call" else (strike - spot)
    if isinstance(diff, np.ndarray):
        return np.maximum(diff, 0.0)
    return max(float(diff), 0.0)


def moneyness(
    kind: OptionKind, spot: float, strike: float, atm_tol: float = 0.005
) -> Literal["ITM", "ATM", "OTM"]:
    """Clasifica la opción como ITM / ATM / OTM.

    - ATM (*at the money*): spot y strike a menos de ``atm_tol`` (0,5%) de distancia.
    - ITM (*in the money*): tiene valor intrínseco (call: S > K; put: S < K).
    - OTM (*out of the money*): no tiene valor intrínseco.
    """
    _check_kind(kind)
    if abs(spot / strike - 1.0) <= atm_tol:
        return "ATM"
    itm = spot > strike if kind == "call" else spot < strike
    return "ITM" if itm else "OTM"


def leg_payoff(leg: OptionLeg, spots: np.ndarray) -> np.ndarray:
    """Payoff de una pata al vencimiento, en CLP, SIN considerar la prima.

    ``signo * nocional * valor_intrínseco(S)``. Una opción vendida (short)
    tiene el payoff opuesto: lo que gana el comprador lo paga el vendedor.
    """
    s = np.asarray(spots, dtype=float)
    return leg.sign * leg.notional_usd * intrinsic_value(leg.kind, s, leg.strike)


def leg_pnl(leg: OptionLeg, spots: np.ndarray) -> np.ndarray:
    """Resultado (PnL) de una pata al vencimiento, en CLP, CON la prima.

    Long: payoff − prima pagada. Short: payoff (negativo) + prima cobrada.
    """
    return leg_payoff(leg, spots) - leg.sign * leg.premium * leg.notional_usd


# --------------------------------------------------------------------------- #
# Valorización antes del vencimiento
# --------------------------------------------------------------------------- #


def _d1_d2(spot, strike, years, rd, rf, vol) -> tuple[float, float]:
    """d1 y d2 de Garman-Kohlhagen (con tasas continuas rd, rf)."""
    sig_t = vol * math.sqrt(years)
    d1 = (math.log(spot / strike) + (rd - rf + 0.5 * vol * vol) * years) / sig_t
    return d1, d1 - sig_t


def garman_kohlhagen(
    kind: OptionKind,
    spot: float,
    strike: float,
    years: float,
    r_dom: float,
    r_for: float,
    vol: float,
) -> float:
    """Precio teórico de una opción europea sobre USD/CLP (CLP por USD).

    Fórmula de Garman-Kohlhagen (Black-Scholes para monedas), con tasas
    continuas ``rd = ln(1 + r_dom)`` y ``rf = ln(1 + r_for)``:

    - call = ``S·e^(−rf·T)·N(d1) − K·e^(−rd·T)·N(d2)``
    - put  = ``K·e^(−rd·T)·N(−d2) − S·e^(−rf·T)·N(−d1)``

    Casos borde: con ``years <= 0`` devuelve el valor intrínseco; con
    ``vol <= 0`` devuelve el valor intrínseco del forward descontado (sin
    incertidumbre, no hay valor temporal por volatilidad).
    """
    _check_kind(kind)
    if spot <= 0 or strike <= 0:
        raise ValueError("spot y strike deben ser > 0")
    if years <= 0:
        return intrinsic_value(kind, spot, strike)
    rd, rf = _cont(r_dom), _cont(r_for)
    df_d, df_f = math.exp(-rd * years), math.exp(-rf * years)
    if vol <= 0:
        diff = spot * df_f - strike * df_d
        return max(diff, 0.0) if kind == "call" else max(-diff, 0.0)
    d1, d2 = _d1_d2(spot, strike, years, rd, rf, vol)
    if kind == "call":
        return spot * df_f * _norm_cdf(d1) - strike * df_d * _norm_cdf(d2)
    return strike * df_d * _norm_cdf(-d2) - spot * df_f * _norm_cdf(-d1)


def greeks(
    kind: OptionKind,
    spot: float,
    strike: float,
    years: float,
    r_dom: float,
    r_for: float,
    vol: float,
) -> dict[str, float]:
    """Griegas de Garman-Kohlhagen: sensibilidades del precio a cada insumo.

    Claves devueltas (todas por USD de nocional, en CLP salvo delta/gamma):
        delta: cambio de precio por +1 CLP en el spot (entre 0 y 1 para call,
            entre −1 y 0 para put). Aprox. "cuántos USD equivale" la opción.
        gamma: cambio de la delta por +1 CLP en el spot.
        vega:  cambio de precio por +1 punto de volatilidad (0,01).
        theta: cambio de precio por el paso de UN día (``/365``); suele ser
            negativo: el valor temporal se "derrite".
        rho:   cambio de precio por +1 punto (0,01) en la tasa en pesos
            ``r_dom`` (expresada, como todo el proyecto, en compuesta anual).

    Si ``years <= 0`` o ``vol <= 0`` devuelve delta escalón y el resto en 0.
    """
    _check_kind(kind)
    if years <= 0 or vol <= 0:
        itm = spot > strike if kind == "call" else spot < strike
        delta = (1.0 if kind == "call" else -1.0) if itm else 0.0
        return {"delta": delta, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}

    rd, rf = _cont(r_dom), _cont(r_for)
    df_d, df_f = math.exp(-rd * years), math.exp(-rf * years)
    d1, d2 = _d1_d2(spot, strike, years, rd, rf, vol)
    sqrt_t = math.sqrt(years)
    pdf_d1 = _norm_pdf(d1)

    gamma = df_f * pdf_d1 / (spot * vol * sqrt_t)
    vega = spot * df_f * pdf_d1 * sqrt_t
    decay = -spot * df_f * pdf_d1 * vol / (2 * sqrt_t)  # parte común de theta
    if kind == "call":
        delta = df_f * _norm_cdf(d1)
        theta_year = decay + rf * spot * df_f * _norm_cdf(d1) - rd * strike * df_d * _norm_cdf(d2)
        rho_cont = strike * years * df_d * _norm_cdf(d2)
    else:
        delta = -df_f * _norm_cdf(-d1)
        theta_year = decay - rf * spot * df_f * _norm_cdf(-d1) + rd * strike * df_d * _norm_cdf(-d2)
        rho_cont = -strike * years * df_d * _norm_cdf(-d2)

    # rho respecto de la tasa compuesta anual: dV/dr = dV/dr_c * dr_c/dr = dV/dr_c / (1 + r)
    rho = rho_cont / (1 + r_dom)
    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega * 0.01,
        "theta": theta_year / 365.0,
        "rho": rho * 0.01,
    }


def binomial_price(
    kind: OptionKind,
    spot: float,
    strike: float,
    years: float,
    r_dom: float,
    r_for: float,
    vol: float,
    steps: int = 200,
    american: bool = False,
) -> float:
    """Precio por árbol binomial de Cox-Ross-Rubinstein (CRR).

    El dólar puede subir (``u = e^(σ√dt)``) o bajar (``d = 1/u``) en cada paso.
    Con la probabilidad neutral al riesgo ``p = (e^((rd−rf)·dt) − d) / (u − d)``
    se calcula el valor esperado descontado desde el vencimiento hacia hoy.

    - Europea: con muchos pasos converge al precio de Garman-Kohlhagen.
    - Americana (``american=True``): en cada nodo se compara con ejercer de
      inmediato, por eso nunca vale menos que la europea.
    """
    _check_kind(kind)
    if steps < 1:
        raise ValueError("steps debe ser >= 1")
    if years <= 0 or vol <= 0:
        return garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
    rd, rf = _cont(r_dom), _cont(r_for)
    dt = years / steps
    u = math.exp(vol * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((rd - rf) * dt) - d) / (u - d)
    if not 0.0 <= p <= 1.0:
        raise ValueError("probabilidad neutral al riesgo fuera de [0, 1]: aumenta steps")
    disc = math.exp(-rd * dt)

    # Spots al vencimiento: S·u^(n−j)·d^j, j = 0..n (de más alto a más bajo)
    j = np.arange(steps + 1)
    spots = spot * u ** (steps - j) * d**j
    values = intrinsic_value(kind, spots, strike)
    for n in range(steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        if american:
            j = np.arange(n + 1)
            spots = spot * u ** (n - j) * d**j  # spots del paso n
            values = np.maximum(values, intrinsic_value(kind, spots, strike))
    return float(values[0])


def time_value(
    kind: OptionKind,
    spot: float,
    strike: float,
    years: float,
    r_dom: float,
    r_for: float,
    vol: float,
) -> float:
    """Valor temporal = precio Garman-Kohlhagen − valor intrínseco.

    Ojo: en puts europeas muy ITM (y en calls muy ITM cuando ``r_for`` es alta)
    puede salir levemente NEGATIVO. No es un error: una opción europea no se
    puede ejercer antes, y el valor intrínseco "hoy" no descuenta el plazo,
    mientras que el precio sí lo hace (``K·e^(−rd·T)`` es menor que ``K``).
    """
    price = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
    return price - intrinsic_value(kind, spot, strike)


def premium_from_pct(pct: float, reference_price: float) -> float:
    """Convierte una prima expresada en % (como en la planilla) a CLP por USD.

    Ej.: prima 2% sobre un spot de 900 → 18 CLP por USD de nocional.
    """
    return pct * reference_price
