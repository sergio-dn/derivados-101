# CONTRACT — derivados-101

App educativa local (Streamlit) para explicar lo básico de derivados de moneda (USD/CLP):
forwards, opciones y estrategias compuestas. Basada en la planilla "Ejemplos Derivados"
(FAQ, Fwd, Options, Estrategia Compuesta, USDCLP). Audiencia: equipos de finanzas no
especialistas y público general (posible post en LinkedIn). Todo en español neutro.

**Alcance pedagógico (nivel básico).** La app es una base para alguien con finanzas básicas
que quiere entender cómo OPERAN los derivados: quién paga a quién, cuándo, cuánto y qué riesgo
queda. No es un curso de hedge accounting, economía financiera ni valuation: se prioriza la
intuición operativa sobre las fórmulas, y el contenido avanzado se simplifica u oculta.

**Reglas comunes**
- Python 3.12 en `.venv` (ya creado: `.venv/bin/python`). No cambiar dependencias sin
  avisar en el reporte final. Sin scipy: usar `math.erf` para la normal.
- Código en inglés, docstrings/comentarios/UI en español.
- Nada de datos de empresas o personas reales: ejemplos genéricos ("un importador chileno").
- Disclaimer visible: "Material educativo. No es asesoría financiera ni contable."
- Los agentes NO hacen commit. Commitea el orquestador.
- Cada agente escribe SOLO en sus carpetas (ver "Dueños").
- Precios CLP por USD. Plazos en años (float). Tasas como decimales (0.0511 = 5,11%).
- Capitalización por defecto: compuesta anual `(1+r)**T` (cuadra con la planilla:
  890 × 1,0511 / 1,0407 = 898,89).

## Dueños

| Carpeta / archivo | Dueño |
|---|---|
| `src/derivados101/**`, `tests/**` | agente `core` |
| `app.py`, `app_pages/**`, `.streamlit/**`, `src/derivados101/ui.py`, `src/derivados101/curso_ui.py` | agente `ui` |
| `src/derivados101/curso/cap*.py` (textos de los temas) | agentes de contenido |
| `README.md`, `LICENSE`, `scripts/**`, `.github/**`, `CLAUDE.md`, `docs/**` | agente `docs` |
| `CONTRACT.md`, `requirements*.txt`, `data/**` | orquestador |

## Datos

`data/usdclp_dolar_observado.csv` — columnas `date` (YYYY-MM-DD), `usdclp` (float).
Dólar observado oficial (BCCh) vía mindicador.cl, 2024-01-02 → 2026-11-02, 706 filas.

`data/tasas_referencia.csv` — columnas `date` (YYYY-MM-DD, primer día del mes), `r_clp`, `r_usd`
(decimales). Mensual desde 2023-01. Tasa interbancaria a 3 meses (OCDE vía FRED, series
`IR3TIB01CLM156N` y `IR3TIB01USM156N`); meses faltantes arrastran el último valor. Se regenera con
`scripts/update_rates.py`. Aproximación didáctica: no es la tasa que cotiza un banco.

## API del núcleo (`src/derivados101/`)

Funciones puras, sin Streamlit. Los nombres/firmas de abajo son el contrato: la UI los
importa tal cual. Se pueden agregar helpers privados, no cambiar firmas.

### `forward.py`
```python
def forward_rate(spot: float, r_dom: float, r_for: float, years: float) -> float
    # paridad de tasas: spot * (1+r_dom)**T / (1+r_for)**T
def forward_points(spot: float, fwd: float) -> float           # fwd - spot

@dataclass(frozen=True)
class SyntheticForward:            # "derivado sintético" de la hoja Fwd
    nominal_usd: float; spot: float; r_dom: float; r_for: float; years: float
    debt_clp_today: float          # nominal_usd * spot
    debt_clp_maturity: float       # debt_clp_today * (1+r_dom)**T
    usd_maturity: float            # nominal_usd * (1+r_for)**T
    implied_rate: float            # debt_clp_maturity / usd_maturity
    implied_points: float          # implied_rate - spot
def synthetic_forward(nominal_usd, spot, r_dom, r_for, years) -> SyntheticForward

@dataclass(frozen=True)
class Settlement:
    nominal_usd: float; fwd_rate: float; spot_at_maturity: float; side: str  # "buy"|"sell"
    full_delivery_clp: float       # CLP que paga (buy) o recibe (sell) = nominal*fwd
    market_value_clp: float        # nominal * spot_at_maturity
    compensation_clp: float        # positivo = la empresa RECIBE. buy: (S-K)*N ; sell: (K-S)*N
def settle_forward(nominal_usd, fwd_rate, spot_at_maturity, side="buy") -> Settlement
    # Ej. planilla: N=500.000, K=948,91, S=900, buy -> compensation = -24.455.000

def forward_mtm(nominal_usd, contract_rate, spot_t, r_dom, r_for, years_remaining,
                side="buy") -> float
    # MtM = sign * N * (F_t - K) / (1+r_dom)**tau, F_t = forward_rate(spot_t, ...)
```

