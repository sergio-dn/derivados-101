"""Estrategias compuestas con opciones (hoja "Estrategia Compuesta").

Combinando calls y puts compradas y vendidas se arman perfiles de resultado a
medida: limitar el costo de una cobertura (collar), apostar a volatilidad
(straddle/strangle), o acotar ganancias y pérdidas (spreads).

Además, una estrategia rara vez está sola: una empresa ya tiene una
*exposición* al dólar por su negocio. Por eso :func:`strategy_pnl` muestra
tres curvas: la de las opciones, la del negocio (subyacente) y la combinada.

- ``long_usd``: tengo un ACTIVO en USD (exportador, cuentas por cobrar en
  dólares): me perjudica que el dólar baje.
- ``short_usd``: tengo un PASIVO en USD (importador, deudas en dólares): me
  perjudica que el dólar suba.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from .options import (
    OptionKind,
    OptionLeg,
    Position,
    garman_kohlhagen,
    leg_pnl,
)

__all__ = [
    "PRESETS",
    "Exposure",
    "StrategyPreset",
    "breakevens",
    "net_premium",
    "spot_grid",
    "strategy_pnl",
    "zero_cost_strike",
]

Exposure = Literal["none", "long_usd", "short_usd"]

# Firma de ``build``: (spot, vol, years, r_dom, r_for) -> patas con prima GK.
BuildFn = Callable[[float, float, float, float, float], list[OptionLeg]]


@dataclass(frozen=True)
class StrategyPreset:
    """Estrategia predefinida.

    Atributos:
        key: identificador interno (ej. ``"collar_importer"``).
        name: nombre para mostrar.
        description: cómo se arma (qué patas lleva).
        objective: para qué sirve y quién la usaría.
        suggested_exposure: exposición del negocio con la que tiene sentido.
        build: función ``(spot, vol, years, r_dom, r_for) -> list[OptionLeg]``.
            Los strikes se fijan relativos al spot (ej. ±2%, ±5%) y cada prima
            es el precio teórico de Garman-Kohlhagen en CLP por USD. En los
            collares, el strike de la pata vendida se resuelve para que la
            prima neta sea cero (ver :func:`zero_cost_strike`).
    """

    key: str
    name: str
    description: str
    objective: str
    suggested_exposure: Exposure
    build: BuildFn


# --------------------------------------------------------------------------- #
# Construcción de patas
# --------------------------------------------------------------------------- #


def zero_cost_strike(
    kind: OptionKind,
    target_premium: float,
    spot: float,
    years: float,
    r_dom: float,
    r_for: float,
    vol: float,
    tol: float = 1e-10,
    max_iter: int = 200,
) -> float:
    """Strike cuya prima Garman-Kohlhagen es igual a ``target_premium``.

    Sirve para armar un collar de costo cero: se compra una opción y se elige
    el strike de la opción vendida para que su prima pague exactamente la
    prima de la comprada (prima neta = 0).

    Cómo funciona (bisección): la prima de una put sube cuando sube el strike
    y la de una call baja. Se busca un intervalo de strikes donde la prima
    pase de estar bajo el objetivo a estar sobre él (ampliándolo si hace
    falta) y se parte por la mitad hasta que el error relativo sea menor que
    ``tol``. Siempre converge porque la prima es monótona en el strike.

    Args:
        kind: tipo de la opción VENDIDA (``"put"`` en el collar importador,
            ``"call"`` en el exportador).
        target_premium: prima a igualar, en CLP por USD (>= 0); normalmente
            la prima de la opción comprada.
        spot, years, r_dom, r_for, vol: mercado, igual que en
            :func:`derivados101.options.garman_kohlhagen`.

    Returns:
        El strike en CLP por USD. Si ``target_premium`` es 0 (por ejemplo con
        volatilidad 0), devuelve el borde donde la opción empieza a valer
        algo (≈ el forward).

    Raises:
        ValueError: si ``kind`` no es call/put, si ``spot <= 0`` o si
            ``target_premium < 0``.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind inválido: {kind!r}")
    if spot <= 0:
        raise ValueError("spot debe ser > 0")
    if target_premium < 0:
        raise ValueError("target_premium debe ser >= 0")

    def gap(strike: float) -> float:
        """Prima menos objetivo, orientada para que crezca con el strike."""
        price = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
        diff = price - target_premium
        return diff if kind == "put" else -diff

    lo, hi = spot * 0.5, spot * 1.5
    # Ampliar el intervalo hasta encerrar la raíz (gap(lo) <= 0 < gap(hi)).
    for _ in range(60):
        if gap(lo) <= 0:
            break
        lo *= 0.5
    for _ in range(60):
        if gap(hi) > 0:
            break
        hi *= 2.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if gap(mid) > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo <= tol * spot:
            break
    return 0.5 * (lo + hi)


def _gk_leg(
    kind: OptionKind,
    position: Position,
    strike: float,
    spot: float,
    vol: float,
    years: float,
    r_dom: float,
    r_for: float,
) -> OptionLeg:
    """Crea una pata con prima Garman-Kohlhagen (CLP por USD de nocional)."""
    premium = garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol)
    return OptionLeg(kind=kind, position=position, strike=strike, notional_usd=1.0,
                     premium=max(premium, 0.0))


