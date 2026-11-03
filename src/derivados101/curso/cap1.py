"""¿Qué es el riesgo cambiario?

Cifras de ejemplo fijas (spot 890). Las del histórico salen del dólar observado 2024–2025
(``data/usdclp_dolar_observado.csv``) y se verificaron con ``market.load_usdclp``.
"""

from .model import Chapter, Chart, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=1,
    slug="que-es-el-riesgo-cambiario",
    title="¿Qué es el riesgo cambiario?",
    menu="Riesgo cambiario",
    icon=":material/currency_exchange:",
    goal="Por qué un dólar que se mueve es un problema para una empresa.",
    minutes=6,
    screens=[
        Concept(
            title="Si compras o vendes en dólares, tu resultado en pesos queda abierto",
            body=(
                "Una empresa chilena lleva sus cuentas en pesos. Si paga o cobra en dólares, el monto en pesos "
                "depende del tipo de cambio del día en que paga o cobra. Entre la firma y el pago pueden pasar meses.\n\n"
                "Un **importador** debe dólares: pierde si el dólar sube. Un **exportador** cobra dólares: "
                "pierde si el dólar baja. El mismo movimiento es buena noticia para uno y mala para el otro."
            ),
            terms=[
                ("Tipo de cambio USD/CLP", "Cuántos pesos cuesta un dólar. Ejemplo: 890 CLP por USD."),
                ("Spot", "El tipo de cambio para comprar o vender dólares hoy, al contado."),
                ("Exposición", "Monto en dólares cuyo valor en pesos todavía no está fijado."),
            ],
        ),
        Example(
            title="Un importador de telas con una factura a 1 año",
            setup=(
                "Ejemplo. Un importador chileno de telas debe pagar US\\$500.000 en 1 año. Hoy el dólar está en 890."
            ),
            steps=[
                "Al dólar de hoy, la factura equivale a 500.000 × 890 = \\$445.000.000.",
                "Si en 1 año el dólar está en 950, paga \\$475.000.000: \\$30.000.000 más.",
                "Si el dólar está en 850, paga \\$425.000.000: \\$20.000.000 menos.",
            ],
            takeaway="La factura en dólares es fija. Su costo en pesos puede variar en decenas de millones.",
        ),
        Demo(
            title="Mueve el dólar y mira cuántos pesos paga el importador",
            prompt=(
                "Mueve el dólar del día de pago. Sobre 890, el importador paga más pesos que hoy. Bajo 890, "
                "paga menos. Prueba con 950: son \\$30.000.000 más."
            ),
            demo="dollar_move",
            params={"spot": 890.0, "notional_usd": 500_000, "side": "importer"},
            takeaway="Cada peso que sube el dólar le cuesta \\$500.000 más a una factura de US\\$500.000.",
        ),
        Concept(
            title="En 2024 y 2025 el dólar se movió más de 130 pesos",
            body=(
                "Según el dólar observado que usa esta app, entre 2024 y 2025 el dólar tocó un mínimo de 877,12 "
                "(2 de enero de 2024) y un máximo de 1.012,76 (14 de enero de 2025).\n\n"
                "En ese período, el cambio a 1 año fue desde una caída de cerca de 9% hasta una subida de cerca "
                "de 15%. Para el importador del ejemplo, 15% más son unos \\$66.750.000."
            ),
            callout=(
                "Ojo: el pasado no predice el futuro. El histórico sirve para dimensionar cuánto puede moverse "
                "el dólar, no para adivinar hacia dónde."
            ),
            chart=Chart(
                name="usdclp_history",
                params={"years": 3},
                caption="Dólar observado (CLP por USD). Fuente: Banco Central de Chile.",
            ),
        ),
        Summary(
            points=[
                "El importador pierde si el dólar sube. El exportador pierde si baja.",
                "Pérdida o ganancia en pesos = monto en dólares × cuánto se movió el dólar.",
                "El dólar se mueve decenas de pesos en meses. En facturas grandes son millones.",
            ],
            next_hint="Siguiente: ¿Qué es un derivado? Un contrato para fijar hoy el dólar futuro.",
        ),
    ],
)
