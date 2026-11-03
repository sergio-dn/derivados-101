"""Actualiza ``data/usdclp_dolar_observado.csv`` con el dólar observado más reciente.

Fuentes, en orden:
1. API oficial del Banco Central de Chile (SIETE), si existen las variables de entorno
   ``BCCH_USER`` y ``BCCH_PASS``. En GitHub Actions vienen de los Secrets del repositorio.
2. mindicador.cl (pública, sin credenciales), si no hay credenciales o el BCCh falla.

Si ninguna responde, deja el CSV intacto y termina con código 0: el CSV incluido sigue
sirviendo de respaldo para la app.

Seguridad: las credenciales del BCCh viajan en la URL de la API. Este script nunca imprime
la URL, el texto de errores de red ni las variables de entorno; solo el tipo de error.

Uso::

    BCCH_USER=... BCCH_PASS=... .venv/bin/python scripts/update_usdclp.py
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from derivados101.market import DEFAULT_CSV, _clean, _fetch_year, _make_client, fetch_usdclp_bcch, load_usdclp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("update_usdclp")
# httpx registra cada request con su URL completa (que incluye las credenciales del BCCh).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def _from_bcch(today: date) -> list[dict]:
    user, password = os.environ.get("BCCH_USER", ""), os.environ.get("BCCH_PASS", "")
    if not (user and password):
        logger.info("Sin credenciales del BCCh; se usa mindicador.cl.")
        return []
    try:
        rows = fetch_usdclp_bcch(user, password, today - timedelta(days=400), today)
    except RuntimeError as exc:  # mensaje genérico, sin URL (ver fetch_usdclp_bcch)
        logger.warning("%s; se intenta mindicador.cl.", exc)
        return []
    logger.info("BCCh: %d observaciones.", len(rows))
    return rows


def _from_mindicador(today: date) -> list[dict]:
    rows: list[dict] = []
    try:
        with _make_client(15.0) as client:
            for y in (today.year - 1, today.year):
                rows.extend(_fetch_year(client, y, retries=4))
    except Exception as exc:  # noqa: BLE001 - se registra y se conserva el CSV actual
        logger.warning("No se pudo descargar desde mindicador.cl (%s).", type(exc).__name__)
        return []
    logger.info("mindicador.cl: %d observaciones.", len(rows))
    return rows


def main() -> int:
    """Une los datos nuevos al CSV. Devuelve 0 siempre (un fallo de red no es un error de la app)."""
    today = date.today()
    rows = _from_bcch(today) or _from_mindicador(today)
    if not rows:
        logger.warning("Ninguna fuente respondió; el CSV queda igual.")
        return 0
    merged = _clean(pd.concat([load_usdclp(), pd.DataFrame(rows)], ignore_index=True))
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    merged.to_csv(DEFAULT_CSV, index=False)
    logger.info("CSV actualizado: %d filas, último dato %s.", len(merged), merged["date"].iloc[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