### `options.py`
```python
OptionKind = Literal["call", "put"];  Position = Literal["long", "short"]

class OptionLeg(BaseModel):        # pydantic v2, frozen
    kind: OptionKind; position: Position
    strike: float                  # CLP/USD, > 0
    notional_usd: float = 1.0      # > 0
    premium: float = 0.0           # CLP por USD de nocional, >= 0 (se paga si long, se recibe si short)

def intrinsic_value(kind, spot, strike) -> float               # por unidad, >= 0
def moneyness(kind, spot, strike, atm_tol=0.005) -> Literal["ITM","ATM","OTM"]
def leg_payoff(leg, spots: np.ndarray) -> np.ndarray          # al vencimiento, SIN prima, con signo y nocional
def leg_pnl(leg, spots: np.ndarray) -> np.ndarray             # payoff ± prima*nocional

def garman_kohlhagen(kind, spot, strike, years, r_dom, r_for, vol) -> float
    # Black-Scholes para FX (subyacente paga r_for). Precio por USD, CLP.
def greeks(kind, spot, strike, years, r_dom, r_for, vol) -> dict[str, float]
    # keys: delta, gamma, vega (por 1 pto de vol = 0.01), theta (por día, /365), rho (por 1 pto = 0.01)
def binomial_price(kind, spot, strike, years, r_dom, r_for, vol, steps=200,
                   american=False) -> float                   # CRR; converge a GK si europea
def time_value(kind, spot, strike, years, r_dom, r_for, vol) -> float
    # garman_kohlhagen - intrinsic_value (puede ser levemente < 0 en puts europeas ITM profundas: documentarlo)
def premium_from_pct(pct: float, reference_price: float) -> float   # prima % (hoja) -> CLP por USD
```

### `strategies.py`
```python
Exposure = Literal["none", "long_usd", "short_usd"]
# long_usd = tengo activo en USD (exportador, cuentas por cobrar); short_usd = pasivo en USD (importador)

@dataclass(frozen=True)
class StrategyPreset:
    key: str; name: str; description: str; objective: str
    suggested_exposure: Exposure
    build: Callable[[float, float, float, float, float], list[OptionLeg]]
    # (spot, vol, years, r_dom, r_for) -> legs; prima de cada pata = garman_kohlhagen (CLP por USD)

PRESETS: dict[str, StrategyPreset]
# mínimo: long_call, long_put, short_call, short_put, bull_call_spread, bear_put_spread,
# collar_importer, collar_exporter, straddle, strangle, seagull_importer.
# Strikes relativos al spot (ej. ±2%, ±5%). Collares de COSTO CERO: importador compra call
# a spot·1,02 y vende put con strike resuelto (zero_cost_strike) para prima neta = 0;
# exportador compra put a spot·0,98 y vende call resuelta. Gaviota: strikes fijos, NO es costo cero.

def zero_cost_strike(kind, target_premium, spot, years, r_dom, r_for, vol,
                     tol=1e-10, max_iter=200) -> float
    # strike cuya prima GK = target_premium (bisección; kind = opción VENDIDA). ValueError si
    # target_premium < 0, spot <= 0 o kind inválido.

def strategy_pnl(legs, spots: np.ndarray, exposure: Exposure = "none",
                 spot0: float | None = None, exposure_usd: float = 1.0) -> pd.DataFrame
    # columnas: spot, options_pnl, underlying_pnl, combined_pnl
    # underlying_pnl: long_usd -> (S-spot0)*N ; short_usd -> (spot0-S)*N ; none -> 0
def net_premium(legs) -> float          # CLP total; positivo = pago neto (débito)
def breakevens(spots, pnl) -> list[float]   # cruces por cero, interpolados
def spot_grid(spot0: float, pct: float = 0.20, n: int = 401) -> np.ndarray
```

