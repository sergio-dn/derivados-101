"""Inicio: qué es un derivado, cobertura vs especulación y mapa de la app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.ui import disclaimer, learn_box, page_setup

page_setup("Derivados 101: cubrirse del dólar sin ser trader", "🧭")

learn_box(
    "Qué es un derivado, para qué lo usa una empresa (cubrirse vs especular) y cómo "
    "recorrer esta app. No necesitas saber nada de finanzas: cada página tiene sliders "
    "para que veas qué pasa con los números cuando cambia el dólar."
)

st.header("¿Qué es un derivado?")
st.markdown(
    """
Un **derivado** es un contrato cuyo valor *deriva* de otra cosa: el **subyacente**
(acá, el tipo de cambio USD/CLP). El contrato no es el dólar en sí; es un acuerdo sobre
**a qué precio** se va a comprar o vender dólares en una fecha futura, o sobre el
**derecho** a hacerlo.

Piensa en un **importador chileno** que debe pagar US\\$500.000 a su proveedor en un año.
Hoy el dólar está en \\$890. Si en un año sube a \\$1.000, la factura le cuesta \\$55 millones
más de lo presupuestado. Un derivado le permite **fijar hoy** (forward) o **ponerle techo**
(opción) a ese precio.
"""
)

c1, c2 = st.columns(2)
with c1:
    st.subheader("🛡️ Cobertura")
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
with c2:
    st.subheader("🎲 Especulación")
    st.markdown(
        """
**No tienes** un riesgo previo: tomas el derivado para apostar a que el dólar sube o baja.

- Si aciertas, ganas; si no, pierdes, y nada lo compensa.
- El mismo contrato puede ser cobertura para una empresa y especulación para otra:
  **lo que define el caso es la exposición que hay detrás**, no el instrumento.
"""
    )

with st.expander("¿Y por qué no simplemente esperar y ver?"):
    st.markdown(
        """
No cubrirse también es una decisión: equivale a **apostar** a que el dólar no se moverá en
contra. Cubrirse tiene costos y exigencias (primas, margen del banco, uso de líneas de crédito) y también
**renuncia a ganancias** si el dólar se mueve a favor. La pregunta correcta no es
"¿ganaré con el derivado?", sino "¿qué nivel de incertidumbre puede tolerar mi negocio?".
"""
    )

st.header("Mapa de la app")
st.caption("Recomendado recorrerla en orden. Cada página parte con lo que vas a aprender.")

pages = [
    ("app_pages/1_Conceptos.py", "📚 Conceptos", "Las 8 preguntas frecuentes y cómo se contabilizan."),
    ("app_pages/2_Forward.py", "📈 Forward", "Fijar hoy el dólar futuro: puntos forward, liquidación y MtM."),
    ("app_pages/3_Opciones.py", "🎛️ Opciones", "Derecho sin obligación: prima, valor intrínseco y temporal."),
    ("app_pages/4_Estrategias.py", "🧩 Estrategias", "Combinar opciones: collares, spreads y el collar cero costo."),
    ("app_pages/5_USDCLP.py", "💵 USD/CLP", "Cuánto se mueve el dólar en Chile y qué habría pasado cubriéndose."),
    ("app_pages/6_Quiz.py", "✅ Quiz", "Pon a prueba lo aprendido."),
]
cols = st.columns(3)
for i, (path, label, desc) in enumerate(pages):
    with cols[i % 3], st.container(border=True):
        st.page_link(path, label=label)
        st.caption(desc)

with st.expander("Convenciones usadas en la app"):
    st.markdown(
        """
- Precios en **CLP por USD** (ej. 898,89). Montos en pesos con formato chileno: \\$1.234.567.
- Tasas anuales en porcentaje; capitalización **compuesta anual** $(1+r)^T$.
- Plazos en años (0,5 = seis meses).
- Ejemplos genéricos ("un importador chileno"); no corresponden a ninguna empresa real.
"""
    )

disclaimer()
