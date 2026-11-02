"""¿Qué es un forward?

Caso ancla: spot 890, tasas 5,11% CLP / 4,07% USD, 1 año -> forward 898,89 (``forward.forward_rate``).
"""

from .model import Chapter, Chart, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=3,
    slug="que-es-un-forward",
    title="¿Qué es un forward?",
    menu="Forward",
    icon=":material/trending_flat:",
    goal="Fijar hoy el dólar de una fecha futura, y de dónde sale ese precio.",
    minutes=5,
    screens=[
        Concept(
            title="Un forward fija hoy el dólar de una fecha futura",
            body=(
                "Un **forward** es una compra o venta de dólares a una fecha futura, a un precio fijado hoy. "
                "Obliga a ambas partes y no tiene costo al firmar.\n\n"
                "El banco no adivina el dólar. Calcula cuánto le cuesta replicar el contrato hoy: pide pesos "
                "prestados, compra dólares y los invierte hasta el vencimiento. Como la tasa en pesos es mayor que "
                "la tasa en dólares, el forward queda sobre el spot. Esa diferencia son los **puntos forward**."
            ),
            terms=[
                ("Precio forward", "Spot × (1 + tasa CLP)^plazo ÷ (1 + tasa USD)^plazo."),
                ("Puntos forward", "Precio forward − spot. Reflejan la diferencia de tasas entre las 2 monedas."),
            ],
            callout=(
                "Ojo: en la realidad el banco agrega un margen, y las tasas que usa no son exactamente las de "
                "este ejemplo. La fórmula da el orden de magnitud."
            ),
            chart=Chart(
                name="forward_points",
                params={"spot": 890.0, "r_dom": 0.0511, "r_for": 0.0407},
                caption="Ejemplo: spot 890, tasa CLP 5,11%, tasa USD 4,07%. A más plazo, más puntos.",
            ),
        ),
        Example(
            title="El forward a 1 año del importador: 898,89",
            setup=(
                "Ejemplo. Un importador chileno de telas quiere comprar US\\$500.000 a 1 año. Spot 890, tasa en "
                "pesos 5,11% y tasa en dólares 4,07%."
            ),
            steps=[
                "Pesos a 1 año: 890 × 1,0511 = 935,48 por cada dólar de hoy.",
                "Dólares a 1 año: cada dólar de hoy rinde 1,0407.",
                "Forward = 935,48 ÷ 1,0407 = 898,89 CLP por USD.",
                "Puntos forward: 898,89 − 890 = 8,89 pesos.",
            ],
            takeaway="Fijar el dólar a 1 año cuesta 8,89 pesos sobre el spot, por la diferencia de tasas.",
            lab="app_pages/2_Forward.py",
        ),
        Demo(
            title="Mueve las tasas y el plazo, y mira cómo cambia el forward",
            prompt=(
                "Alarga el plazo: los puntos forward crecen. Iguala la tasa en pesos con la tasa en dólares: "
                "los puntos desaparecen y el forward queda igual al spot."
            ),
            demo="forward_calc",
            params={"spot": 890.0, "r_dom": 0.0511, "r_for": 0.0407, "years": 1.0},
            takeaway="El forward depende de spot, tasas y plazo. No depende de lo que alguien espere del dólar.",
        ),
        Summary(
            points=[
                "Un forward fija hoy el precio de comprar o vender dólares en una fecha futura. Obliga a ambas partes.",
                "Su precio sale del spot y la diferencia de tasas entre pesos y dólares.",
                "Los puntos forward no son un pronóstico del dólar. Crecen con el plazo.",
            ],
            next_hint="Siguiente: ¿Qué tipos de forward hay? Compra o venta, y cómo se liquida.",
        ),
    ],
)
