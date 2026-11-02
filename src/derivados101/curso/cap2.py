"""¿Qué es un derivado?

Caso ancla: compra a plazo de US$500.000 a 1 año a 898,89 (spot 890, tasas 5,11% / 4,07%).
Compensaciones verificadas con ``forward.settle_forward``.
"""

from .model import Chapter, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=2,
    slug="que-es-un-derivado",
    title="¿Qué es un derivado?",
    menu="Derivado",
    icon=":material/description:",
    goal="Un contrato que depende del dólar, y cuándo cubre o apuesta.",
    minutes=6,
    screens=[
        Concept(
            title="Un derivado es un contrato cuyo valor depende del dólar",
            body=(
                "Un **derivado** es un contrato entre dos partes. Su valor depende del precio de otro activo, el "
                "**subyacente**. Aquí el subyacente es el dólar. Al firmarlo no compras dólares: firmas una regla "
                "sobre qué pasa en una fecha futura según dónde esté el dólar.\n\n"
                "Las empresas suelen firmarlos directo con su banco, a la medida de su monto y su fecha. Eso se "
                "llama **OTC** (fuera de bolsa)."
            ),
            terms=[
                ("Nocional", "Cuántos dólares cubre el contrato. Sirve para calcular los pagos."),
                ("Plazo", "Cuándo vence el contrato."),
                ("Precio pactado", "El tipo de cambio fijado en el contrato."),
                ("Contraparte", "Con quién firmas. Si no cumple, pierdes lo que te debía."),
            ],
            callout=(
                "Ojo: en la realidad hay muchos derivados (forwards, opciones, swaps, futuros). Aquí verás "
                "forwards y opciones de dólar, los más simples."
            ),
        ),
        Example(
            title="Leer un contrato: compra a plazo de dólares",
            setup=(
                "Ejemplo. Un importador chileno de telas firma con su banco: \"compro US\\$500.000 a 1 año, "
                "a 898,89 pesos por dólar\"."
            ),
            steps=[
                "Nocional: US\\$500.000. Plazo: 1 año. Precio pactado: 898,89. Contraparte: el banco.",
                "Al vencer, obtiene sus dólares a 898,89, sin importar el dólar de ese día.",
                "Su costo queda fijado hoy: 500.000 × 898,89 = \\$449.445.000.",
            ],
            takeaway="Con nocional, plazo, precio y contraparte sabes exactamente qué firmaste.",
        ),
        Concept(
            title="El mismo contrato puede cubrir o especular",
            body=(
                "Lo que define el uso es lo que la empresa ya tiene, no el contrato.\n\n"
                "1. **Cobertura:** la empresa ya tiene una exposición y el derivado va en sentido contrario. Si el "
                "negocio pierde, el derivado gana. El riesgo total baja.\n"
                "2. **Especulación:** no hay exposición que cubrir, o el derivado va en el mismo sentido. Gana si "
                "acierta la dirección del dólar. El riesgo total sube."
            ),
        ),
        Demo(
            title="Con el contrato, el costo del importador deja de moverse",
            prompt=(
                "Mueve el dólar al vencimiento. Sin contrato, el costo de la factura sube y baja con el dólar. "
                "Con el contrato a 898,89, queda en \\$449.445.000 en cualquier escenario."
            ),
            demo="forward_vs_none",
            params={"spot": 890.0, "forward": 898.89, "notional_usd": 500_000},
            takeaway="Cubrirse cambia un costo incierto por uno fijo. A veces sale más caro y a veces más barato.",
        ),
        Example(
            title="Dos empresas, el mismo contrato, resultados distintos",
            setup=(
                "Ejemplo. Dos empresas compran US\\$500.000 a 1 año a 898,89. Una es el importador, que debe "
                "US\\$500.000. La otra no tiene flujos en dólares. Al vencer, el dólar está en 850."
            ),
            steps=[
                "El contrato pierde la diferencia: 500.000 × (850 − 898,89) = −\\$24.445.000 para ambas.",
                "El importador compra sus dólares a 850: paga \\$425.000.000.",
                "Su costo total es 425.000.000 + 24.445.000 = \\$449.445.000: el precio que fijó.",
                "La otra empresa no tiene dólares que comprar. Solo le queda la pérdida.",
            ],
            takeaway="Para el importador el contrato fijó su costo. Para la otra empresa fue una apuesta perdida.",
        ),
        Summary(
            points=[
                "Un derivado es un contrato cuyo valor depende del dólar: nocional, plazo, precio pactado y contraparte.",
                "Si compensa una exposición que ya tienes, es cobertura. Si la crea o la aumenta, es especulación.",
                "Con cobertura, lo que pierde el contrato lo gana el negocio, y al revés.",
            ],
            next_hint="Siguiente: ¿Qué es un forward? De dónde sale el 898,89.",
        ),
    ],
)
