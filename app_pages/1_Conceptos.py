"""Conceptos: FAQ de derivados y contabilización (simplificada)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.ui import PAGES, disclaimer, learn_box, page_setup, section

page_setup(
    "Conceptos clave",
    icon=PAGES[1].icon,
    subtitle="Las preguntas frecuentes antes de firmar un derivado, y cómo se reflejan en la contabilidad.",
)

learn_box(
    "Las 8 preguntas que todo equipo de finanzas se hace antes de firmar un derivado: "
    "qué es, para qué sirve, qué tipos hay, cómo se valoriza y qué efectos tiene en "
    "caja, balance y resultados."
)

FAQ: list[tuple[str, str]] = [
    (
        "1. ¿Qué es un derivado?",
        """
Un **instrumento financiero cuyo valor depende de un activo subyacente**, sin necesidad de
comprar ese subyacente. En esta app el subyacente es el tipo de cambio **USD/CLP**.

*Ejemplo:* un forward de compra de US\\$500.000 a un año gana o pierde valor cada vez que se
mueve el dólar, aunque la empresa todavía no haya comprado ni un dólar.
""",
    ),
    (
        "2. ¿Cuáles son las razones para tomar un derivado?",
        """
Dos: **cobertura** o **especulación**.

- **Cobertura:** se mantiene una posición en el subyacente (por ejemplo, una deuda con un
  proveedor en USD) y el derivado busca **reducir esa exposición**.
- **Especulación:** se toma exposición al subyacente para aprovechar un sesgo alcista o
  bajista que se cree tener. Usualmente **aumenta el riesgo**.

*Ejemplo:* comprar dólares a plazo es cobertura para un importador que debe USD, y
especulación para alguien que no tiene ningún flujo en dólares.
""",
    ),
    (
        "3. ¿Cuáles son los tipos de derivados más comunes?",
        """
| Tipo | Qué es |
|---|---|
| **Forward** de moneda o de tasa | Compra/venta (o tasa) fijada hoy para una fecha futura. Obliga a ambas partes. |
| **Call** | Derecho, no obligación, a **comprar** el subyacente a un precio fijado (strike). Se paga prima. |
| **Put** | Derecho, no obligación, a **vender** el subyacente a un precio fijado. Se paga prima. |
| **Cross-currency swap** | Intercambio de flujos en dos monedas a lo largo del tiempo (ej. deuda en USD a CLP). |
| **Credit (default) swap** | Protección contra el incumplimiento de un emisor a cambio de un pago periódico. |

Hay muchos más (futuros, swaps de tasa, opciones exóticas, etc.). En general, para empresas
no financieras los más usados son forwards de moneda y swaps.
""",
    ),
    (
        "4. ¿Qué alternativas de contabilización existen?",
        """
Dos tratamientos:

- **Como especulación** (o cobertura no designada): el valor del derivado según su
  **Mark-to-Market** va **directo a resultado** del período.
- **Con contabilidad de cobertura:** aplican los criterios de **IFRS 9** (ver pregunta 6 y la
  sección de abajo), que permiten calzar el efecto del derivado con el de la partida cubierta.
""",
    ),
    (
        "5. ¿Qué considerar al contratar un derivado?",
        """
Tres tipos de efectos:

- **Financieros:** los flujos que se pagan o reciben **a la liquidación**. Pueden ir en la
  **misma o en la contraria** dirección que el subyacente cubierto.
- **De liquidez:** una **prima al inicio** (opciones) o **llamados de margen** / garantías
  durante la vida del contrato, además de los flujos al liquidar.
- **Contables:** efectos en **patrimonio o resultado** según el tratamiento elegido,
  **independientes del efecto financiero a término**.

*Ejemplo:* un importador cubierto con forward puede tener que pagar una compensación al
banco (el dólar bajó) justo cuando su importación le salió más barata: el efecto neto es el
precio fijado, pero la caja se mueve en dos partidas distintas.
""",
    ),
    (
        "6. ¿Qué es hedge accounting?",
        """
Una metodología que, **bajo ciertos criterios**, permite llevar los efectos del derivado a
**patrimonio (OCI)** y no a resultado, o reconocer **en conjunto** el efecto neto de la
partida cubierta y del derivado. El objetivo es **reducir la volatilidad del resultado**
que produciría el MtM del derivado por sí solo. Ver detalle más abajo.
""",
    ),
    (
        "7. ¿Cómo se valoriza un derivado?",
        """
**Depende del tipo** de derivado y, en general, **no es trivial**. Lo afectan las tasas de
interés de cada moneda, el riesgo (de crédito y volatilidad), el plazo, el spot, entre otros.

*Ejemplos en esta app:* el forward se valoriza con la paridad de tasas (página Forward); las
opciones, con Garman-Kohlhagen o árboles binomiales (página Opciones).
""",
    ),
    (
        "8. ¿Cómo se calcula el MtM (Mark-to-Market)?",
        """
Al **cierre de cada período** se calcula el **valor de mercado de la posición**, independiente
de si se posee o no el subyacente.

