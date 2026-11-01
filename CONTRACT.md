# CONTRACT — derivados-101

App educativa local (Streamlit) para explicar lo básico de derivados de moneda (USD/CLP):
forwards, opciones y estrategias compuestas. Basada en la planilla "Ejemplos Derivados"
(FAQ, Fwd, Options, Estrategia Compuesta, USDCLP). Audiencia: equipos de finanzas no
especialistas y público general (posible post en LinkedIn). Todo en español neutro.

**Reglas comunes**
- Python 3.12 en `.venv` (ya creado: `.venv/bin/python`). No cambiar dependencias sin
  avisar en el reporte final. Sin scipy: usar `math.erf` para la normal.
- Código en inglés, docstrings/comentarios/UI en español.
- Nada de datos de Wild Lama ni de nadie: ejemplos genéricos ("un importador chileno").
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
| `app.py`, `app_pages/**`, `.streamlit/**`, `src/derivados101/ui.py` | agente `ui` |
| `README.md`, `LICENSE`, `scripts/**`, `.github/**`, `CLAUDE.md`, `docs/**` | agente `docs` |
| `CONTRACT.md`, `requirements*.txt`, `data/**` | orquestador |

## Datos

`data/usdclp_dolar_observado.csv` — columnas `date` (YYYY-MM-DD), `usdclp` (float).
Dólar observado oficial (BCCh) vía mindicador.cl, 2024-01-02 → 2026-11-02, 706 filas.

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
    build: Callable[[float, float], list[OptionLeg]]   # (spot, premium_pct) -> legs

PRESETS: dict[str, StrategyPreset]
# mínimo: long_call, long_put, short_call, short_put, bull_call_spread, bear_put_spread,
# collar_importer (long call + short put), collar_exporter (long put + short call),
# straddle, strangle, seagull_importer. Strikes relativos al spot (ej. ±2%, ±5%).

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
def hedge_backtest(df, start: date, years: float, r_dom: float, r_for: float,
                   nominal_usd: float) -> dict
    # "¿y si hubiera tomado un forward?" -> fwd_rate, spot_end, cost_unhedged, cost_hedged, compensation
def simulate_gbm(spot, vol, years, r_dom, r_for, n_paths=500, n_steps=252, seed=42) -> np.ndarray
    # shape (n_steps+1, n_paths), drift neutral al riesgo (r_dom - r_for)
```

### Logging
`src/derivados101/__init__.py` define `get_logger(name)` con formato simple a stderr.

## UI (`app.py` + `app_pages/`)

Streamlit multipage con `st.navigation` (títulos e íconos explícitos en `app.py`). `streamlit run app.py`.
La carpeta se llama `app_pages/` (no `pages/`) a propósito: con `pages/` Streamlit activa su modo
multipage antiguo y un link directo tras arrancar el servidor muestra el menú autogenerado.
Páginas:
1. `app_pages/0_Inicio.py` — Inicio: qué es un derivado, cobertura vs especulación, mapa de la app.
2. `app_pages/1_Conceptos.py` — FAQ de la hoja "Derivados" (8 preguntas) + contabilidad
   (especulación a resultado vía MtM vs hedge accounting IFRS 9 / OCI), con aviso de simplificación.
3. `app_pages/2_Forward.py` — sintético paso a paso (inputs editables, default planilla:
   500.000 USD, spot 890, 5,11% / 4,07%, 1 año), liquidación full delivery vs compensación
   con slider de spot final, gráfico costo cubierto vs no cubierto, MtM en el tiempo.
4. `app_pages/3_Opciones.py` — una opción: payoff/PnL, valor intrínseco vs temporal (GK),
   ITM/ATM/OTM, griegas, sensibilidad a vol y plazo, Monte Carlo (fan chart) explicando valor del tiempo.
5. `app_pages/4_Estrategias.py` — presets + editor de hasta 4 patas, exposición subyacente,
   gráfico opciones / subyacente / combinado, breakevens, prima neta, comparación vs forward.
6. `app_pages/5_USDCLP.py` — histórico, vol realizada, distribución por horizonte, backtest de cobertura.
7. `app_pages/6_Quiz.py` — 8–10 preguntas con feedback y explicación.

Gráficos con Plotly. `src/derivados101/ui.py` (dueño `ui`): helpers de formato
(`fmt_clp`, `fmt_usd`, `fmt_pct` con separador de miles "." y decimal ","), disclaimer, paleta.
