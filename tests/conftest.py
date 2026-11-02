"""Configuración común de tests: la UI no consulta internet durante las pruebas."""

import os

os.environ["DERIVADOS101_OFFLINE"] = "1"
