"""Regenera ``data/tasas_referencia.csv`` con tasas de referencia mensuales CLP y USD.

Fuente: FRED (Federal Reserve Bank of St. Louis), sin API key, series OCDE de
tasa interbancaria a 3 meses (% anual, promedio mensual):

- Chile: ``IR3TIB01CLM156N``
- EE.UU.: ``IR3TIB01USM156N``

Es una aproximación didáctica para tener tasas "de la época" en los ejemplos:
no es la tasa que cotiza un banco para un forward (esa incluye spreads, base
cross-currency y riesgo de contraparte).

Salida: CSV con columnas ``date`` (primer día del mes, YYYY-MM-DD), ``r_clp`` y
``r_usd`` (decimales: 0.0465 = 4,65%), desde 2023-01 hasta el último mes con
dato en alguna de las dos series. Si un mes falta en una serie, se arrastra el
último valor conocido.

Uso::

    .venv/bin/python scripts/update_rates.py
"""

from __future__ import annotations

import io
import logging
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("update_rates")

OUT_CSV = Path(__file__).resolve().parents[1] / "data" / "tasas_referencia.csv"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SERIES = {"r_clp": "IR3TIB01CLM156N", "r_usd": "IR3TIB01USM156N"}
START = "2023-01-01"


def fetch_series(client: httpx.Client, series_id: str, retries: int = 4) -> pd.Series:
    """Descarga una serie de FRED (CSV) con reintentos y backoff exponencial.

    Devuelve una Serie indexada por fecha (inicio de mes) en decimales.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client.get(FRED_URL, params={"id": series_id, "cosd": START})
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            date_col, value_col = df.columns[0], df.columns[1]
            values = pd.to_numeric(df[value_col], errors="coerce") / 100.0
            out = pd.Series(values.to_numpy(), index=pd.to_datetime(df[date_col]), name=series_id)
            out = out.dropna()
            if out.empty:
                raise ValueError("serie vacía")
            return out
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            last_exc = exc
            wait = 1.0 * 2**attempt
            logger.warning("Intento %d/%d falló para %s (%s); reintento en %.0fs",
                           attempt + 1, retries, series_id, type(exc).__name__, wait)
            if attempt < retries - 1:
                time.sleep(wait)
    raise RuntimeError(f"No se pudo descargar {series_id}") from last_exc


def build_table(series: dict[str, pd.Series]) -> pd.DataFrame:
    """Une las series en una tabla mensual desde ``START`` y arrastra valores faltantes."""
    end = max(s.index.max() for s in series.values())
    months = pd.date_range(START, end, freq="MS")
    table = pd.DataFrame({name: s.reindex(months) for name, s in series.items()}, index=months)
    table = table.ffill().bfill().round(6)
    table.index.name = "date"
    return table.reset_index()


def main() -> int:
    """Descarga ambas series y escribe el CSV."""
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        series = {name: fetch_series(client, sid) for name, sid in SERIES.items()}
    table = build_table(series)
    table["date"] = table["date"].dt.strftime("%Y-%m-%d")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)
    logger.info("Escrito %s: %d filas (%s → %s)", OUT_CSV, len(table),
                table["date"].iloc[0], table["date"].iloc[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