### `market.py`
```python
DEFAULT_CSV: Path    # data/usdclp_dolar_observado.csv (resuelto relativo al repo)
def load_usdclp(path: Path | None = None) -> pd.DataFrame     # date (datetime64), usdclp; ordenado
def fetch_usdclp_live(years: list[int], timeout=10.0, retries=3) -> pd.DataFrame
    # httpx a https://mindicador.cl/api/dolar/{year}, backoff exponencial; si falla -> load_usdclp()
    # con logging.warning. Nunca lanza excepción a la UI.
def realized_vol(df, window: int = 21, periods: int = 252) -> pd.Series   # log-returns anualizados
def horizon_changes(df, horizons_days=(21, 63, 126, 189, 252)) -> pd.DataFrame
    # distribución de variación % del USD/CLP a cada horizonte (min, p5, p50, p95, max, std)
def latest_spot(live: bool = True, timeout: float = 5.0) -> tuple[float, date, str]
    # (valor, fecha, fuente "mindicador.cl"|"csv"|"fijo"); nunca lanza
RATES_CSV: Path      # data/tasas_referencia.csv
def reference_rates(on: date | None = None) -> tuple[float, float, date]
    # (r_clp, r_usd, fecha_fila): fila vigente en o antes de `on`; None = última; antes de la
    # primera fila = la primera. Si el CSV falla: (0.0511, 0.0407, on o hoy) + warning. Nunca lanza.
def hedge_backtest(df, start: date, years: float, nominal_usd: float,
                   r_dom: float | None = None, r_for: float | None = None) -> dict
    # "¿y si hubiera tomado un forward?". Tasas None -> reference_rates(start).
    # keys: start_date, end_date, spot_start, fwd_rate, spot_end, cost_unhedged, cost_hedged,
    # compensation, savings, r_dom, r_for
def simulate_gbm(spot, vol, years, r_dom, r_for, n_paths=500, n_steps=252, seed=42) -> np.ndarray
    # shape (n_steps+1, n_paths), drift neutral al riesgo (r_dom - r_for)
```

### Logging
`src/derivados101/__init__.py` define `get_logger(name)` con formato simple a stderr.

## UI (`app.py` + `app_pages/`)

Streamlit multipage con `st.navigation` (títulos e íconos explícitos en `app.py`). `streamlit run app.py`.
La carpeta se llama `app_pages/` (no `pages/`) a propósito: con `pages/` Streamlit activa su modo
multipage antiguo y un link directo tras arrancar el servidor muestra el menú autogenerado.
Menú en 3 secciones (`ui.SECTIONS`):
1. **Conceptos**: Inicio (una línea + lista de preguntas) y 9 temas, uno por pregunta directa
   ("¿Qué es un forward?"). Contenido puro en `src/derivados101/curso/` (`model.py` = esquema;
   `cap*.py` = un tema cada uno; `CHAPTERS` = orden). Render en `src/derivados101/curso_ui.py`
   (st.Page callable, `url_path` = slug, menú con `Chapter.menu` corto ≤16 caracteres).
   Cada tema: 3–7 pantallas tipo slide (Concept, Example, Demo, Summary), Anterior/Siguiente,
   al menos 1 **Demo**: calculadora interactiva (10 tipos, `DEMO_PARAMS`) que muestra cómo funciona,
   no una prueba. Sin preguntas, puntajes ni progreso dentro de los temas.
2. **Simuladores**: `2_Forward.py`, `3_Opciones.py`, `4_Estrategias.py`, `5_USDCLP.py`.
3. **Repasa**: `1_Conceptos.py` ("Más preguntas", FAQ) y `6_Quiz.py`.

Cifras de ejemplo de los temas FIJAS (spot 890, 5,11% / 4,07%, 1 año, vol 12%) y verificadas con el
núcleo; `tests/test_curso.py` fija las clave. Si cambian presets o tasas de ejemplo, revisar textos.

Gráficos con Plotly. `src/derivados101/ui.py` (dueño `ui`): helpers de formato
(`fmt_clp`, `fmt_usd`, `fmt_pct` con separador de miles "." y decimal ","), disclaimer, paleta.