def _builder(*specs: tuple[OptionKind, Position, float]) -> BuildFn:
    """Fabrica una función ``build`` a partir de (tipo, posición, multiplicador de strike)."""

    def build(spot: float, vol: float, years: float, r_dom: float, r_for: float) -> list[OptionLeg]:
        return [_gk_leg(kind, pos, spot * mult, spot, vol, years, r_dom, r_for)
                for kind, pos, mult in specs]

    return build


def _zero_cost_collar(bought: OptionKind, bought_mult: float) -> BuildFn:
    """``build`` de un collar de costo cero.

    Compra una opción ``bought`` con strike ``spot·bought_mult`` y vende la
    opción contraria con el strike que hace que ambas primas sean iguales.
    """
    sold: OptionKind = "put" if bought == "call" else "call"

    def build(spot: float, vol: float, years: float, r_dom: float, r_for: float) -> list[OptionLeg]:
        long_leg = _gk_leg(bought, "long", spot * bought_mult, spot, vol, years, r_dom, r_for)
        k_sold = zero_cost_strike(sold, long_leg.premium, spot, years, r_dom, r_for, vol)
        # La prima de la vendida se fija igual a la comprada: así la prima neta
        # es exactamente cero (la diferencia con GK es del orden de la tolerancia).
        short_leg = OptionLeg(kind=sold, position="short", strike=k_sold, notional_usd=1.0,
                              premium=long_leg.premium)
        return [long_leg, short_leg]

    return build


_PRESET_LIST: list[StrategyPreset] = [
    StrategyPreset(
        key="long_call",
        name="Compra de call",
        description="Compro una call ATM (strike = spot).",
        objective="Importador que quiere un techo para el dólar sin renunciar a que baje. "
        "Costo: la prima.",
        suggested_exposure="short_usd",
        build=_builder(("call", "long", 1.00)),
    ),
    StrategyPreset(
        key="long_put",
        name="Compra de put",
        description="Compro una put ATM (strike = spot).",
        objective="Exportador que quiere un piso para el dólar sin renunciar a que suba. "
        "Costo: la prima.",
        suggested_exposure="long_usd",
        build=_builder(("put", "long", 1.00)),
    ),
    StrategyPreset(
        key="short_call",
        name="Venta de call",
        description="Vendo una call ATM (strike = spot).",
        objective="Cobrar prima a cambio de renunciar a las alzas del dólar. Sin cobertura "
        "detrás, la pérdida potencial es ilimitada.",
        suggested_exposure="long_usd",
        build=_builder(("call", "short", 1.00)),
    ),
    StrategyPreset(
        key="short_put",
        name="Venta de put",
        description="Vendo una put ATM (strike = spot).",
        objective="Cobrar prima a cambio de renunciar a las bajas del dólar. Pierde si el "
        "dólar cae fuerte.",
        suggested_exposure="short_usd",
        build=_builder(("put", "short", 1.00)),
    ),
    StrategyPreset(
        key="bull_call_spread",
        name="Bull call spread",
        description="Compro call ATM y vendo call 5% más arriba.",
        objective="Protección contra alzas moderadas del dólar, más barata que una call sola. "
        "Sobre el strike alto vuelvo a quedar expuesto.",
        suggested_exposure="short_usd",
        build=_builder(("call", "long", 1.00), ("call", "short", 1.05)),
    ),
    StrategyPreset(
        key="bear_put_spread",
        name="Bear put spread",
        description="Compro put ATM y vendo put 5% más abajo.",
        objective="Protección contra bajas moderadas del dólar, más barata que una put sola.",
        suggested_exposure="long_usd",
        build=_builder(("put", "long", 1.00), ("put", "short", 0.95)),
    ),
    StrategyPreset(
        key="collar_importer",
        name="Collar importador (costo cero)",
        description="Compro una call 2% sobre el spot y vendo una put cuyo strike se elige "
        "para que su prima pague exactamente la call.",
        objective="Importador fija una banda: techo para el dólar (la call) a cambio de "
        "renunciar a las bajas bajo el strike de la put. No paga prima neta hoy.",
        suggested_exposure="short_usd",
        build=_zero_cost_collar("call", 1.02),
    ),
    StrategyPreset(
        key="collar_exporter",
        name="Collar exportador (costo cero)",
        description="Compro una put 2% bajo el spot y vendo una call cuyo strike se elige "
        "para que su prima pague exactamente la put.",
        objective="Exportador fija una banda: piso para el dólar que recibirá (la put) a "
        "cambio de renunciar a las alzas sobre el strike de la call. No paga prima neta hoy.",
        suggested_exposure="long_usd",
        build=_zero_cost_collar("put", 0.98),
    ),
    StrategyPreset(
        key="straddle",
        name="Straddle",
        description="Compro call y put ATM (mismo strike).",
        objective="Ganar si el dólar se mueve mucho, para cualquier lado. Pierde la prima "
        "si se queda quieto. Es una apuesta a volatilidad, no una cobertura.",
        suggested_exposure="none",
        build=_builder(("call", "long", 1.00), ("put", "long", 1.00)),
    ),
    StrategyPreset(
        key="strangle",
        name="Strangle",
        description="Compro call 5% sobre el spot y put 5% bajo el spot.",
        objective="Como el straddle pero más barato: necesita movimientos más grandes "
        "para ganar.",
        suggested_exposure="none",
        build=_builder(("call", "long", 1.05), ("put", "long", 0.95)),
    ),
    StrategyPreset(
        key="seagull_importer",
        name="Gaviota (seagull) importador",
        description="Compro call 2% arriba, vendo call 7% arriba y vendo put 3% abajo.",
        objective="Importador abarata la protección: techo entre +2% y +7%, renuncia a "
        "bajas bajo −3%. Sobre +7% vuelve a quedar expuesto. Strikes fijos: la prima "
        "neta no es cero (puede ser un pago o un cobro según tasas y volatilidad).",
        suggested_exposure="short_usd",
        build=_builder(("call", "long", 1.02), ("call", "short", 1.07), ("put", "short", 0.97)),
    ),
]

