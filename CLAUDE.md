# derivados-101 — contexto para agentes

App educativa local (Streamlit) sobre derivados de moneda USD/CLP: forwards, opciones y
estrategias. Audiencia no especialista; posible publicación abierta. Todo en español neutro.
**`CONTRACT.md` es la fuente de verdad** (firmas de la API, dueños, reglas). Léelo antes de tocar código.

## Comandos
```bash
bash scripts/run.sh                      # crea .venv, instala y lanza la app (Windows: scripts\run.bat)
.venv/bin/python -m streamlit run app.py # lanzar directo
.venv/bin/python -m pytest -q             # pythonpath=src vía pyproject.toml
.venv/bin/ruff check .                    # ruff 0.17.* fijado; reglas en pyproject.toml
```

## Convenciones
- Config de pytest y ruff en `pyproject.toml` (line-length 110; E,F,W,I,B,UP). `.gitattributes`: `.bat` CRLF, `.sh` LF.
- Python 3.12 en `.venv`. Sin scipy: normal vía `math.erf`. No cambiar dependencias sin avisar.
- Código en inglés; docstrings, comentarios y UI en español.
- CLP por USD, plazos en años (float), tasas decimales, capitalización compuesta anual `(1+r)**T`.
- Signos: compensación positiva = la empresa RECIBE; prima neta positiva = pago neto (débito).
  `long_usd` = activo en USD (exportador), `short_usd` = pasivo en USD (importador).
- Núcleo (`src/derivados101/`) puro y sin Streamlit; la UI solo importa las firmas del contrato.
- Ejemplos genéricos ("un importador chileno"). Sin datos ni nombres de empresas reales.
- Disclaimer visible: "Material educativo. No es asesoría financiera ni contable."

## Dueños
| Ruta | Dueño |
|---|---|
| `src/derivados101/**` (salvo `ui.py`), `tests/**` | core |
| `app.py`, `app_pages/**`, `.streamlit/**`, `src/derivados101/ui.py` | ui |
| `README.md`, `LICENSE`, `scripts/**`, `.github/**`, `CLAUDE.md`, `docs/**` | docs |
| `CONTRACT.md`, `requirements*.txt`, `pyproject.toml`, `.gitattributes`, `data/**` | orquestador |

Los agentes no commitean; commitea el orquestador.
