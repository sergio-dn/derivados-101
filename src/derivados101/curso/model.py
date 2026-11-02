"""Modelo de datos del curso: capítulos formados por pantallas.

Puro (sin Streamlit). La UI (``derivados101.curso_ui``) recorre ``CHAPTERS`` y dibuja cada
pantalla según su tipo. El contenido vive en ``cap1.py`` … ``cap6.py``.

Convenciones de texto:
- Markdown de Streamlit. Escapar todo "$" de montos como ``\\$`` (pares de "$" se vuelven LaTeX).
- Formato chileno: miles con "." y decimales con "," (898,89; US\\$500.000).
- Tuteo neutro ("tú"), oraciones cortas, cifra y mecanismo antes que adjetivos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Gráficos que la UI sabe dibujar. Un ejemplo puede pedir uno por nombre con sus parámetros.
#   usdclp_history   {"years": int}                                   dólar observado histórico
#   forward_points   {"spot", "r_dom", "r_for"}                        forward vs plazo (0–2 años)
#   forward_payoff   {"spot", "forward", "side": "buy"|"sell", "notional_usd"}
#                                                                      compensación al vencimiento
#   hedge_compare    {"spot", "forward", "notional_usd", "side"}       costo en CLP con y sin forward
#   option_payoff    {"kind": "call"|"put", "position": "long"|"short", "strike", "premium", "spot"}
#   strategy_payoff  {"preset": clave de strategies.PRESETS, "spot", "vol", "years", "r_dom", "r_for"}
#   hedge_backtest   {"years": float, "nominal_usd": float}            importador con y sin forward
ChartName = Literal[
    "usdclp_history",
    "forward_points",
    "forward_payoff",
    "hedge_compare",
    "option_payoff",
    "strategy_payoff",
    "hedge_backtest",
]


@dataclass(frozen=True)
class Chart:
    name: ChartName
    params: dict = field(default_factory=dict)
    caption: str | None = None


@dataclass(frozen=True)
class Concept:
    """Pantalla de definición: idea central + términos clave."""

    title: str
    body: str  # markdown, 2–5 párrafos cortos
    terms: list[tuple[str, str]] = field(default_factory=list)  # (término, definición de una línea)
    callout: str | None = None  # "Ojo:" — matiz o advertencia ("en la realidad es más complejo…")
    chart: Chart | None = None
    kind: Literal["concept"] = "concept"


@dataclass(frozen=True)
class Example:
    """Pantalla de ejemplo numérico paso a paso."""

    title: str
    setup: str  # el caso: quién, cuánto, cuándo
    steps: list[str]  # cada paso una línea con la cuenta
    takeaway: str  # la lección en una oración
    chart: Chart | None = None
    lab: str | None = None  # ruta de página laboratorio, ej. "app_pages/2_Forward.py"
    kind: Literal["example"] = "example"


# Demos interactivas: la UI dibuja controles (sliders/segmented) + resultado en vivo (métricas y gráfico).
# `params` fija los valores iniciales; el usuario los mueve para VER cómo funciona (no es una prueba).
#   dollar_move        {"spot", "notional_usd", "side": "importer"|"exporter"}  slider dólar futuro -> pesos a pagar/recibir
#   forward_calc       {"spot", "r_dom", "r_for", "years"}       sliders tasas y plazo -> forward y puntos
#   forward_settlement {"forward", "spot_T", "side": "buy"|"sell", "notional_usd"}  slider spot al vencimiento -> quién paga a quién
#   forward_vs_none    {"spot", "forward", "notional_usd"}       slider dólar al vencimiento -> costo con y sin forward
#   mtm                {"forward", "market_forward", "notional_usd", "credit_line_clp"}  slider forward de mercado -> MtM y si se piden garantías
#   option_payoff      {"kind", "position", "strike", "premium", "spot"}  controles -> resultado al vencimiento
#   option_price       {"kind", "spot", "strike", "vol", "years", "r_dom", "r_for"}  sliders vol/plazo/strike -> prima (intrínseco + temporal)
#   collar             {"spot", "vol", "years", "r_dom", "r_for", "call_strike"}  slider strike call -> strike put de costo cero y gráfico
#   hedge_ratio        {"spot", "forward", "notional_usd"}       slider % cubierto -> rango de costo en escenarios del dólar
#   backtest           {"years", "nominal_usd"}                  fecha de decisión -> qué habría pasado con y sin forward
DemoName = Literal[
    "dollar_move",
    "forward_calc",
    "forward_settlement",
    "forward_vs_none",
    "mtm",
    "option_payoff",
    "option_price",
    "collar",
    "hedge_ratio",
    "backtest",
]


@dataclass(frozen=True)
class Demo:
    """Pantalla interactiva tipo calculadora: el usuario mueve controles y ve el efecto."""

    title: str
    prompt: str  # qué probar: "Mueve el dólar al vencimiento y mira quién le paga a quién."
    demo: DemoName
    params: dict = field(default_factory=dict)
    takeaway: str | None = None  # lo que debería notar, en una oración
    kind: Literal["demo"] = "demo"


@dataclass(frozen=True)
class Choice:
    """Ejercicio de alternativas. NO USAR en los temas (decisión 2026-11-02: se reemplaza por Demo)."""

    question: str
    options: list[str]
    answer: int  # índice correcto
    explanation: str  # por qué; se muestra al revisar
    kind: Literal["choice"] = "choice"


@dataclass(frozen=True)
class Numeric:
    """Ejercicio numérico. NO USAR en los temas (se reemplaza por Demo)."""

    question: str
    answer: float
    tolerance: float  # absoluta
    unit: str  # "CLP por USD", "CLP", "%"…
    explanation: str
    hint: str | None = None
    decimals: int = 2  # decimales del input
    kind: Literal["numeric"] = "numeric"


@dataclass(frozen=True)
class Summary:
    """Cierre del capítulo."""

    points: list[str]  # 3–5 ideas para llevarse
    next_hint: str | None = None  # puente al capítulo siguiente
    kind: Literal["summary"] = "summary"


Screen = Concept | Example | Demo | Choice | Numeric | Summary


@dataclass(frozen=True)
class Chapter:
    number: int
    slug: str  # url_path, ej. "cap-1-riesgo-cambiario"
    title: str  # corto para el menú
    icon: str  # Material Symbol ":material/...:"
    goal: str  # "Al terminar vas a poder…" (una oración)
    minutes: int  # duración estimada
    screens: list[Screen]
    menu: str = ""  # nombre corto para el menú lateral (la pregunta completa se corta); vacío = title

    @property
    def demos(self) -> list[Demo]:
        return [s for s in self.screens if isinstance(s, Demo)]