PRESETS: dict[str, StrategyPreset] = {p.key: p for p in _PRESET_LIST}


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #


def spot_grid(spot0: float, pct: float = 0.20, n: int = 401) -> np.ndarray:
    """Grilla de spots al vencimiento: de ``spot0·(1−pct)`` a ``spot0·(1+pct)``.

    Con ``n`` impar el spot inicial queda exactamente en el centro.
    """
    if spot0 <= 0 or not 0 < pct < 1 or n < 2:
        raise ValueError("se requiere spot0 > 0, 0 < pct < 1 y n >= 2")
    return np.linspace(spot0 * (1 - pct), spot0 * (1 + pct), n)


def net_premium(legs: list[OptionLeg]) -> float:
    """Prima neta total en CLP. Positivo = pago neto (débito); negativo = cobro neto."""
    return float(sum(leg.sign * leg.premium * leg.notional_usd for leg in legs))


def strategy_pnl(
    legs: list[OptionLeg],
    spots: np.ndarray,
    exposure: Exposure = "none",
    spot0: float | None = None,
    exposure_usd: float = 1.0,
) -> pd.DataFrame:
    """Resultado al vencimiento de la estrategia, del negocio y de ambos juntos.

    Columnas devueltas:
        spot: dólar al vencimiento.
        options_pnl: suma del PnL de todas las patas (incluye primas).
        underlying_pnl: ganancia/pérdida del negocio por moverse el dólar desde
            ``spot0``: ``long_usd`` → ``(S − spot0)·N``; ``short_usd`` →
            ``(spot0 − S)·N``; ``none`` → 0.
        combined_pnl: options_pnl + underlying_pnl (lo que realmente importa
            si la opción es una cobertura).

    Si ``spot0`` es ``None`` se usa el punto central de ``spots`` (que es el
    spot inicial cuando la grilla viene de :func:`spot_grid`).
    """
    s = np.asarray(spots, dtype=float)
    options = np.zeros_like(s)
    for leg in legs:
        options = options + leg_pnl(leg, s)

    if exposure not in ("none", "long_usd", "short_usd"):
        raise ValueError(f"exposure inválida: {exposure!r}")
    ref = float(s[len(s) // 2]) if spot0 is None else float(spot0)
    if exposure == "long_usd":
        underlying = (s - ref) * exposure_usd
    elif exposure == "short_usd":
        underlying = (ref - s) * exposure_usd
    else:
        underlying = np.zeros_like(s)

    return pd.DataFrame(
        {
            "spot": s,
            "options_pnl": options,
            "underlying_pnl": underlying,
            "combined_pnl": options + underlying,
        }
    )


def breakevens(spots: np.ndarray, pnl: np.ndarray) -> list[float]:
    """Puntos de equilibrio: spots donde el PnL cruza por cero.

    Se busca cada cambio de signo entre puntos consecutivos y se interpola
    linealmente (exacto para payoffs de opciones, que son tramos rectos).
    Si el PnL toca cero en un tramo plano, se reporta el punto medio de ese
    tramo solo cuando el signo realmente cambia a ambos lados.
    """
    x = np.asarray(spots, dtype=float)
    y = np.asarray(pnl, dtype=float)
    if x.shape != y.shape:
        raise ValueError("spots y pnl deben tener el mismo largo")
    sign = np.sign(np.where(np.abs(y) < 1e-9, 0.0, y))
    result: list[float] = []
    i, n = 0, len(x)
    while i < n - 1:
        if sign[i] != 0 and sign[i + 1] != 0 and sign[i] != sign[i + 1]:
            x0, x1, y0, y1 = x[i], x[i + 1], y[i], y[i + 1]
            result.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)))
            i += 1
        elif sign[i + 1] == 0:
            # tramo de ceros que empieza en i+1
            j = i + 1
            while j < n and sign[j] == 0:
                j += 1
            before = sign[i]
            after = sign[j] if j < n else 0
            if before != 0 and after != 0 and before != after:
                result.append(float((x[i + 1] + x[j - 1]) / 2))
            i = j
        else:
            i += 1
    return result
