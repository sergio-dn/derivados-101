"""Helpers de presentación para la app Streamlit: formato chileno, disclaimer, paleta y estilo Plotly.

Formato numérico chileno: separador de miles "." y decimal "," (1.234.567,89).
Este módulo sí importa Streamlit (a diferencia del resto del núcleo, que es puro).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import plotly.graph_objects as go
import streamlit as st

DISCLAIMER = "Material educativo. No es asesoría financiera ni contable."

# Paleta sobria, legible en tema claro y oscuro.
PALETTE: dict[str, str] = {
    "primary": "#1F6F8B",   # azul petróleo: serie principal / opciones
    "secondary": "#E07A2E",  # naranjo: subyacente / no cubierto
    "accent": "#2E9E6A",    # verde: combinado / ganancia
    "negative": "#C8463D",  # rojo: pérdida
    "neutral": "#8A96A3",   # gris: referencias (spot, strike)
    "purple": "#7A5BA6",    # cuarta serie
}
SERIES_COLORS = [PALETTE[k] for k in ("primary", "secondary", "accent", "purple", "negative")]


# ---------------------------------------------------------------- formato


def fmt_num(value: float | None, decimals: int = 0) -> str:
    """Número con formato chileno: miles con '.', decimales con ','."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    # Se formatea en estilo US y luego se intercambian separadores.
    s = f"{value:,.{decimals}f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    if s.startswith("-") and float(value) == 0:
        s = s[1:]  # evita "-0"
    return s


def fmt_clp(value: float | None, decimals: int = 0) -> str:
    """Monto en pesos chilenos: $1.234.567 (signo antes del $)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    sign = "-" if value < 0 and round(abs(value), decimals) != 0 else ""
    return f"{sign}${fmt_num(abs(value), decimals)}"


def md_clp(value: float | None, decimals: int = 0) -> str:
    """Como fmt_clp pero con el "$" escapado para textos markdown.

    Streamlit interpreta pares de "$" como LaTeX: "$890 ... $1.000" se renderiza como fórmula.
    """
    return fmt_clp(value, decimals).replace("$", "\\$")


def md_usd(value: float | None, decimals: int = 0) -> str:
    """Como fmt_usd pero con el "$" escapado para textos markdown (ver md_clp)."""
    return fmt_usd(value, decimals).replace("$", "\\$")


def fmt_rate(value: float | None, decimals: int = 2) -> str:
    """Tipo de cambio CLP por USD: 898,89."""
    return fmt_num(value, decimals)


def fmt_usd(value: float | None, decimals: int = 0) -> str:
    """Monto en dólares: US$500.000."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    sign = "-" if value < 0 and round(abs(value), decimals) != 0 else ""
    return f"{sign}US${fmt_num(abs(value), decimals)}"


