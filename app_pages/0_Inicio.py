"""Inicio: qué es un derivado, cobertura vs especulación y mapa de la app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.ui import (
    PAGES,
    disclaimer,
    example_spot,
    fmt_num,
    learn_box,
    md_clp,
    md_usd,
    page_setup,
    section,
)

page_setup(
    "Derivados 101: cubrirse del dólar sin ser trader",
    icon=PAGES[0].icon,
    subtitle="Una guía práctica, con números que puedes mover, para entender forwards y opciones USD/CLP.",
)

st.markdown(
    ":blue-badge[:material/handshake: Qué es un derivado] "
    ":green-badge[:material/shield: Cubrirse vs especular] "
    ":orange-badge[:material/calculate: Forwards y opciones con números]"
)

learn_box(
    "Qué es un derivado, para qué lo usa una empresa (cubrirse vs especular) y cómo "
    "recorrer esta app. No necesitas saber nada de finanzas: cada página tiene sliders "
    "para que veas qué pasa con los números cuando cambia el dólar."
)
st.caption(
    ":material/info: Es una introducción práctica a cómo operan los derivados (quién paga a quién, "
    "cuándo y cuánto). No es asesoría financiera ni un curso de contabilidad o de valorización."
)

if st.button(
    "Empezar por Conceptos",
    icon=":material/arrow_forward:",
    icon_position="right",
    type="primary",
    key="start_conceptos",
):
    st.switch_page(PAGES[1].path)

section("¿Qué es un derivado?", icon=":material/help:")

# Ejemplo del importador con el dólar de ejemplo (último observado) y una subida redonda ~12%.
NOMINAL_USD = 500_000
spot_ex, spot_day, _source = example_spot()
spot_ex = round(spot_ex)
spot_up = round(spot_ex * 1.12 / 50) * 50  # valor redondo (múltiplo de 50) ≈ 12% arriba
extra_cost = NOMINAL_USD * (spot_up - spot_ex)
extra_mm = fmt_num(extra_cost / 1e6, 0 if extra_cost % 1_000_000 == 0 else 1)

st.markdown(
    f"""
Un **derivado** es un contrato cuyo valor *deriva* de otra cosa: el **subyacente**
(acá, el tipo de cambio USD/CLP). El contrato no es el dólar en sí; es un acuerdo sobre
**a qué precio** se va a comprar o vender dólares en una fecha futura, o sobre el
**derecho** a hacerlo.

Piensa en un **importador chileno** que debe pagar {md_usd(NOMINAL_USD)} a su proveedor en un
año. Como ejemplo, toma el dólar observado al {spot_day}: {md_clp(spot_ex)}. Si en un año sube
a {md_clp(spot_up)}, la factura le cuesta \\${extra_mm} millones
más de lo presupuestado. Un derivado le permite **fijar hoy** (forward) o **ponerle techo**
(opción) a ese precio.
"""
)

# Dos tarjetas de igual alto: contenedor horizontal con hijos height="stretch".
with st.container(horizontal=True, gap="medium"):
    with st.container(border=True, height="stretch"):
        st.subheader("Cobertura", anchor=False)
        st.badge("Reduce el riesgo", icon=":material/shield:", color="green")
        st.markdown(
            """
Tienes un riesgo **que ya existe** (una deuda o cobro en dólares) y tomas un derivado
**en sentido contrario** para neutralizarlo.

- El importador (debe USD) **compra** dólares a futuro.
- El exportador (recibirá USD) **vende** dólares a futuro.

Lo que pierdes en el derivado lo ganas en el negocio, y viceversa. El objetivo no es
ganar: es **saber hoy cuánto vas a pagar o recibir**.
"""
        )
    with st.container(border=True, height="stretch"):
        st.subheader("Especulación", anchor=False)
        st.badge("Aumenta el riesgo", icon=":material/casino:", color="orange")
        st.markdown(
            """
**No tienes** un riesgo previo: tomas el derivado para apostar a que el dólar sube o baja.

- Si aciertas, ganas; si no, pierdes, y nada lo compensa.
- El mismo contrato puede ser cobertura para una empresa y especulación para otra:
  **lo que define el caso es la exposición que hay detrás**, no el instrumento.
"""
        )

with st.expander("¿Y por qué no simplemente esperar y ver?", icon=":material/hourglass_empty:"):
    st.markdown(
        """
No cubrirse también es una decisión: equivale a **apostar** a que el dólar no se moverá en
contra. Cubrirse tiene costos y exigencias (primas, margen del banco, uso de líneas de crédito) y también
**renuncia a ganancias** si el dólar se mueve a favor. La pregunta correcta no es
"¿ganaré con el derivado?", sino "¿qué nivel de incertidumbre puede tolerar mi negocio?".
"""
    )

section("Mapa de la app", icon=":material/map:")
st.caption("Recomendado recorrerla en orden. Cada página parte con lo que vas a aprender.")

# Mapa generado desde el registro de páginas (sin Inicio), agrupado por sección.
by_section: dict[str, list] = {}
for page in PAGES[1:]:
    by_section.setdefault(page.section, []).append(page)

for section_name, pages in by_section.items():
    st.subheader(section_name, anchor=False)
    cols = st.columns(3)
    for i, page in enumerate(pages):
        with cols[i % 3], st.container(border=True, height="stretch"):
            st.page_link(page.path, label=page.title, icon=page.icon, width="stretch")
            st.caption(page.blurb)

with st.expander("Convenciones usadas en la app", icon=":material/rule:"):
    st.markdown(
        """
- Precios en **CLP por USD** (ej. 898,89). Montos en pesos con formato chileno: \\$1.234.567.
- Tasas anuales en porcentaje; capitalización **compuesta anual** $(1+r)^T$.
- Plazos en años (0,5 = seis meses).
- Ejemplos genéricos ("un importador chileno"); no corresponden a ninguna empresa real.
"""
    )

disclaimer(current="0_Inicio.py")
