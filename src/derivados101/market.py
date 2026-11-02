"""Datos de mercado del USD/CLP: histórico, volatilidad, escenarios y simulación.

Fuente: dólar observado oficial del Banco Central de Chile, vía la API
pública de mindicador.cl. Se incluye un CSV local para que la app funcione sin
internet; :func:`fetch_usdclp_live` intenta actualizar y, si falla, usa el CSV.
"""

from __future__ import annotations

import math
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from . import get_logger
from .forward import forward_rate, settle_forward

__all__ = [
    "DEFAULT_CSV",
    "fetch_usdclp_live",
    "hedge_backtest",
    "horizon_changes",
    "latest_spot",
    "load_usdclp",
    "realized_vol",
    "reference_rates",
    "simulate_gbm",
]

logger = get_logger(__name__)

DEFAULT_CSV: Path = Path(__file__).resolve().parents[2] / "data" / "usdclp_dolar_observado.csv"
RATES_CSV: Path = Path(__file__).resolve().parents[2] / "data" / "tasas_referencia.csv"
# Último recurso si no se puede leer el CSV de tasas (ejemplo de la planilla original).
_FALLBACK_RATES = (0.0511, 0.0407)
_API_URL = "https://mindicador.cl/api/dolar/{year}"
_COLUMNS = ["date", "usdclp"]

# Indirecciones para poder reemplazarlas en tests (sin red y sin esperas reales).
_sleep = time.sleep


