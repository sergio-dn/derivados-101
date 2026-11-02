"""¿Qué tipos de forward hay?

Caso ancla: compra de US$500.000 a 898,89. Compensaciones verificadas con ``forward.settle_forward``.
"""

from .model import Chapter, Chart, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=4,
    slug="tipos-de-forward",
    title="¿Qué tipos de forward hay?",
    menu="Tipos de forward",
    icon=":material/call_split:",
    goal="Comprar o vender a plazo, y pagar la diferencia o entregar los dólares.",
    minutes=5,
    screens=[
        Concept(
            title="El importador compra a plazo y el exportador vende a plazo",
            body=(
                "Un forward puede ser de **compra** o de **venta** de dólares. Para cubrirte, eliges el que va en "
                "sentido contrario a tu negocio.\n\n"
                "1. El importador debe dólares. Firma un forward de compra: fija cuántos pesos paga por ellos.\n"
                "2. El exportador va a recibir dólares. Firma un forward de venta: fija cuántos pesos recibe."
            ),
            terms=[
                ("Forward de compra", "Te obliga a comprar dólares al precio pactado. Gana si el dólar sube."),
                ("Forward de venta", "Te obliga a vender dólares al precio pactado. Gana si el dólar baja."),
            ],
        ),
        Concept(
            title="Al vencer, se entregan los dólares o se paga la diferencia",
            body=(
                "Hay 2 formas de liquidar un forward:\n\n"
                "1. **Entrega física** (*full delivery*): la empresa paga los pesos pactados y recibe los dólares, "
                "o al revés.\n"
                "2. **Compensación** (*non delivery*): no se mueven dólares. Se paga solo la diferencia entre el "
                "precio pactado y el dólar del día. La empresa compra o vende sus dólares en el mercado, como "
                "siempre.\n\n"
                "El costo final es el mismo en las 2. Cambia cuánta plata se mueve ese día y entre quiénes."
            ),
            callout=(
                "Ojo: lo usual es un forward con fecha fija. Algunos bancos ofrecen forwards con ventana, que se "
                "pueden liquidar en cualquier día de un rango de fechas. Esa flexibilidad tiene un precio menos "
                "favorable."
            ),
            chart=Chart(
                name="forward_payoff",
                params={"spot": 890.0, "forward": 898.89, "side": "buy", "notional_usd": 500_000},
                caption="Compensación de un forward de compra de US\\$500.000 a 898,89, según el dólar al vencer.",
            ),
        ),
        Demo(
            title="Mueve el dólar al vencimiento y mira quién le paga a quién",
            prompt=(
                "Sube el dólar al vencimiento: cuando pasa de 898,89, el banco le paga la diferencia al importador. "
                "Bájalo: bajo 898,89, el importador le paga al banco. Con 870 paga \\$14.445.000."
            ),
            demo="forward_settlement",
            params={"forward": 898.89, "spot_T": 870.0, "side": "buy", "notional_usd": 500_000},
            takeaway="La compensación es nocional × diferencia entre el dólar del día y el precio pactado.",
        ),
        Example(
            title="Con compensación, el costo del importador queda en \\$449.445.000",
            setup=(
                "Ejemplo. Un importador chileno de telas compró US\\$500.000 a 898,89 con compensación. Al vencer "
                "compra sus dólares en el mercado, al spot del día."
            ),
            steps=[
                "Si el dólar está en 950, el banco le paga 500.000 × (950 − 898,89) = \\$25.555.000.",
                "Si está en 850, él le paga al banco 500.000 × (898,89 − 850) = \\$24.445.000.",
                "En ambos casos, dólares a mercado más compensación suman \\$449.445.000 (500.000 × 898,89).",
            ],
            takeaway="El forward fija el costo final. La compensación solo cuadra la diferencia con el mercado.",
            chart=Chart(
                name="hedge_compare",
                params={"spot": 890.0, "forward": 898.89, "notional_usd": 500_000, "side": "buy"},
                caption="Costo en pesos de la factura con y sin forward, según el dólar al vencer.",
            ),
            lab="app_pages/2_Forward.py",
        ),
        Summary(
            points=[
                "El importador cubre con un forward de compra. El exportador, con uno de venta.",
                "Entrega física o compensación dejan el mismo costo final. Cambia solo el flujo de ese día.",
                "Compensación positiva: el banco te paga. Negativa: tú le pagas al banco.",
            ],
            next_hint="Siguiente: ¿Qué es el MtM y por qué piden garantías? Lo que pasa antes de vencer.",
        ),
    ],
)
