"""¿Qué es una opción?

Cifras de ejemplo (fijas): spot 890, tasas 5,11% CLP / 4,07% USD, plazo 1 año, volatilidad 12%.
Primas calculadas con ``options.garman_kohlhagen``: call 900 = 40,42; put 900 = 41,47;
call 850 = 67,30; call 900 con vol 20% = 67,64; call 900 a 6 meses = 26,98.
"""

from .model import Chapter, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=6,
    slug="que-es-una-opcion",
    title="¿Qué es una opción?",
    menu="Opción",
    icon=":material/tune:",
    goal="Cómo funciona un seguro contra el dólar: pagas una prima y conservas el lado bueno.",
    minutes=4,
    screens=[
        Concept(
            title="Una opción es un derecho que se paga por adelantado",
            body=(
                "El forward obliga a las dos partes. La opción obliga solo a quien la vende. Quien la "
                "compra decide al vencimiento si la ejerce o la deja expirar.\n\n"
                "Ese derecho cuesta una prima, que el comprador paga al inicio y no recupera. "
                "Funciona como un seguro: te protege del escenario malo y conservas el bueno.\n\n"
                "La call le sirve al importador, que teme un alza. La put le sirve al exportador, "
                "que teme una baja."
            ),
            terms=[
                ("Call", "Derecho a COMPRAR dólares al strike."),
                ("Put", "Derecho a VENDER dólares al strike."),
                ("Strike", "Precio de ejercicio, fijado hoy, en CLP por USD."),
                ("Prima", "Lo que paga el comprador al vendedor por el derecho."),
                ("Vendedor", "Cobra la prima y asume la obligación. Puede perder mucho más que la prima."),
            ],
            callout=(
                "Ojo: aquí las opciones solo se ejercen al vencimiento y se liquidan por compensación. "
                "En la realidad existen otras variantes."
            ),
        ),
        Example(
            title="Un importador compra una call para ponerle techo al dólar",
            setup=(
                "Un importador chileno de telas pagará US\\$500.000 en 1 año. Compra una call con "
                "strike 900 y prima de 40,42 CLP por USD. Ejemplo: spot 890, tasas 5,11% CLP y "
                "4,07% USD, volatilidad 12%."
            ),
            steps=[
                "Prima total hoy: 40,42 × 500.000 = \\$20.208.703.",
                "Si el dólar termina en 950, ejerce y recibe (950 − 900) × 500.000 = \\$25.000.000.",
                "Si termina en 850, no ejerce: compra a 850 en el mercado y solo pierde la prima.",
                "En ningún escenario paga más de 900 + 40,42 = 940,42 por dólar.",
            ],
            takeaway="La call fija un techo de 940,42 y deja abierta la ganancia si el dólar baja.",
            lab="app_pages/3_Opciones.py",
        ),
        Demo(
            title="Mueve el dólar y mira quién gana con la opción",
            prompt=(
                "Parte con la call comprada a 900 y prima 40,42. Bajo 900 pierdes solo la prima. "
                "Sobre 940,42 la call gana. Luego cambia a vender la call y mira cómo la pérdida "
                "deja de tener techo."
            ),
            demo="option_payoff",
            params={"kind": "call", "position": "long", "strike": 900.0, "premium": 40.42, "spot": 890.0},
            takeaway="El comprador arriesga como máximo la prima; el vendedor puede perder mucho más.",
        ),
        Summary(
            points=[
                "La call protege al que compra dólares; la put, al que los vende.",
                "El comprador paga la prima al inicio y esa es su pérdida máxima.",
                "El vendedor cobra la prima y asume una obligación que puede costarle mucho más.",
            ],
            next_hint="Siguiente: de qué depende el precio de una opción.",
        ),
    ],
)
