"""derivados101: núcleo de cálculo de la app educativa de derivados USD/CLP.

Contiene funciones puras (sin Streamlit) para forwards, opciones, estrategias
compuestas y datos de mercado. Material educativo: no es asesoría financiera ni contable.
"""

from __future__ import annotations

import logging
import sys

__all__ = ["get_logger"]

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con formato simple que escribe a stderr.

    Se configura una sola vez por nombre (no duplica handlers si se llama
    varias veces, cosa común cuando Streamlit re-ejecuta los scripts).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
