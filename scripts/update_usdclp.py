"""Actualiza ``data/usdclp_dolar_observado.csv`` con el dólar observado desde mindicador.cl.

Descarga el año en curso (y el anterior, para cubrir el cambio de año), lo une al CSV
existente y lo guarda sin duplicados. Si la API no responde, deja el CSV intacto y
termina con código 0: el CSV incluido sigue sirviendo de respaldo para la app.

Uso::

    .venv/bin/python scripts/update_usdclp.py
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from derivados101.market import DEFAULT_CSV, _clean, _fetch_year, _make_client, load_usdclp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("update_usdclp")


def main() -> int:
    """Une los datos nuevos al CSV. Devuelve 0 siempre (un fallo de red no es un error de la app)."""
    current = load_usdclp()
    year = date.today().year
    rows: list[dict] = []
    try:
        with _make_client(15.0) as client:
            for y in (year - 1, year):
                rows.extend(_fetch_year(client, y, retries=4))
    except Exception as exc:  # noqa: BLE001 - se registra y se conserva el CSV actual
        logger.warning("No se pudo descargar el dólar observado (%s); el CSV queda igual.", exc)
        return 0
    merged = _clean(pd.concat([current, pd.DataFrame(rows)], ignore_index=True))
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    merged.to_csv(DEFAULT_CSV, index=False)
    logger.info("CSV actualizado: %d filas, último dato %s.", len(merged), merged["date"].iloc[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
