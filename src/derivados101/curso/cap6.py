"""¿Cuánto y cuándo cubrirse?

Cifras de ejemplo (fijas): forward 898,89 (spot 890, 5,11% CLP / 4,07% USD, 1 año).
Backtest con ``market.hedge_backtest`` sobre el dólar observado (BCCh) y tasas de referencia
vigentes al inicio, US$500.000 a 1 año:
- inicio 2024-01-02: spot 877,12, forward 896,98, spot final 996,46 -> el forward ahorró \\$49,7 MM.
- inicio 2025-01-02: spot 996,46, forward 1.004,12, spot final 907,13 -> el forward costó \\$48,5 MM más.
Son datos históricos: no cambian con la actualización semanal del CSV.
"""

from .model import Chapter, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=9,
    slug="cuanto-y-cuando-cubrirse",
    title="¿Cuánto y cuándo cubrirse?",
    menu="Cuánto cubrir",
    icon=":material/checklist:",
    goal="Cuánto y a qué plazo cubrir, y cómo juzgar una cobertura sin mirar solo el resultado.",
    minutes=4,
    screens=[
        Concept(
            title="Cubre flujos que conoces, por una parte y al mismo plazo",
            body=(
                "Una política simple responde 3 preguntas:\n\n"
                "1. Qué cubrir: pagos o cobros en dólares con fecha y monto razonablemente seguros.\n"
                "2. Cuánto: un porcentaje, más alto mientras más seguro es el flujo. Cubrir el 100% "
                "de algo incierto puede dejarte con un derivado sin exposición detrás.\n"
                "3. A qué plazo: el vencimiento del derivado debe calzar con la fecha del pago o cobro.\n\n"
                "Los errores frecuentes son cubrir más que el flujo (eso ya es especular), descalzar "
                "el plazo y olvidar la línea de crédito o las garantías que pide el banco."
            ),
            callout=(
                "Ojo: la política real depende de cada empresa: márgenes, capacidad de traspasar "
                "precios, caja, líneas con bancos y apetito por riesgo. Esto es un punto de partida."
            ),
        ),
        Demo(
            title="Mueve el porcentaje cubierto y mira cuánto se angosta el costo",
            prompt=(
                "Con 0% cubierto, el costo depende entero del dólar. Con 100%, queda fijo en 898,89. "
                "Prueba 50%: si el dólar termina en 950, pagas en promedio 924,45."
            ),
            demo="hedge_ratio",
            params={"spot": 890.0, "forward": 898.89, "notional_usd": 500000.0},
            takeaway="Cubrir una parte reduce el rango de resultados sin eliminarlo.",
        ),
        Example(
            title="Con el mismo forward, un año ganó y el siguiente perdió",
            setup=(
                "Un importador debe pagar US\\$500.000 en 1 año y lo cubre con un forward. Se usan el "
                "dólar observado (Banco Central de Chile) y las tasas de referencia de cada fecha."
            ),
            steps=[
                "Inicio enero 2024: forward 896,98. El dólar terminó en 996,46. El forward ahorró "
                "cerca de \\$49,7 millones.",
                "Inicio enero 2025: forward 1.004,12. El dólar terminó en 907,13. El forward costó "
                "cerca de \\$48,5 millones más que no cubrirse.",
                "En los dos casos el importador supo su costo desde el primer día.",
            ],
            takeaway="Una cobertura se juzga por la certeza que dio, no por si le ganó al mercado.",
            lab="app_pages/5_USDCLP.py",
        ),
        Demo(
            title="Elige la fecha de decisión y mira qué habría pasado",
            prompt=(
                "Prueba enero 2024 y después enero 2025. El mismo forward a 1 año ahorró en un caso "
                "y costó en el otro. En ambos el costo se supo desde el primer día."
            ),
            demo="backtest",
            params={"years": 1.0, "nominal_usd": 500000.0},
            takeaway="El pasado no predice el próximo año: juzga la cobertura por la certeza que dio.",
        ),
        Summary(
            points=[
                "Cubre flujos conocidos, en un porcentaje acorde a su certeza y al mismo plazo.",
                "Cubrir más que tu exposición convierte la cobertura en especulación.",
                "Juzga una cobertura por la certeza que dio; el pasado no predice el próximo año.",
            ],
            next_hint="Prueba tus propios casos en los simuladores o responde el Quiz.",
        ),
    ],
)
