"""Helpers de presentación para la app Streamlit: formato chileno, disclaimer, paleta y estilo Plotly.

Formato numérico chileno: separador de miles "." y decimal "," (1.234.567,89).
Este módulo sí importa Streamlit (a diferencia del resto del núcleo, que es puro).
"""

from __future__ import annotations

import math

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


# ---------------------------------------------------------------- bloques de página


def page_setup(title: str, icon: str = "📘") -> None:
    """Configura la página (debe llamarse primero) y muestra el título."""
    st.set_page_config(page_title=f"{title} · Derivados 101", page_icon=icon, layout="wide")
    st.title(f"{icon} {title}")


def learn_box(text: str) -> None:
    """Párrafo corto de 'qué vas a aprender' al inicio de cada página."""
    st.info(f"**Qué vas a aprender.** {text}", icon="🎯")


def disclaimer() -> None:
    """Disclaimer visible al pie de cada página y en la barra lateral."""
    st.sidebar.caption(f"⚠️ {DISCLAIMER}")
    st.divider()
    st.caption(f"⚠️ {DISCLAIMER} Ejemplos genéricos con datos ilustrativos.")


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