def fmt_pct(value: float | None, decimals: int = 2) -> str:
    """Porcentaje a partir de un decimal: 0.0511 -> '5,11%'."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{fmt_num(value * 100, decimals)}%"


# ---------------------------------------------------------------- dólar de ejemplo


@st.cache_data(ttl=3600, show_spinner=False)
def _example_spot_cached(live: bool) -> tuple[float, str, str]:
    from .market import latest_spot  # import local: evita costo de httpx/pandas si no se usa

    value, day, source = latest_spot(live=live, timeout=3.0)
    return round(value, 2), day.strftime("%d-%m-%Y"), source


def example_spot() -> tuple[float, str, str]:
    """Dólar de ejemplo para los valores por defecto: el último observado que se encuentre.

    Devuelve ``(valor, fecha dd-mm-aaaa, fuente)``. Con la variable de entorno
    ``DERIVADOS101_OFFLINE=1`` (tests) no consulta internet y usa el CSV local.
    """
    live = os.environ.get("DERIVADOS101_OFFLINE") != "1"
    return _example_spot_cached(live)


@st.cache_data(ttl=3600, show_spinner=False)
def example_rates() -> tuple[float, float, str]:
    """Tasas de ejemplo (CLP, USD) = última fila de data/tasas_referencia.csv.

    Devuelve ``(r_clp, r_usd, fecha dd-mm-aaaa)`` en decimales. Si el archivo no existe o
    falla, cae a 5,11% / 4,07% (ejemplo de la planilla original).
    """
    try:
        from .market import reference_rates

        r_clp, r_usd, day = reference_rates()
        return round(r_clp, 4), round(r_usd, 4), day.strftime("%d-%m-%Y")
    except Exception:  # noqa: BLE001 - la UI nunca debe caerse por los datos de ejemplo
        return 0.0511, 0.0407, "planilla"


def example_spot_note() -> None:
    """Caption estándar que deja explícito que el spot por defecto es solo un ejemplo."""
    value, day, source = example_spot()
    origin = {"mindicador.cl": "dólar observado (mindicador.cl)", "csv": "dólar observado (datos incluidos)"}
    st.caption(
        f":material/info: Ejemplo: los valores por defecto parten del último "
        f"{origin.get(source, 'valor de referencia')} disponible, {fmt_rate(value)} al {day}. "
        "Puedes cambiarlos; no es una cotización para operar."
    )


# ---------------------------------------------------------------- registro de páginas


@dataclass(frozen=True)
class PageInfo:
    """Metadatos de una página: única fuente para la navegación, el mapa de Inicio y "siguiente"."""

    path: str  # relativo a la raíz del repo
    title: str  # nombre corto en el menú
    icon: str  # Material Symbol (":material/...:")
    section: str  # grupo en el menú lateral
    blurb: str  # una línea para el mapa de Inicio


PAGES: list[PageInfo] = [
    PageInfo("app_pages/0_Inicio.py", "Inicio", ":material/explore:", "Empezar",
             "Qué es un derivado y cómo recorrer la app."),
    PageInfo("app_pages/1_Conceptos.py", "Conceptos", ":material/menu_book:", "Empezar",
             "Las 8 preguntas frecuentes y una idea básica de cómo se registran."),
    PageInfo("app_pages/2_Forward.py", "Forward", ":material/trending_flat:", "Instrumentos",
             "Fijar hoy el dólar futuro: puntos forward, liquidación y MtM."),
    PageInfo("app_pages/3_Opciones.py", "Opciones", ":material/tune:", "Instrumentos",
             "Derecho sin obligación: prima, valor intrínseco y temporal."),
    PageInfo("app_pages/4_Estrategias.py", "Estrategias", ":material/stacks:", "Instrumentos",
             "Combinar opciones: collares, spreads y el collar de costo cero."),
    PageInfo("app_pages/5_USDCLP.py", "Dólar en Chile", ":material/monitoring:", "Práctica",
             "Cuánto se mueve el USD/CLP y qué habría pasado cubriéndose."),
    PageInfo("app_pages/6_Quiz.py", "Quiz", ":material/quiz:", "Práctica",
             "Pon a prueba lo aprendido."),
]


def _page_info(path_suffix: str) -> PageInfo | None:
    return next((p for p in PAGES if p.path.endswith(path_suffix)), None)


# ---------------------------------------------------------------- bloques de página


def page_setup(title: str, icon: str = ":material/school:", subtitle: str | None = None) -> None:
    """Configura la página (debe llamarse primero) y muestra título y bajada opcional.

    ``icon`` es un Material Symbol (":material/...:"). ``subtitle`` es una frase corta bajo el título.
    """
    st.set_page_config(page_title=f"{title} · Derivados 101", page_icon=icon, layout="wide")
    st.title(title, icon=icon)
    if subtitle:
        st.markdown(f":gray[{subtitle}]")


def learn_box(text: str) -> None:
    """Recuadro de 'qué vas a aprender' al inicio de cada página."""
    st.info(text, title="Qué vas a aprender", icon=":material/school:")


def section(title: str, icon: str | None = None) -> None:
    """Encabezado de sección numerada dentro de una página (st.header con ícono opcional)."""
    st.header(title, icon=icon)


def next_page(current: str) -> None:
    """Enlaces "anterior / siguiente" al pie para recorrer la app en orden.

    ``current`` es el nombre de archivo de la página (ej. "2_Forward.py"). Solo funciona bajo
    st.navigation (app.py); si la página corre suelta (tests directos), no muestra nada.
    """
    info = _page_info(current)
    if info is None:
        return
    idx = PAGES.index(info)
    prev_p = PAGES[idx - 1] if idx > 0 else None
    next_p = PAGES[idx + 1] if idx + 1 < len(PAGES) else None
    try:
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            if prev_p:
                st.page_link(prev_p.path, label=f"Anterior: {prev_p.title}", icon=":material/arrow_back:")
            if next_p:
                st.page_link(next_p.path, label=f"Siguiente: {next_p.title}", icon=":material/arrow_forward:",
                             icon_position="right")
    except Exception:  # noqa: BLE001 - st.page_link exige st.navigation; fuera de ella se omite
        pass


def disclaimer(current: str | None = None) -> None:
    """Pie de página: navegación anterior/siguiente (si se indica la página) y disclaimer visible."""
    st.space("medium")
    if current:
        next_page(current)
    st.sidebar.caption(f":material/info: {DISCLAIMER}")
    st.caption(f":material/info: {DISCLAIMER} Ejemplos genéricos con datos ilustrativos.")


# ---------------------------------------------------------------- Plotly


def style_fig(
    fig: go.Figure,
    x_title: str | None = None,
    y_title: str | None = None,
    height: int = 420,
) -> go.Figure:
    """Estilo común de gráficos: separadores chilenos, leyenda arriba, márgenes compactos.

    No fija colores de fondo para que Streamlit adapte el gráfico al tema claro/oscuro.
    """
    # Leyenda horizontal BAJO el gráfico: arriba choca con el título y con las etiquetas de
    # líneas verticales. Se ubica ~80 px bajo el área de datos (deja espacio al título del eje X);
    # Plotly expande el margen inferior automáticamente si la leyenda ocupa varias filas.
    plot_height = max(height - 110, 150)
    fig.update_layout(
        separators=",.",  # decimal ",", miles "."
        height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        title=dict(x=0, xanchor="left", y=0.98, yanchor="top"),
        legend=dict(orientation="h", yanchor="top", y=-80 / plot_height, xanchor="left", x=0),
        hovermode="x unified",
        colorway=SERIES_COLORS,
    )
    if x_title is not None:
        fig.update_xaxes(title_text=x_title)
    if y_title is not None:
        fig.update_yaxes(title_text=y_title)
    fig.update_yaxes(zeroline=True, zerolinewidth=1)
    return fig


def vline(
    fig: go.Figure,
    x: float,
    label: str,
    color: str | None = None,
    dash: str = "dot",
    position: str = "top right",
) -> None:
    """Línea vertical de referencia (spot, strike, breakeven) con etiqueta."""
    fig.add_vline(
        x=x,
        line_dash=dash,
        line_color=color or PALETTE["neutral"],
        line_width=1,
        annotation_text=label,
        annotation_position=position,  # usar "top left" en la 2ª línea para no superponer
    )
