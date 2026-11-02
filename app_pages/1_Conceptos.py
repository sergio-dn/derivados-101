"""Conceptos: FAQ de derivados y una idea básica de cómo se registran."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from derivados101.ui import PAGES, disclaimer, learn_box, page_setup, section

page_setup(
    "Conceptos clave",
    icon=PAGES[1].icon,
    subtitle="Las preguntas frecuentes antes de firmar un derivado, y una idea básica de cómo se registra.",
)

learn_box(
    "Las 8 preguntas que todo equipo de finanzas se hace antes de firmar un derivado: "
    "qué es, para qué sirve, qué tipos hay, qué exige en caja y garantías, y cómo se "
    "refleja (a grandes rasgos) en los estados financieros."
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
| **Forward** de moneda | Compra o venta de dólares a un precio fijado hoy para una fecha futura. Obliga a ambas partes. |
| **Call** | Derecho, no obligación, a **comprar** dólares a un precio fijado (strike). Se paga una prima. |
| **Put** | Derecho, no obligación, a **vender** dólares a un precio fijado. Se paga una prima. |
| **Swap de tasa** | Intercambiar pagos de interés: por ejemplo, convertir una deuda a tasa variable en tasa fija. |
| **Cross-currency swap** | Intercambiar flujos en dos monedas a lo largo del tiempo (ej. una deuda en USD a CLP). |

Hay más (futuros, opciones exóticas, etc.), pero para empresas no financieras en Chile los
más usados son los forwards de moneda y los swaps.
""",
    ),
    (
        "4. ¿Cómo se registra un derivado en la contabilidad?",
        """
En simple: el derivado va al balance a su **valor de mercado (MtM)** y, en general, sus
cambios de valor **afectan el resultado** de cada período.

Existe la **contabilidad de coberturas** (*hedge accounting*), que permite suavizar ese
efecto si se cumplen ciertos requisitos (ver pregunta 6 y la sección de abajo).
""",
    ),
    (
        "5. ¿Qué considerar al contratar un derivado?",
        """
Tres tipos de efectos:

- **Financieros:** los flujos que se pagan o reciben **al vencimiento**. Pueden ir en la
  **misma o en la contraria** dirección que el negocio cubierto.
- **De liquidez:** una **prima al inicio** (opciones) y, mientras el contrato está vivo, el
  riesgo de que el banco pida respaldo si el MtM se pone en tu contra. Para empresas en Chile
  lo usual es que el banco **consuma tu línea de crédito** o **pida garantías**.
- **Contables:** el MtM puede mover el resultado aunque la cobertura funcione bien.

*Ejemplo:* un importador cubierto con forward puede tener que pagar una compensación al
banco (el dólar bajó) justo cuando su importación le salió más barata: el efecto neto es el
precio fijado, pero la caja se mueve en dos partidas distintas.
""",
    ),
    (
        "6. ¿Qué es hedge accounting?",
        """
Es la **contabilidad de coberturas**: un tratamiento opcional que, si se cumplen requisitos
formales, permite registrar el derivado **junto con lo que cubre** para que el resultado no
salte con cada cambio del MtM. Su aplicación se define con contabilidad y auditores.
""",
    ),
    (
        "7. ¿Cómo se valoriza un derivado?",
        """
Su valor **depende principalmente de** el spot, las **tasas de interés** de cada moneda, el
**plazo** y, en las opciones, la **volatilidad** del dólar. No necesitas hacerlo a mano:
**la app lo calcula por ti** en las páginas **Forward** y **Opciones**, y puedes mover cada
variable para ver cómo cambia.
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

# Dos tarjetas lado a lado y de igual alto: contenedor horizontal con hijos height="stretch".
cards = st.container(horizontal=True, gap="medium")
with cards, st.container(border=True, height="stretch"):
    st.subheader("Regla general", anchor=False)
    st.badge("MtM a resultados", icon=":material/show_chart:", color="orange")
    st.markdown(
        """
1. Cada cierre, el derivado se registra a su **valor de mercado (MtM)**.
2. Los cambios de ese valor van al **resultado** del período.

**Efecto:** el resultado puede mostrar ganancias o pérdidas del derivado antes de que
llegue la factura en dólares que se está cubriendo.
"""
    )
with cards, st.container(border=True, height="stretch"):
    st.subheader("Con contabilidad de coberturas", anchor=False)
    st.badge("Efecto suavizado", icon=":material/savings:", color="green")
    st.markdown(
        """
1. El derivado igual se registra a su valor de mercado.
2. Si se cumplen los requisitos, sus cambios se reconocen **junto con lo que cubre**.

**Efecto:** el resultado refleja el tipo de cambio "fijado", sin saltos por el MtM.
"""
    )

st.warning(
    "En la realidad es más complejo: aplicar contabilidad de coberturas exige requisitos "
    "formales (documentación, efectividad, entre otros) y tiene efectos tributarios. Revísalo "
    "con tu equipo de contabilidad y tus auditores antes de contratar.",
    title="Esto es una simplificación",
    icon=":material/edit_note:",
)

disclaimer(current="1_Conceptos.py")
