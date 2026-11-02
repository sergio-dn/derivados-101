"""¿Qué es el MtM y por qué piden garantías?

Caso ancla: compra de US$500.000 a 898,89. MtM verificado con ``forward.forward_mtm``
(6 meses después, spot 870, tasas 5,11% / 4,07%: F_t = 874,34; MtM = −11.974.724).
Texto alineado con la sección MtM de ``app_pages/2_Forward.py``.
"""

from .model import Chapter, Concept, Demo, Example, Summary

CHAPTER = Chapter(
    number=5,
    slug="mtm-y-garantias",
    title="¿Qué es el MtM y por qué piden garantías?",
    menu="MtM y garantías",
    icon=":material/account_balance:",
    goal="Cuánto vale tu forward antes de vencer, y por qué eso puede pedirte caja.",
    minutes=5,
    screens=[
        Concept(
            title="El MtM es cuánto valdría cerrar hoy el contrato",
            body=(
                "El **MtM** (*mark-to-market*) es cuánto le debes al banco, o cuánto te debe él, si terminaran "
                "el contrato hoy. Se calcula todos los días, aunque nadie pague nada hasta el vencimiento.\n\n"
                "Se compara el precio pactado con el forward que hoy se obtendría para la misma fecha de "
                "vencimiento. Al firmar, el MtM es cero. Al vencer, el MtM es igual a la compensación."
            ),
            terms=[
                ("MtM", "Valor de cerrar hoy el contrato. Positivo: a tu favor. Negativo: en tu contra."),
            ],
            callout=(
                "Ojo: el cálculo real trae esa diferencia a valor presente y usa las curvas de tasas del banco. "
                "Aquí basta la idea."
            ),
        ),
        Example(
            title="6 meses después, el forward del importador está \\$11.974.724 en contra",
            setup=(
                "Ejemplo. Un importador chileno de telas compró US\\$500.000 a 1 año a 898,89. Pasaron 6 meses y "
                "el dólar está en 870."
            ),
            steps=[
                "Hoy, un forward nuevo a la misma fecha (6 meses) se pactaría a 874,34.",
                "Su contrato quedó 898,89 − 874,34 = 24,55 pesos por dólar peor que el de mercado.",
                "500.000 × 24,55, traído a valor presente, da un MtM de −\\$11.974.724.",
                "Si cerrara hoy, le pagaría eso al banco. Si espera, el resultado depende del dólar al vencer.",
            ],
            takeaway="Un dólar que baja deja en contra el forward de compra, aunque todavía no venza.",
            lab="app_pages/2_Forward.py",
        ),
        Concept(
            title="Con MtM en contra, el banco consume tu línea o pide garantías",
            body=(
                "Cuando el MtM está en tu contra, el banco corre el riesgo de que al vencer no le pagues. Se "
                "protege de 2 formas, según lo que firmaste con él:\n\n"
                "1. Consume tu **línea de crédito**. El monto en contra, más un colchón, se descuenta de la línea "
                "que te asignó. Queda menos línea para otros créditos, como financiar importaciones.\n"
                "2. Te pide **garantías**: caja o documentos mientras el MtM siga en contra. Se liberan cuando el "
                "dólar vuelve o el contrato vence."
            ),
            terms=[
                ("Línea de crédito", "Monto que el banco te asigna para operar derivados y otros créditos."),
                ("Garantía", "Caja o documentos que entregas al banco mientras el MtM está en tu contra."),
            ],
            callout=(
                "Ojo: la cobertura sigue funcionando. El problema es el calendario: la pérdida del forward se mide "
                "hoy y el ahorro del negocio llega al vencimiento. Antes de cubrirte, revisa cuánta línea tienes y "
                "cuánta caja aguantas si el dólar se mueve en contra."
            ),
        ),
        Demo(
            title="Mueve el forward de mercado y mira cuándo piden garantías",
            prompt=(
                "Baja el forward de mercado bajo 898,89: el MtM del importador queda en contra. Con 874,34 son "
                "unos \\$12 millones en contra, más que la línea de ejemplo de \\$10.000.000. Ahí el banco "
                "pediría garantías."
            ),
            demo="mtm",
            params={"forward": 898.89, "market_forward": 874.34, "notional_usd": 500_000, "credit_line_clp": 10_000_000},
            takeaway="Mientras el MtM en contra cabe en la línea, no sale caja. Si la supera, sale caja hoy.",
        ),
        Summary(
            points=[
                "El MtM es cuánto valdría cerrar hoy el forward. Es cero al firmar e igual a la compensación al vencer.",
                "Con MtM en contra, el banco consume tu línea de crédito o te pide garantías.",
                "La cobertura sigue funcionando. El riesgo es de caja: la pérdida se mide antes que el ahorro.",
            ],
            next_hint="Siguiente: ¿Qué es una opción? Protegerte del dólar sin renunciar a que se mueva a tu favor.",
        ),
    ],
)
