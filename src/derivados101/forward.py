"""Forwards de moneda (USD/CLP).

Un *forward* es un contrato para comprar o vender dólares en una fecha futura
a un precio fijado HOY. Ese precio no es una "predicción" del dólar: sale de
un arbitraje entre las tasas de interés de cada moneda (paridad de tasas).

Idea clave ("derivado sintético", hoja Fwd de la planilla): si hoy pido pesos
prestados, compro dólares al spot y los invierto en USD, al vencimiento debo
cierta cantidad de CLP y tengo cierta cantidad de USD. El cociente entre ambos
es el tipo de cambio que "me aseguré" sin firmar ningún derivado. Si un banco
cotizara un forward distinto, habría arbitraje.

Convenciones: precios en CLP por USD, plazos en años, tasas como decimales
(0.0511 = 5,11%) y capitalización compuesta anual ``(1 + r) ** T``.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Settlement",
    "SyntheticForward",
    "forward_mtm",
    "forward_points",
    "forward_rate",
    "settle_forward",
    "synthetic_forward",
]

_VALID_SIDES = ("buy", "sell")


def _side_sign(side: str) -> int:
    """+1 si la empresa COMPRA dólares a plazo, -1 si los VENDE."""
    if side not in _VALID_SIDES:
        raise ValueError(f"side debe ser 'buy' o 'sell', no {side!r}")
    return 1 if side == "buy" else -1


def forward_rate(spot: float, r_dom: float, r_for: float, years: float) -> float:
    """Tipo de cambio forward por paridad de tasas de interés.

    ``F = spot * (1 + r_dom) ** T / (1 + r_for) ** T``

    - ``r_dom``: tasa en pesos (moneda doméstica, la del precio).
    - ``r_for``: tasa en dólares (moneda extranjera, el "activo").

    Si la tasa en pesos es mayor que la tasa en dólares, el forward queda
    sobre el spot (puntos forward positivos): el peso "paga" más interés, y
    eso se compensa con un dólar más caro a plazo.

    Ejemplo de la planilla: ``forward_rate(890, 0.0511, 0.0407, 1) ≈ 898,89``.
    """
    if spot <= 0:
        raise ValueError("spot debe ser > 0")
    if years < 0:
        raise ValueError("years no puede ser negativo")
    return spot * (1 + r_dom) ** years / (1 + r_for) ** years


def forward_points(spot: float, fwd: float) -> float:
    """Puntos forward: diferencia entre el forward y el spot (``fwd - spot``).

    Es la forma en que los bancos suelen cotizar: "spot + X puntos".
    """
    return fwd - spot


@dataclass(frozen=True)
class SyntheticForward:
    """Resultado paso a paso del "derivado sintético" (hoja Fwd).

    Atributos:
        nominal_usd: dólares que la empresa necesitará al vencimiento.
        spot, r_dom, r_for, years: insumos de mercado.
        debt_clp_today: pesos que pido prestados hoy para comprar los USD (``N * spot``).
        debt_clp_maturity: pesos que debo devolver al vencimiento (con interés en CLP).
        usd_maturity: dólares que tendré al vencimiento (invertidos a la tasa USD).
        implied_rate: tipo de cambio implícito = deuda CLP final / USD finales.
        implied_points: ``implied_rate - spot``.
    """

    nominal_usd: float
    spot: float
    r_dom: float
    r_for: float
    years: float
    debt_clp_today: float
    debt_clp_maturity: float
    usd_maturity: float
    implied_rate: float
    implied_points: float


def synthetic_forward(
    nominal_usd: float, spot: float, r_dom: float, r_for: float, years: float
) -> SyntheticForward:
    """Construye el forward "a mano" con préstamos y depósitos.

    Pasos:
        1. Pido ``nominal_usd * spot`` pesos y compro los dólares hoy.
        2. Mi deuda en pesos crece a la tasa CLP: ``* (1 + r_dom) ** T``.
        3. Mis dólares crecen a la tasa USD: ``* (1 + r_for) ** T``.
        4. Tipo de cambio implícito = pesos que debo / dólares que tengo.

    El resultado coincide con :func:`forward_rate` (el nominal se cancela):
    por eso el forward se deriva de las tasas y no de una opinión del mercado.
    """
    if nominal_usd <= 0:
        raise ValueError("nominal_usd debe ser > 0")
    debt_today = nominal_usd * spot
    debt_maturity = debt_today * (1 + r_dom) ** years
    usd_maturity = nominal_usd * (1 + r_for) ** years
    implied = debt_maturity / usd_maturity
    return SyntheticForward(
        nominal_usd=nominal_usd,
        spot=spot,
        r_dom=r_dom,
        r_for=r_for,
        years=years,
        debt_clp_today=debt_today,
        debt_clp_maturity=debt_maturity,
        usd_maturity=usd_maturity,
        implied_rate=implied,
        implied_points=implied - spot,
    )


@dataclass(frozen=True)
class Settlement:
    """Liquidación de un forward al vencimiento.

    Atributos:
        nominal_usd: monto del contrato en USD.
        fwd_rate: precio pactado (K).
        spot_at_maturity: dólar observado al vencimiento (S).
        side: ``"buy"`` (la empresa compra USD) o ``"sell"`` (los vende).
        full_delivery_clp: pesos que la empresa paga (buy) o recibe (sell) si hay
            entrega física: ``N * K``.
        market_value_clp: lo que valen esos dólares al spot final: ``N * S``.
        compensation_clp: liquidación por diferencia (non-delivery). Positivo =
            la empresa RECIBE. buy: ``(S - K) * N``; sell: ``(K - S) * N``.
    """

    nominal_usd: float
    fwd_rate: float
    spot_at_maturity: float
    side: str
    full_delivery_clp: float
    market_value_clp: float
    compensation_clp: float


def settle_forward(
    nominal_usd: float, fwd_rate: float, spot_at_maturity: float, side: str = "buy"
) -> Settlement:
    """Calcula cómo se liquida el forward: entrega física vs compensación.

    En Chile es común que los forwards de empresas se liquiden por
    *compensación*: nadie entrega los dólares, solo se paga la diferencia
    entre el precio pactado y el dólar observado del día.

    Ejemplo de la planilla: N = 500.000, K = 948,91, S = 900, compra →
    compensación = (900 − 948,91) × 500.000 = −24.455.000 (la empresa PAGA,
    porque se comprometió a comprar más caro de lo que terminó valiendo el dólar;
    a cambio, compra los USD en el mercado a 900, y el costo total queda en K).
    """
    sign = _side_sign(side)
    return Settlement(
        nominal_usd=nominal_usd,
        fwd_rate=fwd_rate,
        spot_at_maturity=spot_at_maturity,
        side=side,
        full_delivery_clp=nominal_usd * fwd_rate,
        market_value_clp=nominal_usd * spot_at_maturity,
        compensation_clp=sign * (spot_at_maturity - fwd_rate) * nominal_usd,
    )


def forward_mtm(
    nominal_usd: float,
    contract_rate: float,
    spot_t: float,
    r_dom: float,
    r_for: float,
    years_remaining: float,
    side: str = "buy",
) -> float:
    """Valor de mercado (*mark-to-market*) de un forward vivo, en CLP.

    ``MtM = signo * N * (F_t - K) / (1 + r_dom) ** tau``

    donde ``F_t`` es el forward que se cotizaría HOY para el plazo que queda
    (``tau``) y ``K`` el precio pactado. Se descuenta a valor presente porque
    la diferencia se pagaría recién al vencimiento. Es lo que la contabilidad
    reconoce período a período: ganancia si el contrato "está a favor".
    """
    sign = _side_sign(side)
    tau = max(years_remaining, 0.0)
    f_t = forward_rate(spot_t, r_dom, r_for, tau)
    return sign * nominal_usd * (f_t - contract_rate) / (1 + r_dom) ** tau