def _make_client(timeout: float) -> httpx.Client:
    """Crea el cliente HTTP (aislado para poder mockearlo en tests)."""
    return httpx.Client(timeout=timeout)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza: tipos, sin nulos ni duplicados, ordenado por fecha."""
    out = df[_COLUMNS].copy()
    out["date"] = pd.to_datetime(out["date"])
    out["usdclp"] = pd.to_numeric(out["usdclp"], errors="coerce")
    out = out.dropna().drop_duplicates(subset="date", keep="last")
    return out.sort_values("date").reset_index(drop=True)


def load_usdclp(path: Path | None = None) -> pd.DataFrame:
    """Carga el histórico local del dólar observado.

    Devuelve un DataFrame con columnas ``date`` (datetime64) y ``usdclp``
    (CLP por USD), ordenado por fecha y sin duplicados.
    """
    df = pd.read_csv(path or DEFAULT_CSV)
    return _clean(df)


def _fetch_year(client: httpx.Client, year: int, retries: int) -> list[dict]:
    """Descarga un año desde mindicador.cl con reintentos y backoff exponencial."""
    url = _API_URL.format(year=year)
    last_exc: Exception | None = None
    for attempt in range(max(retries, 1)):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            serie = resp.json()["serie"]
            # "fecha" viene en UTC a medianoche de Chile (ej. 2024-01-02T03:00:00.000Z):
            # los primeros 10 caracteres son la fecha local correcta.
            return [{"date": item["fecha"][:10], "usdclp": float(item["valor"])} for item in serie]
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            last_exc = exc
            wait = 0.5 * 2**attempt
            logger.info("Intento %d/%d falló para %s (%s); reintento en %.1fs",
                        attempt + 1, retries, url, type(exc).__name__, wait)
            if attempt < retries - 1:
                _sleep(wait)
    raise RuntimeError(f"No se pudo descargar {url}") from last_exc


def fetch_usdclp_live(years: list[int], timeout: float = 10.0, retries: int = 3) -> pd.DataFrame:
    """Descarga el dólar observado de los años pedidos desde mindicador.cl.

    Usa reintentos con backoff exponencial (0,5 s, 1 s, 2 s...). Si algo
    falla (sin internet, API caída, respuesta rara), registra un
    ``logging.warning`` y devuelve el CSV local (:func:`load_usdclp`).
    Nunca lanza excepciones: si incluso el CSV falla, devuelve un DataFrame vacío.
    """
    try:
        rows: list[dict] = []
        with _make_client(timeout) as client:
            for year in years:
                rows.extend(_fetch_year(client, year, retries))
        if not rows:
            raise RuntimeError("la API no devolvió datos")
        return _clean(pd.DataFrame(rows))
    except Exception as exc:  # noqa: BLE001 - la UI nunca debe recibir excepciones
        logger.warning("Fallo la descarga en vivo (%s); se usa el CSV local.", exc)
        try:
            return load_usdclp()
        except Exception as exc2:  # noqa: BLE001
            logger.warning("Tampoco se pudo leer el CSV local (%s).", exc2)
            return pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"),
                                 "usdclp": pd.Series(dtype=float)})


_LATEST_URL = "https://mindicador.cl/api/dolar"


def latest_spot(live: bool = True, timeout: float = 5.0) -> tuple[float, date, str]:
    """Último dólar observado disponible, para usarlo como valor de ejemplo en la app.

    Si ``live`` es True intenta mindicador.cl (un intento, timeout corto); si falla o
    ``live`` es False, usa el último dato del CSV local. Nunca lanza excepciones: como
    último recurso devuelve 900,0 con fuente ``"fijo"``.

    Devuelve ``(valor, fecha, fuente)`` con fuente ``"mindicador.cl"``, ``"csv"`` o ``"fijo"``.
    """
    if live:
        try:
            with _make_client(timeout) as client:
                resp = client.get(_LATEST_URL)
                resp.raise_for_status()
                item = resp.json()["serie"][0]
                return float(item["valor"]), date.fromisoformat(item["fecha"][:10]), "mindicador.cl"
        except Exception as exc:  # noqa: BLE001 - la UI nunca debe recibir excepciones
            logger.info("No se pudo obtener el dólar en vivo (%s); se usa el CSV.", type(exc).__name__)
    try:
        df = load_usdclp()
        last = df.iloc[-1]
        return float(last["usdclp"]), last["date"].date(), "csv"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tampoco se pudo leer el CSV local (%s).", exc)
        return 900.0, date.today(), "fijo"


def realized_vol(df: pd.DataFrame, window: int = 21, periods: int = 252) -> pd.Series:
    """Volatilidad realizada anualizada (ventana móvil).

    1. Retornos logarítmicos diarios: ``ln(S_t / S_{t−1})``.
    2. Desviación estándar en una ventana de ``window`` días hábiles (21 ≈ 1 mes).
    3. Anualizada multiplicando por ``√periods`` (252 días hábiles al año).

    Devuelve una Serie indexada por fecha (las primeras ``window`` quedan NaN).
    """
    s = df.set_index("date")["usdclp"]
    log_ret = np.log(s / s.shift(1))
    vol = log_ret.rolling(window).std() * math.sqrt(periods)
    vol.name = "realized_vol"
    return vol


def horizon_changes(
    df: pd.DataFrame, horizons_days: tuple[int, ...] = (21, 63, 126, 189, 252)
) -> pd.DataFrame:
    """Distribución histórica de la variación % del USD/CLP a distintos plazos.

    Para cada horizonte ``h`` (en días hábiles: 21 ≈ 1 mes, 252 ≈ 1 año) se
    calcula ``S_{t+h} / S_t − 1`` para todas las fechas posibles (ventanas
    traslapadas, por eso las observaciones no son independientes).

    Columnas: horizon_days, n, min, p5, p50, p95, max, std (variaciones como
    decimales: 0.05 = +5%). Los horizontes sin datos suficientes se omiten.
    """
    s = df["usdclp"].reset_index(drop=True)
    rows = []
    for h in horizons_days:
        changes = (s.shift(-h) / s - 1).dropna()
        if changes.empty:
            continue
        rows.append(
            {
                "horizon_days": h,
                "n": int(changes.size),
                "min": changes.min(),
                "p5": changes.quantile(0.05),
                "p50": changes.quantile(0.50),
                "p95": changes.quantile(0.95),
                "max": changes.max(),
                "std": changes.std(),
            }
        )
    return pd.DataFrame(rows, columns=["horizon_days", "n", "min", "p5", "p50", "p95", "max", "std"])


def _load_rates(path: Path | None = None) -> pd.DataFrame:
    """Lee el CSV de tasas de referencia (date, r_clp, r_usd), ordenado por fecha."""
    df = pd.read_csv(path or RATES_CSV)
    df["date"] = pd.to_datetime(df["date"])
    df["r_clp"] = pd.to_numeric(df["r_clp"], errors="coerce")
    df["r_usd"] = pd.to_numeric(df["r_usd"], errors="coerce")
    df = df.dropna().drop_duplicates(subset="date", keep="last")
    return df.sort_values("date").reset_index(drop=True)


def reference_rates(on: date | None = None) -> tuple[float, float, date]:
    """Tasas de referencia CLP y USD vigentes en una fecha (aproximación didáctica).

    Lee ``data/tasas_referencia.csv`` (mensual, generado por
    ``scripts/update_rates.py`` desde FRED): tasa interbancaria a 3 meses de
    Chile y de EE.UU., promedio del mes, en decimales. No es la tasa que
    cotiza un banco para un forward; sirve para que los ejemplos usen tasas
    "de la época" y no números fijos.

    Reglas:
        - ``on`` es ``None`` → última fila disponible.
        - si no → la fila más reciente con fecha en o antes de ``on``.
        - ``on`` anterior a la primera fila → la primera fila.

    Devuelve ``(r_clp, r_usd, fecha_de_la_fila)``. Nunca lanza excepciones:
    si el CSV no se puede leer, registra un warning y devuelve las tasas de
    la planilla original (5,11% / 4,07%) con la fecha ``on`` (o hoy).
    """
    try:
        rates = _load_rates()
        if rates.empty:
            raise ValueError("CSV de tasas vacío")
        if on is None:
            row = rates.iloc[-1]
        else:
            valid = rates[rates["date"] <= pd.Timestamp(on)]
            row = valid.iloc[-1] if not valid.empty else rates.iloc[0]
        return float(row["r_clp"]), float(row["r_usd"]), row["date"].date()
    except Exception as exc:  # noqa: BLE001 - la UI nunca debe recibir excepciones
        logger.warning("No se pudieron leer las tasas de referencia (%s); se usan fijas.", exc)
        return _FALLBACK_RATES[0], _FALLBACK_RATES[1], on or date.today()


def hedge_backtest(
    df: pd.DataFrame,
    start: date,
    years: float,
    nominal_usd: float,
    r_dom: float | None = None,
    r_for: float | None = None,
) -> dict:
    """"¿Y si hubiera tomado un forward?": backtest para un importador.

    Supone que en ``start`` la empresa sabe que deberá pagar ``nominal_usd``
    dentro de ``years`` años. Compara:

    - sin cobertura: compra los USD al spot del vencimiento.
    - con cobertura: fija hoy un forward de compra calculado con las tasas
      ``r_dom`` (CLP) y ``r_for`` (USD). Si alguna es ``None`` se usa la tasa
      de referencia vigente en ``start`` (:func:`reference_rates`), así el
      forward refleja las tasas de esa época y no las de hoy.

    Fechas: se usa el primer dato disponible desde ``start`` y desde
    ``start + years·365 días``.

    Devuelve: start_date, end_date, spot_start, fwd_rate, spot_end,
    cost_unhedged, cost_hedged, compensation (desde la empresa: positivo = la
    empresa RECIBE del banco; negativo = la empresa PAGA al banco), savings
    (cost_unhedged − cost_hedged; positivo = la cobertura convino *ex post*, lo
    que no significa que haya sido "mejor decisión"), r_dom y r_for (las tasas
    efectivamente usadas).

    Lanza ``ValueError`` si no hay datos para el inicio o el vencimiento.
    """
    if r_dom is None or r_for is None:
        ref_dom, ref_for, _ = reference_rates(start)
        r_dom = ref_dom if r_dom is None else r_dom
        r_for = ref_for if r_for is None else r_for
    data = _clean(df)
    start_ts = pd.Timestamp(start)
    end_ts = start_ts + timedelta(days=round(years * 365))
    after_start = data[data["date"] >= start_ts]
    after_end = data[data["date"] >= end_ts]
    if after_start.empty or after_end.empty:
        raise ValueError("No hay datos suficientes para ese inicio y plazo.")
    row0, row1 = after_start.iloc[0], after_end.iloc[0]
    spot_start = float(row0["usdclp"])
    spot_end = float(row1["usdclp"])
    fwd = forward_rate(spot_start, r_dom, r_for, years)
    settlement = settle_forward(nominal_usd, fwd, spot_end, side="buy")
    cost_unhedged = nominal_usd * spot_end
    cost_hedged = nominal_usd * fwd
    return {
        "start_date": row0["date"].date(),
        "end_date": row1["date"].date(),
        "spot_start": spot_start,
        "fwd_rate": fwd,
        "spot_end": spot_end,
        "cost_unhedged": cost_unhedged,
        "cost_hedged": cost_hedged,
        "compensation": settlement.compensation_clp,
        "savings": cost_unhedged - cost_hedged,
        "r_dom": float(r_dom),
        "r_for": float(r_for),
    }


def simulate_gbm(
    spot: float,
    vol: float,
    years: float,
    r_dom: float,
    r_for: float,
    n_paths: int = 500,
    n_steps: int = 252,
    seed: int = 42,
) -> np.ndarray:
    """Simula trayectorias del USD/CLP con movimiento browniano geométrico.

    ``S_{t+dt} = S_t · exp((μ − σ²/2)·dt + σ·√dt·Z)``, con ``Z ~ N(0, 1)``.

    El drift es neutral al riesgo: ``μ = rd − rf`` usando las tasas continuas
    equivalentes ``ln(1 + r)``; así el promedio de los spots finales tiende al
    forward de :func:`derivados101.forward.forward_rate`. No es un pronóstico:
    sirve para ver el abanico de escenarios que valoriza una opción.

    Devuelve un arreglo de forma ``(n_steps + 1, n_paths)``; la fila 0 es ``spot``.
    """
    if n_paths < 1 or n_steps < 1:
        raise ValueError("n_paths y n_steps deben ser >= 1")
    rng = np.random.default_rng(seed)
    dt = years / n_steps
    mu = math.log1p(r_dom) - math.log1p(r_for)
    z = rng.standard_normal((n_steps, n_paths))
    increments = (mu - 0.5 * vol**2) * dt + vol * math.sqrt(dt) * z
    log_paths = np.vstack([np.zeros((1, n_paths)), np.cumsum(increments, axis=0)])
    return spot * np.exp(log_paths)