*Ejemplo:* para un forward, se compara el precio pactado con el forward de mercado para el
plazo que queda y se trae a valor presente. Pruébalo en la sección "MtM" de la página **Forward**.
""",
    ),
]

# Bloques temáticos del FAQ: (pestaña, ícono, índices de FAQ). Mantienen el orden 1→8.
FAQ_GROUPS: list[tuple[str, str, list[int]]] = [
    ("Fundamentos", ":material/lightbulb:", [0, 1, 2]),
    ("Contratar y contabilizar", ":material/receipt_long:", [3, 4, 5]),
    ("Valorización", ":material/calculate:", [6, 7]),
]
FAQ_ICONS = [
    ":material/help:",
    ":material/target:",
    ":material/category:",
    ":material/account_balance:",
    ":material/checklist:",
    ":material/balance:",
    ":material/price_check:",
    ":material/event_repeat:",
]

section("Preguntas frecuentes", icon=":material/forum:")
tabs = st.tabs([f"{icon} {name}" for name, icon, _ in FAQ_GROUPS])
for tab, (_name, _icon, idxs) in zip(tabs, FAQ_GROUPS, strict=True):
    with tab:
        for j, i in enumerate(idxs):
            question, answer = FAQ[i]
            with st.expander(question, icon=FAQ_ICONS[i], expanded=(j == 0)):
                st.markdown(answer)

section("¿Dónde va la ganancia o pérdida del derivado?", icon=":material/account_balance_wallet:")
st.warning(
    "La aplicación de IFRS 9 (designación, medición de "
    "efectividad, tratamiento del valor temporal de opciones y de los puntos forward, "
    "impuestos diferidos) requiere revisión con tus auditores.",
    title="Simplificación pedagógica",
    icon=":material/edit_note:",
)

# Dos tarjetas lado a lado y de igual alto: contenedor horizontal con hijos height="stretch".
cards = st.container(horizontal=True, gap="medium")
with cards, st.container(border=True, height="stretch"):
    st.subheader("Sin hedge accounting", anchor=False)
    st.badge("MtM a resultados", icon=":material/show_chart:", color="orange")
    st.markdown(
        """
**Especulación o cobertura no designada.**

1. Cada cierre, el derivado se mide a valor razonable (MtM).
2. La variación del MtM va **directo a resultados**.
3. La partida cubierta (ej. una compra futura) puede no estar aún en el balance.

**Efecto:** el resultado muestra volatilidad aunque la cobertura funcione económicamente.
"""
    )
with cards, st.container(border=True, height="stretch"):
    st.subheader("Con hedge accounting (flujo de efectivo)", anchor=False)
    st.badge("Porción efectiva a OCI", icon=":material/savings:", color="green")
    st.markdown(
        """
**Cobertura designada y documentada.**

1. El derivado igual se mide a valor razonable en el balance.
2. La parte **efectiva** de la variación va a **OCI** (reserva de cobertura en patrimonio);
   la inefectiva, a resultados.
3. Si lo cubierto es una **compra de inventario**, al reconocer el inventario el monto
   acumulado en OCI **se incorpora a su costo** (*basis adjustment*, IFRS 9 6.5.11(d)) y
   llega a resultados vía **costo de venta** cuando ese inventario se vende.

**Efecto:** el costo del inventario refleja el tipo de cambio "fijado", sin saltos por el MtM.
"""
    )

with st.expander(
    "Requisitos para aplicar hedge accounting (IFRS 9 6.3.3 y 6.4.1)", icon=":material/fact_check:"
):
    st.markdown(
        """
- **Designación y documentación formal al inicio** de la relación: objetivo y estrategia de
  gestión de riesgo, partida cubierta, instrumento, riesgo cubierto y cómo se evaluará la
  efectividad.
- **Relación económica** entre la partida cubierta y el instrumento (sus valores tienden a
  moverse en sentido contrario ante el riesgo cubierto).
- Que el **riesgo de crédito no domine** los cambios de valor de esa relación económica.
- **Hedge ratio** (proporción cubierta) consistente con el que la empresa usa efectivamente
  en su gestión de riesgo.
- Solo partidas elegibles: para transacciones previstas, deben ser **altamente probables**.
"""
    )

with st.expander("Ejemplo numérico simple", icon=":material/table_chart:"):
    st.markdown(
        """
Un importador compra un forward por US\\$500.000 a \\$898,89 para pagar una importación de
inventario. Al cierre de año (antes de recibir la mercadería) el MtM es **+\\$12.000.000**
(el dólar subió).

| | Sin hedge accounting | Con hedge accounting (100% efectiva) |
|---|---|---|
| Balance: activo derivado | +\\$12.000.000 | +\\$12.000.000 |
| Resultado del ejercicio | +\\$12.000.000 | \\$0 |
| Patrimonio (OCI) | \\$0 | +\\$12.000.000 |

Cuando llega la mercadería (más cara por el dólar alto), con hedge accounting los
\\$12 millones salen del OCI y **rebajan el costo del inventario**: queda registrado al tipo de
cambio fijado. El efecto llega a resultados recién vía costo de venta, cuando se vende.
"""
    )

disclaimer(current="1_Conceptos.py")
